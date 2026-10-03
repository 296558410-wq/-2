# -*- coding: utf-8 -*-
"""phase4_micro_research.py — FXTM tick 微观结构信息研究（Phase 4 主脚本）。

步骤：
  1) 合并 tick 日文件 → M1 微结构 bar（micro_duka.tick_to_bars，严格 bar 内 tick）
  2) 特征矩阵（含滚动/zscore 变体，无前视）
  3) 标签：forward_return_{1,2,5,10,15,30,60}m / future_vol_{5,15,30,60}m（严格未来）
  4) IC 衰减曲线（feature × horizon）+ 代表性置换 p
  5) session / vol-regime / spread-regime 分层（对 top 特征）
输出 reports/phase4_info_decay.json + parquet 供后续策略层
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "C:/AIQuant")
sys.path.insert(0, "C:/AIQuant/scripts")
from research_engine.features.micro_duka import tick_to_bars

STAGE = Path("C:/AIQuant/data/staging_fxtm")
OUT = Path("C:/AIQuant/reports")
HORIZONS_RET = [1, 2, 5, 10, 15, 30, 60]
HORIZONS_VOL = [5, 15, 30, 60]


def load_ticks() -> pd.DataFrame:
    parts = [pd.read_parquet(p) for p in sorted(STAGE.glob("ticks_*.parquet"))]
    df = pd.concat(parts, ignore_index=True)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    return df


def build_micro_bars(ticks: pd.DataFrame) -> pd.DataFrame:
    return tick_to_bars(ticks, rule="1min").reset_index().rename(columns={"index": "ts_utc"})


def build_features(bars: pd.DataFrame) -> pd.DataFrame:
    b = bars.set_index("ts_utc")
    out = pd.DataFrame(index=b.index)
    base = {
        "tick_count": b["tick_count"], "arrival": b["tick_arrival_rate"],
        "spread": b["spread_mean"], "tick_imb": b["tick_imbalance"],
        "vol_imb": b["vol_imbalance"], "buy_pressure": b["buy_pressure"],
        "impact": b["impact_proxy"],
    }
    for name, s in base.items():
        out[name] = s
        out[f"{name}_r30"] = s.rolling(30).mean()
        out[f"{name}_r120"] = s.rolling(120).mean()
        out[f"z_{name}_120"] = ((s - s.rolling(120).mean()) / s.rolling(120).std(ddof=1))
    out["flow_persist"] = np.sign(b["tick_imbalance"]).eq(np.sign(b["tick_imbalance"].shift(1))).astype(float)
    out["spread_chg"] = b["spread_mean"].diff()
    return out


def add_labels(bars: pd.DataFrame) -> pd.DataFrame:
    b = bars.set_index("ts_utc")
    close = b["mid_last"]
    r = close.pct_change()
    out = pd.DataFrame(index=b.index)
    for h in HORIZONS_RET:
        out[f"fwd_{h}"] = close.shift(-h) / close - 1.0
    for h in HORIZONS_VOL:
        out[f"fvol_{h}"] = r.rolling(h).std(ddof=1).shift(-h)
    out["rvol30_now"] = r.rolling(30).std(ddof=1)
    out["spread_now"] = b["spread_mean"]
    return out


def ic(a, b):
    m = pd.concat([a, b], axis=1).dropna()
    if len(m) < 500:
        return float("nan"), 0
    return float(spearmanr(m.iloc[:, 0], m.iloc[:, 1]).statistic), len(m)


def main():
    t0 = time.perf_counter()
    ticks = load_ticks()
    print(f"ticks: {len(ticks):,}", flush=True)
    bad = ((ticks["ask"] <= ticks["bid"]) | (ticks["ask"] <= 0)).sum()
    print(f"spread<=0 ticks: {bad} ({bad/len(ticks)*100:.3f}%)", flush=True)
    bars = build_micro_bars(ticks)
    print(f"micro M1 bars: {len(bars)}  {bars['ts_utc'].iloc[0]} -> {bars['ts_utc'].iloc[-1]}", flush=True)
    print(f"  spread $ mean={bars['spread_mean'].mean():.4f} med={bars['spread_mean'].median():.4f} "
          f"p99={bars['spread_mean'].quantile(0.99):.4f}  (close ~3300)", flush=True)
    print(f"  ticks/min mean={bars['tick_count'].mean():.0f} arrival/s={bars['tick_arrival_rate'].mean():.1f}", flush=True)
    bars.to_parquet(STAGE / "micro_m1_bars.parquet", index=False)

    X = build_features(bars)
    Y = add_labels(bars)
    n = min(len(X), len(Y))
    X, Y = X.iloc[:n], Y.iloc[:n]
    X.to_parquet(STAGE / "micro_m1_features.parquet")
    Y.to_parquet(STAGE / "micro_m1_labels.parquet")

    # ---- IC 衰减 ----
    feats = list(X.columns)
    decay = {}
    for f in feats:
        row = {}
        for h in HORIZONS_RET:
            row[f"fwd_{h}"] = round(ic(X[f], Y[f"fwd_{h}"])[0], 5)
        for h in HORIZONS_VOL:
            row[f"fvol_{h}"] = round(ic(X[f], Y[f"fvol_{h}"])[0], 5)
        decay[f] = row
    dfd = pd.DataFrame(decay).T
    dfd.to_csv(OUT / "phase4_ic_decay_matrix.csv")
    print("\n=== IC decay (ret horizons) ===", flush=True)
    cols = [f"fwd_{h}" for h in HORIZONS_RET]
    print(dfd[cols].round(4).to_string(), flush=True)
    print("\n=== IC decay (vol horizons) ===", flush=True)
    cols2 = [f"fvol_{h}" for h in HORIZONS_VOL]
    print(dfd[cols2].round(4).to_string(), flush=True)
    print(f"\nwall {time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
