"""Order-Flow Imbalance.

TRUE OFI (Cont-2014 style, from price/size evolution) requires
    bid, bid_size, ask, ask_size
-> DATA_GAP on this feed.

Only a TICK-RULE PROXY is computable. It is always returned as OFI_PROXY.
Calling the proxy "OFI" is forbidden by the task contract.
"""
from __future__ import annotations

import numpy as np


def true_ofi(bid, ask, bid_size, ask_size):
    if bid_size is None or ask_size is None:
        return None, "DATA_GAP(needs bid/ask sizes)"
    return None, "DATA_GAP(implementation requires L2 sizes; feed is L1_QUOTE_ONLY)"


def ofi_proxy(mid, window=20):
    """Tick-rule proxy: rolling sum of sign(delta mid) / window. NOT OFI."""
    m = np.asarray(mid, float)
    d = np.zeros(len(m))
    d[1:] = np.sign(m[1:] - m[:-1])
    cs = np.concatenate([[0.0], np.cumsum(d)])
    out = np.full(len(m), np.nan)
    w = int(window)
    out[w - 1:] = (cs[w:] - cs[:-w]) / w
    return out, "OFI_PROXY"
