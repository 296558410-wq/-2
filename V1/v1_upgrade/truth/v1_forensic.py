# -*- coding: utf-8 -*-
"""v1_forensic.py — One-Command Forensics CLI for the V1 Truth System (READ-ONLY).

Usage:
  python v1_forensic.py --trade V1T-2378322488        # full causal chain for a trade
  python v1_forensic.py --trade 2378322488            # (raw position id accepted too)
  python v1_forensic.py --incident V1I-...            # incident dossier
  python v1_forensic.py --cycle V1C-20261002T041802   # everything in one cycle
  python v1_forensic.py --date 2026-10-02             # daily Truth Report + incident index
  python v1_forensic.py --incidents                   # list incidents
  python v1_forensic.py --index                       # evidence inventory
Options: --json  (raw JSON out)
"""
from __future__ import annotations
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import truth_lib as TR  # noqa: E402


def p(o, as_json):
    if as_json:
        print(json.dumps(o, ensure_ascii=False, indent=1, default=str))
    return o


def show_trade(tid, as_json):
    pid = tid[4:] if str(tid).startswith("V1T-") else str(tid)
    case = TR.build_case(pid)
    if as_json:
        return p(case, True)
    print(f"== CASE {case['case_id']} ==")
    print(f"trade_id={case['trade_id']}  links={json.dumps(case['links'], ensure_ascii=False)}")
    print("--- chain (why -> what -> broker -> result) ---")
    for st in case["chain"]:
        if st.get("status") != "OK":
            print(f"  [UNKNOWN] {st['stage']}")
            continue
        d = st.get("data", {})
        extra = ""
        if st["stage"] == "signal_and_context":
            extra = f"signal={d.get('signal')}"
        elif st["stage"] == "risk_evaluation":
            extra = f"risk_allow={d.get('risk_allow')} reasons={d.get('risk_reasons')}"
        elif st["stage"] == "decision":
            extra = f"action={d.get('action')}"
        elif st["stage"] == "order_send":
            extra = f"ok_retcode={d.get('retcode')} slip={d.get('slippage_bps')}"
        elif st["stage"] == "close":
            extra = f"reason={d.get('reason')} broker_time={d.get('broker_time_utc')}"
        elif st["stage"] == "pnl":
            extra = f"pnl={d.get('pnl')}"
        print(f"  {st['stage']:<20} seq={st.get('seq')} ev={st.get('event_id')} {extra} ({st.get('link_method')})")
    print("--- raw broker deals ---")
    print(json.dumps(case["raw"].get("broker_deals", []), ensure_ascii=False, indent=1, default=str))
    print("--- derived (independent) ---")
    print(json.dumps(case["derived"], ensure_ascii=False))
    if case["unknowns"]:
        print("--- UNKNOWNS ---")
        print(json.dumps(case["unknowns"], ensure_ascii=False))
    return case


def show_incident(iid, as_json):
    inc = TR.forensic_incident(iid)
    if not inc:
        print(f"incident {iid} not found"); return None
    if as_json:
        return p(inc, True)
    print(f"== INCIDENT {inc['incident_id']} ==")
    for k in ("type", "severity", "status", "first_seen", "last_seen", "root_cause", "resolution", "validation"):
        print(f"  {k:<12} {inc.get(k)}")
    print(f"  affected_ids {inc.get('affected_ids')}")
    print(f"  evidence     {json.dumps(inc.get('evidence'), ensure_ascii=False)}")
    return inc


def show_cycle(cid, as_json):
    r = TR.forensic_cycle(cid)
    if as_json:
        return p(r, True)
    print(f"== CYCLE {cid} ==  events={len(r['events'])}")
    for e in r["events"]:
        print(f"  seq={e['seq']:<5} {e['ts_utc'][:19]} {e['event']:<14} {str(e.get('action') or '')} {str(e.get('risk_reasons') or '')}")
    return r


def show_date(d, as_json):
    rep = TR.daily_truth(d)
    if as_json:
        return p(rep, True)
    print(f"== DAILY TRUTH {d} (FACTS_ONLY) ==")
    for k in ("cycles", "signals", "wait", "risk_block", "orders", "mt5_rejects", "fills", "closes", "open_positions",
              "pnl_price_component", "commission", "swap", "net", "spread_bps", "risk_blocks_by_reason",
              "ledger_integrity", "evidence_snapshot_integrity", "incidents_file_integrity", "incidents"):
        print(f"  {k:<28} {json.dumps(rep.get(k), ensure_ascii=False, default=str)[:220]}")
    return rep


def main():
    ap = argparse.ArgumentParser(prog="v1 forensic")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--trade"); g.add_argument("--incident"); g.add_argument("--cycle")
    g.add_argument("--date"); g.add_argument("--incidents", action="store_true"); g.add_argument("--index", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.trade:
        show_trade(a.trade, a.json)
    elif a.incident:
        show_incident(a.incident, a.json)
    elif a.cycle:
        show_cycle(a.cycle, a.json)
    elif a.date:
        show_date(a.date, a.json)
    elif a.incidents:
        for i in TR.latest_incidents():
            print(f"  {i['incident_id']:<32} {i['type']:<24} {i['severity']:<9} {i['status']:<12} {str(i.get('first_seen'))[:19]}")
    elif a.index:
        for e in TR.evidence_inventory():
            print(f"  {e['path']:<45} exists={e['exists']} sha256={str(e['sha256'])[:16]} records={e['records']} bytes={e['bytes']}")


if __name__ == "__main__":
    main()
