# -*- coding: utf-8 -*-
"""diag_lag.py — FINAL instrument check: is archive content ~3h behind wall clock?
Discriminator: compare a just-fetched range tick's price against candidate M1 bars."""
import datetime as dt, os
import numpy as np
import pandas as pd

now = dt.datetime.now(dt.timezone.utc)
print("now_true:", now.isoformat())

env = {}
for line in open(r"C:\AIQuant\.env.mt5_demo", encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5  # noqa: E402
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
assert mt5.initialize(**kw), mt5.last_error()

live = mt5.symbol_info_tick("XAUUSD")
print("LIVE bid/ask:", live.bid, live.ask, "| msc render:", pd.Timestamp(int(live.time_msc), unit="ms", tz="UTC"))

frm = now - dt.timedelta(minutes=20); to = now - dt.timedelta(minutes=10)
rt = mt5.copy_ticks_range("XAUUSD", int(frm.timestamp()), int(to.timestamp()), mt5.COPY_TICKS_ALL)
print("range n:", 0 if rt is None else len(rt))
if rt is not None and len(rt):
    last = rt[-1]
    print("range-last render:", pd.Timestamp(int(last["time_msc"]), unit="ms", tz="UTC"), "| bid:", float(last["bid"]))

bars = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, now - dt.timedelta(hours=5), now + dt.timedelta(hours=5))
ts = pd.to_datetime(bars["time"], unit="s", utc=True)
print("bars n:", len(bars), "| last bar label:", ts[-1], "| last close:", bars["close"][-1])

def bar_at(label_ms, name):
    target = pd.Timestamp(int(label_ms), unit="ms", tz="UTC")
    i = int(np.argmin(np.abs((ts - target).total_seconds())))
    print(f"  {name} [{target}] -> bar {ts[i]} close={bars['close'][i]}")
    return float(bars["close"][i])

to_ms = int(to.timestamp() * 1000)
c_b0 = bar_at(to_ms, "bar(now-10m)")
c_bp3 = bar_at(to_ms + 10_800_000, "bar(now-10m+3h)")
c_bm3 = bar_at(to_ms - 10_800_000, "bar(now-10m-3h)")
if rt is not None and len(rt):
    lb = float(last["bid"])
    print("distances: to bar(now-10m):", abs(lb - c_b0), "| to bar(+3h):", abs(lb - c_bp3), "| to bar(-3h):", abs(lb - c_bm3))

# archive tail vs its label's bar
t_arch = pd.read_parquet(r"C:\AIQuant\data\live_fxtm\ticks_20261002.parquet", columns=["ts_utc", "bid", "ask"])
tail_lab = t_arch["ts_utc"].iloc[-1]; tail_bid = float(t_arch["bid"].iloc[-1])
print("archive tail:", tail_lab, "| bid:", tail_bid)
c_ta = bar_at(int(tail_lab.timestamp() * 1000), "bar(archive-tail label)")
c_ta_m3 = bar_at(int(tail_lab.timestamp() * 1000) - 10_800_000, "bar(tail label-3h)")
c_ta_p3 = bar_at(int(tail_lab.timestamp() * 1000) + 10_800_000, "bar(tail label+3h)")
print("archive tail bid distances: to bar(label):", abs(tail_bid - c_ta), "| to bar(label-3h):", abs(tail_bid - c_ta_m3), "| to bar(label+3h):", abs(tail_bid - c_ta_p3))
mt5.shutdown()
print("done")
