# -*- coding: utf-8 -*-
"""phase3_spread_round.py — spread 信息层快速漏斗（R3 子集），DUKA 与 FXTM 双源交叉。

假设：spread 状态（流动性代理）→ 未来波动（+）与条件收益（- 高 spread 后走弱?）
全部走 OOS perm + 全局 BH。
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from alpha_engine.filters import oos_permutation_p, bootstrap_ci_ic
from research_engine.core import data_registry
from research_engine.statistics.multiple_testing import benjamini_hochberg

FEEDS = ["XAUUSD_M1_Dukascopy-HTTP_20260904_v001", "XAUUSD_M1_MT5-FXTM-Live_20260904_v001"]
HYP = [  # (feature, label_kind, holding, direction)
    ("spread", "vol", 15, "+"), ("spread", "vol", 60, "+"), ("spread", "vol", 240, "+"),
    ("spread", "ret", 15, "-"), ("spread", "ret", 60, "-"),
    ("spread_z", "ret", 60, "-"), ("spread_z", "vol", 60, "+"),
]


def zscore(s, w=480):
    mu = s.rolling(w).mean()
    sd = s.rolling(w).std(ddof=1)
    return ((s - mu) / sd)


def run_feed(ds_id):
    df, meta = data_registry.load_dataset(ds_id)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    close = df["close"]
    sp = df["spread"]
    # spread 相对波动归一：spread/close（bp）
    sp_bp = sp / close * 1e4
    r = close.pct_change()
    out = []
    for (feat, kind, h, direction) in HYP:
        if kind == "vol":
            label = r.rolling(h).std(ddof=1).shift(-h)
        else:
            label = close.shift(-h) / close - 1.0
        if feat == "spread":
            f = sp_bp
        else:
            f = zscore(sp_bp)
        m = pd.concat([f, label], axis=1).dropna()
        n = len(m)
        cut = int(n * 0.6)
        perm = oos_permutation_p(m.iloc[:, 0], m.iloc[:, 1], n_iter=800, seed=3)
        boot = bootstrap_ci_ic(m.iloc[cut:, 0], m.iloc[cut:, 1], n_iter=300, seed=5)
        out.append({"hyp": f"{feat}_h{h}_{kind}", "ic": perm["ic_oos"], "p": perm["p_value"],
                    "backend": perm["backend"], "ci": boot["ci95"]})
    return out


results = {}
for ds in FEEDS:
    results[ds] = run_feed(ds)
    p = np.array([r["p"] for r in results[ds]])
    bh = benjamini_hochberg(p, alpha=0.05)
    for r, q, rej in zip(results[ds], bh["q_values"], bh["reject"]):
        r["q"] = float(q)
        r["fdr"] = bool(rej)

rep = {"feed1": FEEDS[0], "feed2": FEEDS[1], "results": results}
json.dump(rep, open("C:/AIQuant/reports/phase3_spread_info.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
for ds in FEEDS:
    print("==", ds)
    for r in results[ds]:
        print("  %-20s ic=%8.4f p=%6.4f q=%6.4f fdr=%s ci=[%.4f, %.4f]" %
              (r["hyp"], r["ic"], r["p"], r["q"], r["fdr"], r["ci"][0], r["ci"][1]))
