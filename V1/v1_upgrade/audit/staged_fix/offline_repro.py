# -*- coding: utf-8 -*-
"""offline_repro.py — read-only offline reproduction + counterfactual for the V1 risk-guard wiring defect.

No production file is touched; nothing is written to the live ledger; no MT5 call; no order.

Old logic  : RiskGuard built fresh each cycle (counters 0) + slippage_bps=0 / data_age_seconds=0 hardcoded
             => only MAX_POSITION / SPREAD_LIMIT can ever fire.
New logic  : RiskGuard state rebuilt from the ledger CLOSE/PNL facts, real pnl + real inputs
             => MAX_DAILY_LOSS / MAX_CONSECUTIVE_LOSS are live.

Output: per-open counterfactual verdict and the count of "should have been rejected but was allowed".
"""
from __future__ import annotations
import json, os, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
RECON = os.path.join(ROOT, "audit", "V1_TRADE_RECONCILIATION.json")
SERVER_OFFSET = dt.timedelta(hours=3)      # FXTM demo server frame = UTC+3 (audit §9)
LIM_MDL, LIM_MCL, LIM_STALE = -20.0, 3, 900


def rows(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def srv2utc(s):
    return dt.datetime.fromisoformat(s) - SERVER_OFFSET


def main():
    R = rows(LEDGER)
    recon = json.load(open(RECON, encoding="utf-8"))
    net_by = {str(p["position_id"]): p.get("broker_net") for p in recon["reconciliation"]["per_trade"]}

    opens = [(dt.datetime.fromisoformat(e["ts_utc"]), str(e.get("order_id")))
             for e in R if e["event"] == "POSITION"]
    opens.sort()

    closes = []
    for e in R:
        if e["event"] != "PNL":
            continue
        pid = str(e.get("position_id"))
        utc = srv2utc(e["broker_time_utc"]) if e.get("broker_time_utc") else dt.datetime.fromisoformat(e["ts_utc"])
        price = float(e.get("pnl") or 0.0)
        net = net_by.get(pid)
        if net is None:                      # not yet in the audit snapshot -> price component - commission
            net = round(price - 0.2, 2)
        closes.append((utc, pid, price, float(net)))
    closes.sort()

    def simulate(basis, frame):
        out, day, daily, cons = [], None, 0.0, 0
        byday = defaultdict(lambda: {"opens": 0, "blocked": 0, "losses": 0})
        ci = 0
        for ts, oid in opens:
            oday = (ts - (SERVER_OFFSET if frame == "srv" else dt.timedelta())) .date().isoformat()
            # advance closes known before this open (by real close time, same frame)
            while ci < len(closes):
                cu, pid, price, net = closes[ci]
                cday = (cu if frame == "utc" else cu + SERVER_OFFSET).date().isoformat()
                if cu > ts:
                    break
                if cday != day:
                    day, daily, cons = cday, 0.0, 0
                v = price if basis == "price" else net
                daily += v
                cons = cons + 1 if v < 0 else 0
                byday[cday]["losses"] += 1
                ci += 1
            if oday != day:
                day, daily, cons = oday, 0.0, 0
            reasons = []
            if daily <= LIM_MDL:
                reasons.append("MAX_DAILY_LOSS")
            if cons >= LIM_MCL:
                reasons.append("MAX_CONSECUTIVE_LOSS")
            byday[oday]["opens"] += 1
            if reasons:
                byday[oday]["blocked"] += 1
            out.append({"open_utc": ts.isoformat(), "order_id": oid, "day": oday,
                        "daily": round(daily, 2), "cons": cons, "blocked": reasons})
        return out, dict(byday)

    print("=" * 78)
    print("opens (real ENTERs):", len(opens), " closes (realized):", len(closes))
    for basis in ("price", "net"):
        for frame in ("utc", "srv"):
            out, byday = simulate(basis, frame)
            nb = sum(1 for o in out if o["blocked"])
            print(f"\n--- basis={basis:5s} frame={frame:3s} : SHOULD-REJECT-BUT-ALLOWED = {nb} / {len(out)} opens ---")
            for d in sorted(byday):
                b = byday[d]
                print(f"    {d}: opens={b['opens']:2d} blocked={b['blocked']:2d} closes={b['losses']:2d}")
    print("\n--- per-open detail (basis=net, frame=utc) ---")
    out, _ = simulate("net", "utc")
    for o in out:
        tag = ",".join(o["blocked"]) if o["blocked"] else "allow"
        print(f"  {o['open_utc'][:19]}  {o['order_id']:>12}  day={o['day']}  daily={o['daily']:8.2f}  cons={o['cons']}  -> {tag}")


if __name__ == "__main__":
    main()
