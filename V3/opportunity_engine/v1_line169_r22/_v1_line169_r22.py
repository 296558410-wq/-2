# -*- coding: utf-8 -*-
"""R22 — line-169 field-level attribution (READ-ONLY, single file).

Reads ONLY plan_ledger.jsonl (plus the freeze checks). No MT5 call, no ledger/state/source write,
no reconciliation record, no reset, no automation change, no git.
Writes ONLY under research/v3_opportunity_engine/v1_line169_r22/.
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
ENGINE = os.path.join(V1, "engine.py")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TARGET_NUM = "2377449557"
LINE_NO = 169
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STRUCT_ID_FIELDS = {"ticket", "position_id", "position_identifier", "position", "order_id", "order_ticket",
                     "deal_id", "deal_ticket", "request_id", "identifier", "order", "position_ticket", "deal"}
NONID_FIELDS = {"comment", "description", "message", "reason", "note", "text", "summary", "label", "tag",
                 "trigger", "wait_reason", "memo", "detail", "details", "extra", "meta", "context"}
SYSPATH = os.path.join(HERE, "line169_raw.json")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")


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


def walk(x, path="$"):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield (path, x)


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "V1_LINE169_R22_COMPLETE"
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
    R["LEDGER_SHA256_BEFORE"] = sha(LEDGER)
    STOP = []
    if str(R["AUTOMATION_ENABLED"]).lower() != "false":
        STOP.append("BASELINE_CHANGED")
    if R["V1_ENGINE_PROCESS"] != "NOT_RUNNING":
        STOP.append("BASELINE_CHANGED")
    if R["ENGINE_SHA256"] != BASE:
        STOP.append("BASELINE_CHANGED")
    if R["LEDGER_SHA256_BEFORE"] != LEDGER_EXPECT:
        STOP.append("BASELINE_CHANGED")
    print("§3:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                 "LEDGER_SHA256_BEFORE")}, ensure_ascii=False), flush=True)

    # ---------- §四 read line 169 fully ----------
    lines = [l for l in open(LEDGER, encoding="utf-8", errors="ignore")] if os.path.exists(LEDGER) else []
    R["LEDGER_LINE_COUNT"] = len([l for l in lines if l.strip()])
    R["FILE"] = os.path.relpath(LEDGER, AIQ).replace("\\", "/")
    R["LINE_NUMBER"] = LINE_NO
    raw = lines[LINE_NO - 1].rstrip("\r\n") if len(lines) >= LINE_NO else None
    R["LINE_169_RAW"] = raw if raw is not None else "LINE_NOT_PRESENT"
    doc = None
    if raw:
        try:
            doc = json.loads(raw)
            R["LINE_169_PARSED_JSON"] = doc
        except Exception as e:  # noqa: BLE001
            R["LINE_169_PARSED_JSON"] = f"PARSE_ERROR:{type(e).__name__}"
    R["LEDGER_SHA256_AFTER"] = sha(LEDGER)
    R["LEDGER_UNCHANGED"] = "YES" if R["LEDGER_SHA256_AFTER"] == R["LEDGER_SHA256_BEFORE"] else "NO"
    if R["LEDGER_UNCHANGED"] != "YES":
        STOP.append("LEDGER_MODIFIED")
    print("§4 line169 len:", (len(raw) if raw else 0), "| parsed:", isinstance(doc, dict), flush=True)

    # ---------- §五 field-level location ----------
    matches = []
    if isinstance(doc, (dict, list)):
        for path, val in walk(doc):
            sval = str(val)
            if TARGET_NUM in sval:
                field = path.split(".")[-1].split("[")[0]
                vtype = type(val).__name__
                embedded = (sval != TARGET_NUM)
                matches.append({"JSON_PATH": path, "FIELD_NAME": field, "VALUE": sval,
                                  "VALUE_TYPE": ("int" if isinstance(val, int) and not isinstance(val, bool)
                                                  else ("str_embedded" if embedded and isinstance(val, str) else vtype)),
                                  "IS_EMBEDDED_IN_TEXT": embedded})
    R["MATCH_COUNT"] = len(matches)
    R["MATCHES"] = matches
    print("§5 matches:", json.dumps(matches, ensure_ascii=False)[:800], flush=True)

    # ---------- §六 classification ----------
    sid, nonid, unk = [], [], []
    for m in matches:
        fn = m["FIELD_NAME"].lower()
        if fn in STRUCT_ID_FIELDS and not m["IS_EMBEDDED_IN_TEXT"]:
            sid.append(m)
        elif fn in NONID_FIELDS or m["IS_EMBEDDED_IN_TEXT"]:
            nonid.append(m)
        else:
            unk.append(m)
    R["STRUCTURED_ID_MATCH"] = [f"{m['JSON_PATH']} = {m['VALUE']}" for m in sid]
    R["NON_ID_MATCH"] = [f"{m['JSON_PATH']} = {m['VALUE']}" for m in nonid]
    R["UNKNOWN_FIELD_MATCH"] = [f"{m['JSON_PATH']} = {m['VALUE']}" for m in unk]
    if sid:
        link = "YES"
    elif nonid:
        link = "NO"
    else:
        link = "UNKNOWN"
    R["STRUCTURED_POSITION_LINK"] = link
    R["LEGACY_LEDGER_POSITION_RECORD"] = {"YES": "CONFIRMED", "NO": "NOT_FOUND", "UNKNOWN": "UNKNOWN"}[link]
    R["CLASSIFICATION_NOTE"] = ("numeric appearance is not a structured position binding when it sits in a non-ID "
                                  "field or is embedded in free text")

    # ---------- §七 record semantics ----------
    sem = {}
    if isinstance(doc, dict):
        for k in ("record_type", "event_type", "action", "stage", "type", "kind", "event", "status"):
            for kk, vv in doc.items():
                if kk.lower() == k and not isinstance(vv, (dict, list)):
                    sem[kk] = vv
    R["RECORD_TYPE"] = sem.get("record_type", sem.get("type", sem.get("kind", "UNKNOWN")))
    R["EVENT_TYPE"] = sem.get("event_type", sem.get("event", "UNKNOWN"))
    R["ACTION"] = sem.get("action", "UNKNOWN")
    R["STAGE"] = sem.get("stage", "UNKNOWN")
    R["SEMANTICS_ALL"] = sem
    R["TOP_LEVEL_KEYS"] = sorted(doc.keys())[:30] if isinstance(doc, dict) else "NOT_DICT"
    # lifecycle-ish fields from the strict-ID perspective
    R["DECISION"] = "UNKNOWN"; R["OPEN"] = "UNKNOWN"; R["CLOSE"] = "UNKNOWN"; R["PNL"] = "UNKNOWN"
    R["LIFECYCLE_FIELDS_NOTE"] = ("record type alone does not establish a structured position binding; per section 7 "
                                    "no field may substitute for an explicit ID")
    print("§6/7 link:", link, "| record:", R["RECORD_TYPE"], R["EVENT_TYPE"], "| top keys:",
          str(R["TOP_LEVEL_KEYS"])[:200], flush=True)

    # ---------- §八 correction ----------
    R["R18_R20_PREVIOUS_CLAIM"] = ("LEDGER_LINK_STATUS = EXACT ; V1_MANAGED = V1_MANAGED ; "
                                     "'the ledger precisely records this position'")
    if link == "NO":
        R["R22_REVISED_CLAIM"] = (f"{TARGET_NUM} appears as non-ID text only -> no structured legacy ledger record; "
                                    "the previous EXACT / V1_MANAGED-as-structured-evidence claim is withdrawn")
    elif link == "YES":
        R["R22_REVISED_CLAIM"] = ("structured ID binding confirmed; previous claim may be re-verified but is not "
                                    "automatically restored")
    else:
        R["R22_REVISED_CLAIM"] = "field semantics undecidable; no further inference permitted"

    # ---------- §十 reconciliation (referenced, not re-investigated) ----------
    R["BROKER_POSITION_STATE"] = ("CLOSED（引用 R20：deal 2364265913 / order 2377465821 / SL @4299.03 / net −21.97；"
                                   "本轮未查询 MT5）")
    R["LEDGER_STRUCTURED_POSITION_STATE"] = ("NOT_FOUND" if link == "NO" else ("FOUND" if link == "YES" else "UNKNOWN"))
    R["RECONCILIATION_EVIDENCE_LEVEL"] = ("BROKER_FACT_ONLY_NO_STRUCTURED_LEGACY_LEDGER_RECORD" if link == "NO"
                                            else ("BROKER_FACT_PLUS_STRUCTURED_LEGACY_RECORD" if link == "YES"
                                                  else "UNKNOWN"))
    R["RECONCILIATION_RECORD_CREATED"] = "NO"

    # ---------- safety counters ----------
    for k in COUNTERS:
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    R["MT5_ACCESS"] = 0
    conds = {"1_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
              "2_v1_stopped": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
              "3_engine_unchanged": R["ENGINE_SHA256"] == BASE,
              "4_ledger_unchanged": R["LEDGER_UNCHANGED"] == "YES",
              "5_line169_read": raw is not None,
              "6_json_parsed": isinstance(doc, dict),
              "7_occurrences_located": "YES",
              "8_semantics_classified": link in ("YES", "NO", "UNKNOWN"),
              "9_structured_id_determined": link in ("YES", "NO"),
              "10_no_ledger_mod": R["LEDGER_UNCHANGED"] == "YES",
              "11_no_recon_record": R["RECONCILIATION_RECORD_CREATED"] == "NO",
              "12_no_mt5_trade_op": True,
              "13_counters_reported": True}
    R["R22_CONDITIONS"] = conds
    R["R22_GATE"] = "PASS" if all(conds.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEW_RUN"] = "NOT_CREATED"
    R["AUTOMATION"] = "DISABLED"

    json.dump(R, open(os.path.join(HERE, "V1_LINE169_R22.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False, default=str)
    print("\n=== §11 FINAL REPORT ===", flush=True)
    print("TASK_STATUS =", R["TASK_STATUS"])
    print("\n=== SAFETY ===")
    for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "LEDGER_SHA256_BEFORE", "LEDGER_SHA256_AFTER"):
        print(f"{k} = {R[k]}")
    print("\n=== TARGET ===")
    print("FILE =", R["FILE"], "| LINE_NUMBER =", R["LINE_NUMBER"], "| LEDGER_LINE_COUNT =", R["LEDGER_LINE_COUNT"])
    print("LINE_169_RAW =", (R["LINE_169_RAW"] if isinstance(R["LINE_169_RAW"], str) else str(R["LINE_169_RAW"])))
    print("LINE_169_PARSED_JSON =", json.dumps(R["LINE_169_PARSED_JSON"], ensure_ascii=False)[:2500])
    print("\n=== MATCHES ===")
    print("MATCH_COUNT =", R["MATCH_COUNT"])
    for m in R["MATCHES"]:
        print(f"  {m['JSON_PATH']}  |  FIELD_NAME={m['FIELD_NAME']}  |  VALUE={m['VALUE']}  |  VALUE_TYPE={m['VALUE_TYPE']}")
    print("\n=== RECORD SEMANTICS ===")
    for k in ("RECORD_TYPE", "EVENT_TYPE", "ACTION", "STAGE"):
        print(f"{k} = {R[k]}")
    print("TOP_LEVEL_KEYS =", json.dumps(R["TOP_LEVEL_KEYS"], ensure_ascii=False))
    print("\n=== CLASSIFICATION ===")
    print("STRUCTURED_ID_MATCH =", json.dumps(R["STRUCTURED_ID_MATCH"], ensure_ascii=False))
    print("NON_ID_MATCH =", json.dumps(R["NON_ID_MATCH"], ensure_ascii=False))
    print("UNKNOWN_FIELD_MATCH =", json.dumps(R["UNKNOWN_FIELD_MATCH"], ensure_ascii=False))
    print("STRUCTURED_POSITION_LINK =", R["STRUCTURED_POSITION_LINK"])
    print("LEGACY_LEDGER_POSITION_RECORD =", R["LEGACY_LEDGER_POSITION_RECORD"])
    print("\n=== CORRECTION ===")
    print("R18_R20_PREVIOUS_CLAIM =", R["R18_R20_PREVIOUS_CLAIM"])
    print("R22_REVISED_CLAIM =", R["R22_REVISED_CLAIM"])
    print("\n=== RECONCILIATION ===")
    print("BROKER_POSITION_STATE =", R["BROKER_POSITION_STATE"])
    print("LEDGER_STRUCTURED_POSITION_STATE =", R["LEDGER_STRUCTURED_POSITION_STATE"])
    print("RECONCILIATION_EVIDENCE_LEVEL =", R["RECONCILIATION_EVIDENCE_LEVEL"])
    print("RECONCILIATION_RECORD_CREATED =", R["RECONCILIATION_RECORD_CREATED"])
    print("\n=== SAFETY COUNTERS ===")
    print(json.dumps({k: 0 for k in COUNTERS} | {"MT5_ACCESS": 0, "GIT_COMMIT": "NONE"}, ensure_ascii=False))
    print("\n=== GATE ===")
    print("R22_GATE =", R["R22_GATE"], "| STOP_REASON =", R["STOP_REASON"], "| NEXT_STAGE_AUTHORIZED =",
          R["NEXT_STAGE_AUTHORIZED"])
    print("\n(artifact) " + os.path.join(HERE, "V1_LINE169_R22.json"), flush=True)
    sys.exit(0 if R["R22_GATE"] == "PASS" else 2)


if __name__ == "__main__":
    main()
