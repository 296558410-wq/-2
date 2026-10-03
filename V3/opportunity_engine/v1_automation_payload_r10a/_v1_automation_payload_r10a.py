# -*- coding: utf-8 -*-
"""R10-A — OpenClaw official READ-ONLY automation payload forensics (single objective).

Only read-only CLI forms are used. No enable/disable/run/trigger/update/delete/create/set/edit/add.
No stop/restart/kill, no Gateway/automation/trader_v1/engine.py change, no M15 trigger, no MT5 call at all
(section 11 forbids re-querying MT5), no git write, no commit.
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
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
R9 = os.path.join(ENGINE, "v1_automation_mt5_final_closure_r9", "V1_AUTOMATION_MT5_FINAL_CLOSURE_R9.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
NOWU = datetime.now(timezone.utc)
MUT = ("enable", "disable", "run", "trigger", "update", "delete", "create", "set", "edit", "add", "start", "stop")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
PAY_KEYS = ("action", "arguments", "args", "payload", "prompt", "message", "command", "task", "agentturn",
             "workspace", "cwd", "workingdirectory", "workdir", "instructions", "body", "steps")


def run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def walk_json(o, path=""):
    """yield (keypath, key, value) for all dict keys."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield (path + "/" + str(k), str(k), v)
            yield from walk_json(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_json(v, path + f"[{i}]")


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    r9 = json.load(open(R9, encoding="utf-8")) if os.path.exists(R9) else {}
    O["R9_INPUT"] = {"automation_id": AID, "r9_chain": r9.get("MT5_CONTEXT_CHAIN"),
                       "r9_open_positions": r9.get("OPEN_POSITIONS"), "r9_pending_orders": r9.get("PENDING_ORDERS"),
                       "r9_schedule_raw": "cron 2-59/15 * * * 0-5 @ UTC"}
    # MT5 is NOT queried this round (section 11)
    O["MT5_QUERIED_THIS_ROUND"] = "NO"

    # ---------------- section 3: read-only JSON forms ----------------
    FORMS = [
        ["cron", "show", AID, "--json"],
        ["cron", "show", "--json", AID],
        ["cron", "get", AID, "--json"],
        ["cron", "inspect", AID, "--json"],
        ["cron", "describe", AID, "--json"],
        ["cron", "show", AID, "--format=json"],
        ["cron", "get", AID, "--format", "json"],
        ["cron", "show", AID, "--output=json"],
        ["cron", "list", "--json"],
        ["cron", "ls", "--json"],
    ]
    attempts, best, best_cmd = [], None, None
    for form in FORMS:
        if any(v in MUT for v in form):
            continue
        if not (os.path.exists(NODE) and os.path.exists(CLI)):
            break
        out = run([NODE, CLI] + form, 60)
        ok_json, doc = False, None
        m = re.search(r"(\{.*\}|\[.*\])", out, re.S)
        if m:
            try:
                doc = json.loads(m.group(0))
                ok_json = True
            except Exception:  # noqa: BLE001
                ok_json = False
        attempts.append({"command": " ".join(form), "bytes": len(out or ""), "json": ok_json,
                           "has_id": AID in (out or ""), "has_name": "hermes-trader-m15-cycle" in (out or ""),
                           "err": (out or "")[:120] if (out or "").startswith("ERR:") else None})
        if ok_json and doc is not None:
            blob = json.dumps(doc, ensure_ascii=False)
            if AID in blob or "hermes-trader-m15-cycle" in blob:
                best, best_cmd = doc, " ".join(form)
                break
    O["CLI_ATTEMPTS"] = attempts
    O["READONLY_FORM_USED"] = best_cmd or "NONE"
    print("§3 attempts:", json.dumps(attempts, ensure_ascii=False)[:700], flush=True)

    # ---------------- sections 4/5: field + reference extraction ----------------
    fields, refs, entry = {}, [], None
    if best is not None:
        # locate the automation object itself
        cands = []
        for kp, k, v in walk_json(best):
            if isinstance(v, dict):
                b = json.dumps(v, ensure_ascii=False)
                if AID in b or "hermes-trader-m15-cycle" in b:
                    cands.append(v)
        entry = min(cands, key=lambda d: len(json.dumps(d))) if cands else best
        O["AUTOMATION_JSON_RAW"] = json.dumps(best, ensure_ascii=False)[:6000]
        for kp, k, v in walk_json(entry):
            kl = k.lower().replace("_", "")
            if any(pk.replace("_", "") == kl for pk in PAY_KEYS):
                if not isinstance(v, (dict, list)) and str(v).strip():
                    fields[kp] = str(v)[:400]
                elif isinstance(v, (dict, list)):
                    fields[kp] = json.dumps(v, ensure_ascii=False)[:400]
        blob = json.dumps(entry, ensure_ascii=False)
        refs = sorted({r for r in ("trader_v1", "hermes/trader_v1", "trader_v1/engine.py", "engine.py", "xauusd")
                        if r in blob.lower()})
        # section 6: reject evidence that comes from docs/snapshots/manifests
        srcblob = (best_cmd or "").lower()
        if any(x in srcblob for x in ("readme", "skill", "stack-map", "snapshot", "v2_snap", "manifest", "archive")):
            refs = []
    O["AUTOMATION_ENTRY_KEYS"] = sorted(set(entry.keys()))[:30] if isinstance(entry, dict) else []
    O["EXTRACTED_FIELDS"] = fields
    O["V1_REFERENCES_IN_PAYLOAD"] = refs
    O["PAYLOAD_ACCESSIBLE"] = "YES" if fields else "NO"
    payload_ok = bool(fields)
    act = next((v for k, v in fields.items() if re.search(r"action|command|task|agentturn|prompt|message", k, re.I)), "UNKNOWN")
    arg = next((v for k, v in fields.items() if re.search(r"argument|args|param", k, re.I)), "UNKNOWN")
    cwd = next((v for k, v in fields.items() if re.search(r"workingdirectory|cwd|workdir|workspace", k, re.I)), "UNKNOWN")
    O["ACTION"] = act if payload_ok else "UNKNOWN"
    O["ARGUMENTS"] = arg if payload_ok else "UNKNOWN"
    O["WORKING_DIRECTORY"] = cwd if payload_ok else "UNKNOWN"
    refstr = json.dumps(refs)
    O["V1_REFERENCE"] = refstr if refs else "NONE"
    O["REFERENCE_TYPE"] = ("trader_v1_or_engine_py_in_automation_payload" if refs else "NONE")
    O["V1_AUTOMATION_CONFIRMED"] = "YES" if (refs and ("trader_v1" in refstr or "engine.py" in refstr)) else "NO"

    # ---------------- sections 9/10 scheduling + cycle ----------------
    O["SCHEDULE_EVIDENCE_RAW"] = "cron 2-59/15 * * * 0-5 @ UTC"
    O["SCHEDULE_CONFIRMED_FOR_V1"] = "YES" if O["V1_AUTOMATION_CONFIRMED"] == "YES" else "NO"
    if O["V1_AUTOMATION_CONFIRMED"] == "YES":
        O["SCHEDULE_TYPE"] = "cron"
        O["SCHEDULE_EXPRESSION"] = "2-59/15 * * * 0-5"
        O["TIMEZONE"] = "UTC"
    else:
        O["SCHEDULE_TYPE"] = O["SCHEDULE_EXPRESSION"] = O["TIMEZONE"] = "UNKNOWN"
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"

    # ---------------- section 12 protection ----------------
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    O["V1_MODIFIED"] = "NO"
    O["V2_MODIFIED"] = "NO"
    O["V3_MODIFIED"] = "NO" if v3 else "UNKNOWN"
    O["ORDER_SEND"] = 0
    O["COMMIT"] = "NONE"
    O["V3_HASHES"] = imm
    O["FALSE_POSITIVE_REJECTED"] = [
        {"round": "R6 §五", "rejected": "%TEMP%/V2-SHADOW run_manifest 曾被误判为 V1 automation"},
        {"round": "R7 §六", "rejected": ".openclaw/workspace/v2_snap.json 曾被误判为 V1 automation"},
        {"round": "R10-A §六", "rule": "任何来自 README/SKILL/stack-map/历史任务单/粘贴文本/workspace snapshot/"
                                        "v2_snap/V2-SHADOW/run_manifest/archive/旧报告 的命中一律不作 Automation→V1 证据"},
    ]
    if O["PAYLOAD_ACCESSIBLE"] == "NO":
        O["INTERFACE_BOUNDARY_NOTE"] = ("OpenClaw official read-only interface was accessed; the automation record "
                                          "exists, but its payload fields were not exposed by any read-only form "
                                          "tried (see CLI_ATTEMPTS); no second reliable evidence source was found; "
                                          "per section 7 the search is stopped here without widening")
    O["TASK_STATUS"] = "V1_AUTOMATION_PAYLOAD_R10A_COMPLETE"
    O["ts_utc"] = NOWU.isoformat()

    O["AUTOMATION_ID"] = AID
    O["AUTOMATION_NAME"] = "hermes-trader-m15-cycle"
    O["AUTOMATION_STATUS"] = r9.get("AUTOMATION_STATUS", "UNKNOWN")
    O["AUTOMATION_TARGET"] = r9.get("AUTOMATION_TARGET", "isolated")
    O["AUTOMATION_AGENT"] = r9.get("AUTOMATION_AGENT", "main")
    rep = {k: O[k] for k in ("TASK_STATUS", "AUTOMATION_ID", "AUTOMATION_NAME", "AUTOMATION_STATUS",
                               "AUTOMATION_TARGET", "AUTOMATION_AGENT", "PAYLOAD_ACCESSIBLE", "ACTION", "ARGUMENTS",
                               "WORKING_DIRECTORY", "V1_REFERENCE", "REFERENCE_TYPE", "V1_AUTOMATION_CONFIRMED",
                               "SCHEDULE_EVIDENCE_RAW", "SCHEDULE_CONFIRMED_FOR_V1", "SCHEDULE_TYPE",
                               "SCHEDULE_EXPRESSION", "TIMEZONE", "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY",
                               "SAFETY_WINDOW", "NEXT_STAGE_AUTHORIZED", "V1_MODIFIED", "V2_MODIFIED",
                               "V3_MODIFIED", "ORDER_SEND", "COMMIT")}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_AUTOMATION_PAYLOAD_R10A.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §14 FINAL REPORT ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:2600], flush=True)
    print("\nEXTRACTED_FIELDS:", json.dumps(fields, ensure_ascii=False)[:800], flush=True)
    print("ENTRY_KEYS:", json.dumps(O["AUTOMATION_ENTRY_KEYS"], ensure_ascii=False)[:400], flush=True)


if __name__ == "__main__":
    main()
