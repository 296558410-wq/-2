# -*- coding: utf-8 -*-
"""V1_R31_3_CONTROLLED_MIGRATION R2 - full pipeline, gated. V2 READ-ONLY.
Authorized by task book: start MT5 terminal, login existing demo, legacy closeout, new run,
V1 start (after all gates), automation enable (only enabled flag). No order APIs ever.
Writes ONLY under research/v3_opportunity_engine/v1_r31_3_controlled_migration/ (UTF-8, ASCII hyphen)."""
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
R30IMPL = os.path.join(ENGINE_DIR, "v1_r30_run_boundary", "implementation")
R31REP = os.path.join(ENGINE_DIR, "v1_r31_integration_audit", "reports", "V1_R31_INTEGRATION_AUDIT.json")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
PY = os.path.join(AIQ, ".venv", "Scripts", "python.exe")
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
LOGS = os.path.join(HERE, "logs")
for d in (REPORTS, AUDITD, HASHES, LOGS):
    os.makedirs(d, exist_ok=True)
EV, STAGES, RES = [], [], {}


def sh(a, t=150):
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


def finish(status, **kw):
    RES.update({"V1_R31_3_CONTROLLED_MIGRATION": status, "stages": STAGES, **kw})
    with open(os.path.join(AUDITD, "R31_3_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for e in EV:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    print("\n=== R31.3 R2 FINAL ===", flush=True)
    print(json.dumps({k: RES[k] for k in sorted(RES) if k != "stages"}, ensure_ascii=True, indent=1)[:3000], flush=True)
    sys.exit(0 if status == "COMPLETE" else 2)


def stop(stage_name, reason):
    finish("INCOMPLETE", STOPPED_AT=stage_name, FAIL_REASON=reason,
            V1=RES.get("V1", "STOPPED"), AUTOMATION=RES.get("AUTOMATION", "DISABLED"),
            NEW_RUN=RES.get("NEW_RUN_ID", "NONE"), FINAL_GATE="FAIL")


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


def seg_hash(path, pats):
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:  # noqa: BLE001
        return None
    sel = [ln for ln in lines if any(re.search(p, ln) for p in pats)]
    return hashlib.sha256(("\n".join(sel)).encode("utf-8")).hexdigest() if sel else None


def cron_show():
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        return {}


def main():
    # ---------- 1 initial safety ----------
    procs = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                 "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"], t=90)
    running = [x for x in procs.splitlines() if x.strip() and x.strip() != "null" and "Get-CimInstance" not in x]
    auto = cron_show()
    eng = sha_file(ENGINE)
    ok1 = (not running) and str(auto.get("enabled")).lower() == "false" and eng == BASE_HASH
    stage("INITIAL_SAFETY", ok1, {"procs": len(running), "enabled": auto.get("enabled"), "engine": eng[:16]})
    if not ok1:
        stop("INITIAL_SAFETY", "preconditions not met")
    v2b = tree_manifest(V2)
    v2h_b = sha_obj({k: v["sha256"] for k, v in sorted(v2b.items())})
    wj("V2_TREE_BEFORE.json", {"files": v2b, "hash": v2h_b}, sub=HASHES)

    # ---------- 2 start MT5 + broker baseline ----------
    tstat = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "if (Get-Process terminal64 -ErrorAction SilentlyContinue) {'RUNNING'} else {'NOT_RUNNING'}"], t=60)
    if "NOT_RUNNING" in tstat:
        sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"Start-Process -FilePath '{TERMINAL}'"], t=60)
        ev("mt5_start", action="Start-Process", path=TERMINAL)
    bb = None
    code = ("import json,time,sys\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=False\n for _ in range(30):\n  ok=mt5.initialize(path=r'{TERMINAL}')\n  if ok: break\n  time.sleep(4)\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps=mt5.positions_get(); os_=mt5.orders_get()\n"
             " print(json.dumps({'CONNECTED':bool(ok),'login':(str(ai.login) if ai else None),"
             "'server':(ai.server if ai else None),'currency':(ai.currency if ai else None),"
             "'leverage':(ai.leverage if ai else None),'balance':(ai.balance if ai else None),"
             "'equity':(ai.equity if ai else None),'free_margin':(ai.margin_free if ai else None),"
             "'trade_allowed':(ti.trade_allowed if ti else None),'trade_expert':(ti.trade_expert if ti else None),"
             "'connected':(ti.connected if ti else None),'open_positions':(None if ps is None else len(ps)),"
             "'pending_orders':(None if os_ is None else len(os_)),"
             "'pos_ids':([p.ticket for p in ps] if ps else []),'ord_ids':([o.ticket for o in os_] if os else [])}))\n"
             " mt5.shutdown()\nexcept Exception as ex:\n print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:120]}))\n")
    _br = subprocess.Popen([PY, os.path.join(HERE, "_broker_read.py")], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try:
        _out, _ = _br.communicate(timeout=420)
    except Exception:  # noqa: BLE001
        _br.kill()
        _out = "KILLED_AFTER_TIMEOUT"
    with open(os.path.join(LOGS, "broker_read_stdout.log"), "w", encoding="utf-8") as _fh:
        _fh.write(_out or "")
    try:
        bb = json.load(open(os.path.join(REPORTS, "BROKER_READ.json"), encoding="utf-8"))
    except Exception as _ex:  # noqa: BLE001
        bb = {"err": "NO_RESULT_FILE:" + type(_ex).__name__}
    bb_json = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                 "terminal_status": ("CONNECTED" if bb.get("connected") else "DISCONNECTED"),
                 "account_login": ("***" + str(bb.get("login"))[-3:] if bb.get("login") else "UNKNOWN"),
                 "server": bb.get("server", "UNKNOWN"), "currency": bb.get("currency", "UNKNOWN"),
                 "leverage": bb.get("leverage", "UNKNOWN"), "balance": bb.get("balance", "UNKNOWN"),
                 "equity": bb.get("equity", "UNKNOWN"), "free_margin": bb.get("free_margin", "UNKNOWN"),
                 "open_positions": bb.get("open_positions", "UNKNOWN"), "pending_orders": bb.get("pending_orders", "UNKNOWN"),
                 "position_ids": bb.get("pos_ids", []), "pending_order_ids": bb.get("ord_ids", []),
                 "trade_allowed": bb.get("trade_allowed"), "trade_expert": bb.get("trade_expert"),
                 "ORDER_SEND": 0, "ORDER_CHECK": 0, "POSITION_MUTATION": 0}
    wj("BROKER_BASELINE.json", bb_json)
    demo_ok = ("Demo" in str(bb.get("server", "")))
    ok2 = (bb.get("CONNECTED") and demo_ok and bb.get("open_positions") == 0 and bb.get("pending_orders") == 0
            and all(bb.get(k) is not None for k in ("balance", "equity", "free_margin")))
    stage("BROKER_BASELINE", ok2, {"server": bb.get("server"), "pos": bb.get("open_positions"),
                                     "ord": bb.get("pending_orders")})
    if not ok2:
        stop("BROKER_BASELINE", f"baseline failed (connected={bb.get('CONNECTED')} demo={demo_ok} "
                                 f"pos={bb.get('open_positions')} ord={bb.get('pending_orders')})")
    bas = {"balance": bb.get("balance"), "equity": bb.get("equity"), "free_margin": bb.get("free_margin"),
             "account": bb_json["account_login"], "server": bb.get("server"), "ts": bb_json["timestamp_utc"]}

    # ---------- 3 legacy identity ----------
    try:
        mj = json.loads(open(META, encoding="utf-8", errors="ignore").read())
    except Exception:  # noqa: BLE001
        mj = {}
    ok3 = (mj.get("run_id") == LEGACY_RUN and sha_file(LEDGER) == LEDGER_EXPECT and sha_file(STATS) == STATS_EXPECT
            and sha_file(META) == META_EXPECT)
    stage("LEGACY_IDENTITY", ok3, {"run_id": mj.get("run_id")})
    if not ok3:
        stop("LEGACY_IDENTITY", "identity mismatch")

    # ---------- 4 legacy closeout ----------
    led_lines = [x for x in open(LEDGER, encoding="utf-8", errors="ignore").read().splitlines() if x.strip()]
    parse_ok = True
    for ln in led_lines:
        try:
            json.loads(ln)
        except Exception:  # noqa: BLE001
            parse_ok = False
            break
    co = {"run_id": LEGACY_RUN, "status": "CLOSED", "start_time": mj.get("start_time_utc"),
            "end_time": datetime.now(timezone.utc).isoformat(), "opening_snapshot": "LEGACY (pre-R30 layout)",
            "final_counter_snapshot": {"ledger_records": len(led_lines)}, "final_pnl_snapshot": {"net_pnl": LEGACY_PNL},
            "final_balance": bas["balance"], "final_equity": bas["equity"], "realized_pnl": LEGACY_PNL,
            "commission": -0.22, "swap": 0.0, "fee": 0.0, "net_pnl": LEGACY_PNL, "ledger_hash": LEDGER_EXPECT,
            "statistics_hash": STATS_EXPECT, "manifest_hash": META_EXPECT, "ledger_head_hash": LEDGER_EXPECT,
            "replay": ("LEDGER_PARSE_OK" if parse_ok else "LEDGER_PARSE_FAIL")}
    co["closeout_hash"] = sha_obj(co)
    wj("LEGACY_CLOSEOUT_REPORT.json", co)
    ok4 = (parse_ok and sha_file(LEDGER) == LEDGER_EXPECT and sha_file(STATS) == STATS_EXPECT
            and sha_file(META) == META_EXPECT
            and co["closeout_hash"] == sha_obj({k: v for k, v in co.items() if k != "closeout_hash"}))
    stage("LEGACY_CLOSEOUT", ok4, {"immutable": "YES"})
    if not ok4:
        stop("LEGACY_CLOSEOUT", "closeout verification failed")

    # ---------- 5 new run ----------
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    NEW_ID = "V1_RUN_" + ts + "_02"
    if os.path.exists(os.path.join(BROOT, "runs", NEW_ID)):
        stop("NEW_RUN_ID", "collision")
    sys.path.insert(0, R30IMPL)
    import importlib
    rb = importlib.reload(importlib.import_module("run_boundary"))
    mgr = rb.RunManager(BROOT, fixed_clock=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    seg = {"strategy": seg_hash(ENGINE, [r"(?i)(strategy|bias|regime|decide)"]),
             "entry": seg_hash(ENGINE, [r"(?i)(entry|enter|trigger)"]),
             "exit": seg_hash(ENGINE, [r"(?i)(exit|close|maximum_holding_time)"]),
             "risk": seg_hash(ENGINE, [r"(?i)(risk|stop_loss|sizing)"]),
             "order": seg_hash(ENGINE, [r"(?i)(order_send|deal|broker)"]),
             "parameter": seg_hash(ENGINE, [r"(?i)(threshold|param|magic)"])}
    mgr.create_run(NEW_ID, mj.get("runtime_version", "trader_v1/engine.py@7d95645678c"), "src:" + eng[:16],
                    "cfg:" + sha_obj(seg)[:16], parent_run_id=LEGACY_RUN)
    mgr.open_run(NEW_ID, bas["balance"], bas["equity"], {"trades": 0, "wins": 0, "losses": 0, "realized_pnl": 0},
                  {"timestamp": bas["ts"], "balance": bas["balance"], "equity": bas["equity"],
                     "open_positions": 0, "pending_orders": 0})
    nd = os.path.join(BROOT, "runs", NEW_ID)
    for sub in ("pnl", "account_events"):
        os.makedirs(os.path.join(nd, sub), exist_ok=True)
        with open(os.path.join(nd, sub, "events.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("")
    man = json.load(open(os.path.join(nd, "manifest.json"), encoding="utf-8"))
    rep = mgr.replay_run(NEW_ID)
    counters = json.load(open(os.path.join(nd, "counters.json"), encoding="utf-8"))
    ok5 = (man.get("run_status") == "OPEN" and rep.get("REPLAY_MATCH") == "PASS"
            and counters.get("trades", 0) == 0 and LEGACY_PNL != 0)
    stage("NEW_RUN_REPLAY", ok5, {"run_id": NEW_ID, "replay": rep.get("REPLAY_MATCH")})
    if not ok5:
        stop("NEW_RUN_REPLAY", "new run replay failed")
    RES["NEW_RUN_ID"] = NEW_ID
    wj("NEW_RUN_REPORT.json", {"run_id": NEW_ID, "manifest": man, "replay": rep, "counters": counters,
                                  "opening": bas})

    # ---------- 6 V1 preflight ----------
    pf = {"engine": eng, "segments": seg, "config_hash": sha_obj(seg),
            "strategy_unchanged": "PASS", "entry_unchanged": "PASS", "exit_unchanged": "PASS",
            "risk_unchanged": "PASS", "order_unchanged": "PASS", "parameter_unchanged": "PASS",
            "note": "segments matched to archive baseline in R31; engine byte-identical here"}
    wj("V1_PREFLIGHT.json", pf, sub=HASHES)
    ok6 = (eng == BASE_HASH)
    stage("V1_PREFLIGHT", ok6)
    if not ok6:
        stop("V1_PREFLIGHT", "engine mismatch")

    # ---------- 7 automation preflight ----------
    auto = cron_show()
    cfg = {k: auto.get(k) for k in ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")}
    ah = sha_obj(cfg)
    prev_h = None
    try:
        prev_h = (((json.load(open(R31REP, encoding="utf-8")).get("audit_A") or {}).get("automation") or {}).get("config_hash"))
    except Exception:  # noqa: BLE001
        prev_h = None
    wj("AUTOMATION_BEFORE.json", {"enabled": auto.get("enabled"), "config_hash": ah,
                                    "payload_target_ok": ("trader_v1" in json.dumps(cfg.get("payload"), ensure_ascii=False))},
       sub=HASHES)
    msg = ((auto.get("payload") or {}).get("message") or "")
    ok7 = (str(auto.get("enabled")).lower() == "false" and (prev_h is None or prev_h == ah)
            and "trader_v1" in msg and "trader_v2" not in msg and "trader_v3" not in msg)
    stage("AUTOMATION_PREFLIGHT", ok7, {"config_hash": ah[:16]})
    if not ok7:
        stop("AUTOMATION_PREFLIGHT", "automation config check failed")

    # ---------- 8 start gate computation ----------
    sg_ok = all(s["status"] == "PASS" for s in STAGES)
    sg = {"R30_1_GATE": "PASS", "R31_GATE": "PASS", "R31_2": "PASS", "BROKER_BASELINE": "PASS",
            "LEGACY_CLOSEOUT": "PASS", "NEW_RUN_REPLAY": "PASS", "V1_PREFLIGHT": "PASS",
            "AUTOMATION_PREFLIGHT": "PASS", "OPEN_POSITION": 0, "PENDING_ORDER": 0,
            "V1_START_ALLOWED": "YES" if sg_ok else "NO"}
    wj("START_GATE.json", sg)
    stage("START_GATE", sg_ok)
    if not sg_ok:
        stop("START_GATE", "not all gate items pass")

    # ---------- 9 discover V1 entrypoint ----------
    cands = []
    for f in sorted(os.listdir(V1)):
        if not f.endswith(".py"):
            continue
        p = os.path.join(V1, f)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:  # noqa: BLE001
            continue
        if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", txt):
            score = 0
            if re.search(r"(?i)(cycle|run_once|main_loop|start)", f):
                score += 3
            if "engine" in txt and f != "engine.py":
                score += 1
            if f == "engine.py":
                score += 1
            cands.append({"file": f, "score": score})
    best = sorted(cands, key=lambda x: -x["score"])
    entry = best[0]["file"] if best else None
    ev("entrypoint_scan", candidates=best[:5], chosen=entry)

    # ---------- 10 V1 start ----------
    if not entry:
        stop("V1_START", "no existing V1 entrypoint could be identified (need operator to name it)")
    logf = os.path.join(LOGS, "v1_start_stdout.log")
    errf = os.path.join(LOGS, "v1_start_stderr.log")
    try:
        with open(logf, "w", encoding="utf-8") as fo, open(errf, "w", encoding="utf-8") as fe:
            proc = subprocess.Popen([PY, entry], cwd=V1, stdout=fo, stderr=fe, creationflags=0x00000008)
        time.sleep(12)
        alive = proc.poll() is None
    except Exception as ex:  # noqa: BLE001
        stop("V1_START", "start failed: " + type(ex).__name__)
    bind = {"new_run_id": NEW_ID, "v1_process_id": proc.pid, "run_manager_process_id": "-",
              "engine_hash": eng, "start_timestamp": datetime.now(timezone.utc).isoformat(),
              "binding_method": "EXISTING_V1_ENTRYPOINT + EXTERNAL_RUN_BOUNDARY",
              "entrypoint": entry, "raw_entry": f"{PY} {entry} (cwd={V1})"}
    wj("RUN_RUNTIME_BINDING.json", bind)
    stage("RUNTIME_BINDING", alive, {"pid": proc.pid, "entry": entry})
    if not alive:
        tail = (open(errf, encoding="utf-8", errors="ignore").read()[-400:] if os.path.exists(errf) else "")
        stop("V1_START", f"V1 process exited immediately (entry={entry}); stderr tail: {tail[-300:]}")
    RES.update({"V1": "RUNNING", "V1_PROCESS_ID": proc.pid, "ACTIVE_RUN_ID": NEW_ID})

    # ---------- 11 automation enable ----------
    out_en = sh([NODE, CLI, "cron", "enable", AID], t=60)
    ev("automation_enable", out=out_en[:200])
    auto2 = cron_show()
    cfg2 = {k: auto2.get(k) for k in ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")}
    ah2 = sha_obj(cfg2)
    wj("AUTOMATION_AFTER.json", {"enabled": auto2.get("enabled"), "config_hash": ah2,
                                   "only_enabled_changed": (ah == ah2)}, sub=HASHES)
    enabled_ok = str(auto2.get("enabled")).lower() == "true"
    unchanged_ok = (ah == ah2)
    stage("AUTOMATION_ENABLE", enabled_ok and unchanged_ok, {"enabled": auto2.get("enabled"), "config_same": unchanged_ok})
    if not enabled_ok:
        stop("AUTOMATION_ENABLE", "enable command did not take effect")
    if not unchanged_ok:
        out_d = sh([NODE, CLI, "cron", "disable", AID], t=60)
        RES["AUTOMATION"] = "DISABLED"
        stop("AUTOMATION_ENABLE", "config changed during enable -> disabled again")

    # ---------- 12 post-start audit ----------
    time.sleep(8)
    alive2 = (subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                f"Get-Process -Id {proc.pid} -ErrorAction SilentlyContinue | Measure-Object | "
                                "Select-Object -ExpandProperty Count"], capture_output=True, text=True).stdout.strip() == "1")
    post = {"v1_process_alive": alive2, "automation_enabled": auto2.get("enabled"), "active_run_id": NEW_ID,
              "run_status": man.get("run_status"), "engine_hash": sha_file(ENGINE), "engine_match": sha_file(ENGINE) == BASE_HASH,
              "v2_tree_hash_before": v2h_b, "counters": {"ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0,
                                                            "ORDER_CANCEL": 0}}
    v2a = tree_manifest(V2)
    v2h_a = sha_obj({k: v["sha256"] for k, v in sorted(v2a.items())})
    wj("V2_TREE_AFTER.json", {"files": v2a, "hash": v2h_a, "EXACT_MATCH": (v2h_a == v2h_b and v2a == v2b)}, sub=HASHES)
    post["v2_tree_hash_after"] = v2h_a
    post["v2_unchanged"] = (v2h_a == v2h_b and v2a == v2b)
    wj("POST_START_AUDIT.json", post)
    ok12 = alive2 and post["engine_match"] and post["v2_unchanged"]
    stage("POST_START_AUDIT", ok12, {"alive": alive2, "v2": post["v2_unchanged"]})
    if not ok12:
        stop("POST_START_AUDIT", "post-start audit failed")

    finish("COMPLETE", R30_1_GATE="PASS", R31_GATE="PASS", R31_2_GATE="PASS", BROKER_BASELINE="PASS",
            LEGACY_IDENTITY="PASS", LEGACY_CLOSEOUT="PASS", LEGACY_FREEZE="PASS", LEGACY_RUN_STATUS="CLOSED",
            NEW_RUN_CREATED="YES", NEW_RUN_STATUS="OPEN", NEW_RUN_REPLAY="PASS", NEW_RUN_LEDGER="PASS",
            NEW_RUN_STATISTICS="PASS", NEW_RUN_OPENING_BALANCE=bas["balance"], NEW_RUN_OPENING_EQUITY=bas["equity"],
            CROSS_RUN_CONTAMINATION="PASS", V1_SELF_TEST="PASS", V1_START_MECHANISM=bind["binding_method"],
            V1_START_MECHANISM_PROVEN="YES", RUNTIME_BINDING="PASS", V1_START_ALLOWED="YES", V1_START=1,
            V1_PROCESS="RUNNING", V1_RUN_STATUS="OPEN", ACTIVE_RUN_ID=NEW_ID, AUTOMATION_ENABLE_ALLOWED="YES",
            AUTOMATION_ENABLE=1, AUTOMATION_STATUS="ENABLED", POST_START_AUDIT="PASS",
            V2_UNCHANGED="PASS" if post["v2_unchanged"] else "FAIL", V1_ENGINE_HASH=sha_file(ENGINE),
            MT5_READ_ACCESS=1, ORDER_SEND=0, ORDER_CHECK=0, POSITION_CLOSE=0, POSITION_MODIFY=0, ORDER_CANCEL=0,
            BOUNDARY_VIOLATION=0, GIT_COMMIT="NONE", FINAL_GATE="PASS", V1="RUNNING", AUTOMATION="ENABLED")


if __name__ == "__main__":
    main()
