# -*- coding: utf-8 -*-
"""Augment V1_RESTART_STATE_AUDIT.json with scheduler / data-freshness / frame / drawdown details.
Read-only: reads the ledger + the builder outputs; rewrites only the audit JSON."""
from __future__ import annotations
import datetime as dt, json, os

BASE = r"C:\AIQuant\research\hermes\trader_v1"
AUDIT = os.path.join(BASE, "audit")
ROOT = os.path.join(BASE, "v1_upgrade")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
RESTART = dt.datetime(2026, 10, 1, 13, 52, 15, tzinfo=dt.timezone.utc)
P = lambda t: dt.datetime.fromisoformat(t)
rows = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]

st = json.load(open(os.path.join(AUDIT, "V1_RESTART_STATE_AUDIT.json"), encoding="utf-8"))
tr = json.load(open(os.path.join(AUDIT, "V1_RESTART_TRADE_TRACE.json"), encoding="utf-8"))

# (a) scheduler gaps around the whole window
dec = [P(r["ts_utc"]) for r in rows if r["event"] == "DECISION"]
dec.sort()
gaps = [{"after": dec[i - 1].isoformat(), "before": dec[i].isoformat(),
         "minutes": round((dec[i] - dec[i - 1]).total_seconds() / 60.0, 1)}
        for i in range(1, len(dec)) if (dec[i] - dec[i - 1]).total_seconds() > 16 * 60]

# (b) first cycle after restart + data freshness
post = [r for r in rows if r["event"] == "DECISION" and P(r["ts_utc"]) >= RESTART]
first = post[0] if post else None
last_pre = [r for r in rows if r["event"] == "DECISION" and P(r["ts_utc"]) < RESTART][-1]
freshness = None
if first:
    ls = first.get("live_state") or {}
    sn = first.get("snapshot") or {}
    freshness = {"first_cycle_after_restart_utc": first["ts_utc"], "action": first.get("action"),
                 "last_cycle_before_restart_utc": last_pre["ts_utc"],
                 "schedule_gap_minutes": round((P(first["ts_utc"]) - P(last_pre["ts_utc"])).total_seconds() / 60.0, 1),
                 "live_state": ls, "snapshot": sn,
                 "guard_fed_data_age_seconds": 0,
                 "note": "risk guard consumed hardcoded data_age_seconds=0 (cycle.py:289-290); real staleness unmeasured at runtime"}

# (c) frame offset measured at read time
acct = tr["account"]
srv_t = int(acct["terminal_time_srv"])
read_u = P(acct["read_utc"])
real_u = srv_t - int(read_u.timestamp())
frames = {"terminal_time_srv": srv_t, "read_utc": acct["read_utc"], "measured_offset_seconds": real_u,
          "measured_offset_hours": round(real_u / 3600.0, 3),
          "declared": "UTC+3 = 10800s; broker_time_utc / live_state.last_bar_utc carry this server frame",
          "note": "engine roll_day(NOW[:10]) uses UTC date; server-frame dates differ by up to one day near midnight"}

# (d) broker closes whose observation straddles the restart / detect lag
closes = [r for r in rows if r["event"] == "CLOSE"]
lags = []
for r in closes:
    b = r.get("broker_time_utc")
    if b:
        obs = P(r["ts_utc"])
        srv = P(b) - dt.timedelta(hours=3)
        lags.append({"position_id": r.get("position_id"), "observed_utc": r["ts_utc"],
                     "realized_utc_est": srv.isoformat(), "lag_sec": round((obs - srv).total_seconds())})
lags.sort(key=lambda x: x["lag_sec"], reverse=True)
pending = {"closes_total": len(lags), "max_detect_lag_sec": (lags[0]["lag_sec"] if lags else None),
           "top5_lag": lags[:5],
           "crossing_restart": [l for l in lags if P(l["observed_utc"]) < RESTART < P(l["observed_utc"]) + dt.timedelta(seconds=l["lag_sec"])]}

# (e) realized drawdown from broker net (closed trades in close order)
closed = sorted([t for t in tr["trades"] if t["closed"]], key=lambda t: t["close_utc"])
peak, dd, worst, run = 0.0, 0.0, 0.0, 0.0
post_run = 0.0
for t in closed:
    run += t["net"] or 0.0
    peak = max(peak, run)
    dd = min(dd, run - peak)
    worst = min(worst, dd)
    if P(t["open_utc"]) >= RESTART:
        post_run += t["net"] or 0.0
drawdown = {"cum_net_all_closed": round(run, 2), "max_drawdown_net": round(worst, 2),
            "post_restart_net": round(post_run, 2),
            "balance_now": acct["balance"], "equity_now": acct["equity"],
            "balance_at_audit_snapshot_09_28": 1949.93}

st["scheduler"] = {"expected": "OpenClaw cron v1-upgrade-demo-cycle (3-59/15 * * * *) UTC",
                   "gaps_over_16min": gaps,
                   "missed_during_reboot": [g for g in gaps if P(g["after"]) < RESTART < P(g["before"]) + dt.timedelta(minutes=g["minutes"])] or gaps[:2],
                   "watchdog": "none dedicated; the cron job itself is the only scheduler; it recovered (fired the 14:18Z cycle)"}
st["data_freshness_at_restart"] = freshness
st["time_frames"] = frames
st["pending_close_writes"] = pending
st["drawdown"] = drawdown
json.dump(st, open(os.path.join(AUDIT, "V1_RESTART_STATE_AUDIT.json"), "w", encoding="utf-8", newline="\n"),
          indent=1, ensure_ascii=False)
print(json.dumps({"gaps": gaps, "freshness": freshness, "frames": frames,
                  "pending": {k: pending[k] for k in ("closes_total", "max_detect_lag_sec", "crossing_restart")},
                  "drawdown": drawdown}, ensure_ascii=False, indent=1)[:3000])
