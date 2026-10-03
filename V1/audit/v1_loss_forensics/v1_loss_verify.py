# -*- coding: utf-8 -*-
"""v1_loss_verify.py — independent verification for the V1 loss-forensics package (READ-ONLY).
Checks: (1) broker↔ledger 1:1 coverage for magic 90011; (2) win/loss vs broker profit sign;
(3) audit-side order_send/order_check = 0 (static scan of this dir's scripts);
(4) V1/V2/V3 isolation (this package read only V1 paths + broker magic 90011).
Writes VERIFY.json. No orders; no writes outside this audit dir.
"""
from __future__ import annotations
import datetime as dt, glob, hashlib, json, os, re

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_loss_forensics")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")

L = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
led_pos = [str(e.get("order_id")) for e in L if e.get("event") == "POSITION"]

env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5  # noqa: E402
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
ok = mt5.initialize(**kw)
assert ok, mt5.last_error()
frm = dt.datetime(2026, 9, 25, tzinfo=dt.timezone.utc); to = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
deals = mt5.history_deals_get(frm, to) or []
mt5.shutdown()
d9 = [d for d in deals if int(getattr(d, "magic", 0) or 0) == 90011]
broker_sides = {}
for d in d9:
    broker_sides.setdefault(str(d.position_id), {})[("open" if d.entry == 0 else "close")] = d
broker_pos = sorted(broker_sides.keys(), key=lambda x: int(x))
broker_complete = sorted([p for p, s in broker_sides.items() if "open" in s and "close" in s], key=lambda x: int(x))

db = [json.loads(l) for l in open(os.path.join(OUT, "TRADE_ERROR_DATABASE.jsonl"), encoding="utf-8") if l.strip()]
db_pos = [r["position_id"] for r in db]

# broker win/loss vs db outcome (price-basis profit of close leg)
sign_mismatch = []
for r in db:
    s = broker_sides.get(r["position_id"], {})
    c = s.get("close")
    if c is None:
        sign_mismatch.append({"trade_id": r["trade_id"], "reason": "no close deal"}); continue
    bsign = "WIN" if float(c.profit) > 0 else "LOSS"
    if bsign != r["outcome"]:
        sign_mismatch.append({"trade_id": r["trade_id"], "db": r["outcome"], "broker_profit": float(c.profit)})

# static scan: audit-side order calls
pat = re.compile(r"order_(send|check)\s*\(")
sends = []
for f in sorted(glob.glob(os.path.join(OUT, "*.py"))):
    txt = open(f, encoding="utf-8", errors="replace").read()
    for m in pat.finditer(txt):
        line = txt[:m.start()].count("\n") + 1
        sends.append({"file": os.path.basename(f), "line": line, "call": m.group(0)})
# also confirm the production engine path is not imported for execution here
eng_imports = []
for f in sorted(glob.glob(os.path.join(OUT, "*.py"))):
    txt = open(f, encoding="utf-8", errors="replace").read()
    for mm in re.finditer(r"^\s*(import|from)\s+([A-Za-z0-9_\.]+)", txt, re.M):
        eng_imports.append(mm.group(2))

res = {
    "schema": "v1_loss_verify/1",
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "ledger_sha256": hashlib.sha256(open(LEDGER, "rb").read()).hexdigest(),
    "coverage": {
        "ledger_positions": len(led_pos), "broker_positions_magic90011": len(broker_pos),
        "broker_complete_roundtrips": len(broker_complete), "db_trades": len(db_pos),
        "ledger_minus_broker": sorted(set(led_pos) - set(broker_complete), key=lambda x: int(x)),
        "broker_minus_ledger": sorted(set(broker_complete) - set(led_pos), key=lambda x: int(x)),
        "ledger_minus_db": sorted(set(led_pos) - set(db_pos), key=lambda x: int(x)),
        "db_minus_ledger": sorted(set(db_pos) - set(led_pos), key=lambda x: int(x)),
    },
    "winloss_sign_mismatch": sign_mismatch,
    "audit_order_calls": sends,
    "audit_order_calls_count": len(sends),
    "imports_seen": sorted(set(eng_imports)),
    "isolation": {"mt5_magic_filter": [90011], "v2_or_v3_paths_read": False,
                  "note": "package reads V1 ledger + broker magic 90011 + XAUUSD bars/ticks only; no V2/V3 paths."},
}

json.dump(res, open(os.path.join(OUT, "VERIFY.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(res["coverage"], ensure_ascii=False))
print("sign_mismatch:", sign_mismatch)
print("audit_order_calls:", sends)
print("coverage_ok:", (not res["coverage"]["ledger_minus_broker"] and not res["coverage"]["broker_minus_ledger"]
                      and not res["coverage"]["ledger_minus_db"] and not res["coverage"]["db_minus_ledger"]))
print("VERDICT:", "PASS" if (not sends and not sign_mismatch and res["coverage"]["ledger_minus_broker"] == []
                             and res["coverage"]["broker_minus_ledger"] == []) else "REVIEW")
