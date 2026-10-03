# -*- coding: utf-8 -*-
"""V1_RESET_PREPARATION_AUDIT_R16 — READ-ONLY freeze-condition audit + archive inventory.

Allowed: read-only V1 source/config/runtime/ledger/stats/reviews, read-only automation state, ONE read-only
MT5 check (account_info/terminal_info/positions_get/orders_get only), read-only process state, file metadata/hashes.
Writes ONLY under research/v3_opportunity_engine/ (this task dir). Nothing under research/hermes/trader_v1/.
Forbidden & never executed: V1_STOP/RESTART/KILL, AUTOMATION_RUN/TRIGGER/UPDATE/ENABLE/DISABLE/DELETE,
ORDER_SEND/POSITION_CLOSE/POSITION_MODIFY, ENGINE_WRITE/CONFIG_WRITE/STRATEGY_CHANGE/PARAMETER_CHANGE, GIT_COMMIT.
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
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
TARGET = os.path.join(V1, "engine.py")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
SCAN_DIRS = [os.path.join(V1, "run_state"), os.path.join(V1, "runtime"), os.path.join(V1, "tmp"),
              os.path.join(V1, "cache"), os.path.join(V1, "memory", "reviews"),
              os.path.join(V1, "observations"), os.path.join(V1, "state", "decision_contexts"),
              os.path.join(V1, "ledger"), os.path.join(V1, "state")]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}


def sh(args, t=90):
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


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def mask(a):
    s = str(a)
    return s[:3] + "***" + s[-2:] if len(s) > 6 else "UNKNOWN"


def classify(rel):
    r = rel.replace("\\", "/").lower()
    b = os.path.basename(r)
    if "ledger" in b:
        return "LEDGER"
    if re.search(r"trade|closed|fill|deal|order_history", r):
        return "TRADE_HISTORY"
    if "statistic" in b or r.endswith("stats.json"):
        return "STATISTICS"
    if "/memory/reviews/" in r or "review" in b:
        return "REVIEWS"
    if "/decision_contexts/" in r or "workflow_history" in b or "/decisions/" in r:
        return "DECISION_HISTORY"
    if "state_package" in b or b in ("workflow_latest.json",):
        return "STATE"
    if "/run_state/tmp/" in r or "/runtime/" in r or "/cache/" in r or "/tmp/" in r:
        return "RUNTIME"
    if "audit" in b or "report" in b:
        return "AUDIT"
    if r.endswith((".json", ".jsonl")):
        return "STATE"
    return "OTHER"


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "RUNNING"
    R["STARTED_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------- Stage 1 ----------
    esha = sha(TARGET)
    R["ENGINE_SHA256"] = esha
    R["ENGINE_STATE"] = "MV-R1_BASELINE" if esha == BASE else "OTHER"
    if esha != BASE:
        return abort("ENGINE_BASELINE_CHANGED")
    print("S1 engine:", esha[:20], R["ENGINE_STATE"], flush=True)

    # ---------- Stage 2 ----------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    doc = None
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    if m:
        try:
            doc = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            doc = None

    def findkey(obj, keys):
        res = {}

        def w(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if re.sub(r"[^a-z0-9]", "", k.lower()) in keys and not isinstance(v, (dict, list)):
                        res.setdefault(re.sub(r"[^a-z0-9]", "", k.lower()), v)
                    w(v)
            elif isinstance(x, list):
                for v in x:
                    w(v)
        w(obj)
        return res
    kk = findkey(doc, {"id", "name", "enabled", "status", "lastrunatms", "lastrunstatus", "nextrunatms",
                        "sessiontarget", "agentid", "updatedatms"})
    sched = None
    if isinstance(doc, dict):
        sched = doc.get("schedule")
    R["AUTOMATION_ENABLED"] = kk.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = kk.get("status", "UNKNOWN")
    R["LAST_RUN_AT"] = iso(int(kk["lastrunatms"]) / 1000.0) if "lastrunatms" in kk else "UNKNOWN"
    R["LAST_RUN_STATUS"] = kk.get("lastrunstatus", "UNKNOWN")
    R["NEXT_RUN_AT"] = iso(int(kk["nextrunatms"]) / 1000.0) if "nextrunatms" in kk else "UNKNOWN"
    R["SESSION_TARGET"] = kk.get("sessiontarget", "UNKNOWN")
    R["AGENT_ID"] = kk.get("agentid", "UNKNOWN")
    if isinstance(sched, dict):
        R["SCHEDULE"] = json.dumps(sched, ensure_ascii=False)
        R["SCHEDULE_KIND"] = sched.get("kind") or sched.get("type") or "UNKNOWN"
        R["SCHEDULE_EXPRESSION"] = sched.get("expression") or sched.get("cron") or sched.get("every") or "UNKNOWN"
        R["TIMEZONE"] = sched.get("tz") or sched.get("timezone") or "UNKNOWN"
    else:
        R["SCHEDULE"] = str(sched) if sched is not None else "UNKNOWN"
        R["SCHEDULE_KIND"] = R["SCHEDULE_EXPRESSION"] = R["TIMEZONE"] = "UNKNOWN"
    R["AUTOMATION_READABLE"] = "YES" if doc is not None else "NO"
    print("S2 automation:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "AUTOMATION_STATUS", "LAST_RUN_AT",
                                                            "LAST_RUN_STATUS", "NEXT_RUN_AT", "SCHEDULE_KIND",
                                                            "SCHEDULE_EXPRESSION", "TIMEZONE", "SESSION_TARGET",
                                                            "AGENT_ID")}, ensure_ascii=False), flush=True)

    # ---------- Stage 3 ----------
    procs = []
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
                "ConvertTo-Json -Compress -Depth 4"], 90)
    try:
        d = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = d if isinstance(d, list) else [d]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if re.search(r"trader_v1|engine\.py|state_package", (x.get("CommandLine") or ""), re.I)
            and "Get-CimInstance" not in (x.get("CommandLine") or "")]
    eng = [x for x in v1p if re.search(r"engine\.py", (x.get("CommandLine") or ""), re.I)]
    byid = {x.get("ProcessId"): x for x in allp}
    chain = []
    if v1p:
        cur = v1p[0]
        for _ in range(8):
            pp = cur.get("ParentProcessId")
            par = byid.get(pp)
            if not par:
                break
            chain.append(f"{par.get('Name')}({pp}) :: {(par.get('CommandLine') or '')[:110]}")
            cur = par
    R["V1_ENGINE_PROCESS"] = "RUNNING" if eng else ("NOT_RUNNING" if not v1p else "NOT_RUNNING")
    R["V1_ENGINE_PID"] = eng[0].get("ProcessId") if eng else "NONE"
    R["V1_ENGINE_START"] = str(eng[0].get("CreationDate")) if eng else "NONE"
    R["V1_MATCHING_PROCESSES"] = [{"PID": x.get("ProcessId"), "NAME": x.get("Name"),
                                     "CMDLINE": (x.get("CommandLine") or "")[:150]} for x in v1p[:5]]
    R["V1_PROCESS_CHAIN"] = chain
    R["CURRENT_CYCLE"] = "RUNNING" if eng else "NOT_RUNNING"
    print("S3 process:", R["V1_ENGINE_PROCESS"], R["CURRENT_CYCLE"], "v1matching=", len(v1p), flush=True)

    # ---------- Stage 4 : ONE read-only MT5 check ----------
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " res={'CONNECTED':bool(ok),'server':(ai.server if ai else None),"
             "'login':(str(ai.login) if ai and ai.login else None),'equity':(ai.equity if ai else None),"
             "'balance':(ai.balance if ai else None),'trade_allowed':(ti.trade_allowed if ti else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_))}\n"
             " print(json.dumps(res))\n mt5.shutdown()\nexcept Exception as e:\n"
             " print(json.dumps({'err':type(e).__name__+':'+str(e)[:110]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        r4 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as e:  # noqa: BLE001
        r4 = {"err": type(e).__name__}
    ok4 = bool(r4.get("CONNECTED")) and r4.get("positions") is not None and r4.get("orders") is not None
    R["MT5_CONTEXT"] = "CONFIRMED" if ok4 else "UNKNOWN"
    R["ACCOUNT_ID"] = mask(r4.get("login")) if r4.get("login") else "UNKNOWN"
    R["SERVER"] = r4.get("server") or "UNKNOWN"
    R["TRADE_ALLOWED"] = r4.get("trade_allowed", "UNKNOWN")
    R["OPEN_POSITIONS"] = r4.get("positions") if r4.get("positions") is not None else "UNKNOWN"
    R["PENDING_ORDERS"] = r4.get("orders") if r4.get("orders") is not None else "UNKNOWN"
    R["INITIAL_BALANCE"] = r4.get("balance", "UNKNOWN")
    R["INITIAL_EQUITY"] = r4.get("equity", "UNKNOWN")
    R["MT5_RAW"] = {k: v for k, v in r4.items() if k != "login"}
    print("S4 MT5:", json.dumps({k: R[k] for k in ("MT5_CONTEXT", "ACCOUNT_ID", "SERVER", "TRADE_ALLOWED",
                                                     "OPEN_POSITIONS", "PENDING_ORDERS")}, ensure_ascii=False), flush=True)

    # ---------- Stage 5 freeze gate on trading state ----------
    reason = None
    if not ok4:
        reason = "MT5_CONTEXT_UNKNOWN"
    elif isinstance(R["OPEN_POSITIONS"], int) and R["OPEN_POSITIONS"] > 0:
        reason = "OPEN_POSITION_EXISTS"
    elif isinstance(R["PENDING_ORDERS"], int) and R["PENDING_ORDERS"] > 0:
        reason = "PENDING_ORDER_EXISTS"
    R["RESET_BLOCKED"] = "YES" if reason in ("OPEN_POSITION_EXISTS", "PENDING_ORDER_EXISTS") else "NO"

    # ---------- Stage 6 runtime write window ----------
    def snap():
        d = {}
        for root in SCAN_DIRS[:7]:
            if not os.path.isdir(root):
                continue
            for r_, _, fs in os.walk(root):
                if "__pycache__" in r_:
                    continue
                for f in fs:
                    p = os.path.join(r_, f)
                    try:
                        st = os.stat(p)
                        d[os.path.relpath(p, AIQ).replace("\\", "/")] = (st.st_size, round(st.st_mtime, 3))
                    except OSError:
                        continue
        return d
    a0 = snap()
    newest_before = max((v[1] for v in a0.values()), default=0)
    time.sleep(15)
    a1 = snap()
    ch = [k for k in a1 if k in a0 and a0[k] != a1[k]]
    newest_after = max((v[1] for v in a1.values()), default=0)
    R["WRITE_WINDOW_SECONDS"] = 15
    R["WATCHED_FILES"] = len(a1)
    R["FILES_CHANGED_IN_WINDOW"] = ch[:10]
    key_files = [k for k in a1 if k.endswith("state_package_latest.json") or k.endswith("plan_ledger.jsonl")]
    key_mtimes = {k: iso(a1[k][1]) for k in key_files}
    R["KEY_FILE_MTIMES"] = key_mtimes
    ages = [time.time() - v[1] for v in a1.values()]
    min_age = min(ages) if ages else None
    if ch:
        R["STATE_WRITE_IN_FLIGHT"] = "YES"
        reason = reason or "RUNTIME_WRITE_IN_FLIGHT"
    elif min_age is not None and min_age > 300:
        R["STATE_WRITE_IN_FLIGHT"] = "NO"
    else:
        R["STATE_WRITE_IN_FLIGHT"] = "UNKNOWN"
    R["NEWEST_V1_WRITE_AGE_SECONDS"] = round(min_age, 1) if min_age is not None else "UNKNOWN"
    print("S6 write window:", R["STATE_WRITE_IN_FLIGHT"], "changed=", len(ch), "newest_age_s=",
          R["NEWEST_V1_WRITE_AGE_SECONDS"], flush=True)

    # ---------- Stage 7/8 archive inventory ----------
    cands = []
    for root in SCAN_DIRS:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                p = os.path.join(r_, f)
                try:
                    st = os.stat(p)
                    if st.st_size > 20_000_000:
                        continue
                except OSError:
                    continue
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                cands.append({"path": rel, "size": st.st_size, "mtime": iso(st.st_mtime),
                               "sha256": sha(p), "classification": classify(rel)})
    cands.sort(key=lambda x: x["mtime"], reverse=True)
    R["ARCHIVE_CANDIDATE_COUNT"] = len(cands)
    cls = {}
    for c in cands:
        cls[c["classification"]] = cls.get(c["classification"], 0) + 1
    R["ARCHIVE_CLASS_COUNTS"] = cls
    R["ARCHIVE_CANDIDATES"] = cands[:60]
    # must-archive distinct list (top-level重要文件)
    must = [c for c in cands if c["classification"] in ("LEDGER", "TRADE_HISTORY", "STATISTICS", "REVIEWS",
                                                          "DECISION_HISTORY")]
    R["MUST_ARCHIVE_COUNT"] = len(must)
    R["MUST_ARCHIVE_TOP"] = must[:20]
    R["CAN_RESET_COUNT"] = cls.get("RUNTIME", 0)
    R["MUST_KEEP"] = [c["path"] for c in cands if c["classification"] in ("LEDGER", "TRADE_HISTORY")][:10]
    R["UNDETERMINED_COUNT"] = cls.get("OTHER", 0)
    ledger_found = [c["path"] for c in cands if c["classification"] == "LEDGER"]
    R["OLD_LEDGER_FOUND"] = "YES" if ledger_found else "NO"
    R["OLD_LEDGER_PATHS"] = ledger_found[:10]
    print("S7/8 archive:", R["ARCHIVE_CANDIDATE_COUNT"], cls, "ledger=", len(ledger_found), flush=True)

    # ---------- Stage 9 new-run isolation design ----------
    seq = None
    pl = None
    for c in cands:
        if c["path"].endswith("plan_ledger.jsonl"):
            pl = os.path.join(AIQ, c["path"])
    if pl and os.path.exists(pl):
        try:
            last = [l for l in open(pl, encoding="utf-8") if l.strip()][-1]
            j = json.loads(last)
            seq = j.get("seq") or j.get("index") or j.get("id") or "PRESENT_NO_SEQ"
        except Exception:  # noqa: BLE001
            seq = "UNREADABLE"
    R["NEW_RUN_DESIGN"] = {"RUN_ID": "V1_RUN_20260924_RESET_01(proposed, not created)",
                            "BASELINE_ENGINE_SHA256": BASE,
                            "INITIAL_OPEN_POSITIONS": R["OPEN_POSITIONS"],
                            "INITIAL_PENDING_ORDERS": R["PENDING_ORDERS"],
                            "INITIAL_BALANCE": R["INITIAL_BALANCE"], "INITIAL_EQUITY": R["INITIAL_EQUITY"],
                            "INITIAL_LEDGER_SEQUENCE": seq if seq is not None else "UNKNOWN",
                            "RUN_START": "NOT_CREATED"}
    R["NEW_RUN_DIR_CREATED"] = "NO"

    # ---------- Stage 10/11 ----------
    R["STRATEGY_CHANGED"] = "NO"
    R["PARAMETER_CHANGED"] = "NO"
    R["ENGINE_SHA256_RECORDED_FOR_RESET"] = BASE
    def newer(root, lim):
        out = []
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(root, r_, f) if False else os.path.join(r_, f)
                    try:
                        if os.path.getmtime(p) > lim:
                            out.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                    except OSError:
                        continue
        return out
    lim10 = time.time() - 86400
    v2c = newer(V2, lim10)
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    R["V2_CHANGES_24H"] = v2c[:5]
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_RESEARCH_MODIFIED"] = "NO" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "YES"

    # ---------- Stage 12 gates ----------
    conds = {
        "1_engine_baseline": R["ENGINE_STATE"] == "MV-R1_BASELINE",
        "2_automation_readable": R["AUTOMATION_READABLE"] == "YES",
        "3_cycle_not_running": R["CURRENT_CYCLE"] == "NOT_RUNNING",
        "4_mt5_confirmed": R["MT5_CONTEXT"] == "CONFIRMED",
        "5_no_open_positions": R["OPEN_POSITIONS"] == 0,
        "6_no_pending_orders": R["PENDING_ORDERS"] == 0,
        "7_no_runtime_write": R["STATE_WRITE_IN_FLIGHT"] == "NO",
        "8_old_ledger_found": R["OLD_LEDGER_FOUND"] == "YES",
        "9_archive_candidates_built": R["ARCHIVE_CANDIDATE_COUNT"] > 0,
        "10_v2v3_clean": R["V2_SOURCE_CONFIG_MODIFIED"] == "NO" and R["V3_RESEARCH_MODIFIED"] == "NO"}
    R["GATE_CONDITIONS"] = conds
    R["RESET_FREEZE_GATE"] = "PASS" if all(conds.values()) else "FAIL"
    R["ENGINE_WRITE"] = 0
    R["AUTOMATION_WRITE"] = 0
    R["AUTOMATION_RUN"] = 0
    R["ORDER_SEND"] = 0
    R["POSITION_CLOSE"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["TASK_STATUS"] = "V1_RESET_PREPARATION_AUDIT_R16_COMPLETE"
    R["STOP_REASON"] = reason or "NONE"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FINISHED_UTC"] = datetime.now(timezone.utc).isoformat()
    dump(0)


def abort(reason):
    R["TASK_STATUS"] = "V1_RESET_PREPARATION_AUDIT_R16_COMPLETE"
    R["STOP_REASON"] = reason
    R["RESET_FREEZE_GATE"] = "FAIL"
    R["RESET_BLOCKED"] = "YES"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["ENGINE_WRITE"] = 0
    R["AUTOMATION_WRITE"] = 0
    R["AUTOMATION_RUN"] = 0
    R["ORDER_SEND"] = 0
    R["POSITION_CLOSE"] = 0
    R["V1_STOP"] = 0
    R["V1_RESTART"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["FINISHED_UTC"] = datetime.now(timezone.utc).isoformat()
    dump(0)


def dump(rc):
    os.makedirs(HERE, exist_ok=True)
    json.dump(R, open(os.path.join(HERE, "V1_RESET_PREPARATION_AUDIT_R16.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "ENGINE_SHA256", "ENGINE_STATE", "AUTOMATION_ENABLED", "AUTOMATION_STATUS", "LAST_RUN_AT",
             "LAST_RUN_STATUS", "NEXT_RUN_AT", "SCHEDULE_KIND", "SCHEDULE_EXPRESSION", "TIMEZONE", "SESSION_TARGET",
             "AGENT_ID", "V1_ENGINE_PROCESS", "CURRENT_CYCLE", "V1_ENGINE_PID", "V1_PROCESS_CHAIN",
             "MT5_CONTEXT", "ACCOUNT_ID", "SERVER", "TRADE_ALLOWED", "OPEN_POSITIONS", "PENDING_ORDERS",
             "STATE_WRITE_IN_FLIGHT", "ARCHIVE_CANDIDATE_COUNT", "ARCHIVE_CLASS_COUNTS", "OLD_LEDGER_FOUND",
             "OLD_LEDGER_PATHS", "MUST_ARCHIVE_COUNT", "CAN_RESET_COUNT", "UNDETERMINED_COUNT",
             "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED", "V3_M01_EVENT_HASH", "V3_R1_LEDGER_HASH",
             "V3_M01_AUDIT_HASH", "V3_R2_CANONICAL_HASH", "ENGINE_WRITE", "AUTOMATION_WRITE", "AUTOMATION_RUN",
             "ORDER_SEND", "POSITION_CLOSE", "V1_STOP", "V1_RESTART", "GIT_COMMIT", "GATE_CONDITIONS",
             "RESET_FREEZE_GATE", "RESET_BLOCKED", "STOP_REASON", "NEXT_STAGE_AUTHORIZED"]
    print("\n=== §19 FINAL REPORT ===", flush=True)
    for k in keys:
        v = R.get(k, "UNKNOWN")
        print(("{} = {}" if not isinstance(v, (dict, list)) else "{} = {}").format(k, v), flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_RESET_PREPARATION_AUDIT_R16.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
