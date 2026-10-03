# -*- coding: utf-8 -*-
"""xauusd_baseline.py — 真实数据市场基线（§5）→ reports/xauusd_baseline.md。

覆盖 M1/M5/H1 × (整体/Asia/London/NY/overlap)：
收益分布/波动/自相关/日内季节性/spread 分布/缺口分布/趋势持续性/均值回复/波动聚集。
"""
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.core.dataquality import session_of

OUT = "C:/AIQuant/reports/xauusd_baseline.md"


def load(tf: str):
    ds = data_registry.find_dataset("XAUUSD", tf, source="MT5-FXTM-Live")[-1]
    df, meta = data_registry.load_dataset(ds["dataset_id"])
    df = df.sort_values("ts_utc").reset_index(drop=True)
    return df, meta


def r_stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 10:
        return {}
    return {"n": int(len(r)), "mean_bp": float(r.mean() * 1e4), "std_bp": float(r.std(ddof=1) * 1e4),
            "skew": float(r.skew()), "kurt": float(r.kurtosis()),
            "min_pct": float(r.min() * 100), "max_pct": float(r.max() * 100),
            "ac1": float(r.autocorr(1)), "ac5": float(r.autocorr(5)),
            "ac_abs1": float(r.abs().autocorr(1)),
            "mean_rev_ratio": float(-r.autocorr(1))}


def per_session(df: pd.DataFrame, freq_min: int) -> dict:
    r = df.set_index("ts_utc")["close"].pct_change()
    sess = session_of(pd.DatetimeIndex(df["ts_utc"]))
    out = {"overall": r_stats(r)}
    for name in ("asia", "london", "ny", "london_ny_overlap"):
        mask = sess.values == name
        rr = r[mask]
        out[name] = r_stats(rr)
        out[name]["mean_bp_per_h"] = out[name]["mean_bp"] * (60 / freq_min)
    return out


def intraday_seasonality(df: pd.DataFrame, freq_min: int) -> pd.DataFrame:
    r = df.set_index("ts_utc")["close"].pct_change()
    h = pd.DatetimeIndex(df["ts_utc"]).hour
    t = pd.DataFrame({"r": r.values, "h": h.values}).dropna()
    g = t.groupby("h")["r"].agg(["mean", "std"])
    g["mean_bp"] = g["mean"] * 1e4
    g["std_bp"] = g["std"] * 1e4
    return g


def spread_stats(df: pd.DataFrame) -> dict:
    s = df["spread"]
    return {"mean": float(s.mean()), "median": float(s.median()),
            "p99": float(s.quantile(0.99)), "max": float(s.max()),
            "mean_bps": float(s.mean() / df["close"].mean() * 1e4)}


def gap_analysis(df: pd.DataFrame, freq_min: int) -> dict:
    ts = pd.DatetimeIndex(df["ts_utc"])
    gaps = ts.to_series().diff().dropna().dt.total_seconds() / 60.0
    expected = freq_min
    weekend = gaps[(gaps > expected * 2) & (gaps > 60 * 12)]  # >12h = 周末
    intraday = gaps[(gaps > expected) & (gaps <= 60 * 12)]
    return {"weekend_gaps": int(len(weekend)),
            "intraday_gaps_gt_expected": int(len(intraday)),
            "intraday_gap_minutes_max": float(intraday.max()) if len(intraday) else 0.0,
            "weekend_gap_hours_min": float(weekend.min() / 60) if len(weekend) else 0.0,
            "weekend_gap_hours_max": float(weekend.max() / 60) if len(weekend) else 0.0,
            "gap_hist_hours": sorted([round(g / 60, 1) for g in weekend])[:10]}


def main() -> None:
    L: list[str] = [f"# XAUUSD 真实市场 Baseline", "",
                    f"> 生成 {datetime.now(timezone.utc).isoformat()} · 源: FXTM MT5 Live 只读历史 · 已过 QC",
                    ""]
    metas = {}
    dfs = {}
    for tf in ("M1", "M5", "H1"):
        df, meta = load(tf)
        dfs[tf] = df
        metas[tf] = meta
        L += [f"## {tf}", "",
              f"- dataset: `{meta['dataset_id']}` · rows={meta['rows']:,} · "
              f"{meta['start']} → {meta['end']} (UTC)",
              f"- spread 均值 ${meta['extra']['qc'] if False else ''}" ]
    # 简洁重写
    L = [f"# XAUUSD 真实市场 Baseline", "",
         f"> 生成 {datetime.now(timezone.utc).isoformat()} · 源: FXTM MT5 Live（只读历史）· data_registry 注册 · QC 通过",
         ""]
    for tf in ("M1", "M5", "H1"):
        df, meta = dfs[tf], metas[tf]
        freq = {"M1": 1, "M5": 5, "H1": 60}[tf]
        L += [f"## {tf}", "",
              f"`{meta['dataset_id']}` · rows={meta['rows']:,} · {meta['start']} → {meta['end']} UTC · sha256={meta['sha256'][:20]}…",
              ""]
        g = gap_analysis(df, freq)
        L += ["### 缺口", "",
              f"- 周末缺口（>12h）: {g['weekend_gaps']} 次，时长 {g['weekend_gap_hours_min']:.1f}–{g['weekend_gap_hours_max']:.1f}h",
              f"- 周内异常缺口: {g['intraday_gaps_gt_expected']} 次（最大 {g['intraday_gap_minutes_max']:.0f}min）",
              f"- 周末缺口样本(h): {g['gap_hist_hours']}", ""]
        ss = spread_stats(df)
        L += ["### Spread（USD，point=0.01）", "",
              f"- mean={ss['mean']:.3f} median={ss['median']:.3f} p99={ss['p99']:.3f} max={ss['max']:.2f} "
              f"≈ {ss['mean_bps']:.2f}bp（对价格）", ""]
        st = per_session(df, freq)
        L += ["### 收益分布（分钟收益 bp）· 按 session", "",
              "| segment | n | mean bp | mean bp/h | std bp | skew | kurt | ac1 | ac5 | ac(|r|)1 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for seg in ("overall", "asia", "london", "ny", "london_ny_overlap"):
            s = st[seg]
            L.append(f"| {seg} | {s['n']:,} | {s['mean_bp']:.2f} | {s.get('mean_bp_per_h', float('nan')):.2f} | "
                     f"{s['std_bp']:.2f} | {s['skew']:.2f} | {s['kurt']:.1f} | {s['ac1']:.4f} | {s['ac5']:.4f} | {s['ac_abs1']:.4f} |")
        L.append("")
        L.append("解读：ac1 显著为负 → 短周期均值回复；ac(|r|)1 高 → 波动聚集；mean bp/h 偏离 0 大且稳定 → 时段漂移。")
        L.append("")
        sea = intraday_seasonality(df, freq)
        peak_h = sea["std_bp"].idxmax()
        L += ["### 日内波动率季节性（UTC 小时）", "",
              f"- 最活跃小时: {peak_h:02d}:00 UTC（std {sea['std_bp'].max():.1f}bp）· 最静: {sea['std_bp'].idxmin():02d}:00",
              f"- 小时 std 表（前 8 活跃）:", ""]
        top = sea.sort_values("std_bp", ascending=False).head(8)
        L.append("| hour(UTC) | mean bp | std bp |")
        L.append("|---|---|---|")
        for h, row in top.iterrows():
            L.append(f"| {h:02d}:00 | {row['mean_bp']:.2f} | {row['std_bp']:.2f} |")
        L.append("")
        # 趋势持续性：variance ratio (10-bar) 近似
        r = dfs[tf].set_index("ts_utc")["close"].pct_change().dropna()
        vr10 = r.rolling(10).sum().var(ddof=1) / (r.var(ddof=1) * 10) if len(r) > 1000 else float("nan")
        L += [f"### 趋势/回复", "",
              f"- Variance Ratio (10-bar) ≈ {vr10:.3f}（<1 回复 / >1 趋势）",
              f"- 1-bar 自相关 ac1 见上表（负 → 均值回复主导）", ""]
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text("\n".join(L), encoding="utf-8")
    print(f"baseline 已写入 {OUT}")


from pathlib import Path  # noqa: E402

if __name__ == "__main__":
    main()
