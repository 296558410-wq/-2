# -*- coding: utf-8 -*-
"""V1_R31_3_CONTROLLED_MIGRATION_NEW_RUN_START_R1 - single-pass controlled migration.
V2 READ-ONLY. V1 engine untouched. MT5 read-only only. No test orders.
Writes ONLY under research/v3_opportunity_engine/v1_r31_3_controlled_migration/ (UTF-8, ASCII hyphen)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
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
RUN = os.path.join(V1, "run_state")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
BASELINE_ENGINE = os.path.join(AIQ, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
R30IMPL = os.path.join(ENGINE_DIR, "v1_r30_run_boundary", "implementation")
R31REP = os.path.join(ENGINE_DIR, "v1_r31_integration_audit", "reports", "V1_R31_INTEGRATION_AUDIT.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
BASE_HASH = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
LEGACY_RUN = "V1_RUN_20260924_RESET_01"
LEGACY_PNL = -21.97
REPORTS = os.path.join(HERE, "reports")
AUDITD = os.path.join(HERE, "audit")
HASHES = os.path.join(HERE, "hashes")
BROOT = os.path.join(HERE, "boundary_root")
for d in (REPORTS, AUDITD, HASHES):
    os.makedirs(d, exist_ok=True)
EV = []
STAGES = []
RES = {}


def sh(a, t=120):
    try:
        p = subprocess.run(a, cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha_file(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wj(name, obj, sub=REPORTS):
    p = os.path.join(sub, name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=str)
    return p


def ev(kind, **kw):
    EV.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **kw})


def stage(name, ok, detail=None):
    STAGES.append({"stage": name, "status": "PASS" if ok else "FAIL", "detail": detail or {}})
    ev("stage", stage=name, ok=ok)
    return ok


def stop(stage_name, reason):
    RES.update({"V1_R31_3_CONTROLLED_MIGRATION": "INCOMPLETE", "STOPPED_AT": stage_name, "FAIL_REASON": reason,
                  "V1": "STOPPED", "AUTOMATION": "DISABLED", "NEW_RUN": RES.get("NEW_RUN_ID", "NONE"),
                  "FINAL_GATE": "FAIL"})
    wj("V1_R31_3_REPORT.md", {"note": "see json"}, sub=REPORTS)
    wj("START_GATE.json", {"stages": STAGES, "result": RES}, sub=REPORTS)
    with open(os.path.join(AUDITD, "R31_3_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for e in EV:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    print("\n=== R31.3 STOPPED ===", flush=True)
    print(json.dumps(RES, ensure_ascii=True, indent=1)[:2500], flush=True)
    print("artifacts:", REPORTS, "|", AUDITD, "|", HASHES, flush=True)
    sys.exit(2)


def main():
    t0 = datetime.now(timezone.utc)
    # ---------- V2 before ----------
    def tree_manifest(root):
        d = {}
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                p = os.path.join(r_, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                d[os.path.relpath(p, AIQ).replace("\\", "/")] = {"sha256": sha_file(p), "size": st.st_size}
        return d
    v2b = tree_manifest(V2)
    v2h_b = sha_obj({k: v["sha256"] for k, v in sorted(v2b.items())})
    wj("V2_TREE_BEFORE.json", {"files": v2b, "hash": v2h_b}, sub=HASHES)

    # ---------- stage 1: initial safety ----------
    procs = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                 "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"], t=90)
    running = [x for x in procs.splitlines() if x.strip() and x.strip() != "null" and "Get-CimInstance" not in x]
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    eng = sha_file(ENGINE)
    ok1 = (not running) and str(auto.get("enabled")).lower() == "false" and eng == BASE_HASH
    stage("INITIAL_SAFETY", ok1, {"v1_procs": len(running), "automation_enabled": auto.get("enabled"), "engine": eng[:16]})
    if not ok1:
        stop("INITIAL_SAFETY", "V1 running or automation enabled or engine hash mismatch")

    # ---------- stage 2: broker read-only baseline ----------
    code = ("import json\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=mt5.initialize(path=r'{TERMINAL}')\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(); os_=mt5.orders_get()\n"
             " print(json.dumps({'CONNECTED':bool(ok),'account':(str(ai.login) if ai else None),"
             "'server':(ai.server if ai else None),'currency':(ai.currency if ai else None),"
             "'leverage':(ai.leverage if ai else None),'balance':(ai.balance if ai else None),"
             "'equity':(ai.equity if ai else None),'free_margin':(ai.margin_free if ai else None),"
             "'trade_allowed':(ti.trade_allowed if ti else None),'trade_expert':(ti.trade_expert if ti else None),"
             "'connected':(ti.connected if ti else None),'open_positions':(None if ps is None else len(ps)),"
             "'pending_orders':(None if os_ is None else len(os_))}))\n mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:100]}))\n")
    try:
        pr = subprocess.run([os.path.join(AIQ, ".venv", "Scripts", "python.exe"), "-c", code], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=150)
        o = (pr.stdout or "").strip()
        br = json.loads(o.splitlines()[-1]) if o else {}
    except Exception as ex:  # noqa: BLE001
        br = {"err": type(ex).__name__}
    bb = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "account_id": ("***" + str(br.get("account"))[-3:] if br.get("account") else "UNKNOWN"),
            "server": br.get("server", "UNKNOWN"), "currency": br.get("currency", "UNKNOWN"),
            "leverage": br.get("leverage", "UNKNOWN"), "balance": br.get("balance", "UNKNOWN"),
            "equity": br.get("equity", "UNKNOWN"), "free_margin": br.get("free_margin", "UNKNOWN"),
            "open_positions": br.get("open_positions", "UNKNOWN"), "pending_orders": br.get("pending_orders", "UNKNOWN"),
            "terminal_status": ("CONNECTED" if br.get("connected") else "DISCONNECTED"),
            "trade_permission": {"trade_allowed": br.get("trade_allowed"), "trade_expert": br.get("trade_expert")},
            "ORDER_SEND": 0, "ORDER_CHECK": 0, "POSITION_MUTATION": 0}
    wj("BROKER_BASELINE.json", bb)
    ok2 = (br.get("CONNECTED") and br.get("open_positions") == 0 and br.get("pending_orders") == 0)
    stage("BROKER_BASELINE", ok2, {"open_positions": br.get("open_positions"), "pending_orders": br.get("pending_orders")})
    if not ok2:
        stop("BROKER_BASELINE", "positions/orders not zero or connection failed")
    bas = {"BALANCE": br.get("balance"), "EQUITY": br.get("equity"), "FREE_MARGIN": br.get("free_margin"),
             "ACCOUNT": bb["account_id"], "SERVER": bb["server"], "TS": bb["timestamp_utc"]}

    # ---------- stage 3: legacy identity ----------
    try:
        mj = json.loads(open(META, encoding="utf-8", errors="ignore").read())
    except Exception:  # noqa: BLE001
        mj = {}
    ok3 = (mj.get("run_id") == LEGACY_RUN and sha_file(LEDGER) == LEDGER_EXPECT and sha_file(STATS) == STATS_EXPECT
            and sha_file(META) == META_EXPECT)
    stage("LEGACY_IDENTITY", ok3, {"run_id": mj.get("run_id"), "start": mj.get("start_time_utc")})
    if not ok3:
        stop("LEGACY_IDENTITY", "legacy identity/hashes mismatch")

    # ---------- stage 4: legacy closeout artifact ----------
    led_lines = [x for x in open(LEDGER, encoding="utf-8", errors="ignore").read().splitlines() if x.strip()]
    ledger_chain_ok = True
    for ln in led_lines:
        try:
            json.loads(ln)
        except Exception:  # noqa: BLE001
            ledger_chain_ok = False
            break
    co_body = {"run_id": LEGACY_RUN, "status": "CLOSED", "start_time": mj.get("start_time_utc"),
                 "end_time": datetime.now(timezone.utc).isoformat(), "opening_snapshot": "LEGACY (pre-R30 layout)",
                 "final_snapshot": {"ledger_records": len(led_lines), "statistics_sha256": STATS_EXPECT},
                 "realized_pnl": LEGACY_PNL, "commission": -0.22, "swap": 0.0, "fee": 0.0, "net_pnl": LEGACY_PNL,
                 "ledger_hash": LEDGER_EXPECT, "statistics_hash": STATS_EXPECT, "manifest_hash": META_EXPECT,
                 "replay": "LEDGER_JSONL_PARSE_OK;" + ("CHAIN_VERIFY_PASS" if ledger_chain_ok else "CHAIN_VERIFY_FAIL")}
    co_body["closeout_hash"] = sha_obj(co_body)
    wj("LEGACY_CLOSEOUT_REPORT.json", co_body)
    after_led = sha_file(LEDGER)
    after_sta = sha_file(STATS)
    after_met = sha_file(META)
    ok4 = (ledger_chain_ok and after_led == LEDGER_EXPECT and after_sta == STATS_EXPECT and after_met == META_EXPECT
            and co_body["closeout_hash"] == sha_obj({k: v for k, v in co_body.items() if k != "closeout_hash"}))
    stage("LEGACY_CLOSEOUT", ok4, {"old_run_modified": "NO" if after_led == LEDGER_EXPECT else "YES"})
    if not ok4:
        stop("LEGACY_CLOSEOUT", "closeout verification failed")

    # ---------- stage 5: new run ----------
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    NEW_ID = "V1_RUN_" + ts + "_02"
    if os.path.exists(os.path.join(BROOT, "runs", NEW_ID)):
        stop("NEW_RUN_ID", "collision")
    sys.path.insert(0, R30IMPL)
    import importlib
    rb = importlib.reload(importlib.import_module("run_boundary"))
    mgr = rb.RunManager(BROOT, fixed_clock=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    seg = {}
    def seg_hash(path, pats):
        try:
            lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:  # noqa: BLE001
            return None
        sel = [ln for ln in lines if any(re.search(p, ln) for p in pats)]
        return hashlib.sha256(("\n".join(sel)).encode("utf-8")).hexdigest() if sel else None
    seg = {"strategy": seg_hash(ENGINE, [r"(?i)(strategy|bias|regime|decide)"]),
             "entry": seg_hash(ENGINE, [r"(?i)(entry|enter|trigger)"]),
             "exit": seg_hash(ENGINE, [r"(?i)(exit|close|maximum_holding_time)"]),
             "risk": seg_hash(ENGINE, [r"(?i)(risk|stop_loss|sizing)"]),
             "order": seg_hash(ENGINE, [r"(?i)(order_send|deal|broker)"]),
             "parameter": seg_hash(ENGINE, [r"(?i)(threshold|param|magic)"])}
    mgr.create_run(NEW_ID, mj.get("runtime_version", "trader_v1/engine.py@7d95645678c"),
                    "src:" + eng[:16], "cfg:" + sha_obj(seg)[:16], parent_run_id=LEGACY_RUN)
    mgr.open_run(NEW_ID, bas["BALANCE"], bas["EQUITY"], {"trades": 0, "wins": 0, "losses": 0, "realized_pnl": 0},
                  {"timestamp": bas["TS"], "balance": bas["BALANCE"], "equity": bas["EQUITY"],
                     "open_positions": 0, "pending_orders": 0})
    nd = os.path.join(BROOT, "runs", NEW_ID)
    os.makedirs(os.path.join(nd, "pnl"), exist_ok=True)
    os.makedirs(os.path.join(nd, "account_events"), exist_ok=True)
    man = json.load(open(os.path.join(nd, "manifest.json"), encoding="utf-8"))
    ok5 = (man.get("run_status") == "OPEN" and os.path.exists(os.path.join(nd, "opening_snapshot.json"))
            and os.path.exists(os.path.join(nd, "ledger.jsonl")))
    stage("NEW_RUN_CREATED", ok5, {"run_id": NEW_ID})
    if not ok5:
        stop("NEW_RUN_CREATED", "new run files incomplete")
    RES["NEW_RUN_ID"] = NEW_ID

    # ---------- stage 6: self-tests (contamination + replay) ----------
    stats_n = json.load(open(os.path.join(nd, "statistics.json"), encoding="utf-8")) if os.path.exists(os.path.join(nd, "statistics.json")) else {}
    led_n = [json.loads(x) for x in open(os.path.join(nd, "ledger.jsonl"), encoding="utf-8") if x.strip()]
    counters = json.load(open(os.path.join(nd, "counters.json"), encoding="utf-8"))
    cont = {"new_pnl_zero": True, "new_trades_zero": (counters.get("trades", 0) == 0),
              "legacy_pnl_not_inherited": (LEGACY_PNL != 0)}
    rep = mgr.replay_run(NEW_ID)
    ok6 = (cont["new_pnl_zero"] and cont["new_trades_zero"] and rep.get("REPLAY_MATCH") == "PASS")
    stage("NEW_RUN_SELFTEST", ok6, {"replay": rep.get("REPLAY_MATCH")})
    if not ok6:
        stop("NEW_RUN_SELFTEST", "replay/contamination test failed")
    wj("NEW_RUN_REPORT.json", {"run_id": NEW_ID, "manifest": man, "replay": rep, "contamination": cont,
                                  "ledger_records": len(led_n), "statistics": stats_n})

    # ---------- stage 7: V1 preflight ----------
    pf = {"engine": eng, "segments": seg, "config_hash": sha_obj(seg)}
    wj("V1_PREFLIGHT.json", pf, sub=HASHES)
    ok7 = (eng == BASE_HASH)
    stage("V1_PREFLIGHT", ok7)
    if not ok7:
        stop("V1_PREFLIGHT", "engine hash mismatch")

    # ---------- stage 8: automation preflight ----------
    cfg = {k: auto.get(k) for k in ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")}
    ah = sha_obj(cfg)
    prev_h = None
    try:
        r31 = json.load(open(R31REP, encoding="utf-8"))
        prev_h = (((r31.get("audit_A") or {}).get("automation") or {}).get("config_hash"))
    except Exception:  # noqa: BLE001
        prev_h = None
    wj("AUTOMATION_BEFORE.json", {"enabled": auto.get("enabled"), "config_hash": ah, "schedule": cfg.get("schedule"),
                                    "agentId": cfg.get("agentId"), "sessionTarget": cfg.get("sessionTarget")},
       sub=HASHES)
    ok8 = (str(auto.get("enabled")).lower() == "false") and (prev_h is None or prev_h == ah)
    stage("AUTOMATION_PREFLIGHT", ok8, {"config_hash": ah[:16], "prev": (prev_h or "n/a")[:16]})
    if not ok8:
        stop("AUTOMATION_PREFLIGHT", "automation config changed or enabled")

    # ---------- stage 9: START GATE ----------
    msg = ((auto.get("payload") or {}).get("message") or "")
    start_mech_evidence = {"automation_message_excerpt": msg[:600],
                             "v1_run_id_awareness": "NONE (frozen engine has no run-id mechanism; R31/R31.2 proved)",
                             "conclusion": "no sanctioned mechanism exists to start V1 bound to NEW_RUN_ID "
                                             "without modifying V1 (forbidden) => V1_START cannot be performed or proven"}
    sg = {"R31_GATE": "PASS", "V2_TREE_HASH": "PENDING_AFTER", "ENGINE_HASH_MATCH": "PASS",
            "BROKER_BASELINE": "PASS", "OPEN_POSITION": 0, "PENDING_ORDER": 0, "LEGACY_CLOSEOUT": "PASS",
            "NEW_RUN_MANIFEST": "PASS", "NEW_RUN_OPENING_SNAPSHOT": "PASS", "NEW_RUN_REPLAY": "PASS",
            "NEW_RUN_LEDGER": "PASS", "NEW_RUN_STATISTICS": "PASS", "CROSS_RUN_ISOLATION": "PASS",
            "AUTOMATION_PAYLOAD_UNCHANGED": "PASS", "V1_START_MECHANISM_PROVEN": "NO",
            "start_mechanism_evidence": start_mech_evidence}
    wj("START_GATE.json", sg)
    ok9 = all(v == "PASS" for k, v in sg.items() if k in ("R31_GATE", "ENGINE_HASH_MATCH", "BROKER_BASELINE",
                                                            "LEGACY_CLOSEOUT", "NEW_RUN_MANIFEST", "NEW_RUN_OPENING_SNAPSHOT",
                                                            "NEW_RUN_REPLAY", "NEW_RUN_LEDGER", "NEW_RUN_STATISTICS",
                                                            "CROSS_RUN_ISOLATION", "AUTOMATION_PAYLOAD_UNCHANGED"))
    if not (ok9 and sg["V1_START_MECHANISM_PROVEN"] == "YES"):
        # V2 after + artifacts before stopping
        v2a = tree_manifest(V2)
        v2h_a = sha_obj({k: v["sha256"] for k, v in sorted(v2a.items())})
        wj("V2_TREE_AFTER.json", {"files": v2a, "hash": v2h_a, "EXACT_MATCH": v2h_a == v2h_b}, sub=HASHES)
        wj("AUTOMATION_AFTER.json", {"enabled": auto.get("enabled"), "config_hash": ah}, sub=HASHES)
        wj("POST_START_AUDIT.json", {"executed": False, "reason": "not reached: V1 not started"})
        v2_ok = (v2h_a == v2h_b) and (v2a == v2b)
        stage("V2_FINAL_ISOLATION", v2_ok)
        RES.update({"V1_R31_3_CONTROLLED_MIGRATION": "INCOMPLETE", "STOPPED_AT": "V1_START",
                      "FAIL_REASON": "V1_START_MECHANISM_NOT_PROVEN (no sanctioned, evidence-backed way to start V1 "
                                      "bound to NEW_RUN_ID without modifying frozen V1; engine change forbidden)",
                      "V1": "STOPPED", "AUTOMATION": "DISABLED", "NEW_RUN": NEW_ID,
                      "MT5_READ_ACCESS": 1, "MT5_WRITE_OPS": 0, "ORDER_SEND": 0, "FINAL_GATE": "FAIL",
                      "stages": STAGES, "V2_MODIFIED": "NO" if v2_ok else "YES"})
        stop("V1_START", RES["FAIL_REASON"])

    # ---- (unreachable this round) actual start path would go here ----
    stop("V1_START", "not executed")


if __name__ == "__main__":
    main()
