# -*- coding: utf-8 -*-
"""Standalone broker read (hardened). Writes reports/BROKER_READ.json in pipeline key format.
All optional attributes are read via getattr to tolerate MT5 API version differences."""
from __future__ import annotations

import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")
os.makedirs(REPORTS, exist_ok=True)
OUT = os.path.join(REPORTS, "BROKER_READ.json")
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"


def g(obj, name, default=None):
    try:
        return getattr(obj, name, default)
    except Exception:  # noqa: BLE001
        return default


def run():
    res = {"err": None}
    try:
        import MetaTrader5 as mt5
        ok = False
        for i in range(60):
            try:
                ok = mt5.initialize(path=TERMINAL)
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                break
            time.sleep(4)
        ai = mt5.account_info()
        ti = mt5.terminal_info()
        ps_ = mt5.positions_get()
        os_ = mt5.orders_get()
        res = {"CONNECTED": bool(ok),
                "login": (str(g(ai, "login")) if ai and g(ai, "login") else None),
                "server": (g(ai, "server") if ai else None),
                "currency": (g(ai, "currency") if ai else None),
                "leverage": (g(ai, "leverage") if ai else None),
                "balance": (g(ai, "balance") if ai else None),
                "equity": (g(ai, "equity") if ai else None),
                "free_margin": (g(ai, "margin_free") if ai else None),
                "trade_allowed": (g(ti, "trade_allowed") if ti else None),
                "trade_expert": (g(ti, "trade_expert", "UNAVAILABLE") if ti else None),
                "connected": (g(ti, "connected") if ti else None),
                "open_positions": (None if ps_ is None else len(ps_)),
                "pending_orders": (None if os_ is None else len(os_)),
                "pos_ids": ([g(p, "ticket") for p in ps_] if ps_ else []),
                "ord_ids": ([g(o, "ticket") for o in os_] if os_ else []),
                "last_error": (mt5.last_error() if hasattr(mt5, "last_error") else None)}
        try:
            mt5.shutdown()
        except Exception:  # noqa: BLE001
            pass
    except Exception as ex:  # noqa: BLE001
        res = {"err": type(ex).__name__ + ":" + str(ex)[:150]}
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(res, ensure_ascii=True)[:600])


if __name__ == "__main__":
    run()
