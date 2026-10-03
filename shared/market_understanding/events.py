# -*- coding: utf-8 -*-
"""market_understanding/events.py — 显著市场运动事件检测。

事件：30m 窗口 |收盘变化| > 阈值（滚动 30m vol 的 k 倍），窗口滑动取局部极大，
记录事件时段/幅度/方向/session。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_events(df: pd.DataFrame, window: int = 30, k_sigma: float = 3.0,
                  min_gap: int = 60) -> pd.DataFrame:
    d = df.sort_values("ts_utc").reset_index(drop=True) if "ts_utc" in df.columns else df.reset_index(drop=True)
    close = d["close"]
    r = close.pct_change()
    win_ret = close / close.shift(window) - 1.0
    vol = r.rolling(window).std(ddof=1) * np.sqrt(window)
    score = win_ret.abs() / vol
    cand = (score > k_sigma).values
    events = []
    i = 0
    n = len(d)
    ts = pd.DatetimeIndex(d["ts_utc"])
    while i < n:
        if cand[i]:
            j = i
            while j + 1 < n and cand[j + 1]:
                j += 1
            mid = i + int((j - i) / 2)
            ret = float(win_ret.iloc[mid])
            events.append({"t_start": ts[i], "t_end": ts[j], "t_mid": ts[mid],
                           "win_ret": ret, "abs_ret_pct": abs(ret) * 100,
                           "direction": "down" if ret < 0 else "up",
                           "k_sigma": float(score.iloc[mid]), "session": None})
            i = j + min_gap
        else:
            i += 1
    ev = pd.DataFrame(events)
    if len(ev):
        from research_engine.core.dataquality import session_of
        ev["session"] = session_of(pd.DatetimeIndex(ev["t_mid"])).values
    return ev
