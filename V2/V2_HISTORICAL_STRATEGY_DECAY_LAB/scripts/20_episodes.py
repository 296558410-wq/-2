"""
20_episodes.py — SYSTEM_EPISODES.jsonl

Derive every start / restart / switch / reset episode per system from raw evidence
(magic change, commit change, config_hash change, state-reset boundary, gaps,
backend/signal-source change). Conflicts are registered, not silently resolved.

READ-ONLY. Writes only to the lab dir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (REPO, LAB, DATA, SRC, banner, read_jsonl, read_json,
                        write_jsonl, write_json, git_commit, parse_ts, hours_between)

SOURCES = ["v1_upgrade_ledger", "v1_run_meta", "v1_run_statistics", "archive_manifest",
           "v1_trade_db", "v2_run_health", "v2_scheduler_state", "v1_broker_facts"]


def trade_gaps(rows, system, threshold_h=8):
    ts = sorted(r["entry_ts"] for r in rows
                if r.get("system") == system and r.get("entry_ts"))
    gaps = []
    for a, b in zip(ts, ts[1:]):
        h = hours_between(parse_ts(a), parse_ts(b))
        if h and h >= threshold_h:
            gaps.append({"from": a, "to": b, "gap_hours": round(h, 2)})
    return gaps


def main():
    banner("20_episodes.py", SOURCES)
    eps = []

    def add(**kw):
        kw.setdefault("conflict", None)
        kw.setdefault("confidence", "HIGH")
        eps.append(kw)

    # ---------------- V1_OLD (magic 90002) ----------------
    v1 = read_jsonl(SRC["v1_trade_db"])
    v1old = [r for r in v1 if r.get("system") == "V1_OLD"]
    v1new = [r for r in v1 if r.get("system") == "V1_NEW"]

    add(system="V1_OLD", magic=90002, episode_type="EPOCH_START",
        ts="2026-09-07T11:46:00Z", evidence="archive originals_moved first decisions file decisions__20260907T1146Z.json",
        detail="first recorded V1 decision (pre-first-trade)")
    add(system="V1_OLD", magic=90002, episode_type="TRADE_START",
        ts=v1old[0]["entry_ts"] if v1old else None,
        evidence="V1_HERMES_TRADE_DATABASE.jsonl first closed trade",
        detail="first executed roundtrip")
    add(system="V1_OLD", magic=90002, episode_type="RESTART",
        ts="2026-09-09T06:07:00+08:00", evidence="prior audit RESTART_FACTS.json (Windows update reboot ~06:07-06:12 local)",
        detail="machine reboot (Windows update)", confidence="MEDIUM",
        conflict="restart date precision: local-time window, no exact cycle boundary")
    add(system="V1_OLD", magic=90002, episode_type="RESTART",
        ts="2026-09-14T00:00:00+08:00", evidence="prior audit RESTART_FACTS.json",
        detail="documented restart 2026-09-14 (day precision)", confidence="LOW",
        conflict="no exact timestamp in evidence")
    add(system="V1_OLD", magic=90002, episode_type="STATE_RESET",
        ts="2026-09-23T23:37:41Z", evidence="archive/v1_pre_reset_20260923_233741/MANIFEST.json ts_utc",
        detail="V1 pre-reset archive boundary; history preserved")
    rm = read_json(SRC["v1_run_meta"])
    add(system="V1_OLD", magic=90002, episode_type="RUN_START",
        ts=rm.get("start_time_utc"), evidence="run_state/RUN_META.json start_time_utc",
        detail=f"new clean run {rm.get('run_id')} (state zeroed after reset)")
    add(system="V1_OLD", magic=90002, episode_type="EPOCH_END",
        ts=v1old[-1]["entry_ts"] if v1old else None,
        evidence="V1_HERMES_TRADE_DATABASE.jsonl last V1_OLD entry",
        detail="last V1_OLD roundtrip; superseded by V1_NEW control arm")
    for g in trade_gaps(v1, "V1_OLD", threshold_h=8):
        add(system="V1_OLD", magic=90002, episode_type="TRADE_GAP",
            ts=g["to"], evidence="trade DB inter-entry gap", detail=json.dumps(g),
            confidence="MEDIUM")

    # ---------------- V1_NEW (magic 90011) ----------------
    add(system="V1_NEW", magic=90011, episode_type="EPOCH_START",
        ts="2026-09-28T12:33:29Z", evidence="v1_upgrade_ledger seq1 ts_utc",
        detail="first DECISION of upgrade runtime")
    add(system="V1_NEW", magic=90011, episode_type="CONFIG_SWITCH",
        ts="2026-09-28T12:45:00Z", evidence="registry/runtime_config.json set_at_utc",
        detail="signal_source=BASELINE_TRANSITION (control arm armed)")
    add(system="V1_NEW", magic=90011, episode_type="BACKEND_ENABLE",
        ts="2026-09-28T15:35:00Z", evidence="runtime_config order_send_opened_at",
        detail="order_send_enabled=true (demo sending opened)")
    add(system="V1_NEW", magic=90011, episode_type="TRADE_START",
        ts="2026-09-28T15:35:14Z", evidence="ledger first FILL/POSITION",
        detail="first executed fill")
    add(system="V1_NEW", magic=90011, episode_type="FIRST_CLOSE",
        ts="2026-09-29T23:38:02Z", evidence="ledger first CLOSE/PNL (seq228/229)",
        detail="first closed roundtrip")
    add(system="V1_NEW", magic=90011, episode_type="RESTART",
        ts="2026-10-01T13:52:15Z", evidence="prior audit RESTART_FACTS.json + v1 timelines",
        detail="host restart (gap; back ~14:18Z)")
    add(system="V1_NEW", magic=90011, episode_type="CODE_SWITCH",
        ts="2026-10-02T03:51:44Z", evidence="git 63d5a22 v1-riskguard wiring fix",
        detail="risk-guard wiring fix (cycle.py,gates.py)")
    add(system="V1_NEW", magic=90011, episode_type="CODE_SWITCH",
        ts="2026-10-02T04:13:08Z", evidence="git eceeec2 v1-risk-hardening",
        detail="fail-closed inputs + kill switch")
    add(system="V1_NEW", magic=90011, episode_type="CODE_SWITCH",
        ts="2026-10-02T04:31:39Z", evidence="git ec0907e v1-truth-system",
        detail="black-box truth chain added")
    add(system="V1_NEW", magic=90011, episode_type="TRADE_END",
        ts=v1new[-1]["exit_ts"] if v1new else None,
        evidence="V1_HERMES_TRADE_DATABASE.jsonl last V1_NEW closed trade",
        detail="last executed roundtrip to date")
    for g in trade_gaps(v1, "V1_NEW", threshold_h=8):
        add(system="V1_NEW", magic=90011, episode_type="TRADE_GAP",
            ts=g["to"], evidence="trade DB inter-entry gap", detail=json.dumps(g),
            confidence="MEDIUM")

    # ---------------- V2_PAPER (shadow runs) ----------------
    lineage = [
        ("V2-SHADOW-20260911-*", "2026-09-11T13:33:00Z", "PAPER start (earliest decision ctx)",
         "V2_HERMES_TRADE_DATABASE.jsonl first ts"),
        ("V2-PAPER-20260913-224157-7a88", "2026-09-13T22:41:57Z", "PAPER run (MEMORY 09-14)",
         "MEMORY.md promoted entry"),
        ("V2-PAPER-20260914-231126-5fe2", "2026-09-14T23:11:26Z", "V2_REPAIRED run start",
         "MEMORY.md promoted entry"),
        ("V2-PAPER-20260916-110402-4644", "2026-09-16T11:04:02Z", "post broker-reconcile-fix run",
         "MEMORY.md promoted entry"),
        ("V2-SHADOW-20260917-021627-f80e", "2026-09-17T02:16:27Z", "SHADOW run", "V2_G3_RUN_LINEAGE.md"),
        ("V2-SHADOW-20260917-041800-3276", "2026-09-17T04:18:00Z", "SHADOW run (STOPPED)", "V2_G3_RUN_LINEAGE.md"),
        ("V2-SHADOW-20260917-042036-df35", "2026-09-17T04:20:36Z", "pre-source-switch transitional", "V2_G3_RUN_LINEAGE.md"),
        ("V2-SHADOW-20260917-104824-76af", "2026-09-17T10:48:24Z", "transitional 1-cycle", "V2_G3_RUN_LINEAGE.md"),
        ("V2-SHADOW-20260917-105319-b5e4", "2026-09-17T10:53:19Z", "final G3 48h shadow", "V2_G3_RUN_LINEAGE.md"),
        ("V2-PAPER-20260930-203702-484f", "2026-09-30T20:37:02Z", "blocked run (replay mismatch)", "v2_run_health last_failure"),
        ("V2-PAPER-20261001-205202-8b9e", "2026-10-01T20:52:02Z", "ACTIVE run", "state/runs/ACTIVE.json"),
    ]
    for rid, ts, detail, ev in lineage:
        add(system="V2_PAPER_SHADOW", magic=90003, episode_type="RUN_START",
            ts=ts, evidence=ev, detail=f"{rid}: {detail}", confidence="MEDIUM",
            conflict="V2 runs are shadow/paper restarts (no broker trades); not a trade episode")

    # ---------------- V3 ----------------
    add(system="V3_CALIBRATION", magic=None, episode_type="EPISODE",
        ts="2026-09-25T00:00:00Z", evidence="trader_v3/state/V3_CALIBRATION_PILOT.json",
        detail="calibration pilot; execution gated OFF (V3_EXECUTION_MODE)",
        confidence="MEDIUM")

    # conflict register
    conflicts = [e for e in eps if e.get("conflict")]
    write_jsonl(LAB / "SYSTEM_EPISODES.jsonl", eps)
    summary = {
        "schema": "system_episodes_summary/1",
        "code_commit": git_commit(),
        "n_episodes": len(eps),
        "by_system": {},
        "by_type": {},
        "conflicts": len(conflicts),
    }
    for e in eps:
        summary["by_system"][e["system"]] = summary["by_system"].get(e["system"], 0) + 1
        summary["by_type"][e["episode_type"]] = summary["by_type"].get(e["episode_type"], 0) + 1
    write_json(DATA / "SYSTEM_EPISODES_SUMMARY.json", summary)

    print(f"\nEpisodes registered : {len(eps)}")
    print(f"By system           : {summary['by_system']}")
    print(f"By type             : {summary['by_type']}")
    print(f"Conflicts registered: {len(conflicts)}")


if __name__ == "__main__":
    main()
