# -*- coding: utf-8 -*-
"""mt5_pull3.py — 只读拉取 v3：naive datetime（MetaTrader5 包限制），
返回时间为服务器墙钟（epoch）。先近后远、逐年落盘。
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

OUT = Path("C:/AIQuant/data/staging_mt5")
SYMBOL = "XAUUSD"

if not mt5.initialize():
    print("initialize failed:", mt5.last_error())
    sys.exit(1)


def pull_year(tf, tf_name, year):
    s = datetime(year, 1, 1)
    e = datetime.now()
    for attempt in range(3):
        t0 = time.perf_counter()
        r = mt5.copy_rates_range(SYMBOL, tf, s, e)
        if r is not None and len(r):
            d = pd.DataFrame(r)
            d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
            print(f"  {tf_name} {year}: {len(d):,} rows in {time.perf_counter()-t0:.1f}s "
                  f"({d['time'].iloc[0]} -> {d['time'].iloc[-1]})", flush=True)
            return d
        print(f"  {tf_name} {year}: attempt {attempt+1} {mt5.last_error()} "
              f"({time.perf_counter()-t0:.1f}s)", flush=True)
        time.sleep(2)
    return None


def pull_tf(tf, tf_name, years):
    parts = []
    for y in years:
        d = pull_year(tf, tf_name, y)
        if d is not None:
            # 只保留该年份的数据（避免重复累积）
            d = d[(d["time"].dt.year == y) | (d["time"].dt.year == y)]
            parts.append(d)
            tmp = pd.concat(parts, ignore_index=True)
            tmp.to_parquet(OUT / f"XAUUSD_{tf_name}_server.parquet", index=False)
    if not parts:
        return None
    full = pd.concat(parts, ignore_index=True)
    full = full.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    full.to_parquet(OUT / f"XAUUSD_{tf_name}_server.parquet", index=False)
    return full


YEARS = list(range(datetime.now().year, datetime.now().year - 7, -1))
for tf_name, tf in (("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("H1", mt5.TIMEFRAME_H1)):
    df = pull_tf(tf, tf_name, YEARS)
    if df is None:
        print(f"[fail] {tf_name}")
        continue
    print(f"[ok] {tf_name}: {len(df):,} rows  {df['time'].iloc[0]} -> {df['time'].iloc[-1]}", flush=True)
mt5.shutdown()
print("pull3 done (read-only)")
