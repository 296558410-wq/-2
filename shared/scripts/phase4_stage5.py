# -*- coding: utf-8 -*-
"""phase4_stage5.py — 非重叠再检验（修正重叠标签功效虚高）。

对 7 条 session 规则：
  1) 仅在 session 内每隔 h 分钟取一个入场点 → 非重叠 fwd 收益
  2) OOS 段：IC + 置换 p（样本数 ~ n/h，诚实功效）
  3) 交易层：同一入场点序列，动态成本（half-spread+slippage 0.1$），
     按日净收益 → 23 天 t 检验（小样本诚实检验）
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
bars = pd.read_parquet(STAGE / "micro_m1_bars.parquet").set_index("ts_utc")
close = bars["mid_last"].reindex(Y.index)
spread_usd = bars["spread_mean"].reindex(Y.index)
rng = np.random.default_rng(7)
out = {}
for seg, feat, h, sign in RULES:
    mask = sess.values == seg
    f_all = X.loc[mask, feat]
    close_all = close.loc[mask]
    sp_all = spread_usd.loc[mask]
    # 非重叠入场点：每组 h 分钟取一个（跳过组内 NaN）
    n_all = len(f_all)
    entry_idx = []
    for st in range(0, n_all - h, h):
        seg_slice = f_all.iloc[st:st + h]
        if seg_slice.notna().sum() >= h // 2 and np.isfinite(close_all.iloc[st + h]):
            entry_idx.append(st)
    ei = np.array(entry_idx)
    f = f_all.values[ei].astype(float)
    px = close_all.values
    ret_h = px[ei + h] / px[ei] - 1.0
    sp_entry = sp_all.values[ei]
    # 分 train/OOS（按入场序号 60/40）
    cut = int(len(ei) * 0.6)
    tr, te = slice(0, cut), slice(cut, len(ei))
    ic_te = float(spearmanr(f[te], ret_h[te]).statistic)
    # 置换 p（OOS）
    obs = ic_te
    dist = np.empty(2000)
    for i in range(2000):
        perm = rng.permutation(ret_h[te])
        dist[i] = float(spearmanr(f[te], perm).statistic)
    p_val = float((np.abs(dist) >= abs(obs)).mean())
    # 交易层：仅 OOS 入场；方向 sign；成本 half-spread@入场 + slippage
    pos = np.where(np.sign(f[te]) * sign > 0, 1.0, np.where(np.sign(f[te]) * sign < 0, -1.0, 0.0))
    cost_per = (sp_entry[te] / 2.0 + 0.10) / px[ei[te]]
    net = pos * ret_h[te] - np.abs(pos) * cost_per
    # 按日汇总（入场时间 → day）
    day_of = pd.DatetimeIndex(f_all.index[ei[te]]).date
    daily = pd.Series(net).groupby(day_of).sum()
    dmean, dstd = daily.mean(), daily.std(ddof=1)
    t_stat = float(dmean / (dstd / np.sqrt(len(daily)))) if dstd > 0 else 0.0
    out[f"{seg}|{feat}|{h}"] = {
        "n_entries_full": int(len(ei)), "n_oos": int(len(ei) - cut), "n_days": int(len(daily)),
        "ic_oos_nonoverlap": round(ic_te, 4), "p_perm": round(p_val, 4),
        "mean_net_per_trade_bp": round(float(net.mean()) * 1e4, 3),
        "day_mean_net_bp": round(float(dmean) * 1e4, 2), "day_t": round(t_stat, 2),
        "pos_days": int((daily > 0).sum()),
    }
    print("%-38s n=%4d ic=%7.4f p=%6.4f | net/trade=%6.2fbp dayMean=%7.2fbp t=%6.2f posDays=%d/%d" %
          (f"{seg} {feat} h{h}", len(ei), ic_te, p_val, net.mean() * 1e4, dmean * 1e4, t_stat,
           int((daily > 0).sum()), len(daily)), flush=True)

json.dump(out, open("C:/AIQuant/reports/phase4_stage5_nonoverlap.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("stage5 done")
