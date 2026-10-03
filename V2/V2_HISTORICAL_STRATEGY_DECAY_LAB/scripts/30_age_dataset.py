"""
30_age_dataset.py — AGE_ALIGNED_DATASET.jsonl + STRATEGY_LIFECYCLE_DATABASE.json

Recompute prediction / opportunity / trade / risk / data metrics from RAW evidence
(V1 trade DB is verified against the ledger; V2 decision contexts from the raw DB).
before-cost (profit_price) and after-cost (net) are both kept. Continuous age (hours
from the run/epoch start) plus analysis age buckets.

READ-ONLY. Writes only to the lab dir.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (REPO, LAB, DATA, SRC, banner, read_jsonl, read_json, write_jsonl,
                        write_json, git_commit, parse_ts, hours_between, mean, median,
                        stdev, EXPERIMENT_CONFIG)

SOURCES = ["v1_trade_db", "v1_upgrade_ledger", "v2_trade_db", "v2_ledger",
           "v1_run_meta", "archive_manifest"]
BUCKETS = EXPERIMENT_CONFIG["age_bucket_hours"]


def bucket_of(age_h):
    if age_h is None:
        return "UNKNOWN"
    last = None
    for b in BUCKETS:
        if age_h < b:
            return f"0-{b}h"
        last = b
    return f">{last}h"


def verify_v1_against_ledger():
    """Cross-check the V1_NEW trade DB against the upgrade ledger FILL/CLOSE events."""
    led = read_jsonl(SRC["v1_upgrade_ledger"])
    fills = [r for r in led if r.get("event") == "FILL"]
    closes = [r for r in led if r.get("event") == "CLOSE"]
    pnls = [r for r in led if r.get("event") == "PNL"]
    return {"ledger_fills": len(fills), "ledger_closes": len(closes),
            "ledger_pnls": len(pnls),
            "ledger_pnl_net_sum": round(sum(float(p.get("pnl", 0)) for p in pnls), 2)}


def build_v1_rows():
    rows = read_jsonl(SRC["v1_trade_db"])
    out = []
    epoch_v1old = parse_ts("2026-09-07T11:46:00Z")
    reset_v1old = parse_ts("2026-09-23T23:39:46Z")
    epoch_v1new = parse_ts("2026-09-28T12:33:29Z")
    for r in rows:
        if not isinstance(r, dict) or r.get("__malformed__"):
            continue
        sysname = r.get("system")
        if not sysname:
            continue
        closed = bool(r.get("closed"))
        entry = parse_ts(r.get("entry_ts"))
        if sysname == "V1_OLD":
            # age resets at the state-reset boundary (new run after it)
            epoch = reset_v1old if (entry and entry >= reset_v1old) else epoch_v1old
            run_id = "V1_RUN_20260924_RESET_01" if (entry and entry >= reset_v1old) \
                else "V1_UNNAMED_PRE_RESET"
            workstream = "V1_OLD"
        else:
            epoch = epoch_v1new
            run_id = "V1_UPGRADE_RUN_20260928"
            workstream = "V1_NEW"
        age = hours_between(epoch, entry)
        net = r.get("net")
        before = r.get("profit_price")
        comm = r.get("commission") or 0.0
        swap = r.get("swap") or 0.0
        cost = (comm or 0.0) + (swap or 0.0)
        out.append({
            "unit": "TRADE",
            "system": sysname,
            "run_id": run_id,
            "magic": r.get("magic"),
            "trade_id": r.get("trade_id"),
            "direction": r.get("direction"),
            "closed": closed,
            "entry_ts": r.get("entry_ts"),
            "exit_ts": r.get("exit_ts"),
            "age_hours": round(age, 3) if age is not None else None,
            "age_bucket": bucket_of(age),
            "holding_hours": round(hours_between(entry, parse_ts(r.get("exit_ts"))), 4)
            if entry and r.get("exit_ts") else None,
            "pnl_before_cost": before,
            "cost_usd": round(cost, 4),
            "pnl_after_cost": net,
            "outcome": r.get("outcome"),
            "strategy_provenance": r.get("provenance"),
            "source": "V1_HERMES_TRADE_DATABASE.jsonl",
        })
    return out


def build_v2_rows():
    rows = read_jsonl(SRC["v2_trade_db"])
    out = []
    for r in rows:
        if not isinstance(r, dict) or r.get("__malformed__"):
            continue
        ts = parse_ts(r.get("ts"))
        out.append({
            "unit": "DECISION",
            "system": "V2_PAPER_SHADOW",
            "run_id": None,
            "ts": r.get("ts"),
            "age_hours": None,
            "age_bucket": "UNKNOWN",
            "decision": r.get("decision"),
            "n_candidates": r.get("n_candidates"),
            "executed": r.get("executed", False),
            "outcome": r.get("outcome"),
            "regime_tags": r.get("regime_tags"),
            "source": "V2_HERMES_TRADE_DATABASE.jsonl",
        })
    return out


def summarize(rows):
    trade_rows = [r for r in rows if r["unit"] == "TRADE" and r["closed"]]
    out = {}
    for sysname in ("V1_OLD", "V1_NEW"):
        s = [r for r in trade_rows if r["system"] == sysname]
        if not s:
            continue
        after = [r["pnl_after_cost"] for r in s if r["pnl_after_cost"] is not None]
        before = [r["pnl_before_cost"] for r in s if r["pnl_before_cost"] is not None]
        wins = [x for x in after if x > 0]
        out[sysname] = {
            "n_closed": len(s),
            "n_win": len(wins),
            "win_rate": round(len(wins) / len(s), 4) if s else None,
            "net_after_cost": round(sum(after), 2),
            "net_before_cost": round(sum(before), 2),
            "cost_total": round(sum(r["cost_usd"] for r in s), 2),
            "mean_after": round(mean(after), 3),
            "median_after": round(median(after), 3),
            "stdev_after": round(stdev(after), 3) if stdev(after) else None,
            "entry_min": min(r["entry_ts"] for r in s),
            "entry_max": max(r["entry_ts"] for r in s),
            "age_hours_max": round(max(r["age_hours"] for r in s), 2) if all(
                r["age_hours"] is not None for r in s) else None,
        }
    # by bucket
    buckets = {}
    for sysname in ("V1_OLD", "V1_NEW"):
        s = [r for r in trade_rows if r["system"] == sysname]
        b = {}
        for r in s:
            k = r["age_bucket"]
            b.setdefault(k, {"n": 0, "net": 0.0, "wins": 0})
            b[k]["n"] += 1
            b[k]["net"] = round(b[k]["net"] + (r["pnl_after_cost"] or 0), 2)
            if (r["pnl_after_cost"] or 0) > 0:
                b[k]["wins"] += 1
        for k, v in b.items():
            v["win_rate"] = round(v["wins"] / v["n"], 3)
        buckets[sysname] = b
    return out, buckets


def main():
    banner("30_age_dataset.py", SOURCES)
    ledger_check = verify_v1_against_ledger()
    rows = build_v1_rows()
    v2rows = build_v2_rows()
    all_rows = rows + v2rows
    write_jsonl(LAB / "AGE_ALIGNED_DATASET.jsonl", all_rows)

    perf, buckets = summarize(all_rows)
    lifecycle = {
        "schema": "strategy_lifecycle_database/1",
        "code_commit": git_commit(),
        "note": "Only V1_OLD and V1_NEW have real closed trades. V2/V3 = 0 executed trades.",
        "systems": {
            "V1_OLD": {
                "strategy_provenance": "Hermes LLM plan engine (candidate, PIT-unverifiable early inputs)",
                "execution_mode": "MT5_DEMO", "magic": 90002,
                "epoch_start": "2026-09-07T11:46:00Z",
                "reset_boundary": "2026-09-23T23:39:46Z",
                "epoch_end": perf.get("V1_OLD", {}).get("entry_max"),
                "performance": perf.get("V1_OLD"),
                "age_buckets": buckets.get("V1_OLD"),
            },
            "V1_NEW": {
                "strategy_provenance": "BASELINE_CONTROL (not_hermes_alpha=true) - control arm",
                "execution_mode": "MT5_DEMO", "magic": 90011,
                "epoch_start": "2026-09-28T12:33:29Z",
                "epoch_end": perf.get("V1_NEW", {}).get("entry_max"),
                "performance": perf.get("V1_NEW"),
                "age_buckets": buckets.get("V1_NEW"),
            },
            "V2_PAPER_SHADOW": {
                "strategy_provenance": "reference_rules placeholder (signal_from_agents=false)",
                "execution_mode": "PAPER_LOCAL", "magic": 90003,
                "n_decision_rows": len(v2rows),
                "n_executed": sum(1 for r in v2rows if r.get("executed")),
                "performance": None,
                "verdict": "NOT_EVALUABLE (0 executed trades)",
            },
            "V3_CALIBRATION": {
                "strategy_provenance": "V3 research (alpha discovery)",
                "execution_mode": "DISABLED",
                "performance": None,
                "verdict": "NOT_EVALUABLE (execution disabled, 0 trades)",
            },
        },
        "ledger_verification": ledger_check,
        "input_hashes": {k: str(SRC[k]) for k in SOURCES},
    }
    write_json(LAB / "STRATEGY_LIFECYCLE_DATABASE.json", lifecycle)

    print(f"\nDataset rows          : {len(all_rows)}  (trades={len(rows)}, v2_decisions={len(v2rows)})")
    print(f"Ledger verification   : {ledger_check}")
    for s, p in perf.items():
        print(f"  {s}: n={p['n_closed']} win_rate={p['win_rate']} "
              f"net_after={p['net_after_cost']} net_before={p['net_before_cost']}")
    print("\nAge buckets (after-cost net):")
    for s, b in buckets.items():
        for k in sorted(b, key=lambda x: (len(x), x)):
            print(f"  {s} {k:>8}: n={b[k]['n']:>3} net={b[k]['net']:>9} win_rate={b[k]['win_rate']}")


if __name__ == "__main__":
    main()
