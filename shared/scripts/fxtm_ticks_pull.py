# -*- coding: utf-8 -*-
"""fxtm_ticks_pull.py — 从 FXTM MT5 拉取近期 tick（copy_ticks_range，按日），存 parquet。

安全：只读。输出 data/staging_fxtm/ticks_YYYYMMDD.parquet
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

OUT = Path("C:/AIQuant/data/staging_fxtm")
OUT.mkdir(parents=True, exist_ok=True)

if not mt5.initialize():
    print("init failed", mt5.last_error())
    sys.exit(1)

days_back = 32
for d in range(days_back - 1, -1, -1):
    day = datetime.now(timezone.utc) - timedelta(days=d)
    p = OUT / f"ticks_{day.strftime('%Y%m%d')}.parquet"
    if p.exists():
        continue
    s = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    e = s + timedelta(days=1)
    r = mt5.copy_ticks_range("XAUUSD", s, e, mt5.COPY_TICKS_ALL)
    if r is None or len(r) == 0:
        print(day.date(), "no ticks", flush=True)
        continue
    df = pd.DataFrame(r)
    df["ts_utc"] = pd.to_datetime(df["time_msc"], unit="ms", utc=True)
    df = df.drop(columns=["time_msc", "time", "flags_real"] if "flags_real" in df else ["time_msc", "time"])
    df = df.sort_values("ts_utc").drop_duplicates(subset="ts_utc")
    df.to_parquet(p, index=False)
    print(day.date(), len(df), flush=True)
mt5.shutdown()
print("fxtm ticks pull done")
