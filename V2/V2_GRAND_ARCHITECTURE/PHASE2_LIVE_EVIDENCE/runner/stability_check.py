"""Daily stability self-check (spec section 18).

Checks scheduler / data router / agent1 / agent2 / context / discovery /
strategy factory / strategy brain / outcome engine / ledger / replay / shadow
modules. Any anomaly -> FAIL-CLOSED for the RESEARCH component only; it never
affects production. Also enforces the hard boundary: runner code must never
import MetaTrader5 or call order_send/order_check.

CLI:  python runner/stability_check.py
"""
from __future__ import annotations
import os
import sys
import glob
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402

SHADOW_MODULES = ["shadow_stack.py", "backfill.py", "gpu_batch.py", "analytics.py",
                  "build.py", "make_manifest.py", "stability_check.py", "paths.py",
                  "heartbeat.py"]


def _boundary_scan():
    """Static proof the shadow path never touches MT5 order APIs.
    Scans only the OTHER runner modules (skips this scanner itself, which
    necessarily contains the needles as literals)."""
    self_name = os.path.basename(os.path.abspath(__file__))
    # real boundary = a call to an MT5 order API or an MT5 import (prose mentions
    # of the demo/live mode names in docs are not violations)
    needles = ("order_send(", "order_check(", "MetaTrader5")
    bad = []
    for p in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "*.py")):
        if os.path.basename(p) == self_name:
            continue
        txt = open(p, encoding="utf-8").read()
        for needle in needles:
            if needle in txt:
                bad.append({"file": os.path.basename(p), "needle": needle})
    return {"risk_flags": len(bad), "clean": not bad, "findings": bad}


def run_check():
    PP.ensure_dirs()
    health = PP.read_health()
    active = PP.read_active_run()
    checks = {}

    # production components (read-only observation)
    checks["scheduler"] = {"ok": health.get("scheduler") is not None,
                           "value": health.get("scheduler")}
    checks["data_router"] = {"ok": health.get("router_enabled") is not None,
                             "value": health.get("router_enabled")}
    checks["agent1"] = {"ok": health.get("agent1_status") == "OK", "value": health.get("agent1_status")}
    checks["agent2"] = {"ok": health.get("agent2_status") == "OK", "value": health.get("agent2_status")}
    checks["hermes_context"] = {"ok": health.get("hermes_status") == "OK", "value": health.get("hermes_status")}
    checks["ledger"] = {"ok": health.get("ledger_status") == "OK", "value": health.get("ledger_status")}
    checks["replay"] = {"ok": health.get("replay_status") == "MATCH", "value": health.get("replay_status")}
    checks["run_status"] = {"ok": health.get("run_status") == "RUNNING", "value": health.get("run_status")}
    checks["production_blocked"] = {"ok": health.get("blocked") in (None, {}), "value": health.get("blocked")}

    # shadow research modules present
    here = os.path.dirname(os.path.abspath(__file__))
    missing = [m for m in SHADOW_MODULES if not os.path.exists(os.path.join(here, m))]
    checks["shadow_modules"] = {"ok": not missing, "value": {"missing": missing}}
    checks["shadow_registry"] = {"ok": os.path.exists(PP.SHADOW_REGISTRY),
                                 "value": os.path.basename(PP.SHADOW_REGISTRY)}
    checks["outcome_engine"] = {"ok": os.path.exists(PP.OUTCOMES), "value": os.path.basename(PP.OUTCOMES)}

    scan = _boundary_scan()
    checks["boundary_order_api"] = {"ok": scan["clean"], "value": scan}

    # FAIL-CLOSED for the research component
    failed = [k for k, v in checks.items() if not v["ok"]]
    status = "PASS" if not failed else "FAIL"
    result = {
        "generated_utc": PP.now_utc(),
        "status": status,
        "failed": failed,
        "checks": checks,
        "active_run": active.get("run_id"),
        "note": "research-component self-check; production is observed read-only and never modified",
    }
    PP.write_json_if_changed(PP.STATE, result, ignore_keys=("generated_utc",))
    PP.log_event("stability_check", {"status": status, "failed": failed})
    print(f"[stability_check] status={status} failed={failed}")
    if status != "PASS":
        sys.exit(1)
    return result


def main():
    run_check()


if __name__ == "__main__":
    main()
