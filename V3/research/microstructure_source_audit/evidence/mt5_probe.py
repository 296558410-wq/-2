"""MT5 read-only capability probe — V3-HFT-MICROSTRUCTURE-DATA-SOURCE-AUDIT-001.

READ-ONLY. Calls only: initialize(path=...), terminal_info, account_info, symbol_info,
symbol_info_tick, copy_ticks_range, market_book_add/get/release, shutdown.
Places NO orders. Does NOT change any MT5 instance config.

Distinguishes "API theoretically supports" from "FXTM actually receives".
"""
from __future__ import annotations

import datetime as dt
import json
import os

import MetaTrader5 as mt5

V3_TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
SYMBOL = "XAUUSD"
OUT = os.path.dirname(os.path.abspath(__file__))


def main():
    res = {"schema": "mt5_capability_probe/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "terminal_path": V3_TERMINAL, "symbol": SYMBOL, "order_send_called": False}
    ok = mt5.initialize(path=V3_TERMINAL)
    res["initialize_ok"] = bool(ok)
    if not ok:
        res["initialize_error"] = str(mt5.last_error())
        _dump(res)
        return
    try:
        ti = mt5.terminal_info()
        ai = mt5.account_info()
        res["terminal"] = {"connected": bool(getattr(ti, "connected", None)),
                           "name": getattr(ti, "name", None), "company": getattr(ti, "company", None),
                           "build": getattr(ti, "build", None)} if ti else None
        res["account"] = {"login": getattr(ai, "login", None), "server": getattr(ai, "server", None),
                          "currency": getattr(ai, "currency", None)} if ai else None

        mt5.symbol_select(SYMBOL, True)
        si = mt5.symbol_info(SYMBOL)
        if si is None:
            res["symbol_info"] = "DATA_GAP (symbol_info returned None)"
        else:
            d = si._asdict()
            res["symbol_info_fields"] = sorted(d.keys())
            # bid/ask exist? sizes?
            res["symbol_info_selected"] = {
                "bid": d.get("bid"), "ask": d.get("ask"), "spread": d.get("spread"),
                "digits": d.get("digits"), "point": d.get("point"),
                "trade_tick_value": d.get("trade_tick_value"), "trade_tick_size": d.get("trade_tick_size"),
                "volume_min": d.get("volume_min"), "volume_step": d.get("volume_step"),
                "session_deals": d.get("session_deals"), "session_buy_orders": d.get("session_buy_orders"),
                "session_sell_orders": d.get("session_sell_orders"),
                "depth_related_fields_present": [k for k in d if "depth" in k.lower() or "book" in k.lower()],
            }
        tk = mt5.symbol_info_tick(SYMBOL)
        res["symbol_info_tick"] = ({"bid": getattr(tk, "bid", None), "ask": getattr(tk, "ask", None),
                                    "last": getattr(tk, "last", None), "volume": getattr(tk, "volume", None),
                                    "volume_real": getattr(tk, "volume_real", None),
                                    "flags": getattr(tk, "flags", None)} if tk else None)

        # ticks over the last 30 minutes
        to = dt.datetime.now(dt.timezone.utc)
        frm = to - dt.timedelta(minutes=30)
        ticks = mt5.copy_ticks_range(SYMBOL, frm, to, mt5.COPY_TICKS_ALL)
        if ticks is None:
            res["ticks"] = {"status": "DATA_GAP", "error": str(mt5.last_error())}
        else:
            import numpy as np
            vol = ticks["volume"] if "volume" in ticks.dtype.names else None
            vr = ticks["volume_real"] if "volume_real" in ticks.dtype.names else None
            last = ticks["last"] if "last" in ticks.dtype.names else None
            res["ticks"] = {
                "n": int(len(ticks)),
                "fields": list(ticks.dtype.names),
                "window_utc": [frm.isoformat(), to.isoformat()],
                "volume_nonzero": int(np.count_nonzero(vol)) if vol is not None else None,
                "volume_real_nonzero": int(np.count_nonzero(vr)) if vr is not None else None,
                "last_nonzero": int(np.count_nonzero(last)) if last is not None else None,
            }
        # Market Depth / DOM
        book = {"add_ok": None, "book_get": None, "n_levels": None, "error": None}
        try:
            book["add_ok"] = bool(mt5.market_book_add(SYMBOL))
            b = mt5.market_book_get(SYMBOL)
            if b is None:
                book["book_get"] = "NONE (no DOM published by broker feed)"
                book["error"] = str(mt5.last_error())
            else:
                book["book_get"] = "RETURNED"
                book["n_levels"] = int(len(b))
            mt5.market_book_release(SYMBOL)
        except Exception as e:                                  # noqa: BLE001
            book["error"] = f"{type(e).__name__}: {e}"
        res["market_depth"] = book
    finally:
        mt5.shutdown()
    _dump(res)


def _dump(res):
    with open(os.path.join(OUT, "mt5_probe_result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
