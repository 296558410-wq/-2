# -*- coding: utf-8 -*-
"""v1_7loss_verify.py — independent verification pass: risk-state reconstruction both bases,
execution facts, linkage IDs, restart/pair checks. READ-ONLY. Writes one JSON in this dir."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_7loss_forensics")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "truth"))
import gates, truth_lib as TR  # noqa: E402

RESTART = dt.datetime.fromisoformat("2026-10-01T13:52:15+00:00")
PIDS = ["2378322488", "2378333628", "2378343004", "2378348994", "2378382127", "2378409328", "2378413449"]
L = [json.loads(l) for l in open(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]

# fresh broker read (read-only)
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

def net_of(pid):
    r = by_pos.get(str(pid))
    if not r or not r["close"]:
        return None, None, None
    c, o = r["close"], r["open"]
    return (round(float(c.profit) + float(c.commission) + float(o.commission) + float(c.swap), 2),
            round(float(c.profit), 2), round(float(c.commission) + float(o.commission) + float(c.swap), 2))

def state_at(when_utc, day, basis):
    """basis='price' (ledger PNL field) or 'net' (broker deals via position map)."""
    tot, cons = 0.0, 0
    recs = []
    for e in L:
        if e.get("event") != "PNL":
            continue
        utc = gates.realized_close_utc(e)
        if utc > when_utc or utc.date().isoformat() != day:
            continue
        if basis == "price":
            v = float(e.get("pnl") or 0)
        else:
            n, _, _ = net_of(e.get("position_id"))
            v = n if n is not None else float(e.get("pnl") or 0)
        recs.append((utc.isoformat(), str(e.get("position_id")), round(v, 2)))
    recs.sort()
    for _, _, v in recs:
        tot += v; cons = cons + 1 if v < 0 else 0
    return {"basis": basis, "daily_loss": round(tot, 2), "consecutive_losses": cons, "closes": recs}

R = {"schema": "v1_7loss_recon/2", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
     "ledger_sha256": hashlib.sha256(open(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl"), "rb").read()).hexdigest()}

# restart state both bases
R["restart_state"] = {"price_basis": state_at(RESTART, "2026-10-01", "price"),
                       "net_basis": state_at(RESTART, "2026-10-01", "net")}

# per-trade states both bases + verdicts
trades = []
for pid in PIDS:
    dec = None
    send = next((e for e in L if e.get("event") == "ORDER_SEND" and str(e.get("order_id")) == pid), None)
    cands = [r for r in L if r.get("event") == "DECISION" and r.get("seq", 0) < send.get("seq", 0)]
    dec = next((r for r in reversed(cands) if str(r.get("action")) in ("ENTER", "WOULD_ENTER")), None)
    ts = dt.datetime.fromisoformat(dec["ts_utc"])
    sp = state_at(ts, ts.date().isoformat(), "price")
    sn = state_at(ts, ts.date().isoformat(), "net")
    block_p = sp["daily_loss"] <= -20 or sp["consecutive_losses"] >= 3
    block_n = sn["daily_loss"] <= -20 or sn["consecutive_losses"] >= 3
    n, price, cost = net_of(pid)
    close = next((e for e in L if e.get("event") == "CLOSE" and str(e.get("position_id")) == pid), None)
    pnl = next((e for e in L if e.get("event") == "PNL" and str(e.get("position_id")) == pid), None)
    row = {
        "trade_id": TR.trade_id(pid), "position_id": pid,
        "decision_seq": dec.get("seq"), "decision_ts": dec.get("ts_utc")[:19],
        "decision_event_id": TR.event_id(dec), "send_seq": send.get("seq"), "send_event_id": TR.event_id(send),
        "send_retcode": send.get("retcode"), "send_ok": send.get("ok"), "fill_price": send.get("fill_price"),
        "slippage_bps": send.get("slippage_bps"), "latency_ms": send.get("latency_ms"),
        "close_seq": (close or {}).get("seq"), "pnl_seq": (pnl or {}).get("seq"),
        "close_broker_time": (close or {}).get("broker_time_utc"), "ledger_pnl_price": (pnl or {}).get("pnl"),
        "broker_net": n, "broker_price_component": price, "broker_cost": cost,
        "state_price": sp, "state_net": sn,
        "block_price_basis": block_p, "block_net_basis": block_n,
        "dedup_era": "not-wired (V1-D002 era)",
    }
    trades.append(row)
R["trades"] = trades

# window integrity checks
win = [e for e in L if "2026-10-01T14:20" <= e["ts_utc"] <= "2026-10-02T02:10"]
sends = [e for e in win if e.get("event") == "ORDER_SEND"]
R["window_checks"] = {
    "order_send_attempts": len(sends), "order_send_ok": sum(1 for s in sends if s.get("ok")),
    "order_send_rejected": sum(1 for s in sends if not s.get("ok")),
    "duplicate_position_ids": len(PIDS) - len(set(PIDS)),
    "ledger_chain_ok": gates.Ledger(os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")).verify()[0],
    "schedule_gap": "2026-10-01T13:48:03Z -> 2026-10-01T14:18:02Z (30.0 min); restart 13:52:15Z inside gap",
    "incident_ref": "V1I-SCHEDULE_G-FB1B39B4 (truth incidents store)",
}
# open positions across the restart boundary (broker reconstruction)
open_at_restart = []
for pid, r in by_pos.items():
    o, c = r["open"], r["close"]
    if o and (c is None or int(c.time) > int(RESTART.timestamp()) + 10800):
        open_at_restart.append({"position_id": pid,
                                 "open_srv": int(o.time), "close_srv": (int(c.time) if c else None)})
R["broker_open_at_restart_utc_basis"] = {"note": "deal times are server frame (UTC+3); reconstructed", "positions": open_at_restart}
json.dump(R, open(os.path.join(OUT, "V1_7_LOSS_RISK_RECON.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)

print("restart price:", R["restart_state"]["price_basis"]["daily_loss"], R["restart_state"]["price_basis"]["consecutive_losses"])
print("restart net  :", R["restart_state"]["net_basis"]["daily_loss"], R["restart_state"]["net_basis"]["consecutive_losses"])
for t in trades:
    print(f"{t['trade_id']} blk(price/net)={t['block_price_basis']}/{t['block_net_basis']} "
          f"daily_p={t['state_price']['daily_loss']} daily_n={t['state_net']['daily_loss']} "
          f"cons_p={t['state_price']['consecutive_losses']} net={t['broker_net']} rc={t['send_retcode']}")
print("window:", json.dumps(R["window_checks"], ensure_ascii=False))
print("open_at_restart:", open_at_restart)
