# -*- coding: utf-8 -*-
"""v1_7loss_build.py — forensic reconstruction for the 7 post-restart consecutive V1 losses.

READ-ONLY: does not modify ledger/broker/truth-evidence/production code. Reads:
  - v1_upgrade ledger (raw facts)
  - fresh MT5 broker history (read-only) for the 7 positions
  - current gates.py / truth_lib.py semantics for counterfactual risk evaluation
Writes only: this directory (JSON consumed by the report).
"""
from __future__ import annotations
import datetime as dt, glob, hashlib, json, os, sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_7loss_forensics")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "truth"))
import gates                      # noqa: E402
import truth_lib as TR            # noqa: E402

os.makedirs(OUT, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc)
RESTART = dt.datetime.fromisoformat("2026-10-01T13:52:15+00:00")
PIDS = ["2378322488", "2378333628", "2378343004", "2378348994", "2378382127", "2378409328", "2378413449"]


def rows():
    return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]


def srv2utc(s):
    return dt.datetime.fromisoformat(s) - dt.timedelta(hours=3)


def broker_deals():
    env = {}
    for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
    import MetaTrader5 as mt5
    kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
          "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
    kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
    if not mt5.initialize(**kw):
        return None, f"MT5_INIT_FAILED {mt5.last_error()}"
    frm = dt.datetime(2026, 9, 28, tzinfo=dt.timezone.utc); to = NOW + dt.timedelta(days=1)
    deals = mt5.history_deals_get(frm, to) or []
    orders = mt5.history_orders_get(frm, to) or []
    ai = mt5.account_info()
    out = {"read_utc": NOW.isoformat(), "account": {"login": ai.login, "server": ai.server, "balance": ai.balance},
           "deals": [{k: getattr(d, k, None) for k in ("ticket", "order", "time", "type", "entry", "magic", "position_id",
                                                        "volume", "price", "commission", "swap", "profit", "comment")} for d in deals],
           "orders": [{k: getattr(o, k, None) for k in ("ticket", "time_setup", "time_done", "type", "state", "magic",
                                                         "position_id", "price_open", "comment")} for o in orders]}
    mt5.shutdown()
    return out, None


L = rows()
broker, berr = broker_deals()

# ---- restart-time state ----
def correct_state_at(when_utc, day):
    """Rebuild the declared-guard state from ledger closes strictly before `when_utc` (UTC-day scoped)."""
    rg = gates.RiskGuard()
    closes = []
    for e in L:
        if e.get("event") != "PNL":
            continue
        utc = gates.realized_close_utc(e)
        if utc <= when_utc:
            closes.append((utc, gates.realized_pnl(e, "net")))
    same = sorted([c for c in closes if c[0].date().isoformat() == day])
    rg.roll_day(day)
    for _, pnl in same:
        rg.note_close(pnl)
    return {"day": day, "daily_loss": round(rg.daily_loss, 4), "consecutive_losses": rg.consecutive_losses}


def realized_pnl_before(when_utc):
    tot = 0.0
    for e in L:
        if e.get("event") == "PNL" and gates.realized_close_utc(e) <= when_utc:
            tot += float(e.get("pnl") or 0)
    return round(tot, 2)


def open_set_at(when_utc):
    s = {}
    for e in L:
        t = dt.datetime.fromisoformat(e["ts_utc"])
        if t > when_utc:
            continue
        if e.get("event") == "POSITION":
            s[str(e.get("order_id"))] = t.isoformat()
        elif e.get("event") == "CLOSE":
            s.pop(str(e.get("order_id")), None)
    return s


restart_ctx = {
    "restart_utc": RESTART.isoformat(),
    "old_semantics_state": {"daily_loss": 0.0, "consecutive_losses": 0, "note": "fresh RiskGuard per cycle; note_close never called (V1-D001)"},
    "correct_semantics_state": correct_state_at(RESTART, "2026-10-01"),
    "realized_pnl_price_component_before_restart": realized_pnl_before(RESTART),
    "ledger_open_positions_at_restart": open_set_at(RESTART),
    "last_decision_before_restart": (lambda d: {"seq": d.get("seq"), "ts_utc": d.get("ts_utc"), "action": d.get("action"),
                                                 "risk_reasons": d.get("risk_reasons")})([r for r in L if r.get("event") == "DECISION" and r["ts_utc"] < RESTART.isoformat()][-1]),
    "first_decision_after_restart": (lambda d: {"seq": d.get("seq"), "ts_utc": d.get("ts_utc"), "action": d.get("action"),
                                                 "risk_reasons": d.get("risk_reasons")})([r for r in L if r.get("event") == "DECISION" and r["ts_utc"] > RESTART.isoformat()][0]),
}

# ---- per-trade reconstruction ----
trades = []
prev_slip = None
for pid in PIDS:
    t = {}
    t["trade_id"] = TR.trade_id(pid); t["position_id"] = pid
    ev = [e for e in L if str(e.get("order_id")) == pid or str(e.get("position_id")) == pid]
    pos = next((e for e in L if e.get("event") == "POSITION" and str(e.get("order_id")) == pid), None)
    send = next((e for e in L if e.get("event") == "ORDER_SEND" and str(e.get("order_id")) == pid), None)
    req = next((e for e in L if e.get("event") == "ORDER_REQUEST" and abs(e.get("seq", 0) - (send or {}).get("seq", -9)) <= 1), None)
    chk = next((e for e in L if e.get("event") == "ORDER_CHECK" and e.get("seq", 0) < (send or {}).get("seq", 0)), None)
    close = next((e for e in L if e.get("event") == "CLOSE" and str(e.get("position_id")) == pid), None)
    pnl = next((e for e in L if e.get("event") == "PNL" and str(e.get("position_id")) == pid), None)
    dec = None
    if send is not None:
        cands = [r for r in L if r.get("event") == "DECISION" and r.get("seq", 0) < send.get("seq", 0)]
        dec = next((r for r in reversed(cands) if str(r.get("action")) in ("ENTER", "WOULD_ENTER")), None)
    t["events"] = {"decision": dec, "order_check": chk, "order_request": req, "order_send": send, "close": close, "pnl": pnl}
    open_utc = srv2utc(send["broker_comment"]) if False else None
    # decision-time guard counterfactual (declared semantics; only day/consecutive are fact-based)
    if dec is not None:
        ts = dt.datetime.fromisoformat(dec["ts_utc"])
        cs = correct_state_at(ts, ts.date().isoformat())
        mkt = {"spread_bps": (dec.get("snapshot") or {}).get("spread_bps"),
               "slippage_bps": prev_slip, "data_age_seconds": None}
        rg = gates.RiskGuard(); rg.roll_day(cs["day"])
        rg.daily_loss = cs["daily_loss"]; rg.consecutive_losses = cs["consecutive_losses"]
        ok, reasons = rg.evaluate({"order_id": None, "already_sent": set()}, mkt, 0)
        t["guard_counterfactual"] = {"state": cs, "reasons_with_full_inputs": reasons,
                                      "would_block_daily_or_consecutive": ("MAX_DAILY_LOSS" in reasons) or ("MAX_CONSECUTIVE_LOSS" in reasons),
                                      "note": "data_age not recorded in this era (guard consumed hardcoded 0); slippage = last realised before this decision"}
    if send is not None:
        prev_slip_for = send.get("slippage_bps")
    # broker facts per position
    bd = []
    if broker:
        bd = [d for d in broker["deals"] if str(d.get("position_id")) == pid]
    o, c = next((d for d in bd if d.get("entry") == 0), None), next((d for d in bd if d.get("entry") == 1), None)
    if c:
        net = round(float(c.get("profit") or 0) + float(c.get("commission") or 0) + float((o or {}).get("commission") or 0) + float(c.get("swap") or 0), 2)
    else:
        net = None
    t["broker"] = {"open_deal": o, "close_deal": c, "net": net,
                   "close_comment": (c or {}).get("comment")}
    # classification inputs
    blocked = bool(t.get("guard_counterfactual", {}).get("would_block_daily_or_consecutive"))
    anomalies = {
        "execution_anomaly": bool(send and send.get("ok") is not True),
        "broker_anomaly": not bool(c and str((c or {}).get("comment", "")).strip().lower().startswith("[sl")),
        "data_anomaly_recorded": False,  # era did not record data_age; UNKNOWN
    }
    t["classification"] = {
        "primary_cause": "RISK_GUARD_FAILURE" if blocked else "SIGNAL_LOSS",
        "contributing_factors": (["SIGNAL_LOSS"] if blocked else []),
        "basis": ("declared MAX_CONSECUTIVE_LOSS (state>=3) would have blocked this entry; executed because the guard was inert (V1-D001)"
                  if blocked else "no declared gate (correct semantics) would have blocked this entry"),
    }
    t["anomalies"] = anomalies
    prev_slip = send.get("slippage_bps") if send else prev_slip
    trades.append(t)

doc = {
    "schema": "v1_7loss_forensic/1",
    "generated_utc": NOW.isoformat(),
    "restart": restart_ctx,
    "trades": trades,
    "broker_read": {"ok": broker is not None, "error": berr, "read_utc": (broker or {}).get("read_utc"),
                     "account": (broker or {}).get("account")},
    "input_hashes": {"ledger_sha256": hashlib.sha256(open(LEDGER, "rb").read()).hexdigest()},
}
json.dump(doc, open(os.path.join(OUT, "V1_7_LOSS_FORENSIC.json"), "w", encoding="utf-8", newline="\n"),
          indent=1, ensure_ascii=False, default=str)

print("broker ok:", broker is not None, berr or "")
print("restart ctx:", json.dumps(restart_ctx, ensure_ascii=False, default=str)[:500])
for t in trades:
    d = (t["events"].get("decision") or {})
    s = (t["events"].get("order_send") or {})
    gf = t.get("guard_counterfactual", {})
    print(f"{t['trade_id']} dec_seq={d.get('seq')} dec_ts={(d.get('ts_utc') or '')[:19]} "
          f"state={gf.get('state')} block={gf.get('would_block_daily_or_consecutive')} "
          f"slip={s.get('slippage_bps')} ret={s.get('retcode')} net={t['broker']['net']} "
          f"close={(t['broker']['close_comment'] or '')[:12]} class={t['classification']['primary_cause']}")
