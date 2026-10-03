# -*- coding: utf-8 -*-
"""mt5_pull_final.py — 只读全量拉取：按 TF 逐月 copy_rates_range（避免越界 -2）。
输出服务器时间 parquet → 后续统一转 UTC。
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

OUT = Path("C:/AIQuant/data/staging_mt5")
SYMBOL = "XAUUSD"

# (tf, 起始年月) —— 由探测确定
PLAN = {
    "M1": ("2026-05", mt5.TIMEFRAME_M1),
    "M5": ("2025-12", mt5.TIMEFRAME_M5),
    "H1": ("2025-12", mt5.TIMEFRAME_H1),
}

if not mt5.initialize():
    print("init failed:", mt5.last_error())
    sys.exit(1)

now = datetime.now()


def months_between(start_ym: str):
    y, m = int(start_ym[:4]), int(start_ym[5:7])
    out = []
    while (y, m) <= (now.year, now.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out


for tf_name, (start_ym, tf) in PLAN.items():
    parts = []
    for ym in months_between(start_ym):
        y, m = int(ym[:4]), int(ym[5:7])
        s = datetime(y, m, 1)
        e = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
        r = None
        for attempt in range(2):
            r = mt5.copy_rates_range(SYMBOL, tf, s, e)
            if r is not None and len(r):
                break
            time.sleep(2)
        if r is None or len(r) == 0:
            print(f"  {tf_name} {ym}: no data ({mt5.last_error()})", flush=True)
            continue
        d = pd.DataFrame(r)
        d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
        parts.append(d)
        print(f"  {tf_name} {ym}: {len(d):,}", flush=True)
        time.sleep(0.3)
    if not parts:
        print(f"[fail] {tf_name}")
        continue
    full = pd.concat(parts, ignore_index=True)
    full = full.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    p = OUT / f"XAUUSD_{tf_name}_server.parquet"
    full.to_parquet(p, index=False)
    print(f"[ok] {tf_name}: {len(full):,} rows {full['time'].iloc[0]} -> {full['time'].iloc[-1]} -> {p}", flush=True)

mt5.shutdown()
print("final pull done (read-only)")
