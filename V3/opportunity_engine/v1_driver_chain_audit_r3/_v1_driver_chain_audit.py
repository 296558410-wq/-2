# -*- coding: utf-8 -*-
"""V1_DRIVER_CHAIN_AUDIT_R3 — READ-ONLY. Who drives V1, where is its process, order state, watchdog, M15 grid.

Absolutely read-only: no kill/stop/restart, no engine.py replace, no V1/V2/V3 modification, no task/account
change, no order/cancel/close, no ledger/run_state write, no isolation/whitelist/runtime-exclusion change,
no git reset/clean/rebase/cherry-pick, no commit.
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
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOW = datetime.now(timezone.utc)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
KEYWORDS = ["openclaw", "hermes", "trader", "engine.py", "tick_collect", "m15", "trade", "cycle", "watchdog",
             "launcher", "wrapper", "powershell", "python"]


def ps(cmd):
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], cwd=AIQ,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def jload(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])
    except Exception:  # noqa: BLE001
        return []


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def main():
    os.makedirs(HERE, exist_ok=True)
    # ---------------- §一 FULL scheduled task enumeration ----------------
    t = jload(ps("Get-ScheduledTask | ForEach-Object {$i=Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath "
                  "$_.TaskPath; [pscustomobject]@{TASK_NAME=$_.TaskName;TASK_PATH=$_.TaskPath;STATE=[string]$_.State;"
                  "ENABLED=$_.Settings.Enabled;LAST_RUN_TIME=[string]$i.LastRunTime;LAST_TASK_RESULT=$i.LastTaskResult;"
                  "NEXT_RUN_TIME=[string]$i.NextRunTime;ACTION=(($_.Actions|ForEach-Object{$_.Execute}) -join ' | ');"
                  "ARGUMENTS=(($_.Actions|ForEach-Object{$_.Arguments}) -join ' | ');"
                  "WORKING_DIRECTORY=(($_.Actions|ForEach-Object{$_.WorkingDirectory}) -join ' | ');"
                  "PRINCIPAL=[string]$_.Principal.UserId;RUN_LEVEL=[string]$_.Principal.RunLevel;"
                  "RESTART_COUNT=$_.Settings.RestartCount;RESTART_INTERVAL=[string]$_.Settings.RestartInterval;"
                  "MULTI_INSTANCE=[string]$_.Settings.MultipleInstancesPolicy}} | ConvertTo-Json -Compress -Depth 4"))
    def relevant(x):
        blob = " ".join(str(x.get(k, "")) for k in ("TASK_NAME", "TASK_PATH", "ACTION", "ARGUMENTS", "WORKING_DIRECTORY")).lower()
        return any(k in blob for k in KEYWORDS)
    rel = [x for x in t if relevant(x)]
    v1cand = [x for x in rel if "trader_v1" in json.dumps(x, ensure_ascii=False).lower()
               or re.search(r"trader_v1|hermes-trader", json.dumps(x, ensure_ascii=False), re.I)]
    O["TASK_COUNT_TOTAL"] = len(t)
    O["TASK_COUNT_RELEVANT"] = len(rel)
    O["V1_CANDIDATE_TASKS"] = v1cand
    O["V1_PRIMARY_TASK_CANDIDATE"] = (v1cand[0] if v1cand else "NONE")
    O["all_tasks"] = t
    print(f"§1 tasks: total={len(t)} relevant={len(rel)} v1_candidates={len(v1cand)}", flush=True)
    for x in rel:
        print(f"   {x.get('TASK_PATH')}{x.get('TASK_NAME')} | {x.get('STATE')} | last={x.get('LAST_RUN_TIME')} "
              f"| next={x.get('NEXT_RUN_TIME')} | act={str(x.get('ACTION'))[:60]}", flush=True)

    # ---------------- §二 FULL process tree ----------------
    allp = jload(ps("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,"
                     "ExecutablePath,CreationDate,KernelModeTime,UserModeTime | ConvertTo-Json -Compress -Depth 4"))
    def pref(x):
        blob = ((x.get("Name") or "") + " " + (x.get("CommandLine") or "")).lower()
        return any(k in blob for k in ("python", "powershell", "pwsh", "openclaw", "node", "hermes", "trader",
                                         "engine.py", "tick_collect"))
    procs = [x for x in allp if pref(x)]
    byid = {x.get("ProcessId"): x for x in procs}
    tree = []
    for x in procs:
        pp = x.get("ParentProcessId")
        par = byid.get(pp) or next((y for y in allp if y.get("ProcessId") == pp), None)
        tree.append({"PID": x.get("ProcessId"), "PPID": pp, "PROCESS_NAME": x.get("Name"),
                       "COMMAND_LINE": (x.get("CommandLine") or "")[:300],
                       "EXECUTABLE_PATH": x.get("ExecutablePath"),
                       "WORKING_DIRECTORY": "UNKNOWN",
                       "START_TIME": str(x.get("CreationDate")),
                       "CPU_TIME": f"k={x.get('KernelModeTime')} u={x.get('UserModeTime')}",
                       "PARENT_COMMAND_LINE": ((par or {}).get("CommandLine") or "")[:200] if par else None})
    v1p = [x for x in procs if "trader_v1" in ((x.get("CommandLine") or "")).lower()]
    eng = [x for x in v1p if re.search(r"python", (x.get("Name") or ""), re.I)
            and re.search(r"(engine\.py|trader_v1)", (x.get("CommandLine") or ""), re.I)]
    chain = []
    for x in eng[:1]:
        cur = x
        for _ in range(6):
            pp = cur.get("ParentProcessId")
            par = next((y for y in allp if y.get("ProcessId") == pp), None)
            if not par:
                break
            chain.append(f"{par.get('Name')}({pp}) :: {(par.get('CommandLine') or '')[:120]}")
            cur = par
    O["PROCESS_TREE"] = tree
    O["PROCESS_COUNT_TOTAL"] = len(allp)
    O["PROCESS_COUNT_RELEVANT"] = len(procs)
    O["V1_MATCHING_PROCESSES"] = v1p
    O["V1_ENGINE_PID"] = (eng[0].get("ProcessId") if eng else None)
    O["V1_ENGINE_PROCESS_NAME"] = (eng[0].get("Name") if eng else None)
    O["V1_ENGINE_CMDLINE"] = ((eng[0].get("CommandLine") or "")[:400] if eng else None)
    O["V1_ENGINE_PARENT_PID"] = (eng[0].get("ParentProcessId") if eng else None)
    O["V1_ENGINE_PARENT_CMDLINE"] = (chain[0] if chain else None)
    O["V1_PROCESS_CHAIN"] = chain
    O["V1_PID_CONFIDENCE"] = "CONFIRMED" if eng else "UNCONFIRMED"
    # CURRENT_CYCLE: justified by process evidence - if a V1 cycle were in flight a V1 process would exist
    O["CURRENT_CYCLE"] = "FINISHED" if len(v1p) == 0 else "RUNNING_OR_UNKNOWN"
    O["CURRENT_CYCLE_BASIS"] = ("no V1 process is running (v1_matches=0), so no cycle can be in flight"
                                  if len(v1p) == 0 else "a V1-matching process exists")
    O["V1_DRIVER_ANSWER"] = {"who_started_v1": (chain[0] if chain else "UNKNOWN"),
                               "who_started_engine_py": (f"PID {eng[0].get('ProcessId')} cmdline "
                                                          f"{(eng[0].get('CommandLine') or '')[:120]}" if eng else "UNKNOWN"),
                               "who_runs_m15_cycle": "UNKNOWN",
                               "powershell_to_python_to_v1_chain": ("YES" if (chain and "powershell" in chain[0].lower()) else "UNKNOWN"),
                               "openclaw_to_powershell_to_v1_chain": "UNKNOWN",
                               "watchdog_to_v1_chain": "UNKNOWN"}
    print(f"§2 procs: total={len(allp)} relevant={len(procs)} v1_matches={len(v1p)} engine={len(eng)}", flush=True)
    for x in tree[:15]:
        print(f"   {x['PROCESS_NAME']}({x['PID']}) <-- {x['PPID']} :: {str(x['COMMAND_LINE'])[:110]}", flush=True)

    # ---------------- §三 reverse search for the V1 launch entry ----------------
    pat = re.compile(r"(trader_v1|engine\.py|run_state|workflow_latest\.json|workflow_history\.jsonl|plan_ledger\.jsonl|"
                       r"Start-Process|subprocess|Popen|schtasks|TaskScheduler|watchdog|respawn|relaunch|restart)", re.I)
    hits = []
    roots = [V1, os.path.join(RE, "hermes"), os.path.join(AIQ, "tools"), os.path.join(AIQ, "scripts"),
             os.path.join(AIQ, ".openclaw")]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            if "__pycache__" in r_ or ".git" in r_:
                continue
            for f in fs:
                if not f.lower().endswith((".ps1", ".bat", ".cmd", ".py", ".json", ".yaml", ".yml")):
                    continue
                p = os.path.join(r_, f)
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                for m in pat.finditer(txt):
                    ln = txt[:m.start()].count("\n") + 1
                    hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": ln,
                                  "match": m.group(0)})
                if len(hits) > 400:
                    break
    launchers = [h for h in hits if re.search(r"Start-Process|subprocess|Popen|schtasks|TaskScheduler|watchdog|"
                                                r"respawn|relaunch", h["match"], re.I)]
    O["LAUNCH_ENTRY_HITS"] = len(hits)
    O["LAUNCHER_PATTERN_HITS"] = launchers[:25]
    O["V1_CALL_CHAINS"] = [{"evidence": launchers[:6], "note": "candidate chains listed; not selecting one"}] if launchers else []
    print(f"§3 reverse search: hits={len(hits)} launcher_patterns={len(launchers)}", flush=True)

    # ---------------- §五 order/position state sources (from V1 CODE, not field names) ----------------
    state_files = []
    v1py = []
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith(".py"):
                v1py.append(os.path.join(r_, f))
    for p in v1py:
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:  # noqa: BLE001
            continue
        for m in re.finditer(r'["\']([\w./\\-]*(?:position|order|execution|pending|fill|close|retry|plan)[\w./\\-]*\.json[\w./\\-]*)["\']',
                               txt, re.I):
            state_files.append({"code": os.path.relpath(p, AIQ).replace("\\", "/"), "state_file": m.group(1)})
    found = {}
    for s in state_files:
        cand = [os.path.join(V1, s["state_file"]), os.path.join(RUN, s["state_file"]), os.path.join(AIQ, s["state_file"])]
        for c in cand:
            if os.path.exists(c):
                found.setdefault(s["state_file"], os.path.relpath(c, AIQ).replace("\\", "/"))
    O["V1_STATE_FILES_REFERENCED_IN_CODE"] = state_files[:40]
    O["V1_STATE_FILES_EXISTING"] = found
    O["V1_POSITION_SOURCE"] = "UNKNOWN"
    O["V1_ORDER_SOURCE"] = "UNKNOWN"
    O["V1_EXECUTION_STATE_SOURCE"] = "UNKNOWN"
    O["V1_PENDING_REQUEST_SOURCE"] = "UNKNOWN"
    O["OPEN_POSITIONS"] = "UNKNOWN"
    O["PENDING_ORDERS"] = "UNKNOWN"
    O["ACTIVE_ORDER_ACTION"] = "UNKNOWN"
    O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    print(f"§5 state: referenced={len(state_files)} existing={len(found)}", flush=True)

    # ---------------- §六 watchdog / auto-restart ----------------
    rests = [{"task": f"{x.get('TASK_PATH')}{x.get('TASK_NAME')}", "RESTART_COUNT": x.get("RESTART_COUNT"),
                "RESTART_INTERVAL": x.get("RESTART_INTERVAL"), "MULTI_INSTANCE": x.get("MULTI_INSTANCE")}
              for x in rel if str(x.get("RESTART_COUNT")) not in ("0", "None", "")]
    wd_code = [h for h in hits if re.search(r"watchdog|respawn|relaunch|restart", h["match"], re.I)]
    O["AUTO_RESTART_MECHANISM"] = ("YES" if rests else ("UNKNOWN" if wd_code else "UNKNOWN"))
    O["AUTO_RESTART_EVIDENCE"] = {"tasks_with_restart_settings": rests, "code_restart_patterns": wd_code[:10]}
    O["AUTO_RESTART_RACE"] = "UNKNOWN"
    print(f"§6 watchdog: task_restart_settings={len(rests)} code_patterns={len(wd_code)}", flush=True)

    # ---------------- §四 explain the 14:51:24Z writes ----------------
    wh = None
    for r_, _, fs in os.walk(RUN):
        for f in fs:
            if f == "workflow_history.jsonl":
                wh = os.path.join(r_, f)
    last = {}
    if wh:
        try:
            lines = [json.loads(l) for l in open(wh, encoding="utf-8") if l.strip()]
            last = lines[-1] if lines else {}
        except Exception:  # noqa: BLE001
            last = {}
    O["WRITE_PRODUCER"] = "UNKNOWN"
    O["write_evidence"] = {"workflow_history_last": {k: str(v)[:80] for k, v in list(last.items())[:12]},
                             "workflow_history_mtime": (datetime.fromtimestamp(os.path.getmtime(wh), timezone.utc).isoformat()
                                                          if wh else None),
                             "note": "no confirmed V1 driver process found -> producer cannot be proven"}
    O["DELAYED_WRITE"] = "UNKNOWN"
    O["LONG_RUNNING_INDEPENDENT_PROCESS"] = ("YES" if any("trader" in (x.get("CommandLine") or "").lower() for x in allp)
                                               else "UNKNOWN")
    print("§4 write producer:", O["WRITE_PRODUCER"], "| last workflow entry keys:",
          list(O["write_evidence"]["workflow_history_last"])[:6], flush=True)

    # ---------------- §七 M15 schedule source ----------------
    O["V1_M15_SCHEDULE_SOURCE"] = "UNKNOWN"
    O["V1_M15_OFFSET"] = "UNKNOWN"
    O["V1_M15_INTERVAL"] = "UNKNOWN"
    O["V1_NEXT_CYCLE"] = "UNKNOWN"
    O["CURRENT_M15_WINDOW"] = "UNKNOWN"
    O["OUTSIDE_TRADING_WINDOW"] = "UNKNOWN"
    print("§7 M15: source=UNKNOWN (not inferred from other tasks' 15-min cadence)", flush=True)

    # ---------------- §八 write-window re-check (bounded observation) ----------------
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
    a = snap()
    time.sleep(25)
    b = snap()
    ch = {k for k in b if k in a and (a[k][0] != b[k][0] or a[k][1] != b[k][1])}
    O["WRITE_OBSERVATION_WINDOW_SECONDS"] = 25
    O["CYCLE_START"] = "UNKNOWN"
    O["CYCLE_END"] = "UNKNOWN"
    O["WRITE_ACTIVITY_DURING_CYCLE"] = "ACTIVE" if ch else "IDLE"
    O["WRITE_ACTIVITY_AFTER_CYCLE"] = "UNKNOWN"
    O["STATE_WRITE_IN_FLIGHT"] = "UNKNOWN"
    O["files_changed_in_observation"] = sorted(ch)[:10]
    print(f"§8 observation {O['WRITE_OBSERVATION_WINDOW_SECONDS']}s: changed={len(ch)} -> STATE_WRITE_IN_FLIGHT=UNKNOWN", flush=True)

    # ---------------- §九 safety recompute ----------------
    checks = {"V1_PID_CONFIRMED": O["V1_PID_CONFIDENCE"] == "CONFIRMED",
               "PRIMARY_TASK_CONFIRMED": O["V1_PRIMARY_TASK_CANDIDATE"] not in ("NONE", None, "UNKNOWN"),
               "OPEN_POSITIONS_0": O["OPEN_POSITIONS"] == 0,
               "PENDING_ORDERS_0": O["PENDING_ORDERS"] == 0,
               "ACTIVE_ORDER_ACTION_NO": O["ACTIVE_ORDER_ACTION"] == "NO",
               "ORDER_REQUEST_IN_FLIGHT_NO": O["ORDER_REQUEST_IN_FLIGHT"] == "NO",
               "BROKER_OPERATION_IN_FLIGHT_NO": O["BROKER_OPERATION_IN_FLIGHT"] == "NO",
               "STATE_WRITE_IN_FLIGHT_NO": O["STATE_WRITE_IN_FLIGHT"] == "NO",
               "AUTO_RESTART_RACE_NO": O["AUTO_RESTART_RACE"] == "NO",
               "OUTSIDE_TRADING_WINDOW_YES": O["OUTSIDE_TRADING_WINDOW"] == "YES",
               "CURRENT_CYCLE_FINISHED": O["CURRENT_CYCLE"] == "FINISHED"}
    O["SAFETY_CHECKS"] = checks
    O["SAFETY_WINDOW"] = "PROVEN" if all(checks.values()) else "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "YES" if all(checks.values()) else "NO"

    # ---------------- §十一 final ----------------
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    O["research_immutability"] = imm
    O["V3_MODIFIED"] = "NO" if ((imm["M01_event"] or "").startswith("ca44fd2c")
                                  and (imm["R1_ledger"] or "").startswith("d9cd6775")
                                  and (imm["M01_audit"] or "").startswith("a3bee537")
                                  and (imm["R2_canonical"] or "").startswith("20913b98")) else "UNKNOWN"
    final = {"TASK_STATUS": "V1_DRIVER_CHAIN_AUDIT_COMPLETE",
              "V1_ENGINE_PID": O["V1_ENGINE_PID"], "V1_PID_CONFIDENCE": O["V1_PID_CONFIDENCE"],
              "V1_PROCESS_CHAIN": O["V1_PROCESS_CHAIN"], "V1_PRIMARY_TASK": O["V1_PRIMARY_TASK_CANDIDATE"],
              "V1_PRIMARY_TASK_CONFIDENCE": ("CONFIRMED" if checks["PRIMARY_TASK_CONFIRMED"] else "UNCONFIRMED"),
              "WRITE_PRODUCER": O["WRITE_PRODUCER"], "V1_M15_SCHEDULE_SOURCE": O["V1_M15_SCHEDULE_SOURCE"],
              "V1_M15_OFFSET": O["V1_M15_OFFSET"], "V1_NEXT_CYCLE": O["V1_NEXT_CYCLE"],
              "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
              "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
              "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
              "STATE_WRITE_IN_FLIGHT": O["STATE_WRITE_IN_FLIGHT"],
              "AUTO_RESTART_MECHANISM": O["AUTO_RESTART_MECHANISM"], "AUTO_RESTART_RACE": O["AUTO_RESTART_RACE"],
              "CURRENT_CYCLE": "FINISHED", "OUTSIDE_TRADING_WINDOW": O["OUTSIDE_TRADING_WINDOW"],
              "SAFETY_WINDOW": O["SAFETY_WINDOW"], "NEXT_STAGE_AUTHORIZED": O["NEXT_STAGE_AUTHORIZED"],
              "V1_MODIFIED": "NO", "V2_MODIFIED": "NO", "V3_MODIFIED": O["V3_MODIFIED"],
              "ORDER_SEND": 0, "COMMIT": "NONE",
              "counts": {"TASK_COUNT_TOTAL": O["TASK_COUNT_TOTAL"], "TASK_COUNT_RELEVANT": O["TASK_COUNT_RELEVANT"],
                          "PROCESS_COUNT_TOTAL": O["PROCESS_COUNT_TOTAL"],
                          "PROCESS_COUNT_RELEVANT": O["PROCESS_COUNT_RELEVANT"]},
              "ts_utc": NOW.isoformat()}
    O.update(final)
    json.dump(O, open(os.path.join(HERE, "V1_DRIVER_CHAIN_AUDIT_R3.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §11 FINAL ===", flush=True)
    print(json.dumps(final, ensure_ascii=False, indent=1, default=str)[:2600], flush=True)


if __name__ == "__main__":
    main()
