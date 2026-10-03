"""Diagnostics for the suspicious strong-positive result (task §三十).

Checks: timestamp order/duplication, quote sanity (stale/wide quotes), whether the
"edge" is produced by a purely MECHANICAL predictor (pred = -spread_bp/2), tail
concentration, and whether it survives excluding untradable stale quotes.

READ_ONLY. No orders.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from sklearn.linear_model import Ridge

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_edge_discovery as R  # noqa: E402

def main():
    ts, bid, ask, nf = R.load_snapshot()
    mid = (bid + ask) / 2.0
    gi = R.make_grid(ts)
    fo = R.folds_of(ts, gi)
    med_dt = float(np.median(np.diff(ts)))
    out = {"schema": "v3_l1_edge_diagnostics/1",
           "ticks": int(len(ts)), "grid": int(len(gi)),
           "ts_monotonic": bool(np.all(np.diff(ts) >= 0)),
           "ts_out_of_order": int((np.diff(ts) < 0).sum()),
           "ts_duplicates": int(len(ts) - len(np.unique(ts)))}

    feats = R.build_features(ts, bid, ask, gi)
    sb = feats["spread_bp"]
    out["spread_bp"] = {"median": float(np.median(sb)), "p90": float(np.percentile(sb, 90)),
                         "p99": float(np.percentile(sb, 99)), "p999": float(np.percentile(sb, 99.9)),
                         "max": float(np.max(sb)),
                         "count_gt_2bp": int((sb > 2).sum()), "count_gt_5bp": int((sb > 5).sum()),
                         "count_gt_20bp": int((sb > 20).sum())}

    h = 5000
    lab = R.labels_for(ts, mid, bid, ask, gi, h)
    rho = max(1.0, h / med_dt)
    purge = ((fo == "train") & (lab["fwd_day"] >= R.FOLDS["val"][0])) | \
            ((fo == "val") & (lab["fwd_day"] >= R.FOLDS["test"][0]))
    base = lab["elig"] & (~purge) & (fo != "none")
    X = np.column_stack([feats[c] for c in ["spread_bp", "spread_pctile_200t"]])
    good = base & np.isfinite(X).all(1) & np.isfinite(lab["long"])
    tr, va, te = good & (fo == "train"), good & (fo == "val"), good & (fo == "test")
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-12
    Z = (X - mu) / sd
    m = Ridge(alpha=1.0).fit(Z[tr], lab["long"][tr])

    def rule_net(pred, msk, spread_cap=None):
        cb = lab["cost_bp"][msk]
        pos = np.where(pred > cb, 1.0, np.where(pred < -cb, -1.0, 0.0))
        nz = pos != 0
        if spread_cap is not None:
            nz = nz & (feats["spread_bp"][msk] <= spread_cap)
        net = np.where(pos > 0, lab["long"][msk] - cb, lab["short"][msk] - cb)[nz]
        grs = np.where(pos > 0, lab["long"][msk], lab["short"][msk])[nz]
        return {"n_trades": int(net.size),
                "mean_bp": float(net.mean()) if net.size else None,
                "median_bp": float(np.median(net)) if net.size else None,
                "win_rate": float((net > 0).mean()) if net.size else None,
                "gross_mean_bp": float(grs.mean()) if grs.size else None,
                "tail": R.tail_shares(net)}

    pred_model = m.predict(Z[te])
    pred_mech = -(feats["spread_bp"][te]) / 2.0          # purely mechanical, uses NO future
    pred_zero = np.zeros(int(te.sum()))
    out["TEST_ridge_spread"] = rule_net(pred_model, te)
    out["TEST_mechanical_neg_half_spread"] = rule_net(pred_mech, te)
    out["TEST_zero_pred"] = rule_net(pred_zero, te)
    out["TEST_ridge_spread_excl_spread_gt_2bp"] = rule_net(pred_model, te, spread_cap=2.0)
    out["TEST_ridge_spread_excl_spread_gt_5bp"] = rule_net(pred_model, te, spread_cap=5.0)
    out["corr_pred_vs_spread_bp"] = float(np.corrcoef(pred_model, feats["spread_bp"][te])[0, 1])
    out["corr_pred_vs_actual_long_markout"] = float(
        np.corrcoef(pred_model, lab["long"][te][np.isfinite(lab["long"][te])])[0, 1]
        if np.isfinite(lab["long"][te]).sum() > 10 else float("nan"))
    # where does the money come from?
    cb = lab["cost_bp"][te]
    pos = np.where(pred_model > cb, 1.0, np.where(pred_model < -cb, -1.0, 0.0))
    nz = pos != 0
    sb_t = feats["spread_bp"][te][nz]
    out["trades_spread_profile"] = {"median_spread_bp": float(np.median(sb_t)) if sb_t.size else None,
                                     "share_spread_gt_2bp": float((sb_t > 2).mean()) if sb_t.size else None,
                                     "share_spread_gt_5bp": float((sb_t > 5).mean()) if sb_t.size else None,
                                     "share_spread_gt_20bp": float((sb_t > 20).mean()) if sb_t.size else None,
                                     "long_share": float((pos[nz] > 0).mean()) if nz.sum() else None}
    with open(os.path.join(HERE, "diagnostics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
