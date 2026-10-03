# -*- coding: utf-8 -*-
"""V1_GATEWAY_SAFETY_AUDIT_R4 — READ-ONLY. Gateway automation -> M15 schedule -> restart/respawn -> trade-state
sources -> cycle boundary. Nothing is modified; no stop; no order API write; no commit.

All prohibitions of section 8 honoured. Any UNKNOWN/uncertain result => NOT_PROVEN => STOP.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
OC = os.path.join(HOME, ".openclaw")
V1 = os.path.join(RE, "hermes", "trader_v1")
RUN = os.path.join(V1, "run_state")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOWU = datetime.now(timezone.utc)
NOWL = datetime.now().astimezone()
KW = ("trader_v1", "hermes-trader", "engine.py", "hermes_trader", "hermes-trader-m15")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


def sh(*a, cwd=None):
    try:
        p = subprocess.run(list(a), cwd=cwd or AIQ, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=240)
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
    O["CURRENT_TIME_LOCAL"] = NOWL.isoformat()

    # ---------------- §一 Gateway automation definition ----------------
    cands, scanned = [], 0
    roots = [OC, os.path.join(OC, "workspace"), os.path.join(OC, "agents")]
    skip = ("node_modules", ".git", "__pycache__", "mt5_instances", "logs")
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            if any(s in r_ for s in skip):
                continue
            for f in fs:
                if not f.lower().endswith((".json", ".jsonl", ".yaml", ".yml", ".js", ".cjs", ".mjs", ".md", ".txt",
                                             ".cmd", ".ps1")):
                    continue
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > 3_000_000:
                        continue
                except OSError:
                    continue
                scanned += 1
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                low = txt.lower()
                if any(k in low for k in KW):
                    ctx = []
                    for m in re.finditer(r"(?i)(trader_v1|hermes-trader[\w-]*|engine\.py)", txt):
                        ln = txt[:m.start()].count("\n") + 1
                        seg = txt.splitlines()[max(0, ln - 2):ln + 2]
                        ctx.append({"line": ln, "match": m.group(0), "context": " | ".join(s.strip() for s in seg)[:300]})
                        if len(ctx) >= 4:
                            break
                    rel = os.path.relpath(p, AIQ).replace("\\", "/")
                    cands.append({"path": rel, "size": os.path.getsize(p), "matched_context": ctx,
                                    "classification": ("ARCHIVED" if re.search(r"archive|backup|old|bak|history",
                                                                                 rel, re.I) else "LOADED_CANDIDATE")})
                if scanned > 5000:
                    break
            if scanned > 5000:
                break
    O["GATEWAY_AUTOMATION_CANDIDATES"] = cands[:25]
    O["GATEWAY_V1_AUTOMATION_FOUND"] = "YES" if cands else "NO"
    loaded = [c for c in cands if c["classification"] == "LOADED_CANDIDATE"]
    O["GATEWAY_V1_AUTOMATION_SOURCE"] = (loaded[0]["path"] if loaded else (cands[0]["path"] if cands else "NOT_FOUND"))
    O["GATEWAY_V1_AUTOMATION_ID"] = "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ENABLED"] = "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ACTION"] = "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_ARGUMENTS"] = "UNKNOWN"
    O["GATEWAY_V1_AUTOMATION_WORKING_DIRECTORY"] = "UNKNOWN"
    # try to read a structured automation entry from the top candidate
    if loaded:
        try:
            doc = open(os.path.join(AIQ, loaded[0]["path"]), encoding="utf-8", errors="ignore").read()
            m = re.search(r'"([\w\-.]*(?:trader[-_]?v1|hermes[-_]trader)[\w\-.]*)"\s*:\s*(\{.*?\})\s*[,}]', doc, re.S)
            if m:
                O["GATEWAY_V1_AUTOMATION_ID"] = m.group(1)
                try:
                    entry = json.loads(m.group(2))
                    for k in ("enabled", "schedule", "cron", "interval", "command", "action", "args", "arguments",
                               "cwd", "workingDirectory", "restart", "retry"):
                        if k in entry:
                            O[f"GATEWAY_ENTRY_{k.upper()}"] = entry[k]
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
    O["gateway_cmd"] = (open(os.path.join(OC, "gateway.cmd"), encoding="utf-8", errors="ignore").read()[:800]
                         if os.path.exists(os.path.join(OC, "gateway.cmd")) else None)
    print(f"§1 automation: scanned={scanned} candidates={len(cands)} loaded={len(loaded)}", flush=True)
    for c in cands[:8]:
        print("   ", c["classification"], c["path"], "|", str(c["matched_context"][:1])[:160], flush=True)

    # ---------------- §二 M15 schedule (only from the V1 automation) ----------------
    O["SCHEDULE_TYPE"] = "UNKNOWN"
    O["SCHEDULE_EXPRESSION"] = "UNKNOWN"
    O["TIMEZONE"] = "UNKNOWN"
    O["INTERVAL"] = "UNKNOWN"
    O["OFFSET"] = "UNKNOWN"
    O["V1_M15_SCHEDULE_SOURCE"] = "UNKNOWN"
    O["V1_M15_OFFSET"] = "UNKNOWN"
    O["V1_NEXT_CYCLE"] = "UNKNOWN"
    O["LAST_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["NEXT_EXPECTED_V1_CYCLE"] = "UNKNOWN"
    O["MINUTES_TO_NEXT_V1_CYCLE"] = "UNKNOWN"
    O["schedule_note"] = ("no V1-specific schedule definition was proven; the 15-minute cadence of "
                           "hermes-v2-cycle / hermes-tick-collect is NOT used as evidence (section 2 forbids it)")
    print("§2 M15: UNKNOWN (no proven V1 automation schedule; other tasks' cadence not used)", flush=True)

    # ---------------- §三 restart / respawn audit ----------------
    restart_hits = []
    for root in (V1, OC):
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            if any(s in r_ for s in skip):
                continue
            for f in fs:
                if not f.lower().endswith((".py", ".js", ".cjs", ".json", ".yaml", ".yml", ".cmd", ".ps1")):
                    continue
                p = os.path.join(r_, f)
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                for m in re.finditer(r"(?i)(restart|retry|respawn|relaunch|keepalive|on_exit|on_failure|watchdog|"
                                       r"heartbeat|supervisor)", txt):
                    ln = txt[:m.start()].count("\n") + 1
                    rel = os.path.relpath(p, AIQ).replace("\\", "/")
                    v1link = bool(re.search(r"trader_v1|hermes-trader|engine\.py", txt, re.I))
                    restart_hits.append({"MECHANISM": m.group(0).lower(), "SOURCE": rel, "line": ln,
                                           "V1_LINKED": v1link})
                    if len(restart_hits) > 300:
                        break
    v1linked = [h for h in restart_hits if h["V1_LINKED"]]
    O["RESTART_MECHANISMS"] = {"total_hits": len(restart_hits), "v1_linked_hits": len(v1linked),
                                 "examples": restart_hits[:20], "v1_linked_examples": v1linked[:10]}
    O["AUTO_RESTART_MECHANISM"] = ("YES" if v1linked else "UNKNOWN")
    O["V1_RESTART_TRIGGER"] = "UNKNOWN"
    O["V1_RESTART_DELAY"] = "UNKNOWN"
    O["V1_RESTART_RACE"] = "UNKNOWN"
    O["restart_note"] = ("other tasks having restart settings is NOT treated as V1 evidence (section 3); only a "
                          "V1-linked mechanism counts, and none is proven to execute")
    print(f"§3 restart: hits={len(restart_hits)} v1_linked={len(v1linked)} -> AUTO_RESTART_MECHANISM={O['AUTO_RESTART_MECHANISM']} RACE=UNKNOWN", flush=True)

    # ---------------- §四 trade-state sources (code tracing) ----------------
    trace = {}
    py = []
    for r_, _, fs in os.walk(V1):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith(".py"):
                py.append(os.path.join(r_, f))
    API = re.compile(r"(positions_get|orders_get|order_check|order_send|positions_total|orders_total|history_|"
                       r"account_info|symbol_info|mt5\.|broker\.|MetaTrader5)", re.I)
    FILEPAT = re.compile(r"[\"']([\w./\\-]*(?:position|order|execution|pending|fill|close|retry|trade|state)[\w./\\-]*"
                          r"\.(?:json|jsonl))[\"']", re.I)
    for p in py:
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:  # noqa: BLE001
            continue
        rel = os.path.relpath(p, AIQ).replace("\\", "/")
        funcs = [m.group(1) for m in re.finditer(r"^def\s+([A-Za-z_][\w]*)\s*\(", txt, re.M)]
        apis = sorted({m.group(0) for m in API.finditer(txt)})
        files = sorted({m.group(1) for m in FILEPAT.finditer(txt)})
        if apis or files:
            trace[rel] = {"functions": funcs[:25], "broker_api_tokens": apis[:10], "state_files_referenced": files[:10]}
    O["CODE_TRACE"] = trace
    O["V1_POSITION_SOURCE"] = ("MT5 (code reads positions via broker API)" if any("positions_get" in json.dumps(v)
                                                                                    for v in trace.values())
                                 else "UNKNOWN")
    O["V1_PENDING_ORDER_SOURCE"] = ("MT5 (orders_get)" if any("orders_get" in json.dumps(v) for v in trace.values())
                                      else "UNKNOWN")
    O["V1_EXECUTION_STATE_SOURCE"] = "UNKNOWN"
    O["V1_REQUEST_STATE_SOURCE"] = "UNKNOWN"
    O["V1_FILL_STATE_SOURCE"] = "UNKNOWN"
    O["MT5_READ_CONTEXT"] = {"READ_SOURCE": ("MT5" if O["V1_POSITION_SOURCE"].startswith("MT5") else "UNKNOWN"),
                              "READ_ONLY": "YES", "TERMINAL": "UNKNOWN", "ACCOUNT": "UNKNOWN", "SYMBOL": "UNKNOWN"}
    print(f"§4 trace files={len(trace)} position_source={O['V1_POSITION_SOURCE'][:40]}", flush=True)

    # ---------------- §五 trade state (read-only, never a write API) ----------------
    O["OPEN_POSITIONS"] = "UNKNOWN"
    O["PENDING_ORDERS"] = "UNKNOWN"
    O["ACTIVE_ORDER_ACTION"] = "UNKNOWN"
    O["ORDER_REQUEST_IN_FLIGHT"] = "UNKNOWN"
    O["BROKER_OPERATION_IN_FLIGHT"] = "UNKNOWN"
    O["TRADE_STATE_CONFIRMED"] = "NO"
    O["trade_state_note"] = ("state source not proven; no MetaTrader5 read attempted because the source chain is "
                              "not established (and no trading interface is used by this audit)")
    print("§5 trade state: UNKNOWN -> TRADE_STATE_CONFIRMED = NO", flush=True)

    # ---------------- §六 cycle boundary (bounded observation only) ----------------
    def snap():
        d = {}
        for root in (RUN, os.path.join(V1, "runtime"), os.path.join(V1, "state")):
            if not os.path.isdir(root):
                continue
            for r_, _, fs in os.walk(root):
                for f in fs:
                    p = os.path.join(r_, f)
                    try:
                        st = os.stat(p)
                        d[os.path.relpath(p, AIQ).replace("\\", "/")] = (st.st_size, st.st_mtime)
                    except OSError:
                        continue
        return d
    obs_seconds = 75
    a = snap()
    t0 = time.time()
    time.sleep(obs_seconds)
    b = snap()
    ch = {k for k in b if k in a and (a[k][0] != b[k][0] or a[k][1] != b[k][1])}
    O["CYCLE_OBSERVATION_SECONDS"] = obs_seconds
    O["CYCLE_OBSERVATION_COVERED_A_FULL_BOUNDARY"] = "NO"
    O["files_changed_in_observation"] = sorted(ch)[:10]
    for k in ("CYCLE_START", "ENGINE_START", "DECISION_TIME", "PLAN_TIME", "EXECUTION_TIME", "LEDGER_WRITE_TIME",
                "STATE_WRITE_TIME", "ENGINE_EXIT", "FINAL_WRITE_TIME"):
        O[k] = "UNKNOWN"
    O["WRITE_AFTER_ENGINE_EXIT"] = "UNKNOWN"
    O["STATE_WRITE_IN_FLIGHT"] = "UNKNOWN"
    O["CURRENT_CYCLE"] = "UNKNOWN"
    O["OUTSIDE_TRADING_WINDOW"] = "UNKNOWN"
    O["cycle_note"] = (f"only a bounded {obs_seconds}s observation was performed; per section 6 a short no-change "
                        "sample cannot prove absence, and NEXT_EXPECTED_V1_CYCLE is UNKNOWN so a real boundary "
                        "could not be targeted")
    print(f"§6 cycle: observed {obs_seconds}s changed={len(ch)} full_boundary=NO -> STATE_WRITE_IN_FLIGHT=UNKNOWN", flush=True)

    # ---------------- §七 recompute ----------------
    checks = {"V1_PID_CONFIRMED": False, "PRIMARY_TASK_CONFIRMED": False, "OPEN_POSITIONS_0": False,
               "PENDING_ORDERS_0": False, "ACTIVE_ORDER_ACTION_NO": False, "ORDER_REQUEST_IN_FLIGHT_NO": False,
               "BROKER_OPERATION_IN_FLIGHT_NO": False, "STATE_WRITE_IN_FLIGHT_NO": False,
               "V1_RESTART_RACE_NO": False, "OUTSIDE_TRADING_WINDOW_YES": False, "CURRENT_CYCLE_FINISHED": False}
    O["SAFETY_CHECKS"] = checks
    O["SAFETY_WINDOW"] = "PROVEN" if all(checks.values()) else "NOT_PROVEN"
    O["NEXT_STAGE_AUTHORIZED"] = "YES" if all(checks.values()) else "NO"

    imm = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    v3 = ((imm["M01_event"] or "").startswith("ca44fd2c") and (imm["R1_ledger"] or "").startswith("d9cd6775")
           and (imm["M01_audit"] or "").startswith("a3bee537") and (imm["R2_canonical"] or "").startswith("20913b98"))
    final = {"TASK_STATUS": "V1_GATEWAY_SAFETY_AUDIT_COMPLETE",
              "GATEWAY_V1_AUTOMATION_FOUND": O["GATEWAY_V1_AUTOMATION_FOUND"],
              "GATEWAY_V1_AUTOMATION_SOURCE": O["GATEWAY_V1_AUTOMATION_SOURCE"],
              "GATEWAY_V1_AUTOMATION_ID": O["GATEWAY_V1_AUTOMATION_ID"],
              "GATEWAY_V1_AUTOMATION_ENABLED": O["GATEWAY_V1_AUTOMATION_ENABLED"],
              "V1_M15_SCHEDULE_SOURCE": O["V1_M15_SCHEDULE_SOURCE"], "V1_M15_OFFSET": O["V1_M15_OFFSET"],
              "V1_NEXT_CYCLE": O["V1_NEXT_CYCLE"],
              "AUTO_RESTART_MECHANISM": O["AUTO_RESTART_MECHANISM"], "V1_RESTART_TRIGGER": O["V1_RESTART_TRIGGER"],
              "V1_RESTART_DELAY": O["V1_RESTART_DELAY"], "V1_RESTART_RACE": O["V1_RESTART_RACE"],
              "V1_POSITION_SOURCE": O["V1_POSITION_SOURCE"], "V1_PENDING_ORDER_SOURCE": O["V1_PENDING_ORDER_SOURCE"],
              "V1_EXECUTION_STATE_SOURCE": O["V1_EXECUTION_STATE_SOURCE"],
              "V1_REQUEST_STATE_SOURCE": O["V1_REQUEST_STATE_SOURCE"], "V1_FILL_STATE_SOURCE": O["V1_FILL_STATE_SOURCE"],
              "OPEN_POSITIONS": O["OPEN_POSITIONS"], "PENDING_ORDERS": O["PENDING_ORDERS"],
              "ACTIVE_ORDER_ACTION": O["ACTIVE_ORDER_ACTION"], "ORDER_REQUEST_IN_FLIGHT": O["ORDER_REQUEST_IN_FLIGHT"],
              "BROKER_OPERATION_IN_FLIGHT": O["BROKER_OPERATION_IN_FLIGHT"],
              "CYCLE_START": "UNKNOWN", "ENGINE_START": "UNKNOWN", "DECISION_TIME": "UNKNOWN", "PLAN_TIME": "UNKNOWN",
              "EXECUTION_TIME": "UNKNOWN", "LEDGER_WRITE_TIME": "UNKNOWN", "STATE_WRITE_TIME": "UNKNOWN",
              "ENGINE_EXIT": "UNKNOWN", "FINAL_WRITE_TIME": "UNKNOWN",
              "WRITE_AFTER_ENGINE_EXIT": O["WRITE_AFTER_ENGINE_EXIT"],
              "STATE_WRITE_IN_FLIGHT": O["STATE_WRITE_IN_FLIGHT"], "CURRENT_CYCLE": O["CURRENT_CYCLE"],
              "OUTSIDE_TRADING_WINDOW": O["OUTSIDE_TRADING_WINDOW"],
              "SAFETY_WINDOW": O["SAFETY_WINDOW"], "NEXT_STAGE_AUTHORIZED": O["NEXT_STAGE_AUTHORIZED"],
              "V1_MODIFIED": "NO", "V2_MODIFIED": "NO", "V3_MODIFIED": "NO" if v3 else "UNKNOWN",
              "ORDER_SEND": 0, "COMMIT": "NONE", "ts_utc": NOWU.isoformat(),
              "CURRENT_TIME_UTC": O["CURRENT_TIME_UTC"], "CURRENT_TIME_LOCAL": O["CURRENT_TIME_LOCAL"]}
    O.update(final)
    O["research_immutability"] = imm
    json.dump(O, open(os.path.join(HERE, "V1_GATEWAY_SAFETY_AUDIT_R4.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print("\n=== §9 FINAL ===", flush=True)
    print(json.dumps(final, ensure_ascii=False, indent=1, default=str)[:2600], flush=True)
    print("\nCHECKS:", json.dumps(checks, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
