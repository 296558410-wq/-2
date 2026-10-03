# -*- coding: utf-8 -*-
"""V3 Phase-2 R1 — sub-segment audit (item 9).

Splits the SAME frozen events into disjoint sub-segments and re-reports the MID markout,
so "one lucky pocket" vs "stable" is visible. No re-tuning, no threshold change.

Segments: (a) session by UTC hour  (b) trailing-liquidity tercile by trailing spread.
"""
from __future__ import annotations
import json
import os
import numpy as np

import run_r1 as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "results_r1.json")
COST = 0.914
HS = [1000, 5000]


def sessions(ts):
    h = ((ts // 3_600_000) % 24)
    out = np.full(len(ts), "OTHER", dtype=object)
    out[(h >= 0) & (h < 7)] = "ASIA_00-07Z"
    out[(h >= 7) & (h < 12)] = "LONDON_07-12Z"
    out[(h >= 12) & (h < 21)] = "NY_12-21Z"
    return out


def main():
    df, man = R.load_ticks()
    ts = df["ts_ms"].to_numpy(np.int64)
    bid = df["bid"].to_numpy(np.float64)
    ask = df["ask"].to_numpy(np.float64)
    mid = (bid + ask) / 2.0
    seg = R.segment_ids(ts)
    dmid = np.diff(mid, prepend=np.nan)
    sgn = np.sign(np.nan_to_num(dmid))
    spread_bp = (ask - bid) / mid * 1e4
    sess = sessions(ts)

    ret100 = R.seg_rolling_sum(dmid, seg, 100)
    ret500 = R.seg_rolling_sum(dmid, seg, 500)
    sd3000 = np.sqrt(np.maximum(R.seg_rolling_sum(dmid ** 2, seg, 3000) / np.maximum(R.seg_rolling_cnt(seg, 3000), 1), 1e-18))
    z500 = ret500 / (sd3000 * np.sqrt(500) + 1e-18)
    ti100 = R.seg_rolling_sum(sgn, seg, 100) / np.sqrt(np.maximum(R.seg_rolling_cnt(seg, 100), 1))
    thr_sp = R.causal_quantile_grid(spread_bp, seg, 0.67)
    rate = (np.arange(len(ts)) - np.searchsorted(ts, ts - 5000, side="left") + 1) / 5.0
    thr_rate = R.causal_quantile_grid(rate, seg, 0.90)

    evA1 = np.flatnonzero(R.onset(np.abs(ti100) >= 2.0))
    evA2 = np.flatnonzero(R.onset(np.abs(z500) >= 2.0))
    evC1 = np.flatnonzero(R.onset(spread_bp >= np.nan_to_num(thr_sp, nan=np.inf)) & (np.abs(ret100) > 0))
    evC2 = np.flatnonzero(R.onset(rate >= np.nan_to_num(thr_rate, nan=np.inf)) & (np.abs(ret100) > 0))

    specs = [
        ("A1_CONT", evA1, np.where(ti100[evA1] >= 0, 1, -1)),
        ("A1_REV", evA1, np.where(ti100[evA1] >= 0, -1, 1)),
        ("A2_CONT", evA2, np.sign(np.nan_to_num(ret500[evA2])).astype(int)),
        ("A2_REV", evA2, (-np.sign(np.nan_to_num(ret500[evA2]))).astype(int)),
        ("C1_MR", evC1, (-np.sign(np.nan_to_num(ret100[evC1]))).astype(int)),
        ("C2_CONT", evC2, np.sign(np.nan_to_num(ret100[evC2])).astype(int)),
    ]

    def markout(ev, d, h):
        e = ev + 1
        ok = e < len(ts)
        e, d = e[ok], d[ok]
        j = np.searchsorted(ts, ts[e] + h, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[e])
        ei, ji = e[v], np.minimum(j, len(ts) - 1)[v]
        return ei, d[v] * (mid[ji] - mid[ei]) / mid[ei] * 1e4

    out = {"cost_bp": COST, "by_session": {}, "by_liquidity_tercile": {}}
    sp_med = spread_bp
    terc = np.full(len(ts), "", dtype=object)
    q33 = np.nanpercentile(spread_bp, 33)
    q67 = np.nanpercentile(spread_bp, 67)
    terc[sp_med <= q33] = "TIGHT"
    terc[(sp_med > q33) & (sp_med < q67)] = "MID"
    terc[sp_med >= q67] = "WIDE"

    for tag, ev, d in specs:
        out["by_session"][tag] = {}
        out["by_liquidity_tercile"][tag] = {}
        for h in HS:
            ei, g = markout(ev, d, h)
            for name in ["ASIA_00-07Z", "LONDON_07-12Z", "NY_12-21Z"]:
                m = sess[ei] == name
                if m.sum() >= 20:
                    out["by_session"][tag][f"{h}|{name}"] = {
                        "n": int(m.sum()), "mid_mean_bp": float(np.mean(g[m])),
                        "net1x_bp": float(np.mean(g[m]) - COST),
                        "pos_frac": float(np.mean(g[m] > 0))}
            for name in ["TIGHT", "MID", "WIDE"]:
                m = terc[ei] == name
                if m.sum() >= 20:
                    out["by_liquidity_tercile"][tag][f"{h}|{name}"] = {
                        "n": int(m.sum()), "mid_mean_bp": float(np.mean(g[m])),
                        "net1x_bp": float(np.mean(g[m]) - COST),
                        "pos_frac": float(np.mean(g[m] > 0))}

    res = json.load(open(OUT_JSON, encoding="utf-8"))
    res["subsegment_audit"] = out
    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("=== by session (mid mean bp) ===")
    for tag in [s[0] for s in specs]:
        row = out["by_session"][tag]
        print(f"{tag:9s} " + " ".join(f"{k}={v['mid_mean_bp']:+.3f}(n={v['n']})" for k, v in row.items()))
    print("=== by liquidity tercile (mid mean bp) ===")
    for tag in [s[0] for s in specs]:
        row = out["by_liquidity_tercile"][tag]
        print(f"{tag:9s} " + " ".join(f"{k}={v['mid_mean_bp']:+.3f}(n={v['n']})" for k, v in row.items()))
    print("merged subsegment_audit into", OUT_JSON)


if __name__ == "__main__":
    main()
