# -*- coding: utf-8 -*-
"""core/dataquality.py — 真实数据质量门（Phase 2 §4）。

检查：时间（UTC/单调/重复/缺失/异常缺口）、OHLC 不变量、spread、
Session 标注（Asia/London/NY/overlap —— 只标注不删除）。
返回结构化 QC 报告；全部 PASS 才允许进入研究。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 固定 UTC 时段（冬季惯例，XAUUSD 24x5）：
#   Asia 00–07 · London 07–12 · NY 12–21 · London/NY overlap 12–16
SESSION_BANDS = {
    "asia": (0, 7),
    "london": (7, 12),
    "ny": (12, 21),
    "london_ny_overlap": (12, 16),
}


def session_of(ts: pd.DatetimeIndex) -> pd.Series:
    h = ts.hour
    out = pd.Series("off", index=ts)
    for name, (a, b) in SESSION_BANDS.items():
        out[(h >= a) & (h < b)] = name
    return out


def _ts_series(df: pd.DataFrame) -> pd.Series:
    if "ts_utc" in df.columns:
        return df["ts_utc"]
    return df.index.to_series()


def run_quality_gate(df: pd.DataFrame, *, symbol: str = "XAUUSD",
                     timeframe: str = "M1", expected_freq: str | None = None,
                     has_spread: bool = False) -> dict:
    """返回 QC 结果 dict；gate_passed=False 时禁止进研究。"""
    ts = _ts_series(df)
    tsi = pd.DatetimeIndex(ts)
    if tsi.tz is None:
        tz_ok = False
    else:
        tz_ok = str(tsi.tz) == "UTC"

    n = len(df)
    dup = int(tsi.duplicated().sum())
    mono = bool(tsi.is_monotonic_increasing)
    # 缺失/异常缺口：以期望频率推算
    freq = expected_freq or ("1min" if timeframe == "M1" else "5min" if timeframe == "M5" else "1h")
    missing, abnormal_gaps = 0, 0
    if n > 1 and mono:
        gaps = tsi.to_series().diff().dropna()
        gap_min = pd.Timedelta(freq).total_seconds() / 60.0
        # 正常缺口 = 周末(≥2天)；异常 = 非周末且 > 2×freq
        weekend_mask = tsi.weekday >= 5
        # 逐 gap 判断
        prev = tsi[0]
        for i in range(1, n):
            cur = tsi[i]
            delta = (cur - prev).total_seconds() / 60.0
            if delta <= 0:
                continue
            # 周末断点：周五 21:00 UTC 收盘 → 周一 21:00? XAUUSD 24x5 周一 00 开盘
            expected = gap_min
            if abs(delta - expected) > gap_min * 0.5:
                # 判断是否跨周末
                days = (cur.normalize() - prev.normalize()).days
                if days >= 2 and prev.dayofweek >= 4 and cur.dayofweek <= 1:
                    missing += max(0, int(delta / gap_min) - 1 - int((days - 1) * 1440 / gap_min))
                else:
                    abnormal_gaps += 1
            else:
                missing += max(0, int(round(delta / gap_min)) - 1)
            prev = cur

    # OHLC 不变量
    ohlc_ok = True
    ohlc_violations = 0
    if {"open", "high", "low", "close"}.issubset(df.columns):
        hi = df["high"]
        lo = df["low"]
        ohlc_violations = int(((hi < df[["open", "close"]].max(axis=1)) |
                               (lo > df[["open", "close"]].min(axis=1)) |
                               (hi < lo)).sum())
        ohlc_ok = ohlc_violations == 0

    # spread
    spread = {}
    if has_spread or "spread" in df.columns:
        sp = df["spread"]
        spread = {"n": int((sp > 0).sum()), "n_nonpos": int((sp <= 0).sum()),
                  "mean": float(sp.mean()), "p99": float(sp.quantile(0.99)),
                  "max": float(sp.max())}
        # 异常尖峰：> 当日中位数的 10 倍
        med = sp.median()
        spikes = int((sp > med * 10).sum()) if med > 0 else 0
        spread["spike_count"] = spikes

    return {
        "symbol": symbol, "timeframe": timeframe, "n": n,
        "tz_utc": tz_ok, "monotonic": mono, "duplicates": dup,
        "missing_bars": int(missing), "abnormal_gaps": int(abnormal_gaps),
        "ohlc_ok": bool(ohlc_ok), "ohlc_violations": int(ohlc_violations),
        "spread": spread,
        "range": {"start": str(tsi.min()), "end": str(tsi.max())},
        "sessions": {k: int((session_of(tsi) == k).sum()) for k in SESSION_BANDS},
        "gate_passed": bool(tz_ok and mono and dup == 0 and ohlc_ok
                            and (not spread or spread["n_nonpos"] == 0)),
    }


def add_session_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["session"] = session_of(pd.DatetimeIndex(_ts_series(out)))
    return out
