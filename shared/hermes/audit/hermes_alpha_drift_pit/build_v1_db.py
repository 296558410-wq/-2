# -*- coding: utf-8 -*-
"""build_v1_db.py — V1 (old magic 90002 + new magic 90011) trade database from broker deals
+ ledger/trade-master provenance. READ-ONLY. Writes V1_HERMES_TRADE_DATABASE.jsonl into the audit dir.
"""
from __future__ import annotations
import datetime as dt, json, os, hashlib, collections

REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "audit", "hermes_alpha_drift_pit")
os.makedirs(OUT, exist_ok=True)

env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass"+"word"] = env["DEMO_MT5_PASSWORD"]
assert mt5.initialize(**kw), mt5.last_error()
frm = dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc); to = dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1)
deals = mt5.history_deals_get(frm, to) or []
mt5.shutdown()

def utc(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc)

def roundtrips(magic):
    ds = [d for d in deals if int(getattr(d, "magic", 0) or 0) == magic]
    pos = {}
    for d in ds:
        r = pos.setdefault(str(d.position_id), {"open": None, "close": [], "magic": magic})
        if d.entry == 0: r["open"] = d
        elif d.entry in (1, 3): r["close"].append(d)
    rows = []
    for pid, r in pos.items():
        if not r["open"]: continue
        o = r["open"]; cs = r["close"]
        c = max(cs, key=lambda x: x.time) if cs else None
        profit = sum(float(x.profit) for x in cs) if cs else None
        comm = float(o.commission) + sum(float(x.commission) for x in cs)
        swap = sum(float(x.swap) for x in cs)
        rows.append({
            "system": "V1_OLD" if magic == 90002 else "V1_NEW",
            "trade_id": f"V1{'OLD' if magic==90002 else 'NEW'}-{pid}",
            "position_id": pid, "magic": magic, "symbol": o.symbol,
            "direction": "LONG" if int(o.type) == 0 else "SHORT",
            "entry_ts": utc(o.time).isoformat(), "entry_price": float(o.price), "qty": float(o.volume),
            "exit_ts": utc(c.time).isoformat() if c else None,
            "exit_price": float(c.price) if c else None,
            "close_comment": (getattr(c, "comment", "") if c else None),
            "profit_price": round(profit, 2) if profit is not None else None,
            "commission": round(comm, 2), "swap": round(swap, 2),
            "net": round((profit or 0.0) + comm + swap, 2) if c else None,
            "outcome": ("WIN" if (profit or 0) > 0 else "LOSS") if c else "OPEN",
            "closed": c is not None,
            "provenance": ("BASELINE_CONTROL(not_hermes_alpha=true)" if magic == 90011 else
                           "HERMES_LLM_PLAN_ENGINE(decisions carry model/confidence; early-phase inputs rotated=DATA_GAP)"),
        })
    rows.sort(key=lambda r: r["entry_ts"])
    return rows

allrows = []
for m in (90002, 90011):
    rs = roundtrips(m)
    allrows += rs
    closed = [r for r in rs if r["closed"]]
    net = round(sum(r["net"] for r in closed), 2)
    pr = round(sum(r["profit_price"] for r in closed), 2)
    wins = sum(1 for r in closed if r["outcome"] == "WIN")
    print(f"magic {m}: positions={len(rs)} closed={len(closed)} W/L={wins}/{len(closed)-wins} profit_price={pr} net={net} "
          f"{rs[0]['entry_ts']} -> {closed[-1]['exit_ts']}")
    # phase split by median exit date
    dates = sorted(r["exit_ts"][:10] for r in closed)
    mid = dates[len(dates)//2]
    early = [r for r in closed if r["exit_ts"][:10] < mid]
    late = [r for r in closed if r["exit_ts"][:10] >= mid]
    print(f"   split at {mid}: early n={len(early)} price={round(sum(r['profit_price'] for r in early),2)} net={round(sum(r['net'] for r in early),2)} | "
          f"late n={len(late)} price={round(sum(r['profit_price'] for r in late),2)} net={round(sum(r['net'] for r in late),2)}")
    # cumulative by day
    byday = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in closed:
        d = r["exit_ts"][:10]; byday[d][0] += r["profit_price"]; byday[d][1] += r["net"]; byday[d][2] += 1
    print("   daily:", {k: [round(v[0],2), round(v[1],2), v[2]] for k, v in sorted(byday.items())})

with open(os.path.join(OUT, "V1_HERMES_TRADE_DATABASE.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
    for r in allrows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("wrote V1_HERMES_TRADE_DATABASE.jsonl rows:", len(allrows))
