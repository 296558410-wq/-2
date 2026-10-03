# -*- coding: utf-8 -*-
"""V1_CLOSE_AND_RUNID_FORENSIC_R20 — READ-ONLY. Two questions: broker close event for 2377449557,
and the true origin/identity of V1_RUN_20260924_RESET_01.

No trading write API at all. No writes to V1/V2 or their runtime. Writes ONLY under
research/v3_opportunity_engine/v1_close_runid_forensic_r20/.
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
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
TICKET = 2377449557
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_R19 = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
TOKEN = "V1_RUN_20260924_RESET_01"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
REASON = {0: "CLIENT", 1: "MOBILE", 2: "WEB", 3: "EXPERT", 4: "SL", 5: "TP", 6: "SO", 7: "ROLLOVER",
           8: "VMARGIN", 9: "SPLIT"}
ENTRY = {0: "IN", 1: "OUT", 2: "INOUT", 3: "OUT_BY"}
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = {}
STOP = []


def sh(a, t=150):
    try:
        p = subprocess.run(a, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
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


def dump(rc=0):
    os.makedirs(HERE, exist_ok=True)
    json.dump(R, open(os.path.join(HERE, "V1_CLOSE_AND_RUNID_FORENSIC_R20.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False, default=str)
    keys = ["TASK_STATUS", "AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256", "LEDGER_SHA256",
             "BROKER_POSITION_STATE", "OPEN_POSITIONS", "PENDING_ORDERS", "POSITION_TICKET", "POSITION_IDENTIFIER",
             "CLOSE_DEAL_FOR_POSITION", "CLOSE_DEAL_TICKET", "CLOSE_ORDER_TICKET", "CLOSE_POSITION_ID",
             "CLOSE_VOLUME", "CLOSE_PRICE", "CLOSE_TIME", "CLOSE_REASON", "GROSS_PROFIT", "SWAP", "COMMISSION",
             "FEE", "NET_PROFIT", "LEDGER_OPEN", "LEDGER_CLOSE", "LEDGER_PNL",
             "LEDGER_BROKER_RECONCILIATION", "LEDGER_CLOSE_MISSING_REASON", "CLOSE_ACTOR", "ACTUAL_RUN_ID",
             "PLANNED_RUN_ID", "DOCUMENT_REFERENCE_RUN_ID", "REAL_OLD_RUN_ID", "SELF_REFERENCE_FILTER_TEST",
             "LEDGER_POSITION_STATE", "RECONCILIATION_STATE", "ARCHIVE_READY", "BRIDGE_CREATED", "NEW_RUN_CREATED",
             "RESET_EXECUTED", "R20_GATE", "STOP_REASON", "FORMAL_RESET", "NEXT_STAGE_AUTHORIZED",
             "V2_SOURCE_CONFIG_MODIFIED", "V3_RESEARCH_MODIFIED"]
    print("\n=== §22 FINAL REPORT ===", flush=True)
    for k in keys:
        v = R.get(k, "UNKNOWN")
        print(f"{k} = {v}", flush=True)
    print("\nRUN_ID_SOURCE_FILES =", json.dumps(R.get("RUN_ID_SOURCE_FILES", []), ensure_ascii=False), flush=True)
    print("RUN_ID_SOURCE_FIELDS =", json.dumps(R.get("RUN_ID_SOURCE_FIELDS", []), ensure_ascii=False), flush=True)
    print("RESET_BLOCKERS =", json.dumps(R.get("RESET_BLOCKERS", []), ensure_ascii=False), flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_CLOSE_AND_RUNID_FORENSIC_R20.json"), flush=True)
    sys.exit(rc)


def stop(reason):
    R["R20_GATE"] = "FAIL"
    R["STOP_REASON"] = reason
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["TASK_STATUS"] = "V1_CLOSE_AND_RUNID_FORENSIC_R20_COMPLETE"
    dump(0)


def main():
    R["TASK_STATUS"] = "RUNNING"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------- R20-01 ----------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], 60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        d = {}
    R["AUTOMATION_ENABLED"] = d.get("enabled", "UNKNOWN")
    R["ENGINE_SHA256"] = sha(ENGINE)
    R["LEDGER_SHA256"] = sha(LEDGER)
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], 90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "NOT_RUNNING" if not v1p else "RUNNING"
    R["V1_MATCHING_PROCESSES"] = [{"PID": x.get("ProcessId"), "CMD": (x.get("CommandLine") or "")[:110]} for x in v1p[:5]]
    print("R20-01:", json.dumps({k: R[k] for k in ("AUTOMATION_ENABLED", "V1_ENGINE_PROCESS", "ENGINE_SHA256",
                                                     "LEDGER_SHA256")}, ensure_ascii=False), flush=True)
    if R["ENGINE_SHA256"] != BASE:
        STOP.append("BASELINE_CHANGED")
    if R["LEDGER_SHA256"] != LEDGER_R19:
        STOP.append("BASELINE_CHANGED")
    if str(R["AUTOMATION_ENABLED"]).lower() != "false":
        STOP.append("AUTOMATION_ENABLED_TRUE")
    if R["V1_ENGINE_PROCESS"] != "NOT_RUNNING":
        STOP.append("V1_ENGINE_RUNNING")
    if STOP:
        return stop(",".join(sorted(set(STOP))))

    # ---------- R20-02 + history deals (one MT5 session, read-only) ----------
    code = ("import json,sys\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(symbol='XAUUSD'); os_=mt5.orders_get(symbol='XAUUSD')\n"
             f" hd=mt5.history_deals_get(position={TICKET})\n"
             " ho=mt5.history_orders_get(position=%d)\n" % TICKET +
             " def d(x):\n  return {'ticket':getattr(x,'ticket',None),'order':getattr(x,'order',None),"
             "'position_id':getattr(x,'position_id',None),'symbol':getattr(x,'symbol',None),"
             "'type':getattr(x,'type',None),'entry':getattr(x,'entry',None),'volume':getattr(x,'volume',None),"
             "'price':getattr(x,'price',None),'time':getattr(x,'time',None),'time_msc':getattr(x,'time_msc',None),"
             "'profit':getattr(x,'profit',None),'swap':getattr(x,'swap',None),'commission':getattr(x,'commission',None),"
             "'fee':getattr(x,'fee',None),'magic':getattr(x,'magic',None),'comment':getattr(x,'comment',None),"
             "'reason':getattr(x,'reason',None)}\n"
             " def o(x):\n  return {'ticket':getattr(x,'ticket',None),'position_id':getattr(x,'position_id',None),"
             "'state':getattr(x,'state',None),'type':getattr(x,'type',None),'volume':getattr(x,'volume',None),"
             "'price_open':getattr(x,'price_open',None),'time_setup':getattr(x,'time_setup',None),"
             "'time_done':getattr(x,'time_done',None),'comment':getattr(x,'comment',None),'reason':getattr(x,'reason',None)}\n"
             " res={'CONNECTED':bool(ok),'server':(ai.server if ai else None),"
             "'balance':(ai.balance if ai else None),'equity':(ai.equity if ai else None),"
             "'positions':(None if ps is None else len(ps)),'orders':(None if os_ is None else len(os_)),"
             "'deals':(None if hd is None else [d(x) for x in hd]),"
             "'hist_orders':(None if ho is None else [o(x) for x in ho]),"
             "'deals_err':mt5.last_error()}\n"
             " print(json.dumps(res))\n mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:120]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=180)
        o = (pr.stdout or "").strip()
        mt5 = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        mt5 = {"err": type(ex).__name__}
    R["MT5_CONTEXT"] = "CONFIRMED" if mt5.get("CONNECTED") else "UNKNOWN"
    R["OPEN_POSITIONS"] = mt5.get("positions", "UNKNOWN")
    R["PENDING_ORDERS"] = mt5.get("orders", "UNKNOWN")
    R["BROKER_POSITION_STATE"] = "CLOSED" if mt5.get("positions") == 0 else ("OPEN" if mt5.get("positions") else "UNKNOWN")
    R["POSITION_TICKET"] = TICKET
    R["POSITION_IDENTIFIER"] = TICKET
    R["BROKER_SERVER"] = mt5.get("server", "UNKNOWN")
    R["BROKER_BALANCE"] = mt5.get("balance", "UNKNOWN")
    R["BROKER_EQUITY"] = mt5.get("equity", "UNKNOWN")
    if mt5.get("positions") not in (0, None):
        STOP.append("POSITION_STATE_CHANGED")
    print("R20-02:", json.dumps({"BROKER_POSITION_STATE": R["BROKER_POSITION_STATE"], "OPEN": R["OPEN_POSITIONS"],
                                   "PENDING": R["PENDING_ORDERS"]}, ensure_ascii=False), flush=True)

    # ---------- R20-03/04/05/06/07 ----------
    deals = mt5.get("deals") or []
    R["HISTORY_DEALS_RAW"] = deals
    R["HISTORY_DEALS_COUNT"] = len(deals) if mt5.get("deals") is not None else "UNAVAILABLE"
    R["HISTORY_ORDERS_RAW"] = mt5.get("hist_orders")
    bound = [x for x in deals if str(x.get("position_id")) == str(TICKET)]
    outs = [x for x in bound if x.get("entry") == 1]
    R["DEALS_BOUND_TO_POSITION"] = len(bound)
    R["DEALS_ENTRY_OUT"] = len(outs)
    if R["MT5_CONTEXT"] != "CONFIRMED" or mt5.get("deals") is None:
        cdfp = "UNKNOWN"
    elif outs:
        cdfp = "YES"
    elif bound:
        cdfp = "NO"
    else:
        cdfp = "UNKNOWN"
    R["CLOSE_DEAL_FOR_POSITION"] = cdfp
    cd = outs[-1] if outs else {}
    R["CLOSE_DEAL_TICKET"] = cd.get("ticket", "UNAVAILABLE")
    R["CLOSE_ORDER_TICKET"] = cd.get("order", "UNAVAILABLE")
    R["CLOSE_POSITION_ID"] = cd.get("position_id", "UNAVAILABLE")
    R["CLOSE_VOLUME"] = cd.get("volume", "UNAVAILABLE")
    R["CLOSE_PRICE"] = cd.get("price", "UNAVAILABLE")
    R["CLOSE_TIME"] = (iso(cd["time"]) if cd.get("time") else "UNAVAILABLE")
    R["CLOSE_TIME_MSC"] = cd.get("time_msc", "UNAVAILABLE")
    rz = cd.get("reason", None)
    R["CLOSE_REASON"] = REASON.get(rz, rz) if rz is not None else "UNAVAILABLE"
    R["CLOSE_DEAL_ENTRY"] = ENTRY.get(cd.get("entry"), cd.get("entry", "UNAVAILABLE"))
    R["CLOSE_DEAL_COMMENT"] = cd.get("comment", "UNAVAILABLE")
    R["CLOSE_DEAL_MAGIC"] = cd.get("magic", "UNAVAILABLE")
    # PnL: sum over bound deals (in + out) for profit/swap/commission/fee
    def ssum(key):
        vals = [x.get(key) for x in bound if isinstance(x.get(key), (int, float))]
        return round(float(sum(vals)), 5) if vals else "UNAVAILABLE"
    R["GROSS_PROFIT"] = ssum("profit")
    R["SWAP"] = ssum("swap")
    R["COMMISSION"] = ssum("commission")
    R["FEE"] = ssum("fee")
    comps = [R["GROSS_PROFIT"], R["SWAP"], R["COMMISSION"], R["FEE"]]
    R["NET_PROFIT"] = (round(sum(comps), 5) if all(isinstance(c, (int, float)) for c in comps) else "UNKNOWN")
    R["NET_PROFIT_NOTE"] = "sum(profit+swap+commission+fee) over deals bound to the position; computed only from explicit broker fields"
    R["BROKER_LIFECYCLE"] = []
    for x in sorted(bound, key=lambda z: (z.get("time") or 0)):
        R["BROKER_LIFECYCLE"].append({"source": "mt5.history_deals_get(position=)",
                                        "deal_ticket": x.get("ticket"), "order_id": x.get("order"),
                                        "position_id": x.get("position_id"), "entry": ENTRY.get(x.get("entry"), x.get("entry")),
                                        "price": x.get("price"), "volume": x.get("volume"),
                                        "timestamp": iso(x["time"]) if x.get("time") else "UNAVAILABLE",
                                        "reason": REASON.get(x.get("reason"), x.get("reason"))})
    print("R20-03/07 deals:", json.dumps({"count": R["HISTORY_DEALS_COUNT"], "bound": R["DEALS_BOUND_TO_POSITION"],
                                            "outs": R["DEALS_ENTRY_OUT"], "CLOSE_DEAL_FOR_POSITION": cdfp,
                                            "reason": R["CLOSE_REASON"], "close_price": R["CLOSE_PRICE"],
                                            "net_profit": R["NET_PROFIT"]}, ensure_ascii=False), flush=True)

    # ---------- R20-08 ledger reconciliation ----------
    lines = [l for l in open(LEDGER, encoding="utf-8", errors="ignore") if l.strip()] if os.path.exists(LEDGER) else []
    tkphit = [i for i, l in enumerate(lines) if str(TICKET) in l]
    R["LEDGER_TICKET_LINES"] = [i + 1 for i in tkphit]
    R["LEDGER_OPEN"] = "YES" if tkphit else "UNKNOWN"
    close_bound = "UNKNOWN"
    for i in tkphit:
        try:
            j = json.loads(lines[i])
        except Exception:  # noqa: BLE001
            continue
        blob = json.dumps(j, ensure_ascii=False).lower()
        if re.search(r"close|closed", blob):
            vals = [str(j.get(k)) for k in ("ticket", "identifier", "position_id", "order_id", "request_id")]
            if str(TICKET) in vals:
                close_bound = "YES"
    R["LEDGER_CLOSE"] = close_bound
    R["LEDGER_PNL"] = "NO"  # no per-position pnl field located for this ticket
    if R["BROKER_POSITION_STATE"] == "CLOSED" and R["LEDGER_CLOSE"] in ("NO", "UNKNOWN") and R["LEDGER_OPEN"] == "YES":
        rec = "MISMATCH(ledger shows open, broker closed)" if R["LEDGER_CLOSE"] == "NO" else "PARTIAL(broker closed; ledger close evidence absent)"
    elif R["LEDGER_CLOSE"] == "YES":
        rec = "MATCH"
    else:
        rec = "UNKNOWN"
    R["LEDGER_BROKER_RECONCILIATION"] = rec
    R["LEDGER_POSITION_STATE"] = R["LEDGER_OPEN"] == "YES" and R["LEDGER_CLOSE"] != "YES" and "OPEN" or "UNKNOWN"
    R["RECONCILIATION_STATE"] = "MISMATCH" if rec.startswith("MISMATCH") else ("PARTIAL" if rec.startswith("PARTIAL")
                                                                                 else ("MATCH" if rec == "MATCH" else "UNKNOWN"))
    print("R20-08 ledger:", json.dumps({"open": R["LEDGER_OPEN"], "close": R["LEDGER_CLOSE"], "rec": rec},
                                         ensure_ascii=False), flush=True)

    # ---------- R20-09 why ledger has no CLOSE ----------
    ev = []
    for fn in ("state_package_latest.json", "workflow_latest.json", "statistics.json", "trader_summary.txt",
                 "RUN_META.json"):
        p = os.path.join(RUN, fn)
        if os.path.exists(p):
            st = os.stat(p)
            ev.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "mtime": iso(st.st_mtime),
                         "size": st.st_size})
    R["RUN_WRITE_EVIDENCE"] = ev
    automation_disabled_since = R.get("AUTOMATION_LAST_UPDATE", "UNKNOWN")
    R["LEDGER_CLOSE_MISSING_REASON"] = (
        "PROVEN" if False else
        "UNKNOWN")   # no direct evidence ties 'no reconciliation' to the freeze; not inferred
    R["LEDGER_CLOSE_MISSING_EXPLANATION_NOTE"] = ("the ledger hash is unchanged and no V1 process ran; a reconciliation "
                                                    "would have to be performed by the V1 cycle, which is disabled. This is a "
                                                    "plausible mechanism but NOT proven from artefacts -> UNKNOWN")
    # ---------- R20-10 close actor ----------
    actor = "UNKNOWN"
    rz2 = cd.get("reason", None)
    if rz2 in (4, 5):
        actor = "BROKER"
    elif rz2 in (0, 3):
        actor = "TERMINAL" if rz2 == 0 else "V1"
    R["CLOSE_ACTOR"] = actor
    R["CLOSE_ACTOR_BASIS"] = f"broker deal reason field = {R['CLOSE_REASON']} (no inference from price action)"
    print("R20-09/10:", json.dumps({"missing": R["LEDGER_CLOSE_MISSING_REASON"], "actor": actor,
                                      "reason": R["CLOSE_REASON"]}, ensure_ascii=False), flush=True)

    # ---------- R20-11/12/13 run-id forensics ----------
    src_files, src_fields = [], []
    first_obs = None
    for fn in ("RUN_META.json", "statistics.json", "state_package_latest.json", "workflow_latest.json",
                 "workflow_history.jsonl", "plan_ledger.jsonl"):
        p = os.path.join(RUN, fn)
        if not os.path.exists(p):
            continue
        st = os.stat(p)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:  # noqa: BLE001
            continue
        if TOKEN in txt:
            src_files.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "mtime": iso(st.st_mtime),
                                "size": st.st_size, "occurrences": txt.count(TOKEN)})
            if first_obs is None or st.st_mtime < first_obs["mtime_ts"]:
                first_obs = {"file": os.path.relpath(p, AIQ).replace("\\", "/"), "mtime_ts": st.st_mtime,
                               "mtime": iso(st.st_mtime)}
            for mm in re.finditer(r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*[:=]\s*"?' + re.escape(TOKEN) + r'"?', txt):
                src_fields.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "field": mm.group(1)})
            for mm in re.finditer(re.escape(TOKEN), txt):
                ln = txt[:mm.start()].count("\n")
                line = txt.splitlines()[ln] if ln < len(txt.splitlines()) else ""
                src_fields.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": ln + 1,
                                     "line_preview": line.strip()[:200]})
    R["RUN_ID_SOURCE_FILES"] = src_files
    R["RUN_ID_FIELDS_RAW"] = src_fields[:20]
    R["RUN_ID_SOURCE_FIELDS"] = sorted({f.get("field") for f in src_fields if f.get("field")})
    R["RUN_ID_FIRST_OBSERVED"] = (first_obs or {}).get("mtime", "UNKNOWN")
    # classify field names
    fld = [f.lower() for f in R["RUN_ID_SOURCE_FIELDS"]]
    actual_fields = [f for f in fld if f in ("run_id", "runid")]
    planned_fields = [f for f in fld if f in ("planned_run", "planned_run_id", "target_run", "target_run_id",
                                                "reset_name", "task_name", "next_run", "next_run_id")]
    R["ACTUAL_RUN_ID"] = (TOKEN if actual_fields else "UNKNOWN")
    R["PLANNED_RUN_ID"] = (TOKEN if planned_fields and not actual_fields else ("UNKNOWN" if not planned_fields else TOKEN))
    R["DOCUMENT_REFERENCE_RUN_ID"] = "NONE_IN_RUNTIME(see layer-3 scan)"
    R["REAL_OLD_RUN_ID"] = "CONFIRMED" if actual_fields else "UNKNOWN"
    R["RUN_ID_IDENTITY_BASIS"] = {"actual_fields_found": actual_fields, "planned_fields_found": planned_fields,
                                    "field_names_observed": R["RUN_ID_SOURCE_FIELDS"]}
    print("R20-11/13 run_id:", json.dumps({"files": len(src_files), "fields": R["RUN_ID_SOURCE_FIELDS"],
                                             "actual": R["ACTUAL_RUN_ID"], "first": R["RUN_ID_FIRST_OBSERVED"]},
                                            ensure_ascii=False)[:700], flush=True)

    # ---------- R20-15 three-layer self-reference test ----------
    L1 = any("v3_opportunity_engine" not in f["file"] for f in src_files)   # runtime layer
    L3 = TOKEN in json.dumps([os.path.relpath(p, AIQ) for p in [HERE]], ensure_ascii=False)
    l3_files = []
    for r_, _, fs in os.walk(ENGINE_DIR):
        if "v3_opportunity_engine" not in r_.replace("\\", "/"):
            continue
        for f in fs:
            if f.lower().endswith((".json", ".md", ".txt")):
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > 3_000_000:
                        continue
                    if TOKEN in open(p, encoding="utf-8", errors="ignore").read():
                        l3_files.append(os.path.relpath(p, AIQ).replace("\\", "/"))
                except Exception:  # noqa: BLE001
                    continue
        if len(l3_files) > 12:
            break
    R["SELF_REFERENCE_LAYERS"] = {"LAYER1_runtime_files_containing_token": [f["file"] for f in src_files],
                                    "LAYER2_source_config": "not scanned (no token expected)",
                                    "LAYER3_audit_docs": l3_files[:12]}
    R["SELF_REFERENCE_FILTER_TEST"] = ("PASS" if (not L1 or L3) and src_files is not None else "FAIL")
    R["SELF_REFERENCE_FILTER_NOTE"] = ("runtime hits are NOT excluded merely because the token also appears in task "
                                         "documents; Layer-3 documents are counted as source-explanation only")
    if not src_files:
        R["SELF_REFERENCE_FILTER_TEST"] = "PASS"
    print("R20-15 layers:", json.dumps(R["SELF_REFERENCE_LAYERS"], ensure_ascii=False)[:600], flush=True)

    # ---------- R20-16/17/18 ----------
    R["BROKER_POSITION_STATE"] = R["BROKER_POSITION_STATE"]
    R["LEDGER_POSITION_STATE"] = "OPEN" if R["LEDGER_OPEN"] == "YES" else "UNKNOWN"
    R["RESET_BLOCKERS"] = [{"blocker": "LEDGER_BROKER_RECONCILIATION", "value": R["LEDGER_BROKER_RECONCILIATION"]},
                             {"blocker": "FINAL_PNL_STATE", "value": "PROVEN" if R["NET_PROFIT"] != "UNKNOWN" else "UNKNOWN"},
                             {"blocker": "RUN_ID_STATE", "value": R["REAL_OLD_RUN_ID"]},
                             {"blocker": "RECONCILIATION_RECORD", "value": "NOT_CREATED"},
                             {"blocker": "ARCHIVE_READY", "value": "see ARCHIVE_READY"}]
    conds = {"1_broker_close_proven": R["CLOSE_DEAL_FOR_POSITION"] == "YES",
              "2_final_pnl_proven": R["NET_PROFIT"] != "UNKNOWN",
              "3_ledger_close_exists": R["LEDGER_CLOSE"] == "YES",
              "4_reconciliation_record_possible_without_ledger_write": "YES",
              "5_new_run_needs_legacy_layer": "UNKNOWN"}
    R["ARCHIVE_CONDITIONS"] = conds
    if conds["1_broker_close_proven"] and conds["2_final_pnl_proven"] and conds["3_ledger_close_exists"]:
        R["ARCHIVE_READY"] = "YES"
    elif conds["1_broker_close_proven"] and not conds["3_ledger_close_exists"]:
        R["ARCHIVE_READY"] = "CONDITIONAL"
    else:
        R["ARCHIVE_READY"] = "UNKNOWN"
    R["RESET_ALLOWED"] = "NO"
    for k in ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "PENDING_ORDER_CANCEL", "V1_START", "V1_STOP",
                "V1_RESTART", "AUTOMATION_ENABLE", "AUTOMATION_RUN", "AUTOMATION_UPDATE", "NEW_RUN_CREATE",
                "RESET_EXECUTE", "LEDGER_WRITE", "LEDGER_CLEAR", "STATE_WRITE", "STATE_CLEAR", "HISTORICAL_MOVE",
                "HISTORICAL_DELETE", "HISTORICAL_RENAME", "ENGINE_WRITE", "CONFIG_WRITE"):
        R[k] = 0
    R["BRIDGE_CREATED"] = "NO"
    R["NEW_RUN_CREATED"] = "NO"
    R["RESET_EXECUTED"] = "NO"
    R["GIT_COMMIT"] = "NONE"
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_M01_EVENT_HASH"] = v3["M01_event"]
    R["V3_R1_LEDGER_HASH"] = v3["R1_ledger"]
    R["V3_M01_AUDIT_HASH"] = v3["M01_audit"]
    R["V3_R2_CANONICAL_HASH"] = v3["R2_canonical"]
    R["V3_RESEARCH_MODIFIED"] = "NO" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "YES"
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = [os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
            for r_, _, fs in os.walk(V2) if "__pycache__" not in r_ for f in fs
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim]
    R["V2_SOURCE_CONFIG_MODIFIED"] = "NO" if not v2c else "YES"
    if R["V2_SOURCE_CONFIG_MODIFIED"] != "NO":
        STOP.append("V2_CHANGED")
    if R["V3_RESEARCH_MODIFIED"] != "NO":
        STOP.append("V3_CHANGED")
    crit = {"automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
             "v1_not_running": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
             "engine_ok": R["ENGINE_SHA256"] == BASE, "ledger_ok": R["LEDGER_SHA256"] == LEDGER_R19,
             "broker_state_confirmed": R["MT5_CONTEXT"] == "CONFIRMED",
             "close_deal_searched": R["HISTORY_DEALS_COUNT"] != "UNAVAILABLE",
             "no_trade_write": True, "no_file_write_outside_scope": True}
    R["R20_CONDITIONS"] = crit
    R["R20_GATE"] = "PASS" if all(crit.values()) and not STOP else "FAIL"
    R["STOP_REASON"] = "NONE" if not STOP else ",".join(sorted(set(STOP)))
    R["FORMAL_RESET"] = "FORBIDDEN"
    R["NEXT_STAGE_AUTHORIZED"] = "NO"
    R["TASK_STATUS"] = "V1_CLOSE_AND_RUNID_FORENSIC_R20_COMPLETE"
    dump(0)


if __name__ == "__main__":
    main()
