# -*- coding: utf-8 -*-
"""Generate the Truth System registry/report artifacts. Reads only; writes under audit/v1_truth_system/."""
from __future__ import annotations
import datetime as dt, json, os, sys

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_truth_system")
sys.path.insert(0, os.path.join(ROOT, "truth"))
sys.path.insert(0, ROOT)
import truth_lib as TR  # noqa: E402

os.makedirs(OUT, exist_ok=True)
now = dt.datetime.now(dt.timezone.utc).isoformat()
rows = TR.load_ledger()
facts = TR.load_broker_facts()

# ---------------- V1_TRUTH_SCHEMA.json
schema = {
    "schema": "V1_TRUTH_SCHEMA", "protocol_version": TR.TRUTH_VERSION, "schema_version": TR.SCHEMA_VERSION,
    "generated_utc": now,
    "layers": {"Raw Facts": "MT5 broker responses / market data / ledger events (as recorded)",
               "Derived Facts": "ids / cases / incidents / consistency checks / daily aggregates (recomputable)",
               "Interpretation": "human/AI reports only; never stored as fact"},
    "priority": ["Raw Facts", "Derived Facts", "Interpretation"],
    "ids": {
        "event_id": "V1E-<sha12(seq,current_hash,event)> (deterministic, derived)",
        "cycle_id": "V1C-<YYYYMMDDTHHMMSSZ> (stamped on new events; derived from ts for legacy)",
        "decision_id": "V1D-<sha10(cycle_id|action)> (stamped on new events)",
        "order_id": "broker order ticket (string)",
        "trade_id": "V1T-<broker position_id>",
        "incident_id": "V1I-<TYPE>-<sha8(key)> (deterministic per fact)",
        "dedup_key": "MAGIC:SYMBOL:M15_bucket (server frame)"
    },
    "decision_snapshot": {
        "store": "truth/evidence/decision_snapshots.jsonl (append-only, per-line sha256 + prev chain)",
        "required_fields": ["protocol_version", "schema_version", "cycle_id", "decision_id", "code_version",
                            "config_hash", "timestamp_utc", "server_time", "symbol", "market_snapshot", "data_source",
                            "data_timestamp", "data_age", "PIT_status", "hermes_input_hash", "hermes_output",
                            "signal", "risk_state", "risk_reasons", "daily_loss", "consecutive_loss",
                            "position_state", "slippage_state", "dedup_state", "kill_switch_state", "decision",
                            "risk_inputs_ok"],
        "written": "BEFORE any execution path; write failure => no new entry (WAIT_TRUTH)"},
    "incident": {"fields": ["incident_id", "type", "severity", "first_seen", "last_seen", "root_cause",
                             "affected_ids", "status", "resolution", "validation", "evidence", "cycle_id"],
                  "root_cause": "UNKNOWN allowed; must never be fabricated",
                  "store": "truth/evidence/incidents.jsonl (append-only; updates appended; latest state wins)"},
    "case": {"id": "CASE-V1T-<position_id>", "stages": ["signal_and_context", "risk_evaluation", "decision",
                                                         "order_check", "order_request", "order_send", "fill", "position",
                                                         "close", "pnl"],
              "link_method": "cycle_id (new) / time_adjacency(legacy, marked)"},
}
json.dump(schema, open(os.path.join(OUT, "V1_TRUTH_SCHEMA.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------- V1_EVENT_REGISTRY.json
EV = {
    "DECISION": {"producer": "cycle.py", "fields_key": ["action", "signal", "risk_allow", "risk_reasons", "snapshot",
                                                          "cycle_id", "decision_id", "truth_record_ok"],
                  "links": ["cycle_id", "decision_id"], "downstream": ["ORDER_CHECK", "ORDER_REQUEST"]},
    "ORDER_CHECK": {"producer": "cycle.py", "fields_key": ["side", "lots", "price", "filling_name", "retcode", "ok"],
                     "links": ["cycle_id"], "downstream": ["ORDER_REQUEST", "DECISION(BLOCKED)"]},
    "ORDER_REQUEST": {"producer": "cycle.py", "fields_key": ["side", "lots", "price", "sl", "tp", "dedup_key"],
                       "links": ["dedup_key"], "downstream": ["ORDER_SEND"]},
    "ORDER_SEND": {"producer": "cycle.py", "fields_key": ["order_id", "retcode", "ok", "slippage_bps", "latency_ms",
                                                            "dedup_key", "broker_comment"],
                    "links": ["order_id", "dedup_key"], "downstream": ["FILL", "POSITION"]},
    "FILL": {"producer": "cycle.py", "fields_key": ["order_id", "price", "qty"], "links": ["order_id"], "downstream": ["POSITION"]},
    "POSITION": {"producer": "cycle.py", "fields_key": ["order_id", "ticket", "sl", "tp"], "links": ["order_id"], "downstream": ["CLOSE"]},
    "CLOSE": {"producer": "cycle.py (reconcile from broker deals)", "fields_key": ["position_id", "side", "qty", "price",
                                                                                      "reason", "broker_time_utc"],
               "links": ["position_id"], "downstream": ["PNL"]},
    "PNL": {"producer": "cycle.py (reconcile)", "fields_key": ["pnl", "commission", "swap", "realized_R", "broker_time_utc"],
             "links": ["position_id"], "downstream": ["risk state rebuild"]},
}
json.dump({"registry": "V1_EVENT_REGISTRY", "protocol_version": TR.TRUTH_VERSION, "generated_utc": now,
           "note": "schema of the append-only ledger; new events additionally carry cycle_id/decision_id/dedup_key",
           "events": EV},
          open(os.path.join(OUT, "V1_EVENT_REGISTRY.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------- V1_EVIDENCE_REGISTRY.json
inv = TR.evidence_inventory()
inc_ok, inc_n = TR.verify_evidence(TR.INCIDENTS)
snap_ok, snap_n = TR.verify_evidence(TR.SNAP)
lg_ok, lg_n, lg_bad = TR._ledger_verify(rows)
evreg = {"registry": "V1_EVIDENCE_REGISTRY", "generated_utc": now, "protocol_version": TR.TRUTH_VERSION,
         "stores": [{"name": "trading_ledger", "path": "v1_upgrade/ledger/v1_upgrade_ledger.jsonl",
                      "kind": "raw+derived", "append_only": True, "integrity": {"ok": lg_ok, "entries": lg_n, "bad": lg_bad}},
                     {"name": "decision_snapshots", "path": "v1_upgrade/truth/evidence/decision_snapshots.jsonl",
                      "kind": "raw(evidence)", "append_only": True, "integrity": {"ok": snap_ok, "entries": snap_n}},
                     {"name": "incidents", "path": "v1_upgrade/truth/evidence/incidents.jsonl",
                      "kind": "derived", "append_only": True, "integrity": {"ok": inc_ok, "entries": inc_n}},
                     {"name": "broker_facts_cache", "path": "v1_upgrade/truth/evidence/broker_facts.json",
                      "kind": "raw(snapshot)", "append_only": False, "note": "refreshed per cycle; latest state only"},
                     {"name": "cases", "path": "v1_upgrade/truth/evidence/cases/", "kind": "derived", "append_only": False}],
         "inventory": inv}
json.dump(evreg, open(os.path.join(OUT, "V1_EVIDENCE_REGISTRY.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------- V1_DAILY_TRUTH_REPORT.md (today)
today = dt.datetime.now(dt.timezone.utc).date().isoformat()
rep = TR.daily_truth(today, rows, facts)
lines = [f"# V1 Daily Truth Report — {today} (UTC)", "",
         "> **FACTS_ONLY** — numbers below are computed from raw evidence (ledger + broker facts). No interpretation.",
         "", f"- generated: {now} · protocol {TR.TRUTH_VERSION}", "",
         "| metric | value |", "|---|---|"]
for k in ("cycles", "signals", "wait", "risk_block", "orders", "mt5_rejects", "fills", "closes", "open_positions"):
    lines.append(f"| {k} | {rep.get(k)} |")
for k in ("pnl_price_component", "commission", "swap", "net"):
    lines.append(f"| {k} | {rep.get(k)} |")
lines += ["", "## risk blocks by reason", "```json",
          json.dumps(rep.get("risk_blocks_by_reason"), ensure_ascii=False, indent=1), "```",
          "## spread / slippage", "```json",
          json.dumps({"spread_bps": rep.get("spread_bps"), "slippage_bps": rep.get("slippage_bps")}, ensure_ascii=False, indent=1), "```",
          "## integrity", "```json",
          json.dumps({"ledger": rep.get("ledger_integrity"), "snapshots": rep.get("evidence_snapshot_integrity"),
                      "incidents_file": rep.get("incidents_file_integrity")}, ensure_ascii=False, indent=1), "```",
          "## incidents today (index)", "```json",
          json.dumps(rep.get("incidents"), ensure_ascii=False, indent=1), "```", "",
          "## UNKNOWNs", "- legacy events (before the Truth System) carry **no** cycle_id/decision_id; links use "
          "time_adjacency and are marked as such.", "- broker_facts is a latest-state cache, not an append-only log.",
          "- decision snapshots start with the first live cycle after enablement."]
open(os.path.join(OUT, "V1_DAILY_TRUTH_REPORT.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("schema/event/evidence/daily written; daily net =", rep.get("net"), "cycles =", rep.get("cycles"))
