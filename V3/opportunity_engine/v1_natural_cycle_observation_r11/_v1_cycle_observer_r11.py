# -*- coding: utf-8 -*-
"""V1_NATURAL_M15_CYCLE_OBSERVATION_R11 — READ-ONLY natural cycle observer.

Waits for the NATURAL 15:32/15:47 UTC cycle (schedule 2-59/15 * * * 0-5), samples processes and runtime
files every 4s, records a UTC timeline, then a >=60s post-cycle stability window.
Absolutely no writes to V1/V2/V3; no trigger/stop/restart/kill; no MT5 query; no git write; no commit.
Writes only its own JSON/MD under this task's directory.
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
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
MAX_SECONDS = 660          # hard cap ~11 min
POLL = 4
STABLE_NEED = 60
SAMPLE_DIRS = [RUN, os.path.join(V1, "runtime"), os.path.join(V1, "state"), os.path.join(V1, "observations"),
                os.path.join(RUN, "tmp"), os.path.join(RUN, "decision_contexts"), os.path.join(V1, "memory", "reviews")]
WATCH_NAMED = ["state_package_latest.json", "plan_ledger.jsonl", "workflow_history.jsonl", "workflow_latest.json",
                "statistics.json", "trader_summary.txt", "state_package.json"]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {"task": "V1_NATURAL_M15_CYCLE_OBSERVATION_R11", "events": [], "timeline": {}}


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def sh(args, t=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def procs():
    """V1-related python/ps processes (read-only CIM query)."""
    out = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|state_package|engine.py'} | "
               "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress -Depth 4"])
    try:
        d = json.loads(out) if out and out.strip().startswith(("{", "[")) else []
        lst = d if isinstance(d, list) else [d]
        # drop self-matches: our own CIM query string contains the search pattern
        return [x for x in lst if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    except Exception:  # noqa: BLE001
        return []


def snapshot():
    files = {}
    for root in SAMPLE_DIRS:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                p = os.path.join(r_, f)
                try:
                    st = os.stat(p)
                    files[os.path.relpath(p, AIQ).replace("\\", "/")] = (st.st_size, round(st.st_mtime, 3))
                except OSError:
                    continue
    for f in WATCH_NAMED:
        p = os.path.join(RUN, f)
        if os.path.exists(p):
            try:
                st = os.stat(p)
                files[os.path.relpath(p, AIQ).replace("\\", "/")] = (st.st_size, round(st.st_mtime, 3))
            except OSError:
                pass
    return files


def src_digest(root):
    d = {}
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith((".py", ".yaml", ".yml")):
                p = os.path.join(r_, f)
                d[os.path.relpath(p, AIQ).replace("\\", "/")] = sha(p)
    return d


def automation_state():
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60)
    try:
        m = re.search(r"\{.*\}", out, re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        return {}


def log(kind, **kw):
    O["events"].append({"t": iso(), "kind": kind, **kw})
    print(f"[{iso()}] {kind} {json.dumps(kw, ensure_ascii=False)[:220]}", flush=True)


def main():
    os.makedirs(HERE, exist_ok=True)
    t0 = now()
    O["OBSERVATION_START_UTC"] = iso(t0)
    # baselines
    b_v1 = src_digest(V1)
    b_v2 = src_digest(V2)
    b_v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
             "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
             "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
             "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    O["BASELINE"] = {"V1_source_files": len(b_v1), "V2_source_files": len(b_v2), "V3_hashes": b_v3}
    a0 = automation_state()
    O["AUTOMATION_BEFORE"] = {k: a0.get(k) for k in ("id", "name", "enabled", "status", "state", "lastRunAtMs",
                                                       "nextRunAtMs", "lastRunStatus", "sessionTarget")}
    base_files = snapshot()
    base_procs = {p.get("ProcessId"): p for p in procs()}
    log("BASELINE", files=len(base_files), v1_procs=len(base_procs), nextRunAtMs=O["AUTOMATION_BEFORE"].get("nextRunAtMs"),
        schedule="2-59/15 * * * 0-5 @ UTC")

    seen_procs, first_change, last_change = {}, None, None
    cycle_start, cycle_start_evidence = None, None
    engine_first_seen, engine_exit = None, None
    started = time.time()
    prev = base_files
    poll_n = 0
    while time.time() - started < MAX_SECONDS:
        time.sleep(POLL)
        poll_n += 1
        tn = now()
        # processes
        cur_p = procs()
        cur_ids = {p.get("ProcessId") for p in cur_p}
        new_ids = cur_ids - set(base_procs) - set(seen_procs)
        gone = set(seen_procs) - cur_ids
        for pid in new_ids:
            p = next((x for x in cur_p if x.get("ProcessId") == pid), {})
            seen_procs[pid] = p
            log("PROCESS_START", pid=pid, ppid=p.get("ParentProcessId"), name=p.get("Name"),
                cmdline=(p.get("CommandLine") or "")[:200], creation=str(p.get("CreationDate")))
            if engine_first_seen is None:
                engine_first_seen = tn
                if cycle_start is None:
                    cycle_start, cycle_start_evidence = tn, "B_engine_process_appeared"
        for pid in gone:
            log("PROCESS_EXIT", pid=pid, name=(seen_procs.get(pid) or {}).get("Name"))
            if engine_exit is None:
                engine_exit = tn
        # files
        cur = snapshot()
        changed = [k for k in cur if k in prev and cur[k] != prev[k]]
        added = [k for k in cur if k not in prev]
        if changed or added:
            if first_change is None:
                first_change = tn
                if cycle_start is None:
                    cycle_start, cycle_start_evidence = tn, "C_runtime_file_changed"
            last_change = tn
            if poll_n % 3 == 0 or len(changed) < 6:
                log("FILE_CHANGE", changed=changed[:6], added=added[:4], n_changed=len(changed))
        prev = cur
        # cycle end detection
        if engine_first_seen and engine_exit and (tn - last_change).total_seconds() >= STABLE_NEED:
            break
        if int(time.time() - started) % 60 < POLL:
            print(f"… {iso()} poll={poll_n} procs={len(cur_ids)} changed_total={len(changed)}", flush=True)
    a1 = automation_state()
    O["AUTOMATION_AFTER"] = {k: a1.get(k) for k in ("id", "name", "enabled", "status", "state", "lastRunAtMs",
                                                      "nextRunAtMs", "lastRunStatus", "sessionTarget")}
    # stability window
    stab_start = now()
    s_prev = snapshot()
    stab_changes = []
    while (now() - stab_start).total_seconds() < STABLE_NEED:
        time.sleep(POLL)
        s_cur = snapshot()
        ch = [k for k in s_cur if k in s_prev and s_cur[k] != s_prev[k]]
        if ch:
            stab_changes += ch
        s_prev = s_cur
    post_procs = procs()
    O["POST_CYCLE_STABILITY_SECONDS"] = STABLE_NEED
    O["STATE_STABLE"] = "YES" if (not stab_changes and not post_procs) else "NO"
    # workflow tail (read-only)
    wf = os.path.join(RUN, "workflow_history.jsonl")
    tail = []
    if os.path.exists(wf):
        try:
            lines = [l for l in open(wf, encoding="utf-8") if l.strip()][-3:]
            for l in lines:
                try:
                    tail.append(json.loads(l))
                except Exception:  # noqa: BLE001
                    tail.append({"raw": l.strip()[:200]})
        except Exception:  # noqa: BLE001
            tail = []
    # verification
    a_v1, a_v2 = src_digest(V1), src_digest(V2)
    a_v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
             "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
             "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
             "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v1_chg = [k for k, v in b_v1.items() if a_v1.get(k) != v]
    v2_chg = [k for k, v in b_v2.items() if a_v2.get(k) != v]
    v3_ok = (a_v3["M01_event"] or "").startswith("ca44fd2c") and (a_v3["R1_ledger"] or "").startswith("d9cd6775") \
        and (a_v3["M01_audit"] or "").startswith("a3bee537") and (a_v3["R2_canonical"] or "").startswith("20913b98")
    lr0, lr1 = O["AUTOMATION_BEFORE"].get("lastRunAtMs"), O["AUTOMATION_AFTER"].get("lastRunAtMs")
    rep = {
        "TASK_STATUS": "V1_NATURAL_M15_CYCLE_OBSERVATION_R11_COMPLETE",
        "AUTOMATION_ID": AID, "AUTOMATION_NAME": "hermes-trader-m15-cycle",
        "CYCLE_OBSERVED": "YES" if (cycle_start and (engine_first_seen or last_change)) else ("PARTIAL" if cycle_start else "NO"),
        "CYCLE_START": "CONFIRMED" if cycle_start else "UNKNOWN",
        "CYCLE_START_EVIDENCE": cycle_start_evidence or "NONE",
        "CYCLE_END": ("CONFIRMED" if (engine_exit and last_change and (last_change <= engine_exit or (last_change - engine_exit).total_seconds() <= STABLE_NEED)) else
                       ("NOT_YET_STABLE" if (engine_exit and last_change and last_change > engine_exit) else "UNKNOWN")),
        "STATE_STABLE": O["STATE_STABLE"],
        "V1_ENGINE_PID": ",".join(str(p) for p in list(seen_procs.keys())[:5]) or "NOT_OBSERVED",
        "V1_ENGINE_START": iso(engine_first_seen) if engine_first_seen else "NOT_OBSERVED",
        "V1_ENGINE_END": iso(engine_exit) if engine_exit else "NOT_OBSERVED",
        "AUTOMATION_NATURAL_RUN": ("YES" if (lr1 and lr1 != lr0) else "UNKNOWN"),
        "AUTOMATION_LASTRUN_BEFORE": lr0, "AUTOMATION_LASTRUN_AFTER": lr1,
        "TRADING_HOURS_GATE_OBSERVED": "UNKNOWN",
        "STATE_PACKAGE_OBSERVED": ("YES" if any("state_package" in e.get("changed", []) or "state_package" in str(e)
                                                  for e in O["events"] if e["kind"] == "FILE_CHANGE") else "UNKNOWN"),
        "RUNTIME_FILE_CHANGES": sum(1 for e in O["events"] if e["kind"] == "FILE_CHANGE"),
        "LEDGER_CHANGE": "YES" if any("ledger" in str(e) for e in O["events"] if e["kind"] == "FILE_CHANGE") else "UNKNOWN",
        "DELAYED_WRITES": "YES" if O["STATE_STABLE"] == "NO" else "NO",
        "POST_CYCLE_STABILITY_SECONDS": STABLE_NEED,
        "RESPAWN_OBSERVED": "YES" if any(e["kind"] == "PROCESS_START" and e["t"] > (iso(engine_exit) if engine_exit else ""))
                              else "NO",
        "RETRY_OBSERVED": "UNKNOWN",
        "OPEN_POSITIONS": "NOT_REQUERIED", "PENDING_ORDERS": "NOT_REQUERIED",
        "V1_SOURCE_CONFIG_MODIFIED": "YES" if v1_chg else "NO", "V1_CHANGED_FILES": v1_chg[:5],
        "V2_SOURCE_CONFIG_MODIFIED": "YES" if v2_chg else "NO",
        "V3_RESEARCH_MODIFIED": "NO" if v3_ok else "YES",
        "V3_HASHES": a_v3,
        "ORDER_SEND": 0, "COMMIT": "NONE",
        "SAFETY_WINDOW": "NOT_PROVEN", "NEXT_STAGE_AUTHORIZED": "NO",
        "poll_count": poll_n, "observation_seconds": round((now() - t0).total_seconds(), 1),
        "timeline": {"T0_observation_start": iso(t0), "T1_automation_natural_trigger": iso(cycle_start) if cycle_start else "NOT_OBSERVED",
                       "T2_trading_hours_gate": "NOT_OBSERVED", "T3_state_package": "NOT_OBSERVED",
                       "T4_engine_appeared": iso(engine_first_seen) if engine_first_seen else "NOT_OBSERVED",
                       "T5_runtime_first_change": iso(first_change) if first_change else "NOT_OBSERVED",
                       "T6_decision_plan": "NOT_OBSERVED", "T7_last_runtime_change": iso(last_change) if last_change else "NOT_OBSERVED",
                       "T8_engine_exit": iso(engine_exit) if engine_exit else "NOT_OBSERVED",
                       "T9_automation_complete": "NOT_OBSERVED", "T10_stability_window_end": iso(now())},
        "workflow_tail": tail, "events": O["events"],
        "ts_utc": iso(),
    }
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_NATURAL_M15_CYCLE_OBSERVATION_R11.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    md = ["# V1 自然 M15 周期观察 R11", "", f"`{iso()}`", "", "```text"]
    for k in ("TASK_STATUS", "AUTOMATION_ID", "AUTOMATION_NAME", "CYCLE_OBSERVED", "CYCLE_START", "CYCLE_END",
                "STATE_STABLE", "V1_ENGINE_PID", "V1_ENGINE_START", "V1_ENGINE_END", "AUTOMATION_NATURAL_RUN",
                "TRADING_HOURS_GATE_OBSERVED", "STATE_PACKAGE_OBSERVED", "RUNTIME_FILE_CHANGES", "LEDGER_CHANGE",
                "DELAYED_WRITES", "POST_CYCLE_STABILITY_SECONDS", "RESPAWN_OBSERVED", "RETRY_OBSERVED",
                "OPEN_POSITIONS", "PENDING_ORDERS", "V1_SOURCE_CONFIG_MODIFIED", "V2_SOURCE_CONFIG_MODIFIED",
                "V3_RESEARCH_MODIFIED", "ORDER_SEND", "COMMIT", "SAFETY_WINDOW", "NEXT_STAGE_AUTHORIZED"):
        md.append(f"{k} = {rep.get(k)}")
    md += ["```", "", "## 时间线", "", "```text"] + [f"{k} = {v}" for k, v in rep["timeline"].items()] + \
          ["```", "", "## 事件流", "", "```text"] + [f"{e['t']} {e['kind']} {json.dumps({k: v for k, v in e.items() if k not in ('t','kind')}, ensure_ascii=False)[:200]}" for e in O["events"][:200]] + ["```"]
    open(os.path.join(HERE, "V1_NATURAL_M15_CYCLE_OBSERVATION_R11.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("\n=== §13 FINAL REPORT ===", flush=True)
    print(json.dumps({k: rep.get(k) for k in ("TASK_STATUS", "CYCLE_OBSERVED", "CYCLE_START", "CYCLE_END", "STATE_STABLE",
                                                  "V1_ENGINE_PID", "V1_ENGINE_START", "V1_ENGINE_END",
                                                  "AUTOMATION_NATURAL_RUN", "AUTOMATION_LASTRUN_BEFORE",
                                                  "AUTOMATION_LASTRUN_AFTER", "RUNTIME_FILE_CHANGES", "LEDGER_CHANGE",
                                                  "DELAYED_WRITES", "RESPAWN_OBSERVED", "V1_SOURCE_CONFIG_MODIFIED",
                                                  "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED", "ORDER_SEND",
                                                  "COMMIT", "SAFETY_WINDOW", "NEXT_STAGE_AUTHORIZED",
                                                  "observation_seconds", "poll_count")}, ensure_ascii=False, indent=1)[:2200], flush=True)
    print("TIMELINE:", json.dumps(rep["timeline"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
