# -*- coding: utf-8 -*-
"""phase6_transitions.py — 状态转换的可预测性（FXTM 2026，非重叠）。

目标：从 t 时已知特征预测 “未来 30m 内进入高波动/压力态(S4∪S5)”：
特征候选（冻结 6 个，OOS AUC + 单侧置换 p + BH）：
  spread_z 变化 / activity 变化(log) / vol_ratio(5/30) / |mom30| / rvol 分位 / tick 失衡(仅 tick 窗)
训练：前 60% 样本；评估：OOS 非重叠 30m 块。
"""
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.statistics.multiple_testing import benjamini_hochberg

df, _ = data_registry.load_dataset("XAUUSD_M1_MT5-FXTM-Live_20260904_v001")
df = df.sort_values("ts_utc").reset_index(drop=True)
n = len(df)
close = df["close"]
r = close.pct_change()
rvol30 = r.rolling(30).std(ddof=1)
rvol5 = r.rolling(5).std(ddof=1)
act = df["tick_volume"].rolling(30).sum()
sp = df["spread"]
sp_z = (sp - sp.rolling(480).mean()) / (sp.rolling(480).std(ddof=1) + 1e-12)
vol_ratio = rvol5 / rvol30
mom30 = close / close.shift(30) - 1.0

# 压力态标签（来自 phase6_states FXTM 输出：S4/S5 = rvol 最高两档）
# 直接用 vol 阈值定义（可比、可迁移）：rvol30 > p85(历史滚动窗) → 压力/扩张
stress = (rvol30 > rvol30.rolling(480).quantile(0.85)).astype(float)

feats = {
    "spread_z_chg": sp_z.diff(15),
    "log_act_chg": np.log(act + 1).diff(15),
    "vol_ratio_5_30": vol_ratio,
    "abs_mom30": np.abs(mom30),
    "rvol_pct": rvol30.rank(pct=True),
}
X = pd.DataFrame(feats).iloc[480:].reset_index(drop=True)
y_future = pd.Series(stress.values).iloc[480:]
# 未来 30m 内是否进入压力（非重叠前瞻窗判定）
y = y_future.rolling(30).max().shift(-30)
m = pd.concat([X, y.rename("y")], axis=1).dropna()
cut = int(len(m) * 0.6)
mtrain, mtest = m.iloc[:cut], m.iloc[cut:]
# 非重叠抽样（30m 块）用于统计
idx = np.arange(0, len(mtest), 30)
mt = mtest.iloc[idx]

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

res = []
for c in X.columns:
    x_tr = mtrain[c].values.reshape(-1, 1)
    y_tr = mtrain["y"].values
    clf = LogisticRegression(max_iter=500)
    clf.fit(x_tr, y_tr)
    x_te = mt[c].values.reshape(-1, 1)
    y_te = mt["y"].values
    auc = roc_auc_score(y_te, clf.predict_proba(x_te)[:, 1])
    # 单侧置换 p（打乱标签）
    obs = auc
    rng = np.random.default_rng(5)
    dist = np.empty(500)
    for i in range(500):
        yp = rng.permutation(y_te)
        if yp.sum() in (0, len(yp)):
            dist[i] = 0.5
        else:
            dist[i] = roc_auc_score(yp, clf.predict_proba(x_te)[:, 1])
    p_val = float((dist >= obs).mean())
    res.append({"feature": c, "auc_oos": round(auc, 4), "p_perm": round(p_val, 4),
                "n_oos_blocks": int(len(mt)), "base_rate": round(float(y_te.mean()), 3)})
pvals = np.array([x["p_perm"] for x in res])
bh = benjamini_hochberg(pvals, alpha=0.1)
for x, q, rej in zip(res, bh["q_values"], bh["reject"]):
    x["q"] = round(float(q), 4)
    x["bh_reject_01"] = bool(rej)
for x in res:
    print(x)
json.dump(res, open("C:/AIQuant/reports/phase6_transition_pred.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("transition pred done")
