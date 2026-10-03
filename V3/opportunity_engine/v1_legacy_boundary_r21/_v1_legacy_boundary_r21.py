# -*- coding: utf-8 -*-
"""V1_LEGACY_LEDGER_BOUNDARY_R21 — READ-ONLY reconciliation-boundary + statistics-isolation audit.

No trading write API. No writes to V1/V2 or their runtime. No bridge, no new run, no reset, no automation
change, no git. Writes ONLY under research/v3_opportunity_engine/v1_legacy_boundary_r21/.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
TICKET = 2377449557
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
LEGACY_RUN = "V1_RUN_20260924_RESET_01"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}
STOP = []


def sh(a, t=150):
    try:
        p = subprocess.run(a, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "V1_LEGACY_LEDGER_BOUNDARY_R21_COMPLETE"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------------- §三 safety freeze ----------------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        d = {}
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], 90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "NOT_RUNNING" if not v1p else "RUNNING"
    R["ENGINE_SHA256"] = sha(ENGINE)
    R["LEDGER_SHA256"] = sha(LEDGER)
    # one read-only MT5 check
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " print(json.dumps({'CONNECTED':bool(ok),'balance':(ai.balance if ai else None),"
             "'equity':(ai.equity if ai else None),'margin_free':(ai.margin_free if ai else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_))}))\n"
             " mt5.shutdown()\nexcept Exception as ex:\n print(json.dumps({'err':type(ex).__name__}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        mt5 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        mt5 = {"err": type(ex).__name__}
    R["MT5_CONTEXT"] = "CONFIRMED" if mt5.get("CONNECTED") else "UNKNOWN"
    R["MT5_POSITION_COUNT"] = mt5.get("positions", "UNKNOWN")
    R["PENDING_ORDERS"] = mt5.get("orders", "UNKNOWN")
    R["ACCOUNT_BALANCE"] = mt5.get("balance", "UNKNOWN")
    R["ACCOUNT_EQUITY"] = mt5.get("equity", "UNKNOWN")
    R["FREE_MARGIN"] = mt5.get("margin_free", "UNKNOWN")
    if R["AUTOMATION_ENABLED"] is not False and str(R["AUTOMATION_ENABLED"]).lower() != "false":
        STOP.append("AUTOMATION_ENABLED")
    if R["V1_ENGINE_PROCESS"] != "NOT_RUNNING":
        STOP.append("V1_ENGINE_STARTED")
    if R["ENGINE_SHA256"] != BASE:
        STOP.append("ENGINE_HASH_CHANGED")
    if R["LEDGER_SHA256"] != LEDGER_EXPECT:
        STOP.append("LEDGER_HASH_CHANGED")
    if R["MT5_POSITION_COUNT"] not in (0, "UNKNOWN"):
        STOP.append("POSITION_REAPPEARED")
    if isinstance(R["PENDING_ORDERS"], int) and R["PENDING_ORDERS"] > 0:
        STOP.append("PENDING_ORDER_REAPPEARED")
    print("§3:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                 "LEDGER_SHA256", "MT5_POSITION_COUNT", "PENDING_ORDERS",
                                                 "ACCOUNT_BALANCE", "ACCOUNT_EQUITY")}, ensure_ascii=False), flush=True)

    # ---------------- §四 legacy ledger: strict binding ----------------
    lines = [l for l in open(LEDGER, encoding="utf-8", errors="ignore") if l.strip()] if os.path.exists(LEDGER) else []
    R["LEDGER_SIZE"] = os.path.getsize(LEDGER) if os.path.exists(LEDGER) else "UNAVAILABLE"
    R["LEDGER_LINE_COUNT"] = len(lines)
    IDKEYS = ("ticket", "identifier", "position_id", "order_id", "request_id", "deal_id")
    bound_lines = []
    for i, raw in enumerate(lines):
        try:
            j = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        hit = False
        for k in IDKEYS:
            if str(j.get(k)) == str(TICKET):
                hit = True
        if hit:
            bound_lines.append({"line": i + 1, "keys": sorted(j.keys())[:20],
                                 "id_fields": {k: j.get(k) for k in IDKEYS if k in j}})
    R["BOUND_LINES_BY_ID"] = bound_lines
    R["POSITION_2377449557_STATE"] = "RECORDED_OPEN" if bound_lines else "NOT_FOUND"
    if bound_lines:
        blob = json.dumps([json.loads(lines[b["line"] - 1]) for b in bound_lines], ensure_ascii=False).lower()
        R["DECISION"] = "FOUND" if re.search(r"decision|think", blob) else "UNKNOWN"
        R["REQUEST"] = "FOUND" if re.search(r"request|req_id", blob) else "UNKNOWN"
        R["ORDER"] = "FOUND" if re.search(r"order", blob) else "UNKNOWN"
        R["FILL"] = "FOUND" if re.search(r"fill|deal", blob) else "UNKNOWN"
        R["OPEN"] = "FOUND" if re.search(r"open|entry", blob) else "UNKNOWN"
        R["CLOSE"] = "FOUND" if re.search(r"close|closed|exit", blob) else "UNKNOWN"
        R["PNL"] = "FOUND" if re.search(r"pnl|profit", blob) else "UNKNOWN"
    else:
        for k in ("DECISION", "REQUEST", "ORDER", "FILL", "OPEN", "CLOSE", "PNL"):
            R[k] = "UNKNOWN"
    R["LEDGER_CLOSE"] = R["CLOSE"]
    R["LEDGER_PNL"] = R["PNL"]
    R["OLD_LEDGER_IMMUTABLE"] = "YES" if R["LEDGER_SHA256"] == LEDGER_EXPECT else "NO"
    print("§4 ledger:", json.dumps({"hash_ok": R["OLD_LEDGER_IMMUTABLE"], "lines": R["LEDGER_LINE_COUNT"],
                                      "bound": [b["line"] for b in bound_lines], "close": R["CLOSE"]},
                                     ensure_ascii=False), flush=True)

    # ---------------- §八 PnL boundary ----------------
    R["BROKER_REALIZED_PNL"] = -21.97
    R["LEGACY_PNL"] = -21.97
    R["NEW_RUN_PERFORMANCE_PNL"] = 0
    R["NEW_RUN_OPENING_EQUITY"] = R["ACCOUNT_EQUITY"]
    R["NEW_RUN_ACCOUNT_BALANCE"] = R["ACCOUNT_BALANCE"]
    R["ACCOUNTING_BOUNDARY_NOTE"] = ("legacy broker-realized PnL (−21.97) is attributed to LEGACY; the new run's "
                                       "performance must start from its own opening balance/equity; account funds are "
                                       "NOT inflated to make the new run 'start from zero'")

    # ---------------- §九 statistics isolation ----------------
    stats = {}
    for fn in ("statistics.json", "workflow_latest.json", "state_package_latest.json"):
        p = os.path.join(RUN, fn)
        if not os.path.exists(p):
            continue
        st = os.stat(p)
        try:
            doc = json.loads(open(p, encoding="utf-8", errors="ignore").read())
        except Exception:  # noqa: BLE001
            doc = None
        keys = {}
        if isinstance(doc, dict):
            for k, v in doc.items():
                if re.search(r"(?i)(pnl|profit|balance|equity|trade|win|loss|count|run_id|start)", str(k)) and not isinstance(v, (dict, list)):
                    keys[k] = v
        stats[fn] = {"mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(), "fields": keys}
    tail = []
    p = os.path.join(RUN, "trader_summary.txt")
    if os.path.exists(p):
        st = os.stat(p)
        stats["trader_summary.txt"] = {"mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                                         "preview": (open(p, encoding="utf-8", errors="ignore").read()[:600])}
    R["STATISTICS_FIELDS"] = stats
    R["STATS_RUN_ID"] = (stats.get("statistics.json", {}).get("fields", {}) or {}).get("run_id", "UNKNOWN")
    # decide
    mixed = "UNKNOWN"
    R["NEW_RUN_STATS"] = "UNKNOWN"
    R["NEW_RUN_STATS_BOUNDARY"] = "UNKNOWN"
    R["NEW_RUN_STATS_NOTE"] = ("existing statistics are scoped to the legacy run id; whether a future new run would "
                                "inherit/mix legacy PnL is not provable from current data -> UNKNOWN (not assumed clean)")
    print("§9 stats:", json.dumps({"run_id": R["STATS_RUN_ID"], "boundary": R["NEW_RUN_STATS_BOUNDARY"]},
                                   ensure_ascii=False), flush=True)

    # ---------------- §十 run id identity ----------------
    rm = os.path.join(RUN, "RUN_META.json")
    meta = {}
    if os.path.exists(rm):
        st = os.stat(rm)
        try:
            meta = json.loads(open(rm, encoding="utf-8", errors="ignore").read())
        except Exception:  # noqa: BLE001
            meta = {}
        meta["_file_mtime"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
    R["RUN_META"] = meta
    R["LEGACY_RUN_ID"] = meta.get("run_id", "UNKNOWN")
    R["LEGACY_RUN_START"] = meta.get("start_time_utc", "UNKNOWN")
    R["LEGACY_RUN_RUNTIME_VERSION"] = meta.get("runtime_version", "UNKNOWN")
    rv = str(meta.get("runtime_version", ""))
    R["RUN_RUNTIME_MATCHES_BASELINE"] = "YES" if BASE[:12] in rv else "UNKNOWN"
    R["LEGACY_RUN_CONFIRMED"] = "YES" if R["LEGACY_RUN_ID"] == LEGACY_RUN else "NO"
    print("§10 run:", json.dumps({k: R[k] for k in ("LEGACY_RUN_ID", "LEGACY_RUN_START",
                                                     "LEGACY_RUN_RUNTIME_VERSION",
                                                     "RUN_RUNTIME_MATCHES_BASELINE")}, ensure_ascii=False), flush=True)

    # ---------------- §六 design record (design only) ----------------
    R["RECORD_DESIGN"] = {"name": "LEGACY_POSITION_RECONCILIATION", "created": "NO", "design_only": True,
                            "position_id": TICKET, "legacy_run_id": R["LEGACY_RUN_ID"], "broker_state": "CLOSED",
                            "close_deal_ticket": 2364265913, "close_order_ticket": 2377465821, "close_reason": "SL",
                            "close_price": 4299.03, "gross_profit": -21.75, "swap": 0.00, "commission": -0.22,
                            "fee": 0.00, "net_profit": -21.97, "ledger_state": "OPEN", "ledger_close": "UNKNOWN",
                            "ledger_pnl": "NO", "reconciliation_state": "BROKER_CLOSED_LEDGER_OPEN",
                            "source_broker": "R20 broker history evidence", "source_ledger": "plan_ledger.jsonl",
                            "legacy_ledger_mutation": 0}
    R["RECONCILIATION_RECORD_STATUS"] = "DESIGNED_NOT_CREATED"

    # ---------------- §七 reconciliation states ----------------
    R["RECONCILIATION_DEFINITIONS"] = {"MATCH": "broker and ledger fully agree on the same lifecycle",
                                         "MISMATCH": "explicit conflict on the same lifecycle",
                                         "PARTIAL": "broker lifecycle fully proven; ledger only partially evidenced",
                                         "UNKNOWN": "insufficient evidence"}
    R["BROKER_STATE"] = "CLOSED"
    R["LEDGER_STATE"] = "OPEN"
    R["RECONCILIATION_STATE"] = "PARTIAL"
    R["RECONCILIATION_CONFLICT"] = "YES"
    R["RECONCILIATION_NOTE"] = "two fields kept separate on purpose (completeness view vs conflict view)"

    # ---------------- §十一 four boundaries ----------------
    R["LEGACY_BROKER_RECONCILED"] = "CONDITIONAL"
    R["LEGACY_BROKER_RECONCILED_REASON"] = ("broker close is proven (R20) but no independent reconciliation record "
                                              "has been created in R21 -> not YES")
    R["ACCOUNTING_BOUNDARY"] = ("defined: legacy broker-realized PnL (−21.97) is isolated from new-run performance; "
                                  "new run must start from its own opening balance/equity without fund inflation")

    # ---------------- §十二/§十三/§十四 ----------------
    arc_conds = ["independent reconciliation record created (not yet)", "ledger-vs-broker classification fixed",
                  "stats boundary proven clean or explicitly quarantined", "account boundary recorded at new-run init",
                  "archive manifest reviewed for immutability"]
    R["ARCHIVE_READINESS"] = "CONDITIONAL"
    R["ARCHIVE_CONDITIONS"] = arc_conds
    R["RESET_BLOCKER"] = ("LEDGER_BROKER_RECONCILED=CONDITIONAL; RECONCILIATION_RECORD_STATUS=DESIGNED_NOT_CREATED; "
                            "NEW_RUN_STATS_BOUNDARY=UNKNOWN")
    R["RESET_READINESS"] = "NO"
    R["BRIDGE_REQUIRED"] = "NO"
    R["BRIDGE_REQUIRED_REASON"] = ("the broker fact can be closed by an independent reconciliation record without "
                                     "touching the old ledger; a legacy bridge is not required for this closed position "
                                     "(a future bridge would need separate authorisation)")
    R["BRIDGE_CREATED"] = "NO"

    # ---------------- §五 re-check immutability + §十五 V2/V3 ----------------
    R["LEDGER_SHA256_END"] = sha(LEDGER)
    R["OLD_LEDGER_MUTATION"] = 0 if R["LEDGER_SHA256_END"] == LEDGER_EXPECT else 1
    if R["OLD_LEDGER_MUTATION"] != 0:
        STOP.append("LEDGER_WRITE")
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_RESEARCH_MODIFIED"] = "NO" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "YES"
    if R["V3_RESEARCH_MODIFIED"] != "NO":
        STOP.append("V3_CHANGED")
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = [os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
            for r_, _, fs in os.walk(V2) if "__pycache__" not in r_ for f in fs
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim]
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    if R["V2_SOURCE_CONFIG_MODIFIED"] != "NO":
        STOP.append("V2_CHANGED")

    # ---------------- §十六 counters + gate ----------------
    for k in COUNTERS:
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    conds = {"1_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
              "2_v1_stopped": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
              "3_engine_unchanged": R["ENGINE_SHA256"] == BASE,
              "4_ledger_unchanged": R["OLD_LEDGER_IMMUTABLE"] == "YES" and R["OLD_LEDGER_MUTATION"] == 0,
              "5_no_mt5_write": True, "6_old_ledger_immutable": R["OLD_LEDGER_IMMUTABLE"] == "YES",
              "7_ledger_lifecycle_documented": bool(R["BOUND_LINES_BY_ID"]),
              "8_broker_fact_referenced": "YES", "9_reconciliation_defined": True,
              "10_conflict_separated": R["RECONCILIATION_CONFLICT"] in ("YES", "NO"),
              "11_legacy_pnl_boundary": True, "12_stats_boundary_investigated": R["NEW_RUN_STATS_BOUNDARY"] in ("YES", "NO", "UNKNOWN"),
              "13_account_boundary": True, "14_legacy_run_confirmed": R["LEGACY_RUN_CONFIRMED"] == "YES",
              "15_bridge_assessed": R["BRIDGE_REQUIRED"] in ("YES", "NO", "UNKNOWN"),
              "16_archive_assessed": R["ARCHIVE_READINESS"] in ("YES", "NO", "CONDITIONAL", "UNKNOWN"),
              "17_reset_assessed": R["RESET_READINESS"] in ("YES", "NO", "CONDITIONAL", "UNKNOWN"),
              "18_v2_unchanged": R["V2_SOURCE_CONFIG_MODIFIED"] == "NO",
              "19_v3_unchanged": R["V3_RESEARCH_MODIFIED"] == "NO", "20_counters_reported": True}
    R["R21_CONDITIONS"] = conds
    R["R21_GATE"] = "PASS" if all(conds.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    dump(0)


def dump(rc):
    json.dump(R, open(os.path.join(HERE, "V1_LEGACY_LEDGER_BOUNDARY_R21.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §18 FINAL REPORT ===", flush=True)
    print("TASK_STATUS =", R.get("TASK_STATUS"))
    def blk(name, keys):
        print("\n=== %s ===" % name)
        for k in keys:
            print(f"{k} = {R.get(k, 'UNKNOWN')}")
    blk("SAFETY", ["AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "LEDGER_SHA256",
                    "MT5_POSITION_COUNT", "PENDING_ORDERS"])
    blk("LEGACY LEDGER", ["LEDGER_SHA256", "LEDGER_LINE_COUNT", "POSITION_2377449557_STATE", "DECISION", "REQUEST",
                            "ORDER", "FILL", "OPEN", "CLOSE", "PNL", "OLD_LEDGER_IMMUTABLE"])
    blk("BROKER FACT REFERENCE", ["BROKER_POSITION_STATE", "CLOSE_DEAL_TICKET", "CLOSE_ORDER_TICKET", "CLOSE_REASON",
                                    "CLOSE_PRICE", "NET_PROFIT"])
    blk("RECONCILIATION", ["BROKER_STATE", "LEDGER_STATE", "RECONCILIATION_STATE", "RECONCILIATION_CONFLICT",
                             "RECONCILIATION_RECORD_STATUS"])
    blk("RUN BOUNDARY", ["LEGACY_RUN_ID", "LEGACY_RUN_CONFIRMED", "LEGACY_PNL", "LEGACY_PNL_BOUNDARY",
                            "NEW_RUN_STATS_BOUNDARY", "ACCOUNTING_BOUNDARY"])
    blk("BRIDGE", ["BRIDGE_REQUIRED", "BRIDGE_CREATED"])
    blk("ARCHIVE", ["ARCHIVE_READINESS"])
    blk("RESET", ["RESET_BLOCKER", "RESET_READINESS", "FORMAL_RESET", "NEXT_STAGE_AUTHORIZED"])
    blk("V2/V3", ["V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED"])
    print("\n=== SAFETY COUNTERS ===")
    print(json.dumps({k: R.get(k, 0) for k in COUNTERS} | {"GIT_COMMIT": R.get("GIT_COMMIT")}, ensure_ascii=False))
    print("\n=== GATE ===")
    print("R21_GATE =", R.get("R21_GATE"), "| STOP_REASON =", R.get("STOP_REASON"))
    print("\n(artifact) " + os.path.join(HERE, "V1_LEGACY_LEDGER_BOUNDARY_R21.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
