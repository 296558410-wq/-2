"""build_snapshot — V3 immutable research snapshot (task V/VI/VII/VIII).

LIVE RAW -> SNAPSHOT CUT -> COPY/MATERIALIZE -> SHA256 -> IMMUTABLE MANIFEST -> RESEARCH

After this runs, research reads the snapshot only. The live collector may keep
appending; the snapshot must not change.

Writes only under trader_v3/data/snapshots/ (ignored by git: data/ + *.parquet)
and trader_v3/research/snapshot/. Places NO orders. Read-only on market data.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import os
import shutil
import stat
import sys

import pandas as pd

V3 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, V3)
from microstructure import timestamp_unit_guard as TG  # noqa: E402

SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SRC = {
    "staging_fxtm": r"C:\AIQuant\data\staging_fxtm\ticks_*.parquet",
    "live_fxtm": r"C:\AIQuant\data\live_fxtm\ticks_*.parquet",
}
DEST = os.path.join(V3, "data", "snapshots", SNAPSHOT_ID)
OUT = os.path.join(V3, "research", "snapshot")
TS_UNIT = "ms"          # DECLARED, not inferred (native dtype datetime64[ms, UTC])


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def file_meta(src_path, dst_path, source, snapshot_time):
    d = pd.read_parquet(dst_path, columns=["bid", "ask", "ts_utc"])
    desc = TG.describe(d["ts_utc"], TS_UNIT)
    ts_ns = d["ts_utc"].astype("int64").to_numpy()      # ms since epoch (declared)
    order = TG.assert_monotonic(ts_ns)
    ooo = int((pd.Series(ts_ns).diff().dropna() < 0).sum())
    return {
        "path": dst_path.replace("\\", "/"),
        "source_path": src_path.replace("\\", "/"),
        "size": os.path.getsize(dst_path),
        "sha256": sha256(dst_path),
        "row_count": int(len(d)),
        "ts_min": str(d["ts_utc"].min()),
        "ts_max": str(d["ts_utc"].max()),
        "timezone": desc["timestamp_timezone"],
        "timestamp_unit": TS_UNIT,
        "timestamp_dtype": desc["timestamp_dtype"],
        "duplicate_count": int(d["ts_utc"].duplicated().sum()),
        "out_of_order_count": ooo,
        "monotonic": order["monotonic"],
        "source": source,
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_time": snapshot_time,
    }


def main():
    os.makedirs(DEST, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    snapshot_time = now_utc()
    per_file = []
    for source, pattern in SRC.items():
        sub = os.path.join(DEST, source)
        os.makedirs(sub, exist_ok=True)
        files = sorted(glob.glob(pattern))
        if not files:
            raise SystemExit(f"no files for {source}: {pattern}")
        for f in files:
            dst = os.path.join(sub, os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst)
            m = file_meta(f, dst, source, snapshot_time)
            per_file.append(m)
            # enforce immutability after hashing
            os.chmod(dst, stat.S_IREAD)

    total_rows = sum(m["row_count"] for m in per_file)
    manifest = {
        "schema": "v3_data_snapshot/1",
        "SNAPSHOT_ID": SNAPSHOT_ID,
        "CREATED_AT_UTC": snapshot_time,
        "SOURCE_ROOT": "C:/AIQuant/data/{staging_fxtm,live_fxtm}",
        "FILE_COUNT": len(per_file),
        "TOTAL_ROWS": total_rows,
        "MIN_TIMESTAMP": min(m["ts_min"] for m in per_file),
        "MAX_TIMESTAMP": max(m["ts_max"] for m in per_file),
        "LIVE_SOURCE_MUTABLE": True,
        "RESEARCH_SNAPSHOT_IMMUTABLE": True,
        "IMMUTABILITY_MECHANISM": "copy-on-cut + read-only file attribute + content sha256 per file",
        "timestamp_unit": TS_UNIT,
        "timezone": "UTC",
        "files": per_file,
    }
    raw = json.dumps(manifest, indent=1, sort_keys=True)
    manifest["SHA256"] = hashlib.sha256(raw.encode()).hexdigest()
    mpath = os.path.join(OUT, f"V3_DATA_SNAPSHOT_{SNAPSHOT_ID}.json")
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    # the snapshot data dir gets its own copy of the manifest
    with open(os.path.join(DEST, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)

    # ---------------- duplicate triage (task VII): 3 levels -----------------
    dup = {"schema": "v3_dup_triage/1", "SNAPSHOT_ID": SNAPSHOT_ID, "generated_utc": now_utc(),
           "method": "exact-equality at three levels, computed per family on the SNAPSHOT copy",
           "EVENT_IDENTITY": "DATA_GAP", "files": {}}
    for source in SRC:
        frames = []
        paths = sorted(glob.glob(os.path.join(DEST, source, "ticks_*.parquet")))
        for p in paths:
            d = pd.read_parquet(p, columns=["bid", "ask", "ts_utc"])
            d["source"] = os.path.basename(p)
            frames.append(d)
        if not frames:
            continue
        allf = pd.concat(frames, ignore_index=True)
        l1 = int(allf["ts_utc"].duplicated().sum())
        l2 = int(allf.duplicated(subset=["ts_utc", "bid", "ask"]).sum())
        l3 = int(allf.duplicated(subset=["ts_utc", "bid", "ask", "source"]).sum())
        dup["files"][source] = {
            "rows": int(len(allf)),
            "DUP_TIMESTAMP_COUNT": l1,
            "DUP_QUOTE_COUNT": l2,
            "DUP_EVENT_COUNT": l3,
            "fraction_of_rows": round(l1 / len(allf), 8),
        }
        dup[f"{source}_DUP_TIMESTAMP_COUNT"] = l1
        dup[f"{source}_DUP_QUOTE_COUNT"] = l2
        dup[f"{source}_DUP_EVENT_COUNT"] = l3
    dup["CONCLUSION"] = ("duplicates are same-timestamp repeats; DUP_QUOTE_COUNT isolates identical "
                          "(ts,bid,ask) quotes. No event id exists in the feed, so true event identity "
                          "cannot be proven -> EVENT_IDENTITY = DATA_GAP. Nothing is deleted.")
    with open(os.path.join(OUT, f"V3_DUP_TRIAGE_{SNAPSHOT_ID}.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(dup, f, indent=1)

    print(json.dumps({"SNAPSHOT_ID": SNAPSHOT_ID, "FILE_COUNT": len(per_file),
                      "TOTAL_ROWS": total_rows, "MANIFEST_SHA256": manifest["SHA256"],
                      "staging_dup": dup.get("staging_fxtm_DUP_TIMESTAMP_COUNT"),
                      "live_dup": dup.get("live_fxtm_DUP_TIMESTAMP_COUNT"),
                      "live_dup_quote": dup.get("live_fxtm_DUP_QUOTE_COUNT")}, indent=1))


if __name__ == "__main__":
    main()
