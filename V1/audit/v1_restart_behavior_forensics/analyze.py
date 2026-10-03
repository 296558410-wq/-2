# -*- coding: utf-8 -*-
"""analyze.py — ledger schema/behaviour drift + pre/post-restart cycle comparison (READ-ONLY)."""
from __future__ import annotations
import csv, json, os, collections, datetime as dt
REPO = r"C:\AIQuant"; BASE = os.path.join(REPO, "research", "hermes", "trader_v1"); UP = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_restart_behavior_forensics")
os.makedirs(OUT, exist_ok=True)
L = [json.loads(l) for l in open(os.path.join(UP, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
D = [e for e in L if e.get("event") == "DECISION"]
RESTART = "2026-10-01T13:52:15+00:00"

# ---- 1) schema drift over time (top-level / snapshot / live_state key sets) ----
def keyset(e, field):
    v = e.get(field)
    return tuple(sorted(v.keys())) if isinstance(v, dict) else None
drift = {"top": [], "snapshot": [], "live_state": []}
for field in ("__top__", "snapshot", "live_state"):
    seen = {}
    for e in D:
        ks = tuple(sorted(k for k in e.keys() if k not in ("current_hash",))) if field == "__top__" else keyset(e, field)
        if ks is None: continue
        if ks not in seen:
            seen[ks] = e["ts_utc"]
            drift[field.replace("__top__", "top")].append({"first_seen": e["ts_utc"], "n": len(ks), "keys": list(ks)})

# ---- 2) pre/post restart comparison of the last/first valid cycles ----
def brief(e):
    ls = e.get("live_state") or {}; sn = e.get("snapshot") or {}; oi = e.get("order_intent") or {}
    sg = e.get("signal") or {}
    return {"seq": e.get("seq"), "ts_utc": e.get("ts_utc"), "action": e.get("action"),
            "signal_source": e.get("signal_source"), "state": ls.get("state"), "family": ls.get("family"),
            "MARKET_BEHAVIOR": ls.get("MARKET_BEHAVIOR"), "trend_20": ls.get("trend_20"), "ma20": ls.get("ma20"),
            "atr": e.get("atr") if e.get("atr") is not None else ls.get("atr"), "last_bar_utc": ls.get("last_bar_utc"),
            "signal_family": sg.get("signal_family"), "known": sg.get("known"),
            "oi_trade": oi.get("trade"), "oi_side": oi.get("side"), "oi_sl": oi.get("sl"), "oi_tp": oi.get("tp"),
            "bid": sn.get("bid"), "ask": sn.get("ask"), "spread_bps": sn.get("spread_bps"),
            "snapshot_keys": ",".join(sorted(sn.keys())), "live_state_keys": ",".join(sorted(ls.keys())),
            "risk_allow": e.get("risk_allow"), "risk_reasons": ";".join(e.get("risk_reasons") or []),
            "account_positions": e.get("account_positions")}
# pre: last 6 DECISION before restart that carry a live_state; post: first 6 after
pre = [e for e in D if e["ts_utc"] < RESTART and (e.get("live_state") or {}).get("state")]
post = [e for e in D if e["ts_utc"] >= RESTART and (e.get("live_state") or {}).get("state")]
sel = pre[-6:] + post[:6]
rows = [brief(e) for e in sel]
with open(os.path.join(OUT, "pre_post_replay.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow(r)
print("PRE (last 6 w/ live_state):")
for r in rows[:6]: print("  ", r["ts_utc"][:19], r["action"][:22], "state=", r["state"], "fam=", r["family"], "trend20=", r["trend_20"], "atr=", round(r["atr"],3) if isinstance(r["atr"],float) else r["atr"], "bar=", r["last_bar_utc"])
print("POST (first 6 w/ live_state):")
for r in rows[6:]: print("  ", r["ts_utc"][:19], r["action"][:22], "state=", r["state"], "fam=", r["family"], "trend20=", r["trend_20"], "atr=", round(r["atr"],3) if isinstance(r["atr"],float) else r["atr"], "bar=", r["last_bar_utc"])
print("\n=== schema drift ===")
for field in ("top", "snapshot", "live_state"):
    print(f"-- {field} ({len(drift[field])} distinct shapes)")
    for d in drift[field]:
        print("   ", d["first_seen"][:19], d["n"], d["keys"][:8], "...")

# ---- 3) state_diff.json (hidden-state inventory) ----
S = json.load(open(os.path.join(OUT, "_state_seed.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "_state_seed.json")) else {}
S.update({
 "schema": "v1_restart_state_diff/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
 "restart_utc": RESTART,
 "label_hysteresis": {"persisted": False, "note": "hysteresis k=2 is path-dependent; recomputed each cycle from MT5 M1 bars; warm-up ~90000 M1 (~6000 M15) >> 5000-M15 convergence threshold; nothing persisted across restart"},
 "risk_guard": {"persisted": False, "note": "RiskGuard() constructed fresh each cycle in the 09-28/10-01 code; daily_loss/consecutive_losses never written back -> identical before and after restart (no state to lose)"},
 "position_state": {"persisted": "broker(MT5) holds positions; engine reads mt5.positions_get()", "note": "not engine-persisted; restart does not drop positions"},
 "time_base": {"persisted": False, "note": "NOW = module import time; roll_day(NOW[:10]) uses import-time UTC date"},
 "mt5_terminal_cache": {"persisted": False, "note": "terminal data cache/history refreshed on process restart; connection reopened each cycle with explicit path"},
 "ledger": {"persisted": True, "recovered": "Ledger.verify() on every cycle; chain continues across restart"},
 "snapshot_fields_drift": drift["snapshot"],
})
json.dump(S, open(os.path.join(OUT, "state_diff.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
json.dump({"schema": "v1_restart_schema_drift/1", "drift": drift}, open(os.path.join(OUT, "_schema_drift.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("\nwrote pre_post_replay.csv, state_diff.json, _schema_drift.json")
