# -*- coding: utf-8 -*-
"""Raw time-column inspection of the tick archive (resolve the frame convention definitively)."""
import os
import pandas as pd

TICKS = r"C:\AIQuant\data\live_fxtm"
for day in ("20260928", "20261001", "20261002"):
    p = os.path.join(TICKS, f"ticks_{day}.parquet")
    t = pd.read_parquet(p)
    print("====", day, "rows:", len(t), "cols:", list(t.columns))
    print("first 3:")
    print(t[["time", "time_msc", "utc_ms", "ts_utc", "bid", "ask"]].head(3).to_string())
    print("last 3:")
    print(t[["time", "time_msc", "utc_ms", "ts_utc", "bid", "ask"]].tail(3).to_string())
    r0 = t.iloc[0]
    print("row0 relationships: time_msc-time =", int(r0["time_msc"]) - int(r0["time"]),
          "| utc_ms - time_msc =", int(r0["utc_ms"]) - int(r0["time_msc"]),
          "| ts_utc(ms) - utc_ms =", int(pd.Timestamp(r0["ts_utc"]).value // 10**6) - int(r0["utc_ms"]))
    rl = t.iloc[-1]
    print("lastrow relationships: utc_ms - time_msc =", int(rl["utc_ms"]) - int(rl["time_msc"]),
          "| ts_utc =", rl["ts_utc"])
    print()
