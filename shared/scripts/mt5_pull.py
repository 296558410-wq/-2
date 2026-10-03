# -*- coding: utf-8 -*-
"""mt5_pull.py — 只读拉取 XAUUSD M1/M5/H1（分年向后探测最早可用）。

安全：仅 copy_rates_*。
输出：C:/AIQuant/data/staging_mt5/XAUUSD_<TF>_server.parquet（服务器时间，未转 UTC）
"""
import sys
import time
from datetime import datetime, timezone

import MetaTrader5 as mt5
import pandas as pd

OUT = "C:/AIQuant/data/staging_mt5"
SYMBOL = "XAUUSD"
NOW = datetime.now(timezone.utc)

if not mt5.initialize():
    print("initialize failed:", mt5.last_error())
    sys.exit(1)


def pull(tf, tf_name, start_year=2016):
    chunks = []
    for year in range(start_year, NOW.year + 1):
        s = datetime(year, 1, 1, tzinfo=timezone.utc)
        e = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if year < NOW.year else NOW
        for attempt in range(3):
            r = mt5.copy_rates_range(SYMBOL, tf, s, e)
            if r is not None and len(r):
                d = pd.DataFrame(r)
                d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
                chunks.append(d)
                print(f"  {tf_name} {year}: {len(d):,} rows  {d['time'].iloc[0]} -> {d['time'].iloc[-1]}")
                break
            err = mt5.last_error()
            time.sleep(2 * (attempt + 1))
            if attempt == 2:
                print(f"  {tf_name} {year}: FAILED {err}")
        time.sleep(0.4)
    if not chunks:
        return None
    full = pd.concat(chunks, ignore_index=True)
    full = full.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    return full


for tf_name, tf in (("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("H1", mt5.TIMEFRAME_H1)):
    df = pull(tf, tf_name)
    if df is None:
        continue
    p = f"{OUT}/XAUUSD_{tf_name}_server.parquet"
    df.to_parquet(p, index=False)
    print(f"[ok] {tf_name}: {len(df):,} rows -> {p}  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")
mt5.shutdown()
print("pull done (read-only)")
