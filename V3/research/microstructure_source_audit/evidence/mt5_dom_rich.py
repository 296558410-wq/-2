"""Rich DOM capture — READ-ONLY, no orders.

Purpose: prove whether the FXTM XAUUSD Market Depth is GENUINE depth
(real bid/ask levels with non-zero sizes that update with the market) or a
degenerate/synthetic placeholder. Also measures snapshot update behaviour.

Only read-only calls. No order_send.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

import MetaTrader5 as mt5

V3_TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
SYMBOL = "XAUUSD"
SECONDS = 15.0
POLL = 0.2
HERE = os.path.dirname(os.path.abspath(__file__))


def rows(b):
    out = []
    for x in list(b):
        try:
            out.append(x._asdict())
        except Exception:
            try:
                out.append({n: x[n] for n in x.dtype.names})
            except Exception:
                out.append(str(x))
    return out


def main():
    res = {"schema": "mt5_dom_rich/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "order_send_called": False, "symbol": SYMBOL, "seconds": SECONDS}
    if not mt5.initialize(path=V3_TERMINAL):
        res["error"] = str(mt5.last_error()); _dump(res); return
    try:
        si = mt5.symbol_info(SYMBOL)
        res["declared_bookdepth"] = getattr(si, "ticks_bookdepth", None)
        res["symbol_bid_ask"] = [getattr(si, "bid", None), getattr(si, "ask", None)]
        mt5.market_book_add(SYMBOL)
        t0 = time.time()
        first = None
        distinct = 0
        prev_sig = None
        sizes_seen = []
        types = set()
        n_snap = 0
        while time.time() - t0 < SECONDS:
            b = mt5.market_book_get(SYMBOL)
            if b is not None and len(b):
                rr = rows(b)
                n_snap += 1
                if first is None:
                    first = rr
                for r in rr:
                    if r.get("type") is not None:
                        types.add(int(r["type"]))
                    if r.get("volume") is not None:
                        sizes_seen.append(float(r["volume"]))
                sig = tuple((r.get("type"), r.get("price"), r.get("volume")) for r in rr)
                if sig != prev_sig:
                    distinct += 1
                    prev_sig = sig
            time.sleep(POLL)
        res["snapshots_polled"] = n_snap
        res["distinct_books"] = distinct
        res["levels_per_book"] = len(first) if first else 0
        res["first_book"] = first
        res["book_types_seen"] = sorted(types)          # 1 = BOOK_TYPE_SELL(ask), 2 = BOOK_TYPE_BUY(bid)
        res["volume_min_max"] = [min(sizes_seen), max(sizes_seen)] if sizes_seen else None
        res["non_zero_size_levels"] = int(sum(1 for s in sizes_seen if s > 0))
        bids = [r for r in (first or []) if r.get("type") == 2]
        asks = [r for r in (first or []) if r.get("type") == 1]
        res["n_bid_levels"] = len(bids)
        res["n_ask_levels"] = len(asks)
        res["best_bid"] = max((r["price"] for r in bids), default=None)
        res["best_ask"] = min((r["price"] for r in asks), default=None)
        res["verdict"] = ("GENUINE_DEPTH" if (res["non_zero_size_levels"] > 0 and distinct > 1)
                          else "DEGENERATE_OR_STATIC")
        mt5.market_book_release(SYMBOL)
    finally:
        mt5.shutdown()
    _dump(res)


def _dump(o):
    with open(os.path.join(HERE, "mt5_dom_rich_result.json"), "w", encoding="utf-8") as f:
        json.dump(o, f, indent=1, default=str)
    print(json.dumps({k: o.get(k) for k in ("declared_bookdepth", "snapshots_polled", "distinct_books",
                                            "levels_per_book", "n_bid_levels", "n_ask_levels",
                                            "best_bid", "best_ask", "book_types_seen",
                                            "volume_min_max", "non_zero_size_levels", "verdict")}, indent=1))
    print("first_book:", json.dumps(o.get("first_book"), default=str)[:900])


if __name__ == "__main__":
    main()
