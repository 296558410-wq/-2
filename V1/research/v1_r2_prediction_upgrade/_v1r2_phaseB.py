# -*- coding: utf-8 -*-
"""V1-R2 PHASE B: ten capability engines (PIT-strict) + old/new parallel replay + determinism + truncation tests.
Primary dataset: research/v3_alpha_discovery_r1/xauusd_m1_histdata.parquet (M1, real OHLC, UTC) -> M15 grid.
Read-only w.r.t. data. Writes ONLY under v1_r2_prediction_upgrade/. No order APIs."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
NOW = datetime.now(timezone.utc).isoformat()
P = {"M15_GRID": 15, "ATR_N": 20, "ER_N": 10, "PIVOT_L": 2, "PIVOT_R": 2, "CONFIRM_LAG": 2,
      "LEVEL_MAX": 40, "RANGE_W": 96, "TOUCH_TOL_ATR": 0.25, "TOUCH_W": 240, "RECOVERY_W": 8,
      "ABS_PEN": 0.15, "ABS_EFF_DEC": 0.40, "ABS_ACT_RISE": 0.30, "LIQ_Z": 1.5,
      "BREAK_CRIT": 4, "BREAK_ELEV": 2, "MOM_FAST": 0.8, "MOM_ACC": 0.35, "FAIL_CONFIRM": 2,
      "FAIL_RECLAIM": 6, "ATR_HI_PCTL": 80, "ATR_LO_PCTL": 20, "VOL_EXT": 2.5}
RUNS = os.path.join(UP, "v1_r2_research_runs")


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_m15():
    m = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m["dt"] = pd.to_datetime(m["dt_utc"], utc=True)
    m = m.set_index("dt").sort_index()
    o = m["open"].resample("15min").first()
    h = m["high"].resample("15min").max()
    l = m["low"].resample("15min").min()
    c = m["close"].resample("15min").last()
    df = pd.DataFrame({"o": o, "h": h, "l": l, "c": c}).dropna()
    return df


def indicators(df):
    c, h, l = df["c"], df["h"], df["l"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    df["atr20"] = tr.rolling(P["ATR_N"]).mean()
    df["atr4"] = tr.rolling(4).mean()
    df["ma20"] = c.rolling(20).mean()
    df["slope5"] = df["ma20"] - df["ma20"].shift(5)
    df["er10"] = (c - c.shift(P["ER_N"])).abs() / c.diff().abs().rolling(P["ER_N"]).sum()
    df["atr_pctl"] = df["atr20"].rolling(480, min_periods=100).apply(lambda x: (x[-1] >= x).mean() * 100, raw=True)
    df["rng_exp"] = df["atr4"] / df["atr20"]
    df["ret1"] = c.pct_change() * 1e4
    df["vel4"] = (c - c.shift(4)) / df["atr20"]
    df["vel4_prev"] = df["vel4"].shift(1)
    df["acc"] = df["vel4"] - df["vel4_prev"]
    df["eff3"] = (c - c.shift(3)).abs() / c.diff().abs().rolling(3).sum()
    df["eff3_prev"] = df["eff3"].shift(3)
    df["act3"] = df["atr4"] / df["atr20"]
    df["act3_prev"] = df["act3"].shift(3)
    df["range_last"] = (h - l)
    return df


def engines(df):
    """single PIT pass; every output at bar i uses only rows <= i"""
    n = len(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("o", "h", "l", "c"))
    atr = df["atr20"].to_numpy(float); atrp = df["atr_pctl"].to_numpy(float); er = df["er10"].to_numpy(float)
    slope = df["slope5"].to_numpy(float); rngx = df["rng_exp"].to_numpy(float)
    vel = df["vel4"].to_numpy(float); acc = df["acc"].to_numpy(float); ret1 = df["ret1"].to_numpy(float)
    eff, effp = df["eff3"].to_numpy(float), df["eff3_prev"].to_numpy(float)
    act, actp = df["act3"].to_numpy(float), df["act3_prev"].to_numpy(float)
    idx = df.index
    out = []
    levels = []            # dict: type, price, created_i, confirmed_i, touches[], pend[] 
    pend_rec = []          # pending recovery evaluations: (bar_i_of_touch, level_ref)
    prev_vec = None
    for i in range(n):
        A = atr[i]
        rec = {"i": i, "t": str(idx[i])}
        if not np.isfinite(A) or A <= 0:
            rec["regime"] = "UNKNOWN"; rec["next_state"] = "UNKNOWN"
            out.append(rec); continue
        # ---- A) regime
        reg = "UNKNOWN"
        if np.isfinite(atrp[i]):
            if atrp[i] < P["ATR_LO_PCTL"]:
                reg = "COMPRESSION"
            elif atrp[i] > P["ATR_HI_PCTL"]:
                reg = "EXPANSION"
        if reg == "UNKNOWN" and np.isfinite(er[i]):
            if er[i] > 0.35 and np.isfinite(slope[i]) and abs(slope[i]) > 0:
                reg = "TREND"
            elif er[i] < 0.20:
                reg = "RANGE"
        if np.isfinite(slope[i]) and np.isfinite(slope[i - 10]) if i >= 10 else False:
            if np.sign(slope[i]) != np.sign(slope[i - 10]) and np.isfinite(er[i]) and er[i] > 0.2 and reg in ("RANGE", "UNKNOWN"):
                reg = "REVERSAL"
        if np.isfinite(ret1[i]) and abs(ret1[i]) > 3 * A * (10000.0 / max(c[i], 1e-9)):
            reg = "EVENT_DRIVEN"
        rec["regime"] = reg
        # ---- B) key levels (confirm lag PIT)
        if i >= P["PIVOT_L"] + P["PIVOT_R"]:
            j = i - P["PIVOT_R"]
            win_h = h[j - P["PIVOT_L"]:j + P["PIVOT_R"] + 1]
            win_l = l[j - P["PIVOT_L"]:j + P["PIVOT_R"] + 1]
            if len(win_h) == P["PIVOT_L"] + P["PIVOT_R"] + 1 and h[j] == win_h.max() and i >= j + P["CONFIRM_LAG"]:
                levels.append({"type": "RESISTANCE", "price": float(h[j]), "created_i": j, "confirmed_i": i,
                                 "touches": [], "n": 0})
            if len(win_l) == P["PIVOT_L"] + P["PIVOT_R"] + 1 and l[j] == win_l.min() and i >= j + P["CONFIRM_LAG"]:
                levels.append({"type": "SUPPORT", "price": float(l[j]), "created_i": j, "confirmed_i": i,
                                 "touches": [], "n": 0})
        if i >= P["RANGE_W"]:
            rh = h[max(0, i - P["RANGE_W"]):i].max(); rl = l[max(0, i - P["RANGE_W"]):i].min()
            levels.append({"type": "RANGE_HIGH", "price": float(rh), "created_i": i, "confirmed_i": i, "touches": [], "n": 0})
            levels.append({"type": "RANGE_LOW", "price": float(rl), "created_i": i, "confirmed_i": i, "touches": [], "n": 0})
        tol = P["TOUCH_TOL_ATR"] * A
        # keep only levels confirmed <= i and within age/limit
        levels = [L for L in levels if L["confirmed_i"] <= i]
        # dedupe by (type, rounded price)
        seen = set(); ded = []
        for L in reversed(levels):
            key = (L["type"], round(L["price"] / max(A, 1e-9), 2))
            if key in seen:
                continue
            seen.add(key); ded.append(L)
        levels = ded[: P["LEVEL_MAX"] * 2]
        # ---- C) touches (PIT: only bars <= i; recovery resolved only when full window elapsed)
        nearest = None
        for L in levels:
            lo, hi = l[i], h[i]
            if hi >= L["price"] - tol and lo <= L["price"] + tol:
                pen = max(0.0, max(hi - L["price"], L["price"] - lo)) / A
                L["touches"].append({"i": i, "pen": float(pen)})
                L["n"] += 1
            # resolve recoveries whose window has fully elapsed by i
        # evaluate nearest (by distance)
        cand = sorted(levels, key=lambda L: abs(c[i] - L["price"]))[:6]
        if cand:
            L0 = cand[0]
            d = abs(c[i] - L0["price"]) / A
            ts_state = "NOT_APPLICABLE"
            if L0["n"] == 1:
                ts_state = "FIRST_TEST"
            elif L0["n"] == 2:
                ts_state = "RETEST"
            elif 3 <= L0["n"] <= 4:
                ts_state = "REPEATED_TEST"
            elif L0["n"] >= 5:
                # decay: compare avg pen of last 2 resolved touches vs earlier 2
                pens = [t["pen"] for t in L0["touches"]]
                rec_ratio = 0.0
                if len(pens) >= 4:
                    recent = np.mean(pens[-2:]); earlier = np.mean(pens[-4:-2]) or 1e-9
                    rec_ratio = max(0.0, (recent - earlier) / max(earlier, 1e-9))
                ts_state = "EXHAUSTION_CONFIRMED" if (rec_ratio > 0.5 and d < 1.0) else \
                           ("EXHAUSTION_BUILDING" if rec_ratio > 0.3 or d < 0.5 else "REPEATED_TEST")
            nearest = {"type": L0["type"], "price": round(L0["price"], 2), "touches": L0["n"],
                         "dist_atr": round(float(d), 3), "pen_last": round(float(L0["touches"][-1]["pen"]), 3) if L0["touches"] else 0.0,
                         "state": ts_state}
        rec["level"] = nearest
        # ---- D) absorption (PROXY_BAR)
        abs_state = "NONE"
        if np.isfinite(eff[i]) and np.isfinite(effp[i]) and np.isfinite(act[i]) and np.isfinite(actp[i]):
            eff_dec = (effp[i] - eff[i]) / max(effp[i], 1e-9)
            act_rise = (act[i] - actp[i]) / max(actp[i], 1e-9)
            if eff_dec >= P["ABS_EFF_DEC"] and act_rise >= P["ABS_ACT_RISE"]:
                abs_state = "POSSIBLE"
                if nearest and nearest["pen_last"] >= P["ABS_PEN"]:
                    abs_state = "STRONG"
            elif effp[i] > 0 and eff[i] < effp[i] * 0.6 and act[i] > actp[i] * 1.3:
                abs_state = "FAILED"
        rec["absorption"] = {"state": abs_state, "source": "PROXY_BAR", "direct_orderbook": False}
        # ---- E) liquidity (PROXY only where spread data exists; here UNKNOWN for long history)
        rec["liquidity"] = {"state": "UNKNOWN", "source": "PROXY_UNAVAILABLE_IN_LONG_HISTORY",
                              "note": "spread 仅在 2026-09 tick 窗口可用"}
        # ---- F) break risk (evidence set)
        ev = {}
        ev["E1_repeated_test"] = bool(nearest and nearest["touches"] >= 4)
        ev["E2_response_decay"] = bool(nearest and nearest["state"] in ("EXHAUSTION_BUILDING", "EXHAUSTION_CONFIRMED"))
        ev["E3_absorption_possible"] = abs_state in ("POSSIBLE", "STRONG")
        ev["E4_liquidity_withdrawal"] = False
        ev["E5_penetration"] = bool(nearest and nearest["pen_last"] >= P["ABS_PEN"])
        ev["E6_momentum_fast"] = bool(np.isfinite(vel[i]) and abs(vel[i]) > P["MOM_FAST"])
        cnt = sum(1 for v in ev.values() if v)
        br = "LOW" if cnt == 0 else "NORMAL" if cnt == 1 else "ELEVATED" if cnt < P["BREAK_CRIT"] else "CRITICAL"
        rec["break_risk"] = {"state": br, "evidence": {k: v for k, v in ev.items() if v}, "count": cnt}
        # ---- G) momentum
        mom = "UNKNOWN"
        if np.isfinite(vel[i]) and np.isfinite(acc[i]):
            if abs(vel[i]) < 0.3:
                mom = "SLOW"
            elif acc[i] > P["MOM_ACC"] and abs(vel[i]) > P["MOM_FAST"]:
                mom = "ACCELERATING"
            elif acc[i] < -P["MOM_ACC"] and abs(vel[i]) > 0:
                mom = "DECELERATING"
            elif abs(vel[i]) > P["MOM_FAST"] and np.isfinite(rngx[i]) and rngx[i] < 0.9:
                mom = "EXHAUSTING"
            else:
                mom = "NORMAL"
        rec["momentum"] = mom
        # ---- H) failed events (simplified PIT)
        rec["failed_event"] = "NONE"
        if nearest and i >= 3:
            nb = nearest["price"]
            if c[i - 1] > nb + P["ABS_PEN"] * A and c[i] < nb:
                rec["failed_event"] = "FAILED_BREAKOUT"
            elif c[i - 1] < nb - P["ABS_PEN"] * A and c[i] > nb:
                rec["failed_event"] = "FAILED_BREAKDOWN"
        # ---- I) state transition + J) counter evidence + K) next state
        lrel = "ABOVE" if (nearest and c[i] > nearest["price"]) else ("BELOW" if nearest else "NA")
        vec = (reg, lrel, (nearest or {}).get("state", "NA"), abs_state, mom, br)
        if prev_vec is None:
            trans = "INIT"
        elif vec[0] != prev_vec[0]:
            trans = "REGIME_CHANGED"
        elif vec[2] != prev_vec[2]:
            trans = "TOUCH_STATE_CHANGED"
        elif vec[3] != prev_vec[3]:
            trans = "ABSORPTION_CHANGED"
        elif vec[4] != prev_vec[4]:
            trans = "MOMENTUM_CHANGED"
        else:
            trans = "SAME_STATE"
        prev_vec = vec
        rec["transition"] = trans
        # counter evidence (relative to momentum direction)
        d = 1 if (np.isfinite(vel[i]) and vel[i] > 0) else (-1 if (np.isfinite(vel[i]) and vel[i] < 0) else 0)
        sup, cntr = [], []
        if mom in ("ACCELERATING",): sup.append("momentum_accelerating")
        if reg == "TREND": sup.append("regime_trend")
        if lrel == "ABOVE" and d > 0: sup.append("price_above_level_with_up_momentum")
        if abs_state in ("POSSIBLE", "STRONG"): cntr.append("absorption_detected")
        if nearest and nearest["state"] in ("EXHAUSTION_BUILDING", "EXHAUSTION_CONFIRMED"): cntr.append("touch_exhaustion")
        if br in ("ELEVATED", "CRITICAL"): cntr.append("break_risk_elevated")
        if mom == "DECELERATING": cntr.append("momentum_decelerating")
        if reg in ("COMPRESSION", "RANGE"): cntr.append("regime_range_or_compression")
        rec["counter_evidence"] = {"direction_hypothesis": ("LONG" if d > 0 else "SHORT" if d < 0 else "NONE"),
                                     "supporting": sup, "counter": cntr}
        # next state (frozen rules)
        ns, ndir, conf = "UNKNOWN", "NONE", "LOW"
        if br in ("ELEVATED", "CRITICAL") and abs_state in ("POSSIBLE", "STRONG"):
            ns = "REVERSION"; ndir = "SHORT" if lrel == "ABOVE" else "LONG"; conf = "MED"
        elif br == "CRITICAL" and nearest and nearest["state"] in ("EXHAUSTION_CONFIRMED",):
            ns = "REVERSION"; ndir = "SHORT" if lrel == "ABOVE" else "LONG"; conf = "HIGH"
        elif mom == "ACCELERATING" and reg == "TREND" and len(cntr) == 0 and d != 0:
            ns = "CONTINUATION"; ndir = "LONG" if d > 0 else "SHORT"; conf = "MED"
        elif reg in ("COMPRESSION",):
            ns = "HOLD"; ndir = "NONE"; conf = "LOW"
        elif nearest and nearest["state"] in ("FIRST_TEST", "RETEST") and reg == "RANGE":
            ns = "HOLD"; ndir = "NONE"; conf = "LOW"
        elif rec["failed_event"] == "FAILED_BREAKOUT":
            ns = "REVERSION"; ndir = "SHORT"; conf = "MED"
        elif rec["failed_event"] == "FAILED_BREAKDOWN":
            ns = "REVERSION"; ndir = "LONG"; conf = "MED"
        rec["next_state"] = {"state": ns, "direction": ndir, "confidence": conf,
                               "counter_count": len(cntr), "support_count": len(sup)}
        out.append(rec)
    return out


def main():
    os.makedirs(RUNS, exist_ok=True)
    t0 = datetime.now(timezone.utc)
    df = load_m15()
    df = indicators(df)
    states1 = engines(df)
    h1 = sha_obj([{k: s.get(k) for k in ("i", "t", "regime", "momentum", "next_state", "break_risk", "absorption")} for s in states1])
    states2 = engines(df)
    h2 = sha_obj([{k: s.get(k) for k in ("i", "t", "regime", "momentum", "next_state", "break_risk", "absorption")} for s in states2])
    deterministic = (h1 == h2)
    # truncation (anti-lookahead) test: recompute on slices, compare the last bar
    import random
    rnd = random.Random(20260926)
    n = len(df)
    samples = sorted(rnd.sample(range(2000, n - 5), 8))
    trunc = []
    for si in samples:
        sub = indicators(load_m15_slice(df, si))
        s_sub = engines(sub)
        a = {k: states1[si].get(k) for k in ("regime", "momentum", "next_state", "break_risk", "absorption", "transition")}
        b = {k: s_sub[-1].get(k) for k in ("regime", "momentum", "next_state", "break_risk", "absorption", "transition")}
        trunc.append({"i": si, "match": a == b, "full": a, "truncated": b})
    trunc_ok = all(x["match"] for x in trunc)
    # old/new parallel replay vs V1 recorded decisions
    replay = []
    if os.path.isdir(DEC):
        for f in sorted(os.listdir(DEC))[-200:]:
            try:
                d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                continue
            cyc = d.get("cycle")
            if not cyc:
                continue
            try:
                ts = pd.Timestamp(cyc.replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                continue
            pos = df.index.searchsorted(ts, side="right") - 1
            if pos < 100 or pos >= len(states1):
                continue
            s = states1[pos]
            replay.append({"cycle": cyc, "v1_decision": d.get("decision"), "v1_confidence": d.get("confidence"),
                             "v2_state": {"regime": s.get("regime"), "momentum": s.get("momentum"),
                                            "absorption": (s.get("absorption") or {}).get("state"),
                                            "break_risk": (s.get("break_risk") or {}).get("state"),
                                            "touch": (s.get("level") or {}).get("state"),
                                            "transition": s.get("transition")},
                             "v2_next_state": s.get("next_state"),
                             "why_changed": ([] if d.get("decision") == "WAIT" and (s.get("next_state") or {}).get("state") == "HOLD"
                                               else ["V1-R2 引入 touch/absorption/transition/counter 证据",
                                                       "方向比较: V1=%s vs V2=%s" % (d.get("decision"), (s.get("next_state") or {}).get("direction"))])})
    # write artifacts
    rdir = os.path.join(RUNS, "V1_R2_RUN_" + t0.strftime("%Y%m%dT%H%M%S"))
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, "v1_r2_states.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for s in states1:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(os.path.join(rdir, "parallel_replay.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in replay:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    rules = {"rules_version": "v1r2-r1-rules", "frozen_at_utc": NOW, "params": P, "registry_hash": None,
               "rule_notes": ["REGIME 判定优先级: COMPRESSION/EXPANSION(ATR 分位) → TREND/RANGE(ER) → REVERSAL → EVENT_DRIVEN",
                               "ABSORPTION 为 PROXY_BAR（无 DOM、无真实成交量）；liquidity 长历史为 UNKNOWN（spread 仅 tick 窗口）",
                               "BREAK_RISK 为证据计数（0/1/2-3/4+），非黑箱分数",
                               "NEXT_STATE 规则顺序固定；counter_evidence 必须同时输出支持/反对"]}
    rules["rules_hash"] = sha_obj({k: v for k, v in rules.items() if k != "rules_hash"})
    with open(os.path.join(UP, "registry", "v1_r2_engine_rules_frozen.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rules, fh, indent=1, ensure_ascii=False)
    summary = {"phase": "B", "dataset": {"source": "research/v3_alpha_discovery_r1/xauusd_m1_histdata.parquet",
                                            "m15_bars": int(len(df)), "range": [str(df.index[0]), str(df.index[-1])]},
                 "engines": {"REGIME": "ON", "KEY_LEVEL": "ON", "TOUCH_EXHAUSTION": "ON", "ABSORPTION": "PROXY_BAR",
                                "LIQUIDITY": "PROXY_UNAVAILABLE_IN_LONG_HISTORY(仅 tick 窗口可算)",
                                "BREAK_RISK": "ON", "MOMENTUM": "ON", "FAILED_EVENT": "ON_simplified",
                                "STATE_TRANSITION": "ON", "COUNTER_EVIDENCE": "ON", "NEXT_STATE": "ON"},
                 "states_written": len(states1), "parallel_replay_records": len(replay),
                 "DETERMINISTIC_TEST": "PASS" if deterministic else "FAIL", "hash_run1": h1[:16], "hash_run2": h2[:16],
                 "TRUNCATION_TEST": "PASS" if trunc_ok else "FAIL", "truncation_samples": trunc,
                 "rules_hash": rules["rules_hash"], "run_dir": os.path.relpath(rdir, REPO).replace("\\", "/"),
                 "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "V2_WRITE": 0, "V3_WRITE": 0},
                 "pending": ["walk-forward/时间切分评估", "ablation", "redundancy", "26 tests", "final report/verdict"],
                 "ts_utc": NOW}
    with open(os.path.join(UP, "reports", "V1_R2_PHASE_B_SUMMARY.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False, default=str)
    # ledger append
    lp = os.path.join(UP, "ledger", "v1_r2_prediction_ledger.jsonl")
    prev, seq = "GENESIS", 0
    for line in open(lp, encoding="utf-8"):
        if line.strip():
            o = json.loads(line); prev = o["record_hash"]; seq = o["seq"] + 1
    for kind, payload in (("ENGINE_RULES_FROZEN", rules), ("PHASE_B_STATES", {"n": len(states1), "h": h1}),
                            ("PARALLEL_REPLAY", {"n": len(replay)}), ("DETERMINISM_TEST", {"pass": deterministic}),
                            ("TRUNCATION_TEST", {"pass": trunc_ok})):
        body = json.dumps({"seq": seq, "ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "payload": payload},
                            sort_keys=True, ensure_ascii=False)
        hh = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
        with open(lp, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"seq": seq, "ts": datetime.now(timezone.utc).isoformat(), "kind": kind,
                                   "payload": payload, "prev_hash": prev, "record_hash": hh},
                                  sort_keys=True, ensure_ascii=False) + "\n")
        prev = hh; seq += 1
    print(json.dumps({k: summary[k] for k in ("states_written", "parallel_replay_records", "DETERMINISTIC_TEST",
                                                  "TRUNCATION_TEST", "rules_hash", "run_dir", "dataset")},
                       ensure_ascii=False, indent=1)[:1600], flush=True)
    print("truncation:", json.dumps(trunc, ensure_ascii=False)[:600], flush=True)


def load_m15_slice(df, upto):
    """recreate M15 bars limited to rows with index <= df.index[upto] (PIT slice)"""
    return df.iloc[: upto + 1].copy()


if __name__ == "__main__":
    main()
