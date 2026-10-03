# -*- coding: utf-8 -*-
"""V1_GATEWAY_ACCOUNT_CLOSURE_R7 — READ-ONLY. Two closures only (gateway context, MT5 account), then
read-only positions/orders IF and only if MT5_CONTEXT_CHAIN == CONFIRMED.

No stop/restart/kill/config change/automation change/V1 change/engine.py replace/cycle trigger/MT5 write/
git write/commit. Secrets are never read out, printed, or stored: only presence flags and masked accounts.
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
R6 = os.path.join(ENGINE, "v1_gateway_account_closure_r6", "V1_GATEWAY_ACCOUNT_CLOSURE_R6.json")
NOWU = datetime.now(timezone.utc)
SECRET_RE = re.compile(r"(?i)(token|password|passwd|secret|api[_-]?key|cookie|credential|auth|session)")
EXCL = ("media", "logs", "temp", "pasted-text", "readme", "skill", "reports", "v2-shadow", "run_manifest",
         "archive", "node_modules", ".git", "__pycache__")
KW = ("hermes-trader-m15-cycle", "trader_v1", "engine.py", "xauusd", "maximum_holding_time")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


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


def redact(s):
    if not s:
        return s
    out = s
    out = re.sub(r"(?i)(--?(?:token|password|passwd|secret|api[-_]?key|cookie|auth|session)[= ]+)(\S+)", r"\1<REDACTED>", out)
    out = re.sub(r"(?i)((?:TOKEN|PASSWORD|PASSWD|SECRET|API_KEY|COOKIE|AUTH|SESSION)\s*=\s*)(\S+)", r"\1<REDACTED>", out)
    return out


def mask_acct(a):
    a = str(a)
    return (a[:3] + "***" + a[-2:]) if len(a) > 6 else "UNKNOWN"


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    # ---------------- §三 read R6 ----------------
    r6 = json.load(open(R6, encoding="utf-8")) if os.path.exists(R6) else {}
    O["R6_PATH"] = os.path.relpath(R6, AIQ).replace("\\", "/")
    O["R6_GATEWAY_PROCESSES_RAW"] = r6.get("gateway_processes", "")
    O["R6_GATEWAY_CMD"] = (r6.get("gateway_cmd_text") or "")[:1500]
    O["R6_MT5_TRACE_CHAIN"] = r6.get("MT5_TRACE_CHAIN", r6.get("MT5_TRACE_CHAIN", []))
    O["R6_MT5_SOURCE_FILES"] = r6.get("V1_MT5_SOURCE_FILES_R5", r6.get("V1_MT5_SOURCE_FILES", []))
    print("§3 R6 read: processes_captured=", bool(O["R6_GATEWAY_PROCESSES_RAW"]),
          "trace_chain=", len(O["R6_MT5_TRACE_CHAIN"] or []), flush=True)

    # ---------------- §四 gateway process context ----------------
    procs = []
    try:
        raw = O["R6_GATEWAY_PROCESSES_RAW"]
        if raw and raw.strip().startswith(("{", "[")):
            d = json.loads(raw)
            procs = d if isinstance(d, list) else [d]
    except Exception:  # noqa: BLE001
        procs = []
    # if R6 capture empty, re-capture (read-only)
    if not procs:
        try:
            p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                 "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'openclaw|gateway'} | "
                                 "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 4"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            d = json.loads(p.stdout or "[]")
            procs = d if isinstance(d, list) else [d]
        except Exception:  # noqa: BLE001
            procs = []
    gw = []
    for x in procs:
        cl = x.get("CommandLine") or ""
        if re.search(r"gateway|openclaw", cl, re.I):
            gw.append({"PID": x.get("ProcessId"), "PPID": x.get("ParentProcessId"), "IMAGE": x.get("Name"),
                        "COMMAND_LINE_RAW": cl})
    primary = None
    for g in gw:
        if re.search(r"gateway\.(cmd|vbs)|node_modules[\\/]openclaw|openclaw[\\/].*gateway", g["COMMAND_LINE_RAW"], re.I):
            primary = g
    primary = primary or (gw[0] if gw else None)
    O["GATEWAY_PROCESSES"] = [{"PID": g["PID"], "PPID": g["PPID"], "IMAGE": g["IMAGE"],
                                 "COMMAND_LINE": redact(g["COMMAND_LINE_RAW"])[:600]} for g in gw[:6]]
    O["GATEWAY_PROCESS_PID"] = (primary or {}).get("PID", "UNKNOWN")
    O["GATEWAY_PARENT_PID"] = (primary or {}).get("PPID", "UNKNOWN")
    O["GATEWAY_COMMAND_LINE"] = (redact((primary or {}).get("COMMAND_LINE_RAW", ""))[:700] or "UNKNOWN")
    cl = (primary or {}).get("COMMAND_LINE_RAW", "") or ""
    flags = dict(re.findall(r"--(config|state|workspace|profile|data|home)[= ]+\"?([^\"\s]+)\"?", cl))
    paths = re.findall(r"[A-Za-z]:\\\\?[^\"\s]+", cl)
    O["GATEWAY_FLAGS"] = flags
    O["GATEWAY_PATH_HINTS"] = paths[:8]
    # storage candidate: .openclaw home / --data / --workspace / openclaw install dir
    cand = None
    for k in ("data", "workspace", "state", "home"):
        v = flags.get(k)
        if v and os.path.exists(v):
            cand = v
            break
    if not cand:
        m = re.search(r"([A-Za-z]:\\[^\"\s]*?\.openclaw)", cl)
        if m and os.path.isdir(m.group(1)):
            cand = m.group(1)
    if not cand and os.path.isdir(OC):
        cand = OC
    O["GATEWAY_STORAGE_CANDIDATE"] = cand or "UNKNOWN"
    O["GATEWAY_CONFIG_PATH"] = flags.get("config") or ((r6.get("GATEWAY_CONFIG_PATH") if isinstance(r6, dict) else None) or "UNKNOWN")
    O["GATEWAY_STATE_PATH"] = flags.get("state") or "UNKNOWN"
    O["GATEWAY_WORKSPACE_PATH"] = flags.get("workspace") or "UNKNOWN"
    O["GATEWAY_PROFILE"] = flags.get("profile") or "UNKNOWN"
    print(f"§4 gateway: procs={len(gw)} pid={O['GATEWAY_PROCESS_PID']} flags={flags} storage="
          f"{str(O['GATEWAY_STORAGE_CANDIDATE'])[:70]}", flush=True)

    # ---------------- §五 env (only if storage unknown) ----------------
    O["GATEWAY_ENV_READ"] = "NOT_ATTEMPTED" if O["GATEWAY_STORAGE_CANDIDATE"] != "UNKNOWN" else "NOT_AVAILABLE"
    O["GATEWAY_SECRET_PRESENT"] = "UNKNOWN"
    O["GATEWAY_ENV_NOTE"] = ("reading another process's environment requires elevation and is not performed; "
                              "no secret value was read, printed or stored")
    if O["GATEWAY_STORAGE_CANDIDATE"] != "UNKNOWN":
        O["GATEWAY_ENV_READ"] = "SKIPPED_STORAGE_RESOLVED"
    print("§5 env:", O["GATEWAY_ENV_READ"], flush=True)

    # ---------------- §六 targeted automation search in the real storage ----------------
    hits = []
    root = O["GATEWAY_STORAGE_CANDIDATE"]
    if root != "UNKNOWN" and os.path.isdir(root):
        for r_, ds, fs in os.walk(root):
            rl = r_.lower()
            if any(e in rl for e in EXCL):
                continue
            for f in fs:
                fl = f.lower()
                if any(e in fl for e in EXCL):
                    continue
                if not fl.endswith((".json", ".jsonl", ".yaml", ".yml", ".js", ".cjs", ".db", ".sqlite")):
                    continue
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > 4_000_000:
                        continue
                except OSError:
                    continue
                txt = rd(p, 4_000_000)
                if not txt:
                    continue
                low = txt.lower()
                if any(k in low for k in KW):
                    hit = {"source": os.path.relpath(p, AIQ).replace("\\", "/"),
                            "matched": [k for k in KW if k in low][:4]}
                    try:
                        doc = json.loads(txt)
                        hit["structured"] = True
                        if isinstance(doc, dict):
                            hit["entry"] = {k: (v if not isinstance(v, (dict, list)) else str(v)[:200])
                                             for k, v in doc.items()}
                    except Exception:  # noqa: BLE001
                        hit["structured"] = False
                    hits.append(hit)
                if len(hits) >= 15:
                    break
            if len(hits) >= 15:
                break
    struct = [h for h in hits if h.get("structured")]
    O["AUTOMATION_HITS"] = hits[:8]
    O["GATEWAY_V1_AUTOMATION_FOUND"] = "YES" if struct else "NO"
    O["GATEWAY_V1_AUTOMATION_SOURCE"] = (struct[0]["source"] if struct else "NOT_FOUND")
    ent = (struct[0].get("entry") or {}) if struct else {}
    gv = lambda *ks: next((ent[k] for k in ent for kk in ks if k.lower() == kk), "UNKNOWN")
    O["GATEWAY_V1_AUTOMATION_ID"] = gv("id", "name") if struct else "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ENABLED"] = gv("enabled") if struct else "UNKNOWN"
    O["ACTION"] = gv("action", "command", "execute") if struct else "UNKNOWN"
    O["ARGUMENTS"] = gv("args", "arguments") if struct else "UNKNOWN"
    O["WORKING_DIRECTORY"] = gv("cwd", "workingdirectory") if struct else "UNKNOWN"
    print(f"§6 automation: root={str(root)[:60]} hits={len(hits)} structured={len(struct)}", flush=True)

    # ---------------- §七 schedule (real automation only) ----------------
    O["SCHEDULE_TYPE"] = gv("schedule", "scheduletype", "type") if struct else "UNKNOWN"
    O["SCHEDULE_EXPRESSION"] = gv("cron", "expression", "interval", "every") if struct else "UNKNOWN"
    O["TIMEZONE"] = gv("timezone", "tz") if struct else "UNKNOWN"
    O["V1_M15_OFFSET"] = gv("offset") if struct else "UNKNOWN"
    O["V1_M15_SCHEDULE_SOURCE"] = O["GATEWAY_V1_AUTOMATION_SOURCE"] if struct else "UNKNOWN"
    O["LAST_EXPECTED_V1_CYCLE"] = O["NEXT_EXPECTED_V1_CYCLE"] = O["MINUTES_TO_NEXT_V1_CYCLE"] = "UNKNOWN"
    O["V1_NEXT_CYCLE"] = "UNKNOWN"
    O["SCHEDULE_CONFIDENCE"] = "UNKNOWN"
    if struct and str(O["SCHEDULE_EXPRESSION"]) not in ("UNKNOWN", "None"):
        m = re.match(r"\*/(\d+)", str(O["SCHEDULE_EXPRESSION"]))
        if m:
            st = int(m.group(1)); nm = NOWU.replace(second=0, microsecond=0)
            add = st - (nm.minute % st)
            nxt = nm.replace(minute=nm.minute + add)
            O["NEXT_EXPECTED_V1_CYCLE"] = O["V1_NEXT_CYCLE"] = nxt.isoformat()
            O["MINUTES_TO_NEXT_V1_CYCLE"] = add
            O["SCHEDULE_CONFIDENCE"] = "CONFIRMED_INTERVAL"
    print("§7 schedule:", O["SCHEDULE_CONFIDENCE"], O["SCHEDULE_EXPRESSION"], flush=True)

    # ---------------- §十二 restart (real automation only) ----------------
    O["AUTO_RESTART_MECHANISM"] = ("YES" if struct and str(gv("restart", "retry", "onexit", "watchdog", "keepalive"))
                                     not in ("UNKNOWN", "None", "False") else "UNKNOWN")
    O["V1_RESTART_TRIGGER"] = O["V1_RESTART_DELAY"] = O["V1_RESTART_RACE"] = "UNKNOWN"
    print("§12 restart:", O["AUTO_RESTART_MECHANISM"], "| RACE=UNKNOWN", flush=True)

    # ---------------- §八/§九/§十 MT5 chain ----------------
    eng = os.path.join(V1, "engine.py")
    etxt = rd(eng, 500000) or ""
    # find the object used for positions_get/orders_get
    callers = sorted({m.group(1) for m in re.finditer(r"([A-Za-z_][\w]*)\.(?:positions_get|orders_get)\s*\(", etxt)})
    O["MT5_CALL_OBJECTS"] = callers
    mods = []
    for name in callers + sorted({m.group(1) for m in re.finditer(r"(?m)^\s*(?:import|from)\s+([a-zA-Z_][\w]*)", etxt)
                                    if os.path.exists(os.path.join(V1, m.group(1) + ".py"))}):
        for cand in (os.path.join(V1, name + ".py"), os.path.join(V1, name, "__init__.py")):
            if os.path.exists(cand) and cand not in mods:
                mods.append(cand)
    if os.path.exists(eng):
        mods.insert(0, eng)
    ctx = {"terminal": "UNKNOWN", "account": "UNKNOWN", "server": "UNKNOWN", "symbol": "UNKNOWN",
            "account_source": "UNKNOWN", "account_present": "NO", "login_form": "NO",
            "config_files": [], "env_keys": [], "api_tokens": []}
    chain = []
    for p in mods[:8]:
        txt = rd(p, 500000) or ""
        rel = os.path.relpath(p, AIQ).replace("\\", "/")
        toks = sorted({m.group(1) for m in re.finditer(r"(?:mt5|MT5)\.(initialize|login|account_info|terminal_info|"
                                                        r"positions_get|orders_get|symbol_info)", txt)})
        envk = sorted({m.group(1) for m in re.finditer(r"(?:getenv|environ(?:\.get)?)\s*\(?\s*[\"']([A-Z0-9_]+)[\"']", txt)})
        chain.append({"module": rel, "mt5_calls": toks, "env_keys": envk[:12]})
        ctx["api_tokens"] += toks
        ctx["env_keys"] += envk
        mi = re.search(r"(?m)^\s*(?:mt5|MT5)\.initialize\(([^)]{0,400})\)", txt)
        ml = re.search(r"(?m)^\s*(?:mt5|MT5)\.login\(([^)]{0,400})\)", txt)
        if ml:
            ctx["login_form"] = "PRESENT"
        ms = re.search(r"(?i)server\s*[:=]\s*[\"']([^\"']+)[\"']", txt)
        if ms and ctx["server"] == "UNKNOWN":
            ctx["server"] = ms.group(1)
        mt = re.search(r"(?i)(?:terminal_path|path)\s*[:=]\s*r?[\"']([^\"']*terminal[^\"']*\.exe)[\"']", txt)
        if mt and ctx["terminal"] == "UNKNOWN":
            ctx["terminal"] = mt.group(1)
        msym = re.search(r"(?i)symbol\s*[:=]\s*[\"']([A-Z]{3,10})[\"']", txt)
        if msym and ctx["symbol"] == "UNKNOWN":
            ctx["symbol"] = msym.group(1)
        for mf in re.finditer(r"[\"']([\w./\\-]+\.(?:json|ini|env|txt))[\"']", txt):
            for c2 in (os.path.join(V1, mf.group(1)), os.path.join(RE, "hermes", mf.group(1)),
                        os.path.join(AIQ, mf.group(1))):
                if os.path.exists(c2) and c2 not in ctx["config_files"]:
                    ctx["config_files"].append(c2)
    # read credential/config files: KEYS ONLY for sensitive values, masked account
    for cf in ctx["config_files"][:6]:
        txt = rd(cf, 200000) or ""
        for m in re.finditer(r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*(\S+)", txt):
            k, v = m.group(1), m.group(2)
            if SECRET_RE.search(k):
                continue                     # never read/store secret values
            if re.search(r"(?i)login|account", k):
                ctx["account"] = mask_acct(v)
                ctx["account_present"] = "YES"
                ctx["account_source"] = "config:" + os.path.relpath(cf, AIQ).replace("\\", "/")
            if re.search(r"(?i)server", k) and ctx["server"] == "UNKNOWN":
                ctx["server"] = v[:60]
            if re.search(r"(?i)terminal|path", k) and ctx["terminal"] == "UNKNOWN":
                ctx["terminal"] = v[:120]
            if re.search(r"(?i)symbol", k) and ctx["symbol"] == "UNKNOWN":
                ctx["symbol"] = v[:20]
        if re.search(r"(?i)(password|token|secret|api[_-]?key)\s*=", txt):
            ctx["secret_present"] = "YES"
    # env-var based account
    if ctx["account"] == "UNKNOWN" and any(re.search(r"(?i)login|account", k) for k in ctx["env_keys"]):
        ctx["account_present"] = "YES"
        ctx["account_source"] = "ENV_VAR_DECLARED_IN_CODE"
    O["MT5_TRACE_CHAIN"] = chain
    O["MT5_TERMINAL_CONTEXT"] = ctx["terminal"] if ctx["terminal"] != "UNKNOWN" else r6.get("MT5_TERMINAL_CONTEXT", "UNKNOWN")
    O["MT5_ACCOUNT_CONTEXT"] = ctx["account"]
    O["MT5_SERVER_CONTEXT"] = ctx["server"]
    O["MT5_SYMBOL_CONTEXT"] = ctx["symbol"] if ctx["symbol"] != "UNKNOWN" else r6.get("MT5_SYMBOL_CONTEXT", "XAUUSD")
    O["ACCOUNT_SOURCE"] = ctx["account_source"]
    O["ACCOUNT_PRESENT"] = ctx["account_present"]
    O["ACCOUNT_MASKED"] = ctx["account"]
    O["MT5_LOGIN_FORM_PRESENT"] = ctx["login_form"]
    O["MT5_CONFIG_FILES_READ"] = [os.path.relpath(c, AIQ).replace("\\", "/") for c in ctx["config_files"][:6]]
    O["MT5_ENV_KEYS_SEEN"] = sorted(set(ctx["env_keys"]))[:15]
    O["MT5_SECRET_PRESENT"] = ctx.get("secret_present", "NO")
    O["MT5_API_TOKENS"] = sorted(set(ctx["api_tokens"]))
    conf = (O["MT5_TERMINAL_CONTEXT"] not in ("UNKNOWN", None) and O["MT5_ACCOUNT_CONTEXT"] not in ("UNKNOWN", None)
             and O["MT5_SERVER_CONTEXT"] not in ("UNKNOWN", None) and O["MT5_SYMBOL_CONTEXT"] == "XAUUSD")
    O["MT5_CONTEXT_CHAIN"] = "CONFIRMED" if conf else ("PARTIAL" if O["MT5_TERMINAL_CONTEXT"] not in ("UNKNOWN", None)
                                                         else "UNKNOWN")
    print(f"§8-10 MT5: terminal={str(O['MT5_TERMINAL_CONTEXT'])[:45]} account={O['MT5_ACCOUNT_CONTEXT']} "
          f"server={O['MT5_SERVER_CONTEXT']} sym={O['MT5_SYMBOL_CONTEXT']} "
          f"src={O['ACCOUNT_SOURCE']} CHAIN={O['MT5_CONTEXT_CHAIN']}", flush=True)

    # ---------------- §十一 read-only state (CONFIRMED only) ----------------
    O["OPEN_POSITIONS"] = O["PENDING_ORDERS"] = O["ACTIVE_ORDER_ACTION"] = O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    O["TRADE_STATE_CONFIRMED"] = "NO"
    note = "MT5_CONTEXT_CHAIN != CONFIRMED -> read-only query not attempted (section 11)"
    if O["MT5_CONTEXT_CHAIN"] == "CONFIRMED":
        code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
                 f" ok=mt5.initialize(path=r'{O['MT5_TERMINAL_CONTEXT']}')\n"
                 " ps=mt5.positions_get(symbol='XAUUSD')\n os_=mt5.orders_get(symbol='XAUUSD')\n"
                 " print(json.dumps({'ok':bool(ok),'positions':(None if ps is None else len(ps)),"
                 "'orders':(None if os_ is None else len(os_))}))\n mt5.shutdown()\nexcept Exception as e:\n"
                 " print(json.dumps({'err':type(e).__name__+':'+str(e)[:100]}))\n")
        try:
            pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=120)
            d = json.loads((pr.stdout or "{}").strip().splitlines()[-1]) if (pr.stdout or "").strip() else {}
            if d.get("positions") is not None and d.get("orders") is not None:
                O["OPEN_POSITIONS"], O["PENDING_ORDERS"] = d["positions"], d["orders"]
                O["TRADE_STATE_CONFIRMED"] = "YES"
                O["ACTIVE_ORDER_ACTION"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["ORDER_REQUEST_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["BROKER_OPERATION_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                note = "read-only positions_get/orders_get(symbol=XAUUSD) executed"
            else:
                note = f"MT5 read failed: {str(d)[:120]}"
        except Exception as e:  # noqa: BLE001
            note = f"MT5 read error: {type(e).__name__}"
    O["mt5_read_note"] = note
    print("§11 state:", O["OPEN_POSITIONS"], O["PENDING_ORDERS"], "|", note[:100], flush=True)

    # ---------------- §十五 report + §十七 protection ----------------
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"
    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    rep = {"TASK_STATUS": "V1_GATEWAY_ACCOUNT_CLOSURE_R7_COMPLETE",
            "GATEWAY_PROCESS_PID": O["GATEWAY_PROCESS_PID"], "GATEWAY_PARENT_PID": O["GATEWAY_PARENT_PID"],
            "GATEWAY_COMMAND_LINE": O["GATEWAY_COMMAND_LINE"][:300],
            "GATEWAY_STORAGE_CANDIDATE": O["GATEWAY_STORAGE_CANDIDATE"], "GATEWAY_CONFIG_PATH": O["GATEWAY_CONFIG_PATH"],
            "GATEWAY_STATE_PATH": O["GATEWAY_STATE_PATH"], "GATEWAY_WORKSPACE_PATH": O["GATEWAY_WORKSPACE_PATH"],
            "GATEWAY_PROFILE": O["GATEWAY_PROFILE"], "GATEWAY_SECRET_PRESENT": O["GATEWAY_SECRET_PRESENT"],
            "GATEWAY_V1_AUTOMATION_FOUND": O["GATEWAY_V1_AUTOMATION_FOUND"],
            "GATEWAY_V1_AUTOMATION_SOURCE": O["GATEWAY_V1_AUTOMATION_SOURCE"],
            "GATEWAY_V1_AUTOMATION_ID": O["GATEWAY_V1_AUTOMATION_ID"],
            "GATEWAY_V1_AUTOMATION_ENABLED": O["GATEWAY_V1_AUTOMATION_ENABLED"],
            "ACTION": O["ACTION"], "ARGUMENTS": O["ARGUMENTS"], "WORKING_DIRECTORY": O["WORKING_DIRECTORY"],
            "SCHEDULE_TYPE": O["SCHEDULE_TYPE"], "SCHEDULE_EXPRESSION": O["SCHEDULE_EXPRESSION"],
            "TIMEZONE": O["TIMEZONE"], "V1_M15_SCHEDULE_SOURCE": O["V1_M15_SCHEDULE_SOURCE"],
            "V1_M15_OFFSET": O["V1_M15_OFFSET"], "LAST_EXPECTED_V1_CYCLE": O["LAST_EXPECTED_V1_CYCLE"],
            "NEXT_EXPECTED_V1_CYCLE": O["NEXT_EXPECTED_V1_CYCLE"],
            "MINUTES_TO_NEXT_V1_CYCLE": O["MINUTES_TO_NEXT_V1_CYCLE"], "SCHEDULE_CONFIDENCE": O["SCHEDULE_CONFIDENCE"],
            "AUTO_RESTART_MECHANISM": O["AUTO_RESTART_MECHANISM"], "V1_RESTART_TRIGGER": O["V1_RESTART_TRIGGER"],
            "V1_RESTART_DELAY": O["V1_RESTART_DELAY"], "V1_RESTART_RACE": O["V1_RESTART_RACE"],
            "MT5_CONTEXT_CHAIN": O["MT5_CONTEXT_CHAIN"], "MT5_TERMINAL_CONTEXT": O["MT5_TERMINAL_CONTEXT"],
            "MT5_ACCOUNT_CONTEXT": O["MT5_ACCOUNT_CONTEXT"], "MT5_SERVER_CONTEXT": O["MT5_SERVER_CONTEXT"],
            "MT5_SYMBOL_CONTEXT": O["MT5_SYMBOL_CONTEXT"], "ACCOUNT_SOURCE": O["ACCOUNT_SOURCE"],
            "ACCOUNT_PRESENT": O["ACCOUNT_PRESENT"], "MT5_LOGIN_FORM_PRESENT": O["MT5_LOGIN_FORM_PRESENT"],
            "MT5_CONFIG_FILES_READ": O["MT5_CONFIG_FILES_READ"], "MT5_ENV_KEYS_SEEN": O["MT5_ENV_KEYS_SEEN"],
            "MT5_SECRET_PRESENT": O["MT5_SECRET_PRESENT"],
            "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
            "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
            "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
            "TRADE_STATE_CONFIRMED": O["TRADE_STATE_CONFIRMED"],
            "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY": "NO", "SAFETY_WINDOW": "NOT_PROVEN",
            "NEXT_STAGE_AUTHORIZED": "NO", "V1_MODIFIED": "NO", "V2_MODIFIED": "NO",
            "V3_MODIFIED": "NO" if v3 else "UNKNOWN", "ORDER_SEND": 0, "COMMIT": "NONE",
            "V3_HASHES": imm, "mt5_read_note": note, "ts_utc": NOWU.isoformat()}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_GATEWAY_ACCOUNT_CLOSURE_R7.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §15 FINAL ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3400], flush=True)


if __name__ == "__main__":
    main()
