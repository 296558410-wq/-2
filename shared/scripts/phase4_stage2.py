# -*- coding: utf-8 -*-
"""phase4_stage2.py — 微观方向候选的正式检验（预登记短名单，来自 Stage1 筛选矩阵）。

FROZEN 12 测试（screening 后登记，一次性 BH）：
  spread→fwd{1,5,10,15}; imb_r30→fwd{15,30,60}; imb_r120→fwd{60};
  z_tick_count_120→fwd{30,60}; z_impact_120→fwd{60}; flow_persist→fwd{15}
之后：session / vol-regime / spread-regime 分层；FDR 幸存者 → 动态成本（真实半价差+滑点）+ 延迟敏感性。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
from research_engine.core.dataquality import session_of
from alpha_engine.filters import oos_permutation_p, bootstrap_ci_ic
from research_engine.statistics.multiple_testing import benjamini_hochberg

STAGE = Path("C:/AIQuant/data/staging_fxtm")
FROZEN = [
    ("spread", 1), ("spread", 5), ("spread", 10), ("spread", 15),
    ("tick_imb_r30", 15), ("tick_imb_r30", 30), ("tick_imb_r30", 60),
    ("tick_imb_r120", 60),
    ("z_tick_count_120", 30), ("z_tick_count_120", 60),
    ("z_impact_120", 60), ("flow_persist", 15),
]

X = pd.read_parquet(STAGE / "micro_m1_features.parquet")
Y = pd.read_parquet(STAGE / "micro_m1_labels.parquet")
ts = pd.to_datetime(Y.index) if not isinstance(Y.index, pd.DatetimeIndex) else Y.index
X.index = Y.index = ts

# 分层变量
sess = session_of(Y.index)
rvol30 = Y["rvol30_now"]
spread_now = Y["spread_now"]
vol_q = pd.qcut(rvol30.rank(method="first"), 3, labels=["low", "mid", "high"])
sp_q = pd.qcut(spread_now.rank(method="first"), 3, labels=["tight", "mid", "wide"])

results = []
for feat, h in FROZEN:
    f = X[feat]
    lab = Y[f"fwd_{h}"]
    m = pd.concat([f, lab], axis=1).dropna()
    cut = int(len(m) * 0.6)
    perm = oos_permutation_p(f, lab, n_iter=800, seed=11)
    boot = bootstrap_ci_ic(m.iloc[cut:, 0], m.iloc[cut:, 1], n_iter=400, seed=13)
    # 分层（全样本条件 IC）
    cond = {}
    for seg in ("asia", "london", "ny", "london_ny_overlap"):
        mask = sess.reindex(m.index).values == seg
        mm = m[mask]
        cond[f"ic_{seg}"] = round(float(spearmanr(mm.iloc[:, 0], mm.iloc[:, 1]).statistic), 4) if len(mm) > 500 else None
    for qname, qser in (("vol", vol_q), ("spread", sp_q)):
        qq = qser.reindex(m.index)
        for level in ("low", "mid", "high", "tight", "mid", "wide"):
            if (qname == "vol" and level not in ("low", "mid", "high")) or (qname == "spread" and level not in ("tight", "mid", "wide")):
                continue
            mm = m[qq.values == level]
            cond[f"ic_{qname}_{level}"] = round(float(spearmanr(mm.iloc[:, 0], mm.iloc[:, 1]).statistic), 4) if len(mm) > 500 else None
    results.append({"feature": feat, "h": h, "ic_oos": perm["ic_oos"], "p": perm["p_value"],
                    "backend": perm["backend"], "ci": boot["ci95"], "cond": cond})

pvals = np.array([r["p"] for r in results])
bh = benjamini_hochberg(pvals, alpha=0.05)
for r, q, rej in zip(results, bh["q_values"], bh["reject"]):
    r["q"] = float(q)
    r["fdr"] = bool(rej)

rep = {"frozen_n": len(FROZEN), "results": results, "bh": {"n_reject": bh["n_reject"],
       "n_raw": int((pvals < 0.05).sum())}}
json.dump(rep, open("C:/AIQuant/reports/phase4_stage2_frozen.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
for r in results:
    print("%-16s h=%-3d ic=%8.4f p=%8.5f q=%8.5f fdr=%s" % (r["feature"], r["h"], r["ic_oos"], r["p"], r["q"], r["fdr"]))
    print("    cond:", {k: v for k, v in r["cond"].items() if v is not None})
