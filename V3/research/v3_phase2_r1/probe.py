# -*- coding: utf-8 -*-
"""Probe: compute causal features on the frozen snapshot and report event counts.
Read-only. No orders."""
import glob, os, json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_r1 import load_ticks, segment_ids, seg_rolling_sum, seg_rolling_cnt, causal_quantile_grid, onset

df, man, _ = load_ticks()
ts = df["ts_ms"].to_numpy(np.int64)
bid = df["bid"].to_numpy(np.float64)
ask = df["ask"].to_numpy(np.float64)
mid = (bid + ask) / 2.0
seg = segment_ids(ts)
print("rows", len(ts), "segments", int(seg[-1]) + 1, "span", pd.to_datetime(ts[0], unit="ms", utc=True), "->", pd.to_datetime(ts[-1], unit="ms", utc=True))

dmid = np.diff(mid, prepend=np.nan)
sgn = np.sign(np.nan_to_num(dmid))
spread_bp = (ask - bid) / mid * 1e4
ti100 = seg_rolling_sum(sgn, seg, 100) / np.sqrt(np.maximum(seg_rolling_cnt(seg, 100), 1))
ret100 = seg_rolling_sum(dmid, seg, 100)
ret500 = seg_rolling_sum(dmid, seg, 500)
sd3000 = np.sqrt(np.maximum(seg_rolling_sum(dmid ** 2, seg, 3000) / np.maximum(seg_rolling_cnt(seg, 3000), 1), 1e-18))
z500 = ret500 / (sd3000 * np.sqrt(500) + 1e-18)
mp_pos = np.where((ask - bid) > 0, (mid - bid) / (ask - bid), 0.5)
rv500 = np.sqrt(seg_rolling_sum(dmid ** 2, seg, 500) / np.maximum(seg_rolling_cnt(seg, 500), 1))
thr_spread67 = causal_quantile_grid(spread_bp, seg, 0.67)
thr_rv67 = causal_quantile_grid(rv500, seg, 0.67)
j0 = np.searchsorted(ts, ts - 5000, side="left")
idx = np.arange(len(ts))
rate = (idx - j0 + 1) / 5.0
thr_rate90 = causal_quantile_grid(rate, seg, 0.90)

print("spread_bp median", np.nanmedian(spread_bp), "p90", np.nanpercentile(spread_bp,90))
print("z500 |z|>=2 frac", float(np.mean(np.abs(z500)>=2.0)))
print("ti100 |z|>=2 frac", float(np.mean(np.abs(ti100)>=2.0)))
print("mp extreme frac", float(np.mean((mp_pos>=0.7)|(mp_pos<=0.3))))

evA1 = np.flatnonzero(onset(np.abs(ti100) >= 2.0))
evA2 = np.flatnonzero(onset(np.abs(z500) >= 2.0))
wide = spread_bp >= np.nan_to_num(thr_spread67, nan=np.inf)
evC1 = np.flatnonzero(onset(wide) & (np.abs(ret100) > 0))
burst = rate >= np.nan_to_num(thr_rate90, nan=np.inf)
evC2 = np.flatnonzero(onset(burst) & (np.abs(ret100) > 0))
ext = (mp_pos >= 0.70) | (mp_pos <= 0.30)
evB1 = np.flatnonzero(onset(ext))
highrv = rv500 >= np.nan_to_num(thr_rv67, nan=np.inf)
evF1 = np.flatnonzero(onset(highrv))
print("counts A1=%d A2=%d C1=%d C2=%d B1=%d F1=%d" % (len(evA1), len(evA2), len(evC1), len(evC2), len(evB1), len(evF1)))

# quick gross check at 1000ms for A2 both directions
def quick(ev, direction, h=1000):
    e = ev + 1
    ok = (e < len(ts))
    e = e[ok]
    j = np.searchsorted(ts, ts[e] + h, side="left")
    v = (j < len(ts)) & (seg[np.minimum(j, len(ts)-1)] == seg[e])
    ei, ji = e[v], np.minimum(j, len(ts)-1)[v]
    m = mid[ji]
    if direction > 0:
        g = (m - ask[ei]) / mid[ei] * 1e4
    else:
        g = (bid[ei] - m) / mid[ei] * 1e4
    return len(g), float(np.mean(g)), float(np.median(g)), float(np.mean(g) > 0)

print("A2 cont 1000ms", quick(evA2, +1))
print("A2 rev  1000ms", quick(evA2, -1))
print("A1 cont 1000ms", quick(evA1, +1))
print("A1 rev  1000ms", quick(evA1, -1))
