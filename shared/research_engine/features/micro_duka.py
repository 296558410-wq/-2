# -*- coding: utf-8 -*-
"""features/micro_duka.py — Dukascopy tick 微观结构特征（Phase 3）。

输入：tick DataFrame（ts_utc 索引/列, ask, bid, ask_vol, bid_vol）
聚合到 M1（或任意 freq）bar；特征标注于 bar 结束时刻（仅用该 bar 内已发生 tick，
无前视）。价格单位：已转 USD（/1000）。
特征目录：
  tick_count / tick_arrival_rate(每秒) / mid 秒级收益 / realized spread(均/中位/分位) /
  signed tick imbalance (tick rule: 价升=买) / vol imbalance (ask_vol-bid_vol) /
  buy pressure = 买方 tick 数占比 / price impact 代理 = |Δmid|/sqrt(tick_count)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _tick_df(df: pd.DataFrame) -> pd.DataFrame:
    if "ts_utc" in df.columns:
        return df.set_index("ts_utc")
    return df


def tick_to_bars(ticks: pd.DataFrame, rule: str = "1min") -> pd.DataFrame:
    t = _tick_df(ticks).sort_index()
    t = t[~t.index.isna()]
    mid = (t["ask"] + t["bid"]) / 2.0
    t = t.assign(mid=mid, spread=(t["ask"] - t["bid"]))

    def _safe(fn):
        return lambda s: fn(s) if len(s) else np.nan

    g = t.groupby(pd.Grouper(freq=rule))
    has_vol = {"ask_vol", "bid_vol"} <= set(t.columns) or {"ask_volume", "bid_volume"} <= set(t.columns)
    if "ask_vol" not in t.columns and "ask_volume" in t.columns:
        t = t.rename(columns={"ask_volume": "ask_vol", "bid_volume": "bid_vol"})
    cols: dict = {
        "tick_count": g["mid"].count(),
        "duration_s": g["mid"].apply(_safe(lambda s: (s.index[-1] - s.index[0]).total_seconds() + 1.0)),
        "mid_first": g["mid"].first(),
        "mid_last": g["mid"].last(),
        "spread_mean": g["spread"].mean(),
        "spread_median": g["spread"].median(),
        "spread_p95": g["spread"].quantile(0.95),
        "up_ticks": g["mid"].apply(_safe(lambda s: int((s.diff() > 0).sum()))),
        "down_ticks": g["mid"].apply(_safe(lambda s: int((s.diff() < 0).sum()))),
        "abs_mid_move": g["mid"].apply(_safe(lambda s: float(s.diff().abs().sum()))),
    }
    if has_vol:
        cols.update({"ask_vol_sum": g["ask_vol"].sum(), "bid_vol_sum": g["bid_vol"].sum()})
    # 成交（trade print）特征：MT5 tick 中 volume>0 的为成交/最后价更新
    if "volume" in t.columns:
        ttrade = t.assign(trd=(t["volume"] > 0).astype(float))
        gg = ttrade.groupby(pd.Grouper(freq=rule))
        cols["trade_count"] = gg["trd"].sum()
        cols["trade_volume"] = gg["volume"].sum()
    bars = pd.DataFrame(cols).dropna(subset=["tick_count"])
    bars = bars[bars["tick_count"] > 0]
    bars["tick_arrival_rate"] = bars["tick_count"] / bars["duration_s"]
    n = bars["up_ticks"] + bars["down_ticks"]
    bars["tick_imbalance"] = ((bars["up_ticks"] - bars["down_ticks"]) / n.replace(0, np.nan)).fillna(0.0)
    if has_vol:
        vsum = (bars["ask_vol_sum"] + bars["bid_vol_sum"]).replace(0, np.nan)
        bars["vol_imbalance"] = ((bars["ask_vol_sum"] - bars["bid_vol_sum"]) / vsum).fillna(0.0)
    else:
        bars["vol_imbalance"] = np.nan
    bars["mid_ret"] = bars["mid_last"] / bars["mid_first"] - 1.0
    # price impact 代理：|Δmid| / sqrt(tick_count)（Amihud 风格）
    bars["impact_proxy"] = bars["abs_mid_move"] / np.sqrt(bars["tick_count"]).replace(0, np.nan)
    bars["buy_pressure"] = bars["up_ticks"] / bars["tick_count"]
    return bars


# ---- 跨 bar 特征（均只用历史，含当前已收盘 bar）----
def rolling_mean(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).mean()


def rolling_std(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).std(ddof=1)


def zscore(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window).mean()
    sd = s.rolling(window).std(ddof=1)
    return ((s - mu) / sd).rename(f"z_{s.name}_{window}")


MICRO_CATALOG = {
    "tick_count": lambda b, w=30: rolling_mean(b["tick_count"], w),
    "tick_arrival": lambda b, w=30: rolling_mean(b["tick_arrival_rate"], w),
    "spread_mean": lambda b, w=30: rolling_mean(b["spread_mean"], w),
    "spread_std": lambda b, w=30: rolling_std(b["spread_mean"], w),
    "tick_imb": lambda b, w=30: rolling_mean(b["tick_imbalance"], w),
    "vol_imb": lambda b, w=30: rolling_mean(b["vol_imbalance"], w),
    "buy_pressure": lambda b, w=30: rolling_mean(b["buy_pressure"], w),
    "impact_proxy": lambda b, w=30: rolling_mean(b["impact_proxy"], w),
    "z_tick_imb": lambda b, w=120: zscore(b["tick_imbalance"], w),
    "z_vol_imb": lambda b, w=120: zscore(b["vol_imbalance"], w),
    "z_spread": lambda b, w=120: zscore(b["spread_mean"], w),
}
