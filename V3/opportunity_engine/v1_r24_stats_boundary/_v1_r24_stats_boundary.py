# -*- coding: utf-8 -*-
"""R24 — statistics-boundary hard gate (READ-ONLY).

PROVEN requires ALL FOUR, each with direct code/artefact evidence:
  a) code creates a NEW run_id at run start (not inherited)
  b) code initialises statistics counters to zero for a new run
  c) an explicit per-run scope mechanism exists (namespace / path / schema field)
  d) no code path carries legacy counters forward
Otherwise NEW_RUN_STATS_BOUNDARY = NOT_PROVEN and TASK_STATUS = BLOCKED (no reset, no start, no automation).
Writes ONLY under research/v3_opportunity_engine/v1_r24_stats_boundary/.
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
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
V2 = os.path.join(RE, "hermes", "trader_v2")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
LEGACY_RUN = "V1_RUN_20260924_RESET_01"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
PATTERNS = {
    "STATS_FILE": r"statistics\.json",
    "RUN_META": r"RUN_META",
    "RUN_ID": r"run_id",
    "RUN_CREATE": r"(new_run|create_run|init_run|reset_run|start_run|RUN_TYPE|run_type)",
    "COUNTERS": r"(closed_trades|realized_pnl|wins|losses|trade_count)",
    "RESET": r"(?i)\breset\b",
    "SCOPE": r"(run_dir|run_namespace|run_scope|per_run|scope)",
}
R = {}
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME",
             "RESET", "NEW_RUN_CREATE")


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


def tree(x, path="$", depth=0):
    out = []
    if depth > 6:
        return out
    if isinstance(x, dict):
        for k, v in x.items():
            out.append((f"{path}.{k}", type(v).__name__, (v if not isinstance(v, (dict, list)) else None)))
            out += tree(v, f"{path}.{k}", depth + 1)
    elif isinstance(x, list):
        out.append((f"{path}[len={len(x)}]", "list", None))
        for i, v in enumerate(x[:3]):
            out += tree(v, f"{path}[{i}]", depth + 1)
    return out


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "RUNNING"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------- §5 pre-start freeze ----------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        d = {}
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = d.get("status", "UNKNOWN")
    R["AUTOMATION_SCHEDULE"] = json.dumps(d.get("schedule"), ensure_ascii=False)
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
    print("§5 freeze:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                        "LEDGER_SHA256", "STATISTICS_SHA256", "RUN_META_SHA256")},
                                       ensure_ascii=False), flush=True)
    if str(R["AUTOMATION_ENABLED"]).lower() != "false" or R["V1_ENGINE_PROCESS"] != "NOT_RUNNING" \
            or R["ENGINE_SHA256"] != BASE or R["LEDGER_SHA256"] != LEDGER_EXPECT:
        R["TASK_STATUS"] = "BLOCKED"
        R["STOP_REASON"] = "FREEZE_CONSTRAINT_CHANGED"
        return finish()

    # ---------- §3.1 statistics.json full structure ----------
    stats, raw_len = {}, 0
    if os.path.exists(STATS):
        txt = open(STATS, encoding="utf-8", errors="ignore").read()
        raw_len = len(txt)
        try:
            stats = json.loads(txt)
        except Exception:  # noqa: BLE001
            stats = {}
    R["STATISTICS_RAW_LENGTH"] = raw_len
    flat = tree(stats)
    R["STATISTICS_STRUCTURE"] = [{"path": p_, "type": t_, "value": v_} for p_, t_, v_ in flat]
    R["STATISTICS_TOP_KEYS"] = sorted(stats.keys()) if isinstance(stats, dict) else "NOT_DICT"
    numeric_paths = [p_ for p_, t_, v_ in flat if isinstance(v_, (int, float)) and not isinstance(v_, bool)]
    R["STATISTICS_NUMERIC_PATHS"] = numeric_paths[:60]
    counter_like = [p_ for p_ in numeric_paths if re.search(r"(?i)(pnl|profit|trade|win|loss|count|balance|equity)", p_)]
    R["STATISTICS_COUNTER_LIKE_PATHS"] = counter_like
    scope_marks = [p_ for p_, t_, v_ in flat if re.search(r"(?i)(run_id|run|start|scope|legacy)", str(p_))]
    R["STATISTICS_SCOPE_MARKERS"] = scope_marks
    R["STATISTICS_RUN_ID"] = stats.get("run_id", "ABSENT") if isinstance(stats, dict) else "ABSENT"
    print("§3.1 stats: keys=", str(R["STATISTICS_TOP_KEYS"])[:120], "| numeric_paths=", len(numeric_paths),
          "| counter_like=", counter_like[:6], flush=True)

    # ---------- §3.2/3.3 V1 code audit ----------
    code_files = []
    for r_, ds, fs in os.walk(V1):
        if "run_state" in r_.replace("\\", "/") or "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith(".py"):
                code_files.append(os.path.join(r_, f))
    hits = {k: [] for k in PATTERNS}
    for p in code_files:
        try:
            lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:  # noqa: BLE001
            continue
        rel = os.path.relpath(p, AIQ).replace("\\", "/")
        for i, ln in enumerate(lines):
            for name, pat in PATTERNS.items():
                if re.search(pat, ln):
                    hits[name].append({"file": rel, "line": i + 1, "text": ln.strip()[:180]})
    R["CODE_FILES_SCANNED"] = len(code_files)
    R["CODE_HITS"] = {k: v[:25] for k, v in hits.items()}
    R["CODE_HIT_COUNTS"] = {k: len(v) for k, v in hits.items()}
    print("§3.2/3.3 hits:", json.dumps(R["CODE_HIT_COUNTS"], ensure_ascii=False), flush=True)

    # ---------- §3.4/3.5 legacy-inheritance & new-run-init evidence ----------
    def find(regex, where="CODE_HITS"):
        out = []
        for k, v in hits.items():
            for h in v:
                if re.search(regex, h["text"], re.I):
                    out.append(h)
        return out
    creates_run = find(r"(new_run|create_run|init_run|reset_run|start_run|run_id\s*=|RUN_META)")
    zero_init = find(r"(realized_pnl|closed_trades|wins|losses|trade_count)\s*[:=]\s*(0|0\.0|\{\}|\[\])")
    scope_mech = find(r"(run_dir|run_namespace|run_scope|per_run|scope|f\".*run.*\")")
    carry = find(r"(load_existing|carry|inherit|previous_run|last_run|read_statistics|load_statistics)")
    R["EVID_new_run_creation"] = creates_run[:12]
    R["EVID_zero_init"] = zero_init[:12]
    R["EVID_scope_mechanism"] = scope_mech[:12]
    R["EVID_carry_forward_paths"] = carry[:12]
    print("§3.4/3.5:", json.dumps({"create": len(creates_run), "zero": len(zero_init), "scope": len(scope_mech),
                                     "carry": len(carry)}, ensure_ascii=False), flush=True)

    # ---------- §3/§4 PROVEN test ----------
    sub = {
        "a_new_run_id_created_by_code": "YES" if any(re.search(r"run_id\s*=", h["text"]) for h in creates_run) else "NO",
        "b_counters_zero_init_in_code": "YES" if zero_init else "NO",
        "c_explicit_per_run_scope_mechanism": "YES" if scope_mech else "NO",
        "d_no_carry_forward_path": "NO_PATH_FOUND" if not carry else "PATH_PRESENT",
    }
    R["PROVEN_SUBCONDITIONS"] = sub
    proven = (sub["a_new_run_id_created_by_code"] == "YES" and sub["b_counters_zero_init_in_code"] == "YES"
               and sub["c_explicit_per_run_scope_mechanism"] == "YES" and sub["d_no_carry_forward_path"] == "NO_PATH_FOUND")
    R["NEW_RUN_STATS_BOUNDARY"] = "PROVEN" if proven else "NOT_PROVEN"
    R["BOUNDARY_EVIDENCE_SUMMARY"] = {
        "statistics_file_is_single_fixed_path": os.path.exists(STATS),
        "statistics_has_run_id_field": R["STATISTICS_RUN_ID"] == LEGACY_RUN,
        "no_run_scoped_filename_or_namespace_found": "NO" if scope_mech else "YES",
        "no_zero_init_code_found": "NO" if zero_init else "YES",
        "carry_forward_path_found": "YES" if carry else "NO"}
    print("§4 boundary:", R["NEW_RUN_STATS_BOUNDARY"], json.dumps(sub, ensure_ascii=False), flush=True)

    # ---------- §6 legacy ledger immutability (read-only check) ----------
    R["OLD_LEDGER_IMMUTABLE"] = "YES" if sha(LEDGER) == LEDGER_EXPECT else "NO"
    R["OLD_LEDGER_MUTATION"] = 0 if R["OLD_LEDGER_IMMUTABLE"] == "YES" else 1

    # ---------- §13 engine integrity ----------
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-m", "py_compile", ENGINE],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        R["PY_COMPILE"] = "PASS" if pr.returncode == 0 else "FAIL"
    except Exception:  # noqa: BLE001
        R["PY_COMPILE"] = "FAIL"
    R["ENGINE_BASELINE"] = "PASS" if R["ENGINE_SHA256"] == BASE else "FAIL"

    # ---------- §23 isolation ----------
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_ISOLATION"] = "PASS" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "FAIL"
    lim = datetime.now(timezone.utc).timestamp() - 3600
    v2c = [os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
            for r_, _, fs in os.walk(V2) if "__pycache__" not in r_ for f in fs
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim]
    R["V2_ISOLATION"] = "PASS" if not v2c else "FAIL"
    R["V2_CHANGES_1H"] = v2c[:5]

    # ---------- §4 gate outcome ----------
    if not proven:
        R["TASK_STATUS"] = "BLOCKED"
        R["R24_GATE"] = "FAIL"
        R["STOP_REASON"] = "NEW_RUN_STATS_BOUNDARY_NOT_PROVEN"
        R["RESET"] = 0
        R["V1_START"] = 0
        R["AUTOMATION_ENABLE"] = 0
        R["NEW_RUN_CREATE"] = 0
    else:
        R["R24_GATE"] = "PASS"
    for k in COUNTERS:
        R.setdefault(k, 0)
    R["GIT_COMMIT"] = "NONE"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    return finish()


def finish():
    json.dump(R, open(os.path.join(HERE, "V1_R24_STATS_BOUNDARY.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False, default=str)
    print("\n=== §24 REPORT ===", flush=True)
    print("TASK_STATUS =", R.get("TASK_STATUS"))
    print("R24_GATE =", R.get("R24_GATE"))
    print("NEW_RUN_STATS_BOUNDARY =", R.get("NEW_RUN_STATS_BOUNDARY"))
    print("LEGACY_RUN_ID =", LEGACY_RUN)
    print("STOP_REASON =", R.get("STOP_REASON", "NONE"))
    print("RESET =", R.get("RESET", 0), "| NEW_RUN_CREATE =", R.get("NEW_RUN_CREATE", 0),
          "| V1_START =", R.get("V1_START", 0), "| AUTOMATION_ENABLE =", R.get("AUTOMATION_ENABLE", 0))
    print("PROVEN_SUBCONDITIONS =", json.dumps(R.get("PROVEN_SUBCONDITIONS"), ensure_ascii=False))
    print("BOUNDARY_EVIDENCE_SUMMARY =", json.dumps(R.get("BOUNDARY_EVIDENCE_SUMMARY"), ensure_ascii=False))
    print("CODE_HIT_COUNTS =", json.dumps(R.get("CODE_HIT_COUNTS"), ensure_ascii=False))
    print("OLD_LEDGER_IMMUTABLE =", R.get("OLD_LEDGER_IMMUTABLE"), "| OLD_LEDGER_MUTATION =", R.get("OLD_LEDGER_MUTATION"))
    print("ENGINE_BASELINE =", R.get("ENGINE_BASELINE"), "| PY_COMPILE =", R.get("PY_COMPILE"))
    print("V2_ISOLATION =", R.get("V2_ISOLATION"), "| V3_ISOLATION =", R.get("V3_ISOLATION"))
    print("COUNTERS =", json.dumps({k: R.get(k, 0) for k in COUNTERS} | {"GIT_COMMIT": R.get("GIT_COMMIT")},
                                     ensure_ascii=False))
    print("\n(artifact) " + os.path.join(HERE, "V1_R24_STATS_BOUNDARY.json"), flush=True)
    sys.exit(0 if R.get("R24_GATE") == "PASS" else 2)


if __name__ == "__main__":
    main()
