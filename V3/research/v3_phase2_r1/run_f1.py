# -*- coding: utf-8 -*-
"""V3 Phase-2 R1 — F1 non-directional evaluator (magnitude/path, no direction).

Metric (frozen intent): does a HIGH-RV regime onset predict that the forward ABSOLUTE
mid move exceeds the cost anchor, better than the unconditional baseline?
Verdict vocabulary for a non-directional prediction: PREDICTIVE / NOT_PREDICTIVE,
and it can never be CANDIDATE (no direction => not executable as a bet).

Merges its result into results_r1.json (does not touch the frozen protocol).
"""
from __future__ import annotations
import json
import os
import numpy as np

import run_r1 as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "results_r1.json")
COST_BP = 0.914
HORIZONS = [100, 250, 500, 1000, 2000, 5000]


def main():
    df, man = R.load_ticks()
    ts = df["ts_ms"].to_numpy(np.int64)
    bid = df["bid"].to_numpy(np.float64)
    ask = df["ask"].to_numpy(np.float64)
    mid = (bid + ask) / 2.0
    seg = R.segment_ids(ts)
    dmid = np.diff(mid, prepend=np.nan)
    rv500 = np.sqrt(R.seg_rolling_sum(dmid ** 2, seg, 500) / np.maximum(R.seg_rolling_cnt(seg, 500), 1))
    thr = R.causal_quantile_grid(rv500, seg, 0.67)
    high = rv500 >= np.nan_to_num(thr, nan=np.inf)
    ev = np.flatnonzero(R.onset(high))
    # baseline control: every 50th tick (deterministic, not a scan)
    base_idx = np.arange(0, len(ts), 50)
    print("F1 events:", len(ev), "baseline sample:", len(base_idx))

    out = {"events_raw": int(len(ev)), "baseline_n": int(len(base_idx)),
           "metric": "abs(mid move) bp at horizon", "cost_anchor_bp": COST_BP, "horizons": {}}

    for h in HORIZONS:
        def fwd(idx):
            e = idx + 1
            e = e[e < len(ts)]
            j = np.searchsorted(ts, ts[e] + h, side="left")
            v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[e])
            ei, ji = e[v], np.minimum(j, len(ts) - 1)[v]
            mv = np.abs(mid[ji] - mid[ei]) / mid[ei] * 1e4
            return ei, mv
        ei, mv = fwd(ev)
        bi, bmv = fwd(base_idx)
        if len(mv) < 10 or len(bmv) < 10:
            out["horizons"][str(h)] = {"n": int(len(mv)), "status": "INSUFFICIENT_SAMPLE"}
            continue
        hit = float(np.mean(mv > COST_BP))
        bhit = float(np.mean(bmv > COST_BP))
        # block bootstrap on the difference of hit rates
        rng = np.random.default_rng(R.SEED)
        diffs = []
        for _ in range(2000):
            a = mv[rng.integers(0, len(mv), len(mv))]
            b = bmv[rng.integers(0, len(bmv), len(bmv))]
            diffs.append(float(np.mean(a > COST_BP) - np.mean(b > COST_BP)))
        diffs = np.array(diffs)
        lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
        predictive = (lo > 0)
        out["horizons"][str(h)] = {
            "n": int(len(mv)), "censored_n": int(len(ev) - len(mv)),
            "mean_abs_move_bp": float(np.mean(mv)), "median_abs_move_bp": float(np.median(mv)),
            "baseline_mean_abs_move_bp": float(np.mean(bmv)),
            "p_gt_cost": hit, "baseline_p_gt_cost": bhit, "lift": hit - bhit,
            "boot_ci_lift": [lo, hi],
            "verdict": "PREDICTIVE_BUT_NOT_EXECUTABLE" if predictive else "NOT_PREDICTIVE",
        }
        print(f"h={h} mean|mv|={np.mean(mv):.3f}bp base={np.mean(bmv):.3f}bp lift_hit={hit-bhit:+.4f} CI=[{lo:.4f},{hi:.4f}]")

    res = json.load(open(OUT_JSON, encoding="utf-8"))
    res["hypotheses"]["F1_VOL_PERSIST"] = {
        "hypothesis_id": "F1_VOL_PERSIST", "family": "F_nondirectional", **out}
    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("merged F1 into", OUT_JSON)


if __name__ == "__main__":
    main()
