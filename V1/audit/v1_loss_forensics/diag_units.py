# -*- coding: utf-8 -*-
"""Diagnose the structure-features bug: check resample index dtype & close_ms units."""
import numpy as np
import pandas as pd

m1 = pd.read_parquet(r"C:\AIQuant\research\hermes\trader_v1\audit\v1_loss_forensics\m1_bars_snapshot.parquet")
print("m1 index dtype:", m1.index.dtype)
m1.index = m1.index - pd.Timedelta(hours=3)
print("after -3h:", m1.index[-2:].tolist())
g = m1.resample("15min", label="left", closed="left").agg(
    {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
print("resampled dtype:", g.index.dtype)
v = g.index.astype("int64")
print("astype(int64) last3:", v[-3:].tolist())
close_ms_old = (v // 10 ** 6) + 900_000
print("old close_ms last3:", close_ms_old[-3:].tolist())
close_ms_new = ((g.index - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1ms")).astype("int64") + 900_000
print("new close_ms last3:", close_ms_new[-3:].tolist())
cutoff = int(pd.Timestamp("2026-10-01T14:33:03+00:00").timestamp() * 1000)
print("cutoff(ms):", cutoff)
print("old filter keeps:", int((close_ms_old <= cutoff).sum()), "/", len(g))
print("new filter keeps:", int((close_ms_new <= cutoff).sum()), "/", len(g))
