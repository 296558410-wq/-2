# -*- coding: utf-8 -*-
"""phase5_liquidity.py — Spread/Liquidity timing & execution simulation（Phase 5 核心）。

问题：能否预测“什么时候交易成本更低”？等待执行是否真省钱（扣掉价格风险后）？
协议：阈值与统计量在 train 段估计，效果在 OOS 段评估；按日聚合 t 检验；双窗口互证。
模拟（M1 粒度，买方向）：
  - immediate:  立即市价 = 支付 half_spread_now
  - wait:       spread_now > session_p60 时等待至 cap 内首次出现 spread ≤ session_p40，
                在那一刻市价成交；超时则立即市价
  - 成本 = half_spread@成交 + 等待期价格风险 |Δmid|（买方向，mid 上行=不利，如实符号化）
输出 reports/phase5_liquidity_timing.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.core.dataquality import session_of

WINDOWS = {
    "FXTM_2026": "XAUUSD_M1_MT5-FXTM-Live_20260904_v001",
    "DUKA_2023_24": "XAUUSD_M1_Dukascopy-HTTP_20260904_v001",
}
CAP = 30        # 最长等待（分钟）
H_SPREAD = 60   # 预测目标窗口（min）


def session_p_levels(spread_arr, sess_arr):
    """train 段估计各 session 的 p40/p60（位置数组版）。"""
    out = {}
    for s in np.unique(sess_arr):
        vals = spread_arr[sess_arr == s]
        vals = vals[~np.isnan(vals)]
        if len(vals) > 50:
            out[s] = (float(np.quantile(vals, 0.4)), float(np.quantile(vals, 0.6)))
    return out


def run_window(name, ds_id):
    df, meta = data_registry.load_dataset(ds_id)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    n = len(df)
    split = int(n * 0.5)
    tr, te = df.iloc[:split], df.iloc[split:]
    spread = df["spread"]
    sess_all = session_of(pd.DatetimeIndex(df["ts_utc"]))
    # ---- 可预测性（非重叠，OOS）----
    h = H_SPREAD
    ei = np.arange(split, n - h, h)  # OOS 入场
    cur = spread.values[ei]
    fut = np.array([np.median(spread.values[i + 1:i + 1 + h]) for i in ei])
    oos_ic = float(np.corrcoef(cur, fut)[0, 1]) if len(ei) > 30 else float("nan")
    # 排序相关稳健版
    from scipy.stats import spearmanr
    oos_ic_sp = float(spearmanr(cur, fut).statistic)
    # ---- 等待执行策略（train 阈值 → OOS 应用）----
    levels_tr = session_p_levels(spread.values[:split], sess_all.values[:split])
    rows = []
    day_of = pd.DatetimeIndex(te["ts_utc"]).date
    for i in range(len(te)):
        t0 = split + i
        if t0 + 1 >= n:
            break
        s0 = sess_all.values[t0]
        lv = levels_tr.get(s0)
        if lv is None:
            continue
        p40, p60 = lv
        sp0 = spread.iloc[t0]
        cost_imm = sp0 / 2.0
        # wait 策略
        cost_wait, filled_at, waited = cost_imm, 0, 0
        if sp0 > p60:
            limit = min(t0 + CAP, n - 1)
            hit = None
            for j in range(t0 + 1, limit + 1):
                if spread.iloc[j] <= p40:
                    hit = j
                    break
            if hit is not None:
                cost_wait = spread.iloc[hit] / 2.0
                # 价格风险（买方向：mid 上行=不利）
                mid0 = (df["bid"].iloc[t0] + df["ask"].iloc[t0]) / 2 if {"bid", "ask"} <= set(df.columns) else df["close"].iloc[t0]
                midf = df["close"].iloc[hit]
                adv = (midf - mid0) / mid0
                cost_wait = cost_wait + max(0.0, adv)  # 不利移动计入成本
                filled_at, waited = 1, hit - t0
        rows.append({"day": day_of[i], "imm": cost_imm, "wait": cost_wait,
                     "filled": filled_at, "waited": waited})
    sim = pd.DataFrame(rows)
    if len(sim) < 100:
        return {"oos_n": int(len(ei)), "ic": None}
    daily = sim.groupby("day").agg(imm=("imm", "mean"), wait=("wait", "mean"),
                                   save_bp=("imm", lambda x: (x - sim.loc[x.index, "wait"]).mean() * 1e4),
                                   fill=("filled", "mean"))
    d = daily.reset_index()
    saving = (d["imm"] - d["wait"]) * 1e4
    t = float(saving.mean() / (saving.std(ddof=1) / np.sqrt(len(saving)))) if saving.std(ddof=1) > 0 else 0.0
    return {"oos_n_entries": int(len(ei)), "n_sim": int(len(sim)), "n_days": int(len(daily)),
            "ic_spread_persistence_pearson": round(oos_ic, 4),
            "ic_spread_persistence_spearman": round(oos_ic_sp, 4),
            "mean_saving_bp": round(float(saving.mean()), 3),
            "saving_t_daily": round(t, 2),
            "pos_saving_days": int((saving > 0).sum()),
            "fill_rate_when_wait": round(float(sim["filled"].mean()), 3),
            "mean_wait_min": round(float(sim.loc[sim["filled"] == 1, "waited"].mean()), 1),
            "cost_imm_bp": round(float(sim["imm"].mean()) / df["close"].mean() * 1e4, 3),
            "cost_wait_bp": round(float(sim["wait"].mean()) / df["close"].mean() * 1e4, 3)}


out = {}
for name, ds in WINDOWS.items():
    r = run_window(name, ds)
    out[name] = r
    print(f"[{name}]", json.dumps({k: v for k, v in r.items()}, ensure_ascii=False), flush=True)

json.dump(out, open("C:/AIQuant/reports/phase5_liquidity_timing.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("phase5 liquidity done")
