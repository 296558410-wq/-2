"""DOM authenticity test (task §十二: true-vs-fake L2) — READ-ONLY.

Question: is the FXTM XAUUSD 10-level book a GENUINE order-by-order depth pool,
or a broker-published AGGREGATED/SYNTHETIC ladder (which would be unusable for
true queue / OFI research)?

Method (descriptive only; no alpha search):
  capture N snapshots, and for each record the (bid sizes) and (ask sizes) ladders.
  A genuine book has varied, event-driven sizes per level and asymmetric sums.
  A synthetic profile shows a small set of recurring, symmetric ladders.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import time

import MetaTrader5 as mt5

V3_TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
SYMBOL = "XAUUSD"
N = 60
POLL = 0.3
HERE = os.path.dirname(os.path.abspath(__file__))


def _row(x):
    try:
        return x._asdict()
    except Exception:
        pass
    try:
        return {n: x[n] for n in x.dtype.names}
    except Exception:
        return None


def main():
    res = {"schema": "mt5_dom_authenticity/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "order_send_called": False, "n_requested": N}
    if not mt5.initialize(path=V3_TERMINAL):
        res["error"] = str(mt5.last_error()); _dump(res); return
    try:
        mt5.market_book_add(SYMBOL)
        ladders = collections.Counter()
        sym_flags = 0
        n = 0
        spread_vals = []
        to = time.time() + N * POLL
        while time.time() < to:
            b = mt5.market_book_get(SYMBOL)
            if b is not None and len(b):
                rr = [r for r in (_row(x) for x in list(b)) if r is not None]
                bids = sorted([(r["price"], r["volume"]) for r in rr if r["type"] == 2], reverse=True)
                asks = sorted([(r["price"], r["volume"]) for r in rr if r["type"] == 1])
                bs = tuple(v for _, v in bids)
                as_ = tuple(v for _, v in asks)
                ladders[(bs, as_)] += 1
                n += 1
                if sum(bs) == sum(as_):
                    sym_flags += 1
                if bids and asks:
                    spread_vals.append(round(asks[0][0] - bids[0][0], 3))
            time.sleep(POLL)
        res["snapshots"] = n
        res["distinct_ladders"] = len(ladders)
        res["top_ladders"] = [{"bid_sizes": list(k[0]), "ask_sizes": list(k[1]), "count": c}
                              for k, c in ladders.most_common(5)]
        res["symmetric_sum_fraction"] = round(sym_flags / n, 4) if n else None
        res["spread_values"] = sorted(set(spread_vals))[:10]
        res["verdict"] = ("SYNTHETIC_OR_AGGREGATED_PROFILE"
                          if (n and len(ladders) <= max(3, n // 10) and sym_flags / n > 0.5)
                          else "VARIED_PLAUSIBLE_DEPTH")
        mt5.market_book_release(SYMBOL)
    finally:
        mt5.shutdown()
    _dump(res)


def _dump(o):
    with open(os.path.join(HERE, "mt5_dom_authenticity_result.json"), "w", encoding="utf-8") as f:
        json.dump(o, f, indent=1, default=str)
    print(json.dumps(o, indent=1, default=str)[:1800])


if __name__ == "__main__":
    main()
