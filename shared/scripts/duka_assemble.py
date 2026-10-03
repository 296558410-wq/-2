# -*- coding: utf-8 -*-
"""duka_assemble.py — Dukascopy 蜡烛 → 规范数据集 → data_registry 注册。

输出（mid 报价，UTC）：
  XAUUSD_M1_DUKA_<ts>_v001  (open/high/low/close=mid; spread_close=ask.c-bid.c 等)
  XAUUSD_M5/H1 由 mid M1 重采样（同源一致）
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
sys.path.insert(0, "C:/AIQuant/scripts")
from research_engine.core import data_registry
from research_engine.core.dataquality import run_quality_gate

STAGE = Path("C:/AIQuant/data/staging_duka")
SCALE = 1000.0


def load_month(ym: str) -> pd.DataFrame | None:
    p = STAGE / f"candles_{ym}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    # df 列: sec open close low high vol side (+原 day 未存!) → 需要年月日：由文件推断 + sec
    return df


def build_m1() -> pd.DataFrame:
    """逐月拼装 → 每日 1440×2(side) → pivot → mid OHLC。"""
    frames = []
    for p in sorted(STAGE.glob("candles_*.parquet")):
        ym = p.stem.split("_")[1]
        df = pd.read_parquet(p)
        # 该月文件可能包含多天（并行写 append），sec 是日内秒 → 需要 day 字段：由 sec 无法区分 → 修复：写文件时须带 day！
        # 旧文件没有 day 列 → 若缺失则无法恢复日期 → 重新生成带 day 的版本
        if "day" not in df.columns:
            raise SystemExit(
                f"{p} 缺 day 列——需重下。先跑 duka_download 的 candles 阶段（脚本已改）。")
        frames.append(df)
    allc = pd.concat(frames, ignore_index=True)
    allc["ts"] = pd.to_datetime(allc["day"], utc=True) + pd.to_timedelta(allc["sec"], unit="s")
    allc = allc.drop_duplicates(subset=["ts", "side"]).sort_values("ts")
    bid = allc[allc["side"] == "BID"].set_index("ts")
    ask = allc[allc["side"] == "ASK"].set_index("ts")
    out = pd.DataFrame({
        "open": (bid["open"] + ask["open"]) / 2 / SCALE,
        "high": (bid["high"] + ask["high"]) / 2 / SCALE,
        "low": (bid["low"] + ask["low"]) / 2 / SCALE,
        "close": (bid["close"] + ask["close"]) / 2 / SCALE,
        "bid_close": bid["close"] / SCALE,
        "ask_close": ask["close"] / SCALE,
        "spread_close": (ask["close"] - bid["close"]) / SCALE,
        "spread_hl": ((ask["high"] - bid["low"])) / SCALE,
    })
    out = out.dropna(subset=["close"])
    out.index.name = "ts_utc"
    out = out.reset_index()
    out.insert(1, "symbol", "XAUUSD")
    return out


def main():
    m1 = build_m1()
    print("M1 rows:", len(m1), m1["ts_utc"].iloc[0], "->", m1["ts_utc"].iloc[-1])
    qc = run_quality_gate(m1, symbol="XAUUSD", timeframe="M1", expected_freq="1min", has_spread=True)
    print("QC:", qc["gate_passed"], "dup", qc["duplicates"], "missing", qc["missing_bars"],
          "abnormal", qc["abnormal_gaps"], "spread_npos", qc["spread"]["n_nonpos"])
    if not qc["gate_passed"]:
        print("!! QC failed — inspect before register")
        return
    meta = data_registry.register_dataset(
        m1, source="Dukascopy-HTTP", symbol="XAUUSD", timeframe="M1",
        extra={"note": "mid of BID/ASK M1 candles (scale 1000); spread_close=ask.c-bid.c; "
                       "duka proprietary feed",
               "qc": {k: qc[k] for k in ("duplicates", "missing_bars", "abnormal_gaps", "ohlc_ok")}})
    print("REGISTERED", meta["dataset_id"])
    # M5/H1 由 mid 重采样
    base = m1.set_index("ts_utc")
    for rule, tf in (("5min", "M5"), ("1h", "H1")):
        o = base["open"].resample(rule).first()
        h = base["high"].resample(rule).max()
        l = base["low"].resample(rule).min()
        c = base["close"].resample(rule).last()
        sp = base["spread_close"].resample(rule).mean()
        sub = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "spread_close": sp}).dropna()
        sub.insert(0, "symbol", "XAUUSD")
        sub = sub.reset_index().rename(columns={"ts_utc": "ts_utc"})
        m2 = data_registry.register_dataset(
            sub, source="Dukascopy-HTTP", symbol="XAUUSD", timeframe=tf,
            extra={"derived_from": meta["dataset_id"]})
        print("REGISTERED", m2["dataset_id"])


if __name__ == "__main__":
    main()
