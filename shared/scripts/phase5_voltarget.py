# -*- coding: utf-8 -*-
"""phase5_voltarget.py — Volatility timing 用于仓位/风险的价值演示。

问题：波动率可预测（已证）→ 用它做目标波动率定仓是否改善交易结果？
设计（无方向 alpha，纯风险层）：
  基准：H1 恒定全仓多头（买入持有代理）
  方案：目标波动率定仓 size = target / vol_forecast（每日重平衡，成本=roundtrip spread）
  对比：日收益波动、最大回撤、95% VaR、年化收益/风险
窗口：FXTM H1 2026 与 DUKA H1 2023-24（双源互证）
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry

WINDOWS = {
    "FXTM_2026_H1": "XAUUSD_H1_MT5-FXTM-Live_20260904_v001",
    "DUKA_2023_24_H1": "XAUUSD_H1_Dukascopy-HTTP_20260904_v001",
}
TARGET_ANN_VOL = 0.10  # 10% 年化目标


def metrics_from_daily(daily_ret: np.ndarray, periods_per_year=365) -> dict:
    dr = np.asarray(daily_ret, dtype=float)
    sd = dr.std(ddof=1)
    sharpe = float(dr.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0
    eq = np.cumprod(1 + dr)
    mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
    var95 = float(np.percentile(dr, 5))
    return {"ann_ret": float((np.prod(1 + dr) ** (periods_per_year / len(dr)) - 1)) if len(dr) else 0,
            "ann_vol": float(sd * np.sqrt(periods_per_year)),
            "sharpe": round(sharpe, 2), "max_dd": round(mdd, 3), "var95": round(var95, 4)}


def run(name, ds_id, spread_bp: float):
    df, meta = data_registry.load_dataset(ds_id)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    close = df["close"]
    r = close.pct_change()
    # vol forecast: r^2 的 ewm（halflife=12，E[r^2]=σ^2 无偏口径）→ 年化
    vol_f = np.sqrt(r.pow(2).ewm(halflife=12, min_periods=12).mean()).shift(1) * np.sqrt(365 * 24)
    target = TARGET_ANN_VOL
    size = np.clip(target / vol_f, 0.0, 2.0)
    # 每日末重平衡（H1 频率近似：每次 size 变化即换仓，成本 = 单边 roundtrip? 用 |Δsize|*spread_bp）
    cost_oneway_bp = spread_bp / 2 + 0.1
    turnover = np.abs(np.diff(np.concatenate([[0.0], size.values])))
    cost = turnover * cost_oneway_bp / 1e4
    strat_r = size.shift(1).values * r.values - cost
    bench_r = r.values
    # 日聚合（按 UTC 日）
    day = pd.DatetimeIndex(df["ts_utc"]).date
    dd = pd.DataFrame({"strat": strat_r, "bench": bench_r, "day": day}).groupby("day").sum()
    out = {"n_days": int(len(dd)), "n_bars": int(len(df)),
           "bench": metrics_from_daily(dd["bench"].values),
           "strat": metrics_from_daily(dd["strat"].values),
           "vol_forecast_ic_spearman_daily": round(float(
               pd.Series(vol_f.values).corr(pd.Series(r.abs().values), method="spearman")), 3),
           "turnover_cost_total_bp": round(float(np.nansum(cost) * 1e4), 2)}
    out["strat"]["mdd_improve_pct"] = round(
        100 * (1 - out["strat"]["max_dd"] / out["bench"]["max_dd"]) if out["bench"]["max_dd"] < 0 else 0, 1)
    out["strat"]["vol_reduction_pct"] = round(
        100 * (1 - out["strat"]["ann_vol"] / out["bench"]["ann_vol"]) if out["bench"]["ann_vol"] > 0 else 0, 1)
    print(f"[{name}] " + json.dumps(out, ensure_ascii=False), flush=True)
    return out


res = {}
res["FXTM_2026_H1"] = run("FXTM_2026_H1", WINDOWS["FXTM_2026_H1"], spread_bp=0.36)
res["DUKA_2023_24_H1"] = run("DUKA_2023_24_H1", WINDOWS["DUKA_2023_24_H1"], spread_bp=2.4)
json.dump(res, open("C:/AIQuant/reports/phase5_voltarget.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("voltarget done")
