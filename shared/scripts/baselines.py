# -*- coding: utf-8 -*-
"""baselines.py — Phase 2 §19：候选必须与之比较的 4 类 baseline。

1) Random baseline：20 个随机特征走同一 OOS-permutation 漏斗 → 显著比例（null 参照）
2) Buy/Hold：M1 全时段持多（净收益，含成本近似 0 换手）
3) Momentum baseline：mom_60 符号策略（1x 成本）
4) Mean Reversion baseline：zscore_60 符号策略（1x 成本）
输出 reports/round1_baselines.json
"""
import json
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
from alpha_engine.filters import oos_permutation_p
from alpha_engine.generator import _needed_base, build_matrix, add_labels
from alpha_engine.pipeline import M1_DATASET, XAUUSD_COST
from research_engine.core import data_registry
from research_engine.core.backtest import BacktestEngine
from research_engine.core.cost import CostModel
from research_engine.features.xauusd import CATALOG
from research_engine.core.feature import FeatureSpec, build as bf

OUT = "C:/AIQuant/reports/round1_baselines.json"

df, meta = data_registry.load_dataset(M1_DATASET)
df = df.sort_values("ts_utc").reset_index(drop=True)
n = len(df)
close = df.set_index("ts_utc")["close"]
r = close.pct_change().fillna(0.0).values

cm = CostModel(**XAUUSD_COST)
bt = BacktestEngine(cost_model=cm)


def bt_sharpe_note(pos, label):
    res = bt.run(close, pd.Series(pos, index=close.index), name=label)
    m = res.metrics
    return {"label": label, "net_total": m["net_total_return"], "sharpe": m["sharpe_annualized"],
            "max_dd": m["max_drawdown"], "trades": m["n_trades"], "cost": m["cost_total"]}


out = {"dataset": M1_DATASET, "range": [str(close.index[0]), str(close.index[-1])],
       "cost": XAUUSD_COST, "generated": datetime.now(timezone.utc).isoformat()}

# ---- 1) Random baseline（perm 漏斗，null 参照） ----
rng = np.random.default_rng(123)
y = add_labels(df).reset_index(drop=True)
X = build_matrix(df)[0].reset_index(drop=True)
drop = n - len(X)
y = y.iloc[drop:].reset_index(drop=True)
t0 = time.perf_counter()
rand_rows = []
lab = y["forward_return_60m"]
for i in range(20):
    fr = pd.Series(rng.standard_normal(len(X)))
    pr = oos_permutation_p(fr, lab, n_iter=500, seed=1000 + i, backend="auto")
    rand_rows.append({"feat": f"rand_{i}", "p": pr["p_value"], "ic": pr["ic_oos"],
                      "backend": pr["backend"]})
pvals = np.array([x["p"] for x in rand_rows])
out["random_baseline"] = {
    "n": len(rand_rows),
    "raw_sig_at_05": int((pvals < 0.05).sum()),
    "median_p": float(np.median(pvals)),
    "max_abs_ic": float(np.max(np.abs([x["ic"] for x in rand_rows]))),
    "elapsed_s": round(time.perf_counter() - t0, 1),
    "backend_used": sorted({x["backend"] for x in rand_rows}),
}

# ---- 2/3/4) 策略 baseline ----
pos_bh = pd.Series(1.0, index=close.index)
out["buy_hold"] = bt_sharpe_note(pos_bh, "buy_hold")

specs = [FeatureSpec("mom_60", CATALOG["mom_60"][0], CATALOG["mom_60"][1]),
         FeatureSpec("zscore_60", CATALOG["zscore_60"][0], CATALOG["zscore_60"][1])]
fm = bf(df, specs).drop_warmup().X
pos_mom = np.sign(fm["mom_60"]).reindex(close.index).fillna(0.0)
out["momentum_baseline_mom60"] = bt_sharpe_note(pos_mom, "mom60_sign")
pos_mr = np.sign(fm["zscore_60"]).reindex(close.index).fillna(0.0)
out["meanrev_baseline_z60"] = bt_sharpe_note(pos_mr, "zscore60_sign")

json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:1500])
