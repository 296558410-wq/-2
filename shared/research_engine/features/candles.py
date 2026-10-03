# -*- coding: utf-8 -*-
"""features/candles.py — Candlestick 行为特征（Phase 8）。

纪律：
  * 所有特征在 bar t 收盘决策，只用 ≤t；
  * swing 点离线检测（±L 确认），但 t 时刻只用 index ≤ t-L 的“已完全确认”swing（无前视）；
  * 形态均为规则定义（归一化到 range），可复核。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------- 单根形态 ----------------
def shape_frame(df: pd.DataFrame) -> pd.DataFrame:
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    rng = np.maximum(h - l, 1e-12)
    body = c - o
    out = pd.DataFrame(index=df.index if "ts_utc" not in df.columns else df.index)
    out["body"] = body
    out["body_frac"] = body / rng                      # 收成比（效率）
    out["upper_wick"] = (h - np.maximum(o, c)) / rng
    out["lower_wick"] = (np.minimum(o, c) - l) / rng
    out["close_pos"] = (c - l) / rng                   # 收盘在区间分位
    out["abs_body_frac"] = np.abs(body) / rng
    out["marubozu"] = ((out["upper_wick"] + out["lower_wick"]) < 0.1).astype(float)
    out["doji"] = (out["abs_body_frac"] < 0.1).astype(float)
    out["hammer"] = ((out["lower_wick"] >= 2 * out["abs_body_frac"]) & (out["upper_wick"] <= 0.2)
                     & (out["lower_wick"] >= 0.5)).astype(float)
    out["shooting_star"] = ((out["upper_wick"] >= 2 * out["abs_body_frac"]) & (out["lower_wick"] <= 0.2)
                            & (out["upper_wick"] >= 0.5)).astype(float)
    # engulfing（相对前一根实体）
    pb = np.roll(body, 1)
    pb[0] = np.nan
    pr = np.roll(rng, 1)
    pr[0] = np.nan
    up = (body > 0) & (pb < 0) & (c > np.roll(o, 1)) & (o < np.roll(c, 1))
    dn = (body < 0) & (pb > 0) & (c < np.roll(o, 1)) & (o > np.roll(c, 1))
    out["engulf_up"] = up.astype(float)
    out["engulf_dn"] = dn.astype(float)
    ph = np.roll(h, 1)
    pl = np.roll(l, 1)
    ph[0], pl[0] = np.nan, np.nan
    out["inside_bar"] = ((h <= ph) & (l >= pl)).astype(float)
    out["harami"] = ((np.abs(body) < np.abs(pb)) & (np.sign(body) == np.sign(pb))
                     & (np.abs(pb) / np.maximum(pr, 1e-12) > 0.5)).astype(float)
    # 相对尺度（vs 滚动中位，先验窗口 60）
    rng_s = pd.Series(rng, index=out.index)
    bf_s = out["abs_body_frac"]
    out["range_z"] = ((rng_s - rng_s.rolling(60).median()) / (rng_s.rolling(60).std(ddof=1) + 1e-12))
    out["body_eff_z"] = ((bf_s - bf_s.rolling(60).mean()) / (bf_s.rolling(60).std(ddof=1) + 1e-12))
    out["wick_z"] = ((out["upper_wick"] + out["lower_wick"]).rolling(60).mean())
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


# ---------------- Swing 结构（t 时刻只用 ≤t-L 的已确认 swing） ----------------
def swing_structure(df: pd.DataFrame, L: int = 10) -> pd.DataFrame:
    """返回每 bar 的 swing 状态特征。
    swing 点：high[i] 为 [i-L, i+L] 内最大 → swing high（同理 low）；检测用全样本，
    但 t 时刻仅使用 index ≤ t-L 的点（确认窗已完全过去 → 无前视）。"""
    h = df["high"].values
    l = df["low"].values
    n = len(h)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    for i in range(L, n - L):
        if h[i] >= np.max(h[i - L:i + L + 1]) and h[i] > np.max(h[i - L:i]):
            sh[i] = True
        if l[i] <= np.min(l[i - L:i + L + 1]) and l[i] < np.min(l[i - L:i]):
            sl[i] = True
    out = pd.DataFrame(index=df.index)
    out["swing_high"] = sh.astype(float)
    out["swing_low"] = sl.astype(float)
    # 每 bar：最近确认 swing（≤t-L）的高低与方向状态
    idx_sh = np.where(sh)[0]
    idx_sl = np.where(sl)[0]
    sh_hist = []
    sl_hist = []
    dir_hist = []
    last_sh = last_sl = None
    seq_h: list[float] = []
    seq_l: list[float] = []
    for t in range(n):
        if t - L >= 0:
            if sh[t - L]:
                seq_h.append(h[t - L])
                last_sh = h[t - L]
            if sl[t - L]:
                seq_l.append(l[t - L])
                last_sl = l[t - L]
        # 方向：最近两个同向 swing 比较
        d = 0.0
        if len(seq_h) >= 2 and seq_h[-1] > seq_h[-2] and len(seq_l) >= 2 and seq_l[-1] > seq_l[-2]:
            d = 1.0
        elif len(seq_h) >= 2 and seq_h[-1] < seq_h[-2] and len(seq_l) >= 2 and seq_l[-1] < seq_l[-2]:
            d = -1.0
        dir_hist.append(d)
        sh_hist.append(last_sh if last_sh is not None else np.nan)
        sl_hist.append(last_sl if last_sl is not None else np.nan)
    out["last_swing_high"] = sh_hist
    out["last_swing_low"] = sl_hist
    out["trend_dir"] = dir_hist
    # 结构破坏（t 时刻收盘相对最近 swing 的突破状态；≤t 信息）
    c = df["close"].values
    brk_up = np.zeros(n)
    brk_dn = np.zeros(n)
    for t in range(1, n):
        if not np.isnan(out["last_swing_high"].iloc[t - 1]):
            brk_up[t] = float(c[t] > out["last_swing_high"].iloc[t - 1])
        if not np.isnan(out["last_swing_low"].iloc[t - 1]):
            brk_dn[t] = float(c[t] < out["last_swing_low"].iloc[t - 1])
    out["breakout_up"] = brk_up
    out["breakout_dn"] = brk_dn
    return out
