# -*- coding: utf-8 -*-
"""Read-only account/position check (no order of any kind)."""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ENV = r"C:\AIQuant\.env.mt5_demo"
env = {}
for line in open(ENV, encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

import MetaTrader5 as mt5

kw = {"login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
ok = mt5.initialize(**kw)
print("init:", ok, mt5.last_error())
ai = mt5.account_info()
pos = mt5.positions_get() or []
print("account:", ai.login, ai.server, "balance", ai.balance, "equity", ai.equity)
print("open_positions:", len(pos))
for p in pos:
    print("  POS", p.ticket, p.symbol, "type", p.type, "vol", p.volume, "magic", p.magic, "profit", round(p.profit, 2))
deals = mt5.history_deals_get(0, 9999999999) or []
for d in list(deals)[-4:]:
    print("  DEAL", d.ticket, d.symbol, "entry", d.entry, "vol", d.volume, "price", d.price,
          "profit", round(d.profit, 2), "magic", d.magic, "|", d.comment)
mt5.shutdown()
