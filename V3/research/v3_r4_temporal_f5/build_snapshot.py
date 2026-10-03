# -*- coding: utf-8 -*-
"""R4 W1: build the widest SAME-SOURCE (FXTM) immutable tick snapshot + manifest + SHA256.

Only staging_fxtm and live_fxtm are used. staging_duka is a DIFFERENT source with a DIFFERENT
schema (integer-scaled bid/ask, real bid/ask volume, hour-local ms) and is deliberately EXCLUDED.
"""
from __future__ import annotations
import glob, hashlib, json, os, shutil, sys
import pandas as pd, numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [("staging_fxtm", r"C:\AIQuant\data\staging_fxtm"),
       ("live_fxtm", r"C:\AIQuant\data\live_fxtm")]
SNAP = os.path.join(HERE, "SNAPSHOT_FXTM_R4")
os.makedirs(SNAP, exist_ok=True)

man = {"schema": "v3_r4_fxtm_snapshot_manifest/1", "SNAPSHOT_ID": "V3-SNAP-FXTM-R4",
       "purpose": "widest SAME-SOURCE FXTM tick sample for the R4 temporal resubmission",
       "excluded_sources": {"staging_duka": "DIFFERENT source and DIFFERENT schema (ms, integer-scaled ask/bid, ask_vol/bid_vol, hour) - forbidden to splice per the R4 task rules"},
       "format": {"timestamp_field": "ts_utc", "unit": "ms", "timezone": "UTC",
                  "fields_used": ["ts_utc", "bid", "ask"], "volume": "0 on 100% of rows in both sources"},
       "sources": [], "files": []}

total_rows = 0
tmin, tmax = None, None
for tag, d in SRC:
    outdir = os.path.join(SNAP, tag); os.makedirs(outdir, exist_ok=True)
    fs = sorted(glob.glob(os.path.join(d, "ticks_*.parquet")))
    rows_src = 0
    for f in fs:
        df = pd.read_parquet(f, columns=["ts_utc", "bid", "ask"])
        rows = int(len(df))
        rows_src += rows
        t0 = df["ts_utc"].min(); t1 = df["ts_utc"].max()
        dst = os.path.join(outdir, os.path.basename(f))
        if not os.path.exists(dst):
            shutil.copy2(f, dst)
        sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
        man["files"].append({"source": tag, "file": os.path.basename(f), "rows": rows,
                             "min_ts": str(t0), "max_ts": str(t1), "sha256": sha})
        tmin = t0 if tmin is None or t0 < tmin else tmin
        tmax = t1 if tmax is None or t1 > tmax else tmax
        total_rows += rows
    man["sources"].append({"tag": tag, "dir": d, "files": len(fs), "rows": rows_src})

man["TOTAL_ROWS"] = total_rows
man["MIN_TIMESTAMP"] = str(tmin); man["MAX_TIMESTAMP"] = str(tmax)
man["calendar_span_days"] = float((tmax - tmin).total_seconds() / 86400.0)
man["RESEARCH_SNAPSHOT_IMMUTABLE"] = True
json.dump(man, open(os.path.join(SNAP, "MANIFEST.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
h = hashlib.sha256(open(os.path.join(SNAP, "MANIFEST.json"), "rb").read()).hexdigest()
print("SNAPSHOT:", SNAP)
print("sources:", [(s["tag"], s["files"], s["rows"]) for s in man["sources"]])
print("TOTAL_ROWS:", total_rows)
print("span:", man["MIN_TIMESTAMP"], "->", man["MAX_TIMESTAMP"], f"= {man['calendar_span_days']:.2f} calendar days")
print("manifest sha256:", h)
print("G1 >=90d ?", man["calendar_span_days"] >= 90)
