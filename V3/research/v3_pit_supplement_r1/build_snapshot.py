# -*- coding: utf-8 -*-
"""Build the Phase-2 PIT supplement snapshot (copy-on-cut) + PIT registry.

Snapshot covers the tick days that overlap the two frozen Jin10 calendar vintages:
  2026-09-21 .. 2026-10-01
Read-only source dirs are never modified. No orders.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import stat
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
LIVE = r"C:\AIQuant\data\live_fxtm"
STAGE = r"C:\AIQuant\data\staging_fxtm"
CROSS = r"C:\AIQuant\research\v3_crossmarket_sources"
SNAP_ID = "V3-SNAP-PIT2-20261001T131500Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAP_ID)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    days = [f"2026{d:02d}{m:02d}" for d in [21, 22, 23, 24, 25, 28, 29, 30] for m in []]
    days = ["20260921", "20260922", "20260923", "20260924", "20260925",
            "20260928", "20260929", "20260930", "20261001"]
    raw = os.path.join(SNAP, "raw_ticks")
    os.makedirs(raw, exist_ok=True)
    files, total = [], 0
    for d in days:
        src = None
        for root in (LIVE, STAGE):
            p = os.path.join(root, f"ticks_{d}.parquet")
            if os.path.exists(p):
                src = p
                break
        if not src:
            continue
        dst = os.path.join(raw, f"ticks_{d}.parquet")
        if os.path.exists(dst):
            os.chmod(dst, stat.S_IWRITE)
        shutil.copy2(src, dst)
        df = pd.read_parquet(dst, columns=["ts_utc", "bid", "ask"])
        rows = len(df)
        total += rows
        ts = df["ts_utc"]
        files.append({"file": f"raw_ticks/ticks_{d}.parquet", "source": src, "rows": rows,
                      "sha256": sha(dst), "ts_min": str(ts.min()), "ts_max": str(ts.max()),
                      "bytes": os.path.getsize(dst)})
        try:
            os.chmod(dst, stat.S_IREAD)
        except Exception:  # noqa: BLE001
            pass
        print(f"  {d} rows={rows}")

    man = {"schema": "v3_data_snapshot/1", "SNAPSHOT_ID": SNAP_ID,
           "CREATED_AT_UTC": datetime.now(timezone.utc).isoformat(),
           "SOURCE_ROOT": "C:/AIQuant/data/{live_fxtm,staging_fxtm}",
           "PURPOSE": "phase2 PIT supplement: tick window overlapping the frozen Jin10 calendar vintages",
           "FILE_COUNT": len(files), "TOTAL_ROWS": total,
           "MIN_TIMESTAMP": min(f["ts_min"] for f in files),
           "MAX_TIMESTAMP": max(f["ts_max"] for f in files),
           "LIVE_SOURCE_MUTABLE": True, "RESEARCH_SNAPSHOT_IMMUTABLE": True,
           "IMMUTABILITY_MECHANISM": "copy-on-cut + read-only file attribute + content sha256 per file",
           "timestamp_unit": "ms", "timezone": "UTC", "files": files}
    # calendar vintages (frozen, hashed)
    vint_dir = os.path.join(HERE, "vintages")
    vintages = []
    for fn in sorted(os.listdir(vint_dir)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(vint_dir, fn)
        j = json.load(open(p, encoding="utf-8"))
        vintages.append({"file": fn, "sha256": sha(p), "count": j.get("count"),
                         "pub_time_min": j.get("pub_time_min"), "pub_time_max": j.get("pub_time_max")})
    cal = os.path.join(os.path.dirname(os.path.dirname(V3)), "v3_long_history_data", "V3_JIN10_EVENT_PIT.json")
    cal = os.path.normpath(cal)
    if os.path.exists(cal):
        cj = json.load(open(cal, encoding="utf-8"))
        vintages.append({"file": "V3_JIN10_EVENT_PIT.json (2026-09-25 vintage)", "sha256": sha(cal),
                         "count": cj.get("count"),
                         "pub_time_min": min(e["pub_time_utc"] for e in cj["events"]),
                         "pub_time_max": max(e["pub_time_utc"] for e in cj["events"])})
    man["calendar_vintages"] = vintages
    json.dump(man, open(os.path.join(SNAP, "MANIFEST.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # cross-market artifacts (referenced, not re-fetched: Yahoo live fetch = 403)
    cross = []
    for fn in sorted(os.listdir(CROSS)):
        if fn.startswith("series_") and fn.endswith(".parquet"):
            p = os.path.join(CROSS, fn)
            cross.append({"file": fn, "path": p, "sha256": sha(p), "bytes": os.path.getsize(p)})
    json.dump({"schema": "v3_crossmarket_artifact_refs/1", "note": "Yahoo live re-fetch returned HTTP 403; using these extant artifacts",
               "artifacts": cross},
              open(os.path.join(HERE, "CROSSMARKET_ARTIFACT_REFS.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"snapshot": SNAP_ID, "files": len(files), "rows": total,
                      "min": man["MIN_TIMESTAMP"], "max": man["MAX_TIMESTAMP"],
                      "calendar_vintages": len(vintages), "crossmarket_artifacts": len(cross)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
