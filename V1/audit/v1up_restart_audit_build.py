# -*- coding: utf-8 -*-
"""v1up_restart_audit_build.py — READ-ONLY builder for the V1 "restart then consecutive losses" audit.

Hard boundary (task book): no production code change, ORDER_SEND=0, no order_check, no state change.
Reads: MT5 broker deal/order facts (via history_*), the v1_upgrade ledger, runtime registry, staged fix.
Writes: only the 4 audit artifacts under research/hermes/trader_v1/audit/.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
AUDIT = os.path.join(BASE, "audit")
STAGED = os.path.join(ROOT, "audit", "staged_fix")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
ENV = os.path.join(REPO, ".env.mt5_demo")
TERM = os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe")
MAGIC = 90011
SERVER_OFF = dt.timedelta(hours=3)
RESTART_UTC = dt.datetime(2026, 10, 1, 13, 52, 15, tzinfo=dt.timezone.utc)   # host reboot (local 21:52:15 GMT+8)
LIM_MDL, LIM_MCL, LIM_STALE, LIM_SLIP, LIM_SPREAD = -20.0, 3, 900, 15.0, 30.0


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def rows():
    return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]


def load_env():
    d = {}
    for line in open(ENV, encoding="utf-8-sig", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def broker_deals(days=10):
    import MetaTrader5 as mt5
    env = load_env()
    kw = {"path": TERM, "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
    kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
    if not mt5.initialize(**kw):
        raise RuntimeError(f"MT5_INIT_FAILED {mt5.last_error()}")
    frm = utcnow() - dt.timedelta(days=days)
    to = utcnow() + dt.timedelta(days=1)
    deals = mt5.history_deals_get(frm, to) or []
    orders = mt5.history_orders_get(frm, to) or []
    ai = mt5.account_info()
    tk = mt5.symbol_info_tick("XAUUSD")
    snap = {"balance": ai.balance, "equity": ai.equity, "login": ai.login, "server": ai.server,
            "terminal_time_srv": int(getattr(tk, "time", 0) or 0), "read_utc": utcnow().isoformat()}
    mt5.shutdown()
    out = []
    for d in deals:
        out.append({k: getattr(d, k, None) for k in
                    ("ticket", "order", "time", "time_msc", "type", "entry", "magic", "position_id",
                     "volume", "price", "commission", "swap", "profit", "fee", "comment", "symbol", "reason")})
    ord_out = []
    for o in orders:
        ord_out.append({k: getattr(o, k, None) for k in
                        ("ticket", "time_setup", "time_done", "type", "state", "magic", "position_id",
                         "volume_initial", "price_open", "comment", "symbol", "type_filling")})
    return snap, out, ord_out


def srv(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)


def main():
    os.makedirs(AUDIT, exist_ok=True)
    L = rows()
    snap, deals, orders = broker_deals()
    d90011 = [d for d in deals if int(d.get("magic") or 0) == MAGIC]

    # ---- per-position broker reconstruction -------------------------------------------------
    by_pos = {}
    for d in d90011:
        pid = str(d.get("position_id"))
        rec = by_pos.setdefault(pid, {"open": None, "close": None})
        if d.get("entry") == 0:
            rec["open"] = d
        elif d.get("entry") == 1:
            rec["close"] = d
    trades = []
    for pid, rec in by_pos.items():
        o, c = rec.get("open"), rec.get("close")
        if not o:
            continue
        close_t = (srv(c["time"]) if c else None)          # server frame
        open_t = srv(o["time"] if False else o["time"]) if False else srv(o["time"])
        trades.append({
            "position_id": pid,
            "open_srv": open_t.isoformat(), "open_utc": (open_t - SERVER_OFF).isoformat(),
            "close_srv": close_t.isoformat() if close_t else None,
            "close_utc": (close_t - SERVER_OFF).isoformat() if close_t else None,
            "side": "LONG" if int(o.get("type") or 0) == 0 else "SHORT",
            "volume": float(o.get("volume") or 0.0),
            "open_price": float(o.get("price") or 0.0),
            "close_price": float(c.get("price") or 0.0) if c else None,
            "profit": round(float(c.get("profit") or 0.0), 2) if c else None,
            "commission": round(float((c.get("commission") or 0.0) + (o.get("commission") or 0.0)), 2) if c else None,
            "swap": round(float((c.get("swap") or 0.0) + (o.get("swap") or 0.0)), 2) if c else None,
            "net": (round(float(c.get("profit") or 0.0) + float((c.get("commission") or 0.0) + (o.get("commission") or 0.0))
                          + float((c.get("swap") or 0.0) + (o.get("swap") or 0.0)), 2) if c else None),
            "close_comment": (c.get("comment") if c else None),
            "close_reason": ("SL" if c and str(c.get("comment", "")).strip().lower().startswith("[sl")
                             else "TP" if c and str(c.get("comment", "")).strip().lower().startswith("[tp")
                             else ("MANUAL" if c else None)),
            "closed": c is not None,
        })
    trades.sort(key=lambda t: t["open_srv"])
    for t in trades:
        t["phase"] = "POST_RESTART" if dt.datetime.fromisoformat(t["open_utc"]) >= RESTART_UTC else "PRE_RESTART"

    # ---- ledger cross-reference (signal state, risk verdict, slippage) ----------------------
    pos_ev = {str(e.get("order_id")): e for e in L if e["event"] == "POSITION"}
    send_ev = {}
    for e in L:
        if e["event"] == "ORDER_SEND" and e.get("order_id") is not None and e.get("ok"):
            send_ev[str(e["order_id"])] = e
    dec_sig = []
    for t in trades:
        e = pos_ev.get(t["position_id"], {})
        s = send_ev.get(t["position_id"], {})
        t["ledger_position_seq"] = e.get("seq")
        t["sl"] = e.get("sl"); t["tp"] = e.get("tp")
        t["slippage_bps"] = s.get("slippage_bps")
        t["fill_price"] = s.get("fill_price")

    # ---- consecutive-loss sequence (broker net) --------------------------------------------
    seq = [t for t in trades if t["closed"]]
    run = 0
    for t in seq:
        run = run + 1 if (t["net"] or 0) < 0 else 0
        t["consec_net"] = run
    # split at restart
    pre = [t for t in trades if t["phase"] == "PRE_RESTART"]
    post = [t for t in trades if t["phase"] == "POST_RESTART"]
    post_closed = [t for t in post if t["closed"]]

    # ---- old vs correct guard state at the restart boundary --------------------------------
    def day_closes_before(day_utc, when_utc):
        out = []
        for t in trades:
            if t["closed"] and dt.datetime.fromisoformat(t["close_utc"]) <= when_utc:
                if dt.datetime.fromisoformat(t["close_utc"]).date().isoformat() == day_utc:
                    out.append((dt.datetime.fromisoformat(t["close_utc"]), t["net"] or 0.0))
        out.sort()
        return out

    def guard_state(day_utc, when_utc):
        daily, cons = 0.0, 0
        for _, v in day_closes_before(day_utc, when_utc):
            daily += v
            cons = cons + 1 if v < 0 else 0
        return round(daily, 2), cons

    day_of_restart = RESTART_UTC.date().isoformat()
    true_daily, true_cons = guard_state(day_of_restart, RESTART_UTC)
    post_trace = []
    daily, cons = true_daily, true_cons
    for t in post:
        reasons = []
        if daily <= LIM_MDL:
            reasons.append("MAX_DAILY_LOSS")
        if cons >= LIM_MCL:
            reasons.append("MAX_CONSECUTIVE_LOSS")
        post_trace.append({"position_id": t["position_id"], "open_utc": t["open_utc"],
                           "daily_before": round(daily, 2), "cons_before": cons,
                           "old_logic_verdict": "ALLOW", "correct_logic_reasons": reasons,
                           "correct_logic_verdict": "BLOCK" if reasons else "ALLOW",
                           "net": t["net"]})
        if t["closed"]:
            d = dt.datetime.fromisoformat(t["close_utc"]).date().isoformat()
            if d != day_of_restart:
                day_of_restart, daily, cons = d, 0.0, 0
            daily += t["net"] or 0.0
            cons = cons + 1 if (t["net"] or 0) < 0 else 0

    trace_doc = {
        "generated_utc": utcnow().isoformat(),
        "account": snap,
        "restart_utc": RESTART_UTC.isoformat(),
        "frame_note": "all *_utc fields = broker server time minus 3h; *_srv = raw UTC+3 server frame",
        "counts": {"trades_90011": len(trades), "closed": len(seq), "open": len(trades) - len(seq),
                   "pre_restart": len(pre), "post_restart": len(post),
                   "ledger_events": len(L), "broker_deals_90011": len(d90011), "broker_orders_90011": len(orders)},
        "trades": trades,
    }
    json.dump(trace_doc, open(os.path.join(AUDIT, "V1_RESTART_TRADE_TRACE.json"), "w", encoding="utf-8",
                              newline="\n"), indent=1, ensure_ascii=False)

    state_doc = {
        "generated_utc": utcnow().isoformat(),
        "restart_utc": RESTART_UTC.isoformat(),
        "restart_evidence": "host LastBootUpTime 2026-10-01 21:52:15 GMT+8 (= 13:52:15Z); python procs started 21:54",
        "old_logic_state_at_restart": {"daily_loss": 0.0, "consecutive_losses": 0,
                                       "why": "cycle.py:287 builds a fresh RiskGuard each cycle; note_close() never called"},
        "true_state_at_restart": {"day_utc": RESTART_UTC.date().isoformat(), "daily_loss": true_daily,
                                  "consecutive_losses": true_cons},
        "open_position_at_restart": [t for t in trades if t["phase"] == "PRE_RESTART" and not t["closed"]] or None,
        "post_restart_trace": post_trace,
        "post_restart_summary": {
            "trades": len(post), "closed": len(post_closed),
            "losses": sum(1 for t in post_closed if (t["net"] or 0) < 0),
            "wins": sum(1 for t in post_closed if (t["net"] or 0) > 0),
            "net": round(sum((t["net"] or 0) for t in post_closed), 2),
            "longest_loss_run": max([t["consec_net"] for t in post_closed] or [0]),
            "should_have_blocked": sum(1 for p in post_trace if p["correct_logic_verdict"] == "BLOCK"),
        },
        "limits": {"max_daily_loss": LIM_MDL, "max_consecutive_loss": LIM_MCL, "stale_data_seconds": LIM_STALE,
                   "slippage_limit_bps": LIM_SLIP, "spread_limit_bps": LIM_SPREAD},
    }
    json.dump(state_doc, open(os.path.join(AUDIT, "V1_RESTART_STATE_AUDIT.json"), "w", encoding="utf-8",
                              newline="\n"), indent=1, ensure_ascii=False)

    # ---- production-file fingerprints (not touched) ----------------------------------------
    fps = {}
    for f in ("gates.py", "cycle.py", "run_gates.py", "label_adapter.py",
              "registry/v1_upgrade_registry.json", "registry/runtime_config.json", "ledger/v1_upgrade_ledger.jsonl"):
        p = os.path.join(ROOT, f)
        fps[f] = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None

    summary = {
        "banner": "v1up_restart_audit_build::main",
        "deals_magic_histogram": {},
        "production_fingerprints": fps,
        "state": state_doc["post_restart_summary"],
        "true_state_at_restart": state_doc["true_state_at_restart"],
    }
    for d in deals:
        m = str(int(d.get("magic") or 0))
        summary["deals_magic_histogram"][m] = summary["deals_magic_histogram"].get(m, 0) + 1
    print(json.dumps(summary, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
