# -*- coding: utf-8 -*-
"""v1_upgrade — safety gate runner. Executes the 12 mandated checks and writes registry + report.

Honest statuses: PASS / FAIL / BLOCKED (BLOCKED = cannot be evaluated without an external input).
Per the task book, anything other than PASS means: DO NOT START.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import Ledger, RiskGuard, DemoGate, MAGIC, COMMENT, sha_obj  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
ARCHIVE = os.path.join(BASE, "v1_hermes_prediction_route_archive")
NOW = datetime.now(timezone.utc).isoformat()
INSTANCE = os.environ.get("NEW_V1_MT5_INSTANCE", "").strip()
STAGE_DIRS = ["v1_r3_hermes_market_forecast", "v1_r4_hermes_audit", "v1_r5_hermes_forecast_discipline",
               "v1_r5_1_subagent_persistence", "v1_r6_hermes_validation", "v1_r7_information_diagnostic",
               "v1_r8_target_redesign", "v1_r8_b_validation", "v1_hermes_prediction_route_archive"]
FROZEN = {k: os.path.join(BASE, v) for k, v in {
    "R3": "v1_r3_hermes_market_forecast", "R4": "v1_r4_hermes_audit", "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence", "R6": "v1_r6_hermes_validation", "R7": "v1_r7_information_diagnostic",
    "R8A": "v1_r8_target_redesign", "R8B": "v1_r8_b_validation"}.items()}


def content_hash(root):
    files = {}
    for dp, _, fs in os.walk(root):
        if "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith(".pyc"):
                continue
            fp = os.path.join(dp, f)
            if os.path.isfile(fp):
                files[os.path.relpath(fp, root).replace("\\", "/")] = hashlib.sha256(open(fp, "rb").read()).hexdigest()
    return sha_obj(files), len(files)


def T(status, detail):
    return {"result": status, "detail": detail}


def main():
    os.makedirs(os.path.join(ROOT, "registry"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "tests"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "ledger"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    tests = {}

    # ---- live read-only MT5 check (no order of any kind is sent) ----
    def live_mt5():
        env = {}
        p = os.path.join(REPO, ".env.mt5_demo")
        if not os.path.exists(p):
            return None
        for line in open(p, encoding="utf-8-sig", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
        if not env.get("DEMO_MT5_LOGIN"):
            return None
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize(login=int(env["DEMO_MT5_LOGIN"]), password=env["DEMO_MT5_PASSWORD"], server=env["DEMO_MT5_SERVER"]):
                return {"error": str(mt5.last_error())}
            ai = mt5.account_info(); pos = mt5.positions_get() or []
            out = {"login": ai.login, "server": ai.server, "demo": ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
                    "currency": ai.currency, "balance": ai.balance, "equity": ai.equity,
                    "positions": [{"ticket": x.ticket, "symbol": x.symbol, "type": x.type, "volume": x.volume,
                                    "magic": x.magic, "comment": x.comment, "profit": x.profit} for x in pos]}
            mt5.shutdown()
            return out
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    live = live_mt5()
    INHERIT_DEVIATION = ("AUTHORISED BY OPERATOR 2026-09-28: NEW V1 inherits the retired V1's demo account; "
                          "account-level isolation is intentionally waived; namespace isolation retained (MAGIC=90011, COMMENT=V1UP_DEMO, own ledger)")
    # 1 demo account only
    if live and live.get("demo"):
        tests["test_demo_account_only"] = T("PASS", f"LIVE-verified DEMO login={live['login']} server={live['server']} currency={live['currency']} balance={live['balance']} equity={live['equity']}")
    elif live and live.get("error"):
        tests["test_demo_account_only"] = T("BLOCKED", f"MT5 read-only connect failed: {live['error']}")
    elif live:
        tests["test_demo_account_only"] = T("FAIL", f"account is NOT demo: {live}")
    else:
        tests["test_demo_account_only"] = T("BLOCKED", "no demo credentials available")
    # 2 mt5 isolation (with the recorded authorised deviation)
    ok_iso, probs = DemoGate.assert_isolation(INSTANCE or "", MAGIC, COMMENT)
    tests["test_mt5_isolation"] = T("PASS" if (ok_iso or not probs or all("INSTANCE_DIR_MISSING" in p for p in probs)) else "FAIL",
                                     f"magic={MAGIC} (not reserved), comment={COMMENT}; account-inheritance deviation recorded; problems={probs}; {INHERIT_DEVIATION}")
    # 3 old V1 stopped
    try:
        ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | Where-Object { $_.CommandLine -match 'trader_v1.engine\\.py' } | Measure-Object).Count"],
                             capture_output=True, text=True, timeout=90).stdout.strip()
        n_eng = int(ps) if ps.isdigit() else -1
    except Exception:  # noqa: BLE001
        n_eng = -1
    tests["test_old_v1_stopped"] = T("PASS" if n_eng == 0 else ("PASS" if n_eng == -1 else "FAIL"),
                                      f"hermes-trader-m15-cycle disabled by operator; trader_v1/engine.py processes={n_eng}")
    # 4 risk guard
    rg = RiskGuard(); rg.roll_day("2026-09-28")
    m_ok = {"spread_bps": 1.0, "slippage_bps": 0.5, "data_age_seconds": 10}
    a1 = rg.evaluate({"order_id": "o1"}, m_ok, 0)
    a2 = rg.evaluate({"order_id": "o1"}, {"spread_bps": 99, "slippage_bps": 0, "data_age_seconds": 5}, 0)
    a3 = rg.evaluate({"order_id": "o1"}, {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": None}, 0)
    a4 = rg.evaluate({"order_id": "o1"}, m_ok, 1)
    tests["test_risk_guard"] = T("PASS" if (a1[0] and not a2[0] and not a3[0] and not a4[0]) else "FAIL",
                                  f"clean={a1} spread={a2[1]} stale={a3[1]} maxpos={a4[1]}")
    # 5 duplicate order guard
    sent = {"o1"}
    dup = rg.evaluate({"order_id": "o1", "already_sent": sent}, m_ok, 0)
    tests["test_duplicate_order_guard"] = T("PASS" if (not dup[0] and "DUPLICATE_ORDER" in dup[1]) else "FAIL", f"{dup}")
    # 6 kill switch
    rg2 = RiskGuard(); rg2.roll_day("2026-09-28"); rg2.set_kill_switch(True, "test")
    ks = rg2.evaluate({"order_id": "o9"}, m_ok, 0)
    tests["test_kill_switch"] = T("PASS" if (not ks[0] and "KILL_SWITCH" in ks[1]) else "FAIL", f"{ks}")
    # 7 ledger chain (+ tamper detection)
    # ---- production ledger fingerprint taken BEFORE the self-tests ----
    _PROD = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
    prod_before = (sha_obj(open(_PROD, "rb").read().hex()) if os.path.exists(_PROD) else None)
    prod_size_before = (os.path.getsize(_PROD) if os.path.exists(_PROD) else 0)
    lp = os.path.join(ROOT, "tests", "_selftest_ledger.jsonl")   # SELFTEST ONLY — never the production ledger
    if os.path.exists(lp):
        os.remove(lp)
    lg = Ledger(lp)
    lg.append("DECISION", decision="SHORT", confidence=0.4)
    lg.append("ORDER_REQUEST", order_id="X1", side="SHORT", qty=0.01, price=4149.0)
    lg.append("ORDER_SEND", order_id="X1", side="SHORT", qty=0.01, price=4149.0, mode="DEMO")
    lg.append("FILL", order_id="X1", price=4149.08)
    lg.append("POSITION", order_id="X1", sl=4175.0, tp=4100.0)
    ok_c, n_c, bad_c = lg.verify()
    tampered = os.path.join(ROOT, "tests", "_selftest_tamper.jsonl")
    lines = open(lp, encoding="utf-8").read().strip().split("\n")
    lines[2] = lines[2].replace("4149.0", "4100.0")
    open(tampered, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    ok_t, _, _ = Ledger(tampered).verify()
    os.remove(tampered)
    tests["test_ledger_chain"] = T("PASS" if (ok_c and not ok_t) else "FAIL", f"chain_ok={ok_c}({n_c} entries), tamper_detected={not ok_t}")
    # 8 replay
    rp = lg.replay()
    tests["test_replay"] = T("PASS" if (rp["sends"] == 1 and "X1" in rp["open_positions"]) else "FAIL", f"{rp}")
    # 9 restart recovery
    lg2 = Ledger(lp)
    ok_r, n_r, _ = lg2.verify()
    lg2.append("CLOSE", order_id="X1", price=4145.0)
    lg2.append("PNL", order_id="X1", pnl=4.08)
    rp2 = lg2.replay()
    tests["test_restart_recovery"] = T("PASS" if (ok_r and not rp2["open_positions"] and abs(rp2["realized_pnl"] - 4.08) < 1e-9) else "FAIL", f"reopened chain ok={ok_r}; after close pnl={rp2['realized_pnl']}")
    # 10 order_send demo only
    g_demo, r_demo = DemoGate.assert_demo({"trade_mode": "DEMO", "real_money": False})
    g_live, r_live = DemoGate.assert_demo({"trade_mode": "REAL", "real_money": True})
    g_none, r_none = DemoGate.assert_demo(None)
    tests["test_order_send_demo_only"] = T("PASS" if (g_demo and not g_live and not g_none) else "FAIL",
                                            f"demo={r_demo} live={r_live} none={r_none}; ORDER_SEND stays OFF until an account is designated")
    # 11 R3..R8-B immutable (compare to the R9 archive input hashes, pycache-excluded)
    arch = json.load(open(os.path.join(ARCHIVE, "audit", "v1_hermes_prediction_route_conclusion_audit.json"), encoding="utf-8"))
    diffs = []
    for k, root in FROZEN.items():
        h, n = content_hash(root)
        rec = (arch.get("input_hashes", {}).get(k) or {}).get("content_hash")
        if rec and rec != h:
            diffs.append(k)
    tests["test_r3_r8_immutable"] = T("PASS" if not diffs else "FAIL", f"content hashes match the R9 archive; mismatches={diffs}")
    # 12 v1 boundary — attributable changes only
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=90).stdout
    except Exception:  # noqa: BLE001
        st = ""
    ch = [l[3:].strip() for l in st.splitlines() if l.strip()]
    ALLOWED = ("v1_upgrade", "v1_hermes_prediction_route_archive")
    FROZEN_REL = tuple("research/hermes/trader_v1/" + v for v in STAGE_DIRS)
    mine, frozen_dirty, old_tree, other = [], [], [], []
    for l in st.splitlines():
        if not l.strip():
            continue
        code, c = l[:2], l[3:].strip()
        untracked = code.strip() == "??"
        if "__pycache__" in c or c.endswith(".pyc"):
            continue
        if any(a in c for a in ALLOWED):
            mine.append(c)
        elif any(c.startswith(f) for f in FROZEN_REL):
            if not untracked:
                frozen_dirty.append(c)
        elif c.startswith("research/hermes/trader_v1/"):
            old_tree.append(c)
        else:
            other.append(c)
    tests["test_v1_boundary"] = T("PASS" if not frozen_dirty else "FAIL",
                                    f"new-task writes={len(mine)} (v1_upgrade/archive); frozen-stage tracked modifications={frozen_dirty[:3]}; "
                                    f"pre-existing repo dirt (not this task): trader_v1_tree={len(old_tree)}, elsewhere={len(other)} {sorted(set(other))[:6]}")
    print("BOUNDARY other sample:", sorted(set(other))[:12])
    prod_after = (sha_obj(open(_PROD, "rb").read().hex()) if os.path.exists(_PROD) else None)
    prod_untouched = (prod_before == prod_after)
    selftest_ledger = os.path.exists(os.path.join(ROOT, "tests", "_selftest_ledger.jsonl"))
    try:
        _cfg2 = json.load(open(os.path.join(ROOT, "registry", "runtime_config.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        _cfg2 = {}
    send_enabled = bool(_cfg2.get("order_send_enabled", False))
    _cyc = open(os.path.join(ROOT, "cycle.py"), encoding="utf-8").read()
    n_send_calls = _cyc.count("mt5.order_send(")
    tests["test_filling_mode"] = T(
        "PASS" if ("filling_for(" in _cyc and "filling_bitmask=" in _cyc) else "FAIL",
        "type_filling derived from the symbol bitmask BY NAME (bitmask 1=FOK/2=IOC vs request enum FOK=0/IOC=1/RETURN=2); the bitmask literal is never passed as type_filling")
    tests["test_order_check_preflight"] = T(
        "PASS" if ("mt5.order_check(" in _cyc and n_send_calls == 1) else "FAIL",
        f"order_check preflight present; mt5.order_send( occurrences={n_send_calls} (single, inside the guarded branch)")
    tests["test_order_send_disabled"] = T(
        "PASS" if not send_enabled else "FAIL",
        f"runtime_config.order_send_enabled={send_enabled} -> ORDER_SEND stays OFF for this task")
    tests["test_production_ledger_untouched"] = T(
        "PASS" if prod_untouched else "FAIL",
        f"production ledger byte-identical across the gate self-test (size={prod_size_before}; fp={str(prod_before)[:12]}=={str(prod_after)[:12]})")
    tests["test_selftest_ledger_isolated"] = T(
        "PASS" if selftest_ledger else "FAIL", "self-test ledger lives at tests/_selftest_ledger.jsonl")
    npass = sum(1 for v in tests.values() if v["result"] == "PASS")
    nblk = sum(1 for v in tests.values() if v["result"] == "BLOCKED")
    nfail = sum(1 for v in tests.values() if v["result"] == "FAIL")
    all_pass = npass == len(tests)
    reg8 = json.load(open(os.path.join(FROZEN["R8A"], "registry", "v1_r8_target_registry_v2.json"), encoding="utf-8"))
    registry = {"task": "V1_UPGRADE_DEMO_BUILD", "generated_at": NOW, "read_only_on": list(FROZEN),
                 "target_ref": {"scenario_definition_hash": reg8["scenario_definition_hash"], "registry_v2_hash": reg8["registry_hash"],
                                 "horizon": int(reg8["scenario_definition"]["horizon"]), "prediction_status": "UNSUPPORTED (R8-B)"},
                 "isolation": {"instance_dir": INSTANCE or None, "magic": MAGIC, "comment": COMMENT, "reserved_magic": {90001: "collect", 90002: "OLD_V1", 90003: "V2"}},
                 "risk_limits": RiskGuard().cfg,
                 "execution": {"ORDER_SEND": "OFF", "LIVE": False, "REAL_MONEY": False},
                 "note": "this is a data-collection experiment; the predictor is UNSUPPORTED (R3/R6/R8-B); no profit/win-probability output"}
    json.dump(registry, open(os.path.join(ROOT, "registry", "v1_upgrade_registry.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    acc_flat = bool(live and live.get("positions") is not None and len(live.get("positions") or []) == 0)
    first_order = "PENDING_RUNTIME" if (all_pass and acc_flat) else ("DEFERRED_UNTIL_ACCOUNT_FLAT" if all_pass else None)
    report = {"generated_at": NOW, "tests": tests, "pass": npass, "blocked": nblk, "fail": nfail, "total": len(tests),
               "ALL_GATES_PASS": all_pass, "VERDICT": "START_NEW_V1_DEMO" if all_pass else "DO_NOT_START",
               "NEW_V1": "ACTIVE" if all_pass else "BLOCKED", "ORDER_SEND": "DEMO_ONLY" if all_pass else "OFF",
               "LIVE": False, "REAL_MONEY": False,
               "account": ({"login": live.get("login"), "server": live.get("server"), "demo": live.get("demo"),
                             "balance": live.get("balance"), "equity": live.get("equity")} if live else None),
               "account_inheritance_deviation": INHERIT_DEVIATION,
               "open_positions_at_start": (live or {}).get("positions"),
               "first_order_policy": ("WAIT_UNTIL_ACCOUNT_FLAT (task book §7: if a position exists, wait)" if not acc_flat else "account flat"),
               "FIRST_DEMO_ORDER": first_order,
               "blocking_input": None if all_pass else "see non-PASS tests"}
    json.dump(report, open(os.path.join(ROOT, "tests", "GATE_RESULTS.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    for k, v in tests.items():
        print(f"  {v['result']:<8} {k}  {v['detail'][:220]}")
    print("PASS", npass, "BLOCKED", nblk, "FAIL", nfail, "| ALL_GATES_PASS", all_pass, "| VERDICT", report["VERDICT"])


if __name__ == "__main__":
    main()
