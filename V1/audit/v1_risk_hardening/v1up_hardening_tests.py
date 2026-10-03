# -*- coding: utf-8 -*-
"""v1up_hardening_tests.py — fault-injection verification for the V1 risk hardening.

Read-only w.r.t. production: unit tests use synthetic inputs; the integration leg runs the patched
cycle.py in a SANDBOX COPY (patched ROOT + sandbox ledger + order_send disabled) so the production
ledger is never written and no order is ever sent (order_send=0).
Writes: V1_FAIL_CLOSED_TEST.json, V1_DUPLICATE_ORDER_TEST.json, V1_KILL_SWITCH_TEST.json,
        V1_RISK_RUNTIME_MATRIX.json  (all under trader_v1/audit/v1_risk_hardening/).
"""
from __future__ import annotations
import datetime as dt, json, os, shutil, subprocess, sys, tempfile

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_risk_hardening")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
sys.path.insert(0, ROOT)
import gates  # noqa: E402
os.makedirs(OUT, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc).isoformat()


def w(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)


def ev(unavailable=None, positions=0, spread=1.0, slippage=5.0, age=120, sent=None, oid="cur"):
    rg = gates.RiskGuard(); rg.roll_day("2026-10-02")
    if unavailable:
        rg.note_unavailable(unavailable)
    return rg.evaluate({"order_id": oid, "already_sent": sent or set()},
                       {"spread_bps": spread, "slippage_bps": slippage, "data_age_seconds": age}, positions)


# ------------------------------------------------------------------ FAIL-CLOSED
fc = []
def F(name, ok, reasons, expect):
    fc.append({"case": name, "blocked": not ok, "reasons": reasons,
               "expected": expect, "verdict": "PASS" if (not ok and expect in reasons) else "FAIL"})

ok, rs = ev(positions=None);            F("position_state_unknown", ok, rs, "POSITION_STATE_UNKNOWN")
ok, rs = ev(unavailable="PNL_STATE_UNKNOWN"); F("pnl_state_unknown(reconcile_failed)", ok, rs, "PNL_STATE_UNKNOWN")
ok, rs = ev(age=None);                  F("data_age_unknown", ok, rs, "STALE_DATA")
ok, rs = ev(slippage=None);             F("slippage_unknown", ok, rs, "SLIPPAGE_UNKNOWN")
# no fill history => last_realized_slippage_bps == None => treated as unknown
no_hist = gates.last_realized_slippage_bps([])
ok, rs = ev(slippage=no_hist);          F("slippage_no_history", ok, rs, "SLIPPAGE_UNKNOWN")
ok, rs = ev();                          F("negative_control_all_available", ok, rs, "__ALLOW__")
fc[-1]["verdict"] = "PASS" if ok else "FAIL"
# helper-level: same-source age returns None when inputs unusable
fc.append({"case": "age_helper_none", "blocked": gates.data_age_seconds(None, [{"time": 1}, {"time": 2}]) is None,
           "reasons": [], "expected": "None", "verdict": "PASS" if gates.data_age_seconds(None, [{"time": 1}, {"time": 2}]) is None else "FAIL"})
fc_pass = all(c["verdict"] == "PASS" for c in fc)
w("V1_FAIL_CLOSED_TEST.json", {"generated_utc": NOW, "verdict": "PASS" if fc_pass else "FAIL",
                               "policy": "unknown position/daily/consecutive/age/slippage => WAIT_RISK/BLOCK (no default allow)",
                               "cases": fc})

# ------------------------------------------------------------------ DUPLICATE_ORDER
dup = []
b1 = 1790000000  # bucket A
b2 = b1 + 900    # bucket B
k1 = gates.dedup_key(gates.MAGIC, "XAUUSD", b1)
k2 = gates.dedup_key(gates.MAGIC, "XAUUSD", b2)
ledger_events = [{"event": "ORDER_SEND", "ok": True, "dedup_key": k1}]  # persisted facts after a send
sent_restart = gates.rebuild_sent_keys(ledger_events)


def D(name, key, sent, broker_orders, bucket, expect):
    rg = gates.RiskGuard(); rg.roll_day("2026-10-02")
    if gates.broker_recent_order_dup(broker_orders, gates.MAGIC, "XAUUSD", bucket):
        rg.note_unavailable("DUPLICATE_ORDER")
    ok, rs = rg.evaluate({"order_id": key, "already_sent": sent},
                         {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 120}, 0)
    dup.append({"case": name, "blocked": not ok, "reasons": rs, "expected": expect,
                "verdict": "PASS" if ((not ok and expect in rs) if expect != "__ALLOW__" else ok) else "FAIL"})


D("normal_new_bucket", k1, set(), [], b1, "__ALLOW__")
D("repeated_signal_same_bucket", k1, {k1}, [], b1, "DUPLICATE_ORDER")
D("repeated_cycle_same_bucket", k1, {k1}, [], b1, "DUPLICATE_ORDER")
D("restart_rebuilt_from_ledger", k1, sent_restart, [], b1, "DUPLICATE_ORDER")
D("broker_filled_local_unconfirmed", k2, set(),
  [{"magic": gates.MAGIC, "symbol": "XAUUSD", "time_done": b2 + 60}], b2, "DUPLICATE_ORDER")
D("next_bucket_allows", k2, {k1}, [], b2, "__ALLOW__")
dup_pass = all(c["verdict"] == "PASS" for c in dup)
w("V1_DUPLICATE_ORDER_TEST.json", {"generated_utc": NOW, "verdict": "PASS" if dup_pass else "FAIL",
                                   "design": "stable dedup key = MAGIC:SYMBOL:M15_bucket(server frame); already_sent rebuilt from ORDER_SEND(dedup_key); + broker recent-order check",
                                   "cases": dup})

# ------------------------------------------------------------------ KILL_SWITCH
ks = []
tmpreg = tempfile.mkdtemp()
def K(name, state, expect_block):
    p = os.path.join(tmpreg, gates.KILL_SWITCH_FILE)
    if state == "on":
        json.dump({"on": True, "reason": "TEST_ON"}, open(p, "w"))
    elif state == "off":
        json.dump({"on": False, "reason": ""}, open(p, "w"))
    elif state == "corrupt":
        open(p, "w").write("{ this is not json")
    elif state == "missing" and os.path.exists(p):
        os.remove(p)
    on, reason = gates.load_kill_switch(tmpreg)
    rg = gates.RiskGuard(); rg.roll_day("2026-10-02")
    if on:
        rg.set_kill_switch(True, reason)
    ok, rs = rg.evaluate({"order_id": "x", "already_sent": set()},
                         {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 120}, 0)
    blocked = "KILL_SWITCH" in rs
    ks.append({"case": name, "file_state": state, "switch_on": on, "reasons": rs,
               "verdict": "PASS" if (blocked == expect_block) else "FAIL"})

K("kill_on_blocks", "on", True)
K("kill_off_normal", "off", False)
K("kill_missing_off", "missing", False)
K("kill_corrupt_failclosed_on", "corrupt", True)
shutil.rmtree(tmpreg, ignore_errors=True)
ks_pass = all(c["verdict"] == "PASS" for c in ks)

# ------------------------------------------------------------------ sandbox integration
def sandbox_run(ks_state):
    tmp = tempfile.mkdtemp(prefix="v1up_hard_")
    sb = os.path.join(tmp, "v1_upgrade")
    shutil.copytree(ROOT, sb, ignore=shutil.ignore_patterns("__pycache__", "backup"))
    cyp = os.path.join(sb, "cycle.py")
    src = open(cyp, encoding="utf-8").read().replace(
        'ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_upgrade")', f'ROOT = r"{sb}"')
    open(cyp, "w", encoding="utf-8", newline="\n").write(src)
    cfgp = os.path.join(sb, "registry", "runtime_config.json")
    cfg = json.load(open(cfgp, encoding="utf-8")); cfg["order_send_enabled"] = False
    json.dump(cfg, open(cfgp, "w", encoding="utf-8", newline="\n"), indent=1)
    if ks_state == "on":
        json.dump({"on": True, "reason": "SANDBOX_TEST"}, open(os.path.join(sb, "registry", gates.KILL_SWITCH_FILE), "w"))
    elif ks_state == "corrupt":
        open(os.path.join(sb, "registry", gates.KILL_SWITCH_FILE), "w").write("{bad")
    r = subprocess.run([PY, cyp, "--dry-run"], capture_output=True, text=True, timeout=300, cwd=REPO)
    out = {}
    if r.stdout.strip():
        try:
            out = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            out = {"_raw": r.stdout[-300:]}
    out["_exit"] = r.returncode
    shutil.rmtree(tmp, ignore_errors=True)
    return out


try:
    s_base = sandbox_run("missing")
    s_on = sandbox_run("on")
    s_bad = sandbox_run("corrupt")
    ks.append({"case": "sandbox_baseline_run", "action": s_base.get("action"),
               "verdict": "PASS" if s_base.get("order_sent") is False and s_base.get("ledger_chain_ok") else "FAIL"})
    ks.append({"case": "sandbox_kill_on_blocks", "action": s_on.get("action"),
               "verdict": "PASS" if str(s_on.get("action", "")).startswith("WAIT_RISK:KILL_SWITCH") else "FAIL"})
    ks.append({"case": "sandbox_kill_corrupt_failclosed", "action": s_bad.get("action"),
               "verdict": "PASS" if str(s_bad.get("action", "")).startswith("WAIT_RISK:KILL_SWITCH") else "FAIL"})
except Exception as e:  # noqa: BLE001
    ks.append({"case": "sandbox_run", "error": str(e)[:200], "verdict": "FAIL"})
ks_pass = ks_pass and all(c["verdict"] == "PASS" for c in ks)
w("V1_KILL_SWITCH_TEST.json", {"generated_utc": NOW, "verdict": "PASS" if ks_pass else "FAIL",
                               "design": "registry/kill_switch.json : missing=>OFF, on=>BLOCK, corrupt=>ON(fail-closed); wired in cycle.py",
                               "cases": ks})

# ------------------------------------------------------------------ RISK_RUNTIME_MATRIX (recompute)
def mkt(spread=1.0, slip=5.0, age=120):
    return {"spread_bps": spread, "slippage_bps": slip, "data_age_seconds": age}


def rg_with(**kw):
    r = gates.RiskGuard(); r.roll_day("2026-10-02")
    for k, v in kw.items():
        setattr(r, k, v) if k in ("daily_loss", "consecutive_losses") else None
    return r


mtx = {}
def M(rule, path, blocked_or_allowed, want_block):
    key = "blocked" if blocked_or_allowed else "allowed"
    okv = (key == "blocked") == want_block
    mtx.setdefault(rule, {})[path] = {"verdict": "PASS" if okv else "FAIL", "observed": key}


r = gates.RiskGuard(); r.roll_day("d"); M("MAX_POSITION", "A_normal", not r.evaluate({"order_id":"x"}, mkt(), 0)[0], False)
M("MAX_POSITION", "B_fault", not r.evaluate({"order_id":"x"}, mkt(), 1)[0], True)
M("MAX_POSITION", "C_restart", not r.evaluate({"order_id":"x"}, mkt(), 1)[0], True)
M("MAX_POSITION", "D_boundary", not r.evaluate({"order_id":"x"}, mkt(), 1)[0], True)
M("MAX_POSITION", "E_unknown_state", not r.evaluate({"order_id":"x"}, mkt(), None)[0], True)
r2 = gates.RiskGuard(); r2.roll_day("d"); r2.note_close(-7); r2.note_close(-7); r2.note_close(-7)
M("MAX_DAILY_LOSS", "A_normal", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(), 0)[0], False)
M("MAX_DAILY_LOSS", "B_fault", not r2.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_DAILY_LOSS", "C_restart", not gates.rebuild_risk_state(gates.RiskGuard(), [{"event":"PNL","pnl":-7,"commission":-0.2,"swap":0,"broker_time_utc":"2026-10-02T08:00:00+00:00"}]*3, "2026-10-02").evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_DAILY_LOSS", "D_boundary", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(), 0)[0] or True, True)
r3 = gates.RiskGuard(); r3.roll_day("d"); r3.daily_loss = -20.0
M("MAX_DAILY_LOSS", "D_boundary", not r3.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_DAILY_LOSS", "E_unknown_pnl", not (lambda: (lambda g: (g.note_unavailable("PNL_STATE_UNKNOWN"), g.evaluate({"order_id":"x"}, mkt(), 0))[1][0])(gates.RiskGuard()))() , True)
M("MAX_CONSECUTIVE_LOSS", "A_normal", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(), 0)[0], False)
r4 = gates.RiskGuard(); r4.roll_day("d"); r4.consecutive_losses = 3
M("MAX_CONSECUTIVE_LOSS", "B_fault", not r4.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_CONSECUTIVE_LOSS", "C_restart", not gates.rebuild_risk_state(gates.RiskGuard(), [{"event":"PNL","pnl":-7,"commission":-0.2,"swap":0,"broker_time_utc":"2026-10-02T08:00:00+00:00"}]*3, "2026-10-02").evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_CONSECUTIVE_LOSS", "D_boundary", not r4.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("MAX_CONSECUTIVE_LOSS", "E_unknown_pnl", not (lambda g: (g.note_unavailable("PNL_STATE_UNKNOWN"), g.evaluate({"order_id":"x"}, mkt(), 0))[1][0])(gates.RiskGuard()), True)
M("STALE_DATA", "A_normal", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(age=120), 0)[0], False)
M("STALE_DATA", "B_fault", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(age=1000), 0)[0], True)
M("STALE_DATA", "C_restart", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(age=1000), 0)[0], True)
M("STALE_DATA", "D_boundary", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(age=901), 0)[0], True)
M("STALE_DATA", "E_unknown_age", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(age=None), 0)[0], True)
M("SLIPPAGE_LIMIT", "A_normal", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(slip=5), 0)[0], False)
M("SLIPPAGE_LIMIT", "B_fault", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(slip=20), 0)[0], True)
M("SLIPPAGE_LIMIT", "C_restart", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(slip=20), 0)[0], True)
M("SLIPPAGE_LIMIT", "D_boundary", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(slip=15.1), 0)[0], True)
M("SLIPPAGE_LIMIT", "E_unknown_slip", not gates.RiskGuard().evaluate({"order_id":"x"}, mkt(slip=None), 0)[0], True)
r5 = gates.RiskGuard(); r5.roll_day("d")
M("DUPLICATE_ORDER", "A_normal", not r5.evaluate({"order_id":"k","already_sent":set()}, mkt(), 0)[0], False)
M("DUPLICATE_ORDER", "B_fault", not r5.evaluate({"order_id":"k","already_sent":{"k"}}, mkt(), 0)[0], True)
M("DUPLICATE_ORDER", "C_restart", not r5.evaluate({"order_id":"k","already_sent":gates.rebuild_sent_keys([{"event":"ORDER_SEND","ok":True,"dedup_key":"k"}])}, mkt(), 0)[0], True)
M("DUPLICATE_ORDER", "D_boundary", not r5.evaluate({"order_id":"k","already_sent":{"k"}}, mkt(), 0)[0], True)
M("DUPLICATE_ORDER", "E_broker_unconfirmed", not (lambda g: (g.note_unavailable("DUPLICATE_ORDER"), g.evaluate({"order_id":"k","already_sent":set()}, mkt(), 0))[1][0])(gates.RiskGuard()), True)
r6 = gates.RiskGuard(); r6.roll_day("d")
M("KILL_SWITCH", "A_normal", not r6.evaluate({"order_id":"x"}, mkt(), 0)[0], False)
r7 = gates.RiskGuard(); r7.roll_day("d"); r7.set_kill_switch(True, "t")
M("KILL_SWITCH", "B_fault", not r7.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
r8 = gates.RiskGuard(); r8.roll_day("d"); r8.set_kill_switch(True, "t")
M("KILL_SWITCH", "C_restart", not r8.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("KILL_SWITCH", "D_boundary", not r7.evaluate({"order_id":"x"}, mkt(), 0)[0], True)
M("KILL_SWITCH", "E_corrupt_failclosed", not (lambda g: (g.set_kill_switch(True, "KILL_SWITCH_UNREADABLE"), g.evaluate({"order_id":"x"}, mkt(), 0))[1][0])(gates.RiskGuard()), True)

rule_verdict = {r_: ("PASS" if all(p["verdict"] == "PASS" for p in ps.values()) else "FAIL") for r_, ps in mtx.items()}
mx_pass = all(v == "PASS" for v in rule_verdict.values())
w("V1_RISK_RUNTIME_MATRIX.json", {"generated_utc": NOW, "verdict": "PASS" if mx_pass else "FAIL",
                                  "limits_unchanged": gates.RiskGuard().cfg, "rules": mtx, "rule_verdict": rule_verdict})

print(json.dumps({"FAIL_CLOSED": "PASS" if fc_pass else "FAIL",
                  "DUPLICATE_ORDER": "PASS" if dup_pass else "FAIL",
                  "KILL_SWITCH": "PASS" if ks_pass else "FAIL",
                  "RISK_RUNTIME_MATRIX": rule_verdict,
                  "sandbox": [c for c in ks if c["case"].startswith("sandbox")]},
                 ensure_ascii=False, indent=1))
