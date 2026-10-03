"""Bid/ask imbalance.

Depth/size imbalance requires sizes -> DATA_GAP on this feed.
No depth-free substitute is silently reported as "imbalance".
"""
from __future__ import annotations


def size_imbalance(bid_size, ask_size):
    if bid_size is None or ask_size is None:
        return None, "DATA_GAP(no sizes)"
    return None, "DATA_GAP(requires L2 sizes)"


def depth_imbalance_status(volume_nonzero_frac):
    return "DATA_GAP(sizes identically zero)" if volume_nonzero_frac == 0 else "AVAILABLE"
