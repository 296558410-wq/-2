# -*- coding: utf-8 -*-
"""V1_GATEWAY_ACCOUNT_CLOSURE_R6 — READ-ONLY. Two closures only:
A) gateway.cmd -> real launch args -> real storage -> V1 automation -> schedule -> restart linkage
B) engine.py -> broker object -> MT5 initialize/login -> terminal/account/server/symbol -> read-only state
No stop/restart/kill/config change/V1 change/order write/git write/commit. Secrets are never printed.
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
R5 = os.path.join(ENGINE, "v1_gateway_safety_audit_r5", "V1_GATEWAY_SAFETY_AUDIT_R5.json")
NOWU = datetime.now(timezone.utc)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}
MASK = lambda s: (str(s)[:3] + "***" + str(s)[-2:]) if s and len(str(s)) > 6 else "UNKNOWN"


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


def main():
    os.makedirs(HERE, exist_ok=True)
    O["CURRENT_TIME_UTC"] = NOWU.isoformat()
    # ---------------- §三 read R5 (starting point) ----------------
    r5 = json.load(open(R5, encoding="utf-8")) if os.path.exists(R5) else {}
    O["R5_USED"] = {"path": os.path.relpath(R5, AIQ).replace("\\", "/"), "exists": bool(r5),
                     "has_gateway_cmd": bool(r5.get("gateway_cmd")), "has_toplevel": bool(r5.get("openclaw_toplevel")),
                     "R5_TERMINAL": r5.get("MT5_TERMINAL_CONTEXT"), "R5_SYMBOL": r5.get("MT5_SYMBOL_CONTEXT")}
    gcmd = r5.get("gateway_cmd") or (rd(os.path.join(OC, "gateway.cmd"), 4000) or "")
    O["gateway_cmd_text"] = gcmd[:2000]
    O["openclaw_toplevel"] = r5.get("openclaw_toplevel", [])
    O["V1_MT5_SOURCE_FILES_R5"] = r5.get("V1_MT5_SOURCE_FILES", [])
    print("§3 R5 read:", json.dumps(O["R5_USED"], ensure_ascii=False)[:300], flush=True)

    # ---------------- §四 parse the real launch chain ----------------
    flags = re.findall(r"--(config|state|workspace|profile|data|home)[=\s]+\"?([^\"\r\n]+)\"?", gcmd)
    envs = re.findall(r"(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)=(.+)$", gcmd)
    paths = re.findall(r"([A-Za-z]:\\\\?[^\s\"\r\n]+)", gcmd)
    cands = []
    for f, v in flags:
        cands.append({"kind": f"--{f}", "value": v.strip(), "exists": os.path.exists(v.strip())})
    for k, v in envs:
        cands.append({"kind": f"env:{k}", "value": v.strip()[:200], "exists": os.path.exists(v.strip())})
    for p in paths:
        cands.append({"kind": "path", "value": p, "exists": os.path.exists(p)})
    O["LAUNCH_ARGUMENTS"] = flags
    O["LAUNCH_ENV"] = [{"k": k, "v": v[:200]} for k, v in envs]
    O["LAUNCH_PATHS"] = sorted({p for p in paths})[:20]
    O["LAUNCH_CANDIDATES"] = cands[:30]
    # workspace/profile from R5 toplevel + env
    ws = None
    for c in cands:
        k = c["kind"].lower()
        if ("workspace" in k or "data" in k or "state" in k or "home" in k or k.startswith("env:openclaw")) and c["exists"]:
            ws = c["value"]
            break
    O["GATEWAY_STORAGE_CANDIDATE"] = ws or "UNKNOWN"
    # explicit env of the running gateway process (read-only)
    ps = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                          "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'openclaw|gateway'} | "
                          "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 4"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    O["gateway_processes"] = (ps.stdout or "")[:1500]
    print(f"§4 launch: flags={len(flags)} envs={len(envs)} paths={len(paths)} storage_candidate="
          f"{O['GATEWAY_STORAGE_CANDIDATE'][:80]}", flush=True)

    # ---------------- §五 locate V1 automation in the REAL storage only ----------------
    KW = ("hermes-trader-m15-cycle", "trader_v1", "engine.py", "maximum_holding_time", "xauusd")
    search_roots = []
    for c in cands:
        if c["exists"] and os.path.isdir(c["value"]):
            search_roots.append(c["value"])
    if O["GATEWAY_STORAGE_CANDIDATE"] not in ("UNKNOWN", None) and os.path.isdir(O["GATEWAY_STORAGE_CANDIDATE"]):
        search_roots.append(O["GATEWAY_STORAGE_CANDIDATE"])
    search_roots = sorted(set(search_roots))[:6]
    O["AUTOMATION_SEARCH_ROOTS"] = search_roots
    hits = []
    for root in search_roots:
        for r_, ds, fs in os.walk(root):
            if any(s in r_.lower() for s in ("media", "logs", "node_modules", ".git", "__pycache__", "pasted")):
                continue
            for f in fs:
                if not f.lower().endswith((".json", ".jsonl", ".yaml", ".yml", ".js", ".cjs", ".mjs")):
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
                    rel = os.path.relpath(p, AIQ).replace("\\", "/")
                    if re.search(r"(pasted|task|报告|README|SKILL|stack-map)", rel, re.I):
                        continue
                    hit = {"source": rel, "matched": [k for k in KW if k in low][:4]}
                    try:
                        doc = json.loads(txt)
                        hit["structured"] = True
                        hit["entry"] = {k: (v if not isinstance(v, (dict, list)) else str(v)[:200])
                                         for k, v in doc.items()} if isinstance(doc, dict) else "list"
                    except Exception:  # noqa: BLE001
                        hit["structured"] = False
                    hits.append(hit)
                    if len(hits) > 20:
                        break
            if len(hits) > 20:
                break
    struct = [h for h in hits if h.get("structured")]
    O["GATEWAY_V1_AUTOMATION_HITS"] = hits[:10]
    O["GATEWAY_V1_AUTOMATION_FOUND"] = "YES" if struct else "NO"
    O["GATEWAY_V1_AUTOMATION_SOURCE"] = (struct[0]["source"] if struct else "NOT_FOUND")
    ent = struct[0].get("entry", {}) if struct else {}
    ent = ent if isinstance(ent, dict) else {}
    gv = lambda *ks: next((ent[k] for k in ent for kk in ks if k.lower() == kk), "UNKNOWN")
    O["GATEWAY_V1_AUTOMATION_ID"] = gv("id", "name")
    O["GATEWAY_V1_AUTOMATION_ENABLED"] = gv("enabled")
    O["ACTION"] = gv("action", "command", "execute")
    O["ARGUMENTS"] = gv("args", "arguments")
    O["WORKING_DIRECTORY"] = gv("cwd", "workingdirectory")
    O["SCHEDULE_TYPE"] = gv("schedule", "scheduletype", "type")
    O["SCHEDULE_EXPRESSION"] = gv("cron", "expression", "interval", "every")
    O["TIMEZONE"] = gv("timezone", "tz")
    O["OFFSET"] = gv("offset")
    O["V1_M15_SCHEDULE_SOURCE"] = (O["GATEWAY_V1_AUTOMATION_SOURCE"] if struct else "UNKNOWN")
    O["V1_M15_OFFSET"] = (O["OFFSET"] if struct else "UNKNOWN")
    O["LAST_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["NEXT_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["MINUTES_TO_NEXT_V1_CYCLE"] = "UNKNOWN"
    O["V1_NEXT_CYCLE"] = "UNKNOWN"
    O["SCHEDULE_CONFIDENCE"] = "UNKNOWN"
    if struct and O["SCHEDULE_EXPRESSION"] not in ("UNKNOWN", None):
        m = re.match(r"\*/(\d+)", str(O["SCHEDULE_EXPRESSION"]))
        if m:
            step = int(m.group(1))
            nm = NOWU.replace(second=0, microsecond=0)
            add = step - (nm.minute % step)
            nxt = nm.replace(minute=nm.minute + add) if add < 60 else nm
            O["NEXT_EXPECTED_V1_CYCLE"] = nxt.isoformat()
            O["V1_NEXT_CYCLE"] = nxt.isoformat()
            O["MINUTES_TO_NEXT_V1_CYCLE"] = add
            O["SCHEDULE_CONFIDENCE"] = "CONFIRMED_INTERVAL"
    print(f"§5 automation: hits={len(hits)} structured={len(struct)} source={O['GATEWAY_V1_AUTOMATION_SOURCE'][:70]}",
          flush=True)

    # ---------------- §七 restart (real automation only) ----------------
    O["AUTO_RESTART_MECHANISM"] = ("YES" if struct and str(gv("restart", "retry", "onexit", "watchdog", "keepalive"))
                                     not in ("UNKNOWN", "None", "False") else "UNKNOWN")
    O["V1_RESTART_TRIGGER"] = "UNKNOWN"
    O["V1_RESTART_DELAY"] = "UNKNOWN"
    O["V1_RESTART_RACE"] = "UNKNOWN"
    print("§7 restart:", O["AUTO_RESTART_MECHANISM"], "| RACE=UNKNOWN (no proven automation->V1->restart chain)", flush=True)

    # ---------------- §八 MT5 chain: engine.py upward (targeted trace) ----------------
    eng = os.path.join(V1, "engine.py")
    etxt = rd(eng, 400000) or ""
    O["ENGINE_METHODS"] = sorted({m.group(1) for m in re.finditer(r"(positions_get|orders_get|account_info|"
                                                                    r"terminal_info|initialize|login)\s*\(", etxt)})
    local_imports = sorted({m.group(1) for m in re.finditer(r"(?m)^\s*(?:import|from)\s+([a-zA-Z_][\w]*)", etxt)
                             if os.path.exists(os.path.join(V1, m.group(1) + ".py"))})
    O["ENGINE_LOCAL_IMPORTS"] = local_imports
    broker_mods = [m for m in local_imports if re.search(r"broker|mt5|trade|exec", m, re.I)]
    modules = broker_mods or [m for m in local_imports if re.search(r"broker|mt5", m, re.I)] or local_imports[:6]
    chain, ctx = [], {"terminal": "UNKNOWN", "account": "UNKNOWN", "server": "UNKNOWN", "symbol": "UNKNOWN",
                        "init_form": "UNKNOWN", "login_form": "UNKNOWN", "config_file": None, "password_present": False}
    for m in modules:
        p = os.path.join(V1, m + ".py")
        txt = rd(p, 400000) or ""
        if not txt:
            continue
        chain.append({"module": os.path.relpath(p, AIQ).replace("\\", "/"),
                        "functions": sorted({x.group(1) for x in re.finditer(r"(?m)^\s*def\s+([\w]+)\s*\(", txt)})[:12],
                        "mt5_calls": sorted({x.group(1) for x in re.finditer(r"(mt5|MT5)[\.\s]*\.?(initialize|login|"
                                                                               r"account_info|terminal_info)"
                                                                               r"\s*\(", txt)})[:6]})
        mi = re.search(r"(?m)^\s*(?:mt5|MT5)\.initialize\(([^)]{0,300})\)", txt)
        if mi:
            ctx["init_form"] = mi.group(1)[:200]
        ml = re.search(r"(?m)^\s*(?:mt5|MT5)\.login\(([^)]{0,300})\)", txt)
        if ml:
            ctx["login_form"] = "[REDACTED_FORM]"
        mt = re.search(r"(?i)(terminal_path|path)\s*[:=]\s*r?[\"']([^\"']*terminal[^\"']*\.exe)[\"']", txt)
        if mt:
            ctx["terminal"] = mt.group(2)
        ms = re.search(r"(?i)server\s*[:=]\s*[\"']([^\"']+)[\"']", txt)
        if ms:
            ctx["server"] = ms.group(1)
        ma = re.search(r"(?i)(login|account)\s*[:=]\s*[\"']?(\d{5,})", txt)
        if ma:
            ctx["account"] = MASK(ma.group(2))
        msym = re.search(r"(?i)symbol\s*[:=]\s*[\"']([A-Z]{3,10})[\"']", txt)
        if msym:
            ctx["symbol"] = msym.group(1)
        if re.search(r"(?i)password\s*[:=]", txt):
            ctx["password_present"] = True
        for mf in re.finditer(r"[\"']([\w./\\-]+\.(?:json|ini))[\"']", txt):
            c = mf.group(1)
            for cand in (os.path.join(V1, c), os.path.join(RE, "hermes", c), os.path.join(AIQ, c)):
                if os.path.exists(cand):
                    ctx["config_file"] = os.path.relpath(cand, AIQ).replace("\\", "/")
                    cfg = rd(cand, 100000) or ""
                    for k, key in (("account", r"(?i)login|account"), ("server", r"(?i)server"),
                                    ("symbol", r"(?i)symbol"), ("terminal", r"(?i)terminal")):
                        mm = re.search(key + r"[\"']?\s*[:=]\s*[\"']?([^\"',\n}]+)", cfg)
                        if mm and ctx[k] == "UNKNOWN":
                            ctx[k] = MASK(mm.group(1).strip()) if k == "account" else mm.group(1).strip()[:60]
                    break
    O["MT5_TRACE_CHAIN"] = chain
    O["MT5_TERMINAL_CONTEXT"] = ctx["terminal"] if ctx["terminal"] != "UNKNOWN" else r5.get("MT5_TERMINAL_CONTEXT", "UNKNOWN")
    O["MT5_ACCOUNT_CONTEXT"] = ctx["account"]
    O["MT5_SERVER_CONTEXT"] = ctx["server"]
    O["MT5_SYMBOL_CONTEXT"] = ctx["symbol"] if ctx["symbol"] != "UNKNOWN" else r5.get("MT5_SYMBOL_CONTEXT", "UNKNOWN")
    O["MT5_INIT_FORM"] = ctx["init_form"]
    O["MT5_LOGIN_FORM_PRESENT"] = True if ctx["login_form"] != "UNKNOWN" else False
    O["MT5_CONFIG_FILE"] = ctx["config_file"]
    O["MT5_PASSWORD_PRESENT"] = ctx["password_present"]
    closed = (O["MT5_TERMINAL_CONTEXT"] not in ("UNKNOWN", None) and O["MT5_ACCOUNT_CONTEXT"] not in ("UNKNOWN", None)
               and O["MT5_SYMBOL_CONTEXT"] not in ("UNKNOWN", None))
    O["MT5_CONTEXT_CHAIN"] = "CONFIRMED" if closed else ("PARTIAL" if O["MT5_TERMINAL_CONTEXT"] != "UNKNOWN" else "UNKNOWN")
    print(f"§8 MT5 trace: modules={len(modules)} chain={len(chain)} terminal={str(O['MT5_TERMINAL_CONTEXT'])[:50]} "
          f"account={O['MT5_ACCOUNT_CONTEXT']} server={O['MT5_SERVER_CONTEXT']} sym={O['MT5_SYMBOL_CONTEXT']} "
          f"CHAIN={O['MT5_CONTEXT_CHAIN']}", flush=True)

    # ---------------- §十 read-only state (only if CONFIRMED) ----------------
    O["OPEN_POSITIONS"] = "UNKNOWN"
    O["PENDING_ORDERS"] = "UNKNOWN"
    O["ACTIVE_ORDER_ACTION"] = "UNKNOWN"
    O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    O["TRADE_STATE_CONFIRMED"] = "NO"
    note = "MT5_CONTEXT_CHAIN != CONFIRMED -> read-only query not attempted (per section 10)"
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
            out = (pr.stdout or "").strip()
            d = json.loads(out.splitlines()[-1]) if out else {}
            if d.get("positions") is not None and d.get("orders") is not None:
                O["OPEN_POSITIONS"] = d["positions"]
                O["PENDING_ORDERS"] = d["orders"]
                O["TRADE_STATE_CONFIRMED"] = "YES"
                O["ACTIVE_ORDER_ACTION"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["ORDER_REQUEST_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                O["BROKER_OPERATION_IN_FLIGHT"] = "NO" if d["orders"] == 0 else "UNKNOWN"
                note = "read-only positions_get/orders_get (symbol=XAUUSD) executed"
            else:
                note = f"MT5 read failed: {str(d)[:140]}"
        except Exception as e:  # noqa: BLE001
            note = f"MT5 read error: {type(e).__name__}"
    O["mt5_read_note"] = note
    print("§10 state:", O["OPEN_POSITIONS"], O["PENDING_ORDERS"], "|", note[:120], flush=True)

    # ---------------- §十一 gate inputs (extra fields not required this round) ----------------
    O["V1_PID_CONFIRMED"] = "NO"
    O["PRIMARY_AUTOMATION_CONFIRMED"] = "YES" if struct else "NO"
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["SAFETY_WINDOW"] = "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "NO"

    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    rep = {"TASK_STATUS": "V1_GATEWAY_ACCOUNT_CLOSURE_R6_COMPLETE",
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
            "MT5_SYMBOL_CONTEXT": O["MT5_SYMBOL_CONTEXT"],
            "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
            "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
            "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
            "TRADE_STATE_CONFIRMED": O["TRADE_STATE_CONFIRMED"],
            "CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY": "NO", "SAFETY_WINDOW": "NOT_PROVEN",
            "NEXT_STAGE_AUTHORIZED": "NO", "V1_MODIFIED": "NO", "V2_MODIFIED": "NO",
            "V3_MODIFIED": "NO" if v3 else "UNKNOWN", "ORDER_SEND": 0, "COMMIT": "NONE",
            "V3_HASHES": imm, "mt5_read_note": O["mt5_read_note"], "ts_utc": NOWU.isoformat()}
    O.update(rep)
    json.dump(O, open(os.path.join(HERE, "V1_GATEWAY_ACCOUNT_CLOSURE_R6.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §13 FINAL ===", flush=True)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str)[:3200], flush=True)


if __name__ == "__main__":
    main()
