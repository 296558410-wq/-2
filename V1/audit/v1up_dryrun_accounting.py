# -*- coding: utf-8 -*-
"""v1up_dryrun_accounting.py — run ONE production `cycle.py --dry-run` and account for every ledger write.

Honest accounting (task book): a dry-run is NOT zero-side-effect on the ledger — it may append a
DECISION and reconcile CLOSE/PNL. This script records the ledger BEFORE, runs the dry-run, then
classifies NEW events, and hard-fails the verdict if any ORDER_SEND / ORDER_CHECK / FILL / POSITION
appears among them (that would mean a real order side effect => PATCH_BLOCKED).
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, subprocess

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_upgrade")
AUDIT = os.path.join(BASE, "audit")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
CYCLE = os.path.join(ROOT, "cycle.py")
ORDERISH = {"ORDER_SEND", "ORDER_CHECK", "FILL", "POSITION", "ORDER_REQUEST"}


def snap():
    raw = open(LEDGER, "rb").read()
    lines = [l for l in raw.decode("utf-8").splitlines() if l.strip()]
    evs = [json.loads(l) for l in lines]
    return {"sha256": hashlib.sha256(raw).hexdigest(), "lines": len(lines),
            "last_seq": evs[-1]["seq"] if evs else 0, "last_event": evs[-1]["event"] if evs else None,
            "utc": dt.datetime.now(dt.timezone.utc).isoformat()}, lines


before, _ = snap()
proc = subprocess.run([PY, CYCLE, "--dry-run"], capture_output=True, text=True, timeout=300,
                      cwd=r"C:\AIQuant")
after, lines = snap()

ledger_rows = [json.loads(l) for l in lines]
new_rows = [r for r in ledger_rows if r["seq"] > before["last_seq"]]
new_events = [r["event"] for r in new_rows]
new_orderish = [r for r in new_rows if r["event"] in ORDERISH]
try:
    cycle_out = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
except Exception:  # noqa: BLE001
    cycle_out = {"_raw_tail": proc.stdout[-400:]}

# chain verify on the live ledger (post dry-run)
import sys
sys.path.insert(0, ROOT)
import gates  # noqa: E402
ok, n, bad = gates.Ledger(LEDGER).verify()

verdict = "DRYRUN_OK_NO_ORDER_SIDE_EFFECT" if (not new_orderish and cycle_out.get("order_sent") is False) else "DRYRUN_BLOCKED"
doc = {
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "note": "a --dry-run is NOT zero-side-effect: it appends DECISION and may append reconciled CLOSE/PNL; it never sends an order and (in dry mode) never calls order_check",
    "before": before, "after": after,
    "cycle_exit": proc.returncode,
    "cycle_action": cycle_out.get("action"),
    "cycle_order_sent": cycle_out.get("order_sent"),
    "cycle_risk_allow": cycle_out.get("risk_allow"),
    "cycle_risk_reasons": cycle_out.get("risk_reasons"),
    "cycle_risk_daily_loss": cycle_out.get("risk_daily_loss"),
    "cycle_risk_consecutive_losses": cycle_out.get("risk_consecutive_losses"),
    "cycle_data_age_seconds": cycle_out.get("data_age_seconds"),
    "cycle_slippage_bps_used": cycle_out.get("slippage_bps_used"),
    "new_event_count": len(new_rows),
    "new_events": new_events,
    "new_orderish_events": [r["event"] for r in new_orderish],
    "new_events_detail": [{"seq": r["seq"], "ts_utc": r["ts_utc"], "event": r["event"],
                           "action": r.get("action")} for r in new_rows],
    "ledger_chain_after": {"ok": ok, "entries": n, "bad": bad},
    "verdict": verdict,
}
json.dump(doc, open(os.path.join(AUDIT, "V1_DRYRUN_ACCOUNTING.json"), "w", encoding="utf-8", newline="\n"),
          indent=1, ensure_ascii=False)
print(json.dumps({k: doc[k] for k in ("before", "after", "cycle_exit", "cycle_action", "cycle_order_sent",
                                      "cycle_risk_allow", "cycle_risk_reasons", "cycle_risk_daily_loss",
                                      "cycle_risk_consecutive_losses", "cycle_data_age_seconds",
                                      "cycle_slippage_bps_used", "new_event_count", "new_events",
                                      "new_orderish_events", "ledger_chain_after", "verdict")},
                 ensure_ascii=False, indent=1))
