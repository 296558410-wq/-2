# -*- coding: utf-8 -*-
"""diag_units2.py — (1) unit-test close_ms conversions; (2) confirm archive content-lag vs M1 bars."""
import numpy as np
import pandas as pd

HERE = r"C:\AIQuant\research\hermes\trader_v1\audit\v1_loss_forensics"
m1 = pd.read_parquet(HERE + r"\m1_bars_snapshot.parquet")
print("m1 index dtype:", m1.index.dtype, "| last:", m1.index[-1])

# --- conversion candidates for close_ms ---
g = m1.resample("15min", label="left", closed="left").agg(
    {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
old = (g.index.astype("int64") // 10 ** 6) + 900_000
new = np.asarray(g.index.values, dtype="datetime64[ms]").astype(np.int64) + 900_000
cutoff = int(pd.Timestamp("2026-10-01T14:33:03+00:00").timestamp() * 1000)
print("old close_ms last2:", old[-2:].tolist(), "| keeps:", int((old <= cutoff).sum()))
print("new close_ms last2:", new[-2:].tolist(), "| keeps:", int((new <= cutoff).sum()), "of", len(g))

# --- archive content lag check ---
t = pd.read_parquet(r"C:\AIQuant\data\live_fxtm\ticks_20261002.parquet", columns=["ts_utc", "bid", "ask"])
tail = t.tail(3)
print("archive tail stamps:", [str(x) for x in tail["ts_utc"].tolist()])
print("archive tail bids :", tail["bid"].tolist())
print("archive last-200 bid range:", round(t["bid"].tail(200).min(), 2), "-", round(t["bid"].tail(200).max(), 2))

m1raw = pd.read_parquet(HERE + r"\m1_bars_snapshot.parquet")  # raw = server frame
sel1 = m1raw.loc["2026-10-02 11:35":"2026-10-02 11:40"]
sel2 = m1raw.loc["2026-10-02 14:35":"2026-10-02 14:40"]
print("bars(raw) 11:35-11:40 closes:", sel1["close"].tolist())
print("bars(raw) 14:35-14:40 closes:", sel2["close"].tolist())
