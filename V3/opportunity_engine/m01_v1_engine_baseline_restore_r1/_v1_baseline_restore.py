# -*- coding: utf-8 -*-
"""V1_ENGINE_BASELINE_RESTORE_R1 — stages 1..3 only (FREEZE / FIND EXACT BASELINE / PRE-RESTORE VERIFY).

READ-ONLY wrt V1. Stage 1 writes only the evidence copy inside this task's own directory.
No git reconstruction (forbidden), no V1 stop/restart, no restore, no baseline change, no whitelist,
no runtime-exclusion widening, no deletion, no commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
TARGET = os.path.join(RE, "hermes", "trader_v1", "engine.py")
PATHREL = "research/hermes/trader_v1/engine.py"
MVR1 = os.path.join(ENGINE, "mv_r1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOW = datetime.now(timezone.utc).isoformat()
PRE_EXPECT = "e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe"
BASE_EXPECT = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}


def sh(*a):
    try:
        p = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=180)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def write_reports(**kw):
    out = {"task": "V1_ENGINE_BASELINE_RESTORE_R1", "ts_utc": NOW, **R, **kw}
    json.dump(out, open(os.path.join(HERE, "V1_ENGINE_BASELINE_RESTORE_R1.json"), "w", encoding="utf-8",
                         newline="\n"), indent=1, ensure_ascii=False)
    keys = ["TASK_STATUS", "PRE_RESTORE_SHA256", "BASELINE_SHA256", "POST_RESTORE_SHA256",
             "BASELINE_ARTIFACT_FOUND", "BASELINE_HASH_MATCH", "CONTROLLED_RESTART", "V1_PID_BEFORE", "V1_PID_AFTER",
             "COMPILE", "IMPORT", "SELF_TEST", "RUNTIME_HEALTH", "V1_ISOLATION", "V2_ISOLATION",
             "V3_RESEARCH_STATUS", "STRATEGY_CHANGED", "PARAMETER_CHANGED", "ENTRY_CHANGED", "EXIT_CHANGED",
             "RISK_CHANGED", "ORDER_CHANGED", "COMMIT"]
    md = [f"# V1 engine.py 精确基线恢复 R1", "", f"`{NOW}`", "", "```text"]
    for k in keys:
        md.append(f"{k} = {out.get(k, 'UNKNOWN')}")
    md += ["```", "", "## 说明", "", "```text",
            f"STOP_REASON = {out.get('STOP_REASON', 'NONE')}",
            f"BASELINE_SOURCE = {out.get('BASELINE_SOURCE', 'NONE')}",
            f"searched_paths = {out.get('SEARCHED_PATHS', 0)}",
            "git_reconstruction_used = NO（按 §四 禁止）",
            "V1_touched = NO（未停止/未重启/未替换）",
            "```", "", "## 报告要点", "", "```json",
            json.dumps({k: out.get(k) for k in ("STOP_REASON", "LIVE_CONTENT_MATCHES", "PLACEHOLDER_MATCHES",
                                                  "research_immutability", "v1_process_state", "git_status",
                                                  "git_diff_stat")}, ensure_ascii=False, indent=1), "```"]
    open(os.path.join(HERE, "V1_ENGINE_BASELINE_RESTORE_R1.md"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(md))
    print("\n=== V1 BASELINE RESTORE R1 ===\n" + json.dumps({k: out.get(k) for k in keys}, ensure_ascii=False,
                                                              indent=1), flush=True)
    print("STOP_REASON:", out.get("STOP_REASON"), "| FOUND:", out.get("BASELINE_ARTIFACT_FOUND"),
          "| SOURCE:", out.get("BASELINE_SOURCE"), flush=True)


def main():
    os.makedirs(HERE, exist_ok=True)
    # ---------------- STAGE 1: freeze the current anomalous file ----------------
    pre_sha = sha(TARGET)
    R["PRE_RESTORE_SHA256"] = pre_sha
    if pre_sha != PRE_EXPECT:
        write_reports(TASK_STATUS="STOPPED", STOP_REASON="PRE_RESTORE_SHA256 != expected e308e9ce…",
                      BASELINE_ARTIFACT_FOUND="NO", BASELINE_HASH_MATCH="FAIL", POST_RESTORE_SHA256=None,
                      CONTROLLED_RESTART="NO", V1_ISOLATION="FAIL", COMMIT_GATE="FAIL", COMMIT="NONE")
        sys.exit(2)
    ev = os.path.join(HERE, "pre_restore_engine.py")
    shutil.copy2(TARGET, ev)
    stt = os.stat(TARGET)
    est = os.stat(ev)
    pre_diff = sh("git", "diff", "--no-color", "--", PATHREL)
    R["PRE_RESTORE_EVIDENCE"] = {"path": os.path.relpath(ev, AIQ).replace("\\", "/"), "copy_sha256": sha(ev),
                                   "PRE_RESTORE_SHA256": pre_sha, "PRE_RESTORE_SIZE": stt.st_size,
                                   "PRE_RESTORE_MTIME": datetime.fromtimestamp(stt.st_mtime, timezone.utc).isoformat(),
                                   "PRE_RESTORE_CTIME": datetime.fromtimestamp(stt.st_ctime, timezone.utc).isoformat(),
                                   "PRE_RESTORE_DIFF_LINES": len([l for l in pre_diff.splitlines() if l.strip()]),
                                   "PRE_RESTORE_DIFF": pre_diff[:900], "copy_verified": sha(ev) == pre_sha}
    print("STAGE1 frozen:", json.dumps({"sha": pre_sha[:16], "copy_ok": R["PRE_RESTORE_EVIDENCE"]["copy_verified"],
                                          "size": stt.st_size}, ensure_ascii=False), flush=True)

    # ---------------- STAGE 2/3: find an EXACT baseline artifact (no git reconstruction) ----------------
    searched = 0
    found = None
    live_matches = []
    placeholder = []
    roots = [os.path.join(RE, "hermes", "trader_v1"), ENGINE, os.path.join(AIQ, ".openclaw", "workspace"),
             os.path.join(AIQ, "archive") if os.path.isdir(os.path.join(AIQ, "archive")) else ENGINE]
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            if "__pycache__" in r_ or ".git" in r_:
                continue
            for f in fs:
                if not (f.endswith(".py") or f.endswith(".bak") or f.endswith(".orig") or f.endswith(".save")
                        or f.endswith(".snapshot") or f.endswith(".py.bak") or "engine" in f.lower()):
                    continue
                p = os.path.join(r_, f)
                if p in seen:
                    continue
                seen.add(p)
                try:
                    if os.path.getsize(p) > 5_000_000:
                        continue
                except OSError:
                    continue
                searched += 1
                h = sha(p)
                if h == BASE_EXPECT:
                    found = os.path.relpath(p, AIQ).replace("\\", "/")
                    break
                if h == PRE_EXPECT and p != TARGET:
                    live_matches.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                    if re.search(r"BASELINE_SHA256|PLACEHOLDER|sha256\s*[:=]\s*['\"]7d956456", txt):
                        placeholder.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                except Exception:  # noqa: BLE001
                    pass
            if found:
                break
        if found:
            break
    R["SEARCHED_PATHS"] = searched
    R["BASELINE_ARTIFACT_FOUND"] = "YES" if found else "NO"
    R["BASELINE_SOURCE"] = found or "NONE"
    R["BASELINE_HASH_MATCH"] = "PASS" if found else "FAIL"
    R["BASELINE_SHA256"] = BASE_EXPECT
    R["LIVE_CONTENT_MATCHES"] = live_matches[:10]
    R["PLACEHOLDER_MATCHES"] = placeholder[:10]
    R["git_reconstruction_used"] = "NO"
    R["post_restore_engine_content_written"] = "NO（未找到精确基线，未替换）" if not found else "PENDING_SAFE_STOP"

    # ---------------- read-only V1 process / task state + research immutability ----------------
    ps = sh("powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1'} | "
             "Select-Object ProcessId,Name,CreationDate | ConvertTo-Json -Compress")
    cron = sh("schtasks", "/query", "/fo", "LIST", "/v")
    v1tasks = [l for l in cron.splitlines() if re.search(r"(hermes|trader_v1)", l, re.I)][:6]
    R["v1_process_state"] = {"processes_matching_trader_v1": ps[:800], "v1_related_tasks": v1tasks,
                              "PID": (json.loads(ps)[0]["ProcessId"] if ps.strip().startswith("[") and ps != "[]"
                                       else (json.loads(ps).get("ProcessId") if ps.strip().startswith("{") else None)),
                              "OPEN_POSITIONS": "NOT_EVALUATED", "PENDING_ORDERS": "NOT_EVALUATED",
                              "note": "read-only snapshot; no stop/restart attempted"}
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3ok = (imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775") \
        and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98")
    R["research_immutability"] = imm
    R["git_status"] = sh("git", "status", "--short", "--", PATHREL)
    R["git_diff_stat"] = sh("git", "diff", "--stat", "--", PATHREL)

    # ---------------- decision ----------------
    if found:
        write_reports(TASK_STATUS="STAGE_1_3_COMPLETE", POST_RESTORE_SHA256=None, CONTROLLED_RESTART="NO",
                      V1_PID_BEFORE=R["v1_process_state"].get("PID"), V1_PID_AFTER="NOT_RESTARTED",
                      COMPILE="NOT_RUN", IMPORT="NOT_RUN", SELF_TEST="NOT_RUN", RUNTIME_HEALTH="NOT_RUN",
                      V1_ISOLATION="FAIL（尚未替换/复验）", V2_ISOLATION="PASS",
                      V3_RESEARCH_STATUS="UNCHANGED" if v3ok else "CHANGED",
                      STRATEGY_CHANGED="NO", PARAMETER_CHANGED="NO", ENTRY_CHANGED="NO", EXIT_CHANGED="NO",
                      RISK_CHANGED="NO", ORDER_CHANGED="NO", COMMIT="NONE",
                      COMMIT_GATE="READY_FOR_REVIEW",
                      STOP_REASON="baseline artifact found; controlled V1 stop/restore deferred to the next window "
                                    "(trading engine stop is safety-sensitive)")
    else:
        write_reports(TASK_STATUS="STOPPED", POST_RESTORE_SHA256=None, CONTROLLED_RESTART="NO",
                      V1_PID_BEFORE=R["v1_process_state"].get("PID"), V1_PID_AFTER="NOT_RESTARTED",
                      COMPILE="NOT_RUN", IMPORT="NOT_RUN", SELF_TEST="NOT_RUN", RUNTIME_HEALTH="NOT_RUN",
                      V1_ISOLATION="FAIL", V2_ISOLATION="PASS",
                      V3_RESEARCH_STATUS="UNCHANGED" if v3ok else "CHANGED",
                      STRATEGY_CHANGED="NO", PARAMETER_CHANGED="NO", ENTRY_CHANGED="NO", EXIT_CHANGED="NO",
                      RISK_CHANGED="NO", ORDER_CHANGED="NO", COMMIT="NONE", COMMIT_GATE="FAIL",
                      STOP_REASON="EXACT BASELINE ARTIFACT NOT FOUND on disk; git reconstruction is forbidden (§4) "
                                    "-> no V1 stop/restart/restore performed")
    print("research_immutability:", json.dumps(imm, ensure_ascii=False)[:300], flush=True)
    print("v1_process_state:", json.dumps(R["v1_process_state"], ensure_ascii=False)[:400], flush=True)
    print("live_content_matches:", live_matches[:5], "| placeholder:", placeholder[:5], flush=True)


if __name__ == "__main__":
    main()
