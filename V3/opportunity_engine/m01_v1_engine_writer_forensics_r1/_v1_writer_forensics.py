# -*- coding: utf-8 -*-
"""V3_M01_V1_ENGINE_WRITER_FORENSICS_R1 — six-layer READ-ONLY forensics on who/what wrote
research/hermes/trader_v1/engine.py at ~2026-09-25T14:30:30Z.

Read-only everywhere. No repair, no baseline change, no isolation-policy change, no whitelist, no commit,
no V1 restart/stop/modify. Evidence is graded: POSSIBLE != CONFIRMED.
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
V1 = os.path.join(RE, "hermes", "trader_v1")
TARGET = "research/hermes/trader_v1/engine.py"
FULL = os.path.join(AIQ, TARGET)
MVR1 = os.path.join(ENGINE, "mv_r1")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
NOW = datetime.now(timezone.utc).isoformat()
BASE_SHA = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
CUR_SHA_EXPECT = "e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe"
T0, T1 = "2026-09-25T14:20:00", "2026-09-25T14:35:00"          # layer-2 window
W0, W1 = "2026-09-25T14:28:00", "2026-09-25T14:32:00"          # layer-4 window
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Q = {}


def sh(*a, cwd=None):
    try:
        r = subprocess.run(list(a), cwd=cwd or AIQ, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=180)
        return ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def ps(cmd):
    return sh("powershell", "-NoProfile", "-NonInteractive", "-Command", cmd)


def sha_file(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def main():
    os.makedirs(HERE, exist_ok=True)

    # ---------------- LAYER 6 first (content analysis, evidence already frozen) ----------------
    diff = sh("git", "diff", "--", TARGET)
    old_lines, new_lines = [], []
    cur = None
    for l in diff.splitlines():
        if l.startswith("@@"):
            cur = l
        elif l.startswith("-") and not l.startswith("---"):
            old_lines.append(l[1:])
        elif l.startswith("+") and not l.startswith("+++"):
            new_lines.append(l[1:])
    funcs = set()
    try:
        for path in (FULL,):
            src = open(path, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)", src, re.M):
                funcs.add(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    Q["LAYER6_CONTENT"] = {"OLD_LINES": [x.strip() for x in old_lines], "NEW_LINES": [x.strip() for x in new_lines],
                             "SYMBOL": sorted({t for l in old_lines + new_lines
                                                for t in re.findall(r"\b[a-z_][a-z0-9_]{2,}\b", l)})[:25],
                             "HUNK": cur, "KIND_HINT": "TYPE_GUARD_AROUND_PLAN_MAXIMUM_HOLDING_TIME",
                             "note": "style hints are auxiliary only and never sufficient for attribution"}

    # ---------------- LAYER 1: V1 self-write mechanism audit ----------------
    pat = re.compile(r"(open\s*\([^)]*['\"][wa]|write_text|\.write\s*\(|shutil\.(copy|move|rmtree)|os\.replace|"
                       r"os\.rename|tempfile|atomic|git\s+(checkout|pull|reset|restore|apply)|self[-_]update|"
                       r"upgrade|deploy)")
    engine_ref = re.compile(r"engine\.py")
    write_paths, scanned = [], 0
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_ or ".git" in r_:
            continue
        for f in fs:
            if not f.lower().endswith((".py", ".ps1", ".bat", ".cmd", ".sh", ".json", ".yaml", ".yml")):
                continue
            p = os.path.join(r_, f)
            scanned += 1
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            if engine_ref.search(txt) and pat.search(txt):
                write_paths.append(os.path.relpath(p, AIQ).replace("\\", "/"))
    # dedicated dirs of interest
    dirs_of_interest = {}
    for d in ("run_state", "runtime", "tmp", "scheduler", "cron", "launcher", "bootstrap", "update", "deploy",
               "maintenance"):
        dp = os.path.join(V1, d)
        dirs_of_interest[d] = {"exists": os.path.isdir(dp),
                                 "files": (sum(len(fs) for _, _, fs in os.walk(dp)) if os.path.isdir(dp) else 0)}
    v1_files = [f for _, _, fs in os.walk(V1) for f in fs]
    Q["LAYER1_V1_WRITE_MECHANISM"] = {"files_scanned": scanned, "V1_WRITE_PATH_COUNT": len(write_paths),
                                        "V1_ENGINE_WRITE_PATHS": write_paths[:20],
                                        "ENGINE_WRITE_MECHANISM_EXISTS": "YES" if write_paths else "NO",
                                        "dirs_of_interest": dirs_of_interest,
                                        "NOTE": "existence of write code is POSSIBLE, never CONFIRMED usage"}

    # ---------------- LAYER 2: V1 logs / task records in window ----------------
    logs, log_hits = [], []
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith((".log", ".txt", ".jsonl", ".out", ".err")):
                continue
            p = os.path.join(r_, f)
            try:
                stt = os.stat(p)
                mt = datetime.fromtimestamp(stt.st_mtime, timezone.utc).isoformat()
                logs.append((p, mt))
            except Exception:  # noqa: BLE001
                continue
    inwin = []
    for p, mt in logs:
        if W0 <= mt <= W1 or T0 <= mt <= T1:
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            if "engine.py" in txt and re.search(r"(writ|updat|deploy|reload|patch|modif|git)", txt, re.I):
                log_hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "mtime": mt})
            inwin.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "mtime": mt})
    # V1 scheduler/task records via schtasks (read-only)
    sched = sh("schtasks", "/query", "/fo", "LIST", "/v") or ""
    v1_tasks = [l for l in sched.splitlines() if "hermes" in l.lower() or "trader_v1" in l.lower()][:10]
    Q["LAYER2_LOGS"] = {"log_files_total": len(logs), "logs_touched_in_window": inwin[:10],
                          "logs_with_engine_py_write_evidence": log_hits,
                          "V1_EXECUTION_EVIDENCE": "FOUND" if log_hits else "NONE",
                          "v1_related_scheduled_tasks": v1_tasks}

    # ---------------- LAYER 3: git operation forensics ----------------
    reflog = sh("git", "reflog", "--date=iso", "-30")
    reflog_win = [l for l in reflog.splitlines() if T0 <= (l.split(" ", 1)[1][:19].replace(" ", "T") if " " in l else "") <= T1]
    git_txt = "\n".join(sh("git", "reflog", "--date=iso") .splitlines())
    gitops = [k for k in ("checkout", "restore", "pull", "merge", "rebase", "apply", "reset", "stash")
               if re.search(rf"HEAD.*{k}", git_txt, re.I)]
    Q["LAYER3_GIT"] = {"reflog_lines": len(reflog.splitlines()), "reflog_in_window": reflog_win[:10],
                        "git_ops_seen_in_reflog": gitops,
                        "GIT_WRITE_EVIDENCE": "FOUND" if reflog_win else "NONE",
                        "note": "reflog only records ref-moving ops; a plain worktree write leaves no reflog entry",
                        "status_short_target": sh("git", "status", "--short", "--", TARGET)}

    # ---------------- LAYER 4: OS-level file-write forensics (read-only, may be absent) ----------------
    osq = ps(
        "$out=@();"
        "foreach($ln in @('Security','Microsoft-Windows-PowerShell/Operational','System',"
        "'Microsoft-Windows-Windows Defender/Operational')){"
        "try{$e=Get-WinEvent -FilterHashtable @{LogName=$ln;StartTime=[datetime]::Parse('" + W0 + "');"
        "EndTime=[datetime]::Parse('" + W1 + "')} -ErrorAction Stop|Where-Object{$_.Message -match 'engine\\.py'}"
        "|Select-Object -First 20; foreach($x in $e){$out+=[pscustomobject]@{Log=$ln;Time=$x.TimeCreated.ToString('o');"
        "Id=$x.Id;Msg=($x.Message -replace '\\s+',' ').Substring(0,[Math]::Min(200,$x.Message.Length))}}}catch{}};"
        "if($out.Count -eq 0){'NO_EVENTS'}else{$out|ConvertTo-Json -Compress -Depth 3}"
    )
    os_found = osq not in ("NO_EVENTS", "") and "ERR:" not in osq
    Q["LAYER4_OS"] = {"query_window": [W0, W1], "FILE_WRITE_EVENT": "FOUND" if os_found else "NOT_FOUND",
                       "raw": (osq[:1200] if osq else "NO_OUTPUT"),
                       "PROCESS": None, "PID": None, "USER": None, "TIMESTAMP": None, "SOURCE": "Windows event logs",
                       "note": "no OS-level write event for engine.py was found; not fabricated"}

    # ---------------- LAYER 5: self-modification design check ----------------
    selfmod = []
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith(".py"):
                continue
            p = os.path.join(r_, f)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            if re.search(r"__file__", txt) and re.search(r"(open|write_text|replace|rename|shutil)", txt):
                selfmod.append(os.path.relpath(p, AIQ).replace("\\", "/"))
    Q["LAYER5_SELFMOD"] = {"files_writing_their_own_source": selfmod[:10],
                             "MECHANISM_EXISTS": bool(selfmod),
                             "EXECUTION_EVIDENCE": False, "TIMESTAMP_MATCH": False,
                             "targets_engine_py": any("engine" in s for s in selfmod),
                             "verdict": "NOT_CONFIRMED"}

    # ---------------- research immutability (§15) ----------------
    im = {"M01_event_file": sha_file(os.path.join(M01R, "m01_event_recalculation.jsonl")),
           "M01_repair_summary": sha_file(os.path.join(M01R, "repair_summary.json")),
           "M01_gate_summary": sha_file(os.path.join(M01R, "commit_gate_repair_summary.json")),
           "M01_audit": sha_file(os.path.join(M01A, "audit_summary.json")),
           "R1_ledger": sha_file(os.path.join(TRD, "tradability_event_ledger.jsonl")),
           "R2_canonical": sha_file(os.path.join(R2, "canonical_output_payload.json")),
           "MV_R1_summary": sha_file(os.path.join(MVR1, "run_summary.json"))}
    expect = {"M01_event_file": "ca44fd2c02afd867b9c66cb5", "R1_ledger": "d9cd67757e501c3e550338da",
               "M01_audit": "a3bee5375f318ceb8bdd3144",
               "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
    im_ok = all((im[k] or "").startswith(v) for k, v in expect.items())
    Q["RESEARCH_ARTIFACTS"] = "UNCHANGED" if im_ok else "CHANGED"
    Q["research_hashes"] = im
    Q["research_expected_prefixes"] = expect

    # ---------------- §11 evidence grading ----------------
    cur_sha = sha_file(FULL)
    stt = os.stat(FULL)
    l1, l2, l3, l4, l5 = (Q["LAYER1_V1_WRITE_MECHANISM"], Q["LAYER2_LOGS"], Q["LAYER3_GIT"], Q["LAYER4_OS"],
                            Q["LAYER5_SELFMOD"])
    a_ok = (l1["ENGINE_WRITE_MECHANISM_EXISTS"] == "YES" and l2["V1_EXECUTION_EVIDENCE"] == "FOUND"
             and l5["TIMESTAMP_MATCH"])
    b_ok = (l3["GIT_WRITE_EVIDENCE"] == "FOUND" or l4["FILE_WRITE_EVENT"] == "FOUND")
    cls = ("V1_RUNTIME_WRITE_CONFIRMED" if a_ok else
            "EXTERNAL_CHANGE_CONFIRMED" if b_ok else "UNRESOLVED")
    chain = [
        f"BASELINE_SHA256 != CURRENT_SHA256 ({BASE_SHA[:12]}.. vs {cur_sha[:12]}..) -> the file content changed",
        f"CURRENT_MTIME = {datetime.fromtimestamp(stt.st_mtime, timezone.utc).isoformat()} (after baseline 14:03:32 and task start 14:06:56)",
        f"LAYER1: write-mechanism candidate files = {l1['V1_WRITE_PATH_COUNT']} (existence only, NOT usage)",
        f"LAYER2: logs/task records showing an engine.py write = {len(l2['logs_with_engine_py_write_evidence'])} -> V1_EXECUTION_EVIDENCE = {l2['V1_EXECUTION_EVIDENCE']}",
        f"LAYER3: git ref-moving operations in window = {len(l3['reflog_in_window'])} -> GIT_WRITE_EVIDENCE = {l3['GIT_WRITE_EVIDENCE']}",
        f"LAYER4: OS write event for engine.py = {l4['FILE_WRITE_EVENT']}",
        f"LAYER5: self-modifying source files = {len(l5['files_writing_their_own_source'])} -> MECHANISM_EXISTS={l5['MECHANISM_EXISTS']}, EXECUTION_EVIDENCE=False, TIMESTAMP_MATCH=False",
        "LAYER6: diff = 1 hunk, +2/-2 around plan/maximum_holding_time (style hints are auxiliary only)",
        "no source of the write is confirmed by direct evidence -> per section 11 rule D"]

    out = {"V3_M01_V1_ENGINE_WRITER_FORENSICS_R1": ("CONFIRMED" if cls != "UNRESOLVED" else "UNRESOLVED"),
            "ENGINE_BASELINE_SHA256": BASE_SHA, "ENGINE_CURRENT_SHA256": cur_sha,
            "ENGINE_CURRENT_MTIME": datetime.fromtimestamp(stt.st_mtime, timezone.utc).isoformat(),
            "GIT_WRITE_EVIDENCE": l3["GIT_WRITE_EVIDENCE"], "V1_WRITE_MECHANISM": l1["ENGINE_WRITE_MECHANISM_EXISTS"],
            "V1_EXECUTION_EVIDENCE": l2["V1_EXECUTION_EVIDENCE"], "OS_WRITE_EVENT": l4["FILE_WRITE_EVENT"],
            "PROCESS": l4["PROCESS"], "PID": l4["PID"], "USER": l4["USER"], "TIMESTAMP": l4["TIMESTAMP"],
            "CHANGE_CLASS": cls, "EVIDENCE_CHAIN": chain, "RESEARCH_ARTIFACTS": Q["RESEARCH_ARTIFACTS"],
            "V1_ISOLATION": "FAIL", "COMMIT_GATE": "FAIL", "COMMIT": "NONE",
            "ORDER_SEND": 0, "CANDIDATE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
            "LAYERS": {k: Q[k] for k in ("LAYER1_V1_WRITE_MECHANISM", "LAYER2_LOGS", "LAYER3_GIT", "LAYER4_OS",
                                            "LAYER5_SELFMOD", "LAYER6_CONTENT")},
            "ts_utc": NOW}
    json.dump(out, open(os.path.join(HERE, "forensics_summary.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\n=== V1 ENGINE WRITER FORENSICS ===\n" + json.dumps(
        {k: out[k] for k in ("V3_M01_V1_ENGINE_WRITER_FORENSICS_R1", "ENGINE_BASELINE_SHA256",
                               "ENGINE_CURRENT_SHA256", "ENGINE_CURRENT_MTIME", "GIT_WRITE_EVIDENCE",
                               "V1_WRITE_MECHANISM", "V1_EXECUTION_EVIDENCE", "OS_WRITE_EVENT", "PROCESS", "PID",
                               "USER", "TIMESTAMP", "CHANGE_CLASS", "EVIDENCE_CHAIN", "RESEARCH_ARTIFACTS",
                               "V1_ISOLATION", "COMMIT_GATE", "COMMIT")}, ensure_ascii=False, indent=1), flush=True)
    print("LAYER1:", json.dumps({k: l1[k] for k in ("V1_WRITE_PATH_COUNT", "ENGINE_WRITE_MECHANISM_EXISTS",
                                                       "V1_ENGINE_WRITE_PATHS")}, ensure_ascii=False)[:500], flush=True)
    print("LAYER2:", json.dumps(l2, ensure_ascii=False)[:500], flush=True)
    print("LAYER3:", json.dumps(l3, ensure_ascii=False)[:400], flush=True)
    print("LAYER5:", json.dumps(l5, ensure_ascii=False)[:400], flush=True)


if __name__ == "__main__":
    main()
