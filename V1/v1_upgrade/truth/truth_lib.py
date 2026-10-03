# -*- coding: utf-8 -*-
"""truth_lib.py — V1 Truth/Forensic System core library (READ-ONLY w.r.t. trading; append-only evidence).

Layers (never mixed):
  Raw Facts      : MT5 broker responses, market data, ledger events (as recorded)
  Derived Facts  : ids, cases, incidents, consistency checks, daily aggregates (recomputable)
  Interpretation : written by humans/AI in reports only; never stored as fact.

Boundary: this module never sends orders, never changes signals, never bypasses RiskGuard.
If a key safety evidence record cannot be written, callers must record UNKNOWN and go to a
safe state (no new entry) — never fake PASS.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

TRUTH_VERSION = "v1-truth-1"
SCHEMA_VERSION = 1
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # v1_upgrade
EVID = os.path.join(BASE, "truth", "evidence")
LEDGER = os.path.join(BASE, "ledger", "v1_upgrade_ledger.jsonl")
REGISTRY = os.path.join(BASE, "registry")
SNAP = os.path.join(EVID, "decision_snapshots.jsonl")
INCIDENTS = os.path.join(EVID, "incidents.jsonl")
BROKER_FACTS = os.path.join(EVID, "broker_facts.json")
CASES = os.path.join(EVID, "cases")
DAILY = os.path.join(EVID, "daily")
SERVER_OFF_SEC = 10800


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def load_ledger(path=LEDGER):
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    rows.append({"_malformed": True, "_raw": line[:200]})
    return rows


def event_id(rec):
    """Deterministic event id: stable for the same chain position."""
    return "V1E-" + sha_obj({"seq": rec.get("seq"), "h": rec.get("current_hash"), "e": rec.get("event")})[:12]


def cycle_id_for(rec):
    cid = rec.get("cycle_id")
    if cid:
        return cid
    ts = str(rec.get("ts_utc") or "")
    return "V1C-" + ts[:19].replace("-", "").replace(":", "") if ts else "V1C-UNKNOWN"


def make_cycle_id(now_iso):
    return "V1C-" + str(now_iso)[:19].replace("-", "").replace(":", "")


def make_decision_id(cycle_id, action):
    return "V1D-" + sha_obj({"c": cycle_id, "a": action})[:10]


def trade_id(position_id):
    return "V1T-" + str(position_id)


def incident_id(kind, key):
    return "V1I-" + str(kind)[:10].upper() + "-" + sha_obj({"k": key})[:8].upper()


# ---------------------------------------------------------------- append-only evidence (self-hashed chains)
def append_evidence(path, obj):
    """Append one record with a per-file hash chain. Never overwrites. Returns the stored record."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    prev = "0" * 64
    n = 0
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    prev = e.get("sha256") or prev
                    n = e.get("si") or n
                except Exception:  # noqa: BLE001
                    continue
    rec = {"si": n + 1, "ts_utc": _now(), "prev": prev, **obj}
    rec["sha256"] = sha_obj({k: v for k, v in rec.items() if k != "sha256"})
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return rec


def read_evidence(path):
    out = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    out.append({"_malformed": True})
    return out


def verify_evidence(path):
    prev, ok, n = "0" * 64, True, 0
    for e in read_evidence(path):
        n += 1
        if e.get("_malformed") or e.get("prev") != prev or e.get("sha256") != sha_obj({k: v for k, v in e.items() if k != "sha256"}):
            ok = False
            break
        prev = e["sha256"]
    return ok, n


# ---------------------------------------------------------------- decision snapshot (write BEFORE execution)
def write_decision_snapshot(snap):
    """Append the immutable Decision Snapshot. Caller must treat any exception as RECORD FAILURE."""
    return append_evidence(SNAP, snap)


# ---------------------------------------------------------------- broker facts cache (raw layer, appended by cycle)
def refresh_broker_facts(mt5, cycle_id):
    try:
        ai = mt5.account_info()
        tk = mt5.symbol_info_tick("XAUUSD")
        frm = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=12)
        to = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        deals = mt5.history_deals_get(frm, to) or []
        ords = mt5.history_orders_get(frm, to) or []
        pos = mt5.positions_get() or []
        facts = {"cycle_id": cycle_id, "read_utc": _now(),
                 "account": {"login": getattr(ai, "login", None), "balance": getattr(ai, "balance", None),
                             "equity": getattr(ai, "equity", None), "trade_mode": getattr(ai, "trade_mode", None)},
                 "tick_srv": int(getattr(tk, "time", 0) or 0),
                 "positions": [{"ticket": p.ticket, "magic": p.magic, "volume": p.volume, "type": p.type,
                                "sl": p.sl, "tp": p.tp, "profit": p.profit} for p in pos],
                 "deals": [{k: getattr(d, k, None) for k in ("ticket", "order", "time", "type", "entry", "magic",
                                                              "position_id", "volume", "price", "commission", "swap",
                                                              "profit", "comment")} for d in deals],
                 "orders": [{k: getattr(o, k, None) for k in ("ticket", "time_setup", "time_done", "type", "state",
                                                               "magic", "position_id", "price_open", "comment")} for o in ords]}
        tmp = BROKER_FACTS + ".tmp"
        json.dump(facts, open(tmp, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)
        os.replace(tmp, BROKER_FACTS)
        return True
    except Exception:  # noqa: BLE001
        return False


def load_broker_facts():
    if os.path.exists(BROKER_FACTS):
        try:
            return json.load(open(BROKER_FACTS, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
    return None


# ---------------------------------------------------------------- consistency checks (per cycle, non-invasive)
def _last_decisions(rows, n=2):
    return [r for r in rows if r.get("event") == "DECISION"][-n:]


def cycle_consistency(mt5, lg, res, cycle_id, persist=True):
    """Run the per-cycle consistency checks + incident generation. NEVER raises into the trader."""
    out = []
    try:
        refresh_broker_facts(mt5, cycle_id)
    except Exception:  # noqa: BLE001
        pass
    try:
        rows = load_ledger()
        facts = load_broker_facts()
        incs = detect_incidents(rows, facts, cycle_id=cycle_id)
        if persist:
            _persist_incidents(incs)
        out = [i["incident_id"] for i in incs]
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- incident detection
def _cid_dt(cid):
    try:
        return dt.datetime.strptime(str(cid)[4:], "%Y%m%dT%H%M%S").replace(tzinfo=dt.timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _in_cycle(rec, cid):
    d = _cid_dt(cid)
    if d is None:
        return True
    try:
        t = dt.datetime.fromisoformat(str(rec.get("ts_utc")))
    except Exception:  # noqa: BLE001
        return False
    return d <= t < d + dt.timedelta(minutes=15)


def detect_incidents(rows, facts=None, cycle_id=None):
    """Structural incidents are global; event-level incidents are scoped to `cycle_id` (its 15-min window).
    With cycle_id=None only structural incidents are produced (no historical flood)."""
    incs = []

    def add(kind, key, severity, first, affected, root="UNKNOWN", status="OPEN", evidence=None,
            resolution=None, validation=None):
        incs.append({"incident_id": incident_id(kind, key), "type": kind, "severity": severity,
                     "first_seen": first, "last_seen": first, "root_cause": root,
                     "affected_ids": affected, "status": status, "resolution": resolution, "validation": validation,
                     "evidence": evidence or {}, "cycle_id": cycle_id})

    # ledger integrity
    prev = "0" * 64
    for r in rows:
        if r.get("_malformed"):
            add("LEDGER_MALFORMED", f"seq{r.get('seq')}", "CRITICAL", _now(), [], "MALFORMED_LINE",
                evidence={"seq": r.get("seq")})
            break
        if r.get("previous_hash") != prev:
            add("LEDGER_MISMATCH", f"seq{r.get('seq')}", "CRITICAL", r.get("ts_utc"), [], "CHAIN_BREAK",
                evidence={"seq": r.get("seq")})
            break
        prev = r.get("current_hash")
    seqs = [r.get("seq") for r in rows if r.get("seq")]
    if seqs and seqs != list(range(seqs[0], seqs[0] + len(seqs))):
        add("LEDGER_MISMATCH", "seq_gap", "CRITICAL", _now(), [], "SEQ_GAP")
    # schedule gap / restart
    decs = [r for r in rows if r.get("event") == "DECISION"]
    for a, b in zip(decs, decs[1:]):
        try:
            gap = (dt.datetime.fromisoformat(b["ts_utc"]) - dt.datetime.fromisoformat(a["ts_utc"])).total_seconds() / 60.0
        except Exception:  # noqa: BLE001
            continue
        if gap > 25:
            add("SCHEDULE_GAP", f"{a.get('seq')}->{b.get('seq')}", "MEDIUM", a.get("ts_utc"),
                [event_id(a), event_id(b)], f"GAP_{round(gap,1)}min", status="ACKNOWLEDGED",
                evidence={"gap_minutes": round(gap, 1)})
    # per-decision risk/anomaly incidents (only when scoped to a cycle)
    decs_scoped = [r for r in decs if cycle_id is not None and _in_cycle(r, cycle_id)]
    for r in decs_scoped:
        act = str(r.get("action") or "")
        if act.startswith("WAIT_RISK"):
            reasons = r.get("risk_reasons") or []
            sev = "LOW"
            if any(x in ("KILL_SWITCH",) for x in reasons):
                add("KILL_SWITCH", f"seq{r.get('seq')}", "HIGH", r.get("ts_utc"), [event_id(r)], evidence={"reasons": reasons})
            if "DUPLICATE_ORDER" in reasons:
                add("DUPLICATE_BLOCKED", f"seq{r.get('seq')}", "MEDIUM", r.get("ts_utc"), [event_id(r)], evidence={"reasons": reasons})
            if "STALE_DATA" in reasons:
                add("STALE_DATA", f"seq{r.get('seq')}", "MEDIUM", r.get("ts_utc"), [event_id(r)], evidence={"reasons": reasons})
            if any(str(x).endswith("_UNKNOWN") for x in reasons):
                add("MISSING_DATA", f"seq{r.get('seq')}", "MEDIUM", r.get("ts_utc"), [event_id(r)], evidence={"reasons": reasons})
            add("RISK_BLOCK", f"seq{r.get('seq')}", sev, r.get("ts_utc"), [event_id(r)], status="CLOSED",
                root="BY_DESIGN", resolution="guard denied new entry", validation="risk_reasons recorded",
                evidence={"reasons": reasons})
        if act.startswith("HALT") or act.startswith("WAIT_TRUTH"):
            add("UNKNOWN_EXCEPTION", f"seq{r.get('seq')}", "HIGH", r.get("ts_utc"), [event_id(r)],
                evidence={"action": act, "reason": r.get("reason")})
    # MT5 rejects / sends (scoped when a cycle is given)
    sends = [r for r in rows if r.get("event") == "ORDER_SEND"]
    if cycle_id is not None:
        sends = [r for r in sends if _in_cycle(r, cycle_id)]
    for s in sends:
        if s.get("ok") is False:
            add("MT5_REJECT", f"seq{s.get('seq')}", "MEDIUM", s.get("ts_utc"), [event_id(s)],
                root=f"RETCODE_{s.get('retcode')}", evidence={"retcode": s.get("retcode")})
    # order/fill/position linkage
    for i, s in enumerate(sends):
        if s.get("ok") and not any(x.get("event") == "FILL" and x.get("order_id") == s.get("order_id") for x in rows):
            add("ORDER_FILL_MISMATCH", f"send{s.get('seq')}", "HIGH", s.get("ts_utc"), [event_id(s)],
                evidence={"order_id": s.get("order_id")})
    # position / reconciliation / pnl vs broker facts
    if facts:
        bpos = [p for p in facts.get("positions", []) if int(p.get("magic") or 0) == 90011]
        ledger_open = set()
        for r in rows:
            if r.get("event") == "POSITION":
                ledger_open.add(str(r.get("order_id")))
            elif r.get("event") == "CLOSE":
                ledger_open.discard(str(r.get("order_id")))
        if {str(p.get("ticket")) for p in bpos} != ledger_open:
            add("POSITION_MISMATCH", "open_set", "HIGH", _now(),
                sorted({str(p.get("ticket")) for p in bpos} ^ ledger_open), evidence={"broker": sorted(str(p.get('ticket')) for p in bpos), "ledger": sorted(ledger_open)})
        deals = [d for d in facts.get("deals", []) if int(d.get("magic") or 0) == 90011]
        b_closed = {str(d.get("position_id")) for d in deals if d.get("entry") == 1}
        l_closed = {str(r.get("position_id")) for r in rows if r.get("event") == "CLOSE"}
        if b_closed != l_closed:
            add("RECONCILIATION_MISMATCH", "closed_set", "HIGH", _now(), sorted(b_closed ^ l_closed),
                evidence={"broker_only": sorted(b_closed - l_closed), "ledger_only": sorted(l_closed - b_closed)})
        b_profit = round(sum(float(d.get("profit") or 0) for d in deals if d.get("entry") == 1), 2)
        l_pnl = round(sum(float(r.get("pnl") or 0) for r in rows if r.get("event") == "PNL"), 2)
        if abs(b_profit - l_pnl) > 0.05:
            add("PNL_MISMATCH", "profit_sum", "HIGH", _now(), [], evidence={"broker_profit": b_profit, "ledger_pnl": l_pnl})
    return incs


def _persist_incidents(incs):
    existing = {i["incident_id"] for i in read_evidence(INCIDENTS)}
    for i in incs:
        if i["incident_id"] not in existing:
            append_evidence(INCIDENTS, i)


# ---------------------------------------------------------------- trade case
def build_case(position_id, rows=None, facts=None):
    rows = rows if rows is not None else load_ledger()
    facts = facts if facts is not None else load_broker_facts()
    tid = trade_id(position_id)
    pid = str(position_id)
    case = {"case_id": "CASE-" + tid, "trade_id": tid, "position_id": pid, "generated_utc": _now(),
            "protocol_version": TRUTH_VERSION, "schema_version": SCHEMA_VERSION, "links": {}, "chain": [],
            "raw": {}, "derived": {}, "unknowns": []}

    def push(stage, rec, link_method):
        if rec is None:
            case["chain"].append({"stage": stage, "status": "UNKNOWN", "note": "no evidence in ledger"})
            case["unknowns"].append(stage)
            return
        case["chain"].append({"stage": stage, "status": "OK", "event": rec.get("event"), "seq": rec.get("seq"),
                              "ts_utc": rec.get("ts_utc"), "event_id": event_id(rec), "link_method": link_method,
                              "data": {k: rec.get(k) for k in ("action", "risk_reasons", "order_intent", "signal",
                                                                 "side", "qty", "price", "sl", "tp", "pnl", "reason",
                                                                 "dedup_key", "cycle_id", "decision_id", "retcode",
                                                                 "slippage_bps", "broker_time_utc") if k in rec}})

    pos = next((r for r in rows if r.get("event") == "POSITION" and str(r.get("order_id")) == pid), None)
    send = next((r for r in rows if r.get("event") == "ORDER_SEND" and str(r.get("order_id")) == pid and r.get("ok")), None)
    close = next((r for r in rows if r.get("event") == "CLOSE" and str(r.get("position_id")) == pid), None)
    pnl = next((r for r in rows if r.get("event") == "PNL" and str(r.get("position_id")) == pid), None)
    dec = None
    if send is not None:
        cand = [r for r in rows if r.get("event") == "DECISION" and r.get("seq", 0) < send.get("seq", 0)]
        # prefer same cycle_id; else nearest preceding ENTER decision
        if send.get("cycle_id"):
            dec = next((r for r in reversed(cand) if r.get("cycle_id") == send.get("cycle_id")), None)
        if dec is None:
            dec = next((r for r in reversed(cand) if str(r.get("action")) in ("ENTER", "WOULD_ENTER")), None)
    ck = None
    oq = None
    if send is not None:
        cand = [r for r in rows if r.get("seq", 0) < send.get("seq", 0)]
        ck = next((r for r in reversed(cand) if r.get("event") == "ORDER_CHECK"), None)
        oq = next((r for r in reversed(cand) if r.get("event") == "ORDER_REQUEST"), None)
    method = "cycle_id" if (send and send.get("cycle_id")) else "time_adjacency(legacy)"
    push("signal_and_context", dec, method)
    push("risk_evaluation", dec, method)
    push("decision", dec, method)
    push("order_check", ck, method)
    push("order_request", oq, method)
    push("order_send", send, "order_id")
    push("fill", next((r for r in rows if r.get("event") == "FILL" and str(r.get("order_id")) == pid), None), "order_id")
    push("position", pos, "order_id")
    push("close", close, "position_id")
    push("pnl", pnl, "position_id")

    case["links"] = {"cycle_id": (send or dec or {}).get("cycle_id"), "decision_id": (send or dec or {}).get("decision_id"),
                     "order_id": pid, "trade_id": tid, "dedup_key": (send or {}).get("dedup_key")}
    # raw broker facts
    if facts:
        deals = [d for d in facts.get("deals", []) if str(d.get("position_id")) == pid]
        case["raw"]["broker_deals"] = deals
    else:
        case["unknowns"].append("broker_facts_cache_missing")
    # derived
    d_close = case["raw"].get("broker_deals") or []
    cl = next((d for d in d_close if d.get("entry") == 1), None)
    if cl:
        case["derived"] = {"gross_profit": cl.get("profit"), "commission": cl.get("commission"), "swap": cl.get("swap"),
                           "net": round(float(cl.get("profit") or 0) + float(cl.get("commission") or 0) + float(cl.get("swap") or 0), 2)}
        if pnl:
            case["derived"]["ledger_pnl_price_component"] = pnl.get("pnl")
            case["derived"]["consistent"] = abs(float(pnl.get("pnl") or 0) - float(cl.get("profit") or 0)) < 0.01
    else:
        case["derived"]["status"] = "OPEN_OR_UNRECONCILED"
    os.makedirs(CASES, exist_ok=True)
    p = os.path.join(CASES, tid + ".json")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(case, ensure_ascii=False, indent=1, default=str))
    return case


# ---------------------------------------------------------------- daily truth
def daily_truth(date_str, rows=None, facts=None):
    rows = rows if rows is not None else load_ledger()
    facts = facts if facts is not None else load_broker_facts()
    d0 = dt.date.fromisoformat(date_str)
    rep = {"report": "V1_DAILY_TRUTH", "date_utc": date_str, "generated_utc": _now(), "truth_version": TRUTH_VERSION,
           "FACTS_ONLY": True}
    def same_day(ts):
        try:
            return dt.datetime.fromisoformat(str(ts)).date() == d0
        except Exception:  # noqa: BLE001
            return False
    decs = [r for r in rows if r.get("event") == "DECISION" and same_day(r.get("ts_utc"))]
    rep["cycles"] = len(decs)
    rep["signals"] = sum(1 for r in decs if str(r.get("action", "")).startswith("ENTER") or str(r.get("action","")).startswith("WOULD"))
    rep["wait"] = sum(1 for r in decs if str(r.get("action", "")).startswith("WAIT_"))
    rep["risk_block"] = sum(1 for r in decs if str(r.get("action", "")).startswith("WAIT_RISK"))
    blocks = {}
    for r in decs:
        for x in (r.get("risk_reasons") or []):
            blocks[x] = blocks.get(x, 0) + 1
    rep["risk_blocks_by_reason"] = blocks
    sends = [r for r in rows if r.get("event") == "ORDER_SEND" and same_day(r.get("ts_utc"))]
    rep["orders"] = len(sends)
    rep["mt5_rejects"] = sum(1 for s in sends if s.get("ok") is False)
    rep["fills"] = sum(1 for r in rows if r.get("event") == "FILL" and same_day(r.get("ts_utc")))
    closes = [r for r in rows if r.get("event") == "CLOSE" and same_day((r.get("broker_time_utc") or r.get("ts_utc")))]
    rep["closes"] = len(closes)
    pnls = [r for r in rows if r.get("event") == "PNL" and same_day((r.get("broker_time_utc") or r.get("ts_utc")))]
    rep["pnl_price_component"] = round(sum(float(r.get("pnl") or 0) for r in pnls), 2)
    rep["commission"] = round(sum(float(r.get("commission") or 0) for r in pnls), 2)
    rep["swap"] = round(sum(float(r.get("swap") or 0) for r in pnls), 2)
    rep["net"] = round(rep["pnl_price_component"] + rep["commission"] + rep["swap"], 2)
    sp = [(r.get("snapshot") or {}).get("spread_bps") for r in decs if (r.get("snapshot") or {}).get("spread_bps") is not None]
    rep["spread_bps"] = {"n": len(sp), "max": max(sp) if sp else None, "mean": round(sum(sp) / len(sp), 4) if sp else None}
    rep["slippage_bps"] = [s.get("slippage_bps") for s in sends if s.get("slippage_bps") is not None]
    rep["schedule_gaps_gt25min"] = 0
    incs = [i for i in read_evidence(INCIDENTS) if str(i.get("first_seen", ""))[:10] == date_str]
    rep["incidents"] = [{"incident_id": i["incident_id"], "type": i["type"], "severity": i["severity"]} for i in incs]
    # integrity
    lg_ok, lg_n, lg_bad = _ledger_verify(rows)
    rep["ledger_integrity"] = {"ok": lg_ok, "entries": lg_n, "bad": lg_bad}
    ev_ok, ev_n = verify_evidence(SNAP)
    rep["evidence_snapshot_integrity"] = {"ok": ev_ok, "entries": ev_n}
    inc_ok, inc_n = verify_evidence(INCIDENTS)
    rep["incidents_file_integrity"] = {"ok": inc_ok, "entries": inc_n}
    rep["open_positions"] = _open_count(rows)
    os.makedirs(DAILY, exist_ok=True)
    json.dump(rep, open(os.path.join(DAILY, f"V1_DAILY_TRUTH_{date_str}.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    return rep


def _ledger_verify(rows):
    prev, ok, n = "0" * 64, True, 0
    for r in rows:
        n += 1
        if r.get("_malformed") or r.get("previous_hash") != prev:
            return False, n, f"mismatch at seq {r.get('seq')}"
        prev = r.get("current_hash")
    return ok, n, None


def _open_count(rows):
    s = set()
    for r in rows:
        if r.get("event") == "POSITION":
            s.add(str(r.get("order_id")))
        elif r.get("event") == "CLOSE":
            s.discard(str(r.get("order_id")))
    return len(s)


# ---------------------------------------------------------------- forensic queries
def forensic_trade(position_id):
    return build_case(position_id)


def forensic_incident(iid):
    """Latest state wins (append-only store: updates are appended; resolution returns the newest record)."""
    hits = [i for i in read_evidence(INCIDENTS) if i.get("incident_id") == iid]
    return hits[-1] if hits else None


def latest_incidents():
    by = {}
    for i in read_evidence(INCIDENTS):
        if i.get("incident_id"):
            by[i["incident_id"]] = i
    return list(by.values())


def forensic_cycle(cid):
    rows = load_ledger()
    evs = [r for r in rows if str(r.get("cycle_id") or "") == cid]
    if not evs:
        # legacy: match by derived cycle id from ts
        evs = [r for r in rows if cycle_id_for(r) == cid]
    return {"cycle_id": cid, "events": [{"event_id": event_id(r), "seq": r.get("seq"), "ts_utc": r.get("ts_utc"),
                                          "event": r.get("event"), "action": r.get("action"),
                                          "risk_reasons": r.get("risk_reasons")} for r in evs]}


def evidence_inventory():
    def h(p):
        return {"path": os.path.relpath(p, BASE).replace("\\", "/"), "exists": os.path.exists(p),
                "sha256": sha_file(p), "records": len(read_evidence(p)) if p.endswith(".jsonl") else None,
                "bytes": os.path.getsize(p) if os.path.exists(p) else None}
    return [h(LEDGER), h(SNAP), h(INCIDENTS), h(BROKER_FACTS)]
