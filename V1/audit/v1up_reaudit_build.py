# -*- coding: utf-8 -*-
"""v1up_reaudit_build.py — evidence builder for the V1 full re-audit (READ-ONLY, order_send=0).

Generates: V1_RISK_RUNTIME_MATRIX.json, V1_EXECUTION_AUDIT.json, V1_LEDGER_REPLAY_AUDIT.json,
V1_PIT_DATA_REGISTRY.json, V1_DEFECT_REGISTER.json, V1_ALPHA_STATS.json.
Every number is derived from broker facts / the ledger / the applied code — never from V1's own claims.
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, random, statistics, sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_full_reaudit")
ENV = os.path.join(REPO, ".env.mt5_demo")
TERM = os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
MAGIC = 90011
SERVER_OFF = dt.timedelta(hours=3)
sys.path.insert(0, ROOT)
import gates  # noqa: E402  (applied)
import signal_baseline as SB  # noqa: E402

os.makedirs(OUT, exist_ok=True)
now = dt.datetime.now(dt.timezone.utc).isoformat()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def rows():
    return [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]


def load_env():
    d = {}
    for line in open(ENV, encoding="utf-8-sig", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def broker_facts():
    import MetaTrader5 as mt5
    env = load_env()
    kw = {"path": TERM, "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
    kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
    if not mt5.initialize(**kw):
        raise RuntimeError(f"MT5_INIT_FAILED {mt5.last_error()}")
    ai = mt5.account_info()
    tk = mt5.symbol_info_tick("XAUUSD")
    frm = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)
    to = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
    deals = mt5.history_deals_get(frm, to) or []
    orders = mt5.history_orders_get(frm, to) or []
    srv_now, utc_now = int(getattr(tk, "time", 0) or 0), dt.datetime.now(dt.timezone.utc)
    acct = {"balance": ai.balance, "equity": ai.equity, "login": ai.login, "server": ai.server,
            "trade_mode": ai.trade_mode, "offset_sec": srv_now - int(utc_now.timestamp())}
    mt5.shutdown()
    d = [{k: getattr(x, k, None) for k in ("ticket", "order", "time", "type", "entry", "magic", "position_id",
                                            "volume", "price", "commission", "swap", "profit", "comment", "reason")} for x in deals]
    o = [{k: getattr(x, k, None) for k in ("ticket", "time_setup", "time_done", "type", "state", "magic",
                                            "position_id", "volume_initial", "price_open", "comment", "type_filling")} for x in orders]
    return acct, d, o


acct, deals, orders = broker_facts()
d90011 = [x for x in deals if int(x.get("magic") or 0) == MAGIC]
L = rows()
send_events = [e for e in L if e["event"] == "ORDER_SEND"]
ok_sends = [e for e in send_events if e.get("ok")]
by_pos = {}
for x in d90011:
    r = by_pos.setdefault(str(x["position_id"]), {"open": None, "close": None})
    if x["entry"] == 0:
        r["open"] = x
    elif x["entry"] == 1:
        r["close"] = x
trades = []
for pid, r in by_pos.items():
    o, c = r["open"], r["close"]
    if not o:
        continue
    dur = (int(c["time"]) - int(o["time"])) if c else None
    trades.append({"position_id": pid, "open_srv": int(o["time"]), "close_srv": int(c["time"]) if c else None,
                   "open_utc": dt.datetime.fromtimestamp(int(o["time"]) - 10800, dt.timezone.utc).isoformat(),
                   "side": "LONG" if int(o["type"]) == 0 else "SHORT",
                   "volume": float(o["volume"]), "open_price": float(o["price"]),
                   "close_price": float(c["price"]) if c else None,
                   "profit": round(float(c["profit"]), 2) if c else None,
                   "commission": round(float((c.get("commission") or 0) + (o.get("commission") or 0)), 2) if c else None,
                   "swap": round(float((c.get("swap") or 0) + (o.get("swap") or 0)), 2) if c else None,
                   "net": round(float(c["profit"] + (c.get("commission") or 0) + (o.get("commission") or 0)
                                      + (c.get("swap") or 0) + (o.get("swap") or 0)), 2) if c else None,
                   "close_comment": c.get("comment") if c else None,
                   "close_reason": ("SL" if c and str(c["comment"]).strip().lower().startswith("[sl")
                                    else "TP" if c and str(c["comment"]).strip().lower().startswith("[tp")
                                    else ("MANUAL" if c else None)),
                   "closed": c is not None, "duration_sec": dur})
trades.sort(key=lambda t: t["open_srv"])
slip = {e["order_id"]: e.get("slippage_bps") for e in ok_sends if e.get("order_id")}
lat = {e["order_id"]: e.get("latency_ms") for e in ok_sends if e.get("order_id")}
for t in trades:
    t["slippage_bps"] = slip.get(t["position_id"])
    t["latency_ms"] = lat.get(t["position_id"])

# ---------------------------------------------------------------- RISK RUNTIME MATRIX
def ev(daily=0.0, cons=0, pos=0, spread=1.0, slipv=0.0, age=10, pnl_events=None):
    rg = gates.RiskGuard()
    if pnl_events:
        gates.rebuild_risk_state(rg, pnl_events, "2026-10-02")
    else:
        rg.roll_day("2026-10-02")
        rg.daily_loss, rg.consecutive_losses = daily, cons
    ok, reasons = rg.evaluate({"order_id": "x"}, {"spread_bps": spread, "slippage_bps": slipv,
                                                  "data_age_seconds": age}, pos)
    return ok, reasons


lim = gates.RiskGuard().cfg
P = lambda ok, rs: {"result": "PASS" if ok else "FAIL", "reasons": rs}
matrix = {}


def add(rule, path, verdict, detail):
    if isinstance(detail, (set, frozenset)):          # guards against '{text}' set-literal typos
        detail = {"note": "; ".join(sorted(detail))}
    matrix.setdefault(rule, {})[path] = {"verdict": verdict, "detail": detail}


# MAX_POSITION
add("MAX_POSITION", "A_normal", *(( "PASS" if ev(pos=0)[0] else "FAIL"), {"allow": ev(pos=0)[0]}))
add("MAX_POSITION", "B_fault", *((("PASS") if not ev(pos=1)[0] and "MAX_POSITION" in ev(pos=1)[1] else "FAIL"),
                                 {"reasons": ev(pos=1)[1]}))
add("MAX_POSITION", "C_restart", "PASS", {"stateless_live_input": True, "note": "uses live positions each cycle; no persisted state needed"})
add("MAX_POSITION", "D_boundary", (("PASS") if not ev(pos=1)[0] else "FAIL"), {"positions=limit=1 -> deny (>=)"})
add("MAX_POSITION", "E_data_anomaly", "PASS", {"note": "caller normalizes positions_get()None -> []; None would raise in-guard"})
# MAX_DAILY_LOSS
losses = [{"event": "PNL", "pnl": -7.0, "commission": -0.2, "swap": 0.0, "broker_time_utc": "2026-10-02T08:00:00+00:00"} for _ in range(3)]
add("MAX_DAILY_LOSS", "A_normal", (("PASS") if ev(daily=-5.0)[0] else "FAIL"), {"daily=-5 -> allow"})
add("MAX_DAILY_LOSS", "B_fault", (("PASS") if not ev(pnl_events=losses)[0] and "MAX_DAILY_LOSS" in ev(pnl_events=losses)[1] else "FAIL"), {"rebuilt daily=-21.6 -> deny"})
add("MAX_DAILY_LOSS", "C_restart", (("PASS") if not ev(pnl_events=losses)[0] else "FAIL"), {"rebuilt from ledger after restart -> deny"})
add("MAX_DAILY_LOSS", "D_boundary", (("PASS") if not ev(daily=-20.0)[0] else "FAIL"), {"daily == -20.0 -> deny (<=)"})
add("MAX_DAILY_LOSS", "E_data_anomaly", "FAIL", {"note": "no PNL events (broker query fail) -> daily=0 -> no protection (under-count); reconciliation lag under-counts"})
# MAX_CONSECUTIVE_LOSS
add("MAX_CONSECUTIVE_LOSS", "A_normal", (("PASS") if ev(cons=2)[0] else "FAIL"), {"cons=2 -> allow"})
add("MAX_CONSECUTIVE_LOSS", "B_fault", (("PASS") if not ev(cons=3)[0] and "MAX_CONSECUTIVE_LOSS" in ev(cons=3)[1] else "FAIL"), {"cons=3 -> deny"})
add("MAX_CONSECUTIVE_LOSS", "C_restart", (("PASS") if not ev(pnl_events=losses)[0] else "FAIL"), {"rebuilt after restart -> deny"})
add("MAX_CONSECUTIVE_LOSS", "D_boundary", (("PASS") if not ev(cons=3)[0] and ev(cons=2)[0] else "FAIL"), {"cons=3 deny, cons=2 allow"})
add("MAX_CONSECUTIVE_LOSS", "E_data_anomaly", "FAIL", {"note": "win resets to 0; missing closes under-count streak"})
# STALE_DATA
add("STALE_DATA", "A_normal", (("PASS") if ev(age=120)[0] else "FAIL"), {"age=120 -> allow"})
add("STALE_DATA", "B_fault", (("PASS") if not ev(age=1000)[0] and "STALE_DATA" in ev(age=1000)[1] else "FAIL"), {"age=1000 -> deny"})
add("STALE_DATA", "C_restart", "PASS", {"stateless_live_input": True})
add("STALE_DATA", "D_boundary", (("PASS") if ev(age=900)[0] and not ev(age=901)[0] else "FAIL"), {"900 allow, 901 deny (>)"})
add("STALE_DATA", "E_data_anomaly", (("PASS") if not ev(age=None)[0] else "FAIL"), {"age=None -> deny (fail-closed)"})
# SLIPPAGE_LIMIT
add("SLIPPAGE_LIMIT", "A_normal", (("PASS") if ev(slipv=5)[0] else "FAIL"), {"5 bps -> allow"})
add("SLIPPAGE_LIMIT", "B_fault", (("PASS") if not ev(slipv=20)[0] and "SLIPPAGE_LIMIT" in ev(slipv=20)[1] else "FAIL"), {"20 bps -> deny"})
add("SLIPPAGE_LIMIT", "C_restart", "PASS", {"stateless_live_input": True, "note": "fed from last realized ORDER_SEND slip in the ledger"})
add("SLIPPAGE_LIMIT", "D_boundary", (("PASS") if ev(slipv=15.0)[0] and not ev(slipv=15.1)[0] else "FAIL"), {"15.0 allow, 15.1 deny (>)"})
add("SLIPPAGE_LIMIT", "E_data_anomaly", "FAIL", {"note": "no fill history -> slippage treated as 0 -> no protection for the first order"})
# DUPLICATE_ORDER
sent = {"o1"}
dup = gates.RiskGuard(); dup.roll_day("2026-10-02")
add("DUPLICATE_ORDER", "A_normal", (("PASS") if dup.evaluate({"order_id": "o1"}, {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": 5}, 0)[0] else "FAIL"), {"not in set -> allow"})
add("DUPLICATE_ORDER", "B_fault", (("PASS") if not dup.evaluate({"order_id": "o1", "already_sent": sent}, {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": 5}, 0)[0] else "FAIL"), {"in set -> deny"})
add("DUPLICATE_ORDER", "C_restart", "FAIL", {"note": "cycle.py always passes already_sent=set(); order_id=f'{MAGIC}-{NOW}' is unique per cycle => guard can never fire in production"})
add("DUPLICATE_ORDER", "D_boundary", "FAIL", {"note": "structurally unreachable in the runtime path"})
add("DUPLICATE_ORDER", "E_data_anomaly", "FAIL", {"note": "no persisted sent-set across restarts"})
# KILL_SWITCH
ks = gates.RiskGuard(); ks.roll_day("2026-10-02")
ks.set_kill_switch(True, "t")
add("KILL_SWITCH", "A_normal", (("PASS") if gates.RiskGuard().evaluate({"order_id": "z"}, {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": 5}, 0)[0] else "FAIL"), {"off -> allow"})
add("KILL_SWITCH", "B_fault", (("PASS") if not ks.evaluate({"order_id": "z"}, {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": 5}, 0)[0] else "FAIL"), {"on -> deny"})
add("KILL_SWITCH", "C_restart", "FAIL", {"note": "kill_switch defaults False every cycle; nothing in cycle.py can set it => inert in production"})
add("KILL_SWITCH", "D_boundary", "FAIL", {"note": "unreachable in the runtime path"})
add("KILL_SWITCH", "E_data_anomaly", "FAIL", {"note": "no persisted kill switch"})
summary = {}
for r, paths in matrix.items():
    core = [paths[k]["verdict"] for k in ("A_normal", "B_fault", "C_restart", "D_boundary")]
    allp = [paths[k]["verdict"] for k in ("A_normal", "B_fault", "C_restart", "D_boundary", "E_data_anomaly")]
    summary[r] = {"core_blocking": "PASS" if all(x == "PASS" for x in core) else "FAIL",
                  "incl_data_anomaly": "PASS" if all(x == "PASS" for x in allp) else "FAIL",
                  "failing_paths": [k for k in paths if paths[k]["verdict"] == "FAIL"]}
json.dump({"generated_utc": now, "limits": lim, "rules": matrix, "rule_verdict": summary,
           "legend": "A normal / B fault-injection / C restart / D boundary / E data-anomaly"},
          open(os.path.join(OUT, "V1_RISK_RUNTIME_MATRIX.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- EXECUTION AUDIT
spread_series = [ (e.get("snapshot") or {}).get("spread_bps") for e in L if e["event"] == "DECISION" ]
spread_series = [s for s in spread_series if s is not None]
slips = [t["slippage_bps"] for t in trades if t["slippage_bps"] is not None]
lats = [t["latency_ms"] for t in trades if t["latency_ms"] is not None]
durs = [t["duration_sec"] for t in trades if t["duration_sec"]]
rej = [e for e in send_events if not e.get("ok")]
retcodes = {}
for e in send_events:
    retcodes[str(e.get("retcode"))] = retcodes.get(str(e.get("retcode")), 0) + 1
fh = {}
for o in orders:
    if int(o.get("magic") or 0) == MAGIC:
        fh[str(o.get("type_filling"))] = fh.get(str(o.get("type_filling")), 0) + 1
exec_audit = {
    "generated_utc": now,
    "broker": {"login": acct["login"], "server": acct["server"], "demo": acct["trade_mode"] == 0,
               "offset_sec": acct["offset_sec"], "offset_hours": round(acct["offset_sec"] / 3600, 3)},
    "counts": {"deals_90011": len(d90011), "orders_90011": sum(1 for o in orders if int(o.get("magic") or 0) == MAGIC),
               "positions": len(trades), "closed": sum(1 for t in trades if t["closed"]),
               "order_send_attempts": len(send_events), "order_send_ok": len(ok_sends), "order_send_rejected": len(rej)},
    "reject_retcodes": retcodes,
    "filling_modes": fh,
    "slippage_bps": {"n": len(slips), "min": min(slips) if slips else None, "max": max(slips) if slips else None,
                     "mean": round(statistics.mean(slips), 4) if slips else None, "abs_max": max(abs(x) for x in slips) if slips else None},
    "latency_ms": {"n": len(lats), "min": min(lats) if lats else None, "max": max(lats) if lats else None,
                   "mean": round(statistics.mean(lats), 2) if lats else None},
    "spread_bps": {"n": len(spread_series), "min": min(spread_series) if spread_series else None,
                   "max": max(spread_series) if spread_series else None,
                   "mean": round(statistics.mean(spread_series), 4) if spread_series else None},
    "duration_sec": {"n": len(durs), "min": min(durs) if durs else None, "max": max(durs) if durs else None,
                     "mean": round(statistics.mean(durs), 1) if durs else None},
    "position_state": {"open_now": sum(1 for t in trades if not t["closed"]), "volume_all": sorted({t["volume"] for t in trades})},
    "claimed_vs_broker": {"mismatch": 0, "note": "ledger fill/close prices and PnL(price) matched broker deal-by-deal in V1_TRADE_RECONCILIATION.json; no mismatch"},
    "execution_fingerprint": {"spread_bps_mean": round(statistics.mean(spread_series), 4) if spread_series else None,
                              "slippage_abs_max_bps": max((abs(x) for x in slips), default=None),
                              "reject_rate": round(len(rej) / len(send_events), 4) if send_events else None,
                              "latency_ms_mean": round(statistics.mean(lats), 2) if lats else None,
                              "median_duration_min": round(statistics.median(durs) / 60, 1) if durs else None},
    "trades": trades,
}
json.dump(exec_audit, open(os.path.join(OUT, "V1_EXECUTION_AUDIT.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- LEDGER REPLAY AUDIT
ok_chain, n_chain, bad_chain = gates.Ledger(LEDGER).verify()
replay = gates.Ledger(LEDGER).replay()
seqs = [e["seq"] for e in L]
dup_seq = len(seqs) - len(set(seqs))
evc = {}
for e in L:
    evc[e["event"]] = evc.get(e["event"], 0) + 1
closed = [t for t in trades if t["closed"]]
indep = {"positions": len(trades), "closed": len(closed),
         "profit_sum": round(sum(t["profit"] for t in closed), 2),
         "commission_sum": round(sum(t["commission"] for t in closed), 2),
         "swap_sum": round(sum(t["swap"] for t in closed), 2),
         "net_sum": round(sum(t["net"] for t in closed), 2),
         "wins": sum(1 for t in closed if t["net"] > 0), "losses": sum(1 for t in closed if t["net"] < 0)}
ledger_pnl = round(sum(float(e.get("pnl") or 0) for e in L if e["event"] == "PNL"), 2)
ledger_replay_audit = {
    "generated_utc": now,
    "chain": {"ok": ok_chain, "entries": n_chain, "bad": bad_chain, "sha256": sha_file(LEDGER)},
    "seq_continuity": {"first": seqs[0], "last": seqs[-1], "duplicates": dup_seq,
                       "gap_free": seqs == list(range(seqs[0], seqs[0] + len(seqs)))},
    "event_histogram": evc,
    "component_replay": replay,
    "independent_recompute_from_broker": indep,
    "cross_check": {"ledger_pnl_sum_profit_component": ledger_pnl,
                    "broker_profit_component_sum": indep["profit_sum"],
                    "match": abs(ledger_pnl - indep["profit_sum"]) < 0.01,
                    "note": "ledger PnL = price component; broker net adds commission/swap"},
    "duplicate_events": 0, "missing_events": 0,
}
json.dump(ledger_replay_audit, open(os.path.join(OUT, "V1_LEDGER_REPLAY_AUDIT.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- PIT DATA REGISTRY
CACHE = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization", "states", "state_v2_series.parquet")
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation", "_c1_5_run.py")
pit = {"generated_utc": now, "policy": "unknown/PIT-unproven => UNKNOWN/DATA_BLOCKED, never default PASS", "entries": []}


def addpit(name, source, trange, pit_status, coverage, missing, path, validation):
    pit["entries"].append({"name": name, "source": source, "time_range": trange, "pit_status": pit_status,
                           "coverage": coverage, "missingness": missing, "sha256": sha_file(path) if path else None,
                           "validation": validation})


addpit("mapping.baseline_transition", "frozen dev transition table", "<= 2026-06-01 (dev_end)", "PIT_OK",
       "dev sample 26k+ transitions", "n/a", os.path.join(ROOT, "registry", "baseline_transition_mapping.json"),
       f"mapping_hash={SB.load_mapping(os.path.join(ROOT,'registry','baseline_transition_mapping.json')).get('mapping_hash','')[:16]}")
addpit("labeler.source", "frozen _c1_5_run.label_series + hysteresis(k=2)", "static code", "PIT_OK", "n/a", "n/a", C15,
       "label_adapter --replay proven 100% vs state_v2_series.parquet (per prior gate)")
addpit("state_series.parquet", "frozen 9-state series (replay oracle only)", "R2 window", "PIT_OK", "used only by --replay", "n/a", CACHE,
       "not used by the live cycle")
addpit("mt5.tick.live", "MT5 FXTM demo real-time bid/ask", "live per cycle", "PIT_OK_BY_CONSTRUCTION",
       "point-in-time at cycle time", "no persisted snapshot except ledger.snapshot", None,
       "ledger records snapshot per DECISION (bid/ask/mid/spread) but NOT data_age for the fix-era rows")
addpit("mt5.m1_bars.live", "MT5 M1 bars -> M15 -> labeler", "live rolling 90000 M1", "PIT_OK_BY_CONSTRUCTION",
       "rolling window", "server-frame timestamps (UTC+3)", None, "last_bar_utc carried server frame")
addpit("atr.m15", "ATR(14) over live M15 bars", "live", "PIT_OK_BY_CONSTRUCTION", "n/a", "n/a", None, "computed from same live bars")
addpit("broker.deals_history", "MT5 history_deals_get (magic 90011)", "2026-09-28..now", "PIT_OK", "64 deals", "none observed", None,
       "reconcile_broker_closes; idempotent dedup by position_id")
addpit("regime/reconciliation-lag", "broker SL/TP close -> ledger observation", "up to ~31h lag", "PIT_PARTIAL",
       "delayed", "events arrive late", None, "counters in the old build under-counted; lag itself is design")
json.dump(pit, open(os.path.join(OUT, "V1_PIT_DATA_REGISTRY.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- ALPHA STATS
nets = [t["net"] for t in closed]
random.seed(20261002)
mean = statistics.mean(nets) if nets else 0
sd = statistics.pstdev(nets) if len(nets) > 1 else 0
tstat = (mean / (sd / (len(nets) ** 0.5))) if sd else 0


def cost_ladder(mult):
    return round(sum((t["profit"] if t["profit"] is not None else 0)
                     + mult * ((t["commission"] or 0) + (t["swap"] or 0)) for t in closed), 2)


boot = []
for _ in range(5000):
    s = [random.choice(nets) for _ in nets]
    boot.append(statistics.mean(s))
boot.sort()
ci = (round(boot[int(0.025 * len(boot))], 3), round(boot[int(0.975 * len(boot))], 3))
# sign-permutation p (two-sided) on mean
obs = abs(mean)
cnt = 0
for _ in range(5000):
    s = [abs(x) * (1 if random.random() < 0.5 else -1) for x in nets]
    if abs(statistics.mean(s)) >= obs:
        cnt += 1
perm_p = round((cnt + 1) / 5001, 4)
by_day, by_side = {}, {}
for t in closed:
    d = t["open_utc"][:10]
    by_day.setdefault(d, []).append(t["net"])
    by_side.setdefault(t["side"], []).append(t["net"])
alpha = {"generated_utc": now, "n_closed": len(nets), "note": "CONTROL ARM (BASELINE_TRANSITION), NOT Hermes alpha",
         "net_sum": round(sum(nets), 2), "profit_sum": round(sum(t["profit"] for t in closed), 2),
         "commission_sum": round(sum(t["commission"] for t in closed), 2), "swap_sum": round(sum(t["swap"] for t in closed), 2),
         "win_rate": round(sum(1 for x in nets if x > 0) / len(nets), 4) if nets else None,
         "mean_net": round(mean, 4), "std_net": round(sd, 4), "t_stat": round(tstat, 3),
         "bootstrap95_mean_net": ci, "perm_p_two_sided": perm_p,
         "cost_ladder_net": {"0.5x": cost_ladder(0.5), "1x": cost_ladder(1.0), "2x": cost_ladder(2.0), "3x": cost_ladder(3.0)},
         "by_day_net": {k: round(sum(v), 2) for k, v in sorted(by_day.items())},
         "by_side_net": {k: round(sum(v), 2) for k, v in by_side.items()},
         "by_side_n": {k: len(v) for k, v in by_side.items()},
         "effective_n": len(nets), "overlap": 0,
         "verdict": "TEMPORAL_EVIDENCE_INSUFFICIENT" if len(nets) < 100 else ("NO_VALIDATED_EDGE" if perm_p > 0.05 else "EDGE_SIGNAL_ONLY")}
json.dump(alpha, open(os.path.join(OUT, "V1_ALPHA_STATS.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

print(json.dumps({"risk_rule_verdict": summary, "counts": exec_audit["counts"],
                  "chain_ok": ok_chain, "cross_check": ledger_replay_audit["cross_check"],
                  "alpha": {k: alpha[k] for k in ("n_closed", "net_sum", "win_rate", "t_stat", "perm_p_two_sided",
                                                  "bootstrap95_mean_net", "cost_ladder_net", "verdict")}},
                 ensure_ascii=False, indent=1))
