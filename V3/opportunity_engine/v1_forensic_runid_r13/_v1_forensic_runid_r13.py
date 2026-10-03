# -*- coding: utf-8 -*-
"""V1_FORENSIC_AND_RUNID_R13 — READ-ONLY. A) classify every V1 *.py/*.yaml/*.yml changed after
2026-09-25T15:30:46Z (full list + engine.py identity); B) decide whether run id 88f2d297-... belongs to the
15:32Z hermes-trader-m15-cycle run, via official read-only interfaces only.

Forbidden (not executed anywhere): ENGINE_RESTORE, V1_STOP/RESTART/KILL, AUTOMATION_RUN/TRIGGER/ENABLE/
DISABLE/UPDATE/DELETE, MT5_ACCESS (any), SOURCE_WRITE, CONFIG_WRITE, GIT_COMMIT, FULL_MACHINE_SCAN,
FULL_OPENCLAW_SCAN.
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
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
RUNID = "88f2d297-b883-46d3-aec4-90d03b918587"
THRESH = "2026-09-25T15:30:46"
ENGINE_PATH = os.path.join(V1, "engine.py")
ANOM_SHA = "e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe"
BASE_SHA = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
RUNTIME_SEGS = ["run_state/", "runtime/", "tmp/", "cache/", "memory/reviews/", "observations/",
                 "state/decision_contexts/"]
MUT = ("enable", "disable", "run", "trigger", "update", "delete", "create", "set", "edit", "add", "start", "stop")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


def run(args, t=60):
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


def classify(rel):
    r = rel.replace("\\", "/").lower()
    for s in RUNTIME_SEGS:
        if s in r:
            if r.endswith((".py",)):
                return "RUNTIME_TEMP"
            if r.endswith((".yaml", ".yml")):
                return "RUNTIME"
            return "RUNTIME"
    if r.endswith((".py",)):
        return "SOURCE"
    if r.endswith((".yaml", ".yml")):
        return "CONFIG"
    return "UNKNOWN"


def main():
    os.makedirs(HERE, exist_ok=True)
    O["TASK_STATUS"] = "V1_FORENSIC_AND_RUNID_R13_COMPLETE"
    O["OBSERVATION_START"] = THRESH + "Z"
    O["CURRENT_TIME_UTC"] = datetime.now(timezone.utc).isoformat()
    try:
        lim = datetime.fromisoformat(THRESH).replace(tzinfo=timezone.utc).timestamp()
    except Exception:  # noqa: BLE001
        lim = datetime.now(timezone.utc).timestamp()

    # ---------------- PART A ----------------
    hits = []
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith((".py", ".yaml", ".yml")):
                continue
            p = os.path.join(r_, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_mtime > lim:
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                hits.append({"path": rel, "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                              "size": st.st_size, "class": classify(rel)})
    hits.sort(key=lambda x: x["mtime_utc"])
    O["V1_MODIFIED_FILES_COUNT"] = len(hits)
    O["V1_MODIFIED_FILES"] = hits
    classes = {}
    for h in hits:
        classes[h["class"]] = classes.get(h["class"], 0) + 1
    O["V1_MODIFIED_CLASS_COUNTS"] = classes

    # engine.py identity (read-only)
    eng = {}
    if os.path.exists(ENGINE_PATH):
        st = os.stat(ENGINE_PATH)
        h = sha(ENGINE_PATH)
        eng = {"ENGINE_PATH": os.path.relpath(ENGINE_PATH, AIQ).replace("\\", "/"),
                "ENGINE_MTIME": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "ENGINE_SIZE": st.st_size, "ENGINE_SHA256": h,
                "ENGINE_CLASS": classify(os.path.relpath(ENGINE_PATH, AIQ).replace("\\", "/")),
                "ENGINE_MTIME_AFTER_THRESHOLD": st.st_mtime > lim,
                "matches_anomalous_e308": (h == ANOM_SHA), "matches_mv_r1_baseline_7d95": (h == BASE_SHA)}
        eng["ENGINE_HASH_UNCHANGED"] = "YES" if h == ANOM_SHA else "NO"
        eng["ENGINE_HASH_CHANGED"] = "NO" if h == ANOM_SHA else "YES"
    else:
        eng = {"ENGINE_PATH": os.path.relpath(ENGINE_PATH, AIQ).replace("\\", "/"), "ENGINE_MTIME": "MISSING",
                "ENGINE_SIZE": "MISSING", "ENGINE_SHA256": "MISSING", "ENGINE_CLASS": "UNKNOWN",
                "ENGINE_HASH_UNCHANGED": "UNKNOWN", "ENGINE_HASH_CHANGED": "UNKNOWN"}
    O["ENGINE_IDENTITY"] = eng
    print("PART A hits:", len(hits), classes, flush=True)
    for h in hits[:20]:
        print("   ", h["class"], h["path"], h["mtime_utc"], h["size"], flush=True)
    print("ENGINE:", json.dumps(eng, ensure_ascii=False), flush=True)

    # verdict per section 7
    if eng.get("ENGINE_HASH_CHANGED") == "YES" or eng.get("ENGINE_MTIME_AFTER_THRESHOLD") is True:
        O["V1_SOURCE_CONFIG_MODIFIED"] = "YES"
        O["R12_FALSE_POSITIVE_CAUSE"] = "REAL_SOURCE_CHANGE"
        O["STOP_TRIGGER"] = "ENGINE_PY_CHANGED"
    elif hits and all(h["class"] in ("RUNTIME_TEMP", "RUNTIME") for h in hits):
        O["V1_SOURCE_CONFIG_MODIFIED"] = "NO"
        O["R12_FALSE_POSITIVE_CAUSE"] = "RUNTIME_GENERATED_FILES"
        O["STOP_TRIGGER"] = "NONE"
    elif not hits:
        O["V1_SOURCE_CONFIG_MODIFIED"] = "NO"
        O["R12_FALSE_POSITIVE_CAUSE"] = "RUNTIME_GENERATED_FILES"
        O["STOP_TRIGGER"] = "NONE"
    else:
        O["V1_SOURCE_CONFIG_MODIFIED"] = "UNKNOWN"
        O["R12_FALSE_POSITIVE_CAUSE"] = "UNKNOWN"
        O["STOP_TRIGGER"] = "NONE"
    print("A verdict:", O["V1_SOURCE_CONFIG_MODIFIED"], O["R12_FALSE_POSITIVE_CAUSE"], flush=True)

    # ---------------- PART B: run id identity (read-only only) ----------------
    rb, rb_cmd = None, None
    FORMS = [["cron", "runs", AID, "--json"], ["cron", "runs", "--json", AID], ["cron", "runs", "--json"]]
    for form in FORMS:
        if any(v in MUT for v in form):
            continue
        if not (os.path.exists(NODE) and os.path.exists(CLI)):
            break
        out = run([NODE, CLI] + form, 60)
        m = re.search(r"(\{.*\}|\[.*\])", out, re.S)
        if not m:
            continue
        try:
            doc = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            continue
        rb, rb_cmd = doc, " ".join(form)
        break
    O["RUN_LOOKUP_COMMAND"] = rb_cmd or "NONE"
    recs = []
    def collect(x):
        if isinstance(x, list):
            for v in x:
                collect(v)
        elif isinstance(x, dict):
            if any(k.lower() in ("id", "runid", "run_id", "executionid") for k in x):
                recs.append(x)
            for v in x.values():
                collect(v)
    if rb is not None:
        collect(rb)
    target = next((r for r in recs if RUNID in json.dumps(r, ensure_ascii=False)), None)
    flat = {}
    if target:
        for k, v in target.items():
            if not isinstance(v, (dict, list)):
                flat[str(k)] = v
    O["RUN_RECORD_FOUND"] = "YES" if target else "NO"
    O["RUN_RECORD_FIELDS"] = flat
    O["RUN_RECORD_RAW"] = json.dumps(target, ensure_ascii=False)[:1200] if target else "NOT_FOUND"
    def pick(*pats):
        for k, v in flat.items():
            for p in pats:
                if re.search(p, k, re.I):
                    return v
        return "UNKNOWN"
    O["RUN_ID"] = RUNID
    O["RUN_AUTOMATION_ID_FIELD"] = pick(r"automation[_]?id", r"cron[_]?id", r"^id$")
    O["RUN_START"] = pick(r"started[_]?at", r"created[_]?at", r"scheduled[_]?at", r"start")
    O["RUN_END"] = pick(r"finished[_]?at", r"ended[_]?at", r"completed[_]?at")
    O["RUN_STATUS"] = pick(r"status", r"state")
    O["RUN_SESSION_ID"] = pick(r"session[_]?id", r"conversation[_]?id")
    O["RUN_SCHEDULED_AT"] = pick(r"scheduled[_]?at", r"nextrun")
    # decisions (direct evidence only)
    aid_ok = str(O["RUN_AUTOMATION_ID_FIELD"]) == AID
    st = str(O["RUN_START"])
    t_ok = bool(re.match(r"2026-09-25T15:3[2-9]", st)) or ("1790350320000" in st) or ("15:32" in st)
    O["RUN_ID_MATCHES_AUTOMATION"] = "YES" if aid_ok else ("UNKNOWN" if target is None else "NO")
    O["RUN_ID_MATCHES_15_32Z"] = "YES" if t_ok else "UNKNOWN"
    # post-state-package stage (only if the run matches)
    if O["RUN_ID_MATCHES_15_32Z"] == "YES":
        blob = json.dumps(target, ensure_ascii=False).lower()
        has_sp = "state_package" in blob
        has_cont = any(k in blob for k in ("agentturn", "continuation", "message", "tool"))
        has_eng = ("engine.py" in blob) or ("trader_v1" in blob)
        has_decision = ("decision" in blob) or ("plan" in blob) or ("ledger" in blob)
        has_mc = ("market_closed" in blob) or ('"armed": false' in blob) or ("armed=false" in blob)
        O["POST_STATE_PACKAGE_STAGE"] = "CONFIRMED" if (has_sp and has_eng) else "NOT_OBSERVED"
        O["AGENTTURN_CONTINUATION"] = "CONFIRMED" if has_cont else "NOT_CONFIRMED"
        O["TRADING_HOURS_GATE_RESULT"] = "MARKET_CLOSED" if has_mc else "NOT_OBSERVED"
        O["ENGINE_EXECUTION"] = "CONFIRMED" if has_eng else "NOT_CONFIRMED"
        O["DECISION_OR_PLAN"] = "CONFIRMED" if has_decision else "NOT_OBSERVED"
        O["FULL_M15_CYCLE"] = "CONFIRMED" if (O["POST_STATE_PACKAGE_STAGE"] == "CONFIRMED"
                                                 and O["DECISION_OR_PLAN"] == "CONFIRMED") else (
            "PARTIAL" if O["POST_STATE_PACKAGE_STAGE"] == "CONFIRMED" else "NOT_CONFIRMED")
        O["RUN_DETAIL_MARKERS"] = {"state_package": has_sp, "agentTurn_or_message": has_cont,
                                     "trader_v1_or_engine": has_eng, "decision_or_plan_or_ledger": has_decision,
                                     "market_closed_or_disarmed": has_mc}
    else:
        O["POST_STATE_PACKAGE_STAGE"] = "UNKNOWN"
        O["AGENTTURN_CONTINUATION"] = "UNKNOWN"
        O["TRADING_HOURS_GATE_RESULT"] = "NOT_OBSERVED"
        O["ENGINE_EXECUTION"] = "UNKNOWN"
        O["DECISION_OR_PLAN"] = "UNKNOWN"
        O["FULL_M15_CYCLE"] = "NOT_CONFIRMED"
        O["RUN_DETAIL_MARKERS"] = "SECTION_13_STOP: run id not tied to 15:32Z; B stopped here"
    print("PART B:", json.dumps({"found": O["RUN_RECORD_FOUND"], "cmd": rb_cmd, "fields": flat,
                                   "match_automation": O["RUN_ID_MATCHES_AUTOMATION"],
                                   "match_1532": O["RUN_ID_MATCHES_15_32Z"]}, ensure_ascii=False)[:900], flush=True)

    # ---------------- PART C: protection ----------------
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3ok = ((v3["M01_event"] or "").startswith("ca44fd2c") and (v3["R1_ledger"] or "").startswith("d9cd6775")
             and (v3["M01_audit"] or "").startswith("a3bee537") and (v3["R2_canonical"] or "").startswith("20913b98"))
    def newer(root):
        out = []
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r_, f)
                    try:
                        if os.path.getmtime(p) > lim:
                            out.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                    except OSError:
                        continue
        return out
    O["V2_CHANGED_FILES"] = newer(V2)
    O["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not O["V2_CHANGED_FILES"] else "YES"
    O["V3_RESEARCH_MODIFIED"] = "NO" if v3ok else "YES"
    O["V3_HASHES"] = v3
    O["ORDER_SEND"] = 0
    O["COMMIT"] = "NONE"
    O["ENGINE_RESTORE"] = "FORBIDDEN"
    O["V1_STOP"] = "FORBIDDEN"
    O["V1_RESTART"] = "FORBIDDEN"
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"
    O["MT5_ACCESS"] = "FORBIDDEN_NOT_USED"
    O["OPEN_POSITIONS_HISTORICAL"] = 1
    O["PENDING_ORDERS_HISTORICAL"] = 0

    rep = {"TASK_STATUS": O["TASK_STATUS"], "OBSERVATION_START": O["OBSERVATION_START"],
            "V1_MODIFIED_FILES_COUNT": O["V1_MODIFIED_FILES_COUNT"], "V1_MODIFIED_FILES": O["V1_MODIFIED_FILES"],
            "V1_MODIFIED_CLASS_COUNTS": O["V1_MODIFIED_CLASS_COUNTS"], "ENGINE_IDENTITY": O["ENGINE_IDENTITY"],
            "V1_SOURCE_CONFIG_MODIFIED": O["V1_SOURCE_CONFIG_MODIFIED"],
            "R12_FALSE_POSITIVE_CAUSE": O["R12_FALSE_POSITIVE_CAUSE"], "STOP_TRIGGER": O["STOP_TRIGGER"],
            "RUN_ID": RUNID, "RUN_LOOKUP_COMMAND": O["RUN_LOOKUP_COMMAND"], "RUN_RECORD_FOUND": O["RUN_RECORD_FOUND"],
            "RUN_RECORD_FIELDS": O["RUN_RECORD_FIELDS"], "RUN_ID_MATCHES_AUTOMATION": O["RUN_ID_MATCHES_AUTOMATION"],
            "RUN_ID_MATCHES_15_32Z": O["RUN_ID_MATCHES_15_32Z"], "RUN_START": O["RUN_START"],
            "RUN_END": O["RUN_END"], "RUN_STATUS": O["RUN_STATUS"], "RUN_SESSION_ID": O["RUN_SESSION_ID"],
            "POST_STATE_PACKAGE_STAGE": O["POST_STATE_PACKAGE_STAGE"],
            "AGENTTURN_CONTINUATION": O["AGENTTURN_CONTINUATION"],
            "TRADING_HOURS_GATE_RESULT": O["TRADING_HOURS_GATE_RESULT"], "ENGINE_EXECUTION": O["ENGINE_EXECUTION"],
            "DECISION_OR_PLAN": O["DECISION_OR_PLAN"], "FULL_M15_CYCLE": O["FULL_M15_CYCLE"],
            "RUN_DETAIL_MARKERS": O["RUN_DETAIL_MARKERS"],
            "V2_SOURCE_CONFIG_MODIFIED": O["V2_SOURCE_CONFIG_MODIFIED"], "V3_RESEARCH_MODIFIED": O["V3_RESEARCH_MODIFIED"],
            "V3_HASHES": O["V3_HASHES"], "ORDER_SEND": 0, "COMMIT": "NONE", "ENGINE_RESTORE": "FORBIDDEN",
            "V1_STOP": "FORBIDDEN", "V1_RESTART": "FORBIDDEN", "SAFETY_WINDOW": "NOT_PROVEN",
            "NEXT_STAGE_AUTHORIZED": "NO"}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_FORENSIC_AND_RUNID_R13.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §17 FINAL REPORT ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3400], flush=True)


if __name__ == "__main__":
    main()
