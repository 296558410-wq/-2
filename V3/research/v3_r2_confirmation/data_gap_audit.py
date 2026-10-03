# -*- coding: utf-8 -*-
"""V3 R2 data-gap audit: (C) volume/OFI availability, (D) event x tick alignment attrition.

Read-only. No orders. Writes DATA_GAP_AUDIT.json next to this script.
"""
from __future__ import annotations
import glob, json, os, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
SNAP2 = os.path.join(V3, "data", "snapshots", "V3-SNAP-PIT2-20261001T131500Z")
GAP = 60_000
out = {"schema": "v3_r2_data_gap_audit/1"}

# ---------------- C: volume / OFI ----------------
print("=== C. volume / OFI ===")
volcols = {}
for tag, snap in (("MAIN", SNAP), ("PIT2", SNAP2)):
    files = sorted(glob.glob(os.path.join(snap, "*", "*.parquet")))
    cols = None; per = []
    cand = [c for c in ("volume", "volume_real", "last", "tick_volume", "real_volume", "bid_vol", "ask_vol",
                        "bid_size", "ask_size")]
    for f in files:
        df = pd.read_parquet(f)
        if cols is None:
            cols = list(df.columns)
        present = [c for c in cand if c in df.columns]
        row = {"file": os.path.basename(f), "rows": int(len(df)), "present_volume_like": present}
        for c in present:
            try:
                v = df[c].to_numpy()
                row[c + "_nonzero"] = int(np.count_nonzero(v)) if v.dtype.kind in "iu" else int(np.count_nonzero(np.nan_to_num(v)))
                row[c + "_min"] = float(np.nanmin(v)) if len(v) else None
                row[c + "_max"] = float(np.nanmax(v)) if len(v) else None
            except Exception:
                pass
        per.append(row)
    volcols[tag] = {"snapshot": os.path.basename(snap), "files": len(files), "columns": cols,
                    "volume_like_columns_present": sorted({c for r in per for c in r["present_volume_like"]}),
                    "per_file": per[:6],
                    "any_nonzero": any(r.get(c + "_nonzero", 0) > 0 for r in per
                                       for c in r["present_volume_like"])}
    print(f"  {tag}: files={len(files)} columns={cols}")
    print(f"       volume-like present={volcols[tag]['volume_like_columns_present']} any_nonzero={volcols[tag]['any_nonzero']}")
out["C_volume_ofi"] = volcols
out["C_verdict"] = {
    "true_volume_available": bool(volcols["MAIN"]["any_nonzero"] or volcols["PIT2"]["any_nonzero"]),
    "bid_ask_executed_volume": "ABSENT" if not any("bid_vol" in c or "ask_vol" in c or "bid_size" in c
                                                   for c in volcols["MAIN"]["columns"]) else "PRESENT",
    "true_ofi_constructible": "NO" if not (volcols["MAIN"]["any_nonzero"] or volcols["PIT2"]["any_nonzero"]) else "YES",
    "verdict": "TRUE_OFI_DATA_UNAVAILABLE" if not (volcols["MAIN"]["any_nonzero"] or volcols["PIT2"]["any_nonzero"]) else "TRUE_OFI_AVAILABLE",
    "note": "the schema carries a volume column (and volume_real/last in some vintages) but every value is identically 0; there is no bid/ask size field. Every 'flow' feature in R1 is therefore a QUOTE-BASED PROXY (sign of price change), not order flow."
}

# ---------------- D: event x tick alignment ----------------
print("\n=== D. event x tick alignment ===")
vd = os.path.join(V3, "research", "v3_pit_supplement_r1", "vintages")
evfiles = sorted(glob.glob(os.path.join(vd, "*.json")))
raw = []
for fn in evfiles:
    j = json.load(open(fn, encoding="utf-8"))
    for e in j.get("events", []):
        raw.append({"file": os.path.basename(fn), "pub_time": e.get("pub_time"), "name": e.get("event_name"),
                    "country": e.get("country"), "importance": e.get("importance")})
stages = {"raw_event_rows": len(raw),
          "files": [os.path.basename(f) for f in evfiles]}
# PIT-qualified = has a parseable pub_time
pit = []
for r in raw:
    pt = r.get("pub_time")
    if not pt:
        continue
    try:
        t = pd.Timestamp(pt, tz="Asia/Shanghai").tz_convert("UTC").value // 10**6
    except Exception:
        try:
            t = pd.Timestamp(pt).value // 10**6
        except Exception:
            continue
    pit.append((int(t), r))
stages["pit_qualified"] = len(pit)
stages["no_parseable_pub_time"] = len(raw) - len(pit)
# tick window
files2 = sorted(glob.glob(os.path.join(SNAP2, "*", "*.parquet")))
d2 = pd.concat([pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files2], ignore_index=True)
d2 = d2.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
ts2 = d2["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
stages["tick_window_utc"] = [str(pd.to_datetime(ts2[0], unit="ms", utc=True)), str(pd.to_datetime(ts2[-1], unit="ms", utc=True))]
inwin = [t for t, _ in pit if ts2[0] <= t <= ts2[-1]]
stages["within_tick_window"] = len(inwin)
stages["outside_tick_window"] = len(pit) - len(inwin)
pre_ok = [t for t in inwin if t - 60_000 >= ts2[0]]
stages["with_complete_pre_60s_window"] = len(pre_ok)
post_ok = [t for t in pre_ok if t + 15 * 60_000 <= ts2[-1]]
stages["with_complete_post_15min_window"] = len(post_ok)
stages["final_researchable"] = len(post_ok)
# per month/date distribution of the losses
by_date = {}
for t, r in pit:
    dt_ = str(pd.to_datetime(t, unit="ms", utc=True).date())
    by_date.setdefault(dt_, {"events": 0, "in_tick_window": 0})
    by_date[dt_]["events"] += 1
    if ts2[0] <= t <= ts2[-1]:
        by_date[dt_]["in_tick_window"] += 1
stages["by_date"] = by_date
stages["loss_reasons"] = {
    "outside_tick_window": "the vintage roster covers 2026-09-28..10-03 while the PIT2 tick snapshot ends 2026-10-01T12:54Z (and starts 2026-09-21) - all events after the snapshot end have no ticks",
    "incomplete_pre_window": "events in the first 60s of the snapshot",
    "incomplete_post_window": "events in the last 15 min of the snapshot",
    "pit_rule_unchanged": "no window was widened and no PIT standard was relaxed to raise the count"
}
out["D_event_alignment"] = stages
# distinct-timestamp accounting: the R1 loader deduplicated on (ts, filename), which collapsed
# simultaneous releases. Report BOTH the row count and the distinct-timestamp count.
from collections import Counter
tsc = Counter(t for t, _ in pit)
dup_groups = {t: c for t, c in tsc.items() if c > 1}
stages["distinct_timestamps_total"] = len(tsc)
stages["simultaneous_groups"] = len(dup_groups)
stages["rows_collapsed_by_dedup"] = len(pit) - len(tsc)
stages["distinct_timestamps_in_tick_window"] = len([t for t in tsc if ts2[0] <= t <= ts2[-1]])
stages["R1_loader_used"] = {"raw_appended": len(pit), "after_set_dedup": len(tsc),
                            "note": "the R1 event loader deduplicated on (ts, filename) so 283 rows collapsed to 75 distinct timestamps; this UNDER-COUNTED the event sample"}
print(json.dumps({k: stages[k] for k in ("raw_event_rows", "pit_qualified", "within_tick_window",
                                         "distinct_timestamps_total", "simultaneous_groups",
                                         "rows_collapsed_by_dedup", "distinct_timestamps_in_tick_window")},
                 ensure_ascii=False, indent=1))

json.dump(out, open(os.path.join(HERE, "DATA_GAP_AUDIT.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\nwrote DATA_GAP_AUDIT.json")
