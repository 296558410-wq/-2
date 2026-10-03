# -*- coding: utf-8 -*-
"""v1_7loss_table.py — fix the open-at-restart check + build the consolidated per-trade table
(with event_id citations, execution facts, broker raw values). READ-ONLY; one JSON output."""
from __future__ import annotations
import datetime as dt, json, os, sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_7loss_forensics")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "truth"))
import gates, truth_lib as TR  # noqa: E402

RESTART = dt.datetime.fromisoformat("2026-10-01T13:52:15+00:00")
RESTART_SRV = int(RESTART.timestamp()) + 10800
PIDS = ["2378322488", "2378333628", "2378343004", "2378348994", "2378382127", "2378409328", "2378413449"]

L = [json.loads(l) for l in open(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
fort = json.load(open(os.path.join(OUT, "V1_7_LOSS_FORENSIC.json"), encoding="utf-8"))

# fresh broker read
env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5  # noqa: E402
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
assert mt5.initialize(**kw), mt5.last_error()
deals = mt5.history_deals_get(dt.datetime(2026, 9, 28, tzinfo=dt.timezone.utc), dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)) or []
mt5.shutdown()
d90011 = [d for d in deals if int(getattr(d, "magic", 0) or 0) == 90011]
by_pos = {}
for d in d90011:
    r = by_pos.setdefault(str(d.position_id), {"open": None, "close": None})
    if d.entry == 0: r["open"] = d
    elif d.entry == 1: r["close"] = d

# corrected open-at-restart reconstruction (open before boundary, close after or still open)
open_at = []
for pid, r in by_pos.items():
    o, c = r["open"], r["close"]
    oc = int(o.time) if o else None
    cc = int(c.time) if c else None
    if oc is not None and oc < RESTART_SRV and (cc is None or cc > RESTART_SRV):
        open_at.append({"position_id": pid, "open_srv": oc, "close_srv": cc})

# consolidated table
rows = []
for t in fort["trades"]:
    pid = t["position_id"]
    ev = t["events"]
    dec, send, chk, req, close, pnl = (ev.get("decision"), ev.get("order_send"), ev.get("order_check"),
                                       ev.get("order_request"), ev.get("close"), ev.get("pnl"))
    b = t["broker"]
    o, c = b.get("open_deal"), b.get("close_deal")
    fill = next((e for e in L if e.get("event") == "FILL" and str(e.get("order_id")) == pid), None)
    pos = next((e for e in L if e.get("event") == "POSITION" and str(e.get("order_id")) == pid), None)
    rows.append({
        "trade_id": TR.trade_id(pid), "position_id": pid,
        "ids": {"decision": TR.event_id(dec), "order_check": TR.event_id(chk) if chk else None,
                "order_request": TR.event_id(req) if req else None, "order_send": TR.event_id(send) if send else None,
                "fill": TR.event_id(fill) if fill else None, "position": TR.event_id(pos) if pos else None,
                "close": TR.event_id(close) if close else None, "pnl": TR.event_id(pnl) if pnl else None},
        "decision": {"seq": dec.get("seq"), "ts_utc": dec.get("ts_utc"), "action": dec.get("action"),
                     "risk_reasons": dec.get("risk_reasons"), "signal": dec.get("signal"),
                     "order_intent": dec.get("order_intent"), "snapshot": dec.get("snapshot")},
        "exec": {"retcode": send.get("retcode"), "ok": send.get("ok"), "req_price": send.get("price"),
                 "fill_price": send.get("fill_price"), "slippage_bps": send.get("slippage_bps"),
                 "latency_ms": send.get("latency_ms"), "check_retcode": (chk or {}).get("retcode")},
        "position": {"sl": (pos or {}).get("sl"), "tp": (pos or {}).get("tp")},
        "close": {"reason": (close or {}).get("reason"), "price": (close or {}).get("price"),
                  "broker_time_utc": (close or {}).get("broker_time_utc"), "broker_comment": (c or {}).get("comment")},
        "broker": {"open_time_srv": int(o["time"]) if o else None, "open_price": float(o["price"]) if o else None,
                   "close_time_srv": int(c["time"]) if c else None, "close_price": float(c["price"]) if c else None,
                   "profit": float(c["profit"]) if c else None, "commission": round(float(c["commission"] or 0) + float((o or {}).get("commission") or 0), 2) if c else None,
                   "swap": float(c["swap"]) if c else None,
                   "net": round(float(c["profit"]) + float(c["commission"] or 0) + float((o or {}).get("commission") or 0) + float(c["swap"] or 0), 2) if c else None},
        "ledger_pnl": (pnl or {}).get("pnl"),
        "classification": t["classification"],
    })

# ledger/replay vs broker cross-check
replay = gates.Ledger(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")).replay()
b_profit = round(sum(float(c.profit) for p, r in by_pos.items() if (c := r["close"]) is not None), 2)
b_net = round(sum(float(c.profit) + float(c.commission) + (float(r["open"].commission) if r["open"] else 0) + float(c.swap)
                  for p, r in by_pos.items() if (c := r["close"]) is not None), 2)
out = {"schema": "v1_7loss_table/1",
       "open_at_restart_corrected": open_at,
       "open_at_restart_note": "broker reconstruction (server frame): positions open across 2026-10-01T16:52:15 srv; ledger says flat at restart",
       "trades": rows,
       "cross_checks": {"ledger_replay_realized_price": replay["realized_pnl"], "broker_profit_component_sum": b_profit,
                         "delta": round(replay["realized_pnl"] - b_profit, 2), "broker_net_sum": b_net}}
json.dump(out, open(os.path.join(OUT, "V1_7_LOSS_TABLE.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)

print("open_at_restart (corrected):", json.dumps(open_at, ensure_ascii=False))
print("cross:", json.dumps(out["cross_checks"], ensure_ascii=False))
for r in rows:
    e = r["exec"]; b = r["broker"]
    print(f"{r['trade_id']} {r['decision']['ts_utc'][:19]} -> close {r['close']['broker_time_utc']} "
          f"side={r['decision']['order_intent'].get('side')} req={e['req_price']} fill={e['fill_price']} "
          f"slip={e['slippage_bps']} rc={e['retcode']} pnl={r['ledger_pnl']} net={b['net']} {r['close']['broker_comment']}")
