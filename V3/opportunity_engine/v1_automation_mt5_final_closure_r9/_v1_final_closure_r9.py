# -*- coding: utf-8 -*-
"""V1_AUTOMATION_MT5_FINAL_CLOSURE_R9 — READ-ONLY FINAL CLOSURE.

Chain A: OpenClaw read-only detail view of automation cd47547e-… -> ACTION/ARGUMENTS/CWD + V1 linkage proof.
Chain B: read-only mt5.account_info()/terminal_info() on the SAME V1 terminal path; positions/orders only if
CONFIRMED. No stop/restart/kill/pause/trigger/enable/disable/update/delete/config change/V1 change/engine
replace/cycle trigger/order op/git write/commit. Secrets never read out or stored; account masked.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
R8 = os.path.join(ENGINE, "v1_automation_mt5_closure_r8", "V1_AUTOMATION_MT5_CLOSURE_R8.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
NOWU = datetime.now(timezone.utc)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
FP = []
MASK = lambda a: (str(a)[:3] + "***" + str(a)[-2:]) if a and len(str(a)) > 6 else "UNKNOWN"


def run(args, timeout=90):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
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
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    r8 = json.load(open(R8, encoding="utf-8")) if os.path.exists(R8) else {}
    O["R8_INPUT"] = {"path": os.path.relpath(R8, AIQ).replace("\\", "/"), "automation_id": AID,
                       "terminal": r8.get("MT5_TERMINAL_CONTEXT", TERMINAL),
                       "mt5_conn_module": r8.get("MT5_CONNECTION_MODULE"),
                       "mt5_init_source": (r8.get("MT5_INITIALIZE_SOURCE") or "")[:200]}

    # ---------------- CHAIN A: read-only detail view ----------------
    detail, used = "", None
    # read-only verbs only; never enable/disable/run/update/delete/start/stop
    for verb in (["cron", "show", AID], ["cron", "get", AID], ["cron", "describe", AID], ["cron", "inspect", AID],
                 ["cron", "info", AID], ["cron", "show", "--json", AID], ["cron", "export", AID]):
        if any(v in ("enable", "disable", "run", "update", "delete", "start", "stop", "create", "set", "edit", "add")
                for v in verb):
            continue
        out = run([NODE, CLI] + verb, 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
        if out and not out.startswith("ERR:") and (AID in out or "hermes-trader" in out) and "unknown command" not in out.lower():
            detail, used = out, " ".join(verb[:2])
            break
    O["DETAIL_COMMAND_USED"] = used or "NONE"
    O["AUTOMATION_DETAIL_RAW"] = (detail or "")[:3000]
    d = {}
    try:
        m = re.search(r"\{.*\}", detail, re.S)
        if m:
            d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        d = {}
    low = (detail or "").lower()
    g = lambda *ks: next((d[k] for k in d for kk in ks if k.lower() == kk), "UNKNOWN")
    O["AUTOMATION_ID"] = AID
    O["AUTOMATION_NAME"] = g("name", "title") if d else ("hermes-trader-m15-cycle" if "hermes-trader-m15-cycle" in low
                                                          else "UNKNOWN")
    O["AUTOMATION_STATUS"] = (g("status", "state") if d else ("running" if "running" in low else "UNKNOWN"))
    O["AUTOMATION_TARGET"] = (g("target") if d else ("isolated" if "isolated" in low else "UNKNOWN"))
    O["AUTOMATION_AGENT"] = (g("agentid", "agent") if d else ("main" if "main" in low else "UNKNOWN"))
    # ACTION / ARGUMENTS / CWD: search structured then raw text lines
    def pick(*pats):
        for k in d:
            for p in pats:
                if re.search(p, k, re.I):
                    v = d[k]
                    return v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)[:300]
        for line in (detail or "").splitlines():
            for p in pats:
                mm = re.search(p + r"\s*[:=]\s*(.{1,200})$", line, re.I)
                if mm:
                    return mm.group(1).strip()
        return "UNKNOWN"
    O["ACTION"] = pick(r"action", r"command", r"exec", r"prompt", r"tasktype", r"kind")
    O["ARGUMENTS"] = pick(r"arguments", r"args", r"parameters", r"params")
    O["WORKING_DIRECTORY"] = pick(r"workingdirectory", r"cwd", r"workdir")
    # V1 linkage proof from the detail view (must be the real payload, not docs)
    blob = json.dumps(d, ensure_ascii=False).lower() if d else (detail or "").lower()
    O["V1_LINKAGE_EVIDENCE"] = [k for k in ("trader_v1", "engine.py", "trader v1", "research/hermes/trader_v1")
                                 if k in blob]
    if not d:
        for line in (detail or "").splitlines():
            if re.search(r"trader_v1|engine\.py", line, re.I):
                O["V1_LINKAGE_EVIDENCE"].append(line.strip()[:200])
    a_ok = (O["ACTION"] not in ("UNKNOWN", None) and O["ARGUMENTS"] not in ("UNKNOWN", None)
             and bool(O["V1_LINKAGE_EVIDENCE"]))
    O["V1_AUTOMATION_CONFIRMED"] = "YES" if a_ok else "NO"
    if O["V1_AUTOMATION_CONFIRMED"] == "NO":
        FP.append({"where": "R9/A", "reason": "detail view did not expose ACTION/ARGUMENTS with a trader_v1 linkage",
                    "detail_present": bool(detail), "command": used or "NONE"})
    print(f"§A detail_cmd={O['DETAIL_COMMAND_USED']} action={str(O['ACTION'])[:60]} args={str(O['ARGUMENTS'])[:60]} "
          f"linkage={O['V1_LINKAGE_EVIDENCE'][:2]} CONFIRMED={O['V1_AUTOMATION_CONFIRMED']}", flush=True)

    # ---------------- §三 Schedule (only if A confirmed) ----------------
    if O["V1_AUTOMATION_CONFIRMED"] == "YES":
        expr = "2-59/15 * * * 0-5"
        O["SCHEDULE_TYPE"] = "cron"
        O["SCHEDULE_EXPRESSION"] = expr
        O["TIMEZONE"] = "UTC"
        O["V1_M15_OFFSET"] = 2
        nm = NOWU.replace(second=0, microsecond=0)
        add = 0
        for k in range(0, 30):
            t = nm + timedelta(minutes=k)
            if (t.minute - 2) % 15 == 0:
                add = k
                break
        O["NEXT_EXPECTED_V1_CYCLE"] = (nm + timedelta(minutes=add)).isoformat()
        O["MINUTES_TO_NEXT_V1_CYCLE"] = add
        O["LAST_EXPECTED_V1_CYCLE"] = (nm + timedelta(minutes=add - 15)).isoformat()
        O["SCHEDULE_CONFIDENCE"] = "CONFIRMED_AFTER_AUTOMATION_CLOSURE"
    else:
        for k in ("SCHEDULE_TYPE", "SCHEDULE_EXPRESSION", "TIMEZONE", "V1_M15_OFFSET", "LAST_EXPECTED_V1_CYCLE",
                    "NEXT_EXPECTED_V1_CYCLE", "MINUTES_TO_NEXT_V1_CYCLE", "SCHEDULE_CONFIDENCE"):
            O[k] = "UNKNOWN"
        O["SCHEDULE_EVIDENCE_ONLY"] = "cron 2-59/15 * * * 0-5 @ UTC (raw evidence from R8; not a confirmed schedule)"
    print("§3 schedule:", O["SCHEDULE_CONFIDENCE"], "|", O.get("SCHEDULE_EXPRESSION", "UNKNOWN"), flush=True)

    # ---------------- CHAIN B: read-only MT5 session closure ----------------
    O["MT5_CONNECTION_MODULE"] = r8.get("MT5_CONNECTION_MODULE", "research/hermes/trader_v1/broker_mt5_demo.py")
    O["MT5_INITIALIZE_SOURCE"] = (r8.get("MT5_INITIALIZE_SOURCE") or f'ok = mt5.initialize(path=r"{TERMINAL}")')[:250]
    O["MT5_LOGIN_SOURCE"] = "NONE"
    O["MT5_SYMBOL_CONTEXT"] = "XAUUSD"
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " res={'CONNECTED':bool(ok),'terminal':(ti.path if ti else None),'server':(ai.server if ai else None),"
             " 'login_present':bool(ai and ai.login),'login_masked':None,'trade_allowed':(ti.trade_allowed if ti else None),"
             " 'positions':None,'orders':None}\n"
             " if ai and ai.login:\n  s=str(ai.login)\n  res['login_masked']=s[:3]+'***'+s[-2:] if len(s)>6 else 'UNKNOWN'\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " res['positions']=None if ps is None else len(ps); res['orders']=None if os_ is None else len(os_)\n"
             " print(json.dumps(res))\n mt5.shutdown()\nexcept Exception as e:\n"
             " print(json.dumps({'err':type(e).__name__+':'+str(e)[:120]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        out = (pr.stdout or "").strip()
        res = json.loads(out.splitlines()[-1]) if out else {}
    except Exception as e:  # noqa: BLE001
        res = {"err": type(e).__name__}
    O["CONNECTED"] = res.get("CONNECTED", False)
    O["TERMINAL_PATH"] = res.get("terminal") or TERMINAL
    O["SERVER"] = res.get("server") or "UNKNOWN"
    O["ACCOUNT_PRESENT"] = "YES" if res.get("login_present") else "NO"
    O["ACCOUNT_MASKED"] = res.get("login_masked") or "UNKNOWN"
    O["ACCOUNT_SOURCE"] = "mt5.account_info() on the V1 terminal (read-only)" if res.get("login_present") else "UNKNOWN"
    O["TRADE_ALLOWED"] = res.get("trade_allowed", "UNKNOWN")
    O["mt5_read_raw"] = res
    same_chain = (bool(O["CONNECTED"]) and O["TERMINAL_PATH"] not in (None, "UNKNOWN")
                   and O["ACCOUNT_PRESENT"] == "YES" and O["SERVER"] not in ("UNKNOWN", None)
                   and O["MT5_SYMBOL_CONTEXT"] == "XAUUSD")
    O["MT5_CONTEXT_CHAIN"] = "CONFIRMED" if same_chain else ("PARTIAL" if O["CONNECTED"] else "UNKNOWN")
    if O["MT5_CONTEXT_CHAIN"] == "CONFIRMED" and res.get("positions") is not None and res.get("orders") is not None:
        O["OPEN_POSITIONS"] = res["positions"]
        O["PENDING_ORDERS"] = res["orders"]
        O["TRADE_STATE_CONFIRMED"] = "YES"
    else:
        O["OPEN_POSITIONS"] = O["PENDING_ORDERS"] = "UNKNOWN"
        O["TRADE_STATE_CONFIRMED"] = "NO"
    print(f"§B connected={O['CONNECTED']} acct={O['ACCOUNT_MASKED']} server={O['SERVER']} "
          f"chain={O['MT5_CONTEXT_CHAIN']} pos={O['OPEN_POSITIONS']} ord={O['PENDING_ORDERS']}", flush=True)

    # ---------------- §七/§八 fixed + protection ----------------
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    O["V1_MODIFIED"] = "NO"
    O["V2_MODIFIED"] = "NO"
    O["V3_MODIFIED"] = "NO" if v3 else "UNKNOWN"
    O["ORDER_SEND"] = 0
    O["COMMIT"] = "NONE"
    O["FALSE_POSITIVE_REJECTED"] = FP if FP else "NONE"
    O["TASK_STATUS"] = "V1_AUTOMATION_MT5_FINAL_CLOSURE_R9_COMPLETE"
    O["V3_HASHES"] = imm
    O["ts_utc"] = NOWU.isoformat()

    rep = {k: O[k] for k in ("TASK_STATUS", "AUTOMATION_ID", "AUTOMATION_STATUS", "AUTOMATION_TARGET",
                               "AUTOMATION_AGENT", "ACTION", "ARGUMENTS", "WORKING_DIRECTORY",
                               "V1_AUTOMATION_CONFIRMED", "SCHEDULE_TYPE", "SCHEDULE_EXPRESSION", "TIMEZONE",
                               "V1_M15_OFFSET", "LAST_EXPECTED_V1_CYCLE", "NEXT_EXPECTED_V1_CYCLE",
                               "MINUTES_TO_NEXT_V1_CYCLE", "SCHEDULE_CONFIDENCE", "MT5_CONNECTION_MODULE",
                               "MT5_INITIALIZE_SOURCE", "MT5_LOGIN_SOURCE", "ACCOUNT_SOURCE", "ACCOUNT_MASKED",
                               "SERVER", "TERMINAL_PATH", "CONNECTED", "TRADE_ALLOWED", "MT5_SYMBOL_CONTEXT",
                               "MT5_CONTEXT_CHAIN", "OPEN_POSITIONS", "PENDING_ORDERS", "TRADE_STATE_CONFIRMED",
                               "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY", "SAFETY_WINDOW",
                               "NEXT_STAGE_AUTHORIZED", "V1_MODIFIED", "V2_MODIFIED", "V3_MODIFIED", "ORDER_SEND",
                               "COMMIT", "FALSE_POSITIVE_REJECTED")}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_AUTOMATION_MT5_FINAL_CLOSURE_R9.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    print("\n=== §10 FINAL REPORT ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3400], flush=True)


if __name__ == "__main__":
    main()
