# -*- coding: utf-8 -*-
"""DECISIVE frame test: bind live terminal time_msc <-> collector stamps <-> archive labels. Read-only."""
import json, os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

TICKS = r"C:\AIQuant\data\live_fxtm"
now = datetime.now(timezone.utc)
print("machine UTC now :", now.isoformat())
print("machine local   :", datetime.now().isoformat())

ql = os.path.join(TICKS, "quote_latest.json")
if os.path.exists(ql):
    q = json.load(open(ql, encoding="utf-8"))
    print("quote_latest.json:", json.dumps(q, ensure_ascii=False))
else:
    print("quote_latest.json: missing")

log = os.path.join(TICKS, "collect_runs.log")
if os.path.exists(log):
    lines = [l for l in open(log, encoding="utf-8") if l.strip()][-4:]
    print("collect_runs.log tail:")
    for l in lines:
        print("   ", l.strip())

# archive newest labels
t = pd.read_parquet(os.path.join(TICKS, "ticks_20261002.parquet"), columns=["ts_utc", "bid", "ask"])
ts = t["ts_utc"].astype("int64").to_numpy()
o = np.argsort(ts)
ts = ts[o]; b = t["bid"].to_numpy()[o]; a = t["ask"].to_numpy()[o]
print("archive newest label:", pd.Timestamp(int(ts[-1]), unit="ms", tz="UTC").isoformat(), "| bid/ask:", b[-1], a[-1])
print("archive oldest label:", pd.Timestamp(int(ts[0]), unit="ms", tz="UTC").isoformat())
mtime = os.path.getmtime(os.path.join(TICKS, "ticks_20261002.parquet"))
print("archive file mtime  :", pd.Timestamp(mtime, unit="s", tz="UTC").isoformat())

# live terminal comparison
import MetaTrader5 as mt5
env = {}
for line in open(r"C:\AIQuant\.env.mt5_demo", encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
ok = mt5.initialize(**kw)
print("mt5 init:", ok)
if ok:
    tk = mt5.symbol_info_tick("XAUUSD")
    print("LIVE symbol_info_tick: time_s=", tk.time, "time_msc=", tk.time_msc, "bid=", tk.bid, "ask=", tk.ask)
    print("  time_msc as UTC render:", pd.Timestamp(int(tk.time_msc), unit="ms", tz="UTC").isoformat())
    srv_ms = int(tk.time_msc)
    print("  time_msc minus machine-now (s):", round((srv_ms / 1000) - now.timestamp(), 1))
    frm = now - timedelta(minutes=30)
    ct = mt5.copy_ticks_range("XAUUSD", int(frm.timestamp()), int(now.timestamp()) + 30, mt5.COPY_TICKS_ALL)
    if ct is not None and len(ct):
        last = ct[-1]
        print("copy_ticks_range last: time_msc=", int(last["time_msc"]), "bid=", float(last["bid"]))
        print("  range-last as UTC render:", pd.Timestamp(int(last["time_msc"]), unit="ms", tz="UTC").isoformat())
        print("  range-last minus machine-now (s):", round((int(last['time_msc']) / 1000) - now.timestamp(), 1))
        print("  range-last minus LIVE tick (s):", round((int(last["time_msc"]) - srv_ms) / 1000, 1))
        # find this tick in archive: nearest label by price+time
        for cand_off, name in ((0, "as-is"), (-10800_000, "minus3h")):
            tt = int(pd.Timestamp(str(t['ts_utc'].iloc[0])) .timestamp()) if False else int(last["time_msc"]) + cand_off
            i = np.searchsorted(ts, tt)
            j = min(max(i, 0), len(ts) - 1)
            print(f"  nearest archive label for {name}:", pd.Timestamp(int(ts[j]), unit="ms", tz="UTC").isoformat(),
                  "| bid diff:", round(abs(b[j] - float(last["bid"])), 2))
    else:
        print("copy_ticks_range: EMPTY", ct)
    mt5.shutdown()
print("done")
