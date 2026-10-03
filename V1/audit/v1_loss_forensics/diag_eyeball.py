# -*- coding: utf-8 -*-
"""Eyeball dump: raw ticks around candidate label windows for trade 2378322488 (true 14:33:03->14:39:16,
entry 4164.94, SL 4174.09). Which window actually contains the trade path? Read-only."""
import os
import numpy as np
import pandas as pd

TICKS = r"C:\AIQuant\data\live_fxtm"
t = pd.read_parquet(os.path.join(TICKS, "ticks_20261001.parquet"), columns=["ts_utc", "bid", "ask"])
ts = t["ts_utc"].astype("int64").to_numpy(); o = np.argsort(ts); ts = ts[o]
b = t["bid"].to_numpy()[o]; a = t["ask"].to_numpy()[o]

def dump(lo, hi, label):
    L0 = int(pd.Timestamp(lo, tz="UTC").timestamp() * 1000); L1 = int(pd.Timestamp(hi, tz="UTC").timestamp() * 1000)
    m = (ts >= L0) & (ts <= L1)
    idx = np.flatnonzero(m)
    print(f"== {label} [{lo[11:19]}..{hi[11:19]}] ticks={len(idx)}")
    if len(idx) == 0:
        return
    for k in list(idx[:12]) + list(idx[-12:]):
        print("   ", pd.Timestamp(int(ts[k]), unit="ms", tz="UTC").strftime("%H:%M:%S.%f")[:12], b[k], a[k])

dump("2026-10-01T14:32:45+00:00", "2026-10-01T14:34:15+00:00", "window A start (labels)")
dump("2026-10-01T14:38:45+00:00", "2026-10-01T14:40:00+00:00", "window A end (labels)")
dump("2026-10-01T17:32:45+00:00", "2026-10-01T17:34:15+00:00", "window B start (labels)")
dump("2026-10-01T17:38:45+00:00", "2026-10-01T17:40:00+00:00", "window B end (labels)")

# price histogram: where do ticks with bid in [4164.90, 4165.05] sit?
m = (b >= 4164.90) & (b <= 4165.05)
idx = np.flatnonzero(m)
hours = {}
for k in idx:
    hh = pd.Timestamp(int(ts[k]), unit="ms", tz="UTC").strftime("%m-%d %H")
    hours[hh] = hours.get(hh, 0) + 1
print("bid in [4164.90,4165.05]:", sorted(hours.items()))
# where does ask cross 4174.09 (SL for short)?
m2 = (a >= 4174.09) & (a <= 4174.15)
idx2 = np.flatnonzero(m2)
hours2 = {}
for k in idx2:
    hh = pd.Timestamp(int(ts[k]), unit="ms", tz="UTC").strftime("%m-%d %H")
    hours2[hh] = hours2.get(hh, 0) + 1
print("ask in [4174.09,4174.15]:", sorted(hours2.items()))
