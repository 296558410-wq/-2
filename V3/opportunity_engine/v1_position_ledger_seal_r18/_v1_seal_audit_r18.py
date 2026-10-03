# -*- coding: utf-8 -*-
"""V1_POSITION_LEDGER_SEAL_AUDIT_R18 — READ-ONLY lifecycle proof for position 2377449557 + archive design.

Allowed reads only: MT5 read-only (account_info/terminal_info/positions_get/orders_get), V1 ledger/runtime/state,
historical artifacts, automation state, file hashes/metadata. Writes ONLY under
research/v3_opportunity_engine/v1_position_ledger_seal_r18/. No seal, no reset, no order/position op, no
ledger/state/engine writes, no automation change, no git.
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
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_R17 = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
R17 = {"ticket": 2377449557, "identifier": 2377449557, "volume": 0.01, "type": "SELL", "price_open": 4277.28,
        "sl": 4299.0, "tp": 4257.0}
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
SCAN_DIRS = [RUN, os.path.join(V1, "runtime"), os.path.join(V1, "tmp"), os.path.join(V1, "cache"),
              os.path.join(V1, "memory", "reviews"), os.path.join(V1, "observations"),
              os.path.join(V1, "state", "decision_contexts"), os.path.join(V1, "ledger"), os.path.join(V1, "state")]
PREFIX = "research/hermes/trader_v1/"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}
STOP = []


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


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def classify_rel(after):
    r = after.replace("\\", "/").lower()
    b = os.path.basename(r)
    if "ledger" in b:
        return "LEDGER"
    if re.search(r"trade_history|closed_trade", r):
        return "TRADE_HISTORY"
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


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "RUNNING"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ===== Stage 1 =====
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    doc = None
    if m:
        try:
            doc = json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            doc = None
    d = doc if isinstance(doc, dict) else {}
    R["AUTOMATION_EXISTS"] = "YES" if d else "UNKNOWN"
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    R["AUTOMATION_STATUS"] = d.get("status", "UNKNOWN")
    esha = sha(ENGINE)
    R["ENGINE_SHA256"] = esha
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], 90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if re.search(r"trader_v1|engine\.py|state_package", (x.get("CommandLine") or ""), re.I)
            and "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "NOT_RUNNING" if not v1p else "RUNNING"
    if str(R["AUTOMATION_ENABLED"]).lower() != "false":
        STOP.append("AUTOMATION_NOT_DISABLED")
    if R["V1_ENGINE_PROCESS"] != "NOT_RUNNING":
        STOP.append("V1_ENGINE_RUNNING")
    if esha != BASE:
        STOP.append("ENGINE_HASH_CHANGED")
    print("S1:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "AUTOMATION_STATUS", "V1_ENGINE_PROCESS",
                                                 "ENGINE_SHA256")}, ensure_ascii=False), flush=True)

    # ===== Stage 2 =====
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             " pos=[]\n"
             " if ps:\n"
             "  for p in ps:\n"
             "   pos.append({'ticket':p.ticket,'identifier':getattr(p,'identifier',None),'symbol':p.symbol,"
             "'type':p.type,'volume':p.volume,'price_open':p.price_open,'sl':p.sl,'tp':p.tp,'time':p.time,"
             "'time_msc':getattr(p,'time_msc',None),'magic':p.magic,'comment':getattr(p,'comment',None),"
             "'reason':getattr(p,'reason',None),'swap':p.swap,'profit':p.profit})\n"
             " print(json.dumps({'CONNECTED':bool(ok),'server':(ai.server if ai else None),"
             "'login':(str(ai.login) if ai and ai.login else None),'currency':(ai.currency if ai else None),"
             "'trade_allowed':(ti.trade_allowed if ti else None),'company':(ti.company if ti else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_)),'pos':pos}))\n"
             " mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:110]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        r2 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        r2 = {"err": type(ex).__name__}
    ok2 = bool(r2.get("CONNECTED")) and r2.get("positions") is not None and r2.get("orders") is not None
    R["MT5_CONTEXT"] = "CONFIRMED" if ok2 else "UNKNOWN"
    R["MT5_POSITION_COUNT"] = r2.get("positions", "UNKNOWN")
    R["PENDING_ORDERS"] = r2.get("orders", "UNKNOWN")
    R["SERVER"] = r2.get("server") or "UNKNOWN"
    R["COMPANY"] = r2.get("company") or "UNKNOWN"
    R["CURRENCY"] = r2.get("currency") or "UNKNOWN"
    p0 = (r2.get("pos") or [{}])[0] if r2.get("pos") else {}
    R["POSITION_TICKET"] = p0.get("ticket", "UNAVAILABLE")
    R["POSITION_IDENTIFIER"] = p0.get("identifier", "UNAVAILABLE")
    tm = p0.get("type", None)
    R["POSITION_SYMBOL"] = p0.get("symbol", "UNAVAILABLE")
    R["POSITION_TYPE"] = "BUY" if tm == 0 else ("SELL" if tm == 1 else ("UNAVAILABLE" if tm is None else tm))
    R["POSITION_VOLUME"] = p0.get("volume", "UNAVAILABLE")
    R["POSITION_PRICE_OPEN"] = p0.get("price_open", "UNAVAILABLE")
    R["POSITION_SL"] = p0.get("sl", "UNAVAILABLE")
    R["POSITION_TP"] = p0.get("tp", "UNAVAILABLE")
    R["POSITION_TIME"] = iso(p0["time"]) if p0.get("time") else "UNAVAILABLE"
    R["POSITION_TIME_RAW_SERVER"] = p0.get("time", "UNAVAILABLE")
    R["POSITION_TIME_MSC"] = p0.get("time_msc", "UNAVAILABLE")
    R["POSITION_MAGIC"] = p0.get("magic", "UNAVAILABLE")
    R["POSITION_COMMENT"] = p0.get("comment", "UNAVAILABLE")
    R["POSITION_REASON"] = p0.get("reason", "UNAVAILABLE")
    R["POSITION_SWAP"] = p0.get("swap", "UNAVAILABLE")
    R["POSITION_PROFIT"] = p0.get("profit", "UNAVAILABLE")
    print("S2 pos:", json.dumps({k: R[k] for k in ("MT5_POSITION_COUNT", "PENDING_ORDERS", "POSITION_TICKET",
                                                     "POSITION_TYPE", "POSITION_VOLUME", "POSITION_PRICE_OPEN",
                                                     "POSITION_SL", "POSITION_TP", "POSITION_TIME_RAW_SERVER",
                                                     "POSITION_MAGIC", "POSITION_COMMENT")}, ensure_ascii=False), flush=True)

    # ===== Stage 3 continuity =====
    chg = []
    if R["POSITION_TICKET"] != R17["ticket"]:
        chg.append("ticket")
    if R["POSITION_IDENTIFIER"] not in (R17["identifier"], "UNAVAILABLE"):
        chg.append("identifier")
    if str(R["POSITION_TYPE"]).upper() != R17["type"]:
        chg.append("type")
    try:
        if abs(float(R["POSITION_VOLUME"]) - R17["volume"]) > 1e-9:
            chg.append("volume")
    except Exception:  # noqa: BLE001
        chg.append("volume")
    for k, kk in (("POSITION_PRICE_OPEN", "price_open"), ("POSITION_SL", "sl"), ("POSITION_TP", "tp")):
        try:
            if abs(float(R[k]) - R17[kk]) > 1e-6:
                chg.append(kk)
        except Exception:  # noqa: BLE001
            chg.append(kk)
    R["POSITION_CONTINUITY"] = "UNCHANGED" if not chg else "CHANGED"
    R["POSITION_CONTINUITY_FIELDS_CHANGED"] = chg
    if chg:
        STOP.append("POSITION_CHANGED_SINCE_R17")
    if R["MT5_POSITION_COUNT"] not in (1, "UNKNOWN"):
        STOP.append("MT5_POSITION_COUNT_CHANGED")
    if isinstance(R["PENDING_ORDERS"], int) and R["PENDING_ORDERS"] > 0:
        STOP.append("PENDING_ORDER_APPEARED")
    print("S3 continuity:", R["POSITION_CONTINUITY"], chg, flush=True)

    # ===== Stage 4 ledger =====
    R["LEDGER_EXISTS"] = "YES" if os.path.exists(LEDGER) else "NO"
    lines = []
    if R["LEDGER_EXISTS"] == "YES":
        st = os.stat(LEDGER)
        R["LEDGER_SHA256"] = sha(LEDGER)
        R["LEDGER_SIZE"] = st.st_size
        R["LEDGER_MTIME"] = iso(st.st_mtime)
        lines = [l for l in open(LEDGER, encoding="utf-8", errors="ignore") if l.strip()]
        R["LEDGER_LINE_COUNT"] = len(lines)
    else:
        R["LEDGER_SHA256"] = R["LEDGER_SIZE"] = R["LEDGER_MTIME"] = "UNAVAILABLE"
        R["LEDGER_LINE_COUNT"] = 0
    R["LEDGER_MATCHES_R17"] = "YES" if R["LEDGER_SHA256"] == LEDGER_R17 else "NO"
    if R["LEDGER_MATCHES_R17"] != "YES":
        STOP.append("LEDGER_HASH_CHANGED")
    print("S4 ledger:", R["LEDGER_SHA256"][:16] if isinstance(R["LEDGER_SHA256"], str) else R["LEDGER_SHA256"],
          R["LEDGER_LINE_COUNT"], "match_R17=", R["LEDGER_MATCHES_R17"], flush=True)

    # ===== Stage 5/6/7 evidence chain =====
    tk = str(R["POSITION_TICKET"])
    idt = str(R["POSITION_IDENTIFIER"])
    magic = str(R["POSITION_MAGIC"])
    comment = str(R["POSITION_COMMENT"])
    tkt_lines, idt_lines, mag_lines, cmt_lines, sym_lines = [], [], [], [], []
    def brief(i, raw):
        try:
            j = json.loads(raw)
        except Exception:  # noqa: BLE001
            return {"line": i + 1, "raw_head": raw[:200]}
        out = {"line": i + 1, "keys": sorted(j.keys())[:20]}
        for k in ("cycle", "utc_ts", "timestamp", "decision", "plan_id", "triggered", "wait_reason", "run_id",
                    "session_id", "execution_id", "ticket", "identifier", "order_id", "request_id", "symbol",
                    "side", "volume", "price", "price_open", "magic", "comment", "event", "event_type", "status"):
            if k in j and not isinstance(j[k], (dict, list)):
                out[k] = j[k]
        return out
    for i, raw in enumerate(lines):
        if tk and tk != "UNAVAILABLE" and tk in raw:
            tkt_lines.append(brief(i, raw))
        if idt and idt != "UNAVAILABLE" and idt in raw:
            idt_lines.append(brief(i, raw))
        if magic and magic != "UNAVAILABLE" and re.search(r'"magic"\s*:\s*' + re.escape(magic) + r"\b", raw):
            mag_lines.append(brief(i, raw))
        if comment and comment not in ("UNAVAILABLE", "None") and comment.lower() in raw.lower():
            cmt_lines.append(brief(i, raw))
        if "XAUUSD" in raw.upper():
            if R["POSITION_TYPE"] == "SELL" and re.search(r'(?i)"?(side|direction|type)"?\s*:\s*"?sell', raw):
                sym_lines.append(brief(i, raw))
            elif R["POSITION_TYPE"] == "BUY" and re.search(r'(?i)"?(side|direction|type)"?\s*:\s*"?buy', raw):
                sym_lines.append(brief(i, raw))
    R["TICKET_MATCH_LINES"] = [x["line"] for x in tkt_lines]
    R["IDENTIFIER_MATCH_LINES"] = [x["line"] for x in idt_lines]
    R["MAGIC_MATCH_LINES"] = [x["line"] for x in mag_lines]
    R["COMMENT_MATCH_LINES"] = [x["line"] for x in cmt_lines]
    R["SELL_XAUUSD_LINES"] = [x["line"] for x in sym_lines]
    R["TICKET_EVIDENCE"] = tkt_lines[:10]
    R["IDENTIFIER_EVIDENCE"] = idt_lines[:10]
    R["MAGIC_EVIDENCE"] = mag_lines[:10]
    R["COMMENT_EVIDENCE"] = cmt_lines[:10]
    if tkt_lines:
        R["PRIMARY_POSITION_RECORD"] = tkt_lines[0]
    print("S5/6/7:", json.dumps({"ticket": R["TICKET_MATCH_LINES"], "identifier": R["IDENTIFIER_MATCH_LINES"],
                                   "magic": R["MAGIC_MATCH_LINES"], "comment": R["COMMENT_MATCH_LINES"],
                                   "sell_xau": R["SELL_XAUUSD_LINES"][:8]}, ensure_ascii=False)[:500], flush=True)

    # ===== Stage 8 timezone =====
    R["MT5_SERVER_TIMEZONE_STATUS"] = "UNKNOWN"
    R["MT5_SERVER_TIMEZONE_NOTE"] = ("terminal_info()/account_info() expose no timezone field; no read-only proof of "
                                        "the FXTM server offset was obtained -> UNKNOWN; lifecycle matching therefore "
                                        "prioritised ticket/identifier/order_id over time")
    R["MATCH_PRIORITY_USED"] = "ticket > identifier > order_id/request_id > (avoided) time"

    # ===== Stage 9 strict CLOSE =====
    close_for = "UNKNOWN"
    close_evidence = []
    for x in (tkt_lines + idt_lines):
        blob = json.dumps(x, ensure_ascii=False).lower()
        if re.search(r"close|closed|exit|exit_price|deal", blob) and (tk in json.dumps(x) or idt in json.dumps(x)):
            close_for = "YES"
            close_evidence.append(x)
    if close_for == "UNKNOWN":
        for i, raw in enumerate(lines):
            if re.search(r"close|closed", raw, re.I):
                try:
                    j = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                if any(str(j.get(k)) == tk for k in ("ticket", "identifier", "position_id", "order_id", "request_id")):
                    close_for = "YES"
                    close_evidence.append({"line": i + 1, "keys": sorted(j.keys())[:12]})
    R["CLOSE_FOR_POSITION"] = close_for
    R["CLOSE_EVIDENCE"] = close_evidence[:5]
    R["DECISION_FOR_POSITION"] = "YES" if (tkt_lines or idt_lines) else "UNKNOWN"
    R["REQUEST_FOR_POSITION"] = "UNKNOWN"
    R["ORDER_FOR_POSITION"] = "UNKNOWN"
    R["FILL_FOR_POSITION"] = "UNKNOWN"
    R["OPEN_FOR_POSITION"] = "YES" if (tkt_lines or idt_lines) else "UNKNOWN"
    R["PNL_FOR_POSITION"] = "UNKNOWN"
    print("S9 close:", R["CLOSE_FOR_POSITION"], flush=True)

    # ===== Stage 10 ledger position state =====
    if R["CLOSE_FOR_POSITION"] == "YES" and R["MT5_POSITION_COUNT"] == 1:
        state = "CONFLICT"
    elif R["CLOSE_FOR_POSITION"] == "YES":
        state = "CLOSED"
    elif tkt_lines or idt_lines:
        state = "OPEN"
    else:
        state = "UNKNOWN"
    R["LEDGER_POSITION_STATE"] = state
    R["LEDGER_MT5_STATE_CONFLICT"] = "YES" if state == "CONFLICT" else ("NO" if state in ("OPEN", "CLOSED")
                                                                          else "UNKNOWN")
    R["V1_POSITION_OWNERSHIP"] = "V1_MANAGED" if (tkt_lines or idt_lines) else "UNKNOWN"
    print("S10 state:", state, "conflict=", R["LEDGER_MT5_STATE_CONFLICT"], flush=True)

    # ===== Stage 11 archive safety =====
    if state == "OPEN":
        R["ARCHIVE_WITH_OPEN_POSITION"] = "UNSAFE"
        R["ARCHIVE_SAFETY_REASON"] = ("MT5 holds a live XAUUSD position while the ledger that represents it would be "
                                        "closed off; a new active ledger would have no representation of it -> "
                                        "UNSAFE unless a legacy bridge exists (CONDITIONAL with bridge)")
        R["ARCHIVE_WITH_OPEN_POSITION_WITH_BRIDGE"] = "CONDITIONAL"
    elif state == "CLOSED":
        R["ARCHIVE_WITH_OPEN_POSITION"] = "SAFE"
        R["ARCHIVE_SAFETY_REASON"] = "position is closed in both ledger and MT5"
    elif state == "CONFLICT":
        R["ARCHIVE_WITH_OPEN_POSITION"] = "UNSAFE"
        R["ARCHIVE_SAFETY_REASON"] = "ledger says closed while MT5 still holds the position"
    else:
        R["ARCHIVE_WITH_OPEN_POSITION"] = "CONDITIONAL"
        R["ARCHIVE_SAFETY_REASON"] = "lifecycle not fully provable from the ledger"

    # ===== Stage 12 legacy bridge design (design only) =====
    R["LEGACY_POSITION_BRIDGE_DESIGN"] = {
        "LEGACY_POSITION_ID": "LEGACY-2377449557(proposed, not created)",
        "SOURCE_TICKET": R["POSITION_TICKET"], "SOURCE_LEDGER_LINE": (R["TICKET_MATCH_LINES"][0]
                                                                        if R["TICKET_MATCH_LINES"] else "UNKNOWN"),
        "SOURCE_RUN_ID": "UNKNOWN(see CURRENT_OLD_RUN_IDS)", "OPEN_TIME": R["POSITION_TIME_RAW_SERVER"],
        "SIDE": R["POSITION_TYPE"], "VOLUME": R["POSITION_VOLUME"], "OPEN_PRICE": R["POSITION_PRICE_OPEN"],
        "SL": R["POSITION_SL"], "TP": R["POSITION_TP"],
        "MANAGEMENT_POLICY_OPTIONS": ["FREEZE_ONLY", "MONITOR_ONLY", "LEGACY_MANAGED", "EXCLUDE_FROM_NEW_RUN"],
        "MANAGEMENT_POLICY_SELECTED": "NONE(not chosen by this audit)"}

    # ===== Stage 13 reset design options =====
    R["RESET_DESIGN_OPTIONS"] = [
        {"option": "A_inherit_position", "ledger_continuity": "continuous (new run adopts the open position)",
          "risk": "open position carried into a new run without proven full lifecycle; risk of double representation",
          "audit_complexity": "medium", "implementation": "explicit position adoption + bridge record"},
        {"option": "B_no_inherit_observe_only", "ledger_continuity": "broken for this position",
          "risk": "position left unmanaged by the new run", "audit_complexity": "low",
          "implementation": "read-only observation only"},
        {"option": "C_wait_until_closed", "ledger_continuity": "continuous at the cost of delay",
          "risk": "new run cannot start until the position closes", "audit_complexity": "low",
          "implementation": "wait for CLOSE evidence then start"},
        {"option": "D_explicit_bridge_then_start", "ledger_continuity": "continuous with an explicit bridge object",
          "risk": "bridge must be audited; extra artefacts", "audit_complexity": "high",
          "implementation": "legacy bridge + new run referencing it"}]
    R["RESET_DESIGN_RANKING"] = "NONE(factual comparison only)"
    R["NEW_RUN_CREATED"] = "NO"

    # ===== Stage 14 archive manifest =====
    manifest = []
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
                except OSError:
                    continue
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                after = rel[len(PREFIX):] if rel.startswith(PREFIX) else rel
                h = "SKIPPED_LARGE" if st.st_size > 5_000_000 else sha(p)
                manifest.append({"relative_path": rel, "size": st.st_size, "mtime": iso(st.st_mtime), "sha256": h,
                                   "classification": classify_rel(after)})
    counts = {}
    for x in manifest:
        counts[x["classification"]] = counts.get(x["classification"], 0) + 1
    R["ARCHIVE_CLASS_COUNTS"] = counts
    R["ARCHIVE_MANIFEST_COUNT"] = len(manifest)
    R["ARCHIVE_MANIFEST"] = manifest
    R["IMMUTABLE_ARCHIVE_CANDIDATE"] = [x["relative_path"] for x in manifest
                                          if x["classification"] in ("LEDGER", "DECISION_HISTORY", "STATISTICS", "REVIEWS")]
    R["ARCHIVE_MANIFEST_CREATED"] = "YES"
    R["MOVE"] = 0
    R["DELETE"] = 0
    R["RENAME"] = 0
    print("S14 manifest:", len(manifest), json.dumps(counts, ensure_ascii=False), flush=True)

    # ===== Stage 15 active vs historical =====
    active, hist, ambig = [], [], []
    for x in manifest:
        b = os.path.basename(x["relative_path"]).lower()
        if b in ("plan_ledger.jsonl", "state_package_latest.json", "workflow_latest.json", "statistics.json",
                   "workflow_history.jsonl", "trader_summary.txt", "plan_ledger.jsonl"):
            active.append(x["relative_path"])
        elif x["classification"] in ("LEDGER", "STATE", "STATISTICS", "DECISION_HISTORY"):
            ambig.append(x["relative_path"])
        else:
            hist.append(x["relative_path"])
    R["ACTIVE_STATE_FILES"] = active
    R["HISTORICAL_FILES"] = hist[:200]
    R["HISTORICAL_FILES_COUNT"] = len(hist)
    R["AMBIGUOUS_FILES"] = ambig[:200]
    R["AMBIGUOUS_FILES_COUNT"] = len(ambig)

    # ===== Stage 16 old run ids =====
    ids = set()
    for i, raw in enumerate(lines):
        for mm in re.finditer(r'"(run_id|session_id|execution_id)"\s*:\s*"([^"]{4,80})"', raw):
            ids.add(mm.group(2))
    for root in SCAN_DIRS:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if not f.lower().endswith((".json", ".jsonl", ".txt")):
                    continue
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    t = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                for mm in re.finditer(r'"(run_id|session_id|execution_id)"\s*:\s*"([^"]{4,80})"', t):
                    ids.add(mm.group(2))
                if len(ids) > 30:
                    break
    R["CURRENT_OLD_RUN_IDS"] = sorted(ids)[:20]

    # ===== Stage 17 state model =====
    R["STATE_MODEL"] = {"OLD_RUN": {"engine_baseline": BASE, "ledger": R["LEDGER_SHA256"],
                                      "position": {"ticket": R["POSITION_TICKET"],
                                                     "state": R["LEDGER_POSITION_STATE"]}},
                          "AUTOMATION": R["AUTOMATION_ENABLED"], "NEW_RUN": "NOT_CREATED"}

    # ===== Stage 21 + final =====
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_RESEARCH_MODIFIED"] = "NO" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "YES"
    if R["V3_RESEARCH_MODIFIED"] != "NO":
        STOP.append("V3_CHANGED")
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = []
    for r_, _, fs in os.walk(V2):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith((".py", ".yaml", ".yml")):
                p = os.path.join(r_, f)
                try:
                    if os.path.getmtime(p) > lim:
                        v2c.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                except OSError:
                    continue
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    if R["V2_SOURCE_CONFIG_MODIFIED"] != "NO":
        STOP.append("V2_CHANGED")
    for k in ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "PENDING_ORDER_CANCEL", "AUTOMATION_ENABLE",
                "AUTOMATION_RUN", "AUTOMATION_UPDATE", "V1_START", "V1_STOP", "V1_RESTART", "LEDGER_WRITE",
                "LEDGER_CLEAR", "STATE_WRITE", "STATE_CLEAR", "RUN_ID_CHANGE", "CONFIG_WRITE", "ENGINE_WRITE",
                "STRATEGY_CHANGE", "PARAMETER_CHANGE"):
        R[k] = 0
    R["GIT_COMMIT"] = "NONE"
    conds = {
        "1_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
        "2_v1_not_running": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
        "3_engine_hash_ok": R["ENGINE_SHA256"] == BASE,
        "4_position_unchanged": R["POSITION_CONTINUITY"] == "UNCHANGED",
        "5_pending_zero": R["PENDING_ORDERS"] == 0,
        "6_ledger_unchanged": R["LEDGER_MATCHES_R17"] == "YES",
        "7_ticket_search_done": True,
        "8_lifecycle_evidence": bool(R["TICKET_MATCH_LINES"] or R["IDENTIFIER_MATCH_LINES"]),
        "9_close_judged": R["CLOSE_FOR_POSITION"] in ("YES", "NO", "UNKNOWN"),
        "10_state_classified": R["LEDGER_POSITION_STATE"] in ("OPEN", "CLOSED", "UNKNOWN", "CONFLICT"),
        "11_manifest_created": R["ARCHIVE_MANIFEST_CREATED"] == "YES",
        "12_active_vs_historical": bool(R["ACTIVE_STATE_FILES"]),
        "13_old_run_ids": True,
        "14_v2v3_unchanged": R["V2_SOURCE_CONFIG_MODIFIED"] == "NO" and R["V3_RESEARCH_MODIFIED"] == "NO",
        "15_no_reset": True}
    R["R18_CONDITIONS"] = conds
    R["R18_GATE"] = "PASS" if all(conds.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_POSITION_LEDGER_SEAL_AUDIT_R18_COMPLETE"
    dump(0)


def dump(rc):
    json.dump(R, open(os.path.join(HERE, "V1_POSITION_LEDGER_SEAL_AUDIT_R18.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "MT5_POSITION_COUNT",
             "PENDING_ORDERS", "POSITION_TICKET", "POSITION_IDENTIFIER", "POSITION_TYPE", "POSITION_VOLUME",
             "POSITION_PRICE_OPEN", "POSITION_SL", "POSITION_TP", "POSITION_TIME", "POSITION_TIME_RAW_SERVER",
             "POSITION_MAGIC", "POSITION_COMMENT", "POSITION_CONTINUITY", "LEDGER_SHA256", "LEDGER_LINE_COUNT",
             "LEDGER_MATCHES_R17", "TICKET_MATCH_LINES", "IDENTIFIER_MATCH_LINES", "MAGIC_MATCH_LINES",
             "COMMENT_MATCH_LINES", "DECISION_FOR_POSITION", "REQUEST_FOR_POSITION", "ORDER_FOR_POSITION",
             "FILL_FOR_POSITION", "OPEN_FOR_POSITION", "CLOSE_FOR_POSITION", "PNL_FOR_POSITION",
             "LEDGER_POSITION_STATE", "LEDGER_MT5_STATE_CONFLICT", "V1_POSITION_OWNERSHIP",
             "MT5_SERVER_TIMEZONE_STATUS", "ARCHIVE_WITH_OPEN_POSITION", "CURRENT_OLD_RUN_IDS",
             "ARCHIVE_CLASS_COUNTS", "ARCHIVE_MANIFEST_CREATED", "NEW_RUN_CREATED", "R18_CONDITIONS", "R18_GATE",
             "STOP_REASON", "FORMAL_RESET", "NEXT_STAGE_AUTHORIZED"]
    print("\n=== §22 FINAL REPORT ===", flush=True)
    for k in keys:
        print(f"{k} = {R.get(k, 'UNKNOWN')}", flush=True)
    print("\nACTIVE_STATE_FILES =", R.get("ACTIVE_STATE_FILES"), flush=True)
    print("AMBIGUOUS_FILES_COUNT =", R.get("AMBIGUOUS_FILES_COUNT"), "| HISTORICAL_FILES_COUNT =",
          R.get("HISTORICAL_FILES_COUNT"), flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_POSITION_LEDGER_SEAL_AUDIT_R18.json"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
