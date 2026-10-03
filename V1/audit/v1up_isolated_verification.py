# -*- coding: utf-8 -*-
"""v1up_isolated_verification.py — isolated (no MT5, no writes) verification of the APPLIED wiring.
Uses a throwaway copy of the ledger; imports the patched gates.py; proves the guard now fires and that
the execution path is untouched. Writes only V1_ISOLATED_VERIFICATION.json under trader_v1/audit/.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, shutil, sys, tempfile

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_upgrade")
AUDIT = os.path.join(BASE, "audit")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
sys.path.insert(0, ROOT)
import gates  # noqa: E402  (patched)

out = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "mode": "ISOLATED: ledger copy in a temp dir, no MT5, no production write"}

tmp = tempfile.mkdtemp(prefix="v1up_iso_")
copy = os.path.join(tmp, "ledger_copy.jsonl")
shutil.copy2(LEDGER, copy)
ok, n, bad = gates.Ledger(copy).verify()
out["isolated_ledger"] = {"copy": "temp", "chain_ok": ok, "entries": n, "bad": bad,
                          "sha256": hashlib.sha256(open(copy, "rb").read()).hexdigest()}
ev = [json.loads(l) for l in open(copy, encoding="utf-8") if l.strip()]

FRESH = {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 120}
# per-open counterfactual over the whole window, day = open UTC date (engine frame)
opens = sorted((dt.datetime.fromisoformat(e["ts_utc"]), str(e.get("order_id")))
               for e in ev if e["event"] == "POSITION")
blocks, by_day = 0, {}
for ts, _oid in opens:
    known = [e for e in ev if e["event"] == "PNL" and gates.realized_close_utc(e) <= ts]
    rg = gates.rebuild_risk_state(gates.RiskGuard(), known, ts.date().isoformat())
    okk, reasons = rg.evaluate({"order_id": "iso"}, FRESH, 0)
    if not okk:
        blocks += 1
        by_day[ts.date().isoformat()] = by_day.get(ts.date().isoformat(), 0) + 1
out["counterfactual"] = {"opens": len(opens), "should_reject": blocks, "by_day": by_day}

# end-of-window state for the current UTC day (what the live guard would carry now)
today = dt.datetime.now(dt.timezone.utc).date().isoformat()
rg_today = gates.rebuild_risk_state(gates.RiskGuard(), ev, today)
out["state_today"] = {"day_utc": today, "daily_loss": round(rg_today.daily_loss, 2),
                      "consecutive_losses": rg_today.consecutive_losses}

# cross-day isolation
rg_cd = gates.rebuild_risk_state(gates.RiskGuard(), ev, "2026-09-30")
out["state_0930"] = {"daily_loss": round(rg_cd.daily_loss, 2), "consecutive_losses": rg_cd.consecutive_losses}
# explicit cross-day isolation: the 09-30 state must equal the sum of 09-30 closes ONLY (09-29 excluded)
_closes_0930 = [gates.realized_pnl(e) for e in ev
                if e["event"] == "PNL" and gates.realized_close_utc(e).date().isoformat() == "2026-09-30"]
out["cross_day_isolated"] = abs(rg_cd.daily_loss - sum(_closes_0930)) < 1e-6
out["cross_day_isolated_detail"] = {"guard_daily_0930": round(rg_cd.daily_loss, 6),
                                    "independent_sum_0930_closes": round(sum(_closes_0930), 6)}

# execution path untouched
cyc = open(os.path.join(ROOT, "cycle.py"), encoding="utf-8").read()
out["execution_path"] = {"cycle_order_send": cyc.count("mt5.order_send("),
                         "cycle_order_check": cyc.count("mt5.order_check("),
                         "gates_has_mt5": "import MetaTrader5" in open(os.path.join(ROOT, "gates.py"), encoding="utf-8").read()}
out["verdict"] = "ISOLATED_VERIFICATION_PASS" if (ok and blocks >= 8 and out["execution_path"]["cycle_order_send"] == 1) else "FAIL"
json.dump(out, open(os.path.join(AUDIT, "V1_ISOLATED_VERIFICATION.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
