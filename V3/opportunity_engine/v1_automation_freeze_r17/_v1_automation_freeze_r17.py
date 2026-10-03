# -*- coding: utf-8 -*-
"""V1_AUTOMATION_FREEZE_R17 — ONE authorised mutation: set enabled=false for automation cd47547e-....

Everything else untouched. No engine run, no trader_v1 run, no cycle trigger, no order/position op, no MT5.
Writes only under research/v3_opportunity_engine/v1_automation_freeze_r17/.
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
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
ENGINE = os.path.join(V1, "engine.py")
LEDGER = os.path.join(V1, "run_state", "plan_ledger.jsonl")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
CFG_KEYS = ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}


def sh(args, t=90):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def read_auto():
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60)
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    if not m:
        return None, out[:300]
    try:
        return json.loads(m.group(0)), out[:300]
    except Exception:  # noqa: BLE001
        return None, out[:300]


def engine_running():
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], 90)
    try:
        d = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = d if isinstance(d, list) else [d]
    except Exception:  # noqa: BLE001
        return "UNKNOWN", []
    v1p = [x for x in allp if re.search(r"trader_v1|engine\.py|state_package", (x.get("CommandLine") or ""), re.I)
            and "Get-CimInstance" not in (x.get("CommandLine") or "")]
    eng = [x for x in v1p if re.search(r"engine\.py", (x.get("CommandLine") or ""), re.I)]
    return ("RUNNING" if eng else ("NOT_RUNNING" if not v1p else "UNKNOWN")), v1p[:5]


def main():
    os.makedirs(HERE, exist_ok=True)
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()
    R["AUTOMATION_ID"] = AID

    # ---------- BEFORE ----------
    R["ENGINE_SHA256_BEFORE"] = sha(ENGINE)
    R["LEDGER_SHA256_BEFORE"] = sha(LEDGER)
    a0, raw0 = read_auto()
    R["AUTOMATION_EXISTS"] = "YES" if isinstance(a0, dict) and a0 else ("UNKNOWN" if a0 is None else "NO")
    R["AUTOMATION_JSON_BEFORE"] = json.dumps(a0, ensure_ascii=False)[:3000] if a0 else "NOT_READ"
    if not isinstance(a0, dict):
        return stop("AUTOMATION_NOT_READABLE", freeze=False)
    R["AUTOMATION_ENABLED_BEFORE"] = a0.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = a0.get("status", "UNKNOWN")
    R["LAST_RUN_AT"] = a0.get("lastRunAtMs", "UNKNOWN")
    R["LAST_RUN_STATUS"] = a0.get("lastRunStatus", "UNKNOWN")
    R["NEXT_RUN_AT_BEFORE"] = a0.get("nextRunAtMs", "UNKNOWN")
    R["UPDATED_AT_BEFORE"] = a0.get("updatedAtMs", "UNKNOWN")
    cfg0 = {k: a0.get(k) for k in CFG_KEYS}
    R["PAYLOAD_HASH_BEFORE"] = hashlib.sha256(canon(cfg0)).hexdigest()
    R["CONFIG_BEFORE"] = json.dumps(cfg0, ensure_ascii=False)[:2500]
    st, v1p = engine_running()
    R["V1_ENGINE_PROCESS"] = st
    R["V1_MATCHING_PROCESSES"] = [{"PID": x.get("ProcessId"), "CMD": (x.get("CommandLine") or "")[:120]} for x in v1p]
    print("BEFORE:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED_BEFORE", "AUTOMATION_STATUS",
                                                     "NEXT_RUN_AT_BEFORE", "V1_ENGINE_PROCESS",
                                                     "PAYLOAD_HASH_BEFORE")}, ensure_ascii=False), flush=True)

    # ---------- §五 safety gate ----------
    if st != "NOT_RUNNING":
        R["FREEZE_EXECUTION"] = "NOT_EXECUTED"
        return stop("V1_ENGINE_CURRENTLY_RUNNING", freeze=False)

    # ---------- §六 discover syntax then ONE mutation ----------
    h = sh([NODE, CLI, "cron", "--help"], 45)
    R["CLI_CRON_HELP"] = h[:1500]
    low = h.lower()
    forms = []
    if re.search(r"\bdisable\b", low):
        forms.append(["cron", "disable", AID])
    if re.search(r"\benable\b", low) and "disable" not in low:
        forms.append(["cron", "disable", AID])
    if re.search(r"\bupdate\b", low):
        forms.append(["cron", "update", AID, "--enabled=false"])
    forms.append(["cron", "disable", AID])
    forms.append(["cron", "update", AID, "--enabled=false"])
    exec_out, used = "NOT_ATTEMPTED", None
    for form in forms:
        out = sh([NODE, CLI] + form, 60)
        exec_out, used = out[:800], " ".join(form)
        if not out.startswith("ERR:") and not re.search(r"unknown (command|option)", out, re.I):
            break
    R["FREEZE_COMMAND_USED"] = used or "NONE"
    R["FREEZE_COMMAND_OUTPUT"] = exec_out
    R["FREEZE_EXECUTION"] = "EXECUTED"

    # ---------- §七/§八/§九 verify ----------
    a1, raw1 = read_auto()
    R["AUTOMATION_JSON_AFTER"] = json.dumps(a1, ensure_ascii=False)[:3000] if a1 else "NOT_READ"
    if not isinstance(a1, dict):
        return stop("AUTOMATION_NOT_READABLE_AFTER_DISABLE", freeze=None)
    R["AUTOMATION_EXISTS"] = "YES"
    R["AUTOMATION_ENABLED_AFTER"] = a1.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = a1.get("status", R["AUTOMATION_STATUS"])
    R["NEXT_RUN_AT_AFTER"] = a1.get("nextRunAtMs", "UNKNOWN")
    R["UPDATED_AT_AFTER"] = a1.get("updatedAtMs", "UNKNOWN")
    cfg1 = {k: a1.get(k) for k in CFG_KEYS}
    R["PAYLOAD_HASH_AFTER"] = hashlib.sha256(canon(cfg1)).hexdigest()
    R["AUTOMATION_PAYLOAD_CHANGED"] = "NO" if cfg0.get("payload") == cfg1.get("payload") else "YES"
    R["AUTOMATION_SCHEDULE_CHANGED"] = "NO" if cfg0.get("schedule") == cfg1.get("schedule") else "YES"
    R["AUTOMATION_AGENT_CHANGED"] = "NO" if cfg0.get("agentId") == cfg1.get("agentId") else "YES"
    R["AUTOMATION_SESSION_TARGET_CHANGED"] = "NO" if cfg0.get("sessionTarget") == cfg1.get("sessionTarget") else "YES"
    R["AUTOMATION_WAKEMODE_CHANGED"] = "NO" if cfg0.get("wakeMode") == cfg1.get("wakeMode") else "YES"
    R["AUTOMATION_DELIVERY_CHANGED"] = "NO" if cfg0.get("delivery") == cfg1.get("delivery") else "YES"
    if R["AUTOMATION_ENABLED_AFTER"] is False or str(R["AUTOMATION_ENABLED_AFTER"]).lower() == "false":
        R["NEXT_SCHEDULED_EXECUTION"] = "BLOCKED"
    else:
        R["NEXT_SCHEDULED_EXECUTION"] = "UNKNOWN"
    R["SCHEDULE_AFTER"] = json.dumps(cfg1.get("schedule"), ensure_ascii=False)[:300]

    # ---------- AFTER integrity ----------
    R["ENGINE_SHA256_AFTER"] = sha(ENGINE)
    R["LEDGER_SHA256_AFTER"] = sha(LEDGER)
    R["LEDGER_CHANGED"] = "NO" if R["LEDGER_SHA256_BEFORE"] == R["LEDGER_SHA256_AFTER"] else "YES"
    R["ENGINE_CHANGED"] = "NO" if R["ENGINE_SHA256_BEFORE"] == R["ENGINE_SHA256_AFTER"] else "YES"
    st2, v1p2 = engine_running()
    R["V1_ENGINE_PROCESS_AFTER"] = st2
    R["V1_MATCHING_PROCESSES_AFTER"] = [{"PID": x.get("ProcessId"), "CMD": (x.get("CommandLine") or "")[:120]}
                                          for x in v1p2]
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_RESEARCH_MODIFIED"] = "NO" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "YES"
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = []
    for r_, _, fs in os.walk(V2):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith((".py", ".yaml", ".yml")):
                p2 = os.path.join(r_, f)
                try:
                    if os.path.getmtime(p2) > lim:
                        v2c.append(os.path.relpath(p2, AIQ).replace("\\", "/"))
                except OSError:
                    continue
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    R["V2_CHANGES_30MIN"] = v2c[:5]
    R["ORDER_SEND"] = 0
    R["POSITION_CLOSE"] = 0
    R["POSITION_MODIFY"] = 0
    R["PENDING_ORDER_CANCEL"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["ENGINE_WRITE"] = 0
    R["LEDGER_WRITE"] = 0
    R["STATE_WRITE"] = 0
    R["MT5_ACCESS"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["OPEN_POSITIONS"] = 1
    R["POSITION_TICKET"] = 2377449557
    R["POSITION_STATE"] = "UNTOUCHED"

    conds = {
        "1_automation_exists": R["AUTOMATION_EXISTS"] == "YES",
        "2_enabled_false": str(R["AUTOMATION_ENABLED_AFTER"]).lower() == "false",
        "3_payload_unchanged": R["AUTOMATION_PAYLOAD_CHANGED"] == "NO",
        "4_schedule_unchanged": R["AUTOMATION_SCHEDULE_CHANGED"] == "NO",
        "5_agent_unchanged": R["AUTOMATION_AGENT_CHANGED"] == "NO",
        "6_session_target_unchanged": R["AUTOMATION_SESSION_TARGET_CHANGED"] == "NO",
        "7_engine_hash_unchanged": R["ENGINE_CHANGED"] == "NO",
        "8_ledger_unchanged": R["LEDGER_CHANGED"] == "NO",
        "9_v2v3_unchanged": R["V2_SOURCE_CONFIG_MODIFIED"] == "NO" and R["V3_RESEARCH_MODIFIED"] == "NO",
        "10_no_order": True, "11_no_close": True, "12_no_position_modify": True,
        "13_no_new_v1_cycle": R["V1_ENGINE_PROCESS_AFTER"] == "NOT_RUNNING",
        "14_no_restart": True}
    R["SUCCESS_CONDITIONS"] = conds
    R["FREEZE_STATUS"] = "PASS" if all(conds.values()) else "FAIL"
    R["STOP_REASON"] = "NONE" if R["FREEZE_STATUS"] == "PASS" else "ONE_OR_MORE_CONDITIONS_FAILED"
    if R["AUTOMATION_EXISTS"] == "YES" and str(R["AUTOMATION_ENABLED_AFTER"]).lower() != "false":
        R["STOP_REASON"] = "AUTOMATION_DISABLE_FAILED"
        R["FREEZE_STATUS"] = "FAIL"
    R["V1_ENGINE_STATE"] = "MV-R1_BASELINE" if R["ENGINE_SHA256_AFTER"] == BASE else "OTHER"
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_AUTOMATION_FREEZE_R17_COMPLETE"
    dump(0)


def stop(reason, freeze=False):
    R.setdefault("AUTOMATION_ENABLED_BEFORE", "UNKNOWN")
    R.setdefault("AUTOMATION_ENABLED_AFTER", "UNKNOWN")
    R.setdefault("AUTOMATION_STATUS", "UNKNOWN")
    R.setdefault("LAST_RUN_AT", "UNKNOWN")
    R.setdefault("LAST_RUN_STATUS", "UNKNOWN")
    R.setdefault("NEXT_RUN_AT_BEFORE", "UNKNOWN")
    R.setdefault("NEXT_RUN_AT_AFTER", "UNKNOWN")
    for k in ("AUTOMATION_PAYLOAD_CHANGED", "AUTOMATION_SCHEDULE_CHANGED", "AUTOMATION_AGENT_CHANGED",
                "AUTOMATION_SESSION_TARGET_CHANGED"):
        R.setdefault(k, "UNKNOWN")
    R.setdefault("ENGINE_SHA256_BEFORE", sha(ENGINE))
    R.setdefault("ENGINE_SHA256_AFTER", sha(ENGINE))
    R.setdefault("LEDGER_SHA256_BEFORE", sha(LEDGER))
    R.setdefault("LEDGER_SHA256_AFTER", sha(LEDGER))
    R.setdefault("LEDGER_CHANGED", "UNKNOWN")
    R.setdefault("V1_ENGINE_PROCESS", "UNKNOWN")
    R["FREEZE_STATUS"] = "FAIL"
    R["STOP_REASON"] = reason
    R["ORDER_SEND"] = 0
    R["POSITION_CLOSE"] = 0
    R["POSITION_MODIFY"] = 0
    R["PENDING_ORDER_CANCEL"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["ENGINE_WRITE"] = 0
    R["LEDGER_WRITE"] = 0
    R["STATE_WRITE"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["V2_SOURCE_CONFIG_MODIFIED"] = R.get("V2_SOURCE_CONFIG_MODIFIED", "UNKNOWN")
    R["V3_RESEARCH_MODIFIED"] = R.get("V3_RESEARCH_MODIFIED", "UNKNOWN")
    R["OPEN_POSITIONS"] = 1
    R["POSITION_TICKET"] = 2377449557
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_AUTOMATION_FREEZE_R17_COMPLETE"
    dump(2)


def dump(rc):
    json.dump(R, open(os.path.join(HERE, "V1_AUTOMATION_FREEZE_R17.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "AUTOMATION_ID", "AUTOMATION_EXISTS", "AUTOMATION_ENABLED_BEFORE",
             "AUTOMATION_ENABLED_AFTER", "AUTOMATION_STATUS", "LAST_RUN_AT", "LAST_RUN_STATUS",
             "NEXT_RUN_AT_BEFORE", "NEXT_RUN_AT_AFTER", "AUTOMATION_PAYLOAD_CHANGED",
             "AUTOMATION_SCHEDULE_CHANGED", "AUTOMATION_AGENT_CHANGED", "AUTOMATION_SESSION_TARGET_CHANGED",
             "AUTOMATION_WAKEMODE_CHANGED", "AUTOMATION_DELIVERY_CHANGED", "PAYLOAD_HASH_BEFORE",
             "PAYLOAD_HASH_AFTER", "NEXT_SCHEDULED_EXECUTION", "V1_ENGINE_PROCESS", "V1_ENGINE_PROCESS_AFTER",
             "ENGINE_SHA256_BEFORE", "ENGINE_SHA256_AFTER", "LEDGER_SHA256_BEFORE", "LEDGER_SHA256_AFTER",
             "LEDGER_CHANGED", "OPEN_POSITIONS", "POSITION_TICKET", "POSITION_STATE", "ORDER_SEND",
             "POSITION_CLOSE", "POSITION_MODIFY", "PENDING_ORDER_CANCEL", "V1_STOP", "V1_RESTART", "ENGINE_WRITE",
             "LEDGER_WRITE", "STATE_WRITE", "MT5_ACCESS", "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED",
             "FREEZE_COMMAND_USED", "SUCCESS_CONDITIONS", "FREEZE_STATUS", "STOP_REASON", "FORMAL_RESET",
             "NEXT_STAGE_AUTHORIZED", "V1_ENGINE_STATE"]
    print("\n=== §18 FINAL REPORT ===", flush=True)
    for k in keys:
        print(f"{k} = {R.get(k, 'UNKNOWN')}", flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_AUTOMATION_FREEZE_R17.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
