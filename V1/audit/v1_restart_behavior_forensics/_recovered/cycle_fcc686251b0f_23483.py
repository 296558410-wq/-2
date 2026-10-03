# -*- coding: utf-8 -*-
"""v1_upgrade/cycle.py — NEW V1 cycle runner (fail-closed, ledger-first, demo-only).

  live read-only snapshot -> staleness/spread guard -> risk guard
  -> frozen signal (BASELINE_TRANSITION control arm; the Hermes prediction is NOT a permitted signal, §6)
  -> DECISION / ORDER_REQUEST / ORDER_SEND / FILL / POSITION appended to the new SHA256 ledger.

Order path is reachable ONLY when: demo account (live-verified), account flat, risk allows, and the
signal mapping says trade. LIVE/REAL can never be reached.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import (Ledger, RiskGuard, DemoGate, MAGIC, COMMENT,           # noqa: E402
                   rebuild_risk_state, data_age_seconds, last_realized_slippage_bps,
                   load_kill_switch, dedup_key, bar_bucket, rebuild_sent_keys, broker_recent_order_dup)
import signal_baseline as SB  # noqa: E402

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_upgrade")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
ENV = os.path.join(REPO, ".env.mt5_demo")
MAPPING = os.path.join(ROOT, "registry", "baseline_transition_mapping.json")
REPORT = os.path.join(ROOT, "reports", "last_cycle.json")
CACHE = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization", "states", "state_v2_series.parquet")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
NOW = datetime.now(timezone.utc).isoformat()
SYMBOL = "XAUUSD"
TERMINAL_PATH = os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe")
SIGNAL_SOURCES = ("NONE", "BASELINE_TRANSITION")


def load_env():
    d = {}
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8-sig", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def mt5_kwargs(env):
    # explicit path is MANDATORY here: three terminals run on this host and an unspecified
    # initialize() drifts to the "default" one => -10004 No IPC connection.
    kw = {"path": TERMINAL_PATH, "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
    kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
    return kw


def atr_m15(mt5, n=SB.ATR_N):
    bars = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, n + 2)
    if bars is None or len(bars) < n + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = float(bars[i]["high"]), float(bars[i]["low"]), float(bars[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-n:]) / n if len(trs) >= n else None


def snapshot(mt5):
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    if tick is None or info is None:
        return None
    mid = (tick.bid + tick.ask) / 2.0
    return {"bid": tick.bid, "ask": tick.ask, "mid": round(mid, 3),
             "spread_bps": round((tick.ask - tick.bid) / mid * 1e4, 3) if mid else None,
             "digits": info.digits}


def live_state_family(mt5=None):
    """Frozen 9-state labeler applied to LIVE M15 bars (label_adapter).
    No definition change: replay-proven identical to state_v2_series.parquet.
    Pass the caller's MT5 connection so the label path never re-initializes or shuts it down."""
    try:
        import label_adapter as LA
        r = LA.live_state(mt5=mt5)
        if not r.get("ok"):
            return {"state": None, "trend_20": None, "error": r.get("error"), "source": "label_adapter"}
        return {"state": r.get("state"), "family": r.get("family"), "trend_20": r.get("trend_sign"),
                 "atr": r.get("atr14"), "last_bar_utc": r.get("last_bar_utc"), "source": "label_adapter",
                 "MARKET_BEHAVIOR": r.get("MARKET_BEHAVIOR"), "ma20": r.get("ma20")}
    except Exception as e:  # noqa: BLE001
        return {"state": None, "trend_20": None, "error": str(e)[:150], "source": "label_adapter"}


def filling_for(mt5, symbol):
    """Map the SYMBOL filling BITMASK to the REQUEST enum BY NAME.

    symbol_info().filling_mode is a bitmask: bit1 = FOK, bit2 = IOC.
    The request field type_filling uses a DIFFERENT enum: FOK=0, IOC=1, RETURN=2.
    Passing the bitmask literal as type_filling is the #1 trap here (=> retcode 10030).
    """
    fm = int(getattr(mt5.symbol_info(symbol), "filling_mode", 0) or 0)
    if fm & 1:
        return mt5.ORDER_FILLING_FOK, fm, "FOK"
    if fm & 2:
        return mt5.ORDER_FILLING_IOC, fm, "IOC"
    return mt5.ORDER_FILLING_RETURN, fm, "RETURN"


def pick_filling(mt5, symbol, req_base, settle_tries=6, settle_sleep=0.4):
    """Fail-closed filling-mode selection using order_check probes (never sends an order).

    Two real-world quirks are handled WITHOUT weakening safety:
      * symbol_info().filling_mode can read 0 right after initialize() (symbol not yet synced)
        -> bounded settle loop until a usable bitmask appears.
      * order_check can return None while the trade context is still coming up
        -> up to 2 extra probes.  A definitive retcode (10027/10030/...) is NEVER retried.
    No candidate passing => return None (blocked), and nothing is ever sent.
    """
    import time as _t
    fm = 0
    for _ in range(max(1, settle_tries)):
        try:
            mt5.symbol_select(symbol, True)
        except Exception:  # noqa: BLE001
            pass
        fm = int(getattr(mt5.symbol_info(symbol), "filling_mode", 0) or 0)
        if fm:
            break
        _t.sleep(settle_sleep)
    primary, _, _ = filling_for(mt5, symbol) if fm else (None, fm, None)
    order = []
    if primary is not None:
        order.append(("FOK" if primary == mt5.ORDER_FILLING_FOK else "IOC" if primary == mt5.ORDER_FILLING_IOC else "RETURN", primary))
    for nm, v in (("FOK", mt5.ORDER_FILLING_FOK), ("IOC", mt5.ORDER_FILLING_IOC), ("RETURN", mt5.ORDER_FILLING_RETURN)):
        if (nm, v) not in order:
            order.append((nm, v))
    probes = []
    for nm, v in order:
        req = dict(req_base)
        req["type_filling"] = v
        for attempt in range(3):
            c = mt5.order_check(req)
            rc = None if c is None else int(c.retcode)
            probes.append({"filling": nm, "type_filling": int(v), "retcode": rc, "attempt": attempt + 1,
                            "comment": (None if c is None else str(c.comment)),
                            "last_error": str(mt5.last_error())})
            if rc is not None:
                break
            _t.sleep(0.3)
        if rc in (0, 10009):
            return nm, int(v), fm, probes
    return None, None, fm, probes


def _ledger_rows(path):
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass
    return rows


def reconcile_broker_closes(mt5, lg, days=120):
    """Reconcile broker-side (SL/TP) exits into the ledger as CLOSE + PNL events.

    The broker owns the exits (SL/TP), so the engine must OBSERVE them; otherwise every
    close/PnL-derived statistic (closed count, realized pnl, win/loss, drawdown, streak,
    replay) stays pinned at zero while real trades have closed.  Read-only w.r.t. trading
    decisions (never sends an order, never changes a risk verdict); idempotent (dedup by
    broker position_id); append-only (the SHA256 chain stays verifiable).
    """
    known = set()
    for e in _ledger_rows(lg.path):
        if e.get("event") == "CLOSE":
            pid = e.get("position_id") or e.get("order_id")
            if pid is not None:
                known.add(str(pid))
    sl_map = {}
    for e in _ledger_rows(lg.path):
        if e.get("event") == "POSITION" and e.get("order_id") is not None:
            sl_map[str(e.get("order_id"))] = (e.get("sl"), e.get("tp"))
    now = datetime.now(timezone.utc)
    deals = mt5.history_deals_get(now - timedelta(days=days), now + timedelta(days=1)) or []
    by_pos = {}
    for x in deals:
        try:
            mg = int(getattr(x, "magic", 0) or 0)
        except Exception:  # noqa: BLE001
            mg = 0
        if mg != MAGIC:
            continue
        pid = str(x.position_id)
        rec = by_pos.setdefault(pid, {"open": None, "close": None})
        if x.entry == 0:
            rec["open"] = x
        elif x.entry == 1:
            rec["close"] = x

    def _ctime(rec):
        c = rec.get("close")
        return int(getattr(c, "time", 0) or 0) if c is not None else 0

    out = []
    for pid, rec in sorted(by_pos.items(), key=lambda kv: _ctime(kv[1])):
        o, c = rec.get("open"), rec.get("close")
        if o is None or c is None or pid in known:
            continue
        profit = round(float(getattr(c, "profit", 0.0) or 0.0), 2)
        entry_px = float(getattr(o, "price", 0.0) or 0.0)
        exit_px = float(getattr(c, "price", 0.0) or 0.0)
        qty = float(getattr(c, "volume", getattr(o, "volume", 0.0)) or 0.0)
        side = "LONG" if int(getattr(o, "type", 0)) == 0 else "SHORT"
        cmt = str(getattr(c, "comment", "") or "")
        low = cmt.strip().lower()
        reason = "SL" if low.startswith("[sl") else ("TP" if low.startswith("[tp") else "MANUAL")
        sl, tp = sl_map.get(pid, (None, None))
        rr = None
        try:
            if sl is not None and entry_px:
                risk = abs(entry_px - float(sl))
                if risk > 0:
                    rr = round(profit / risk, 3)
        except Exception:  # noqa: BLE001
            rr = None
        close_ts = datetime.fromtimestamp(int(getattr(c, "time", 0)), timezone.utc).isoformat()
        lg.append("CLOSE", order_id=pid, position_id=pid, side=side, qty=qty, price=exit_px,
                  reason=reason, broker_comment=cmt, broker_time_utc=close_ts)
        lg.append("PNL", order_id=pid, position_id=pid, pnl=profit, entry=entry_px, exit=exit_px,
                  qty=qty, side=side, reason=reason, realized_R=rr, sl=sl, tp=tp, broker_time_utc=close_ts,
                  commission=round(float(getattr(c, "commission", 0.0) or 0.0), 2),
                  swap=round(float(getattr(c, "swap", 0.0) or 0.0), 2))
        out.append({"position_id": pid, "side": side, "reason": reason, "pnl": profit, "realized_R": rr})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=False)
    ap.add_argument("--exec", dest="exec_mode", default="dry")
    args = ap.parse_args()
    if args.exec_mode == "live":
        print(json.dumps({"REFUSED": "LIVE_NOT_PERMITTED"})); return
    env = load_env()
    cfg = {}
    cp = os.path.join(ROOT, "registry", "runtime_config.json")
    if os.path.exists(cp):
        try:
            cfg = json.load(open(cp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cfg = {}
    # env overrides the persisted runtime config (the gateway does not reliably propagate env to jobs)
    src = (os.environ.get("V1_SIGNAL_SOURCE") or cfg.get("signal_source") or "NONE").upper()
    lg = Ledger(LEDGER)
    chain_ok, n, bad = lg.verify()
    res = {"ts_utc": NOW, "mode": ("dry-run" if args.exec_mode != "demo" else "exec-demo"),
            "signal_source": src, "ledger_entries_before": n, "ledger_chain_ok": chain_ok,
            "SIGNAL_TYPE": "BASELINE_CONTROL", "NOT_HERMES_ALPHA": True, "order_sent": False}
    # ---- watchdog / missed-cycle observability (D008): report the gap since the last DECISION ----
    _dec = [r for r in _ledger_rows(LEDGER) if r.get("event") == "DECISION"]
    _gap_min = None
    if _dec:
        try:
            _gap_min = round((datetime.now(timezone.utc) - datetime.fromisoformat(_dec[-1]["ts_utc"])).total_seconds() / 60.0, 1)
        except Exception:  # noqa: BLE001
            _gap_min = None
    res["schedule_gap_minutes"] = _gap_min
    if _gap_min is not None and _gap_min > 25:
        res["watchdog"] = f"GAP_DETECTED:{_gap_min}min"
    if not chain_ok:
        lg.append("DECISION", action="HALT", reason=f"LEDGER_CHAIN_BROKEN:{bad}")
        print(json.dumps({**res, "action": "HALT"})); return
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize(**mt5_kwargs(env)):
            lg.append("DECISION", action="HALT", reason="MT5_INIT_FAILED")
            print(json.dumps({**res, "action": "HALT", "reason": "MT5_INIT_FAILED"})); return
        ai = mt5.account_info()
        is_demo = ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        okd, why = DemoGate.assert_demo({"trade_mode": "DEMO" if is_demo else "REAL", "real_money": not is_demo})
        _pos_raw = mt5.positions_get()
        positions = _pos_raw or []
        _positions_ok = _pos_raw is not None          # fail-closed: None => unknown position state
        if not okd:
            mt5.shutdown(); lg.append("DECISION", action="HALT", reason=f"DEMO_GATE:{why}")
            print(json.dumps({**res, "action": "HALT", "reason": f"DEMO_GATE:{why}"})); return
        # ---- broker-close reconciliation: the broker owns SL/TP exits, so observe them (CLOSE + PNL) ----
        _reconcile_ok = True
        try:
            _closes = reconcile_broker_closes(mt5, lg)
            res["reconciled_closes"] = len(_closes)
            if _closes:
                res["reconciled_detail"] = _closes
        except Exception as _e:  # noqa: BLE001
            _reconcile_ok = False                     # fail-closed: PnL counters may under-count
            res["reconcile_error"] = str(_e)[:150]
        snap = snapshot(mt5)
        atr = atr_m15(mt5)
        # risk state is rebuilt from the ledger CLOSE/PNL facts => persists across cycles
        _events = _ledger_rows(LEDGER)
        rg = rebuild_risk_state(RiskGuard(), _events, NOW[:10])
        # --- FAIL-CLOSED: any safety input we cannot determine => deny (WAIT_RISK) ---
        if not _reconcile_ok:
            rg.note_unavailable("PNL_STATE_UNKNOWN")
        # real inputs: same-source (server frame) staleness + last realised fill slippage
        _tick = mt5.symbol_info_tick(SYMBOL)
        _m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 3)
        _age = data_age_seconds(getattr(_tick, "time", None), _m1)
        _slip = last_realized_slippage_bps(_events)          # None => SLIPPAGE_UNKNOWN (deny)
        # kill switch: operator file; missing => OFF, unreadable => ON (fail-closed)
        _ks_on, _ks_reason = load_kill_switch(os.path.join(ROOT, "registry"))
        if _ks_on:
            rg.set_kill_switch(True, _ks_reason)
        # duplicate-order dedup: one entry per symbol per M15 bucket, persisted via the ledger
        _bucket = bar_bucket(_m1)
        _dedup = dedup_key(MAGIC, SYMBOL, _bucket) if _bucket is not None else None
        _already = rebuild_sent_keys(_events)
        _broker_orders = []
        try:
            _broker_orders = [{"magic": getattr(o, "magic", 0), "symbol": getattr(o, "symbol", ""),
                               "time_done": getattr(o, "time_done", 0)}
                              for o in (mt5.history_orders_get(datetime.now(timezone.utc) - timedelta(hours=2),
                                                               datetime.now(timezone.utc) + timedelta(minutes=1)) or [])]
        except Exception:  # noqa: BLE001
            _broker_orders = []
        if broker_recent_order_dup(_broker_orders, MAGIC, SYMBOL, _bucket):
            rg.note_unavailable("DUPLICATE_ORDER")        # broker filled but local ledger unconfirmed
        intent = {"order_id": _dedup, "already_sent": _already}
        allow, reasons = rg.evaluate(intent, {"spread_bps": (snap or {}).get("spread_bps"),
                                                "slippage_bps": _slip,
                                                "data_age_seconds": _age},
                                      (len(positions) if _positions_ok else None))
        mapping = SB.load_mapping(MAPPING)
        if src == "BASELINE_TRANSITION":
            ls = live_state_family(mt5)
            sig = SB.signal_for_state(ls.get("state"), mapping)
            use_atr = ls.get("atr") if ls.get("atr") else atr
            oi = SB.order_intent(sig, ls.get("trend_20"), use_atr, (snap or {}).get("ask"), (snap or {}).get("digits", 2))
        elif src in SIGNAL_SOURCES:
            ls, sig, oi = {}, {"known": False}, {"trade": False, "reason": "SIGNAL_SOURCE_NONE"}
        else:
            ls, sig, oi = {}, {"known": False}, {"trade": False, "reason": f"UNKNOWN_SIGNAL_SOURCE:{src}"}
        action = "WAIT"
        if positions:
            action = "WAIT_POSITION_OPEN"
        elif not allow:
            action = "WAIT_RISK:" + ",".join(reasons)
        elif not oi.get("trade"):
            action = "WAIT_SIGNAL:" + str(oi.get("reason"))
        elif args.exec_mode != "demo":
            action = "WOULD_ENTER"
        else:
            action = "ENTER"
        lg.append("DECISION", action=action, signal_source=src, signal=sig, order_intent=oi, live_state=ls,
                   risk_allow=bool(allow), risk_reasons=reasons, snapshot=snap, atr=atr,
                   account_positions=len(positions), account_login=ai.login, signal_type="BASELINE_CONTROL",
                   not_hermes_alpha=True)
        res.update({"action": action, "signal": sig, "order_intent": oi, "live_state": ls, "risk_allow": bool(allow),
                     "risk_reasons": reasons, "snapshot": snap, "atr": atr, "account_positions": len(positions),
                     "risk_daily_loss": rg.daily_loss, "risk_consecutive_losses": rg.consecutive_losses,
                     "data_age_seconds": _age, "slippage_bps_used": _slip,
                     "kill_switch": rg.kill_switch, "kill_reason": rg.kill_reason, "dedup_key": _dedup,
                     "risk_unavailable": rg.unavailable,
                     "mapping_hash": mapping.get("mapping_hash", "")[:16]})
        if action == "ENTER" and oi.get("trade"):
            req_base = {"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": float(oi["lots"]),
                         "type": mt5.ORDER_TYPE_BUY if oi["side"] == "LONG" else mt5.ORDER_TYPE_SELL,
                         "price": snap["ask"] if oi["side"] == "LONG" else snap["bid"],
                         "sl": float(oi["sl"]), "tp": float(oi["tp"]), "magic": MAGIC, "comment": COMMENT,
                         "type_time": mt5.ORDER_TIME_GTC}
            # ---- preflight ONLY: order_check never places an order ----
            tf_name, tf, fm, probes = pick_filling(mt5, SYMBOL, req_base)
            chk_ok = tf is not None
            lg.append("ORDER_CHECK", order_id=None, side=oi["side"], lots=oi["lots"], price=req_base["price"],
                       sl=req_base["sl"], tp=req_base["tp"], magic=MAGIC, symbol=SYMBOL,
                       filling_bitmask=fm, filling_name=tf_name, type_filling_value=tf,
                       probes=probes, ok=chk_ok, last_error=str(mt5.last_error()))
            req = dict(req_base)
            if chk_ok:
                req["type_filling"] = tf
            res.update({"filling_bitmask": fm, "filling_name": tf_name, "type_filling_value": tf,
                         "ORDER_CHECK": "PASS" if chk_ok else "FAIL", "probes": probes,
                         "check_retcode": (probes[-1]["retcode"] if probes else None)})
            send_enabled = bool((cfg or {}).get("order_send_enabled", False))
            if not chk_ok:
                _last_rc = (probes[-1]["retcode"] if probes else None)
                lg.append("DECISION", action="BLOCKED_ORDER_CHECK", reason=f"ORDER_CHECK_FAILED:{_last_rc}",
                           filling_name=tf_name, retcode=_last_rc, probes=probes)
                res.update({"action": "BLOCKED_ORDER_CHECK", "order_sent": False,
                             "send_blocked_reason": f"ORDER_CHECK_FAILED:{_last_rc}"})
            elif not send_enabled:
                lg.append("DECISION", action="READY_NOT_SENT", reason="ORDER_SEND_DISABLED", filling_name=tf_name)
                res.update({"action": "READY_NOT_SENT", "order_sent": False, "send_blocked_reason": "ORDER_SEND_DISABLED"})
            else:
                rid = lg.append("ORDER_REQUEST", side=oi["side"], lots=oi["lots"], price=req["price"], sl=req["sl"], tp=req["tp"],
                                 magic=MAGIC, comment=COMMENT, mapping_id=SB.MAPPING_ID, filling_name=tf_name,
                                 dedup_key=_dedup)
                import time as _t
                _t0 = _t.perf_counter()
                r = mt5.order_send(req)
                latency_ms = round((_t.perf_counter() - _t0) * 1000.0, 2)
                fill_px = getattr(r, "price", None) if r else None
                try:
                    slip_bps = (round((float(fill_px) - float(req["price"])) / float(req["price"]) * 1e4, 4)
                                if (fill_px and req["price"]) else None)
                except Exception:  # noqa: BLE001
                    slip_bps = None
                ok_send = bool(r and r.retcode == mt5.TRADE_RETCODE_DONE and getattr(r, "order", None))
                lg.append("ORDER_SEND", order_id=str(getattr(r, "order", None)), retcode=getattr(r, "retcode", None),
                           side=oi["side"], qty=oi["lots"], price=req["price"], fill_price=fill_px,
                           sl=req["sl"], tp=req["tp"], magic=MAGIC, comment=COMMENT, ok=ok_send,
                           latency_ms=latency_ms, slippage_bps=slip_bps, filling_name=tf_name,
                           dedup_key=_dedup, broker_comment=getattr(r, "comment", ""))
                if ok_send:
                    lg.append("FILL", order_id=str(r.order), price=getattr(r, "price", req["price"]), qty=oi["lots"])
                    lg.append("POSITION", order_id=str(r.order), ticket=getattr(r, "deal", None), sl=req["sl"], tp=req["tp"],
                               magic=MAGIC, comment=COMMENT)
                    res.update({"TICKET": str(getattr(r, "order", "")), "DEAL": str(getattr(r, "deal", "")),
                                 "SIDE": oi["side"], "ENTRY": fill_px, "SL": req["sl"], "TP": req["tp"],
                                 "MAGIC": MAGIC, "order_sent": True, "retcode": getattr(r, "retcode", None),
                                 "latency_ms": latency_ms, "slippage_bps": slip_bps, "ledger_seq": rid["seq"]})
                else:
                    res.update({"order_sent": False, "retcode": getattr(r, "retcode", None),
                                 "latency_ms": latency_ms, "slippage_bps": slip_bps,
                                 "broker_comment": getattr(r, "comment", "")})
        mt5.shutdown()
    except Exception as e:  # noqa: BLE001
        lg.append("DECISION", action="HALT", reason=f"EXCEPTION:{str(e)[:120]}")
        res.update({"action": "HALT", "reason": str(e)[:200]})
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(res, open(REPORT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(res, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
