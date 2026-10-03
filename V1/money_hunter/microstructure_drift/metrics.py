# -*- coding: utf-8 -*-
"""microstructure_drift/metrics.py — 确定性日内微结构统计 (seed 与 engine 共用)

只消费已存在的报价数据(bid/ask/时间戳), 不购买任何数据, 无 LLM。
与 self_collect/mt5_live_collect.py 的 microstructure() 定义保持同一会话切分
(UTC hour<7 Asia, <12 London, <16 Overlap, <21 NY, 其余 Quiet),
保证 seed(历史同源)与 live(前瞻)口径一致。

输入 parquet 需含 bid, ask 及时间列; ts 支持三种形态:
  - datetime64[ns/ms, UTC]  (staging_fxtm / live_fxtm 采集产物)
  - int64 毫秒 epoch       (DUKA assembled)
归一化为 ts_utc (UTC datetime) 后统一计算。

输出 = 单日指标 dict, 字段与 mt5_live_collect.microstructure() 兼容并扩展:
  n_ticks, n_minutes, arrival_per_min, median/p90/p99_spr_bps,
  spread_usd_median/p90, burst_min_p99_count(分钟计数 p99 阈值),
  burst_minutes(>=p99 的分钟数), by_session{...median/p99...}, n_jump_min, max_min_move_bps
"""
import numpy as np
import pandas as pd

SESSIONS = ("Asia", "London", "Overlap", "NY", "Quiet")
JUMP_MIN_BPS = 10.0  # 分钟级 |log 收益| >= 10bps 计为一次"价格跳跃"分钟 (v0 阈值)


def coerce_ts_utc(ts: pd.Series) -> pd.Series:
    """把三种时间形态统一为 UTC datetime64[ns] Series。"""
    if isinstance(ts.dtype, pd.DatetimeTZDtype) or ts.dtype.kind == "M":
        out = pd.to_datetime(ts, utc=True)
    elif ts.dtype.kind in ("i", "u"):
        out = pd.to_datetime(ts, unit="ms", utc=True)
    else:  # 字符串等兜底
        out = pd.to_datetime(ts, utc=True)
    return out.dt.tz_convert("UTC")


def session_hour_series(ts_utc: pd.Series) -> pd.Series:
    h = ts_utc.dt.hour
    return pd.Series(
        np.select([h < 7, h < 12, h < 16, h < 21], ["Asia", "London", "Overlap", "NY"], default="Quiet"),
        index=ts_utc.index,
    )


def day_metrics_from_df(df: pd.DataFrame) -> dict:
    """df 需含 bid, ask 与时间列(自动识别 ts_utc/utc_ms/time_msc)。"""
    if "ts_utc" in df.columns:
        ts = coerce_ts_utc(df["ts_utc"])
    elif "utc_ms" in df.columns:
        ts = pd.to_datetime(df["utc_ms"], unit="ms", utc=True)
    else:
        ts = coerce_ts_utc(df["time_msc"])
    ts = ts.dt.tz_convert("UTC")
    bid = df["bid"].to_numpy(float)
    ask = df["ask"].to_numpy(float)
    mid = (bid + ask) / 2.0
    spr = ask - bid
    valid = (bid > 0) & (ask > bid) & np.isfinite(bid) & np.isfinite(ask)
    if valid.sum() < 2:
        return None
    ts_v, mid_v, spr_v = ts[valid], mid[valid], spr[valid]
    midv = (spr_v > 0) & np.isfinite(mid_v)
    spr_bps = np.where(midv, spr_v / np.maximum(mid_v, 1e-9) * 1e4, np.nan)
    spr_bps_v = spr_bps[midv]
    # 会话切分 (UTC)
    sess = session_hour_series(ts_v)
    by_sess = {}
    for sname in SESSIONS:
        m = (sess == sname).to_numpy()
        if m.sum() > 0:
            by_sess[sname] = {
                "n": int(m.sum()),
                "median_spr_bps": float(np.nanmedian(spr_bps_v[m])),
                "p99_spr_bps": float(np.nanpercentile(spr_bps_v[m], 99)) if m.sum() >= 20 else None,
            }
    # 分钟级聚合: 报价突发 + 波动 + 跳跃
    minute = ts_v.dt.floor("60s")
    cnt = minute.value_counts().sort_index()
    p99c = float(np.percentile(cnt.to_numpy(), 99)) if len(cnt) > 10 else float(cnt.max())
    burst_minutes = int((cnt >= p99c).sum())
    mid_min = pd.Series(mid_v, index=ts_v).groupby(minute).last().sort_index()
    logret = np.log(mid_min).diff()
    rv1m_bps = float(logret.std(ddof=1) * 1e4) if len(logret.dropna()) >= 30 else None
    abs_min_bps = (logret.abs() * 1e4).dropna()
    n_jump_min = int((abs_min_bps >= JUMP_MIN_BPS).sum()) if len(abs_min_bps) else 0
    max_min_move_bps = float(abs_min_bps.max()) if len(abs_min_bps) else 0.0
    day = ts_v.dt.strftime("%Y%m%d").iloc[0]
    return {
        "date": day,
        "n_ticks": int(len(ts_v)),
        "n_minutes": int(len(cnt)),
        "arrival_per_min": round(float(len(ts_v) / len(cnt)), 2) if len(cnt) else None,
        "median_spr_bps": float(np.nanmedian(spr_bps_v)),
        "p90_spr_bps": float(np.nanpercentile(spr_bps_v, 90)),
        "p99_spr_bps": float(np.nanpercentile(spr_bps_v, 99)),
        "spread_usd_median": float(np.nanmedian(spr_v)),
        "spread_usd_p90": float(np.nanpercentile(spr_v, 90)),
        "burst_min_p99_count": p99c,
        "burst_minutes": burst_minutes,
        "rv1m_bps": rv1m_bps,
        "n_jump_min": n_jump_min,
        "max_min_move_bps": round(max_min_move_bps, 3),
        "by_session": by_sess,
    }


def load_parquet_metrics(path) -> dict | None:
    """读单日 parquet → day_metrics(仅当文件内全部 tick 属同一 UTC 日时口径正确)。"""
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return None
    return day_metrics_from_df(df)


def load_parquet_metrics_by_day(path) -> list[dict]:
    """读 parquet(单日或月文件) → 按 UTC 日拆分, 返回逐日 metrics 列表。
    DUKA assembled 为月文件(ts_utc int64 ms), staging/live 为日文件。
    """
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001
        return []
    if "ts_utc" in df.columns:
        ts = coerce_ts_utc(df["ts_utc"])
    elif "utc_ms" in df.columns:
        ts = pd.to_datetime(df["utc_ms"], unit="ms", utc=True)
    else:
        ts = coerce_ts_utc(df["time_msc"])
    df = df.assign(_day=ts.dt.strftime("%Y%m%d"))
    out = []
    for day, g in df.groupby("_day", sort=True):
        m = day_metrics_from_df(g.drop(columns="_day"))
        if m:
            out.append(m)
    return out
