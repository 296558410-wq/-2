# -*- coding: utf-8 -*-
"""Locate convention break points in the tick archive + verify with raw rows. Read-only."""
import os
import numpy as np
import pandas as pd

TICKS = r"C:\AIQuant\data\live_fxtm"
files = sorted(f for f in os.listdir(TICKS) if f.startswith("ticks_"))

print("=== backward/forward jumps > 10 min (per file) ===")
for fn in files:
    t = pd.read_parquet(os.path.join(TICKS, fn), columns=["ts_utc", "bid", "ask"])
    ts = t["ts_utc"].astype("int64").to_numpy()
    o = np.argsort(ts, kind="mergesort")
    ts_sorted = ts[o]
    d = np.diff(ts_sorted)
    big_fwd = np.flatnonzero(d > 600_000)
    # backward jumps need original order scan (sorting destroys them): scan raw order
    d_raw = np.diff(ts)
    back = np.flatnonzero(d_raw < -600_000)
    if len(big_fwd) or len(back):
        print(fn, "sorted_fwd>10m:", len(big_fwd), "| raw_backward>10m:", len(back))
        for i in back[:6]:
            print("   BACKWARD at row", i, ":", pd.Timestamp(int(ts[i]), unit="ms", tz="UTC"),
                  "->", pd.Timestamp(int(ts[i + 1]), unit="ms", tz="UTC"),
                  "| prices", t["bid"].iloc[i], "->", t["bid"].iloc[i + 1])
        for i in big_fwd[:4]:
            print("   fwd gap:", pd.Timestamp(int(ts_sorted[i]), unit="ms", tz="UTC"), "->",
                  pd.Timestamp(int(ts_sorted[i + 1]), unit="ms", tz="UTC"))
    if fn == "ticks_20261002.parquet":
        print("   [raw order check first/last]", pd.Timestamp(int(ts[0]), unit="ms", tz="UTC"),
              "->", pd.Timestamp(int(ts[-1]), unit="ms", tz="UTC"), "| rows", len(ts))
        # is raw order monotonic?
        print("   raw monotonic (allow tiny): ", bool((d_raw >= -1000).all()), "| n_back(any):", int((d_raw < 0).sum()))

# raw rows: anchor windows
t2 = pd.read_parquet(os.path.join(TICKS, "ticks_20261001.parquet"), columns=["ts_utc", "bid", "ask"])
ts2 = t2["ts_utc"].astype("int64").to_numpy(); o2 = np.argsort(ts2); ts2 = ts2[o2]
b2 = t2["bid"].to_numpy()[o2]; a2 = t2["ask"].to_numpy()[o2]
def window(ts, b, a, lo, hi):
    L0 = int(pd.Timestamp(lo, tz="UTC").timestamp() * 1000); L1 = int(pd.Timestamp(hi, tz="UTC").timestamp() * 1000)
    m = (ts >= L0) & (ts <= L1)
    return m, b[m], a[m]
print()
print("=== 10-01 file, labels 17:33-17:40 (under +3h theory = true 14:33-14:40, trade 2378322488) ===")
m, b, a = window(ts2, b2, a2, "2026-10-01T17:33:00+00:00", "2026-10-01T17:40:00+00:00")
print("ticks:", int(m.sum()), "| bid range:", round(b.min(), 2), round(b.max(), 2), "| ask max:", round(a.max(), 2))
print("=== same file labels 14:33-14:40 (old wrong window) ===")
m, b, a = window(ts2, b2, a2, "2026-10-01T14:33:00+00:00", "2026-10-01T14:40:00+00:00")
print("ticks:", int(m.sum()), "| bid range:", round(b.min(), 2), round(b.max(), 2))

print()
print("=== 09-30 file labels 14:15-14:30 (under +3h = true 11:15-11:30, trade 2378067697) ===")
t3 = pd.read_parquet(os.path.join(TICKS, "ticks_20260930.parquet"), columns=["ts_utc", "bid", "ask"])
ts3 = t3["ts_utc"].astype("int64").to_numpy(); o3 = np.argsort(ts3); ts3 = ts3[o3]
b3 = t3["bid"].to_numpy()[o3]; a3 = t3["ask"].to_numpy()[o3]
m, b, a = window(ts3, b3, a3, "2026-09-30T14:15:00+00:00", "2026-09-30T14:30:00+00:00")
print("ticks:", int(m.sum()), "| bid range:", round(b.min(), 2), round(b.max(), 2), "| ask range:", round(a.min(), 2), round(a.max(), 2))
