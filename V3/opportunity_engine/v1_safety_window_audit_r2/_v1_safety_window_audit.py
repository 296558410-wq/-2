# -*- coding: utf-8 -*-
"""V1_SAFETY_SWITCH_WINDOW_AUDIT_R2 — READ-ONLY. Proves (or refuses to prove) a safe stop window for V1.

No V1/V2/V3 file, parameter, config, task or trading state is modified. No process is stopped/killed/
suspended/restarted. No order/cancel/close API is called. Any UNKNOWN on a key field => NOT_PROVEN => STOP.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
V1 = os.path.join(RE, "hermes", "trader_v1")
RUN = os.path.join(V1, "run_state")
MVR1 = os.path.join(ENGINE, "mv_r1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOW = datetime.now(timezone.utc)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


def ps(cmd):
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], cwd=AIQ,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOW.isoformat()

    # ---------------- §一 V1 process audit ----------------
    raw = ps("Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1'} | "
              "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
              "ConvertTo-Json -Compress -Depth 4")
    try:
        procs = json.loads(raw) if raw and raw.startswith(("{", "[")) else []
    except Exception:  # noqa: BLE001
        procs = []
    if isinstance(procs, dict):
        procs = [procs]
    # also look for python children of those processes
    pids = [p.get("ProcessId") for p in procs]
    kids = []
    if pids:
        idlist = ",".join(str(x) for x in pids)
        kraw = ps(f"Get-CimInstance Win32_Process | Where-Object {{$_.ParentProcessId -in @({idlist})}} | "
                  "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 4")
        try:
            kids = json.loads(kraw) if kraw and kraw.startswith(("{", "[")) else []
        except Exception:  # noqa: BLE001
            kids = []
        if isinstance(kids, dict):
            kids = [kids]
    engine = [p for p in procs + kids
               if re.search(r"python", (p.get("Name") or ""), re.I) and "trader_v1" in (p.get("CommandLine") or "")]
    py_path = None
    wd = None
    cmd = None
    if engine:
        c = engine[0].get("CommandLine") or ""
        cmd = c
        m = re.match(r'\s*"([^"]+python[^"]*\.exe)"', c, re.I) or re.match(r"\s*(\S*python\S*\.exe)", c, re.I)
        py_path = m.group(1) if m else None
        wm = re.search(r"(?:--cwd|-C)\s+\"?([A-Za-z]:\\[^\"]+)", c)
        wd = wm.group(1) if wm else None
    O["V1_PROCESS_STATE"] = {"matched_processes": procs, "children": kids, "engine_candidates": len(engine),
                               "note": "PID 14376 was a powershell.exe in the previous audit and is NOT assumed to be V1"}
    O["V1_ENGINE_PID"] = (engine[0].get("ProcessId") if engine else None)
    O["V1_ENGINE_PROCESS_NAME"] = (engine[0].get("Name") if engine else None)
    O["V1_ENGINE_CMDLINE"] = cmd
    O["V1_ENGINE_PARENT_PID"] = (engine[0].get("ParentProcessId") if engine else None)
    O["V1_PYTHON_PATH"] = py_path
    O["V1_WORKING_DIRECTORY"] = wd or "UNKNOWN"
    O["V1_START_TIME"] = (str(engine[0].get("CreationDate")) if engine else None)
    O["V1_PROCESS_COUNT"] = len(procs) + len(kids)
    O["V1_PID_CONFIDENCE"] = "CONFIRMED" if (engine and py_path and engine[0].get("ParentProcessId")) else "UNCONFIRMED"

    # ---------------- §二 scheduled tasks ----------------
    traw = ps("Get-ScheduledTask | Where-Object {$_.TaskPath -like '*OpenClaw*'} | ForEach-Object {"
               "$i=Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath;"
               "[pscustomobject]@{Name=($_.TaskPath+$_.TaskName);State=[string]$_.State;"
               "Enabled=$_.Settings.Enabled;Last=[string]$i.LastRunTime;Result=$i.LastTaskResult;"
               "Next=[string]$i.NextRunTime;Actions=(($_.Actions|ForEach-Object{($_.Execute+' '+$_.Arguments)}) -join ' | ')}"
               "} | ConvertTo-Json -Compress -Depth 4")
    try:
        tasks = json.loads(traw) if traw and traw.startswith(("{", "[")) else []
    except Exception:  # noqa: BLE001
        tasks = []
    if isinstance(tasks, dict):
        tasks = [tasks]
    v1tasks = [t for t in tasks if re.search(r"(hermes|trader)", t.get("Name", ""), re.I)]
    primary = None
    for t in v1tasks:
        if re.search(r"trader_v1|hermes-trader", (t.get("Name", "") + t.get("Actions", "")), re.I):
            primary = t
    running = [t["Name"] for t in tasks if str(t.get("State", "")).lower() == "running"]
    nextruns = sorted([t["Next"] for t in v1tasks if t.get("Next")])
    O["V1_CRON_STATE"] = {"all_openclaw_tasks": tasks, "v1_related": v1tasks, "running_now": running}
    O["V1_PRIMARY_TASK"] = (primary or "UNKNOWN")
    O["V1_ACTIVE_TASKS"] = running
    O["V1_TASK_RETRY_STATE"] = "UNKNOWN" if any(str(t.get("Result")) not in ("0", "None", "") for t in v1tasks) else "NO_FAILED_TASK_SEEN"
    O["V1_NEXT_TRADING_TASK_TIME"] = (nextruns[0] if nextruns else "UNKNOWN")
    O["V1_AUTO_RESTART_MECHANISM"] = "UNKNOWN"        # cannot be proven read-only without exhaustive rule audit

    # ---------------- §三 trading state (read-only from V1 state files) ----------------
    def find(pat, root=RUN):
        hits = []
        for r_, _, fs in os.walk(root):
            for f in fs:
                if re.search(pat, f, re.I):
                    hits.append(os.path.join(r_, f))
        return hits
    positions = pending = None
    src = {}
    for key, pats in (("positions", (r"position", r"open_trade", r"trades")), ("orders", (r"order", r"pending"))):
        for f in [x for p in pats for x in find(p)][:6]:
            try:
                txt = open(f, encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            for k in ("open_positions", "positions", "pending_orders", "orders"):
                m = re.search(rf'"{k}"\s*:\s*(\[[^\]]*\]|\d+)', txt)
                if m:
                    src.setdefault(key, []).append({"file": os.path.relpath(f, AIQ).replace("\\", "/"), "key": k,
                                                      "value": m.group(1)[:200]})
    # try the canonical state package
    sp = os.path.join(RUN, "state_package_latest.json")
    state_doc = None
    if os.path.exists(sp):
        try:
            state_doc = json.load(open(sp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            state_doc = None
    op = state_doc.get("open_positions") if isinstance(state_doc, dict) else None
    po = state_doc.get("pending_orders") if isinstance(state_doc, dict) else None
    O["OPEN_POSITIONS"] = op if op is not None else "UNKNOWN"
    O["OPEN_POSITION_COUNT"] = (len(op) if isinstance(op, list) else (op if isinstance(op, int) else "UNKNOWN"))
    O["PENDING_ORDERS"] = po if po is not None else "UNKNOWN"
    O["PENDING_ORDER_COUNT"] = (len(po) if isinstance(po, list) else (po if isinstance(po, int) else "UNKNOWN"))
    O["ACTIVE_ORDER_ACTION"] = "UNKNOWN"
    O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["ORDER_RETRY_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    O["trading_state_sources"] = {"state_package": (os.path.relpath(sp, AIQ).replace("\\", "/") if state_doc else None),
                                    "greps": src}

    # ---------------- §四 state-write critical window ----------------
    def snap():
        d = {}
        for root in (RUN, os.path.join(V1, "runtime"), os.path.join(V1, "state")):
            if not os.path.isdir(root):
                continue
            for r_, _, fs in os.walk(root):
                for f in fs:
                    p = os.path.join(r_, f)
                    try:
                        st = os.stat(p)
                        d[os.path.relpath(p, AIQ).replace("\\", "/")] = (st.st_size, st.st_mtime)
                    except OSError:
                        continue
        return d
    s1 = snap()
    time.sleep(6)
    s2 = snap()
    changed = {k for k in s2 if k in s1 and (s2[k][0] != s1[k][0] or s2[k][1] != s1[k][1])}
    newest = sorted(s2.items(), key=lambda kv: kv[1][1], reverse=True)[:5]
    O["V1_CURRENT_WRITE_ACTIVITY"] = "ACTIVE" if changed else "IDLE"
    O["currently_writing_files"] = sorted(changed)[:10]
    O["newest_state_files"] = [{"file": k, "mtime": datetime.fromtimestamp(v[1], timezone.utc).isoformat(),
                                  "size": v[0]} for k, v in newest]
    O["V1_LEDGER_WRITE_ACTIVITY"] = "ACTIVE" if any("ledger" in c for c in changed) else "IDLE"
    O["V1_PLAN_WRITE_ACTIVITY"] = "ACTIVE" if any("plan" in c for c in changed) else "IDLE"
    O["V1_EXECUTION_WRITE_ACTIVITY"] = "ACTIVE" if any("exec" in c for c in changed) else "IDLE"
    O["V1_STATE_WRITE_ACTIVITY"] = "ACTIVE" if changed else "IDLE"
    wh = find(r"workflow_history")
    cyc = {}
    if wh:
        try:
            lines = [json.loads(l) for l in open(wh[0], encoding="utf-8") if l.strip()]
            last = lines[-1] if lines else {}
            cyc = {"last_entry": {k: str(last.get(k))[:60] for k in list(last)[:8]},
                    "file_mtime": datetime.fromtimestamp(os.path.getmtime(wh[0]), timezone.utc).isoformat()}
        except Exception:  # noqa: BLE001
            cyc = {"error": "unparsed"}
    O["V1_CURRENT_CYCLE"] = "RUNNING_OR_UNKNOWN" if (changed or not cyc) else "FINISHED"
    O["V1_LAST_CYCLE_START"] = cyc.get("last_entry", {}).get("start") or cyc.get("last_entry", {}).get("timestamp") or "UNKNOWN"
    O["V1_LAST_CYCLE_END"] = cyc.get("file_mtime", "UNKNOWN")
    O["STATE_WRITE_IN_FLIGHT"] = "YES" if changed else "UNKNOWN"   # absence over 6s does not PROVE absence

    # ---------------- §五 M15 window ----------------
    m = NOW.minute
    phase = m % 15
    mins_to_next = (15 - phase) if phase else 15
    O["CURRENT_M15_PHASE"] = f"minute {m} within M15 bucket (phase={phase})"
    O["NEXT_V1_TRADING_WINDOW"] = (NOW.replace(minute=m - phase, second=0, microsecond=0)
                                    .timestamp() + mins_to_next * 60)
    O["NEXT_V1_TRADING_WINDOW"] = datetime.fromtimestamp(O["NEXT_V1_TRADING_WINDOW"], timezone.utc).isoformat()
    O["MINUTES_TO_NEXT_V1_CYCLE"] = mins_to_next
    O["M15_WINDOW"] = "UNKNOWN"      # the authoritative grid comes from the V1 task's schedule, not a guess

    # ---------------- §六 final determination ----------------
    checks = {"V1_PID_CONFIRMED": O["V1_PID_CONFIDENCE"] == "CONFIRMED",
               "PRIMARY_TASK_CONFIRMED": O["V1_PRIMARY_TASK"] not in ("UNKNOWN", None),
               "NO_ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"] == "NO",
               "OPEN_POSITIONS_ZERO": O["OPEN_POSITIONS"] == 0,
               "PENDING_ORDERS_ZERO": O["PENDING_ORDERS"] == 0,
               "NO_STATE_WRITE_IN_FLIGHT": O["STATE_WRITE_IN_FLIGHT"] == "NO",
               "NO_AUTO_RESTART_RACE": O["V1_AUTO_RESTART_MECHANISM"] == "NO",
               "OUTSIDE_TRADING_WINDOW": O["M15_WINDOW"] == "OUTSIDE_TRADING_WINDOW",
               "CURRENT_CYCLE_FINISHED": O["V1_CURRENT_CYCLE"] == "FINISHED"}
    O["SAFETY_CHECKS"] = checks
    O["SAFETY_WINDOW"] = "PROVEN" if all(checks.values()) else "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "YES" if O["SAFETY_WINDOW"] == "PROVEN" else "NO"
    O["UNKNOWN_FIELDS"] = [k for k, v in O.items() if v == "UNKNOWN"]

    # ---------------- research immutability + safety statement ----------------
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    O["research_immutability"] = imm
    O["TASK_STATUS"] = "READ_ONLY_SAFETY_AUDIT_COMPLETE"
    O["V1_MODIFIED"] = "NO"
    O["V2_MODIFIED"] = "NO"
    O["V3_MODIFIED"] = "NO"
    O["ORDER_SEND"] = 0
    O["COMMIT"] = "NONE"
    O["ts_utc"] = NOW.isoformat()
    json.dump(O, open(os.path.join(HERE, "V1_SAFETY_SWITCH_WINDOW_AUDIT_R2.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    print("\n=== §八 FINAL REPORT ===", flush=True)
    print(json.dumps({"TASK_STATUS": O["TASK_STATUS"], "V1_PID_CONFIRMED": checks["V1_PID_CONFIRMED"],
                        "V1_PRIMARY_TASK_CONFIRMED": checks["PRIMARY_TASK_CONFIRMED"],
                        "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
                        "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "CURRENT_CYCLE": O["V1_CURRENT_CYCLE"],
                        "STATE_WRITE_IN_FLIGHT": O["STATE_WRITE_IN_FLIGHT"],
                        "AUTO_RESTART_RACE": O["V1_AUTO_RESTART_MECHANISM"], "M15_WINDOW": O["M15_WINDOW"],
                        "SAFETY_WINDOW": O["SAFETY_WINDOW"], "NEXT_STAGE_AUTHORIZED": O["NEXT_STAGE_AUTHORIZED"],
                        "V1_MODIFIED": "NO", "V2_MODIFIED": "NO", "V3_MODIFIED": "NO", "ORDER_SEND": 0,
                        "COMMIT": "NONE"}, ensure_ascii=False, indent=1), flush=True)
    print("PID:", json.dumps({"confidence": O["V1_PID_CONFIDENCE"], "pid": O["V1_ENGINE_PID"],
                                "name": O["V1_ENGINE_PROCESS_NAME"], "parent": O["V1_ENGINE_PARENT_PID"],
                                "python": O["V1_PYTHON_PATH"], "count": O["V1_PROCESS_COUNT"]},
                               ensure_ascii=False)[:600], flush=True)
    print("TASKS:", json.dumps(O["V1_CRON_STATE"], ensure_ascii=False, default=str)[:900], flush=True)
    print("WRITE:", json.dumps({"activity": O["V1_CURRENT_WRITE_ACTIVITY"], "changed": O["currently_writing_files"],
                                 "newest": O["newest_state_files"]}, ensure_ascii=False, default=str)[:700], flush=True)
    print("M15:", json.dumps({"phase": O["CURRENT_M15_PHASE"], "next": O["NEXT_V1_TRADING_WINDOW"],
                                "mins": O["MINUTES_TO_NEXT_V1_CYCLE"], "window": O["M15_WINDOW"]},
                               ensure_ascii=False), flush=True)
    print("STATE:", json.dumps(O["trading_state_sources"], ensure_ascii=False, default=str)[:600], flush=True)
    print("CHECKS:", json.dumps(checks, ensure_ascii=False), flush=True)
    print("UNKNOWN_FIELDS:", O["UNKNOWN_FIELDS"][:12], flush=True)


if __name__ == "__main__":
    main()
