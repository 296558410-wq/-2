# -*- coding: utf-8 -*-
"""Tick-quality diagnostic for the loss-forensics MFE/MAE values (instrument-first check)."""
import json, os
import numpy as np
import pandas as pd

TICKS = r"C:\AIQuant\data\live_fxtm"
OUT = r"C:\AIQuant\research\hermes\trader_v1\audit\v1_loss_forensics"
db = {}
for line in open(os.path.join(OUT, "TRADE_ERROR_DATABASE.jsonl"), encoding="utf-8"):
    r = json.loads(line)
    db[r["position_id"]] = r

def load(day):
    p = os.path.join(TICKS, f"ticks_{day}.parquet")
    t = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
    return t["ts_utc"].astype("int64").to_numpy(), t["bid"].to_numpy(np.float64), t["ask"].to_numpy(np.float64)

def check(pid):
    r = db[pid]
    e = pd.Timestamp(r["entry"]["ts_utc"]).tz_convert("UTC")
    x = pd.Timestamp(r["exit"]["ts_utc"]).tz_convert("UTC")
    print("===", pid, "entry", e.strftime("%m-%d %H:%M:%S"), "exit", x.strftime("%m-%d %H:%M:%S"),
          "| mfe", r["path"]["mfe_r"], "mae", r["path"]["mae_r"], "side", r["entry"]["side"],
          "| risk", round(abs(r["entry"]["price"] - (r["decision"]["order_intent"].get("sl") or 0)), 2))
    days = sorted({e.strftime("%Y%m%d"), x.strftime("%Y%m%d")})
    ts, b, a = [], [], []
    for d in days:
        t, bb, aa = load(d)
        ts.append(t); b.append(bb); a.append(aa)
    ts = np.concatenate(ts); b = np.concatenate(b); a = np.concatenate(a)
    ems = int(e.timestamp() * 1000); xms = int(x.timestamp() * 1000)
    m = (ts >= ems) & (ts <= xms)
    n = int(m.sum())
    print("  ticks in window:", n)
    if n == 0:
        return
    bb, aa = b[m], a[m]
    print("  bid min/max:", round(bb.min(), 2), round(bb.max(), 2), "| ask min/max:", round(aa.min(), 2), round(aa.max(), 2))
    print("  crossed(ask<bid):", int((aa < bb).sum()), "| spread>2.0:", int(((aa - bb) > 2.0).sum()),
          "| spread<0:", int(((aa - bb) < 0).sum()))
    mid = (bb + aa) / 2
    d = np.abs(np.diff(mid))
    big = np.argsort(d)[-5:]
    rows = []
    for i in big:
        rows.append((round(float(d[i]), 2), pd.to_datetime(int(ts[m][i]), unit="ms", utc=True).strftime("%H:%M:%S.%f")[:12]))
    print("  top5 |mid jumps|:", rows)
    # recompute MFE/MAE with a simple outlier filter: drop ticks where spread<=0 or |mid-median|>5*ATR-ish (here 30 pts)
    med = np.median(mid)
    keep = (aa > bb) & (np.abs(mid - med) < 30)
    if keep.sum() > 10:
        if r["entry"]["side"] == "SHORT":
            fav = aa[keep].min(); adv = aa[keep].max()
        else:
            fav = bb[keep].max(); adv = bb[keep].min()
        risk = abs(r["entry"]["price"] - (r["decision"]["order_intent"].get("sl") or 0))
        print("  filtered mfe/mae:", round(abs(fav - r["entry"]["price"]) / risk, 3), round(abs(adv - r["entry"]["price"]) / risk, 3),
              f"(kept {int(keep.sum())}/{n})")

for pid in ("2378067697", "2378322488", "2378224663", "2377901575", "2377762527"):
    check(pid)
    print()
