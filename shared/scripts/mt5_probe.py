# -*- coding: utf-8 -*-
"""mt5_probe.py — 只读探测：连接状态、symbol、服务器时区、历史深度。

安全：只用 copy_rates_*/copy_ticks_*/symbol_info（全只读），零交易函数。
"""
import sys
from datetime import datetime, timezone

import MetaTrader5 as mt5

if not mt5.initialize():
    print("initialize failed:", mt5.last_error())
    sys.exit(1)
print("MT5 connected; version:", mt5.version())

info = mt5.symbol_info("XAUUSD")
print("XAUUSD exists:", info is not None)
if info:
    print("  point:", info.point, "| digits:", info.digits, "| trade_mode:", info.trade_mode)
    print("  session:", info.session_deals)

# 最新 M1 bar 时间 vs 当前 UTC → 推断服务器时区偏移
now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 3)
if rates is None or len(rates) == 0:
    print("no M1 rates:", mt5.last_error())
    mt5.shutdown()
    sys.exit(1)
import pandas as pd
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
last = df["time"].iloc[-1]
print("last M1 bar (server):", last, "| now UTC:", now_utc)
print("server-utc offset hours:", int((last.tz_localize("UTC") - now_utc).total_seconds() // 3600))

# 历史深度探测：从 2015 起拉取（检查最早可用）
for tf_name, tf in (("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("H1", mt5.TIMEFRAME_H1)):
    r = mt5.copy_rates_range("XAUUSD", tf, datetime(2015, 1, 1), now_utc)
    if r is None:
        print(tf_name, "ERROR", mt5.last_error())
        continue
    d = pd.DataFrame(r)
    d["time"] = pd.to_datetime(d["time"], unit="s")
    print(f"{tf_name}: rows={len(d):,}  range={d['time'].iloc[0]} -> {d['time'].iloc[-1]}")
    if len(d) > 1000:
        d.to_parquet(f"C:/AIQuant/data/staging_mt5_XAUUSD_{tf_name}.parquet", index=False)
mt5.shutdown()
print("probe done (read-only)")
