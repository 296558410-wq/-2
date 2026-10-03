# -*- coding: utf-8 -*-
"""Definitive per-decision alignment mapping: for every ledger DECISION (known true-UTC + snapshot mid),
find the archive tick-events best matching offset in {-3h, +1h, 0, +3h} against each day file.
Outputs a table by date+hour to locate the exact convention / break point. Read-only."""
import json, os
import numpy as np
import pandas as pd

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_upgrade"
TICKS = r"C:\AIQuant\data\live_fxtm"
L = [json.loads(l) for l in open(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
DEC = [e for e in L if e.get("event") == "DECISION" and (e.get("snapshot") or {}).get("bid")]
print("decisions:", len(DEC))

files = sorted(os.listdir(TICKS))
cache = {}
def load(fn):
    if fn not in cache:
        t = pd.read_parquet(os.path.join(TICKS, fn), columns=["ts_utc", "bid", "ask"])
        ts = t["ts_utc"].astype("int64").to_numpy()
        o = np.argsort(ts, kind="mergesort")
        cache[fn] = (ts[o], t["bid"].to_numpy(np.float64)[o], t["ask"].to_numpy(np.float64)[o])
    return cache[fn]

OFFS = {"-3h": -10800_000, "+1h": 3600_000, "0": 0, "+3h": 10800_000}
rows = []
for d in DEC:
    t_ms = int(pd.Timestamp(d["ts_utc"]).timestamp() * 1000)
    snap_mid = (d["snapshot"]["bid"] + d["snapshot"]["ask"]) / 2.0
    best = None
    for off_name, off in OFFS.items():
        tt = t_ms + off
        day = pd.Timestamp(tt, unit="ms", tz="UTC").strftime("%Y%m%d")
        # search in the file for that day AND the neighbours (chunks span days)
        for fn in files:
            if not fn.startswith("ticks_"):
                continue
            ts, b, a = load(fn)
            if len(ts) == 0 or tt < ts[0] - 10_000 or tt > ts[-1] + 10_000:
                continue
            i = np.searchsorted(ts, tt, side="left")
            cand = []
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(ts):
                    dt_ms = abs(int(ts[j]) - tt)
                    if dt_ms <= 15_000:
                        cand.append((abs((b[j] + a[j]) / 2 - snap_mid), dt_ms, int(ts[j]), (b[j], a[j])))
            if cand:
                c = min(cand)
                if best is None or c[0] < best[0]:
                    best = (c[0], off_name, fn, c[1], c[2])
    if best and best[0] < 1.0:
        rows.append({"ts": d["ts_utc"][:19], "best_off": best[1], "diff": round(best[0], 3), "file": best[3] and best[2],
                     "dt_ms": best[3]})

import collections
by_day = collections.defaultdict(collections.Counter)
by_day_off = collections.defaultdict(collections.Counter)
tot = collections.Counter()
for r in rows:
    day = r["ts"][:10]
    tot[r["best_off"]] += 1
    by_day[day][r["best_off"]] += 1
print("TOTAL matched:", dict(tot), "of", len(DEC))
for day in sorted(by_day):
    print(day, dict(by_day[day]))
# hour-level detail for 10-01 / 10-02
print()
for day in ("2026-10-01", "2026-10-02"):
    print("== hour detail", day)
    hrs = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["ts"][:10] == day:
            h = r["ts"][11:13]
            hrs[h][r["best_off"]] += 1
    for h in sorted(hrs):
        print("  ", h, "h:", dict(hrs[h]))
# file mtimes + label spans
print()
for fn in files[-6:]:
    p = os.path.join(TICKS, fn)
    ts, b, a = load(fn)
    mt = pd.Timestamp(os.path.getmtime(p), unit="s", tz="UTC")
    print(fn, "rows:", len(ts), "label span:", pd.Timestamp(int(ts[0]), unit="ms", tz="UTC").strftime("%m-%d %H:%M"),
          "->", pd.Timestamp(int(ts[-1]), unit="ms", tz="UTC").strftime("%m-%d %H:%M"),
          "| mtime:", mt.strftime("%m-%d %H:%M") + "Z")
