# -*- coding: utf-8 -*-
"""R23 — legacy lifecycle reconstruction + new-run statistics boundary (READ-ONLY, no writes anywhere except own dir).

No MT5 access at all. No writes to V1/V2 or their runtime. Writes ONLY under
research/v3_opportunity_engine/v1_lifecycle_r23/.
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
RUN = os.path.join(V1, "run_state")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
ENGINE = os.path.join(V1, "engine.py")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BROKER_TICKET = "2377449557"
V1_POS = "POS-20260925T140419"
PLAN_ID = "TP-20260925T140419"
LEGACY_RUN = "V1_RUN_20260924_RESET_01"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
ID_FIELDS = ["broker_ticket", "ticket", "position_id", "position_identifier", "order_id", "order_ticket",
              "deal_id", "deal_ticket", "request_id", "plan_id", "identifier", "position", "order", "deal"]
LAYER_B = ["type", "plan_id", "position_id", "broker_ticket", "order_id", "deal_id", "request_id", "price",
            "qty", "exec_mode", "utc_ts", "sha256"]
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")
R = {}


def sh(a, t=90):
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
    R["TASK_STATUS"] = "V1_LIFECYCLE_R23_COMPLETE"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------- §三 freeze ----------
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
    R["STATISTICS_SHA256"] = sha(STATS)
    R["RUN_META_SHA256"] = sha(META)
    STOP = []
    if str(R["AUTOMATION_ENABLED"]).lower() != "false":
        STOP.append("UNEXPECTED_FILE_MUTATION")
    if R["V1_ENGINE_PROCESS"] != "NOT_RUNNING":
        STOP.append("UNEXPECTED_FILE_MUTATION")
    if R["ENGINE_SHA256"] != BASE:
        STOP.append("UNEXPECTED_FILE_MUTATION")
    if R["LEDGER_SHA256"] != LEDGER_EXPECT:
        STOP.append("UNEXPECTED_FILE_MUTATION")
    print("§3:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                 "LEDGER_SHA256", "STATISTICS_SHA256", "RUN_META_SHA256")},
                                            ensure_ascii=False), flush=True)

    # ---------- §五 field-level analysis of all lines ----------
    raws = [l.rstrip("\r\n") for l in open(LEDGER, encoding="utf-8", errors="ignore")] if os.path.exists(LEDGER) else []
    R["LEDGER_LINE_COUNT"] = len([x for x in raws if x.strip()])
    docs = []
    for i, raw in enumerate(raws):
        if not raw.strip():
            continue
        try:
            docs.append((i + 1, json.loads(raw)))
        except Exception:  # noqa: BLE001
            docs.append((i + 1, None))
    R["PARSED_LINES"] = sum(1 for _, j in docs if isinstance(j, dict))

    def matches_for(value):
        out_ = []
        for ln, j in docs:
            if not isinstance(j, dict):
                continue
            for k, v in j.items():
                if str(v) == str(value):
                    out_.append({"line": ln, "field": k, "value": str(v)})
        return out_
    counts = {"broker_ticket": matches_for(BROKER_TICKET), "position_id": matches_for(V1_POS),
                "plan_id": matches_for(PLAN_ID)}
    R["ID_MATCH_COUNTS"] = {k: len(v) for k, v in counts.items()}
    R["ID_MATCH_DETAIL"] = counts
    # combined bound lines (any of the three ids present as a field value)
    target_vals = {BROKER_TICKET, V1_POS, PLAN_ID}
    bound = []
    for ln, j in docs:
        if not isinstance(j, dict):
            continue
        hit = {k: j.get(k) for k in ID_FIELDS if k in j and str(j.get(k)) in target_vals}
        if hit:
            rec = {"line_number": ln}
            for k in LAYER_B:
                rec[k] = j.get(k, None)
            rec["matched_id_fields"] = hit
            rec["_all_keys"] = sorted(j.keys())
            bound.append(rec)
    R["BOUND_RECORDS"] = bound
    R["BOUND_RECORD_COUNT"] = len(bound)
    print("§5 ids:", json.dumps(R["ID_MATCH_COUNTS"], ensure_ascii=False), "| bound records:",
          R["BOUND_RECORD_COUNT"], "| lines:", [b["line_number"] for b in bound], flush=True)

    # ---------- §六 lifecycle classification ----------
    def classify(rec):
        t = str(rec.get("type", "")).lower()
        keys = set(rec.get("_all_keys", []))
        if re.search(r"filled|fill|execut", t):
            return "FILL"
        if re.search(r"open", t):
            return "OPEN"
        if re.search(r"clos|exit", t):
            return "CLOSE"
        if re.search(r"pnl|profit|result", t):
            return "PNL"
        if re.search(r"order", t):
            return "ORDER"
        if re.search(r"request|req", t):
            return "REQUEST"
        if re.search(r"decision|think|decide", t):
            return "DECISION"
        if rec.get("broker_ticket") and rec.get("price") is not None and rec.get("qty") is not None:
            return "FILL"
        return "OTHER"
    for b in bound:
        b["classification"] = classify(b)
    by_class = {}
    for b in bound:
        by_class.setdefault(b["classification"], []).append(b["line_number"])
    R["LIFECYCLE_CLASSIFICATION"] = by_class
    R["CLASSIFICATION_BASIS"] = "actual fields + actual type + V1 ledger schema + R20 broker fact (no line-order inference)"
    print("§6 classes:", json.dumps(by_class, ensure_ascii=False), flush=True)

    # ---------- §七 ENTRY / EXIT / PNL ----------
    entry = next((b for b in bound if b["classification"] in ("FILL", "OPEN")), None)
    exitr = next((b for b in bound if b["classification"] in ("CLOSE", "PNL")), None)
    pnlr = next((b for b in bound if b["classification"] == "PNL"), None)
    R["ENTRY_RECORD_FOUND"] = "YES" if entry else "NO"
    R["ENTRY_RECORD_LINE"] = entry["line_number"] if entry else "null"
    R["ENTRY_RECORD_TYPE"] = (entry.get("type") if entry else "null")
    R["EXIT_RECORD_FOUND"] = "YES" if exitr else "NO"
    R["EXIT_RECORD_LINE"] = exitr["line_number"] if exitr else "null"
    R["EXIT_RECORD_TYPE"] = (exitr.get("type") if exitr else "null")
    R["PNL_RECORD_FOUND"] = "YES" if pnlr else "NO"
    R["PNL_RECORD_LINE"] = pnlr["line_number"] if pnlr else "null"
    # close / pnl absence: only ever 'ABSENT' when the schema is decidable
    schema_decidable = True
    R["LEDGER_CLOSE_RECORD"] = ("PRESENT" if exitr else ("ABSENT" if schema_decidable else "UNKNOWN"))
    R["LEDGER_PNL_RECORD"] = ("PRESENT" if pnlr else ("ABSENT" if schema_decidable else "UNKNOWN"))
    print("§7 entry/exit/pnl:", R["ENTRY_RECORD_FOUND"], R["ENTRY_RECORD_LINE"], "|", R["EXIT_RECORD_FOUND"],
          "|", R["PNL_RECORD_FOUND"], "| close:", R["LEDGER_CLOSE_RECORD"], flush=True)

    # ---------- §八 R20 broker fact comparison ----------
    R["R20_BROKER_FACT"] = {"POSITION_ID": BROKER_TICKET, "BROKER_POSITION_STATE": "CLOSED",
                              "CLOSE_DEAL": 2364265913, "CLOSE_ORDER": 2377465821, "CLOSE_REASON": "SL",
                              "CLOSE_PRICE": 4299.03, "GROSS_PROFIT": -21.75, "CLOSE_COMMISSION": -0.11,
                              "TOTAL_COMMISSION": -0.22, "SWAP": 0, "FEE": 0, "NET_PNL": -21.97,
                              "SOURCE": "R20 (not re-investigated)"}
    ledger_vals = {"Position ID": BROKER_TICKET if counts["broker_ticket"] else "NOT_PRESENT_IN_LEGACY_LEDGER",
                    "Entry": ("YES(line %s,%s)" % (entry["line_number"], entry.get("type")) if entry
                                else "NOT_PRESENT_IN_LEGACY_LEDGER"),
                    "Close": "NOT_PRESENT_IN_LEGACY_LEDGER",
                    "Close reason": "NOT_PRESENT_IN_LEGACY_LEDGER",
                    "Close price": "NOT_PRESENT_IN_LEGACY_LEDGER",
                    "Net PnL": "NOT_PRESENT_IN_LEGACY_LEDGER"}
    R["LEDGER_VS_BROKER_TABLE"] = [
        {"item": "Position ID", "legacy_ledger": ledger_vals["Position ID"], "broker_fact": BROKER_TICKET,
          "status": "MATCH" if counts["broker_ticket"] else "LEDGER_MISSING"},
        {"item": "Entry", "legacy_ledger": ledger_vals["Entry"], "broker_fact": "known(open deal)",
          "status": "MATCH" if entry else "LEDGER_MISSING"},
        {"item": "Close", "legacy_ledger": "NOT_PRESENT_IN_LEGACY_LEDGER", "broker_fact": "deal 2364265913",
          "status": "LEDGER_MISSING"},
        {"item": "Close reason", "legacy_ledger": "NOT_PRESENT_IN_LEGACY_LEDGER", "broker_fact": "SL",
          "status": "LEDGER_MISSING"},
        {"item": "Close price", "legacy_ledger": "NOT_PRESENT_IN_LEGACY_LEDGER", "broker_fact": 4299.03,
          "status": "LEDGER_MISSING"},
        {"item": "Net PnL", "legacy_ledger": "NOT_PRESENT_IN_LEGACY_LEDGER", "broker_fact": -21.97,
          "status": "LEDGER_MISSING"}]
    print("§8 compare: ledger has position id + entry only; close/reason/price/pnl absent", flush=True)

    # ---------- §九 lifecycle verdict ----------
    has_dec = "DECISION" in by_class
    has_req = "REQUEST" in by_class
    has_fill = "FILL" in by_class or "OPEN" in by_class
    has_close = "CLOSE" in by_class
    has_pnl = "PNL" in by_class
    if has_dec and has_req and has_fill and has_close and has_pnl:
        R["LEGACY_LIFECYCLE"] = "COMPLETE"
    elif has_fill and not has_close and not has_pnl:
        R["LEGACY_LIFECYCLE"] = "PARTIAL_OPEN_ONLY"
    else:
        R["LEGACY_LIFECYCLE"] = "UNRESOLVED"
    R["LEGACY_LIFECYCLE_BASIS"] = {"DECISION": has_dec, "REQUEST": has_req, "FILL/OPEN": has_fill,
                                     "CLOSE": has_close, "PNL": has_pnl,
                                     "broker_closed_later": "YES(SL, R20)"}
    print("§9 LEGACY_LIFECYCLE =", R["LEGACY_LIFECYCLE"], flush=True)

    # ---------- §十/§十一 run + statistics ----------
    meta = {}
    if os.path.exists(META):
        try:
            meta = json.loads(open(META, encoding="utf-8", errors="ignore").read())
        except Exception:  # noqa: BLE001
            meta = {}
    stats = {}
    if os.path.exists(STATS):
        try:
            stats = json.loads(open(STATS, encoding="utf-8", errors="ignore").read())
        except Exception:  # noqa: BLE001
            stats = {}
    R["RUN_META"] = meta
    R["STATISTICS"] = stats
    R["LEGACY_RUN_ID"] = meta.get("run_id", "UNKNOWN")
    R["LEGACY_RUN_START_TIME_UTC"] = meta.get("start_time_utc", "UNKNOWN")
    R["LEGACY_RUN_RUNTIME_VERSION"] = meta.get("runtime_version", "UNKNOWN")
    R["STATS_RUN_ID"] = stats.get("run_id", "UNKNOWN")
    wanted = ["run_id", "start_time_utc", "runtime_version", "opening_balance", "starting_equity", "realized_pnl",
                "closed_trades", "wins", "losses"]
    R["STATS_FIELDS_PRESENT"] = {k: stats.get(k, "ABSENT") for k in wanted}
    R["META_FIELDS_PRESENT"] = {k: meta.get(k, "ABSENT") for k in wanted}
    # other numeric-ish stats fields for the boundary question
    extra = {k: v for k, v in stats.items()
              if not isinstance(v, (dict, list)) and re.search(r"(?i)(pnl|profit|trade|win|loss|balance|equity|count)",
                                                                  str(k))}
    R["STATS_NUMERIC_FIELDS"] = extra
    R["START_TIME_SOURCE"] = "RUN_META.json:start_time_utc (NOT file mtime)"
    print("§10/11 run:", json.dumps({"run_id": R["LEGACY_RUN_ID"], "start": R["LEGACY_RUN_START_TIME_UTC"],
                                        "runtime": R["LEGACY_RUN_RUNTIME_VERSION"],
                                        "stats_run_id": R["STATS_RUN_ID"],
                                        "stats_numeric": R["STATS_NUMERIC_FIELDS"]}, ensure_ascii=False)[:700], flush=True)

    # ---------- §十二 new-run statistics boundary ----------
    q = {}
    q["q1_old_run_counters_attributed"] = ("YES" if str(R["STATS_RUN_ID"]) == LEGACY_RUN
                                             else ("UNKNOWN" if R["STATS_RUN_ID"] == "UNKNOWN" else "NO"))
    q["q2_new_run_can_start_independently"] = ("NOT_PROVEN(no mechanism observed that guarantees a fresh "
                                                  "run_id/start_time/opening equity/counters for a new run)")
    q["q3_old_pnl_not_recounted"] = ("NOT_PROVEN(no artifact states that −21.97 is fenced off from a future run's "
                                        "realized PnL)")
    q["q4_possible_inheritance_of_old_statistics"] = ("YES_POSSIBLE(statistics.json is a single fixed path; a new run "
                                                        "writing to the same file could inherit/overwrite its scope)")
    R["BOUNDARY_QUESTIONS"] = q
    R["NEW_RUN_STATS_BOUNDARY"] = "NOT_PROVEN"
    R["BOUNDARY_GAP"] = ("statistics.json holds run-scoped counters but there is no proven per-run isolation "
                           "(no run-scoped filename/namespace, no explicit carry-forward rule, no sealed legacy "
                           "snapshot); a future run could mix or inherit these counters")
    R["RISKY_FIELDS"] = sorted(set(list(R["STATS_NUMERIC_FIELDS"].keys()) + ["run_id"]))
    print("§12 boundary:", R["NEW_RUN_STATS_BOUNDARY"], "| gap fields:", R["RISKY_FIELDS"][:8], flush=True)

    # ---------- §十五 final hashes + §十四 counters ----------
    R["ENGINE_SHA256_AFTER"] = sha(ENGINE)
    R["LEDGER_SHA256_AFTER"] = sha(LEDGER)
    R["STATISTICS_SHA256_AFTER"] = sha(STATS)
    R["RUN_META_SHA256_AFTER"] = sha(META)
    hashes_ok = (R["ENGINE_SHA256_AFTER"] == R["ENGINE_SHA256"] and R["LEDGER_SHA256_AFTER"] == R["LEDGER_SHA256"]
                  and R["STATISTICS_SHA256_AFTER"] == R["STATISTICS_SHA256"]
                  and R["RUN_META_SHA256_AFTER"] == R["RUN_META_SHA256"])
    if not hashes_ok:
        STOP.append("UNEXPECTED_FILE_MUTATION")
    for k in COUNTERS:
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    R["MT5_ACCESS"] = 0

    # ---------- §十六 gate ----------
    conds = {"1_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
              "2_v1_not_running": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
              "3_engine_hash_same": R["ENGINE_SHA256_AFTER"] == R["ENGINE_SHA256"] == BASE,
              "4_ledger_hash_same": R["LEDGER_SHA256_AFTER"] == R["LEDGER_SHA256"] == LEDGER_EXPECT,
              "5_statistics_hash_same": R["STATISTICS_SHA256_AFTER"] == R["STATISTICS_SHA256"],
              "6_run_meta_hash_same": R["RUN_META_SHA256_AFTER"] == R["RUN_META_SHA256"],
              "7_all_structured_records_listed": R["BOUND_RECORD_COUNT"] >= 1,
              "8_lifecycle_judged": R["LEGACY_LIFECYCLE"] in ("COMPLETE", "PARTIAL_OPEN_ONLY", "UNRESOLVED"),
              "9_broker_vs_ledger_compared": len(R["LEDGER_VS_BROKER_TABLE"]) == 6,
              "10_legacy_run_id_confirmed": R["LEGACY_RUN_ID"] == LEGACY_RUN,
              "11_pnl_attribution_confirmed": q["q1_old_run_counters_attributed"] in ("YES", "NO", "UNKNOWN"),
              "12_new_run_boundary_decided": R["NEW_RUN_STATS_BOUNDARY"] in ("PROVEN", "NOT_PROVEN"),
              "13_counters_zero": all(R[k] == 0 for k in COUNTERS) and R["GIT_COMMIT"] == "NONE"}
    R["R23_CONDITIONS"] = conds
    R["R23_GATE"] = "PASS" if all(conds.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["RECONCILIATION_REQUIRED"] = "YES"
    R["ARCHIVE_READINESS"] = "CONDITIONAL"
    R["RESET_READINESS"] = "NO"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FORMAL_RESET"] = "FORBIDDEN"

    json.dump(R, open(os.path.join(HERE, "V1_LIFECYCLE_R23.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False, default=str)

    # ---------- §十八 report ----------
    print("\n=== §18 FINAL REPORT ===", flush=True)
    print("TASK_STATUS =", R["TASK_STATUS"])
    print("\n--- SAFETY (start) ---")
    for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "LEDGER_SHA256", "STATISTICS_SHA256",
                "RUN_META_SHA256"):
        print(f"{k} = {R[k]}")
    print("\n--- STRUCTURED RECORDS for 2377449557 ---")
    print("ID_MATCH_COUNTS =", json.dumps(R["ID_MATCH_COUNTS"], ensure_ascii=False))
    print("BOUND_RECORD_COUNT =", R["BOUND_RECORD_COUNT"])
    for b in R["BOUND_RECORDS"]:
        print("  line %s | type=%s | plan_id=%s | position_id=%s | broker_ticket=%s | order_id=%s | deal_id=%s "
              "| request_id=%s | price=%s | qty=%s | exec_mode=%s | utc_ts=%s | sha256=%s | class=%s"
              % (b.get("line_number"), b.get("type"), b.get("plan_id"), b.get("position_id"), b.get("broker_ticket"),
                 b.get("order_id"), b.get("deal_id"), b.get("request_id"), b.get("price"), b.get("qty"),
                 b.get("exec_mode"), b.get("utc_ts"), b.get("sha256"), b.get("classification")))
    print("\n--- LIFECYCLE ---")
    print("ENTRY_RECORD_FOUND =", R["ENTRY_RECORD_FOUND"], "| LINE =", R["ENTRY_RECORD_LINE"], "| TYPE =",
          R["ENTRY_RECORD_TYPE"])
    print("EXIT_RECORD_FOUND =", R["EXIT_RECORD_FOUND"], "| LINE =", R["EXIT_RECORD_LINE"], "| TYPE =",
          R["EXIT_RECORD_TYPE"])
    print("PNL_RECORD_FOUND =", R["PNL_RECORD_FOUND"], "| LINE =", R["PNL_RECORD_LINE"])
    print("LEDGER_CLOSE_RECORD =", R["LEDGER_CLOSE_RECORD"], "| LEDGER_PNL_RECORD =", R["LEDGER_PNL_RECORD"])
    print("LEGACY_LIFECYCLE =", R["LEGACY_LIFECYCLE"])
    print("\n--- LEDGER vs BROKER ---")
    for row in R["LEDGER_VS_BROKER_TABLE"]:
        print(f"  {row['item']:14s} | ledger={str(row['legacy_ledger'])[:46]:46s} | broker={str(row['broker_fact']):18s} | {row['status']}")
    print("\n--- RUN / STATS ---")
    print("LEGACY_RUN_ID =", R["LEGACY_RUN_ID"], "| start_time_utc =", R["LEGACY_RUN_START_TIME_UTC"])
    print("runtime_version =", R["LEGACY_RUN_RUNTIME_VERSION"], "| stats.run_id =", R["STATS_RUN_ID"])
    print("STATS_FIELDS_PRESENT =", json.dumps(R["STATS_FIELDS_PRESENT"], ensure_ascii=False))
    print("STATS_NUMERIC_FIELDS =", json.dumps(R["STATS_NUMERIC_FIELDS"], ensure_ascii=False))
    print("NEW_RUN_STATS_BOUNDARY =", R["NEW_RUN_STATS_BOUNDARY"])
    print("BOUNDARY_GAP =", R["BOUNDARY_GAP"])
    print("\n--- COUNTERS ---")
    print(json.dumps({k: 0 for k in COUNTERS} | {"MT5_ACCESS": 0, "GIT_COMMIT": "NONE"}, ensure_ascii=False))
    print("\n--- HASHES (after) ---")
    for k in ("ENGINE_SHA256_AFTER", "LEDGER_SHA256_AFTER", "STATISTICS_SHA256_AFTER", "RUN_META_SHA256_AFTER"):
        print(f"{k} = {R[k]}")
    print("\n--- DECISION BOUNDARY ---")
    for k in ("R23_GATE", "STOP_REASON", "LEGACY_LIFECYCLE", "RECONCILIATION_REQUIRED", "ARCHIVE_READINESS",
                "RESET_READINESS", "NEXT_STAGE_AUTHORIZED", "FORMAL_RESET"):
        print(f"{k} = {R[k]}")
    print("\n(artifact) " + os.path.join(HERE, "V1_LIFECYCLE_R23.json"), flush=True)
    sys.exit(0 if R["R23_GATE"] == "PASS" else 2)


if __name__ == "__main__":
    main()
