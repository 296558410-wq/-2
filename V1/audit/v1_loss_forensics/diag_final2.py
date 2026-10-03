# -*- coding: utf-8 -*-
"""Final consistency pass: window tick counts (gap candidates) + manual recheck of edge trades."""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "TRADE_ERROR_DATABASE.jsonl"), encoding="utf-8") if l.strip()]
TICKS = r"C:\AIQuant\data\live_fxtm"
LABEL_TO_TRUE = 10_800_000

cache = {}
def load(fn):
    if fn not in cache:
        t = pd.read_parquet(os.path.join(TICKS, fn), columns=["ts_utc", "bid", "ask"])
        ts = t["ts_utc"].astype("int64").to_numpy() - LABEL_TO_TRUE
        o = np.argsort(ts, kind="mergesort")
        cache[fn] = (ts[o], t["bid"].to_numpy(float)[o], t["ask"].to_numpy(float)[o])
    return cache[fn]

def getwin(a_ms, b_ms):
    d0 = pd.Timestamp(a_ms, unit="ms", tz="UTC").date()
    d1 = pd.Timestamp(b_ms + LABEL_TO_TRUE, unit="ms", tz="UTC").date()
    days = pd.date_range(d0, d1 + pd.Timedelta(days=1), freq="D")
    ts, b, a = [], [], []
    for d in days:
        fn = f"ticks_{d.strftime('%Y%m%d')}.parquet"
        if os.path.exists(os.path.join(TICKS, fn)):
            t, bb, aa = load(fn)
            ts.append(t); b.append(bb); a.append(aa)
    ts = np.concatenate(ts); b = np.concatenate(b); a = np.concatenate(a)
    m = (ts >= a_ms) & (ts <= b_ms)
    o = np.argsort(ts[m])
    return ts[m][o], b[m][o], a[m][o]

print("== window tick counts (flag <200) ==")
for r in R:
    e = int(pd.Timestamp(r["entry"]["ts_utc"]).timestamp() * 1000)
    x = int(pd.Timestamp(r["exit"]["ts_utc"]).timestamp() * 1000)
    ts, b, a = getwin(e - 30_000, min(x + 8 * 3_600_000, 1791000000000))
    n = int(((ts >= e) & (ts <= x)).sum())
    flag = "  <-- LOW" if n < 200 else ""
    print(f"  {r['trade_id']} {r['outcome']:<4} window_ticks={n}{flag}")

print()
print("== manual recheck: 2378137348 (win, TP) ==")
r = next(x for x in R if x["trade_id"] == "V1T-2378137348")
e = int(pd.Timestamp(r["entry"]["ts_utc"]).timestamp() * 1000)
x = int(pd.Timestamp(r["exit"]["ts_utc"]).timestamp() * 1000)
print("  entry:", r["entry"]["ts_utc"], r["entry"]["price"], "| exit:", r["exit"]["ts_utc"], r["exit"]["price"], "| R:", r["R"], "mfe:", r["path"]["mfe_r"], "comment:", r["exit"]["comment"])
ts, b, a = getwin(e - 60_000, x + 5 * 60_000)
mm = (ts >= e) & (ts <= x)
print("  ticks in [e,x]:", int(mm.sum()), "| max bid:", b[mm].max(), "| min bid:", b[mm].min(), "| max ask:", a[mm].max())
# where does exit price first appear above?
k = np.flatnonzero((b[mm] >= float(r["exit"]["price"])) & (ts[mm] <= x))
print("  ticks with bid >= exit_price inside window:", len(k), "| first at:", pd.Timestamp(int(ts[mm][k[0]]), unit='ms', tz='UTC').isoformat() if len(k) else None)
# dump around exit
m2 = (ts >= x - 120_000) & (ts <= x + 60_000)
idx = np.flatnonzero(m2)
print("  dump around exit (first/last 8):")
for kk in list(idx[:8]) + list(idx[-8:]):
    print("   ", pd.Timestamp(int(ts[kk]), unit="ms", tz="UTC").strftime("%H:%M:%S.%f")[:12], b[kk], a[kk])

print()
print("== manual recheck: 2378208028 (win, mfe None -> gap?) ==")
r = next(x for x in R if x["trade_id"] == "V1T-2378208028")
e = int(pd.Timestamp(r["entry"]["ts_utc"]).timestamp() * 1000)
x = int(pd.Timestamp(r["exit"]["ts_utc"]).timestamp() * 1000)
print("  entry:", r["entry"]["ts_utc"], "exit:", r["exit"]["ts_utc"])
ts, b, a = getwin(e - 30 * 60_000, x + 2 * 3_600_000)
print("  ticks in raw ±window:", len(ts))
if len(ts):
    print("  data span:", pd.Timestamp(int(ts[0]), unit='ms', tz='UTC').isoformat(), "->", pd.Timestamp(int(ts[-1]), unit='ms', tz='UTC').isoformat())
    mm = (ts >= e) & (ts <= x)
    print("  ticks in [e,x]:", int(mm.sum()))
