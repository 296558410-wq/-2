"""DOM (Market Depth) probe with proper event wait — READ-ONLY, no orders.

Why: `symbol_info().ticks_bookdepth = 10` DECLARES depth, but an immediate
`market_book_get` returned 0 levels, which may be a subscription-timing artifact.
This probe subscribes, then polls for up to `SECONDS` and reports the MAXIMUM number
of levels ever seen, plus a sample book and the last error.

Only read-only calls: initialize/market_book_add/market_book_get/market_book_release/shutdown.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

import MetaTrader5 as mt5

V3_TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
SYMBOL = "XAUUSD"
SECONDS = 20.0
HERE = os.path.dirname(os.path.abspath(__file__))


def _dom_row(x):
    try:
        return x._asdict()
    except Exception:
        pass
    try:
        return {n: x[n] for n in x.dtype.names}
    except Exception:
        return str(x)


def main():
    out = {"schema": "mt5_dom_wait_probe/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "symbol": SYMBOL, "wait_seconds": SECONDS, "order_send_called": False, "samples": []}
    if not mt5.initialize(path=V3_TERMINAL):
        out["initialize_error"] = str(mt5.last_error())
        _dump(out); return
    try:
        si = mt5.symbol_info(SYMBOL)
        out["declared_bookdepth"] = getattr(si, "ticks_bookdepth", None)
        out["add_ok"] = bool(mt5.market_book_add(SYMBOL))
        max_levels = 0
        first_book = None
        t0 = time.time()
        while time.time() - t0 < SECONDS:
            b = mt5.market_book_get(SYMBOL)
            n = 0 if b is None else len(b)
            if n > max_levels:
                max_levels = n
                if first_book is None and b is not None:
                    first_book = [_dom_row(x) for x in list(b)[:5]]
            out["samples"].append({"t_s": round(time.time() - t0, 1), "levels": n})
            time.sleep(1.0)
        out["max_levels_seen"] = max_levels
        out["sample_book"] = first_book
        out["last_error"] = str(mt5.last_error())
        out["verdict"] = ("DOM_AVAILABLE" if max_levels > 0
                          else "DOM_EMPTY_NO_BROKER_DEPTH")
        mt5.market_book_release(SYMBOL)
    finally:
        mt5.shutdown()
    _dump(out)


def _dump(o):
    with open(os.path.join(HERE, "mt5_dom_wait_result.json"), "w", encoding="utf-8") as f:
        json.dump(o, f, indent=1, default=str)
    print(json.dumps({k: o[k] for k in ("declared_bookdepth", "add_ok", "max_levels_seen",
                                        "verdict", "last_error")}, indent=1, default=str))
    print("samples:", o["samples"][:6], "...", o["samples"][-3:])


if __name__ == "__main__":
    main()
