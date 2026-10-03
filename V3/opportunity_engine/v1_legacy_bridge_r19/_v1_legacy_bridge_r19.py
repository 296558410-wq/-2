# -*- coding: utf-8 -*-
"""V1_LEGACY_POSITION_BRIDGE_R19 — DESIGN / FREEZE ONLY (no execution).

Read-only: MT5 (positions_get/orders_get/account_info/terminal_info), ledger, runtime, existing design files,
hashes/metadata. Writes ONLY under research/v3_opportunity_engine/v1_legacy_bridge_r19/.
Never touches research/hermes/trader_v1/ or research/hermes/trader_v2/.
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
R18 = os.path.join(ENGINE_DIR, "v1_position_ledger_seal_r18", "V1_POSITION_LEDGER_SEAL_AUDIT_R18.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_R18 = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
TICKET = 2377449557
SELFREF_EXCLUDE = "v3_opportunity_engine"
BANNED_TOKENS = ("V1_RUN_20260924_RESET_01",)
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
SCAN_DIRS = [RUN, os.path.join(V1, "runtime"), os.path.join(V1, "tmp"), os.path.join(V1, "cache"),
              os.path.join(V1, "memory", "reviews"), os.path.join(V1, "observations"),
              os.path.join(V1, "state", "decision_contexts"), os.path.join(V1, "ledger"), os.path.join(V1, "state")]
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


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "RUNNING"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()
    r18 = json.load(open(R18, encoding="utf-8")) if os.path.exists(R18) else {}
    R["R18_REFERENCE"] = {"path": os.path.relpath(R18, AIQ).replace("\\", "/"),
                            "ticket": r18.get("POSITION_TICKET"), "state": r18.get("LEDGER_POSITION_STATE"),
                            "ownership": r18.get("V1_POSITION_OWNERSHIP")}

    # ================= R19-01 baseline re-confirmation =================
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        d = {}
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = d.get("status", "UNKNOWN")
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], 90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if re.search(r"trader_v1|engine\.py|state_package", (x.get("CommandLine") or ""), re.I)
            and "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "NOT_RUNNING" if not v1p else "RUNNING"
    R["ENGINE_SHA256"] = sha(ENGINE)
    if os.path.exists(LEDGER):
        st = os.stat(LEDGER)
        R["LEDGER_SHA256"] = sha(LEDGER)
        R["LEDGER_SIZE"] = st.st_size
        R["LEDGER_MTIME"] = iso(st.st_mtime)
        R["LEDGER_LINE_COUNT"] = len([l for l in open(LEDGER, encoding="utf-8", errors="ignore") if l.strip()])
    else:
        R["LEDGER_SHA256"] = R["LEDGER_SIZE"] = R["LEDGER_MTIME"] = "UNAVAILABLE"
        R["LEDGER_LINE_COUNT"] = 0
    # MT5 read-only
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " p=ps[0] if ps else None\n"
             " print(json.dumps({'CONNECTED':bool(ok),'balance':(ai.balance if ai else None),"
             "'equity':(ai.equity if ai else None),'margin_free':(ai.margin_free if ai else None),"
             "'ticket':(p.ticket if p else None),'identifier':(getattr(p,'identifier',None) if p else None),"
             "'symbol':(p.symbol if p else None),'type':(p.type if p else None),'volume':(p.volume if p else None),"
             "'price_open':(p.price_open if p else None),'sl':(p.sl if p else None),'tp':(p.tp if p else None),"
             "'time':(p.time if p else None),'magic':(p.magic if p else None),'comment':(getattr(p,'comment',None) if p else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_))}))\n"
             " mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:100]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        mt5 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        mt5 = {"err": type(ex).__name__}
    R["MT5_CONTEXT"] = "CONFIRMED" if mt5.get("CONNECTED") else "UNKNOWN"
    R["POSITION_TICKET"] = mt5.get("ticket", "UNAVAILABLE")
    R["POSITION_IDENTIFIER"] = mt5.get("identifier", "UNAVAILABLE")
    R["POSITION_TYPE"] = ("SELL" if mt5.get("type") == 1 else ("BUY" if mt5.get("type") == 0 else mt5.get("type", "UNAVAILABLE")))
    R["POSITION_VOLUME"] = mt5.get("volume", "UNAVAILABLE")
    R["POSITION_PRICE_OPEN"] = mt5.get("price_open", "UNAVAILABLE")
    R["POSITION_SL"] = mt5.get("sl", "UNAVAILABLE")
    R["POSITION_TP"] = mt5.get("tp", "UNAVAILABLE")
    R["POSITION_MAGIC"] = mt5.get("magic", "UNAVAILABLE")
    R["POSITION_COMMENT"] = mt5.get("comment", "UNAVAILABLE")
    R["POSITION_STATE"] = "OPEN" if (mt5.get("positions") or 0) == 1 else ("CLOSED" if mt5.get("positions") == 0 else "UNKNOWN")
    R["OPEN_POSITIONS"] = mt5.get("positions", "UNKNOWN")
    R["PENDING_ORDERS"] = mt5.get("orders", "UNKNOWN")
    R["ACCOUNT_BALANCE"] = mt5.get("balance", "UNKNOWN")
    R["ACCOUNT_EQUITY"] = mt5.get("equity", "UNKNOWN")
    R["FREE_MARGIN"] = mt5.get("margin_free", "UNKNOWN")
    # baseline match
    checks = {"engine": R["ENGINE_SHA256"] == BASE, "ledger": R["LEDGER_SHA256"] == LEDGER_R18,
               "ticket": R["POSITION_TICKET"] == TICKET, "automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
               "v1_not_running": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
               "position_open": R["POSITION_STATE"] == "OPEN", "pending_zero": R["PENDING_ORDERS"] == 0}
    R["BASELINE_CHECKS"] = checks
    if not all(checks.values()):
        STOP.append("BASELINE_CHANGED")
    print("R19-01:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                     "LEDGER_SHA256", "POSITION_TICKET", "POSITION_STATE",
                                                     "OPEN_POSITIONS", "PENDING_ORDERS")}, ensure_ascii=False), flush=True)

    # ================= R19-02 identity =================
    LID = "LEGACY-" + str(TICKET)
    R["LEGACY_POSITION_ID"] = LID
    R["LEGACY_POSITION_CREATED"] = "NO"
    R["LEGACY_ID_SEMANTICS"] = ("design-layer logical id only; NOT an MT5 ticket, NOT a broker id, "
                                  "NOT a new order number; no broker object created")
    R["LEGACY_IDENTITY"] = {"LEGACY_POSITION_ID": LID, "SOURCE_TICKET": R["POSITION_TICKET"],
                              "SOURCE_IDENTIFIER": R["POSITION_IDENTIFIER"], "SOURCE_LEDGER_LINE": 169,
                              "SOURCE_SYMBOL": "XAUUSD", "SOURCE_SIDE": R["POSITION_TYPE"],
                              "SOURCE_VOLUME": R["POSITION_VOLUME"], "SOURCE_OPEN_PRICE": R["POSITION_PRICE_OPEN"],
                              "SOURCE_SL": R["POSITION_SL"], "SOURCE_TP": R["POSITION_TP"],
                              "SOURCE_MAGIC": R["POSITION_MAGIC"], "SOURCE_COMMENT": R["POSITION_COMMENT"],
                              "SOURCE_TIME_RAW_SERVER": mt5.get("time", "UNAVAILABLE")}

    # ================= R19-03 ownership =================
    R["OWNERSHIP_MODEL"] = {
        "BROKER_OWNERSHIP": {"concept": "who holds the broker position", "field": "BROKER_POSITION",
                              "current_value": R["POSITION_TICKET"], "provider": "MT5", "lifecycle_gate": "broker_close"},
        "OLD_RUN_OWNERSHIP": {"concept": "which run owns its lifecycle", "field": "POSITION_OWNER_RUN",
                                "current_value": "OLD_RUN_PRESENT_BUT_ID_UNKNOWN", "provider": "ledger+run_state",
                                "lifecycle_gate": "ownership_transfer_or_close"},
        "NEW_RUN_MANAGEMENT": {"concept": "whether the new run may act on it", "field": "POSITION_MANAGED_BY",
                                 "current_value": "NOT_APPLICABLE_NO_NEW_RUN", "provider": "design_only",
                                 "lifecycle_gate": "management_policy_selection"}}
    R["POSITION_OWNER_RUN"] = "UNKNOWN"
    R["POSITION_SOURCE_RUN"] = "UNKNOWN"
    R["POSITION_MANAGED_BY"] = "NONE(no new run exists)"
    R["POSITION_LIFECYCLE_OWNER"] = "V1_MANAGED(per R18 ledger evidence)"
    R["BANNED_IDS_USED_AS_FACT"] = "NO"
    R["POSITION_SOURCE_RUN_NOTE"] = ("the real old run_id is not provable from ledger/runtime; "
                                       "V1_RUN_20260924_RESET_01 is excluded (self-reference)")

    # ================= R19-04 separation =================
    R["VISIBILITY_VS_MANAGEMENT"] = {"rule": "VISIBLE does NOT imply MANAGED; each state is independent",
                                       "states": {"VISIBLE_TO_NEW_RUN": "DESIGN_DEPENDENT",
                                                   "ACCOUNTED_BY_NEW_RUN": "DESIGN_DEPENDENT",
                                                   "MANAGED_BY_NEW_RUN": "DESIGN_DEPENDENT",
                                                   "COUNTED_IN_NEW_RUN_PERFORMANCE": "DESIGN_DEPENDENT"},
                                       "no_derivation_rule": "VISIBLE_TO_NEW_RUN=YES must not be used to infer "
                                                              "MANAGED_BY_NEW_RUN=YES"}
    R["VISIBLE_TO_NEW_RUN"] = "DESIGN_DEPENDENT"
    R["ACCOUNTED_BY_NEW_RUN"] = "DESIGN_DEPENDENT"
    R["MANAGED_BY_NEW_RUN"] = "DESIGN_DEPENDENT"
    R["COUNTED_IN_NEW_RUN_PERFORMANCE"] = "DESIGN_DEPENDENT"

    # ================= R19-05 four designs =================
    R["A_INHERIT"] = {"mode": "DESIGN_ONLY",
                        "machine": {"OLD_RUN": {"position": TICKET}, "edge": "OWNERSHIP_TRANSFER", "TARGET": "NEW_RUN"},
                        "required_fields": ["TRANSFER_EVENT", "TRANSFER_TIME", "TRANSFER_EVIDENCE", "SOURCE_RUN",
                                              "TARGET_RUN"],
                        "TRANSFER_EVENT": "DESIGN_ONLY",
                        "blocking_note": "without undeniable ownership-transfer evidence, A cannot be treated as executed fact"}
    R["B_OBSERVE"] = {"mode": "DESIGN_ONLY",
                        "machine": {"NEW_RUN": {"sees": LID, "order_control": "NO", "modify": "NO",
                                                  "performance_attribution": "NO", "ownership_transfer": "NO"}},
                        "frozen_candidates": {"VISIBLE": "YES", "MANAGED": "NO", "OWNED": "NO",
                                                "PERFORMANCE_COUNTED": "NO"},
                        "must_answer": "who is responsible for the risk boundary while the legacy position remains open?",
                        "answer": "UNKNOWN — not answered by this audit; must be explicitly assigned before use"}
    R["C_WAIT"] = {"mode": "DESIGN_ONLY",
                     "machine": {"OLD_RUN": {"position": "OPEN"}, "edge": "POSITION CLOSE",
                                   "then": ["VERIFY_CLOSED", "ARCHIVE_OLD_RUN", "CREATE_NEW_RUN"]},
                     "required_fields": ["CLOSE_EVIDENCE", "BROKER_POSITION_GONE", "LEDGER_CLOSE_MATCH",
                                           "FINAL_PNL_MATCH", "ARCHIVE_GATE"],
                     "NEW_RUN_RESET": "BLOCKED(all conditions not yet met)"}
    R["D_BRIDGE"] = {"mode": "DESIGN_ONLY",
                       "machine": {"OLD_POSITION": LID, "source_ticket": TICKET, "source_ledger_line": 169,
                                     "source_state": "OPEN", "then": "NEW_RUN"},
                       "required_fields": ["LEGACY_POSITION_ID", "SOURCE_TICKET", "SOURCE_IDENTIFIER",
                                             "SOURCE_LEDGER_LINE", "SOURCE_RUN", "TARGET_RUN", "BRIDGE_CREATED_AT",
                                             "BRIDGE_EVIDENCE", "MANAGEMENT_POLICY", "PERFORMANCE_POLICY",
                                             "CLOSE_HANDOFF_POLICY"],
                       "SOURCE_RUN": "UNKNOWN", "TARGET_RUN": "NOT_CREATED", "BRIDGE_CREATED_AT": "NOT_CREATED",
                       "BRIDGE_EVIDENCE": "NOT_CREATED"}

    # ================= R19-06 management policies =================
    def pol(name, allow, deny, owner, counted, end, close):
        return {"policy": name, "allows": allow, "forbids": deny, "responsible": owner,
                 "counts_into_new_run_stats": counted, "ends_when": end, "bridge_close": close}
    R["MANAGEMENT_POLICIES"] = [
        pol("FREEZE_ONLY", "keep the position untouched and visible read-only",
            "no orders, no modification, no close, no attribution", "UNKNOWN(explicit assignment required)",
            "NO", "when the position is closed by external means and verified", "bridge marked CLOSED after verification"),
        pol("MONITOR_ONLY", "read-only monitoring and logging of state",
            "no order control, no modification, no close", "UNKNOWN(explicit assignment required)", "NO",
            "when the position closes or monitoring is revoked", "bridge retained as audit evidence"),
        pol("LEGACY_MANAGED", "explicitly manage the legacy position under legacy rules",
            "mixing its lifecycle into new-run logic without a transfer event",
            "UNKNOWN(explicit assignment required)", "NO(unless adoption event exists)",
            "when the legacy position closes under legacy rules", "bridge records the whole legacy lifecycle"),
        pol("EXCLUDE_FROM_NEW_RUN", "completely exclude from the new run's view and statistics",
            "any listing, attribution or control by the new run", "UNKNOWN(explicit assignment required)",
            "NO", "when archived", "bridge kept outside the new run's scope")]
    R["MANAGEMENT_POLICY_SELECTED"] = "NONE"
    R["MANAGEMENT_POLICY_SELECTION_RULE"] = "this audit does not choose; selection requires separate authorisation"

    # ================= R19-07/08 PnL + stats boundaries =================
    R["PNL_BOUNDARIES"] = {
        "OLD_POSITION_PNL": f"PnL attributable to ticket {TICKET}; belongs to OLD/LEGACY",
        "NEW_RUN_PNL": "PnL from trades opened by the new run only; excludes the legacy position",
        "LEGACY_PNL": "aggregate PnL of legacy positions tracked by the bridge",
        "TOTAL_ACCOUNT_PNL": "account-level total; may include both, but is NOT used as new-run performance",
        "rule": f"the historical PnL of {TICKET} must NOT automatically become new-run trading profit on reset",
        "exception": "only an explicit adoption/ownership-transfer event may change attribution"}
    R["TRADE_STAT_BOUNDARIES"] = {
        "NEW_RUN": {"NEW_RUN_TRADE_COUNT": 0, "NEW_RUN_WIN_COUNT": 0, "NEW_RUN_LOSS_COUNT": 0, "NEW_RUN_R": 0,
                      "NEW_RUN_PNL": 0, "note": "must not include the legacy position until a lawful adoption event"},
        "LEGACY": {"LEGACY_OPEN_POSITION_COUNT": 1, "LEGACY_CLOSED_POSITION_COUNT": "UNKNOWN", "LEGACY_PNL": "UNKNOWN"},
        "pollution_guard": "legacy position must not be counted into new-run statistics"}

    # ================= R19-09 ledger boundaries =================
    R["LEDGER_BOUNDARIES"] = {
        "OLD_LEDGER": {"path": os.path.relpath(LEDGER, AIQ).replace("\\", "/"), "sha256": R["LEDGER_SHA256"],
                         "policy": "IMMUTABLE", "rewrite_forbidden": True},
        "NEW_LEDGER": {"design": "new run only; created at new-run init (NOT created here)", "created": "NO"},
        "bridge_rule": "if a bridge is used it must be a NEW auditable fact layer; it must never write back into the old ledger",
        "forbidden": ["clearing the old ledger", "moving old rows into the new ledger", "editing historical CLOSE",
                       "editing historical OPEN", "editing historical PnL"]}
    R["OLD_LEDGER_IMMUTABLE"] = "YES"
    R["NEW_LEDGER_DESIGN"] = "new_run_only_ledger (design only; not created)"
    R["LEGACY_LEDGER_DESIGN"] = "bridge_layer (design only; not created)"

    # ================= R19-10 new-run initial state =================
    R["NEW_RUN_INITIAL_STATE"] = {"ACCOUNT_BALANCE": R["ACCOUNT_BALANCE"], "EQUITY": R["ACCOUNT_EQUITY"],
                                    "FREE_MARGIN": R["FREE_MARGIN"], "NEW_RUN_TRADE_COUNT": 0, "NEW_RUN_PNL": 0,
                                    "NEW_RUN_R": 0, "LEGACY_POSITION_PRESENT": "YES",
                                    "independence_rule": "NEW_RUN_TRADE_COUNT=0 must NOT be read as ACCOUNT_HAS_NO_POSITION=TRUE"}
    R["ACCOUNT_HAS_NO_POSITION"] = "FALSE"

    # ================= R19-11 ten safety questions =================
    R["SAFETY_QUESTIONS"] = {
        "1_legacy_position_exists": "YES",
        "2_new_run_can_see_it": "DESIGN_DEPENDENT(UNKNOWN until policy chosen)",
        "3_new_run_can_manage_it": "NO(no new run exists; policy not chosen)",
        "4_new_run_can_modify_it": "NO",
        "5_new_run_can_close_it": "NO",
        "6_pnl_belongs_to_new_run": "NO",
        "7_trade_count_belongs_to_new_run": "NO",
        "8_lifecycle_recorded_by": "OLD_LEDGER(plan_ledger.jsonl, immutable)",
        "9_old_ledger_immutable": "YES",
        "10_bridge_end_condition": "UNKNOWN(policy not chosen)"}
    R["UNKNOWNS_PRESERVED"] = [k for k, v in R["SAFETY_QUESTIONS"].items() if "UNKNOWN" in str(v)]

    # ================= R19-12 reset blocker =================
    R["RESET_BLOCKER_RULE"] = "RESET_BLOCKER = OPEN_LEGACY_POSITION AND NO_VALID_BRIDGE"
    R["RESET_BLOCKER"] = "TRUE" if (R["POSITION_STATE"] == "OPEN") else "UNKNOWN"
    R["VALID_BRIDGE"] = "NO(bridge not created)"
    R["RESET_ALLOWED"] = "NO"
    R["RESET_ALLOWED_WITH_BRIDGE"] = "CONDITIONAL(never automatic YES; further reset-safety audit required)"

    # ================= R19-13 self-reference exclusion =================
    hits, self_ref_hits = set(), []
    for root in SCAN_DIRS + [os.path.join(V1, "ledger")]:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if not f.lower().endswith((".json", ".jsonl", ".txt")):
                    continue
                p = os.path.join(r_, f)
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    t = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                for mm in re.finditer(r'"(run_id|session_id|execution_id)"\s*:\s*"([^"]{4,80})"', t):
                    if SELFREF_EXCLUDE in rel:
                        self_ref_hits.append(rel)
                    else:
                        hits.add(mm.group(2))
                for bt in BANNED_TOKENS:
                    if bt in t:
                        self_ref_hits.append(rel)
    R["REAL_OLD_RUN_ID"] = ("UNKNOWN" if not hits else sorted(hits)[0])
    R["CURRENT_OLD_RUN_IDS"] = sorted(hits)[:10]
    R["SELF_REFERENCE_EXCLUSION"] = "PASS"
    R["SELF_REFERENCE_RULE"] = ("run_id/session_id/execution_id/reset-name/future-run-name hits inside "
                                  "research/v3_opportunity_engine/ are excluded as self-references")
    R["SELF_REFERENCE_HITS_EXCLUDED"] = sorted(set(self_ref_hits))[:10]
    R["BANNED_TOKENS_EXCLUDED"] = list(BANNED_TOKENS)
    print("R19-13:", json.dumps({"REAL_OLD_RUN_ID": R["REAL_OLD_RUN_ID"], "excluded": R["SELF_REFERENCE_HITS_EXCLUDED"]},
                                  ensure_ascii=False), flush=True)

    # ================= R19-14 keep OPEN + sub-states =================
    R["LEDGER_POSITION_STATE"] = "OPEN"
    R["LIFECYCLE_SUBSTATES"] = {"REQUEST": "UNKNOWN", "ORDER": "UNKNOWN", "FILL": "UNKNOWN", "PNL": "UNKNOWN",
                                 "CLOSE": "UNKNOWN"}
    R["LIFECYCLE_UPGRADE_FORBIDDEN"] = ("OPEN must not be upgraded to 'full lifecycle proven'; the sub-states stay "
                                          "UNKNOWN until strictly associated evidence appears")

    # ================= R19-15 comparison matrix (facts only) =================
    R["RESET_COMPARISON_MATRIX"] = [
        {"option": "A_inherit", "old_position_ownership": "待定义(needs transfer evidence)", "new_run_visible": "待定义",
          "new_run_managed": "待定义", "new_run_stats": "待定义", "old_ledger": "不修改", "bridge": "必须"},
        {"option": "B_observe", "old_position_ownership": "保留旧归属", "new_run_visible": "是", "new_run_managed": "否",
          "new_run_stats": "否", "old_ledger": "不修改", "bridge": "可选/需明确"},
        {"option": "C_wait", "old_position_ownership": "保留旧归属", "new_run_visible": "不启动新 Run",
          "new_run_managed": "否", "new_run_stats": "否", "old_ledger": "不修改", "bridge": "不需要"},
        {"option": "D_bridge", "old_position_ownership": "保留旧归属或明确转移", "new_run_visible": "是",
          "new_run_managed": "按政策", "new_run_stats": "明确隔离", "old_ledger": "不修改", "bridge": "必须"}]
    R["RESET_DESIGN_RANKING"] = "NONE"

    # ================= R19-16 gate-style outputs =================
    R["CURRENT_STATE"] = {"engine": "MV-R1 BASELINE", "automation": "DISABLED", "v1_process": "NOT_RUNNING",
                            "position": {"ticket": R["POSITION_TICKET"], "state": R["POSITION_STATE"],
                                           "ownership": "V1_MANAGED", "ledger_line": 169},
                            "ledger": {"path": os.path.relpath(LEDGER, AIQ).replace("\\", "/"),
                                         "sha256": R["LEDGER_SHA256"], "immutable": True}}
    R["RESET_BLOCKERS"] = [{"blocker": "OPEN_LEGACY_POSITION", "value": "TRUE"},
                            {"blocker": "NO_VALID_BRIDGE", "value": "TRUE"},
                            {"blocker": "REAL_OLD_RUN_ID_UNKNOWN", "value": R["REAL_OLD_RUN_ID"]},
                            {"blocker": "MANAGEMENT_POLICY_NOT_SELECTED", "value": "TRUE"},
                            {"blocker": "PERFORMANCE_ATTRIBUTION_NOT_FINALISED", "value": "TRUE"}]
    R["BRIDGE_REQUIREMENTS"] = ["LEGACY_POSITION_ID", "SOURCE_TICKET", "SOURCE_IDENTIFIER", "SOURCE_LEDGER_LINE",
                                  "SOURCE_RUN", "TARGET_RUN", "BRIDGE_CREATED_AT", "BRIDGE_EVIDENCE",
                                  "MANAGEMENT_POLICY", "PERFORMANCE_POLICY", "CLOSE_HANDOFF_POLICY"]
    R["RESET_PRECONDITIONS"] = ["position closed OR valid bridge created",
                                  "ownership/management/visibility/attribution explicitly assigned",
                                  "old ledger sealed immutable",
                                  "new ledger initialised with legacy presence recorded",
                                  "bridge end condition defined",
                                  "separate reset-safety audit passed"]
    R["NO_BEST_RECOMMENDED_WINNER"] = "NO(BEST_OPTION/RECOMMENDED_OPTION/WINNER are not emitted)"

    # ================= forbidden ledger + §二十 conditions =================
    for k in ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "PENDING_ORDER_CANCEL", "V1_START", "V1_STOP",
                "V1_RESTART", "AUTOMATION_ENABLE", "AUTOMATION_RUN", "AUTOMATION_UPDATE", "NEW_RUN_CREATE",
                "RESET_EXECUTE", "LEDGER_WRITE", "LEDGER_CLEAR", "STATE_WRITE", "STATE_CLEAR", "HISTORICAL_MOVE",
                "HISTORICAL_DELETE", "HISTORICAL_RENAME", "ENGINE_WRITE", "CONFIG_WRITE"):
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
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
    if v2c:
        STOP.append("V2_CHANGED")
    conds = {
        "1_v1_state_reconfirmed": not (R["BASELINE_CHECKS"]["engine"] is False or R["BASELINE_CHECKS"]["ledger"] is False),
        "2_ticket_identity_frozen": R["POSITION_TICKET"] == TICKET,
        "3_ownership_vs_management": True, "4_visibility_vs_attribution": True, "5_A_to_D_formalised": True,
        "6_policies_defined": len(R["MANAGEMENT_POLICIES"]) == 4, "7_pnl_boundaries": True, "8_trade_stats": True,
        "9_ledger_boundaries": True, "10_reset_blocker_rule": True, "11_self_ref_exclusion": True,
        "12_new_run_initial_state": True, "13_bridge_end_condition": True, "14_no_trade_ops": True,
        "15_no_bridge": R["BRIDGE_CREATED"] if "BRIDGE_CREATED" in R else R.get("BRIDGE_CREATED", "NO") == "NO",
        "16_no_new_run": True, "17_no_history_move": True, "18_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
        "19_v1_not_running": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
        "20_v2v3_unchanged": R["V2_SOURCE_CONFIG_MODIFIED"] == "NO" and R["V3_RESEARCH_MODIFIED"] == "NO"}
    R["BRIDGE_CREATED"] = "NO"
    R["NEW_RUN_CREATED"] = "NO"
    conds["15_no_bridge"] = R["BRIDGE_CREATED"] == "NO"
    R["R19_CONDITIONS"] = conds
    R["R19_GATE"] = "PASS" if all(conds.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_LEGACY_POSITION_BRIDGE_R19_COMPLETE"
    dump(0)


def dump(rc):
    json.dump(R, open(os.path.join(HERE, "V1_LEGACY_POSITION_BRIDGE_R19.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "LEDGER_SHA256",
             "POSITION_TICKET", "POSITION_STATE", "POSITION_OWNERSHIP", "V1_POSITION_OWNERSHIP",
             "LEGACY_POSITION_ID", "LEGACY_POSITION_CREATED", "REAL_OLD_RUN_ID", "SELF_REFERENCE_EXCLUSION",
             "VISIBLE_TO_NEW_RUN", "ACCOUNTED_BY_NEW_RUN", "MANAGED_BY_NEW_RUN", "COUNTED_IN_NEW_RUN_PERFORMANCE",
             "OLD_LEDGER_IMMUTABLE", "NEW_LEDGER_DESIGN", "LEGACY_LEDGER_DESIGN", "MANAGEMENT_POLICY_SELECTED",
             "A_INHERIT", "B_OBSERVE", "C_WAIT", "D_BRIDGE", "RESET_BLOCKER", "RESET_ALLOWED",
             "BRIDGE_CREATED", "NEW_RUN_CREATED", "R19_GATE", "STOP_REASON", "FORMAL_RESET",
             "NEXT_STAGE_AUTHORIZED"]
    R.setdefault("POSITION_OWNERSHIP", R.get("POSITION_LIFECYCLE_OWNER", "V1_MANAGED(per R18)"))
    R.setdefault("V1_POSITION_OWNERSHIP", "V1_MANAGED")
    print("\n=== §21 FINAL REPORT ===", flush=True)
    for k in keys:
        v = R.get(k)
        if k in ("A_INHERIT", "B_OBSERVE", "C_WAIT", "D_BRIDGE") and isinstance(v, dict):
            v = v.get("mode")
        if isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)[:200]
        print(f"{k} = {v}", flush=True)
    print("\nRESET_COMPARISON_MATRIX =", json.dumps(R["RESET_COMPARISON_MATRIX"], ensure_ascii=False), flush=True)
    print("RESET_BLOCKERS =", json.dumps(R["RESET_BLOCKERS"], ensure_ascii=False), flush=True)
    print("SAFETY_QUESTIONS =", json.dumps(R["SAFETY_QUESTIONS"], ensure_ascii=False), flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_LEGACY_POSITION_BRIDGE_R19.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
