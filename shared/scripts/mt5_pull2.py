# -*- coding: utf-8 -*-
"""mt5_pull2.py — 渐进式只读拉取（先近后远，逐年保存，可断点续传）。

策略：每年一个请求，先测 2024-2026 通路速度，再决定回补深度。
安全：仅 copy_rates_*。
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

OUT = Path("C:/AIQuant/data/staging_mt5")
SYMBOL = "XAUUSD"
NOW = datetime.now(timezone.utc)

if not mt5.initialize():
    print("initialize failed:", mt5.last_error())
    sys.exit(1)


def pull_year(tf, tf_name, year, timeout_attempts=2):
    s = datetime(year, 1, 1, tzinfo=timezone.utc)
    e = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if year < NOW.year else NOW
    for attempt in range(timeout_attempts):
        t0 = time.perf_counter()
        r = mt5.copy_rates_range(SYMBOL, tf, s, e)
        if r is not None and len(r):
            d = pd.DataFrame(r)
            d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
            print(f"  {tf_name} {year}: {len(d):,} rows in {time.perf_counter()-t0:.1f}s", flush=True)
            return d
        print(f"  {tf_name} {year}: attempt {attempt+1} -> {mt5.last_error()} after {time.perf_counter()-t0:.1f}s", flush=True)
        time.sleep(3)
    return None


def pull_tf(tf, tf_name, years):
    parts = []
    for y in years:
        d = pull_year(tf, tf_name, y)
        if d is not None:
            parts.append(d)
        # 每年后落盘一次（断点续传）
        if parts:
            tmp = pd.concat(parts, ignore_index=True)
            tmp.to_parquet(OUT / f"XAUUSD_{tf_name}_server.parquet", index=False)
    if not parts:
        return None
    full = pd.concat(parts, ignore_index=True)
    full = full.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    full.to_parquet(OUT / f"XAUUSD_{tf_name}_server.parquet", index=False)
    return full


YEARS = list(range(NOW.year, NOW.year - 7, -1))  # 2026..2020
for tf_name, tf in (("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("H1", mt5.TIMEFRAME_H1)):
    df = pull_tf(tf, tf_name, YEARS)
    if df is None:
        print(f"[fail] {tf_name}: no data")
        continue
    print(f"[ok] {tf_name}: {len(df):,} rows  {df['time'].iloc[0]} -> {df['time'].iloc[-1]}", flush=True)
mt5.shutdown()
print("pull2 done (read-only)")
