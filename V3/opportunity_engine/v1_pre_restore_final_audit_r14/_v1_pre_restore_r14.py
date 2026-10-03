# -*- coding: utf-8 -*-
"""V1_PRE_RESTORE_FINAL_SAFETY_AUDIT_R14 — READ-ONLY.

Single objective automation: cd47547e-ae38-4b36-a585-8b041ee826bb (hermes-trader-m15-cycle).
Forbidden and NOT executed: ENGINE_RESTORE, V1_STOP/RESTART/KILL, AUTOMATION_TRIGGER/RUN/UPDATE/ENABLE/
DISABLE/DELETE, MT5_ACCESS (account_info/terminal_info/positions_get/orders_get), ORDER_SEND, POSITION_CLOSE,
SOURCE_WRITE, CONFIG_WRITE, GIT_COMMIT, run-id chasing, full .openclaw scan, waiting/triggering M15.
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
R13 = os.path.join(ENGINE_DIR, "v1_forensic_runid_r13", "V1_FORENSIC_AND_RUNID_R13.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
ENGINE = os.path.join(V1, "engine.py")
BASELINE = os.path.join(AIQ, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
BACKUP = os.path.join(ENGINE_DIR, "m01_v1_engine_baseline_restore_r1", "pre_restore_engine.py")
ANOM = "e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
TARGET_KEYS = ("id", "name", "enabled", "status", "lastrunatms", "lastrunstatus", "nextrunatms",
                "lastdeliverystatus", "lastdelivered", "state", "schedule", "sessiontarget", "agentid",
                "updatedatms", "owner", "wakeMode")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
STOPS = []


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


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def dig(obj):
    """recursively collect leaf fields whose normalized key is in TARGET_KEYS"""
    out = {}

    def w(x, path=""):
        if isinstance(x, dict):
            for k, v in x.items():
                if norm(k) in TARGET_KEYS and not isinstance(v, (dict, list)):
                    out.setdefault(norm(k), {"value": v, "keypath": path + "/" + str(k)})
                w(v, path + "/" + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                w(v, path + "[%d]" % i)
    w(obj)
    return out


def ts_iso(v):
    try:
        n = int(v)
        if n > 10_000_000_000:
            return datetime.fromtimestamp(n / 1000.0, timezone.utc).isoformat()
        return datetime.fromtimestamp(n, timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return str(v)


def main():
    os.makedirs(HERE, exist_ok=True)
    O["TASK_STATUS"] = "V1_PRE_RESTORE_FINAL_SAFETY_AUDIT_COMPLETE"
    O["AUDIT_START_UTC"] = datetime.now(timezone.utc).isoformat()
    eng_sha_before = sha(ENGINE)

    # ---------------- §四/§五 automation current state ----------------
    out = run([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    doc = None
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    if m:
        try:
            doc = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            doc = None
    f = dig(doc) if doc is not None else {}
    O["AUTOMATION_RAW_JSON"] = json.dumps(doc, ensure_ascii=False)[:2500] if doc is not None else "NOT_READ"
    g = lambda k: (f.get(k, {}).get("value", "UNKNOWN"))
    O["AUTOMATION_ID"] = str(g("id")) if norm(g("id")) != "unknown" else AID
    O["AUTOMATION_NAME"] = g("name")
    O["AUTOMATION_ENABLED"] = g("enabled")
    O["AUTOMATION_STATUS"] = g("status")
    O["AUTOMATION_STATE_FIELD"] = g("state")
    O["LAST_RUN_AT"] = ts_iso(g("lastrunatms")) if norm(g("lastrunatms")) != "unknown" else "UNKNOWN"
    O["LAST_RUN_STATUS"] = g("lastrunstatus")
    O["NEXT_RUN_AT"] = ts_iso(g("nextrunatms")) if norm(g("nextrunatms")) != "unknown" else "UNKNOWN"
    O["LAST_DELIVERY_STATUS"] = g("lastdeliverystatus")
    sch = g("schedule")
    O["SCHEDULE"] = json.dumps(sch, ensure_ascii=False)[:200] if isinstance(sch, (dict, list)) else sch
    O["TIMEZONE"] = "UNKNOWN"
    if isinstance(sch, dict):
        for k, v in sch.items():
            if norm(k) in ("tz", "timezone"):
                O["TIMEZONE"] = v
    O["SESSION_TARGET"] = g("sessiontarget")
    O["AGENT_ID"] = g("agentid")
    O["AUTOMATION_UPDATED_AT"] = ts_iso(g("updatedatms")) if norm(g("updatedatms")) != "unknown" else "UNKNOWN"
    O["FIELDS_READ"] = {k: f[k]["keypath"] for k in f}
    print("§4/5 automation:", json.dumps({k: O[k] for k in ("AUTOMATION_ID", "AUTOMATION_NAME", "AUTOMATION_ENABLED",
                                                             "AUTOMATION_STATUS", "LAST_RUN_AT", "LAST_RUN_STATUS",
                                                             "NEXT_RUN_AT", "SCHEDULE", "SESSION_TARGET", "AGENT_ID")},
                                            ensure_ascii=False), flush=True)

    # ---------------- §六 automation state judgement ----------------
    en = str(O["AUTOMATION_ENABLED"]).lower()
    blob = " ".join(str(O[k]).lower() for k in ("AUTOMATION_STATUS", "LAST_RUN_STATUS", "AUTOMATION_STATE_FIELD"))
    bad = any(x in blob for x in ("error", "failed", "stuck", "disabled", "abort", "crash"))
    if en == "true" and not bad and O["AUTOMATION_ENABLED"] != "UNKNOWN":
        O["AUTOMATION_STATE"] = "NORMAL_OR_NOT_OBVIOUSLY_ABNORMAL"
    elif en == "false" or bad:
        O["AUTOMATION_STATE"] = "ANOMALY"
        STOPS.append("AUTOMATION_STATE_ANOMALY")
    else:
        O["AUTOMATION_STATE"] = "UNKNOWN"
        if O["AUTOMATION_ENABLED"] == "UNKNOWN":
            STOPS.append("AUTOMATION_STATE_UNKNOWN_UNCONFIRMED")
    print("§6 AUTOMATION_STATE =", O["AUTOMATION_STATE"], flush=True)

    # ---------------- §七 engine.py ----------------
    h = sha(ENGINE)
    if os.path.exists(ENGINE):
        st = os.stat(ENGINE)
        O["ENGINE_PATH"] = os.path.relpath(ENGINE, AIQ).replace("\\", "/")
        O["ENGINE_MTIME"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
        O["ENGINE_SIZE"] = st.st_size
    else:
        O["ENGINE_PATH"] = os.path.relpath(ENGINE, AIQ).replace("\\", "/")
        O["ENGINE_MTIME"] = O["ENGINE_SIZE"] = "MISSING"
    O["ENGINE_SHA256"] = h
    O["ENGINE_EXPECTED_CURRENT_STATE"] = ("KNOWN_ANOMALOUS" if h == ANOM else ("MV_R1_BASELINE" if h == BASE else "OTHER"))
    O["CURRENT_ENGINE_HASH_MATCH"] = "KNOWN_ANOMALOUS" if h == ANOM else "OTHER"
    O["BASELINE_HASH_MATCH"] = "NO" if h != BASE else "YES"
    if h not in (ANOM, BASE):
        STOPS.append("ENGINE_HASH_UNEXPECTED")
    print("§7 engine:", json.dumps({k: O[k] for k in ("ENGINE_MTIME", "ENGINE_SIZE", "ENGINE_SHA256",
                                                        "ENGINE_EXPECTED_CURRENT_STATE")}, ensure_ascii=False), flush=True)

    # ---------------- §八 baseline artifact ----------------
    if os.path.exists(BASELINE):
        st = os.stat(BASELINE)
        O["BASELINE_ARTIFACT_EXISTS"] = "YES"
        O["BASELINE_ARTIFACT_PATH"] = os.path.relpath(BASELINE, AIQ).replace("\\", "/")
        O["BASELINE_ARTIFACT_SIZE"] = st.st_size
        O["BASELINE_SHA256"] = sha(BASELINE)
        O["BASELINE_HASH_MATCH"] = "PASS" if O["BASELINE_SHA256"] == BASE else "FAIL"
    else:
        O["BASELINE_ARTIFACT_EXISTS"] = "NO"
        O["BASELINE_ARTIFACT_PATH"] = os.path.relpath(BASELINE, AIQ).replace("\\", "/")
        O["BASELINE_ARTIFACT_SIZE"] = O["BASELINE_SHA256"] = "MISSING"
        O["BASELINE_HASH_MATCH"] = "FAIL"
    if O["BASELINE_HASH_MATCH"] != "PASS":
        STOPS.append("BASELINE_INTEGRITY_FAILURE")
    print("§8 baseline:", json.dumps({k: O[k] for k in ("BASELINE_ARTIFACT_EXISTS", "BASELINE_ARTIFACT_SIZE",
                                                          "BASELINE_SHA256", "BASELINE_HASH_MATCH")}, ensure_ascii=False), flush=True)

    # ---------------- §九 pre-restore backup ----------------
    if os.path.exists(BACKUP):
        st = os.stat(BACKUP)
        O["PRE_RESTORE_BACKUP_EXISTS"] = "YES"
        O["PRE_RESTORE_BACKUP_PATH"] = os.path.relpath(BACKUP, AIQ).replace("\\", "/")
        O["PRE_RESTORE_BACKUP_SIZE"] = st.st_size
        O["PRE_RESTORE_BACKUP_SHA256"] = sha(BACKUP)
        O["PRE_RESTORE_BACKUP_HASH_MATCH"] = "PASS" if O["PRE_RESTORE_BACKUP_SHA256"] == ANOM else "FAIL"
    else:
        O["PRE_RESTORE_BACKUP_EXISTS"] = "NO"
        O["PRE_RESTORE_BACKUP_PATH"] = os.path.relpath(BACKUP, AIQ).replace("\\", "/")
        O["PRE_RESTORE_BACKUP_SIZE"] = O["PRE_RESTORE_BACKUP_SHA256"] = "MISSING"
        O["PRE_RESTORE_BACKUP_HASH_MATCH"] = "FAIL"
    if O["PRE_RESTORE_BACKUP_HASH_MATCH"] != "PASS":
        STOPS.append("PRE_RESTORE_BACKUP_INTEGRITY_FAILURE")
    print("§9 backup:", json.dumps({k: O[k] for k in ("PRE_RESTORE_BACKUP_EXISTS", "PRE_RESTORE_BACKUP_SIZE",
                                                        "PRE_RESTORE_BACKUP_SHA256",
                                                        "PRE_RESTORE_BACKUP_HASH_MATCH")}, ensure_ascii=False), flush=True)

    # ---------------- §十 isolation (since R13) ----------------
    r13 = json.load(open(R13, encoding="utf-8")) if os.path.exists(R13) else {}
    t13 = r13.get("ts_utc") or r13.get("CURRENT_TIME_UTC") or "2026-09-25T15:30:46+00:00"
    try:
        lim = datetime.fromisoformat(str(t13)).timestamp()
    except Exception:  # noqa: BLE001
        lim = datetime.now(timezone.utc).timestamp()
    O["R13_REFERENCE_TIME"] = str(t13)

    def newer(root):
        out = []
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for fn in fs:
                if fn.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r_, fn)
                    try:
                        if os.path.getmtime(p) > lim:
                            out.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                    except OSError:
                        continue
        return out
    v1c = newer(V1)
    v2c = newer(V2)
    O["V1_CHANGED_SINCE_R13"] = v1c
    O["V2_CHANGED_SINCE_R13"] = v2c
    O["V1_SOURCE_CONFIG_MODIFIED_SINCE_R13"] = "NO" if not v1c else "YES"
    O["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    O["V3_M01_EVENT_HASH"] = v3["M01_event"]
    O["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    O["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    O["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    v3ok = all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT)
    O["V3_RESEARCH_MODIFIED"] = "NO" if v3ok else "YES"
    if not v3ok:
        STOPS.append("V3_INTEGRITY_CHANGE")
    if v1c:
        STOPS.append("V1_SOURCE_CONFIG_CHANGED")
    if v2c:
        STOPS.append("V2_CHANGED_UNEXPECTEDLY")
    print("§10 isolation:", json.dumps({"V1": O["V1_SOURCE_CONFIG_MODIFIED_SINCE_R13"],
                                          "V2": O["V2_SOURCE_CONFIG_MODIFIED"],
                                          "V3": O["V3_RESEARCH_MODIFIED"]}, ensure_ascii=False), flush=True)

    # ---------------- §十三 final gate ----------------
    eng_sha_after = sha(ENGINE)
    O["ENGINE_MODIFIED_DURING_AUDIT"] = "NO" if (eng_sha_before == eng_sha_after) else "YES"
    if O["ENGINE_MODIFIED_DURING_AUDIT"] == "YES":
        STOPS.append("ENGINE_MODIFIED_DURING_AUDIT")
    conds = {
        "1_automation_no_obvious_anomaly": O["AUTOMATION_STATE"] == "NORMAL_OR_NOT_OBVIOUSLY_ABNORMAL",
        "2_engine_hash_known_anomalous": O["ENGINE_EXPECTED_CURRENT_STATE"] == "KNOWN_ANOMALOUS",
        "3_baseline_artifact_exists": O["BASELINE_ARTIFACT_EXISTS"] == "YES",
        "4_baseline_hash_ok": O["BASELINE_HASH_MATCH"] == "PASS",
        "5_backup_exists": O["PRE_RESTORE_BACKUP_EXISTS"] == "YES",
        "6_backup_hash_ok": O["PRE_RESTORE_BACKUP_HASH_MATCH"] == "PASS",
        "7_v1_no_new_source_config": O["V1_SOURCE_CONFIG_MODIFIED_SINCE_R13"] == "NO",
        "8_v2_no_anomaly": O["V2_SOURCE_CONFIG_MODIFIED"] == "NO",
        "9_v3_all_hashes_hold": O["V3_RESEARCH_MODIFIED"] == "NO",
        "10_no_forbidden_op_executed": True}
    O["GATE_CONDITIONS"] = conds
    O["PRE_RESTORE_GATE"] = "PASS" if all(conds.values()) and not STOPS else "FAIL"
    O["STOP_REASON"] = "NONE" if O["PRE_RESTORE_GATE"] == "PASS" else ",".join(sorted(set(STOPS)))
    O["NEXT_STAGE_AUTHORIZED"] = "NO"
    O["ORDER_SEND"] = 0
    O["MT5_ACCESS"] = 0
    O["AUTOMATION_WRITE"] = 0
    O["SOURCE_WRITE"] = 0
    O["CONFIG_WRITE"] = 0
    O["GIT_COMMIT"] = "NONE"
    O["ENGINE_RESTORE"] = "FORBIDDEN"
    O["V1_STOP"] = "FORBIDDEN"
    O["V1_RESTART"] = "FORBIDDEN"
    O["V1_KILL"] = "FORBIDDEN"
    O["AUTOMATION_RUN"] = "FORBIDDEN"
    O["AUDIT_END_UTC"] = datetime.now(timezone.utc).isoformat()
    json.dump(O, open(os.path.join(HERE, "V1_PRE_RESTORE_FINAL_SAFETY_AUDIT_R14.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)

    rep = {"TASK_STATUS": O["TASK_STATUS"], "AUTOMATION_ID": O["AUTOMATION_ID"], "AUTOMATION_NAME": O["AUTOMATION_NAME"],
            "AUTOMATION_ENABLED": O["AUTOMATION_ENABLED"], "AUTOMATION_STATUS": O["AUTOMATION_STATUS"],
            "AUTOMATION_STATE": O["AUTOMATION_STATE"], "LAST_RUN_AT": O["LAST_RUN_AT"],
            "LAST_RUN_STATUS": O["LAST_RUN_STATUS"], "NEXT_RUN_AT": O["NEXT_RUN_AT"],
            "LAST_DELIVERY_STATUS": O["LAST_DELIVERY_STATUS"], "SCHEDULE": O["SCHEDULE"], "TIMEZONE": O["TIMEZONE"],
            "SESSION_TARGET": O["SESSION_TARGET"], "AGENT_ID": O["AGENT_ID"],
            "AUTOMATION_UPDATED_AT": O["AUTOMATION_UPDATED_AT"],
            "ENGINE_PATH": O["ENGINE_PATH"], "ENGINE_MTIME": O["ENGINE_MTIME"], "ENGINE_SIZE": O["ENGINE_SIZE"],
            "ENGINE_SHA256": O["ENGINE_SHA256"], "ENGINE_EXPECTED_CURRENT_STATE": O["ENGINE_EXPECTED_CURRENT_STATE"],
            "ENGINE_MODIFIED_DURING_AUDIT": O["ENGINE_MODIFIED_DURING_AUDIT"],
            "BASELINE_ARTIFACT_EXISTS": O["BASELINE_ARTIFACT_EXISTS"], "BASELINE_SHA256": O["BASELINE_SHA256"],
            "BASELINE_HASH_MATCH": O["BASELINE_HASH_MATCH"],
            "PRE_RESTORE_BACKUP_EXISTS": O["PRE_RESTORE_BACKUP_EXISTS"],
            "PRE_RESTORE_BACKUP_SHA256": O["PRE_RESTORE_BACKUP_SHA256"],
            "PRE_RESTORE_BACKUP_HASH_MATCH": O["PRE_RESTORE_BACKUP_HASH_MATCH"],
            "V1_SOURCE_CONFIG_MODIFIED_SINCE_R13": O["V1_SOURCE_CONFIG_MODIFIED_SINCE_R13"],
            "V2_SOURCE_CONFIG_MODIFIED": O["V2_SOURCE_CONFIG_MODIFIED"],
            "V3_RESEARCH_MODIFIED": O["V3_RESEARCH_MODIFIED"],
            "V3_M01_EVENT_HASH": O["V3_M01_EVENT_HASH"], "V3_R1_LEDGER_HASH": O["V3_R1_LEDGER_HASH"],
            "V3_M01_AUDIT_HASH": O["V3_M01_AUDIT_HASH"], "V3_R2_CANONICAL_HASH": O["V3_R2_CANONICAL_HASH"],
            "ORDER_SEND": 0, "MT5_ACCESS": 0, "AUTOMATION_WRITE": 0, "SOURCE_WRITE": 0, "CONFIG_WRITE": 0,
            "GIT_COMMIT": "NONE", "GATE_CONDITIONS": conds, "PRE_RESTORE_GATE": O["PRE_RESTORE_GATE"],
            "STOP_REASON": O["STOP_REASON"], "NEXT_STAGE_AUTHORIZED": "NO"}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_PRE_RESTORE_FINAL_SAFETY_AUDIT_R14.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    print("\n=== §16 FINAL REPORT ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3400], flush=True)


if __name__ == "__main__":
    main()
