# -*- coding: utf-8 -*-
"""V1_POSITION_RECONCILIATION_R17 — READ-ONLY position<->ledger reconciliation + automation freeze assessment.

Allowed reads: V1 source/config/runtime/ledger/stats, automation state, ONE MT5 read-only check
(account_info/terminal_info/positions_get/orders_get), process state, file metadata/hashes.
Writes ONLY under research/v3_opportunity_engine/v1_position_reconciliation_r17/.
Forbidden & never executed: ORDER_SEND, POSITION_CLOSE/MODIFY, PENDING_ORDER_CANCEL, V1_STOP/RESTART,
LEDGER_CLEAR, STATE_CLEAR, RUN_ID_CHANGE, ENGINE_WRITE, V1_CONFIG_WRITE, STRATEGY_CHANGE, PARAMETER_CHANGE,
AUTOMATION_DISABLE/UPDATE/RUN/TRIGGER, GIT_COMMIT, FORMAL_RESET.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
TARGET = os.path.join(V1, "engine.py")
RUN = os.path.join(V1, "run_state")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
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
SCAN_DIRS = [RUN, os.path.join(V1, "runtime"), os.path.join(V1, "tmp"), os.path.join(V1, "cache"),
              os.path.join(V1, "memory", "reviews"), os.path.join(V1, "observations"),
              os.path.join(V1, "state", "decision_contexts"), os.path.join(V1, "ledger"), os.path.join(V1, "state")]
CYCLE_T0, CYCLE_T1 = "2026-09-25T15:46:30", "2026-09-25T15:53:00"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}


def sh(args, t=120):
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


def mask(s):
    s = str(s)
    return s[:3] + "***" + s[-2:] if len(s) > 6 else "UNKNOWN"


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def dump(rc=0):
    os.makedirs(HERE, exist_ok=True)
    json.dump(R, open(os.path.join(HERE, "V1_POSITION_RECONCILIATION_R17.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    print("\n=== §20 FINAL REPORT ===", flush=True)
    keys = ["TASK_STATUS", "ENGINE_SHA256", "ENGINE_STATE", "AUDIT_NOW_UTC", "OPEN_POSITIONS", "PENDING_ORDERS",
             "POSITION_TICKET", "POSITION_SYMBOL", "POSITION_TYPE", "POSITION_VOLUME", "POSITION_PRICE_OPEN",
             "POSITION_SL", "POSITION_TP", "POSITION_TIME", "POSITION_TIME_MSC", "POSITION_MAGIC",
             "POSITION_COMMENT", "POSITION_REASON", "POSITION_SWAP", "POSITION_PROFIT", "POSITION_IDENTIFIER",
             "POSITION_FINGERPRINT", "LEDGER_EXISTS", "LEDGER_SIZE", "LEDGER_MTIME", "LEDGER_SHA256",
             "LEDGER_LINE_COUNT", "LEDGER_LINK_STATUS", "DECISION_FOUND", "REQUEST_FOUND", "FILL_FOUND",
             "OPEN_FOUND", "CLOSE_FOUND", "PNL_FOUND", "LEDGER_MT5_STATE_CONFLICT", "V1_MANAGED_STATUS",
             "LAST_CYCLE_RUN_ID", "LAST_CYCLE_POSITION_AWARENESS", "LAST_CYCLE_EVIDENCE",
             "AUTOMATION_ENABLED", "AUTOMATION_STATUS", "NEXT_RUN_AT", "SECONDS_TO_NEXT_RUN",
             "AUTOMATION_CAN_TOUCH_V1", "AUTOMATION_PAYLOAD_FLAGS", "STATE_WRITE_IN_FLIGHT",
             "ARCHIVE_CLASS_COUNTS", "NEXT_CYCLE_RISK", "AUTOMATION_FREEZE_REQUIRED", "FORMAL_RESET",
             "ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "V1_STOP", "V1_RESTART", "LEDGER_CLEAR",
             "STATE_CLEAR", "GIT_COMMIT", "RESET_FREEZE_GATE", "NEXT_STAGE_AUTHORIZED", "ANOMALY",
             "ANOMALY_REASON"]
    for k in keys:
        print(f"{k} = {R.get(k, 'UNKNOWN')}", flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_POSITION_RECONCILIATION_R17.json"), flush=True)
    sys.exit(rc)


def stop_anomaly(reason):
    R["ANOMALY"] = "YES"
    R["ANOMALY_REASON"] = reason
    R["RESET_FREEZE_GATE"] = "FAIL"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    for k in ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "V1_STOP", "V1_RESTART", "LEDGER_CLEAR",
                "STATE_CLEAR", "RUN_ID_CHANGE", "ENGINE_WRITE", "V1_CONFIG_WRITE", "AUTOMATION_DISABLE",
                "AUTOMATION_UPDATE", "AUTOMATION_RUN"):
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    R["TASK_STATUS"] = "V1_POSITION_RECONCILIATION_R17_COMPLETE"
    dump(0)


def main():
    now = datetime.now(timezone.utc)
    R["AUDIT_NOW_UTC"] = now.isoformat()
    R["ANOMALY"] = "NO"

    # ---------- Stage 1 ----------
    e = sha(TARGET)
    R["ENGINE_SHA256"] = e
    R["ENGINE_STATE"] = "MV-R1_BASELINE" if e == BASE else "OTHER"
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    doc = None
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    if m:
        try:
            doc = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            doc = None
    R["AUTOMATION_RAW_JSON"] = json.dumps(doc, ensure_ascii=False)[:3000] if doc is not None else "NOT_READ"
    d = doc if isinstance(doc, dict) else {}
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = d.get("status", "UNKNOWN")
    R["LAST_RUN_AT"] = iso(int(d["lastRunAtMs"]) / 1000.0) if d.get("lastRunAtMs") else "UNKNOWN"
    R["LAST_RUN_STATUS"] = d.get("lastRunStatus", "UNKNOWN")
    R["NEXT_RUN_AT"] = iso(int(d["nextRunAtMs"]) / 1000.0) if d.get("nextRunAtMs") else "UNKNOWN"
    R["SESSION_TARGET"] = d.get("sessionTarget", "UNKNOWN")
    R["AGENT_ID"] = d.get("agentId", "UNKNOWN")
    sch = d.get("schedule") if isinstance(d.get("schedule"), dict) else {}
    R["SCHEDULE_KIND"] = sch.get("kind", "UNKNOWN")
    R["TIMEZONE"] = sch.get("tz", "UNKNOWN")
    R["PAYLOAD_KIND"] = (d.get("payload") or {}).get("kind", "UNKNOWN")
    R["PAYLOAD_MESSAGE"] = ((d.get("payload") or {}).get("message") or "")[:4000]
    R["WAKE_MODE"] = d.get("wakeMode", "UNKNOWN")
    try:
        nx = datetime.fromisoformat(R["NEXT_RUN_AT"])
        R["SECONDS_TO_NEXT_RUN"] = int((nx - now).total_seconds())
    except Exception:  # noqa: BLE001
        R["SECONDS_TO_NEXT_RUN"] = "UNKNOWN"
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
                "ConvertTo-Json -Compress -Depth 4"], 90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if re.search(r"trader_v1|engine\.py|state_package", (x.get("CommandLine") or ""), re.I)
            and "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "RUNNING" if any("engine.py" in (x.get("CommandLine") or "").lower() for x in v1p) else "NOT_RUNNING"
    R["CURRENT_CYCLE"] = "RUNNING" if v1p else "NOT_RUNNING"
    R["V1_MATCHING_PROCESSES"] = [{"PID": x.get("ProcessId"), "CMD": (x.get("CommandLine") or "")[:120]} for x in v1p[:5]]
    print("S1:", json.dumps({k: R[k] for k in ("ENGINE_STATE", "AUTOMATION_ENABLED", "AUTOMATION_STATUS",
                                                 "LAST_RUN_AT", "NEXT_RUN_AT", "SECONDS_TO_NEXT_RUN",
                                                 "CURRENT_CYCLE")}, ensure_ascii=False), flush=True)

    # ---------- Stage 2/3 : MT5 read-only + fingerprint ----------
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " pos=None\n"
             " if ps:\n  p=ps[0]\n"
             "  pos={'ticket':getattr(p,'ticket',None),'symbol':getattr(p,'symbol',None),"
             "'type':getattr(p,'type',None),'volume':getattr(p,'volume',None),"
             "'price_open':getattr(p,'price_open',None),'sl':getattr(p,'sl',None),'tp':getattr(p,'tp',None),"
             "'time':getattr(p,'time',None),'time_msc':getattr(p,'time_msc',None),"
             "'magic':getattr(p,'magic',None),'comment':getattr(p,'comment',None),"
             "'reason':getattr(p,'reason',None),'swap':getattr(p,'swap',None),'profit':getattr(p,'profit',None),"
             "'identifier':getattr(p,'identifier',None)}\n"
             " res={'CONNECTED':bool(ok),'server':(ai.server if ai else None),"
             "'login':(str(ai.login) if ai and ai.login else None),'equity':(ai.equity if ai else None),"
             "'balance':(ai.balance if ai else None),'trade_allowed':(ti.trade_allowed if ti else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_)),'pos':pos}\n"
             " print(json.dumps(res))\n mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:110]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        r4 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        r4 = {"err": type(ex).__name__}
    ok4 = bool(r4.get("CONNECTED")) and r4.get("positions") is not None and r4.get("orders") is not None
    R["MT5_CONTEXT"] = "CONFIRMED" if ok4 else "UNKNOWN"
    R["ACCOUNT_MASKED"] = mask(r4.get("login")) if r4.get("login") else "UNKNOWN"
    R["SERVER"] = r4.get("server") or "UNKNOWN"
    R["OPEN_POSITIONS"] = r4.get("positions") if r4.get("positions") is not None else "UNKNOWN"
    R["PENDING_ORDERS"] = r4.get("orders") if r4.get("orders") is not None else "UNKNOWN"
    p = r4.get("pos") or {}
    R["POSITION_TICKET"] = p.get("ticket", "UNAVAILABLE")
    R["POSITION_SYMBOL"] = p.get("symbol", "UNAVAILABLE")
    R["POSITION_TYPE"] = "BUY" if p.get("type") == 0 else ("SELL" if p.get("type") == 1 else p.get("type", "UNAVAILABLE"))
    R["POSITION_VOLUME"] = p.get("volume", "UNAVAILABLE")
    R["POSITION_PRICE_OPEN"] = p.get("price_open", "UNAVAILABLE")
    R["POSITION_SL"] = p.get("sl", "UNAVAILABLE")
    R["POSITION_TP"] = p.get("tp", "UNAVAILABLE")
    R["POSITION_TIME"] = (datetime.fromtimestamp(p["time"], timezone.utc).isoformat() if p.get("time") else "UNAVAILABLE")
    R["POSITION_TIME_MSC"] = p.get("time_msc", "UNAVAILABLE")
    R["POSITION_MAGIC"] = p.get("magic", "UNAVAILABLE")
    R["POSITION_COMMENT"] = p.get("comment", "UNAVAILABLE")
    R["POSITION_REASON"] = p.get("reason", "UNAVAILABLE")
    R["POSITION_SWAP"] = p.get("swap", "UNAVAILABLE")
    R["POSITION_PROFIT"] = p.get("profit", "UNAVAILABLE")
    R["POSITION_IDENTIFIER"] = p.get("identifier", "UNAVAILABLE")
    fp_in = {k: R["POSITION_" + k.upper()] for k in ("ticket", "symbol", "type", "volume", "price_open", "time",
                                                        "magic", "comment", "identifier")}
    R["POSITION_FINGERPRINT"] = hashlib.sha256(json.dumps(fp_in, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    R["POSITION_FINGERPRINT_INPUTS"] = fp_in
    print("S2/3 pos:", json.dumps({k: R[k] for k in ("OPEN_POSITIONS", "PENDING_ORDERS", "POSITION_TICKET",
                                                       "POSITION_TYPE", "POSITION_VOLUME", "POSITION_PRICE_OPEN",
                                                       "POSITION_TIME", "POSITION_MAGIC", "POSITION_COMMENT",
                                                       "POSITION_IDENTIFIER", "POSITION_FINGERPRINT")},
                                    ensure_ascii=False), flush=True)
    # anomaly 1/2
    if R["OPEN_POSITIONS"] not in (1, "UNKNOWN"):
        return stop_anomaly("MT5_POSITION_COUNT_CHANGED")
    if isinstance(R["PENDING_ORDERS"], int) and R["PENDING_ORDERS"] > 0:
        return stop_anomaly("PENDING_ORDER_APPEARED")

    # ---------- Stage 4/5/6 : ledger ----------
    R["LEDGER_EXISTS"] = "YES" if os.path.exists(LEDGER) else "NO"
    if R["LEDGER_EXISTS"] == "YES":
        st = os.stat(LEDGER)
        R["LEDGER_SIZE"] = st.st_size
        R["LEDGER_MTIME"] = iso(st.st_mtime)
        R["LEDGER_SHA256"] = sha(LEDGER)
        lines = [l for l in open(LEDGER, encoding="utf-8", errors="ignore") if l.strip()]
        R["LEDGER_LINE_COUNT"] = len(lines)
        R["LEDGER_SHA256_AT_READ"] = R["LEDGER_SHA256"]
    else:
        R["LEDGER_SIZE"] = R["LEDGER_MTIME"] = R["LEDGER_SHA256"] = "UNAVAILABLE"
        R["LEDGER_LINE_COUNT"] = 0
        lines = []
    R["MATCH_WINDOWS"] = {"time_window_hours": 72, "basis": "POSITION_TIME ± 72h for candidate scan (declared, not widened)"}
    tk = str(R["POSITION_TICKET"])
    idt = str(R["POSITION_IDENTIFIER"])
    magic = str(R["POSITION_MAGIC"])
    cmt = str(R["POSITION_COMMENT"])
    tkt_hits, mag_hits, cmt_hits, id_hits = [], [], [], []
    for i, l in enumerate(lines):
        low = l.lower()
        if tk and tk != "UNAVAILABLE" and tk in l:
            tkt_hits.append(i)
        if idt and idt != "UNAVAILABLE" and idt in l:
            id_hits.append(i)
        if magic and magic != "UNAVAILABLE" and re.search(r'"magic"\s*:\s*' + re.escape(magic) + r'\b', l):
            mag_hits.append(i)
        if cmt and cmt != "UNAVAILABLE" and cmt and cmt.lower() in low:
            cmt_hits.append(i)
    # symbol + time window
    sym_hits = []
    try:
        pt = datetime.fromisoformat(R["POSITION_TIME"])
        for i, l in enumerate(lines):
            if "XAUUSD" in l.upper():
                for mm in re.finditer(r"(20\d\d-\d\d-\d\dT[\d:]{8})", l):
                    try:
                        t = datetime.fromisoformat(mm.group(1)).replace(tzinfo=timezone.utc)
                        if abs((t - pt).total_seconds()) <= 72 * 3600:
                            sym_hits.append(i)
                            break
                    except Exception:  # noqa: BLE001
                        continue
    except Exception:  # noqa: BLE001
        pt = None
    # lifecycle keywords
    LC = {"DECISION": (r'"decision"', r'"think"'), "REQUEST": (r'"request', r'"order_request"', r'"req"'),
           "FILL": (r'"fill"', r'"filled"'), "OPEN": (r'"open"', r'"opened"'),
           "CLOSE": (r'"close"', r'"closed"'), "PNL": (r'"pnl"', r'"profit"', r'"net"')}
    life = {}
    for k, pats in LC.items():
        life[k] = "FOUND" if any(any(re.search(pp, l, re.I) for pp in pats) for l in lines) else "NOT_FOUND"
    R["DECISION_FOUND"] = life["DECISION"]
    R["REQUEST_FOUND"] = life["REQUEST"]
    R["FILL_FOUND"] = life["FILL"]
    R["OPEN_FOUND"] = life["OPEN"]
    R["CLOSE_FOUND"] = life["CLOSE"]
    R["PNL_FOUND"] = life["PNL"]
    R["LEDGER_MT5_STATE_CONFLICT"] = "UNKNOWN"
    okA = bool(tkt_hits or id_hits)
    okC = bool(mag_hits)
    okD = bool(cmt_hits)
    okB = bool(sym_hits)
    link = ("EXACT" if okA else ("STRONG" if (okC or okD) and okB else ("WEAK" if okB or okC or okD else "NONE")))
    if len(lines) == 0:
        link = "UNKNOWN"
    R["LEDGER_LINK_STATUS"] = link
    R["MATCH_DETAIL"] = {"ticket_hits": tkt_hits[:5], "identifier_hits": id_hits[:5], "magic_hits": mag_hits[:5],
                           "comment_hits": cmt_hits[:5], "symbol_time_hits": sym_hits[:5],
                           "time_window_used_hours": 72}
    R["V1_MANAGED_STATUS"] = ("V1_MANAGED" if link in ("EXACT", "STRONG") else
                                ("V1_UNCERTAIN" if link == "WEAK" else
                                 ("EXTERNAL_ORPHAN" if link == "NONE" else "V1_UNCERTAIN")))
    print("S4/5/6 ledger:", json.dumps({"lines": R["LEDGER_LINE_COUNT"], "link": link,
                                          "managed": R["V1_MANAGED_STATUS"], "detail": R["MATCH_DETAIL"]},
                                         ensure_ascii=False)[:600], flush=True)

    # ---------- Stage 12/13 : last cycle artifacts ----------
    cyc_files = []
    for root in SCAN_DIRS:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                pth = os.path.join(r_, f)
                try:
                    st = os.stat(pth)
                except OSError:
                    continue
                if CYCLE_T0 <= iso(st.st_mtime)[:19] <= CYCLE_T1:
                    cyc_files.append({"path": os.path.relpath(pth, AIQ).replace("\\", "/"), "mtime": iso(st.st_mtime),
                                        "size": st.st_size})
    R["LAST_CYCLE_ARTIFACTS"] = cyc_files[:20]
    R["LAST_CYCLE_RUN_ID"] = d.get("id", AID) if d else "UNKNOWN"
    aware = "UNKNOWN"
    if cyc_files and any("state_package" in c["path"] or "workflow" in c["path"] or "ledger" in c["path"]
                          for c in cyc_files):
        aware = "UNKNOWN"
    R["LAST_CYCLE_POSITION_AWARENESS"] = aware
    R["LAST_CYCLE_EVIDENCE"] = {"artifacts_in_window": len(cyc_files),
                                  "window": [CYCLE_T0, CYCLE_T1],
                                  "note": "runtime artifacts in the window listed; whether the cycle READ this position "
                                          "cannot be proven from filenames alone"}
    print("S12/13 cycle:", json.dumps({"artifacts": len(cyc_files), "awareness": aware}, ensure_ascii=False), flush=True)

    # ---------- Stage 14/15 : automation payload capability ----------
    pm = (R.get("PAYLOAD_MESSAGE") or "").lower()
    flags = {"engine.py": "engine.py" in pm, "state_package.py": "state_package" in pm,
              "trader_v1": "trader_v1" in pm, "positions": "position" in pm, "orders": "order" in pm}
    R["AUTOMATION_PAYLOAD_FLAGS"] = flags
    R["AUTOMATION_CAN_TOUCH_V1"] = "YES" if (flags["engine.py"] or flags["trader_v1"] or flags["state_package.py"]) else "UNKNOWN"
    print("S14/15 automation:", json.dumps(flags, ensure_ascii=False), R["AUTOMATION_CAN_TOUCH_V1"], flush=True)

    # ---------- Stage 16 : 60s stillness ----------
    keys = [os.path.join(RUN, "state_package_latest.json"), LEDGER, os.path.join(RUN, "workflow_latest.json"),
             os.path.join(RUN, "statistics.json"), os.path.join(RUN, "workflow_history.jsonl")]
    def ksnap():
        out = {}
        for kp in keys:
            if os.path.exists(kp):
                try:
                    st = os.stat(kp)
                    out[kp] = (st.st_size, round(st.st_mtime, 3), sha(kp))
                except OSError:
                    continue
        return out
    s0 = ksnap()
    lsha0 = R["LEDGER_SHA256"]
    time.sleep(60)
    s1 = ksnap()
    changed = [os.path.relpath(k, AIQ).replace("\\", "/") for k in s1 if k in s0 and s0[k] != s1[k]]
    lsha1 = sha(LEDGER)
    R["STILLNESS_WINDOW_SECONDS"] = 60
    R["STILLNESS_CHANGED_FILES"] = changed[:10]
    ages = [time.time() - v[1] for v in s1.values()]
    R["STILLNESS_MIN_AGE_SECONDS"] = round(min(ages), 1) if ages else "UNKNOWN"
    if changed or (lsha0 and lsha1 and lsha0 != lsha1):
        R["STATE_WRITE_IN_FLIGHT"] = "YES"
    elif ages and min(ages) > 300:
        R["STATE_WRITE_IN_FLIGHT"] = "NO"
    else:
        R["STATE_WRITE_IN_FLIGHT"] = "UNKNOWN"
    R["LEDGER_CHANGED_DURING_AUDIT"] = "YES" if (lsha0 and lsha1 and lsha0 != lsha1) else "NO"
    print("S16 stillness:", R["STATE_WRITE_IN_FLIGHT"], "changed=", changed, "min_age=",
          R["STILLNESS_MIN_AGE_SECONDS"], flush=True)
    if R["LEDGER_CHANGED_DURING_AUDIT"] == "YES":
        return stop_anomaly("LEDGER_CHANGED_DURING_AUDIT")

    # ---------- Stage 17 : corrected archive classification ----------
    PREFIX = "research/hermes/trader_v1/"
    def classify_rel(rel_after_v1):
        r = rel_after_v1.replace("\\", "/").lower()
        b = os.path.basename(r)
        if "ledger" in b:
            return "LEDGER"
        if re.search(r"\b(trade|closed|fill|deal)s?\b", r) or re.search(r"trade_history|closed_trade", r):
            return "TRADE_HISTORY"
        if r.endswith(("plan_ledger.jsonl", "trade_ledger.jsonl")):
            return "LEDGER"
        if "statistic" in b or b == "stats.json":
            return "STATISTICS"
        if "reviews/" in r or "review" in b:
            return "REVIEWS"
        if "decision_contexts/" in r or "workflow_history" in b or "decisions/" in r or "decision" in b:
            return "DECISION_HISTORY"
        if r.endswith((".py",)) and ("run_state/tmp/" in r or r.startswith("tmp/") or "runtime/" in r):
            return "RUNTIME"
        if r.endswith((".yaml", ".yml")):
            return "CONFIG"
        if r.startswith(("run_state/", "state/")) or "state_package" in b or b == "workflow_latest.json":
            return "STATE"
        if "audit" in b or "report" in b:
            return "AUDIT"
        if r.endswith((".py",)):
            return "SOURCE"
        if "run_state/tmp/" in r or "runtime/" in r or "cache/" in r:
            return "RUNTIME"
        return "OTHER"
    counts, samples = {}, {}
    total = 0
    for root in SCAN_DIRS:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                pth = os.path.join(r_, f)
                rel = os.path.relpath(pth, AIQ).replace("\\", "/")
                after = rel[len(PREFIX):] if rel.startswith(PREFIX) else rel
                c = classify_rel(after)
                counts[c] = counts.get(c, 0) + 1
                samples.setdefault(c, []).append(rel)
                total += 1
    R["ARCHIVE_CLASS_COUNTS"] = counts
    R["ARCHIVE_CLASS_SAMPLES"] = {k: v[:4] for k, v in samples.items()}
    R["ARCHIVE_CLASSIFIED_TOTAL"] = total
    R["ARCHIVE_SCOPE_USED"] = "V1 root-relative path (trader_v1 prefix stripped before keyword match)"
    print("S17 archive classes:", json.dumps(counts, ensure_ascii=False), flush=True)

    # ---------- Stage 11/18 : risk + freeze decision ----------
    near = isinstance(R["SECONDS_TO_NEXT_RUN"], int) and R["SECONDS_TO_NEXT_RUN"] < 900
    freeze = (R["AUTOMATION_ENABLED"] is True and R["OPEN_POSITIONS"] == 1
               and R["AUTOMATION_CAN_TOUCH_V1"] == "YES" and near)
    R["NEXT_CYCLE_RISK"] = "ELEVATED" if freeze else ("UNKNOWN" if R["AUTOMATION_CAN_TOUCH_V1"] == "UNKNOWN" else "LOW")
    R["AUTOMATION_FREEZE_REQUIRED"] = "YES" if freeze else "NO"
    R["AUTOMATION_FREEZE_EXECUTED"] = "NO"

    # ---------- final ledger bookkeeping ----------
    for k in ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "PENDING_ORDER_CANCEL", "V1_STOP", "V1_RESTART",
                "LEDGER_CLEAR", "STATE_CLEAR", "RUN_ID_CHANGE", "ENGINE_WRITE", "V1_CONFIG_WRITE",
                "STRATEGY_CHANGE", "PARAMETER_CHANGE", "AUTOMATION_DISABLE", "AUTOMATION_UPDATE", "AUTOMATION_RUN"):
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["RESET_FREEZE_GATE"] = "FAIL"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_POSITION_RECONCILIATION_R17_COMPLETE"
    dump(0)


if __name__ == "__main__":
    main()
