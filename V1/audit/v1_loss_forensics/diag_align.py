# -*- coding: utf-8 -*-
"""Per-day tick-archive alignment check: compare archive prices vs the ENGINE's DECISION snapshots
(ground truth at true UTC times) at label T, T-3h, T+3h. Read-only."""
import json, os
import numpy as np
import pandas as pd

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_upgrade"
TICKS = r"C:\AIQuant\data\live_fxtm"
L = [json.loads(l) for l in open(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
dec = [e for e in L if e.get("event") == "DECISION" and (e.get("snapshot") or {}).get("bid")]

def load(day):
    p = os.path.join(TICKS, f"ticks_{day}.parquet")
    t = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
    return t["ts_utc"].astype("int64").to_numpy(), t["bid"].to_numpy(np.float64), t["ask"].to_numpy(np.float64)

cache = {}
def get(day):
    if day not in cache:
        cache[day] = load(day)
    return cache[day]

OFFS = (-10800_000, 0, 10800_000)  # -3h, 0, +3h in ms
print("day | n | per-offset mean|mid-snap| (ms candidates)")
for day in ("20260928", "20260929", "20260930", "20261001", "20261002"):
    ds = [d for d in dec if d["ts_utc"][:10].replace("-", "") == day]
    if len(ds) < 3:
        print(day, "no snapshots"); continue
    sample = ds[:: max(1, len(ds) // 8)][:8]
    ts, b, a = get(day)
    rows = []
    for d in sample:
        t_ms = int(pd.Timestamp(d["ts_utc"]).timestamp() * 1000)
        snap_mid = (d["snapshot"]["bid"] + d["snapshot"]["ask"]) / 2
        res = []
        for off in OFFS:
            tt = t_ms + off
            i = np.searchsorted(ts, tt, side="left")
            cand = []
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(ts) and abs(int(ts[j]) - tt) <= 10_000:
                    cand.append(abs((b[j] + a[j]) / 2 - snap_mid))
            res.append(round(min(cand), 3) if cand else None)
        rows.append({"ts": d["ts_utc"][11:19], "snap": round(snap_mid, 2), "d_-3h": res[0], "d_0": res[1], "d_+3h": res[2]})
    ok = {o: 0 for o in OFFS}
    for r in rows:
        for o, k in zip(OFFS, ("d_-3h", "d_0", "d_+3h")):
            if r[k] is not None and r[k] < 1.0:
                ok[o] += 1
    print(day, "|", len(rows), "| -3h:", ok[-10800_000], " 0:", ok[0], " +3h:", ok[10800_000])
    for r in rows[:4]:
        print("   ", r)
