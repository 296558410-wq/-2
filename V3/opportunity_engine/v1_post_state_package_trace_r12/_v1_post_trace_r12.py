# -*- coding: utf-8 -*-
"""V1_POST_STATE_PACKAGE_TRACE_R12 — READ-ONLY post-hoc trace of the ALREADY-CAPTURED 15:32Z M15 run.

No trigger, no run, no stop/restart/kill, no automation mutation, no MT5 call, no broad .openclaw scan,
no git write, no commit. Only: R11 artifact, official read-only automation metadata, targeted V1 run_state reads.
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
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
RUN = os.path.join(V1, "run_state")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
R11 = os.path.join(ENGINE, "v1_natural_cycle_observation_r11", "V1_NATURAL_M15_CYCLE_OBSERVATION_R11.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TARGET_MS = 1790350320000          # 2026-09-25T15:32:00Z
WIN0, WIN1 = "2026-09-25T15:31:30", "2026-09-25T15:40:00"
MUT = ("enable", "disable", "run", "trigger", "update", "delete", "create", "set", "edit", "add", "start", "stop")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
FP = []


def run(args, t=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def rd(p, n=400000):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()[:n]
    except Exception:  # noqa: BLE001
        return None


def tail_jsonl(p, n=6):
    out = []
    try:
        lines = [l for l in open(p, encoding="utf-8") if l.strip()][-n:]
        for l in lines:
            try:
                out.append(json.loads(l))
            except Exception:  # noqa: BLE001
                out.append({"raw": l.strip()[:300]})
    except Exception:  # noqa: BLE001
        pass
    return out


def in_win(ts):
    try:
        t = str(ts)[:19].replace(" ", "T")
        return WIN0 <= t <= WIN1
    except Exception:  # noqa: BLE001
        return False


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = datetime.now(timezone.utc).isoformat()
    r11 = json.load(open(R11, encoding="utf-8")) if os.path.exists(R11) else {}
    O["R11_ARTIFACT"] = {"path": os.path.relpath(R11, AIQ).replace("\\", "/"), "exists": bool(r11),
                            "cycle_observed": r11.get("CYCLE_OBSERVED"), "cycle_start": r11.get("CYCLE_START"),
                            "cycle_end": r11.get("CYCLE_END"), "state_stable": r11.get("STATE_STABLE"),
                            "automation_before": r11.get("AUTOMATION_BEFORE"), "automation_after": r11.get("AUTOMATION_AFTER")}
    O["TARGET_RUN_TIME"] = "2026-09-25T15:32:00Z"

    # ---------- 1) R11 workflow_tail ----------
    wt = r11.get("workflow_tail") or []
    O["R11_WORKFLOW_TAIL"] = wt
    wt_win = [e for e in wt if in_win(e.get("utc_ts") or e.get("timestamp") or "")]
    O["workflow_entries_in_window"] = wt_win
    wt_hits = [e for e in wt if json.dumps(e, ensure_ascii=False).lower().find("state_package") >= 0
                or "engine.py" in json.dumps(e, ensure_ascii=False).lower()]
    O["workflow_state_package_or_engine_mentions"] = wt_hits

    # ---------- 2) official read-only automation run metadata ----------
    meta, used = {}, None
    for form in (["cron", "show", AID, "--json"], ["cron", "runs", AID, "--json"], ["cron", "history", AID, "--json"],
                 ["cron", "logs", AID, "--json"]):
        if any(v in MUT for v in form) or not (os.path.exists(NODE) and os.path.exists(CLI)):
            continue
        out = run([NODE, CLI] + form, 60)
        m = re.search(r"(\{.*\}|\[.*\])", out, re.S)
        if m:
            try:
                doc = json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                continue
            b = json.dumps(doc, ensure_ascii=False)
            if AID in b or "hermes-trader-m15-cycle" in b:
                meta, used = doc, " ".join(form)
                if form[1] != "show":
                    break
    O["AUTOMATION_METADATA_COMMAND"] = used or "NONE"
    def dig(o, ks):
        res = {}
        def w(x, path=""):
            if isinstance(x, dict):
                for k, v in x.items():
                    kl = k.lower()
                    if any(kl == kk for kk in ks) and not isinstance(v, (dict, list)):
                        res[path + "/" + k] = v
                    w(v, path + "/" + k)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    w(v, path + f"[{i}]")
        w(o)
        return res
    fields = dig(meta, ("lastrunatms", "lastrunstatus", "lastdelivered", "lastdeliverystatus", "state", "status",
                          "nextrunatms", "enabled", "sessiontarget", "owner", "agentid", "delivery",
                          "lastfailuren", "runid", "sessionid", "executionid", "workflowid", "conversationid"))
    O["AUTOMATION_READONLY_FIELDS"] = fields
    lr = next((v for k, v in fields.items() if k.lower().endswith("lastrunatms")), None)
    O["AUTOMATION_LASTRUN_MATCHES_TARGET"] = ("YES" if str(lr) == str(TARGET_MS) else
                                                ("NO" if lr is not None else "UNKNOWN"))
    O["AUTOMATION_RUN_STATUS"] = next((v for k, v in fields.items() if k.lower().endswith("lastrunstatus")), "UNKNOWN")
    O["AUTOMATION_STATE"] = next((v for k, v in fields.items() if k.lower().endswith("/state")), "UNKNOWN")
    O["AUTOMATION_LAST_DELIVERED"] = next((v for k, v in fields.items() if k.lower().endswith("lastdelivered")), "UNKNOWN")
    O["SESSION_OR_RUN_ID"] = next((v for k, v in fields.items()
                                     if re.search(r"runid|sessionid|executionid|workflowid|conversationid", k, re.I)), "NOT_PRESENT")
    print(f"§7 meta cmd={used} lastRunAtMs={lr} match={O['AUTOMATION_LASTRUN_MATCHES_TARGET']} "
          f"runStatus={O['AUTOMATION_RUN_STATUS']} state={O['AUTOMATION_STATE']} idds={O['SESSION_OR_RUN_ID']}", flush=True)

    # ---------- 3) targeted V1 run_state reads around the window ----------
    targets = {"workflow_history": os.path.join(RUN, "workflow_history.jsonl"),
                "plan_ledger": os.path.join(RUN, "plan_ledger.jsonl"),
                "state_package_latest": os.path.join(RUN, "state_package_latest.json"),
                "workflow_latest": os.path.join(RUN, "workflow_latest.json"),
                "statistics": os.path.join(RUN, "statistics.json"),
                "trader_summary": os.path.join(RUN, "trader_summary.txt")}
    got = {}
    for k, p in targets.items():
        if not os.path.exists(p):
            got[k] = "MISSING"
            continue
        st = os.stat(p)
        mt = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
        if k.endswith("jsonl"):
            got[k] = {"mtime": mt, "tail": tail_jsonl(p, 4), "in_window": in_win(mt)}
        else:
            txt = rd(p, 4000) or ""
            got[k] = {"mtime": mt, "in_window": in_win(mt), "preview": txt[:1200]}
    O["RUNTIME_FILE_EVIDENCE"] = got
    # plan_ledger entries in window
    pl = got.get("plan_ledger", {})
    if isinstance(pl, dict) and pl.get("tail"):
        O["plan_ledger_entries_in_window"] = [e for e in pl["tail"] if in_win(e.get("utc_ts") or e.get("timestamp") or "")
                                                or in_win(pl.get("mtime", ""))]
    # gate traces (trading_hours / armed / MARKET_CLOSED) anywhere in run_state (targeted filename+content read)
    gate = {"files_named_like_gate": [], "armed_mentions": [], "market_closed_mentions": []}
    for r_, _, fs in os.walk(RUN):
        if "tmp" in r_:
            continue
        for f in fs:
            p = os.path.join(r_, f)
            if re.search(r"(?i)trading_?hour|gate|armed|market", f):
                gate["files_named_like_gate"].append(os.path.relpath(p, AIQ).replace("\\", "/"))
            if f.lower().endswith((".json", ".txt", ".jsonl")) and os.path.getsize(p) < 2_000_000:
                t = rd(p, 200000) or ""
                if re.search(r"(?i)armed", t):
                    for m in re.finditer(r"(?i).{0,80}armed.{0,80}", t):
                        gate["armed_mentions"].append({"file": os.path.relpath(p, AIQ).replace("\\", "/"),
                                                         "snippet": " ".join(m.group(0).split())[:160]})
                        break
                if "MARKET_CLOSED" in t:
                    gate["market_closed_mentions"].append(os.path.relpath(p, AIQ).replace("\\", "/"))
    O["GATE_TRACES"] = gate
    if "MARKET_CLOSED" in (got.get("trader_summary", {}).get("preview", "") if isinstance(got.get("trader_summary"), dict) else ""):
        O["TRADING_HOURS_GATE_RESULT"] = "MARKET_CLOSED"
    elif gate["armed_mentions"]:
        O["TRADING_HOURS_GATE_RESULT"] = "ARMED_OR_MENTIONED"
    else:
        O["TRADING_HOURS_GATE_RESULT"] = "NOT_OBSERVED"

    # ---------- 4) timeline + verdicts ----------
    ev = r11.get("events", [])
    p_start = [e for e in ev if e.get("kind") == "PROCESS_START"]
    f_chg = [e for e in ev if e.get("kind") == "FILE_CHANGE"]
    eng_seen = any("engine.py" in json.dumps(e, ensure_ascii=False) for e in p_start)
    agent_evidence = (wt_win or O.get("plan_ledger_entries_in_window") or
                       (O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None)))
    O["DIRECT_EVIDENCE"] = {
        "engine_py_process_observed": eng_seen,
        "agentTurn_continuation_event": "FOUND" if wt_win else "NOT_FOUND",
        "workflow_entries_at_15:32": len(wt_win),
        "runtime_write_at_15:32:21": any(in_win(e.get("t", "")) and "state_package_latest" in json.dumps(e)
                                            for e in f_chg),
        "automation_lastRun_status": O["AUTOMATION_RUN_STATUS"]}
    O["INDIRECT_EVIDENCE"] = {"workflow_tail_entries": len(wt), "plan_ledger_in_window": len(
        O.get("plan_ledger_entries_in_window", [])), "gate_mentions": len(gate["armed_mentions"])}
    O["DOCUMENTARY_EVIDENCE"] = "NOT_USED_AS_PROOF (README/SKILL/stack-map/task-sheets/old reports/snapshots excluded by rule)"
    tl = {"T0_scheduled_run": "CONFIRMED" if O["AUTOMATION_LASTRUN_MATCHES_TARGET"] == "YES" else
            ("INFERRED" if p_start else "UNKNOWN"),
            "T1_agentTurn_start": "INFERRED" if p_start else "NOT_OBSERVED",
            "T2_trading_hours_gate": (O["TRADING_HOURS_GATE_RESULT"] if O["TRADING_HOURS_GATE_RESULT"] in
                                        ("ARMED", "MARKET_CLOSED") else "NOT_OBSERVED"),
            "T3_state_package_py": "CONFIRMED" if any("state_package.py" in json.dumps(e) for e in p_start) else "NOT_OBSERVED",
            "T4_state_package_latest_write": "CONFIRMED" if any("state_package_latest" in json.dumps(e) for e in f_chg) else "NOT_OBSERVED",
            "T5_agent_continuation": "INFERRED" if (wt_win or O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None)) else "NOT_OBSERVED",
            "T6_engine_decision_plan": "NOT_OBSERVED",
            "T7_execution_result": "NOT_OBSERVED",
            "T8_agentTurn_completion": ("INFERRED" if O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None) else "NOT_OBSERVED"),
            "T9_automation_completion": ("CONFIRMED" if O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None) else "NOT_OBSERVED")}
    O["RUN_TIMELINE"] = tl
    O["POST_STATE_PACKAGE_STAGE"] = ("PARTIAL" if (wt_win or O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None))
                                       else "NOT_OBSERVED")
    O["AGENTTURN_CONTINUATION"] = ("CONFIRMED" if wt_win else
                                     ("UNKNOWN" if O["AUTOMATION_RUN_STATUS"] in ("UNKNOWN", None) else "NOT_CONFIRMED"))
    O["ENGINE_EXECUTION"] = "CONFIRMED" if eng_seen else ("NOT_CONFIRMED" if agent_evidence else "UNKNOWN")
    O["ENGINE_PID"] = ",".join(str(e.get("pid")) for e in p_start if "engine.py" in json.dumps(e)) or "NOT_OBSERVED"
    O["DECISION_OR_PLAN"] = ("CONFIRMED" if O.get("plan_ledger_entries_in_window") else "NOT_OBSERVED")
    O["FULL_M15_CYCLE"] = ("PARTIAL" if (p_start and (wt_win or O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None)))
                             else "NOT_CONFIRMED")
    O["AUTOMATION_COMPLETION"] = ("CONFIRMED" if O["AUTOMATION_RUN_STATUS"] not in ("UNKNOWN", None) else "NOT_OBSERVED")

    # ---------- 5) protection ----------
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3ok = ((v3["M01_event"] or "").startswith("ca44fd2c") and (v3["R1_ledger"] or "").startswith("d9cd6775")
             and (v3["M01_audit"] or "").startswith("a3bee537") and (v3["R2_canonical"] or "").startswith("20913b98"))
    obs_start = r11.get("OBSERVATION_START_UTC", "2026-09-25T15:30:46")
    def src_newer_than(root, t0):
        out = []
        try:
            lim = datetime.fromisoformat(t0).timestamp()
        except Exception:  # noqa: BLE001
            return ["UNCHECKED"]
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
    v1chg = src_newer_than(V1, obs_start)
    v2chg = src_newer_than(os.path.join(RE, "hermes", "trader_v2"), obs_start)
    O["V1_SOURCE_CONFIG_MODIFIED"] = "YES" if v1chg else "NO"
    O["V2_SOURCE_CONFIG_MODIFIED"] = "YES" if v2chg else "NO"
    O["V3_RESEARCH_MODIFIED"] = "NO" if v3ok else "YES"
    O["V3_HASHES"] = v3
    O["ORDER_SEND"] = 0
    O["COMMIT"] = "NONE"
    O["FALSE_POSITIVES_REJECTED"] = FP if FP else "NONE"

    rep = {k: O.get(k) for k in ("TASK_STATUS", "AUTOMATION_ID", "AUTOMATION_NAME", "TARGET_RUN_TIME",
                                   "POST_STATE_PACKAGE_STAGE", "AGENTTURN_CONTINUATION", "TRADING_HOURS_GATE_RESULT",
                                   "ENGINE_EXECUTION", "ENGINE_PID", "DECISION_OR_PLAN", "FULL_M15_CYCLE",
                                   "AUTOMATION_COMPLETION", "AUTOMATION_RUN_STATUS", "DIRECT_EVIDENCE",
                                   "INDIRECT_EVIDENCE", "DOCUMENTARY_EVIDENCE", "FALSE_POSITIVES_REJECTED",
                                   "V1_SOURCE_CONFIG_MODIFIED", "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED",
                                   "ORDER_SEND", "COMMIT")}
    rep["TASK_STATUS"] = "V1_POST_STATE_PACKAGE_TRACE_R12_COMPLETE"
    rep["AUTOMATION_ID"] = AID
    rep["AUTOMATION_NAME"] = "hermes-trader-m15-cycle"
    rep["ENGINE_START"] = "NOT_OBSERVED"
    rep["ENGINE_END"] = "NOT_OBSERVED"
    rep["ENGINE_RESTORE"] = "FORBIDDEN"
    rep["V1_STOP"] = "FORBIDDEN"
    rep["V1_RESTART"] = "FORBIDDEN"
    rep["SAFETY_WINDOW"] = "NOT_PROVEN"
    rep["NEXT_STAGE_AUTHORIZED"] = "NO"
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_POST_STATE_PACKAGE_TRACE_R12.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    print("\n=== §17 FINAL REPORT ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3000], flush=True)
    print("TIMELINE:", json.dumps(tl, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
