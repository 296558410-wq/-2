# -*- coding: utf-8 -*-
"""phase4_stage3.py — session 条件化微观假设正式检验（冻结 10 项，OOS+perm+BH）。

来自 stage2 分层的可检验假说（session 内符号相反 → 需 session 内 OOS 检验）：
  1 asia:   imb_r30 → fwd15 (+)
  2 asia:   imb_r30 → fwd30 (+)
  3 asia:   imb_r120 → fwd60 (−)
  4 london: imb_r120 → fwd60 (+)
  5 overlap:imb_r120 → fwd60 (+)
  6 overlap:imb_r30 → fwd30 (+)
  7 ny:     z_tick_count_120 → fwd30 (+)
  8 ny:     z_tick_count_120 → fwd60 (+)
  9 ny:     spread → fwd10 (−)
  10 ny:    spread → fwd15 (−)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
from research_engine.core.dataquality import session_of
from research_engine.statistics.multiple_testing import benjamini_hochberg

STAGE = Path("C:/AIQuant/data/staging_fxtm")
FROZEN = [
    ("asia", "tick_imb_r30", 15, "+"), ("asia", "tick_imb_r30", 30, "+"),
    ("asia", "tick_imb_r120", 60, "-"),
    ("london", "tick_imb_r120", 60, "+"),
    ("london_ny_overlap", "tick_imb_r120", 60, "+"),
    ("london_ny_overlap", "tick_imb_r30", 30, "+"),
    ("ny", "z_tick_count_120", 30, "+"), ("ny", "z_tick_count_120", 60, "+"),
    ("ny", "spread", 10, "-"), ("ny", "spread", 15, "-"),
]

X = pd.read_parquet(STAGE / "micro_m1_features.parquet")
Y = pd.read_parquet(STAGE / "micro_m1_labels.parquet")
X.index = Y.index = pd.DatetimeIndex(X.index)
sess = session_of(Y.index)


def perm_p_within(x, y, n_iter=800, seed=5, train_frac=0.6):
    m = pd.concat([x, y], axis=1).dropna()
    cut = int(len(m) * train_frac)
    xt, yt = m.iloc[cut:, 0].values, m.iloc[cut:, 1].values
    obs = float(spearmanr(xt, yt).statistic)
    rng = np.random.default_rng(seed)
    dist = np.empty(n_iter)
    for i in range(n_iter):
        dist[i] = float(spearmanr(xt, rng.permutation(yt)).statistic)
    return {"ic_oos": obs, "p": float((np.abs(dist) >= abs(obs)).mean()), "oos_n": len(xt)}


res = []
for seg, feat, h, exp_dir in FROZEN:
    mask = sess.values == seg
    f = X.loc[mask, feat]
    lab = Y.loc[mask, f"fwd_{h}"]
    pr = perm_p_within(f, lab)
    # 期望方向一致？
    sign_ok = (exp_dir == "+" and pr["ic_oos"] > 0) or (exp_dir == "-" and pr["ic_oos"] < 0)
    res.append({"session": seg, "feature": feat, "h": h, "expected": exp_dir,
                "ic_oos": round(pr["ic_oos"], 5), "p": pr["p"], "oos_n": pr["oos_n"],
                "sign_ok": sign_ok})

pvals = np.array([r["p"] for r in res])
bh = benjamini_hochberg(pvals, alpha=0.05)
for r, q, rej in zip(res, bh["q_values"], bh["reject"]):
    r["q"] = float(q)
    r["fdr"] = bool(rej)
json.dump({"frozen": FROZEN, "results": res,
           "bh": {"n_raw": int((pvals < 0.05).sum()), "n_reject": int(bh["n_reject"])}},
          open("C:/AIQuant/reports/phase4_stage3_session.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
for r in res:
    print("%-17s %-16s h=%-3d ic=%8.4f p=%7.4f q=%7.4f sign_ok=%s fdr=%s" %
          (r["session"], r["feature"], r["h"], r["ic_oos"], r["p"], r["q"], r["sign_ok"], r["fdr"]))
