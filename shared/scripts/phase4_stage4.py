# -*- coding: utf-8 -*-
"""phase4_stage4.py — 幸存者按天稳定性 + 动态成本交易层。

7 个 FDR 幸存 session 规则：
  asia imb_r120→60(-) / london imb_r120→60(+) / overlap imb_r30→30(+)
  ny z_tick_count_120→30(+) / ny z_tick_count_120→60(+)
  ny spread→10(-) / ny spread→15(-)
按天 IC 稳定性（23 个交易日）；剔除最差 2 天再检验；随后动态成本回测
（每信号分钟真实 half-spread + slippage 0.1$，1 根延迟入场=已内建，2x/3x 成本压力）。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
from research_engine.core.dataquality import session_of

STAGE = Path("C:/AIQuant/data/staging_fxtm")
RULES = [
    ("asia", "tick_imb_r120", 60, -1), ("london", "tick_imb_r120", 60, 1),
    ("london_ny_overlap", "tick_imb_r30", 30, 1),
    ("ny", "z_tick_count_120", 30, 1), ("ny", "z_tick_count_120", 60, 1),
    ("ny", "spread", 10, -1), ("ny", "spread", 15, -1),
]

X = pd.read_parquet(STAGE / "micro_m1_features.parquet")
Y = pd.read_parquet(STAGE / "micro_m1_labels.parquet")
X.index = Y.index = pd.DatetimeIndex(X.index)
sess = session_of(Y.index)
day = Y.index.date
bars = pd.read_parquet(STAGE / "micro_m1_bars.parquet").set_index("ts_utc")
spread_usd = bars["spread_mean"].reindex(Y.index)
close = bars["mid_last"].reindex(Y.index)

out = {}
for seg, feat, h, sign in RULES:
    mask = (sess.values == seg)
    f = X.loc[mask, feat]
    lab = Y.loc[mask, f"fwd_{h}"]
    m = pd.concat([f, lab], axis=1).dropna()
    m["day"] = m.index.date
    # 按天 IC
    day_ics = {}
    for d, g in m.groupby("day"):
        if len(g) > 100:
            day_ics[str(d)] = float(spearmanr(g.iloc[:, 0], g.iloc[:, 1]).statistic)
    ic_arr = np.array(list(day_ics.values()))
    pos_frac = float((ic_arr * sign > 0).mean())
    # 剔最差 2 天
    worst2 = np.argsort(ic_arr * sign)[:2]
    keep = np.delete(ic_arr, worst2)
    pos_frac_drop2 = float((keep * sign > 0).mean())
    median_ic = float(np.median(ic_arr * sign))
    # OOS 段（后 40%）动态成本
    n = len(m)
    cut = int(n * 0.6)
    mo = m.iloc[cut:].copy()
    sp_o = spread_usd.reindex(mo.index) / 2.0 + 0.10   # half-spread + slippage($)
    px = close.reindex(mo.index)
    # 信号 → 持仓（每 h 分钟更新一次，方向 sign；生效于下一分钟 = 已有 1 根延迟）
    pos = np.zeros(len(mo))
    idx = np.arange(0, len(mo), max(1, h))
    vals = np.sign(mo.iloc[:, 0].values) * sign
    for i in idx:
        pos[i] = vals[i]
    last = 0.0
    for i in range(len(pos)):
        if pos[i] != 0.0 or i % max(1, h) == 0:
            last = pos[i]
        pos[i] = last
    ret1 = px.pct_change().fillna(0.0).values
    gross = np.roll(pos, 1) * ret1
    gross[0] = 0.0
    cost = np.abs(np.diff(np.concatenate([[0.0], pos]))) * (sp_o.values / px.values)
    net = gross - cost
    eq = np.cumprod(1 + net)
    sd = net.std(ddof=1)
    sharpe = float(net.mean() / sd * np.sqrt(365 * 1440)) if sd > 0 else 0.0
    gross_sh = float(np.mean(gross) / (np.std(gross, ddof=1) + 1e-12) * np.sqrt(365 * 1440))
    cost_frac = float(cost.sum())
    out[f"{seg}|{feat}|{h}"] = {
        "n_days": len(ic_arr), "pos_day_frac": round(pos_frac, 3),
        "pos_day_frac_drop2": round(pos_frac_drop2, 3), "median_day_ic": round(median_ic, 4),
        "gross_sharpe": round(gross_sh, 2), "net_sharpe_1x": round(sharpe, 2),
        "cost_total": round(cost_frac, 4), "n_trades": int((np.diff(np.concatenate([[0.0], pos])) != 0).sum()),
        "n_oos": int(len(mo)),
    }
    print("%-40s days=%2d posDay=%.2f posDayDrop2=%.2f medDayIc=%6.4f | grossSh=%7.2f netSh1x=%7.2f cost=%.4f trades=%d" %
          (out[f"{seg}|{feat}|{h}"].keys() and f"{seg} {feat} h{h}", len(ic_arr), pos_frac, pos_frac_drop2,
           median_ic, gross_sh, sharpe, cost_frac, int((np.diff(np.concatenate([[0.0], pos])) != 0).sum())), flush=True)

json.dump(out, open("C:/AIQuant/reports/phase4_stage4_tradability.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
print("stage4 done")
