# -*- coding: utf-8 -*-
"""V1_ENGINE_RESTORE_R15 — precise baseline restore of ONE file + post-restore integrity proof.

ONLY authorised write: research/hermes/trader_v1/engine.py (via atomic os.replace from a verified temp copy).
Forbidden & never executed: V1_STOP/RESTART/KILL, AUTOMATION_RUN/TRIGGER/UPDATE/ENABLE/DISABLE/DELETE,
MT5_ACCESS(any), ORDER_SEND, POSITION_CLOSE, GIT_CHECKOUT/RESTORE/RESET/COMMIT, running engine.py.
Baseline and pre-restore backup are never modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
TARGET = os.path.join(V1, "engine.py")
BASELINE = os.path.join(AIQ, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
BACKUP = os.path.join(ENGINE_DIR, "m01_v1_engine_baseline_restore_r1", "pre_restore_engine.py")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
TMPDIR = os.path.join(HERE, "tmp")           # outside V1 source/config
PYEXE = os.path.join(AIQ, ".venv", "Scripts", "python.exe")
CUR_EXPECT = "e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe"
BASE_EXPECT = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
R = {}
os.makedirs(TMPDIR, exist_ok=True)


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def stat_of(p):
    try:
        st = os.stat(p)
        return st.st_size, datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
    except Exception as e:  # noqa: BLE001
        return None, "ERR:" + type(e).__name__


def engine_procs():
    """read-only process query for anything running engine.py"""
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                             "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'engine\\.py'} | "
                             "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        out = (p.stdout or "").strip()
        if out in ("", "null"):
            return []
        d = json.loads(out)
        lst = d if isinstance(d, list) else [d]
        return [x for x in lst if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def main():
    R["TASK_STATUS"] = "RUNNING"
    R["STARTED_UTC"] = datetime.now(timezone.utc).isoformat()

    # ================= STAGE 1 : pre-restore instant check =================
    st_size, st_mtime = stat_of(TARGET)
    cur = sha(TARGET)
    R["PRE_RESTORE_ENGINE_SHA256"] = cur
    R["PRE_RESTORE_ENGINE_SIZE"] = st_size
    R["PRE_RESTORE_ENGINE_MTIME"] = st_mtime
    base = sha(BASELINE)
    R["BASELINE_SHA256"] = base
    b_size, _ = stat_of(BASELINE)
    R["BASELINE_SIZE"] = b_size
    if base != BASE_EXPECT:
        return abort("BASELINE_HASH_FAILURE")
    if cur != CUR_EXPECT:
        return abort("CURRENT_ENGINE_CHANGED_SINCE_R14")

    # ================= STAGE 2 : write-race check (read-only) =================
    m0 = os.stat(TARGET).st_mtime
    s0 = os.stat(TARGET).st_size
    procs0 = engine_procs()
    time.sleep(6)
    m1 = os.stat(TARGET).st_mtime
    s1 = os.stat(TARGET).st_size
    procs1 = engine_procs()
    stable = (m0 == m1 and s0 == s1)
    no_engine_proc = (procs0 == [] and procs1 == [])
    R["WRITE_RACE_OBSERVATION_SECONDS"] = 6
    R["WRITE_RACE_MTIME_STABLE"] = "YES" if stable else "NO"
    R["WRITE_RACE_ENGINE_PROCESS"] = "NONE" if no_engine_proc else ("UNKNOWN" if procs1 == "UNKNOWN" else str(procs1)[:200])
    if not stable:
        return abort("WRITE_RACE_UNKNOWN")
    if not no_engine_proc:
        return abort("WRITE_RACE_UNKNOWN")
    R["WRITE_RACE"] = "NOT_DETECTED"

    # ================= STAGE 3 : re-verify pre-restore backup =================
    bk = sha(BACKUP)
    R["PRE_RESTORE_BACKUP_SHA256"] = bk
    bk_size, _ = stat_of(BACKUP)
    R["PRE_RESTORE_BACKUP_SIZE"] = bk_size
    if bk != CUR_EXPECT:
        return abort("PRE_RESTORE_BACKUP_CHANGED")

    # ================= STAGE 4 : precise restore (atomic, no git) =================
    tmp = os.path.join(TMPDIR, "engine_restore_tmp.py")
    try:
        shutil.copyfile(BASELINE, tmp)
    except Exception:  # noqa: BLE001
        return abort("ATOMIC_REPLACEMENT_NOT_AVAILABLE")
    if sha(tmp) != BASE_EXPECT:
        return abort("ATOMIC_REPLACEMENT_NOT_AVAILABLE")
    R["TEMP_FILE_SHA256"] = sha(tmp)
    R["TEMP_DIR"] = os.path.relpath(TMPDIR, AIQ).replace("\\", "/")
    R["ENGINE_RESTORE_METHOD"] = "baseline -> temp copy (same volume) -> sha256 verify -> os.replace(temp, target); no git; target never truncated"
    try:
        os.replace(tmp, TARGET)          # atomic replace, no 0-byte truncation phase
    except Exception as e:  # noqa: BLE001
        R["REPLACE_ERROR"] = type(e).__name__
        return abort("ATOMIC_REPLACEMENT_NOT_AVAILABLE")
    R["ENGINE_RESTORE_EXECUTED"] = "YES"

    # ================= STAGE 5/6 : post-restore hash + size =================
    post = sha(TARGET)
    p_size, p_mtime = stat_of(TARGET)
    R["POST_RESTORE_ENGINE_SHA256"] = post
    R["POST_RESTORE_ENGINE_SIZE"] = p_size
    R["POST_RESTORE_ENGINE_MTIME"] = p_mtime
    R["ENGINE_RESTORE_HASH"] = "PASS" if post == BASE_EXPECT else "FAIL"
    R["SIZE_MATCH"] = "PASS" if p_size == b_size else "FAIL"
    if post != BASE_EXPECT:
        return abort("POST_RESTORE_HASH_FAILURE")       # no second overwrite, no rollback
    if p_size != b_size:
        return abort("POST_RESTORE_HASH_FAILURE")

    # ================= STAGE 7 : py_compile (no execution) =================
    pycdir = os.path.join(V1, "__pycache__")
    existed_before = os.path.isdir(pycdir)
    files_before = set(os.listdir(pycdir)) if existed_before else set()
    try:
        pr = subprocess.run([PYEXE, "-m", "py_compile", TARGET], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=120)
        rc = pr.returncode
        pyerr = ((pr.stdout or "") + (pr.stderr or ""))[:300]
    except Exception as e:  # noqa: BLE001
        rc, pyerr = 1, type(e).__name__
    files_after = set(os.listdir(pycdir)) if os.path.isdir(pycdir) else set()
    R["PY_COMPILE"] = "PASS" if rc == 0 else "FAIL"
    R["PY_COMPILE_ERR"] = pyerr if rc != 0 else ""
    if not existed_before and files_after:
        R["PYCOMPILE_ARTIFACT"] = "CREATED"
    elif existed_before and files_after:
        R["PYCOMPILE_ARTIFACT"] = "EXISTING" if files_after == files_before else "CREATED"
    else:
        R["PYCOMPILE_ARTIFACT"] = "NONE"
    if rc != 0:
        return abort("PY_COMPILE_FAILURE")

    # ================= STAGE 9 : isolation (expect only engine.py) =================
    def newer(root, lim):
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
    lim = time.time() - 600          # last 10 minutes
    v1c = [p for p in newer(V1, lim) if p != os.path.relpath(TARGET, AIQ).replace("\\", "/")]
    v2c = newer(V2, lim)
    R["V1_OTHER_SOURCE_CHANGES"] = "NO" if not v1c else "YES"
    R["V1_OTHER_SOURCE_CHANGES_LIST"] = v1c[:5]
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    R["V2_CHANGES_LIST"] = v2c[:5]
    if v1c:
        return abort("UNEXPECTED_V1_SOURCE_CHANGE")
    if v2c:
        return abort("V2_INTEGRITY_FAILURE")

    # ================= STAGE 10 : V3 four hashes =================
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    v3ok = all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT)
    R["V3_RESEARCH_MODIFIED"] = "NO" if v3ok else "YES"
    if not v3ok:
        return abort("V3_INTEGRITY_FAILURE")

    # ================= STAGE 11-13 : forbidden-op ledger =================
    R["MT5_ACCESS"] = 0
    R["ORDER_SEND"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["V1_KILL"] = 0
    R["AUTOMATION_RUN"] = 0
    R["AUTOMATION_WRITE"] = 0
    R["CONFIG_WRITE"] = 0
    R["SOURCE_WRITE_SCOPE"] = "engine.py ONLY"
    R["GIT_COMMIT"] = "NONE"
    R["ENGINE_RUN_EXECUTED"] = "NO"
    R["PRE_RESTORE_BACKUP_INTACT"] = "PASS" if sha(BACKUP) == CUR_EXPECT else "FAIL"
    R["BASELINE_INTACT"] = "PASS" if sha(BASELINE) == BASE_EXPECT else "FAIL"
    R["ENGINE_STATE"] = "MV-R1 BASELINE RESTORED"
    R["TASK_STATUS"] = "V1_ENGINE_RESTORE_R15_COMPLETE"
    R["ENGINE_RESTORE"] = "PASS"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FINISHED_UTC"] = datetime.now(timezone.utc).isoformat()
    write(rc=0)


def abort(reason):
    R["TASK_STATUS"] = "V1_ENGINE_RESTORE_R15_ABORTED"
    R["ENGINE_RESTORE"] = "NOT_EXECUTED" if not R.get("ENGINE_RESTORE_EXECUTED") else "FAIL"
    R["STOP_REASON"] = reason
    R.setdefault("WRITE_RACE", "UNKNOWN")
    R.setdefault("ENGINE_RESTORE_EXECUTED", "NO")
    R.setdefault("ENGINE_RESTORE_METHOD", "NOT_EXECUTED")
    R.setdefault("POST_RESTORE_ENGINE_SHA256", "NOT_APPLIED")
    R.setdefault("ENGINE_RESTORE_HASH", "FAIL")
    R.setdefault("PY_COMPILE", "NOT_RUN")
    R.setdefault("PYCOMPILE_ARTIFACT", "NONE")
    R.setdefault("V1_OTHER_SOURCE_CHANGES", "UNKNOWN")
    R.setdefault("V2_SOURCE_CONFIG_MODIFIED", "UNKNOWN")
    R.setdefault("V3_RESEARCH_MODIFIED", "UNKNOWN")
    R.setdefault("ENGINE_STATE", "NOT RESTORED")
    R["MT5_ACCESS"] = 0
    R["ORDER_SEND"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["AUTOMATION_RUN"] = 0
    R["AUTOMATION_WRITE"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FINISHED_UTC"] = datetime.now(timezone.utc).isoformat()
    write(rc=2)


def write(rc=0):
    os.makedirs(HERE, exist_ok=True)
    json.dump(R, open(os.path.join(HERE, "V1_ENGINE_RESTORE_R15.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "PRE_RESTORE_ENGINE_SHA256", "BASELINE_SHA256", "PRE_RESTORE_BACKUP_SHA256",
             "WRITE_RACE", "ENGINE_RESTORE_EXECUTED", "ENGINE_RESTORE_METHOD", "POST_RESTORE_ENGINE_SHA256",
             "POST_RESTORE_ENGINE_SIZE", "BASELINE_SIZE", "ENGINE_RESTORE_HASH", "PY_COMPILE",
             "PYCOMPILE_ARTIFACT", "V1_OTHER_SOURCE_CHANGES", "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED",
             "PRE_RESTORE_BACKUP_INTACT", "V3_M01_EVENT_HASH", "V3_R1_LEDGER_HASH", "V3_M01_AUDIT_HASH",
             "V3_R2_CANONICAL_HASH", "MT5_ACCESS", "ORDER_SEND", "V1_STOP", "V1_RESTART", "AUTOMATION_RUN",
             "AUTOMATION_WRITE", "SOURCE_WRITE_SCOPE", "CONFIG_WRITE", "GIT_COMMIT", "ENGINE_STATE",
             "NEXT_STAGE_AUTHORIZED"]
    print("\n=== §20 FINAL REPORT ===", flush=True)
    for k in keys:
        print(f"{k} = {R.get(k, 'UNKNOWN')}", flush=True)
    if R.get("STOP_REASON"):
        print("STOP_REASON =", R["STOP_REASON"], flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_ENGINE_RESTORE_R15.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
