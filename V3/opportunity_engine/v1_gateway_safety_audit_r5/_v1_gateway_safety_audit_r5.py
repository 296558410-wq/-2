# -*- coding: utf-8 -*-
"""V1_GATEWAY_SAFETY_AUDIT_R5 — TARGETED read-only forensics (no broad workspace walk).

Priority 1: locate the REAL gateway automation store via gateway.cmd -> config/state/automations.
Priority 2: schedule only from that real definition. Priority 3: restart linkage from that definition.
Priority 4/5: close the MT5 terminal/account/symbol chain from V1 source; then read-only positions/orders.
Priority 6: a full cycle boundary is NOT triggered by us; observed only if it naturally occurs.
Everything prohibited by section 2 is untouched.
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
OC = os.path.join(HOME, ".openclaw")
V1 = os.path.join(RE, "hermes", "trader_v1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOWU = datetime.now(timezone.utc)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def rd(p, n=200000):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()[:n]
    except Exception:  # noqa: BLE001
        return None


def find_automation(doc, path, depth=0):
    """search a parsed JSON doc for a V1 trader automation entry (id/name/action/command contains trader_v1)."""
    hits = []
    if depth > 8:
        return hits
    if isinstance(doc, dict):
        blob = json.dumps(doc, ensure_ascii=False)[:4000].lower()
        if ("hermes-trader" in blob or "trader_v1" in blob or "hermes_trader" in blob):
            if any(k in doc for k in ("schedule", "cron", "interval", "action", "command", "args", "enabled",
                                       "prompt", "agentTurn", "agent_turn", "task")):
                hits.append({"source": path, "entry": {k: (v if not isinstance(v, (dict, list)) else str(v)[:300])
                                                         for k, v in doc.items()}})
        for k, v in doc.items():
            hits += find_automation(v, path, depth + 1)
    elif isinstance(doc, list):
        for v in doc:
            hits += find_automation(v, path, depth + 1)
    return hits


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    # ---------------- §三 targeted: gateway.cmd + real stores ----------------
    gcmd = os.path.join(OC, "gateway.cmd")
    O["gateway_cmd"] = rd(gcmd, 2000) if os.path.exists(gcmd) else None
    refs = []
    if O["gateway_cmd"]:
        refs = re.findall(r"([A-Za-z]:\\[^\"\s]+)", O["gateway_cmd"])
    O["gateway_cmd_referenced_paths"] = refs[:10]
    toplevel = []
    if os.path.isdir(OC):
        for n in sorted(os.listdir(OC)):
            p = os.path.join(OC, n)
            toplevel.append({"name": n, "dir": os.path.isdir(p),
                              "size": (os.path.getsize(p) if os.path.isfile(p) else None)})
    O["openclaw_toplevel"] = toplevel
    # candidate stores (targeted: no media/, no logs/)
    cand_files = []
    for rel in ("config.json", "config.yaml", "config.yml", "automations.json", "automations",
                 os.path.join("state", "automations.json"), os.path.join("state", "config.json"),
                 "workflows.json", os.path.join("state", "workflows.json")):
        p = os.path.join(OC, rel)
        if os.path.isfile(p):
            cand_files.append(p)
        elif os.path.isdir(p):
            for r_, _, fs in os.walk(p):
                for f in fs:
                    if f.lower().endswith((".json", ".yaml", ".yml")):
                        cand_files.append(os.path.join(r_, f))
    for d in ("state", "automations", "workflows", "cron", "crons", "tasks", "schedules"):
        dp = os.path.join(OC, d)
        if os.path.isdir(dp):
            for r_, ds, fs in os.walk(dp):
                if "media" in r_ or "logs" in r_:
                    continue
                for f in fs:
                    if f.lower().endswith((".json", ".yaml", ".yml")):
                        cand_files.append(os.path.join(r_, f))
    cand_files = sorted(set(cand_files))[:200]
    hits = []
    for p in cand_files:
        try:
            if os.path.getsize(p) > 5_000_000:
                continue
        except OSError:
            continue
        txt = rd(p, 5_000_000)
        if not txt:
            continue
        doc = None
        try:
            doc = json.loads(txt)
        except Exception:  # noqa: BLE001
            doc = None
        if doc is not None:
            hits += find_automation(doc, os.path.relpath(p, AIQ).replace("\\", "/"))
        elif re.search(r"hermes[-_]trader|trader_v1", txt, re.I):
            for m in re.finditer(r"(?i)(hermes[-_]trader[\w-]*|trader_v1)", txt):
                ln = txt[:m.start()].count("\n") + 1
                hits.append({"source": os.path.relpath(p, AIQ).replace("\\", "/"), "entry": {"line": ln,
                                                                                              "match": m.group(0)},
                              "raw": True})
                break
    O["automation_candidate_files"] = [os.path.relpath(p, AIQ).replace("\\", "/") for p in cand_files]
    O["GATEWAY_V1_AUTOMATION_HITS"] = hits[:5]
    O["GATEWAY_V1_AUTOMATION_FOUND"] = "YES" if hits else "NO"
    O["GATEWAY_V1_AUTOMATION_SOURCE"] = (hits[0]["source"] if hits else "NOT_FOUND")
    e0 = hits[0]["entry"] if hits else {}
    def gv(*keys):
        for k in keys:
            for kk, vv in e0.items():
                if kk.lower() == k.lower():
                    return vv
        return "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ID"] = gv("id", "name", "taskName") if hits else "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ENABLED"] = gv("enabled", "active", "state") if hits else "UNKNOWN"
    O["ACTION"] = gv("action", "command", "execute", "prompt", "taskType") if hits else "UNKNOWN"
    O["ARGUMENTS"] = gv("args", "arguments", "parameters") if hits else "UNKNOWN"
    O["WORKING_DIRECTORY"] = gv("cwd", "workingDirectory", "working_directory") if hits else "UNKNOWN"
    O["SCHEDULE_TYPE"] = gv("schedule", "scheduleType", "type") if hits else "UNKNOWN"
    O["SCHEDULE_EXPRESSION"] = gv("cron", "expression", "interval", "every") if hits else "UNKNOWN"
    O["TIMEZONE"] = gv("timezone", "tz") if hits else "UNKNOWN"
    O["OFFSET"] = gv("offset") if hits else "UNKNOWN"
    O["RETRY"] = gv("retry", "retries") if hits else "UNKNOWN"
    O["RESTART"] = gv("restart", "restartOnExit") if hits else "UNKNOWN"
    O["ON_EXIT"] = gv("onExit", "on_exit") if hits else "UNKNOWN"
    O["WATCHDOG"] = gv("watchdog", "heartbeat") if hits else "UNKNOWN"
    # structured entry = a JSON parse that yielded a dict with fields (not a raw text line)
    structured = any(not h.get("raw") for h in hits)
    O["AUTOMATION_STRUCTURED_ENTRY"] = "YES" if structured else "NO"
    print(f"§3 candidates={len(cand_files)} hits={len(hits)} structured={structured}", flush=True)
    for h in hits[:3]:
        print("   ", h["source"], "->", str(h["entry"])[:220], flush=True)

    # ---------------- §五 schedule only if structured entry ----------------
    O["V1_M15_SCHEDULE_SOURCE"] = (O["GATEWAY_V1_AUTOMATION_SOURCE"] if structured else "UNKNOWN")
    O["V1_M15_OFFSET"] = (O["OFFSET"] if structured else "UNKNOWN")
    O["V1_NEXT_CYCLE"] = "UNKNOWN"
    O["LAST_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["NEXT_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["MINUTES_TO_NEXT_V1_CYCLE"] = "UNKNOWN"
    if structured and O["SCHEDULE_EXPRESSION"] not in ("UNKNOWN", None) and O["SCHEDULE_TYPE"] != "UNKNOWN":
        O["SCHEDULE_CONFIDENCE"] = "PARTIAL"
    else:
        O["SCHEDULE_CONFIDENCE"] = "UNKNOWN"
    print(f"§5 schedule: CONFIDENCE={O['SCHEDULE_CONFIDENCE']} (no inference from docs/V2/tick tasks)", flush=True)

    # ---------------- §六 restart linkage from the real definition only ----------------
    O["AUTO_RESTART_MECHANISM"] = ("YES" if structured and str(O["RESTART"]).lower() not in ("unknown", "none", "")
                                     else "UNKNOWN")
    O["V1_RESTART_TRIGGER"] = "UNKNOWN"
    O["V1_RESTART_DELAY"] = "UNKNOWN"
    O["V1_RESTART_RACE"] = "UNKNOWN"
    print("§6 restart:", O["AUTO_RESTART_MECHANISM"], "| race UNKNOWN", flush=True)

    # ---------------- §七 close the MT5 chain from V1 source ----------------
    srcs, term, acct, sym, meth_p, meth_o = [], "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith(".py"):
                continue
            p = os.path.join(r_, f)
            txt = rd(p, 400000) or ""
            if re.search(r"MetaTrader5|mt5\.|positions_get|orders_get", txt, re.I):
                srcs.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                m = re.search(r"terminal64?\.exe", txt, re.I)
                if m and term == "UNKNOWN":
                    mm = re.search(r"[\"']([A-Za-z]:\\\\?[^\"']*terminal[^\"']*\.exe)[\"']", txt, re.I)
                    term = (mm.group(1) if mm else "UNKNOWN")
                ma = re.search(r"(?i)(login|account)\s*[:=]\s*['\"]?(\d{5,})", txt)
                if ma and acct == "UNKNOWN":
                    acct = ma.group(2)
                ms = re.search(r"(?i)symbol\s*[:=]\s*['\"]([A-Z]{3,10})['\"]", txt)
                if ms and sym == "UNKNOWN":
                    sym = ms.group(1)
                if "positions_get" in txt:
                    meth_p = "positions_get"
                if "orders_get" in txt:
                    meth_o = "orders_get"
    O["V1_MT5_SOURCE_FILES"] = srcs[:10]
    O["V1_POSITION_SOURCE"] = "MT5" if meth_p != "UNKNOWN" else "UNKNOWN"
    O["V1_PENDING_ORDER_SOURCE"] = "MT5" if meth_o != "UNKNOWN" else "UNKNOWN"
    O["V1_EXECUTION_STATE_SOURCE"] = "UNKNOWN"
    O["MT5_TERMINAL_CONTEXT"] = term
    O["MT5_ACCOUNT_CONTEXT"] = (f"{acct[:3]}***{acct[-2:]}" if acct != "UNKNOWN" else "UNKNOWN")
    O["MT5_SYMBOL_CONTEXT"] = sym
    O["POSITION_READ_METHOD"] = meth_p
    O["ORDER_READ_METHOD"] = meth_o
    chain_closed = (meth_p != "UNKNOWN" and term != "UNKNOWN" and acct != "UNKNOWN" and sym != "UNKNOWN")
    print(f"§7 MT5 chain: files={len(srcs)} methods={meth_p}/{meth_o} term={term} acct_set={acct!='UNKNOWN'} "
          f"sym={sym} CLOSED={chain_closed}", flush=True)

    # ---------------- §八 read-only trade state (only if the chain is closed) ----------------
    O["OPEN_POSITIONS"] = "UNKNOWN"
    O["PENDING_ORDERS"] = "UNKNOWN"
    O["ACTIVE_ORDER_ACTION"] = "UNKNOWN"
    O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    O["TRADE_STATE_CONFIRMED"] = "NO"
    mt5_note = "chain not closed -> read-only MT5 query not attempted"
    if chain_closed:
        code = ("import json,sys\ntry:\n import MetaTrader5 as mt5\n"
                 f" ok=mt5.initialize()\n"
                 " ps=mt5.positions_get(); os_=mt5.orders_get()\n"
                 " print(json.dumps({'ok':bool(ok),'positions':(0 if ps is None else len(ps)),"
                 "'orders':(0 if os_ is None else len(os_))}))\n mt5.shutdown()\nexcept Exception as e:\n"
                 " print(json.dumps({'err':type(e).__name__+':'+str(e)[:80]}))\n")
        try:
            pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            out = (pr.stdout or "").strip()
            d = json.loads(out.splitlines()[-1]) if out else {}
            if "positions" in d:
                O["OPEN_POSITIONS"] = d["positions"]
                O["PENDING_ORDERS"] = d["orders"]
                O["TRADE_STATE_CONFIRMED"] = "YES"
                O["ACTIVE_ORDER_ACTION"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["ORDER_REQUEST_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["BROKER_OPERATION_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                mt5_note = "read-only positions_get/orders_get executed successfully"
            else:
                mt5_note = f"MT5 read failed: {str(d)[:120]}"
        except Exception as e:  # noqa: BLE001
            mt5_note = f"MT5 read error: {type(e).__name__}"
    O["mt5_read_note"] = mt5_note
    print("§8 trade state:", O["OPEN_POSITIONS"], O["PENDING_ORDERS"], "|", mt5_note[:100], flush=True)

    # ---------------- §九 cycle boundary (not triggered by us) ----------------
    for k in ("CYCLE_START", "ENGINE_START", "DECISION_TIME", "PLAN_TIME", "EXECUTION_TIME", "LEDGER_WRITE_TIME",
                "STATE_WRITE_TIME", "ENGINE_EXIT", "FINAL_WRITE_TIME"):
        O[k] = "UNKNOWN"
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["WRITE_AFTER_ENGINE_EXIT"] = "UNKNOWN"
    O["STATE_WRITE_IN_FLIGHT"] = "UNKNOWN"
    O["CURRENT_CYCLE"] = "UNKNOWN"
    O["OUTSIDE_TRADING_WINDOW"] = "UNKNOWN"
    O["V1_PID_CONFIRMED"] = "NO"
    O["PRIMARY_AUTOMATION_CONFIRMED"] = "NO"

    # ---------------- §十 gate ----------------
    need = {"V1_PID_CONFIRMED": O["V1_PID_CONFIRMED"], "PRIMARY_AUTOMATION_CONFIRMED": O["PRIMARY_AUTOMATION_CONFIRMED"],
             "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
             "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
             "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
             "STATE_WRITE_IN_FLIGHT": O["STATE_WRITE_IN_FLIGHT"], "V1_RESTART_RACE": O["V1_RESTART_RACE"],
             "CURRENT_CYCLE_FINISHED": O["CURRENT_CYCLE"], "OUTSIDE_TRADING_WINDOW": O["OUTSIDE_TRADING_WINDOW"],
             "WRITE_AFTER_ENGINE_EXIT": O["WRITE_AFTER_ENGINE_EXIT"], "SCHEDULE": O["SCHEDULE_CONFIDENCE"],
             "TRADE_STATE_CONFIRMED": O["TRADE_STATE_CONFIRMED"],
             "CYCLE_BOUNDARY": O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"]}
    O["GATE_INPUTS"] = need
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"

    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    rep = {"TASK_STATUS": "V1_GATEWAY_SAFETY_AUDIT_R5_COMPLETE",
            "GATEWAY_V1_AUTOMATION_FOUND": O["GATEWAY_V1_AUTOMATION_FOUND"],
            "GATEWAY_V1_AUTOMATION_SOURCE": O["GATEWAY_V1_AUTOMATION_SOURCE"],
            "GATEWAY_V1_AUTOMATION_ID": O["GATEWAY_V1_AUTOMATION_ID"],
            "GATEWAY_V1_AUTOMATION_ENABLED": O["GATEWAY_V1_AUTOMATION_ENABLED"],
            "V1_M15_SCHEDULE_SOURCE": O["V1_M15_SCHEDULE_SOURCE"], "V1_M15_OFFSET": O["V1_M15_OFFSET"],
            "V1_NEXT_CYCLE": O["V1_NEXT_CYCLE"], "AUTO_RESTART_MECHANISM": O["AUTO_RESTART_MECHANISM"],
            "V1_RESTART_TRIGGER": O["V1_RESTART_TRIGGER"], "V1_RESTART_DELAY": O["V1_RESTART_DELAY"],
            "V1_RESTART_RACE": O["V1_RESTART_RACE"], "V1_POSITION_SOURCE": O["V1_POSITION_SOURCE"],
            "V1_PENDING_ORDER_SOURCE": O["V1_PENDING_ORDER_SOURCE"],
            "V1_EXECUTION_STATE_SOURCE": O["V1_EXECUTION_STATE_SOURCE"],
            "MT5_TERMINAL_CONTEXT": O["MT5_TERMINAL_CONTEXT"], "MT5_ACCOUNT_CONTEXT": O["MT5_ACCOUNT_CONTEXT"],
            "MT5_SYMBOL_CONTEXT": O["MT5_SYMBOL_CONTEXT"], "OPEN_POSITIONS": O["OPEN_POSITIONS"],
            "PENDING_ORDERS": O["PENDING_ORDERS"], "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"],
            "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
            "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
            "CYCLE_START": "UNKNOWN", "ENGINE_START": "UNKNOWN", "DECISION_TIME": "UNKNOWN", "PLAN_TIME": "UNKNOWN",
            "EXECUTION_TIME": "UNKNOWN", "LEDGER_WRITE_TIME": "UNKNOWN", "STATE_WRITE_TIME": "UNKNOWN",
            "ENGINE_EXIT": "UNKNOWN", "FINAL_WRITE_TIME": "UNKNOWN", "WRITE_AFTER_ENGINE_EXIT": "UNKNOWN",
            "STATE_WRITE_IN_FLIGHT": "UNKNOWN", "CURRENT_CYCLE": "UNKNOWN", "OUTSIDE_TRADING_WINDOW": "UNKNOWN",
            "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY": "NO", "SAFETY_WINDOW": "NOT_PROVEN",
            "NEXT_STAGE_AUTHORIZED": "NO", "V1_MODIFIED": "NO", "V2_MODIFIED": "NO",
            "V3_MODIFIED": "NO" if v3 else "UNKNOWN", "ORDER_SEND": 0, "COMMIT": "NONE",
            "ts_utc": NOWU.isoformat(), "SCHEDULE_CONFIDENCE": O["SCHEDULE_CONFIDENCE"],
            "TRADE_STATE_CONFIRMED": O["TRADE_STATE_CONFIRMED"],
            "automation_structured_entry": O["AUTOMATION_STRUCTURED_ENTRY"],
            "mt5_read_note": O["mt5_read_note"], "gate_inputs": need}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_GATEWAY_SAFETY_AUDIT_R5.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §11 FINAL ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3000], flush=True)


if __name__ == "__main__":
    main()
