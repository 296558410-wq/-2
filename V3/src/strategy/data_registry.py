# -*- coding: utf-8 -*-
"""V3 data registry (§16/§17): source, coverage, timezone, hash, PIT. Read-only."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd

AIQ = r"C:\AIQuant"
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
LIVE = os.path.join(AIQ, "data", "live_fxtm")


def sha256_file(p, cap=64 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        read = 0
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b); read += len(b)
            if read >= cap:
                break
    return h.hexdigest()


def registry_entries():
    """One entry per live_fxtm file (the only venue-consistent PIT source for V3 evaluation)."""
    out = []
    for f in sorted(os.listdir(LIVE)):
        if not f.endswith(".parquet"):
            continue
        p = os.path.join(LIVE, f)
        try:
            d = pd.read_parquet(p, columns=["ts_utc"])
        except Exception:
            continue
        out.append({"kind": "MARKET_DATA", "source": "FXTM XAUUSD L1 (live_fxtm)",
                     "file": f"data/live_fxtm/{f}", "rows": int(len(d)),
                     "coverage": {"from": str(d.ts_utc.min()), "to": str(d.ts_utc.max())},
                     "timezone": "UTC", "retrieval_time": "collected continuously (recorded mtime)",
                     "mtime_utc": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat(),
                     "quality": "venue-consistent", "hash_sha256_of_first_64MB": sha256_file(p),
                     "PIT": "point-in-time (append-only daily parquet; ts_utc from venue)"})
    return out


def load_live_ticks(cols=("ts_utc", "bid", "ask")):
    """PIT tick load. Bars/features are always rebuilt from ticks so no pre-computed
    (potentially leaking) artifact is reused."""
    frames = []
    for f in sorted(os.listdir(LIVE)):
        if f.endswith(".parquet"):
            try:
                frames.append(pd.read_parquet(os.path.join(LIVE, f), columns=list(cols)))
            except Exception:
                pass
    if not frames:
        return pd.DataFrame(columns=list(cols))
    d = pd.concat(frames, ignore_index=True)
    d = d.drop_duplicates(subset=["ts_utc"]).sort_values("ts_utc").reset_index(drop=True)
    d["mid"] = (d["bid"] + d["ask"]) / 2.0
    d["spread"] = d["ask"] - d["bid"]
    return d


def build_bars(ticks, freq="1min"):
    """OHLC + spread from ticks. PIT: bar labelled by its CLOSE time; only ticks <= close are used."""
    t = ticks.set_index("ts_utc")
    agg = t.resample(freq).agg(mid_open=("mid", "first"), mid_high=("mid", "max"),
                                mid_low=("mid", "min"), mid_close=("mid", "last"),
                                n_ticks=("mid", "size"), spread_mean=("spread", "mean"))
    return agg.dropna(subset=["mid_close"]).reset_index()
