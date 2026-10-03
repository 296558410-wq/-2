# -*- coding: utf-8 -*-
"""V3 Temporal Hold — daily same-source coverage check (READ-ONLY on data; appends its own log).

Boundaries (task book): same-source only (staging_fxtm + live_fxtm); no DUKA/other splicing;
no alpha research; keeps R4 frozen protocol untouched; no DEMO/LIVE.
Writes: HOLD_LOG.jsonl (append), HOLD_STATUS.json (latest). Nothing else is modified.
"""
from __future__ import annotations
import datetime as dt, glob, hashlib, json, os, sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\AIQuant"
SRC = [("staging_fxtm", os.path.join(REPO, "data", "staging_fxtm")),
       ("live_fxtm", os.path.join(REPO, "data", "live_fxtm"))]
HOLD = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HOLD, "HOLD_LOG.jsonl")
STATUS = os.path.join(HOLD, "HOLD_STATUS.json")
GAP_MS, DAY_MS = 60_000, 86_400_000
G1_DAYS, G2_DAYS = 90.0, 40


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ts_ms(p):
    """Read the ts column and return int64 epoch-ms regardless of the stored arrow resolution."""
    import pyarrow.parquet as pq
    t = pq.read_table(p, columns=["ts_utc"]).to_pandas()["ts_utc"]
    s = str(t.dtype)
    if s.startswith("datetime64"):
        try:
            unit = s[len("datetime64["):s.index(",") if "," in s else s.index("]")]
        except Exception:  # noqa: BLE001
            unit = "ns"
        a = t.astype("int64")
        return {"s": a * 10 ** 3, "ms": a, "us": a // 10 ** 3, "ns": a // 10 ** 6}.get(unit, a)
    return t.astype("int64")


def main():
    now = dt.datetime.now(dt.timezone.utc)
    rec = {"schema": "v3_temporal_hold_check/1", "check_utc": now.isoformat(), "source_rule": "same-source only (staging_fxtm+live_fxtm); DUKA excluded",
           "data_status": "OK", "notes": []}
    all_ts = []
    per_src = {}
    file_hashes = {}
    monotonic_ok, cols_ok = True, True
    vol_all_zero = True
    files_now = []
    try:
        import pyarrow.parquet as pq  # noqa: F401
        for tag, d in SRC:
            fs = sorted(glob.glob(os.path.join(d, "ticks_*.parquet")))
            rows = 0
            smin, smax = None, None
            for p in fs:
                pf = pq.ParquetFile(p)
                cols = {f.name for f in pf.schema_arrow}
                if not {"bid", "ask", "ts_utc"}.issubset(cols):
                    cols_ok = False
                t = ts_ms(p)
                if len(t) and not bool(np.all(np.diff(t) >= 0)):
                    monotonic_ok = False
                rows += int(pf.metadata.num_rows)
                all_ts.append(t)
                if len(t):
                    a, b = int(t.min()), int(t.max())
                    smin = a if smin is None else min(smin, a)
                    smax = b if smax is None else max(smax, b)
                key = f"{tag}/{os.path.basename(p)}"
                file_hashes[key] = sha256(p)
                files_now.append(key)
            if tag == "live_fxtm" and fs:
                v = pq.read_table(fs[-1], columns=["volume"]).to_pandas()["volume"].to_numpy()
                vol_all_zero = bool(np.nanmax(np.abs(v.astype(float))) == 0)
            fmt = lambda x: str(dt.datetime.fromtimestamp(int(x) / 1000, dt.timezone.utc)) if x is not None else None
            per_src[tag] = {"dir": d, "files": len(fs), "rows": rows, "t_min_utc": fmt(smin), "t_max_utc": fmt(smax)}
    except Exception as e:  # noqa: BLE001
        rec["data_status"] = "DATA_BLOCKED"
        rec["notes"].append(f"read failure: {str(e)[:200]}")

    if all_ts:
        t = np.sort(np.concatenate(all_ts))
        span_days = float((t[-1] - t[0]) / DAY_MS)
        active_days = int(len(np.unique(t // DAY_MS)))
        d = np.diff(t)
        segs = int((d > GAP_MS).sum()) + 1
        # frozen-R4-definition segments (dd<=0 | dd>GAP) for comparability with the R4 snapshot stats
        dd = np.diff(t, prepend=t[0])
        segs_frozen = int(((dd <= 0) | (dd > GAP_MS)).sum())
        big = np.flatnonzero(d > 3_600_000)
        top = sorted(({"gap_hours": round(float(d[i]) / 3.6e6, 2),
                       "from": str(dt.datetime.fromtimestamp(int(t[i]) / 1000, dt.timezone.utc)),
                       "to": str(dt.datetime.fromtimestamp(int(t[i + 1]) / 1000, dt.timezone.utc))}
                      for i in big), key=lambda x: -x["gap_hours"])[:5]
        rec.update({
            "files_total": len(file_hashes), "rows_total": int(sum(len(x) for x in all_ts)),
            "per_source": per_src,
            "t_min_utc": str(dt.datetime.fromtimestamp(int(t[0]) / 1000, dt.timezone.utc)),
            "t_max_utc": str(dt.datetime.fromtimestamp(int(t[-1]) / 1000, dt.timezone.utc)),
            "calendar_days": round(span_days, 4), "active_days": active_days,
            "time_gap_segments": segs, "segments_frozen_r4_def": segs_frozen,
            "gaps": {"gt_1h": int((d > 3_600_000).sum()), "gt_6h": int((d > 21_600_000).sum()),
                      "gt_24h": int((d > 86_400_000).sum()), "top5": top},
            "PIT": {"per_file_monotonic": monotonic_ok, "required_cols_present": cols_ok,
                     "ts_unit": "ms (UTC)", "volume_all_zero_sample_last_live_file": vol_all_zero,
                     "note": "PIT by construction: captured live per 15-min tick job; no revision"},
            "manifest_sha256": hashlib.sha256(json.dumps(dict(sorted(file_hashes.items())), sort_keys=True).encode()).hexdigest(),
            "G1_ge_90d": bool(span_days >= G1_DAYS), "G2_ge_40_active_days": bool(active_days >= G2_DAYS),
            "ready": bool(span_days >= G1_DAYS and active_days >= G2_DAYS),
            "eta_90d_utc": str(dt.datetime.fromtimestamp((int(t[0]) + 90 * DAY_MS) / 1000, dt.timezone.utc)),
        })
    else:
        rec["data_status"] = "UNKNOWN"

    # continuity vs previous record
    prev = None
    if os.path.exists(LOG):
        try:
            lines = [l for l in open(LOG, encoding="utf-8") if l.strip()]
            prev = json.loads(lines[-1]) if lines else None
        except Exception:  # noqa: BLE001
            prev = None
    if prev and rec.get("t_max_utc") and prev.get("t_max_utc"):
        prev_files = set(prev.get("files", [])) if isinstance(prev.get("files"), list) else set()
        rec["new_files_since_last"] = sorted(set(files_now) - prev_files) if prev_files else []
        adv_h = (dt.datetime.fromisoformat(rec["t_max_utc"]) - dt.datetime.fromisoformat(prev["t_max_utc"])).total_seconds() / 3600.0
        since_h = (now - dt.datetime.fromisoformat(prev["check_utc"])).total_seconds() / 3600.0
        rec["max_ts_advanced_hours"] = round(adv_h, 2)
        rec["hours_since_prev_check"] = round(since_h, 2)
        if adv_h < 1.0 and since_h > 36:
            rec["stall_warning"] = True
            rec["notes"].append("STALL: data end timestamp has not advanced >=1h in >36h")
    rec["files"] = files_now

    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush(); os.fsync(fh.fileno())
    with open(STATUS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: rec.get(k) for k in ("check_utc", "data_status", "files_total", "rows_total", "calendar_days",
                                               "active_days", "time_gap_segments", "segments_frozen_r4_def", "t_max_utc",
                                               "G1_ge_90d", "G2_ge_40_active_days", "ready", "eta_90d_utc", "gaps",
                                               "stall_warning")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
