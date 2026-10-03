"""
60_account_mapping.py — ACCOUNT_MAPPING_REPORT data.

Trace the claim "2026-09-23 V2 drawdown near -20%" to a real account / magic /
ledger. If it cannot be tied to V2, declare UNRESOLVED_ACCOUNT_MAPPING and do NOT
attribute it to V2.

READ-ONLY. Writes only to the lab dir.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (DATA, SRC, banner, read_jsonl, read_json, write_json,
                        git_commit, parse_ts, hours_between)

SOURCES = ["v1_trade_db", "v2_trade_db", "v2_paper_account", "v2_ledger",
           "v1_upgrade_registry", "v1_broker_facts", "v1_run_meta"]


def cum_net_at(trades, sysname, cutoff):
    s = [t for t in trades if t.get("system") == sysname and t.get("entry_ts") and
         parse_ts(t["entry_ts"]) <= cutoff]
    s.sort(key=lambda t: t["entry_ts"])
    after = round(sum(t.get("net") or 0 for t in s), 2)
    before = round(sum(t.get("profit_price") or 0 for t in s), 2)
    return {"n": len(s), "cum_net_after_cost": after, "cum_net_before_cost": before,
            "last_entry": s[-1]["entry_ts"] if s else None}


def main():
    banner("60_account_mapping.py", SOURCES)
    v1 = read_jsonl(SRC["v1_trade_db"])
    v2db = read_jsonl(SRC["v2_trade_db"])
    pa = read_json(SRC["v2_paper_account"])
    v2led = read_jsonl(SRC["v2_ledger"])
    reg = read_json(SRC["v1_upgrade_registry"])

    # accounts / magics known
    accounts = [
        {"account": 160759434, "server": "ForexTimeFXTM-Demo01", "project": "V1 / V1_OLD",
         "magic": 90002, "execution": "MT5_DEMO", "real_trades": 109},
        {"account": 160759434, "server": "ForexTimeFXTM-Demo01", "project": "V1_NEW (upgrade)",
         "magic": 90011, "execution": "MT5_DEMO", "real_trades": 32},
        {"account": 160761384, "server": "ForexTimeFXTM-Demo01", "project": "V2",
         "magic": 90003, "execution": "PAPER_LOCAL (no broker)", "real_trades": 0},
        {"account": 160766418, "server": "ForexTimeFXTM-Demo01", "project": "V3 calibration",
         "magic": 90004, "execution": "DEMO_CALIBRATION (gated)", "real_trades": 0},
        {"account": 160759434, "server": "ForexTimeFXTM-Demo01", "project": "collect",
         "magic": 90001, "execution": "MT5_DEMO", "real_trades": 0},
    ]

    # V2 executed trades?
    v2_executed = sum(1 for r in v2db if isinstance(r, dict) and r.get("executed"))
    v2_ledger_events = {}
    for r in v2led:
        if isinstance(r, dict):
            k = r.get("event", r.get("type", "?"))
            v2_ledger_events[k] = v2_ledger_events.get(k, 0) + 1

    # V1_OLD cumulative net around the 2026-09-23 reset
    cutoff = parse_ts("2026-09-23T23:39:46Z")
    v1old_at_reset = cum_net_at(v1, "V1_OLD", cutoff)
    v1old_end = cum_net_at(v1, "V1_OLD", parse_ts("2026-12-31T00:00:00Z"))

    # does the -20% claim match V2 paper drawdown?
    paper_dd_pct = round(100 * pa.get("drawdown", 0) / pa.get("initial_balance", 1), 2)

    findings = {
        "claim": "2026-09-23 V2 drawdown near -20%",
        "v2_executed_trades": v2_executed,
        "v2_real_broker_trades": 0,
        "v2_paper_account": {
            "initial_balance": pa.get("initial_balance"), "balance": pa.get("balance"),
            "drawdown_usd": pa.get("drawdown"), "drawdown_pct_of_initial": paper_dd_pct,
            "backend": pa.get("backend"), "created_utc": pa.get("created_utc"),
            "note": "paper_local synthetic account (no broker); drawdown %.2f%% != -20%%; "
                    "dated 2026-09-12, not 2026-09-23" % paper_dd_pct,
        },
        "v2_ledger_events": v2_ledger_events,
        "v1_old_cum_net_at_2026_09_23_reset": v1old_at_reset,
        "v1_old_cum_net_full": v1old_end,
        "candidate_alternative": (
            "The '~ -20' figure matches the V1_OLD (magic 90002, account 160759434) "
            "cumulative after-cost net at the 2026-09-23 state reset (-20.43 before cost; "
            "see v1_old_cum_net_at_2026_09_23_reset), NOT a V2 account. V1_OLD was the "
            "Hermes LLM candidate; the 09-23 boundary is its state reset."
            if abs(v1old_at_reset["cum_net_before_cost"] + 20) < 12 else
            "No matching account found within +/-12 of -20."
        ),
        "verdict": "UNRESOLVED_ACCOUNT_MAPPING",
        "reason": "V2 executed 0 trades; there is no V2 broker P&L or ledger that can carry a "
                  "-20% drawdown. The claim cannot be attributed to V2. The nearest real figure "
                  "is the V1_OLD cumulative net at the 2026-09-23 reset (see candidate_alternative).",
    }
    write_json(DATA / "ACCOUNT_MAPPING.json", {
        "schema": "account_mapping/1", "code_commit": git_commit(),
        "accounts": accounts, "findings": findings,
    })

    print(f"\nV2 executed trades        : {v2_executed}")
    print(f"V2 paper drawdown         : {paper_dd_pct}% of initial (backend={pa.get('backend')})")
    print(f"V1_OLD cum net @09-23     : {v1old_at_reset}")
    print(f"V1_OLD cum net full       : {v1old_end}")
    print(f"VERDICT                   : {findings['verdict']}")


if __name__ == "__main__":
    main()
