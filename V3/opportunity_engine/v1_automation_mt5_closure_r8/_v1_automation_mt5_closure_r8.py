# -*- coding: utf-8 -*-
"""V1_AUTOMATION_MT5_CLOSURE_R8 — READ-ONLY. Chain A: OpenClaw read-only automation listing (no mutating verbs).
Chain B: locate the real MT5 connection site (import MetaTrader5 / mt5.initialize / mt5.login) and trace
parameter sources. Then report. No stop/restart/kill/config change/automation change/V1 change/engine replace/
cycle trigger/MT5 write/order/git write/commit. Secrets never read out or stored; accounts masked only.
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
OC = os.path.join(HOME, ".openclaw")
V1 = os.path.join(RE, "hermes", "trader_v1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
R7 = os.path.join(ENGINE, "v1_gateway_account_closure_r7", "V1_GATEWAY_ACCOUNT_CLOSURE_R7.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
NOWU = datetime.now(timezone.utc)
SEC = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|credential|session|cookie)")
MUT = re.compile(r"(?i)\b(create|update|enable|disable|delete|remove|run|trigger|start|stop|restart|set|add|edit)\b")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
FP = []          # false positives rejected (section 13)
MASK = lambda a: (str(a)[:3] + "***" + str(a)[-2:]) if a and len(str(a)) > 6 else "UNKNOWN"


def rd(p, n=400000):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()[:n]
    except Exception:  # noqa: BLE001
        return None


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def run(args, timeout=90):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    r7 = json.load(open(R7, encoding="utf-8")) if os.path.exists(R7) else {}
    O["R7_INPUT"] = {"path": os.path.relpath(R7, AIQ).replace("\\", "/"), "gateway_pid": r7.get("GATEWAY_PROCESS_PID"),
                       "storage": r7.get("GATEWAY_STORAGE_CANDIDATE"), "mt5_terminal": r7.get("MT5_TERMINAL_CONTEXT"),
                       "mt5_symbol": r7.get("MT5_SYMBOL_CONTEXT")}
    GATEWAY_PID = r7.get("GATEWAY_PROCESS_PID", "UNKNOWN")
    GATEWAY_STORAGE = r7.get("GATEWAY_STORAGE_CANDIDATE", OC)
    O["GATEWAY_PID"] = GATEWAY_PID
    O["GATEWAY_STORAGE"] = GATEWAY_STORAGE

    # =============== CHAIN A ===============
    O["CLI_PATH_EXISTS"] = os.path.exists(CLI)
    O["CLI_HELP"] = ""
    if os.path.exists(CLI) and os.path.exists(NODE):
        O["CLI_HELP"] = run([NODE, CLI, "--help"], 60)[:4000]
    help_low = O["CLI_HELP"].lower()
    # read-only list candidates derived from help text
    cand_subs = []
    for kw in ("cron", "automation", "schedule", "workflow", "task"):
        if kw in help_low:
            cand_subs += [[kw, "list"], [kw, "ls"], [kw, "show"], [kw, "status"]]
    O["CLI_HELP_MENTIONS"] = sorted({k for k in ("cron", "automation", "schedule", "workflow", "task", "gateway")
                                       if k in help_low})
    listing, used = "", None
    for sub in cand_subs[:10]:
        if MUT.search(" ".join(sub[1:])):
            continue                      # never use a mutating verb
        # verify the subcommand exists first via its own --help (read-only)
        h = run([NODE, CLI, sub[0], "--help"], 45)
        if h.startswith("ERR:") or "unknown" in h.lower() or "not found" in h.lower():
            continue
        out = run([NODE, CLI] + sub, 60)
        if out and not out.startswith("ERR:") and ("error" not in out.lower()[:200] or "hermes" in out.lower()):
            listing, used = out, " ".join(sub)
            break
    O["CLI_LIST_COMMAND_USED"] = used or "NONE"
    O["CLI_LISTING_RAW"] = (listing or "")[:4000]
    # parse for the V1 automation
    auto = None
    if listing:
        for m in re.finditer(r"(?is)(\{[^{}]*(?:hermes-trader|trader_v1|engine\.py)[^{}]*\})", listing):
            try:
                d = json.loads(m.group(1))
                auto = d
                break
            except Exception:  # noqa: BLE001
                continue
        if auto is None:
            for line in listing.splitlines():
                if re.search(r"(hermes-trader|trader_v1|engine\.py)", line, re.I):
                    auto = {"__text__": line.strip()}
                    break
    O["CLI_AUTOMATION_ENTRY"] = auto or "NOT_FOUND"
    structured = bool(auto) and "__text__" not in (auto or {})

    # A3 fallback: directory-structure-only listing of the storage root (no full read)
    if not structured:
        layout = []
        if os.path.isdir(GATEWAY_STORAGE):
            try:
                for n in sorted(os.listdir(GATEWAY_STORAGE))[:60]:
                    p = os.path.join(GATEWAY_STORAGE, n)
                    if os.path.isdir(p):
                        sub = []
                        try:
                            for n2 in sorted(os.listdir(p))[:25]:
                                p2 = os.path.join(p, n2)
                                sub.append({"name": n2, "dir": os.path.isdir(p2),
                                             "size": (None if os.path.isdir(p2) else os.path.getsize(p2))})
                        except OSError:
                            pass
                        layout.append({"name": n, "dir": True, "children": sub})
                    else:
                        layout.append({"name": n, "dir": False, "size": os.path.getsize(p)})
            except OSError:
                pass
        O["STORAGE_LAYOUT"] = layout
        store_hint = [l["name"] for l in layout if l.get("dir") and re.search(
            r"(?i)automation|cron|schedul|state|store|db|database|task", l["name"])]
        O["STORE_DIR_HINTS"] = store_hint
    else:
        O["STORAGE_LAYOUT"] = "skipped (CLI listing succeeded)"
        O["STORE_DIR_HINTS"] = []

    gv = lambda k, *ks: next(((auto or {}).get(x) for x in (k,) + ks if x in (auto or {})), "UNKNOWN")
    if structured:
        O["V1_AUTOMATION_FOUND"] = "YES"
        O["V1_AUTOMATION_ID"] = gv("id", "name", "taskName")
        O["V1_AUTOMATION_ENABLED"] = gv("enabled", "active")
        O["ACTION"] = gv("action", "command", "execute")
        O["ARGUMENTS"] = gv("args", "arguments")
        O["WORKING_DIRECTORY"] = gv("cwd", "workingDirectory", "workdir")
        O["SCHEDULE_TYPE"] = gv("schedule", "scheduleType", "type", "kind")
        O["SCHEDULE_EXPRESSION"] = gv("expression", "cron", "interval", "every")
        O["TIMEZONE"] = gv("timezone", "tz")
        O["V1_M15_OFFSET"] = gv("offset")
        # linkage proof: the automation must actually reference trader_v1 / engine.py
        blob = json.dumps(auto, ensure_ascii=False)
        O["LINKAGE_PROOF"] = ("trader_v1" in blob) or ("engine.py" in blob)
        if not O["LINKAGE_PROOF"]:
            O["V1_AUTOMATION_FOUND"] = "NO"
            FP.append({"where": "CLI listing", "reason": "entry does not reference trader_v1/engine.py"})
    else:
        O["V1_AUTOMATION_FOUND"] = "NO"
        for k in ("V1_AUTOMATION_ID", "V1_AUTOMATION_ENABLED", "ACTION", "ARGUMENTS", "WORKING_DIRECTORY",
                    "SCHEDULE_TYPE", "SCHEDULE_EXPRESSION", "TIMEZONE", "V1_M15_OFFSET", "LINKAGE_PROOF"):
            O[k] = "UNKNOWN"
    O["V1_M15_SCHEDULE_SOURCE"] = ((O["CLI_LIST_COMMAND_USED"] or "UNKNOWN") if O["V1_AUTOMATION_FOUND"] == "YES"
                                     else "UNKNOWN")
    O["LAST_EXPECTED_V1_CYCLE"] = O["NEXT_EXPECTED_V1_CYCLE"] = O["MINUTES_TO_NEXT_V1_CYCLE"] = "UNKNOWN"
    O["SCHEDULE_CONFIDENCE"] = "UNKNOWN"
    if O["V1_AUTOMATION_FOUND"] == "YES" and str(O["SCHEDULE_EXPRESSION"]) not in ("UNKNOWN", "None"):
        m = re.match(r"\*/(\d+)", str(O["SCHEDULE_EXPRESSION"]))
        if m:
            st = int(m.group(1)); nm = NOWU.replace(second=0, microsecond=0)
            add = st - (nm.minute % st)
            O["NEXT_EXPECTED_V1_CYCLE"] = nm.replace(minute=nm.minute + add).isoformat()
            O["MINUTES_TO_NEXT_V1_CYCLE"] = add
            O["SCHEDULE_CONFIDENCE"] = "CONFIRMED_INTERVAL"
    print(f"§A cli_used={O['CLI_LIST_COMMAND_USED']} found={O['V1_AUTOMATION_FOUND']} "
          f"id={O['V1_AUTOMATION_ID']} sched={O['SCHEDULE_EXPRESSION']}", flush=True)

    # =============== CHAIN B ===============
    conn_hits = []
    for r_, ds, fs in os.walk(V1):
        rl = r_.lower()
        if any(x in rl for x in ("run_state", "__pycache__", "replay", "backup")):
            continue
        for f in fs:
            if not f.lower().endswith(".py"):
                continue
            p = os.path.join(r_, f)
            txt = rd(p, 400000) or ""
            for m in re.finditer(r"(?m)^.{0,120}(?:import\s+MetaTrader5|from\s+MetaTrader5|"
                                   r"(?:mt5|MT5)\.initialize\s*\(|(?:mt5|MT5)\.login\s*\(|"
                                   r"(?:mt5|MT5)\.account_info\s*\(|(?:mt5|MT5)\.terminal_info\s*\()", txt):
                line = m.group(0).strip()
                conn_hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"),
                                    "line_no": txt[:m.start()].count("\n") + 1,
                                    "code": re.sub(r"(?i)(password|passwd|secret|token)\s*=\s*\S+", r"\1=<REDACTED>", line)[:200]})
                if len(conn_hits) > 40:
                    break
    O["MT5_CONNECTION_SITES"] = conn_hits[:20]
    # pick the real connection module = the file with mt5.initialize and/or mt5.login
    conn_mod = next((h["file"] for h in conn_hits if re.search(r"\.(initialize|login)\s*\(", h["code"])), "UNKNOWN")
    O["MT5_CONNECTION_MODULE"] = conn_mod
    ctx = {"terminal": "UNKNOWN", "account": "UNKNOWN", "server": "UNKNOWN", "init_src": "UNKNOWN",
            "login_src": "UNKNOWN", "acct_src": "UNKNOWN", "env_keys": [], "cfg_files": [], "secret_present": "NO"}
    if conn_mod != "UNKNOWN":
        txt = rd(os.path.join(AIQ, conn_mod), 400000) or ""
        for m in re.finditer(r"(?m)^(.{0,200})$", txt):
            ln = m.group(1)
            if re.search(r"(?i)(mt5|MT5)\.initialize\s*\(", ln):
                ctx["init_src"] = re.sub(r"(?i)(password|secret|token)\s*=\s*\S+", r"\1=<REDACTED>", ln.strip())[:180]
            if re.search(r"(?i)(mt5|MT5)\.login\s*\(", ln):
                ctx["login_src"] = re.sub(r"(?i)(password|secret|token)\s*=\s*\S+", r"\1=<REDACTED>", ln.strip())[:180]
        for m in re.finditer(r"(?i)(terminal_path|path)\s*[:=]\s*r?[\"']([^\"']*terminal[^\"']*\.exe)[\"']", txt):
            ctx["terminal"] = m.group(2)
        for m in re.finditer(r"(?i)server\s*[:=]\s*[\"']([^\"']+)[\"']", txt):
            ctx["server"] = m.group(1)
        ctx["env_keys"] = sorted({m.group(1) for m in re.finditer(
            r"(?:getenv|environ(?:\.get)?)\s*\(?\s*[\"']([A-Z0-9_]+)[\"']", txt)})
        for m in re.finditer(r"[\"']([\w./\\-]+\.(?:json|ini|env|txt))[\"']", txt):
            for c in (os.path.join(V1, m.group(1)), os.path.join(AIQ, m.group(1))):
                if os.path.exists(c) and c not in ctx["cfg_files"]:
                    ctx["cfg_files"].append(c)
        # account from config (masked) or from env key names
        for cf in ctx["cfg_files"][:5]:
            ct = rd(cf, 200000) or ""
            for m in re.finditer(r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*(\S+)", ct):
                k, v = m.group(1), m.group(2)
                if SEC.search(k):
                    continue
                if re.search(r"(?i)login|account", k):
                    ctx["account"] = MASK(v)
                    ctx["acct_src"] = "config:" + os.path.relpath(cf, AIQ).replace("\\", "/")
                if re.search(r"(?i)server", k) and ctx["server"] == "UNKNOWN":
                    ctx["server"] = v[:60]
                if re.search(r"(?i)symbol", k):
                    pass
            if re.search(r"(?i)(password|token|secret)\s*=", ct):
                ctx["secret_present"] = "YES"
        if ctx["account"] == "UNKNOWN" and any(re.search(r"(?i)login|account", k) for k in ctx["env_keys"]):
            ctx["acct_src"] = "ENV_VAR_DECLARED_IN_CODE"
    O["MT5_INITIALIZE_SOURCE"] = ctx["init_src"]
    O["MT5_LOGIN_SOURCE"] = ctx["login_src"]
    O["ACCOUNT_SOURCE"] = ctx["acct_src"]
    O["ACCOUNT_MASKED"] = ctx["account"]
    O["SERVER"] = ctx["server"]
    O["MT5_TERMINAL_CONTEXT"] = ctx["terminal"] if ctx["terminal"] != "UNKNOWN" else r7.get("MT5_TERMINAL_CONTEXT", "UNKNOWN")
    O["MT5_SYMBOL_CONTEXT"] = r7.get("MT5_SYMBOL_CONTEXT", "XAUUSD")
    O["MT5_ENV_KEYS_SEEN"] = ctx["env_keys"][:15]
    O["MT5_CONFIG_FILES"] = [os.path.relpath(c, AIQ).replace("\\", "/") for c in ctx["cfg_files"][:6]]
    O["MT5_SECRET_PRESENT"] = ctx["secret_present"]
    same_chain = (conn_mod != "UNKNOWN" and ctx["init_src"] != "UNKNOWN" and O["MT5_TERMINAL_CONTEXT"] != "UNKNOWN"
                   and ctx["account"] != "UNKNOWN" and ctx["server"] != "UNKNOWN")
    O["MT5_CONTEXT_CHAIN"] = "CONFIRMED" if same_chain else ("PARTIAL" if conn_mod != "UNKNOWN" else "UNKNOWN")
    print(f"§B conn_module={conn_mod} init={'Y' if ctx['init_src']!='UNKNOWN' else 'N'} "
          f"acct={ctx['account']} server={ctx['server']} CHAIN={O['MT5_CONTEXT_CHAIN']}", flush=True)

    # =============== §九 read-only state only if CONFIRMED ===============
    O["OPEN_POSITIONS"] = O["PENDING_ORDERS"] = "UNKNOWN"
    O["TRADE_STATE_CONFIRMED"] = "NO"
    note = "MT5_CONTEXT_CHAIN != CONFIRMED -> read-only query not attempted"
    if O["MT5_CONTEXT_CHAIN"] == "CONFIRMED":
        code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
                 f" ok=mt5.initialize(path=r'{O['MT5_TERMINAL_CONTEXT']}')\n"
                 " ps=mt5.positions_get(symbol='XAUUSD')\n os_=mt5.orders_get(symbol='XAUUSD')\n"
                 " print(json.dumps({'ok':bool(ok),'positions':(None if ps is None else len(ps)),"
                 "'orders':(None if os_ is None else len(os_))}))\n mt5.shutdown()\nexcept Exception as e:\n"
                 " print(json.dumps({'err':type(e).__name__+':'+str(e)[:90]}))\n")
        try:
            pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=120)
            d = json.loads((pr.stdout or "{}").strip().splitlines()[-1]) if (pr.stdout or "").strip() else {}
            if d.get("positions") is not None and d.get("orders") is not None:
                O["OPEN_POSITIONS"], O["PENDING_ORDERS"] = d["positions"], d["orders"]
                O["TRADE_STATE_CONFIRMED"] = "YES"
                note = "read-only positions_get/orders_get(symbol=XAUUSD) executed"
            else:
                note = f"MT5 read failed: {str(d)[:120]}"
        except Exception as e:  # noqa: BLE001
            note = f"MT5 read error: {type(e).__name__}"
    O["mt5_read_note"] = note

    # =============== §十一 protection + §十三 report ===============
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    O["FALSE_POSITIVE_REJECTED"] = FP + [
        {"where": "R6 §五", "reason": "GATEWAY_V1_AUTOMATION_FOUND=YES 来源于 %TEMP% 下的 V2-SHADOW run_manifest — REJECTED"},
        {"where": "R7 §六", "reason": "GATEWAY_V1_AUTOMATION_FOUND=YES 来源于 .openclaw/workspace/v2_snap.json — REJECTED"}
    ] if True else FP
    rep = {"TASK_STATUS": "V1_AUTOMATION_MT5_CLOSURE_R8_COMPLETE",
            "GATEWAY_PID": GATEWAY_PID, "GATEWAY_STORAGE": GATEWAY_STORAGE,
            "V1_AUTOMATION_FOUND": O["V1_AUTOMATION_FOUND"], "V1_AUTOMATION_ID": O["V1_AUTOMATION_ID"],
            "V1_AUTOMATION_ENABLED": O["V1_AUTOMATION_ENABLED"], "ACTION": O["ACTION"],
            "ARGUMENTS": O["ARGUMENTS"], "WORKING_DIRECTORY": O["WORKING_DIRECTORY"],
            "SCHEDULE_TYPE": O["SCHEDULE_TYPE"], "SCHEDULE_EXPRESSION": O["SCHEDULE_EXPRESSION"],
            "TIMEZONE": O["TIMEZONE"], "V1_M15_SCHEDULE_SOURCE": O["V1_M15_SCHEDULE_SOURCE"],
            "V1_M15_OFFSET": O["V1_M15_OFFSET"], "LAST_EXPECTED_V1_CYCLE": O["LAST_EXPECTED_V1_CYCLE"],
            "NEXT_EXPECTED_V1_CYCLE": O["NEXT_EXPECTED_V1_CYCLE"],
            "SCHEDULE_CONFIDENCE": O["SCHEDULE_CONFIDENCE"],
            "MT5_CONNECTION_MODULE": O["MT5_CONNECTION_MODULE"], "MT5_INITIALIZE_SOURCE": O["MT5_INITIALIZE_SOURCE"],
            "MT5_LOGIN_SOURCE": O["MT5_LOGIN_SOURCE"], "ACCOUNT_SOURCE": O["ACCOUNT_SOURCE"],
            "ACCOUNT_MASKED": O["ACCOUNT_MASKED"], "SERVER": O["SERVER"],
            "MT5_TERMINAL_CONTEXT": O["MT5_TERMINAL_CONTEXT"], "MT5_SYMBOL_CONTEXT": O["MT5_SYMBOL_CONTEXT"],
            "MT5_CONTEXT_CHAIN": O["MT5_CONTEXT_CHAIN"], "OPEN_POSITIONS": O["OPEN_POSITIONS"],
            "PENDING_ORDERS": O["PENDING_ORDERS"], "TRADE_STATE_CONFIRMED": O["TRADE_STATE_CONFIRMED"],
            "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY": "NO", "SAFETY_WINDOW": "NOT_PROVEN",
            "NEXT_STAGE_AUTHORIZED": "NO", "V1_MODIFIED": "NO", "V2_MODIFIED": "NO",
            "V3_MODIFIED": "NO" if v3 else "UNKNOWN", "ORDER_SEND": 0, "COMMIT": "NONE",
            "CLI_LIST_COMMAND_USED": O["CLI_LIST_COMMAND_USED"], "CLI_LISTING_RAW": O["CLI_LISTING_RAW"][:1500],
            "MT5_CONNECTION_SITES": O["MT5_CONNECTION_SITES"][:8],
            "MT5_CONFIG_FILES": O["MT5_CONFIG_FILES"], "MT5_ENV_KEYS_SEEN": O["MT5_ENV_KEYS_SEEN"],
            "MT5_SECRET_PRESENT": O["MT5_SECRET_PRESENT"], "STORAGE_LAYOUT": O["STORAGE_LAYOUT"],
            "STORE_DIR_HINTS": O["STORE_DIR_HINTS"], "mt5_read_note": note, "V3_HASHES": imm,
            "FALSE_POSITIVE_REJECTED": O["FALSE_POSITIVE_REJECTED"], "ts_utc": NOWU.isoformat()}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_AUTOMATION_MT5_CLOSURE_R8.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §13 FINAL ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3400], flush=True)
    print("\nFALSE_POSITIVE_REJECTED:", json.dumps(O["FALSE_POSITIVE_REJECTED"], ensure_ascii=False)[:600], flush=True)


if __name__ == "__main__":
    main()
