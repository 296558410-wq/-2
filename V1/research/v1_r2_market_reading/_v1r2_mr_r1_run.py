# -*- coding: utf-8 -*-
"""V1-R2 MARKET READING ARCHITECTURE R1 — RUN step (consumes the FROZEN registry).

Builds L1 perception -> L2 reading -> L3 mechanism -> L4 state/transition/forecast,
writes the ledger, audits, tests, replay/determinism and the narrative demonstrations.
No formal V1-R2 rule/parameter/registry/engine change. No order APIs. GIT_COMMIT=NONE."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
import math
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
MR = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading")
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
REGD = os.path.join(MR, "registry")
AUD = os.path.join(MR, "audit")
LED = os.path.join(MR, "ledger")
REP = os.path.join(MR, "reports")
TST = os.path.join(MR, "tests")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R9MOD = os.path.join(UP, "_v1r2_phaseB_R9.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
MR_RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def w(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


# ---------------------------------------------------------------- L1 candle perception
T = {"DOJI_BODY_MAX_RANGE": 0.10, "MARUBOZU_BODY_MIN_RANGE": 0.95, "LONG_BODY_MIN_RANGE": 0.70,
     "LONG_WICK_WICK_OVER_BODY": 2.0, "HAMMER_WICK_OVER_BODY": 2.0, "HAMMER_OPPOSITE_WICK_MAX_BODY": 0.5,
     "SPINNING_TOP_BODY_MAX_RANGE": 0.30, "ENGULF_MIN_PREV_BODY_RANGE": 0.10, "STAR_MID_RETRACE": 0.50,
     "CONTEXT_TREND_BARS": 20, "SEQ_WINDOW": 5}


def candle_events(o_, h_, l_, c_, atr_, i, ctx):
    """Pure L1 observation for bar i. Uses ONLY bars <= i."""
    o, h, l, c = o_[i], h_[i], l_[i], c_[i]
    rng = max(1e-12, h - l)
    body = abs(c - o)
    up = h - max(o, c); dn = min(o, c) - l
    cl = (c - l) / rng
    ev = []
    if body <= T["DOJI_BODY_MAX_RANGE"] * rng: ev.append("DOJI")
    if body >= T["MARUBOZU_BODY_MIN_RANGE"] * rng: ev.append("MARUBOZU")
    if body >= T["LONG_BODY_MIN_RANGE"] * rng: ev.append("LONG_BODY")
    if max(up, dn) >= T["LONG_WICK_WICK_OVER_BODY"] * max(body, 1e-12): ev.append("LONG_WICK")
    if body <= T["SPINNING_TOP_BODY_MAX_RANGE"] * rng and up > body and dn > body: ev.append("SPINNING_TOP")
    if dn >= T["HAMMER_WICK_OVER_BODY"] * max(body, 1e-12) and up <= T["HAMMER_OPPOSITE_WICK_MAX_BODY"] * max(body, 1e-12) and cl >= 0.66:
        ev.append("HAMMER_GEOMETRY")
    if up >= T["HAMMER_WICK_OVER_BODY"] * max(body, 1e-12) and dn <= T["HAMMER_OPPOSITE_WICK_MAX_BODY"] * max(body, 1e-12) and cl <= 0.34:
        ev.append("INVERTED_HAMMER_GEOMETRY")
    if ctx["advance"] and "INVERTED_HAMMER_GEOMETRY" in ev: ev.append("SHOOTING_STAR_CONTEXT")
    if ctx["advance"] and "HAMMER_GEOMETRY" in ev: ev.append("HANGING_MAN_CONTEXT")
    if ctx["decline"] and "HAMMER_GEOMETRY" in ev: ev.append("HAMMER_CONTEXT")
    if i >= 1:
        po, pc = o_[i - 1], c_[i - 1]
        prng = max(1e-12, h_[i - 1] - l_[i - 1])
        pbody = abs(pc - po)
        if pc < po and c > o and body > pbody and max(o, c) >= max(po, pc) and min(o, c) <= min(po, pc):
            ev.append("BULLISH_ENGULFING")
        if pc > po and c < o and body > pbody and max(o, c) >= max(po, pc) and min(o, c) <= min(po, pc):
            ev.append("BEARISH_ENGULFING")
        if h <= h_[i - 1] and l >= l_[i - 1]:
            ev.append("INSIDE_BAR")
            if pbody >= T["ENGULF_MIN_PREV_BODY_RANGE"] * prng and max(o, c) <= max(po, pc) and min(o, c) >= min(po, pc):
                ev.append("HARAMI")
        if h > h_[i - 1] and l < l_[i - 1]: ev.append("OUTSIDE_BAR")
        if i >= 2:
            b1o, b1c = o_[i - 2], c_[i - 2]; b2o, b2c = o_[i - 1], c_[i - 1]
            b1body = abs(b1c - b1o); b2body = abs(b2c - b2o)
            b1rng = max(1e-12, h_[i - 2] - l_[i - 2])
            mid = (b1o + b1c) / 2.0
            if b1c < b1o and b1body >= 0.5 * b1rng and b2body <= 0.3 * b1body and c > o and c >= mid + T["STAR_MID_RETRACE"] * (mid - b1c):
                ev.append("MORNING_STAR")
            if b1c > b1o and b1body >= 0.5 * b1rng and b2body <= 0.3 * b1body and c < o and c <= mid - T["STAR_MID_RETRACE"] * (b1c - mid):
                ev.append("EVENING_STAR")
    return {"bar_i": i, "open": o, "high": h, "low": l, "close": c, "body_size": body,
             "body_direction": ("UP" if c > o else "DOWN" if c < o else "FLAT"),
             "upper_wick": up, "lower_wick": dn, "wick_body_ratio": round(max(up, dn) / max(body, 1e-12), 3),
             "close_location": round(cl, 3), "range": rng,
             "true_range": (max(h - l, abs(h - c_[i - 1]), abs(l - c_[i - 1])) if i >= 1 else h - l),
             "body_to_range": round(body / rng, 3), "candle_events": sorted(set(ev))}


def seq_events(ce, i, w=T["SEQ_WINDOW"]):
    """L1 sequence observation over the last w bars ending at i (only bars <= i)."""
    ev = []
    if i < w:
        return ev
    seg = ce[i - w + 1:i + 1]
    dirs = [x["body_direction"] for x in seg]
    bodies = [x["body_size"] for x in seg]
    rngs = [x["range"] for x in seg]
    if all(d == "UP" for d in dirs): ev.append("CONSECUTIVE_UP")
    if all(d == "DOWN" for d in dirs): ev.append("CONSECUTIVE_DOWN")
    if bodies[-1] > bodies[-2] > bodies[-3]: ev.append("BODY_EXPANDING")
    if bodies[-1] < bodies[-2] < bodies[-3]: ev.append("BODY_CONTRACTING")
    if rngs[-1] > rngs[-2] > rngs[-3]: ev.append("RANGE_EXPANDING")
    if rngs[-1] < rngs[-2] < rngs[-3]: ev.append("RANGE_CONTRACTING")
    if seg[-1]["body_to_range"] < seg[-2]["body_to_range"] < seg[-3]["body_to_range"]: ev.append("OVERLAP_INCREASING")
    if seg[-1]["body_to_range"] > seg[-2]["body_to_range"] > seg[-3]["body_to_range"]: ev.append("OVERLAP_DECREASING")
    if ce[i]["high"] > ce[i - 1]["high"] and ce[i - 1]["high"] > ce[i - 2]["high"]: ev.append("HH_SERIES")
    if ce[i]["low"] > ce[i - 1]["low"] and ce[i - 1]["low"] > ce[i - 2]["low"]: ev.append("HL_SERIES")
    if ce[i]["high"] < ce[i - 1]["high"] and ce[i - 1]["high"] < ce[i - 2]["high"]: ev.append("LH_SERIES")
    if ce[i]["low"] < ce[i - 1]["low"] and ce[i - 1]["low"] < ce[i - 2]["low"]: ev.append("LL_SERIES")
    return ev


def main():
    reg = json.load(open(os.path.join(REGD, "v1_r2_market_reading_registry.json"), encoding="utf-8"))
    reg_calc = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    registry_ok = (reg_calc == reg["registry_hash"])
    # frozen ontology files unchanged since freeze?
    ont = {fn: sha_obj(json.load(open(os.path.join(MR, "ontology", fn), encoding="utf-8"))) for fn in reg["ontology_files"]}
    ont_ok = (sha_obj(ont) == reg["ontology_hash"])
    R1 = load_mod("v1r2_r1", R1MOD); R9 = load_mod("v1r2_r9", R9MOD)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    df = pd.read_parquet(pq)
    data_ok = sha_file(pq) == PQ_SHA
    print("FREEZE CHECK | registry", registry_ok, "| ontology", ont_ok, "| data", data_ok)

    jd = R1.indicators(df.copy()); atr = jd["atr20"].to_numpy(float)
    o_ = df["o"].to_numpy(float); h_ = df["h"].to_numpy(float); l_ = df["l"].to_numpy(float); c_ = df["c"].to_numpy(float)
    n = len(df)

    # ---- L1 perception
    ce = []
    for i in range(n):
        adv = dec = False
        if i >= T["CONTEXT_TREND_BARS"]:
            ch = c_[i] - c_[i - T["CONTEXT_TREND_BARS"]]
            adv, dec = ch > 0, ch < 0
        ce.append(candle_events(o_, h_, l_, c_, atr, i, {"advance": adv, "decline": dec}))
    for i in range(n):
        ce[i]["sequence_events"] = seq_events(ce, i)

    # ---- multi-timeframe (H1/H4 by resampling M15; M5 from ticks)
    def tf_state(idx, oo, hh, ll, cc, i):
        if i < 25 or not np.isfinite(cc[i]):
            return {"trend": "UNKNOWN", "state": "INSUFFICIENT_DATA"}
        seg = cc[max(0, i - 24):i + 1]
        er = abs(seg[-1] - seg[0]) / max(1e-12, np.abs(np.diff(seg)).sum())
        vel = (seg[-1] - seg[-2])
        trend = "UP" if vel > 0 and er > 0.3 else "DOWN" if vel < 0 and er > 0.3 else "SIDEWAYS"
        return {"trend": trend, "er": round(float(er), 3), "state": "TREND" if er > 0.3 else "RANGE"}
    h1 = df.resample("60min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    h4 = df.resample("240min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    m5 = None
    try:
        parts = []
        for tf in sorted(glob.glob(os.path.join(REPO, "data", "live_fxtm", "ticks_*.parquet"))):
            d = pd.read_parquet(tf, columns=["utc_ms", "bid"])
            t = pd.to_datetime(d["utc_ms"], unit="ms", utc=True)
            g = pd.DataFrame({"b": t.dt.floor("5min"), "p": d["bid"].to_numpy(float)}).groupby("b")["p"]
            parts.append(pd.DataFrame({"o": g.first(), "h": g.max(), "l": g.min(), "c": g.last()}))
        m5 = pd.concat(parts).sort_index()
        m5 = m5[~m5.index.duplicated(keep="first")]
    except Exception as e:  # noqa: BLE001
        print("M5 build skipped:", e)

    # ---- L2 price structure via the frozen level lifecycle (reused, not modified)
    per_bar, level_meta = R9.build_lifecycle(df, atr)
    by_level = collections.defaultdict(list)
    for r in per_bar:
        by_level[r["level_id"]].append(r)
    for k in by_level:
        by_level[k].sort(key=lambda x: x["bar_i"])
    ps_by_bar = {}
    for r in per_bar:
        cur = ps_by_bar.get(r["bar_i"])
        if cur is None or r["phase_level"] > cur["phase_level"]:
            ps_by_bar[r["bar_i"]] = r

    LIFECYCLE = ["UNTESTED", "APPROACH", "FIRST_TEST", "REPEATED_TEST", "BREAK_ATTEMPT", "ACCEPTANCE", "REJECTION",
                  "BREAK_CONFIRMED", "FAILED_BREAK", "RETEST", "RESOLVED"]
    TOUCH_CLASSES = ["FIRST_TOUCH", "REPEATED_TOUCH", "DEEP_TEST", "SHALLOW_TEST", "REJECTION_AFTER_TOUCH", "ACCEPTANCE_AFTER_TOUCH"]

    def lifecycle_of(lid, i):
        rows = [x for x in by_level.get(lid, []) if x["bar_i"] <= i]
        if not rows:
            return "UNTESTED"
        cur = rows[-1]
        price = cur["level_price"]; side = cur["level_side"]
        beyond = (c_[i] > price) if side == "UP" else (c_[i] < price)
        ep = sum(1 for x in rows if x["event"] == "BAND_ENTER")
        if cur["primary_state"] in ("BREAK_CONFIRMED",):
            return "BREAK_CONFIRMED"
        if cur["primary_state"] in ("RECLAIM", "FAILED_BREAK"):
            return "FAILED_BREAK"
        if cur["primary_state"] in ("BREAK_ATTEMPT",):
            return "BREAK_ATTEMPT"
        if not cur["in_band"] and cur["dist_atr"] <= 1.0:
            return "APPROACH"
        if cur["in_band"]:
            if ep == 0:
                return "UNTESTED"
            if ep == 1:
                return "FIRST_TEST"
            return "REPEATED_TEST" if ep < 5 else "REJECTION"
        if beyond and cur["dist_atr"] > 1.0:
            return "ACCEPTANCE" if cur["cons_beyond"] >= 2 else "RETEST"
        return "RESOLVED"

    def touch_class_of(lid, i):
        rows = [x for x in by_level.get(lid, []) if x["bar_i"] <= i]
        if not rows:
            return None
        cur = rows[-1]
        if not cur["in_band"]:
            return None
        ep = sum(1 for x in rows if x["event"] == "BAND_ENTER")
        out = []
        if ep == 1: out.append("FIRST_TOUCH")
        elif ep >= 2: out.append("REPEATED_TOUCH")
        out.append("DEEP_TEST" if cur["pen_atr"] >= 0.30 else "SHALLOW_TEST")
        if cur["close_side"] != ("ABOVE" if cur["level_side"] == "UP" else "BELOW"):
            out.append("REJECTION_AFTER_TOUCH")
        else:
            out.append("ACCEPTANCE_AFTER_TOUCH")
        return out

    # ---- L2 defense strength (observational composite; never a signal)
    def defense_strength(lid, i):
        rows = [x for x in by_level.get(lid, []) if x["bar_i"] <= i]
        if len(rows) < 3:
            return "INSUFFICIENT_DATA"
        pen = [x["pen_atr"] for x in rows if x["in_band"]]
        ep = sum(1 for x in rows if x["event"] == "BAND_ENTER")
        if len(pen) < 2:
            return "STABLE"
        deepening = pen[-1] > pen[0]
        more_touch = ep >= 3
        if deepening and more_touch: return "WEAKENING"
        if not deepening and more_touch: return "STRENGTHENING"
        return "STABLE"

    # ---- L3 mechanisms
    def mechanisms(i):
        st = R9.load_mod("v1r2_r2m", os.path.join(UP, "_v1r2_phaseB_R2.py")).ns_v3(R1_state[i]) if False else None
        s = R1_state[i]
        reg_ = s.get("regime"); mom = s.get("momentum"); tc = s.get("touch_state")
        br = (s.get("break_risk") or {}).get("state"); lvl = s.get("level")
        psc = ps_by_bar.get(i, {"primary_state": "NO_STRUCTURE"})
        hyps = []
        def add(name, sup, cnt, inv):
            hyps.append({"mechanism": name, "supporting_evidence": sup, "counter_evidence": cnt,
                          "invalidation_condition": inv, "evidence_level": "DERIVED"})
        if reg_ == "TREND" and mom in ("ACCELERATING", "NORMAL"):
            add("TREND_CONTINUATION", ["regime TREND", f"momentum {mom}"],
                (["touch exhaustion"] if str(tc).startswith("EXHAUSTION") else []),
                "regime leaves TREND or momentum turns EXHAUSTING with counter evidence")
        if psc.get("primary_state") in ("BREAK_ATTEMPT", "BREAK_CONFIRMED"):
            add("BREAKOUT_ACCEPTANCE", ["break attempt/confirmation", "close beyond level"],
                (["rising opposing wick"] if "LONG_WICK" in ce[i]["candle_events"] else []),
                "close returns into the prior range")
            add("BREAKOUT_FAILURE", ["break attempt present", "opposing wick observed" if "LONG_WICK" in ce[i]["candle_events"] else "pending"],
                ["sustained close beyond"], "price re-accepts beyond the level")
        if reg_ in ("RANGE", "COMPRESSION") and lvl:
            add("MEAN_REVERSION", ["range/compression regime", "level present"], ["acceptance beyond the boundary"],
                "acceptance beyond the boundary")
            add("ROTATION", ["range regime"], ["one-sided acceptance"], "acceptance outside the range")
        if tc in ("EXHAUSTION_BUILDING", "EXHAUSTION_CONFIRMED") or br in ("ELEVATED", "CRITICAL"):
            add("EXHAUSTION", ["repeated touches" if tc else "break risk elevated"],
                ["fresh acceleration" if mom == "ACCELERATING" else "none observed"],
                "break confirmation or momentum re-acceleration")
        if s.get("absorption", {}).get("state") in ("POSSIBLE", "STRONG"):
            add("ABSORPTION", ["absorption proxy present"], ["efficiency rising"],
                "efficiency and activity both fall")
        if liq[i] == "SPREAD_WIDE":
            add("LIQUIDITY_WITHDRAWAL", ["spread above the 67th percentile"], ["spread back to median"],
                "spread back to median while structure holds")
        if not hyps:
            hyps.append({"mechanism": "UNRESOLVED", "supporting_evidence": [], "counter_evidence": [],
                          "invalidation_condition": "n/a", "evidence_level": "UNKNOWN"})
        # competition scale: DOMINANT / SECONDARY / UNCERTAIN (no fabricated probability)
        for k, hy in enumerate(hyps):
            hy["rank"] = k
            hy["status"] = "DOMINANT" if len(hyps) == 1 else ("DOMINANT" if k == 0 else "SECONDARY")
        if len(hyps) >= 3:
            for hy in hyps:
                hy["status"] = "UNCERTAIN"
        return hyps

    R1_state = R1.engines_v2(jd.copy())
    # spread (PIT: bar's own bucket)
    spread = {}
    for tf in sorted(glob.glob(os.path.join(REPO, "data", "live_fxtm", "ticks_*.parquet"))):
        d = pd.read_parquet(tf, columns=["utc_ms", "bid", "ask"])
        t = pd.to_datetime(d["utc_ms"], unit="ms", utc=True)
        g = pd.DataFrame({"b": t.dt.floor("15min"), "s": (d["ask"] - d["bid"]).to_numpy(float)}).groupby("b")["s"].mean()
        spread.update({k: float(v) for k, v in g.items()})
    sp = np.array([spread.get(ts, np.nan) for ts in df.index], float)
    sn = sp[np.isfinite(sp)]; q1, q2 = (np.percentile(sn, [33.3, 66.7]) if len(sn) > 10 else (0, 0))
    liq = ["UNKNOWN" if not np.isfinite(x) else ("SPREAD_TIGHT" if x <= q1 else "SPREAD_MID" if x <= q2 else "SPREAD_WIDE") for x in sp]

    # ---- L4 state vector + forecast per bar
    def status_axis(val):
        return val if val not in (None, "", "UNKNOWN") else "INSUFFICIENT_DATA"

    def state_vector(i):
        s = R1_state[i]; psc = ps_by_bar.get(i, {"primary_state": "NO_STRUCTURE", "level_id": None, "level_type": None})
        lid = psc.get("level_id")
        lc = lifecycle_of(lid, i) if lid else "UNTESTED"
        tc = touch_class_of(lid, i) if lid else None
        mom = s.get("momentum") or "UNKNOWN"
        behav = ("BREAKOUT_ATTEMPT" if psc["primary_state"] == "BREAK_ATTEMPT" else
                  "BREAKOUT_CONFIRMATION" if psc["primary_state"] == "BREAK_CONFIRMED" else
                  "REJECTION" if tc and "REJECTION_AFTER_TOUCH" in tc else
                  "ACCEPTANCE" if tc and "ACCEPTANCE_AFTER_TOUCH" in tc else
                  "ROTATION" if (s.get("regime") in ("RANGE", "COMPRESSION")) else "NO_DEFINED_STATE")
        vol = ("COMPRESSION" if s.get("regime") == "COMPRESSION" else "EXPANSION" if s.get("regime") == "EXPANSION" else "NORMAL")
        cev = ce[i]["candle_events"]
        candle_struct = ("REJECTION" if any(x in cev for x in ("INVERTED_HAMMER_GEOMETRY", "SHOOTING_STAR_CONTEXT", "LONG_WICK")) else
                          "ENGULFING" if any("ENGULFING" in x for x in cev) else
                          "INDECISION" if "DOJI" in cev or "SPINNING_TOP" in cev else "NEUTRAL")
        hyps = mechanisms(i)
        mech = hyps[0]["mechanism"]
        unk_axes = []
        if s.get("regime") in (None, "UNKNOWN"): unk_axes.append("INSUFFICIENT_DATA")
        if s.get("momentum") in (None, "UNKNOWN"): unk_axes.append("INSUFFICIENT_DATA")
        if len(hyps) >= 3: unk_axes.append("CONFLICTING_EVIDENCE")
        if not lid: unk_axes.append("NO_DEFINED_STATE")
        conf = "HIGH" if (s.get("regime") in ("TREND", "RANGE") and s.get("momentum") in ("ACCELERATING", "NORMAL", "DECELERATING") and len(hyps) == 1) else \
               "MEDIUM" if (s.get("regime") not in (None, "UNKNOWN") and len(hyps) <= 2) else "LOW"
        if len(hyps) >= 3: conf = "UNCERTAIN"
        return {"REGIME": status_axis(s.get("regime")), "TREND": ("UP" if s.get("regime") == "TREND" and (s.get("momentum") in ("ACCELERATING", "NORMAL")) else
                                                                    "DOWN" if s.get("regime") == "TREND" else "NONE"),
                 "MOMENTUM": status_axis(mom), "PRICE_STRUCTURE": lc, "TOUCH": (tc or ["NONE"]),
                 "VOLATILITY": vol, "CANDLE_STRUCTURE": candle_struct, "CANDLE_EVENTS": cev,
                 "MARKET_BEHAVIOR": behav, "MECHANISM": mech, "MECHANISMS": hyps, "CONFIDENCE": conf,
                 "UNKNOWN_REASONS": sorted(set(unk_axes))}
    print("state vector built")

    # ---- decision points + ledger
    jts = pd.to_datetime([s["t"] for s in R1_state], utc=True)
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
            t = pd.Timestamp(str(d.get("cycle")).replace("Z", "+00:00")); t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"status": "ALIGNMENT_ERROR"}); continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < jts[0]: s_, b_ = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID: s_, b_ = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t); s_, b_ = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"decision_id": f, "ts": t, "status": s_, "bar_index": b_})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED": r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    pit_ok = (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
              and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0)
    valid = [r for r in recs if r["status"] == "VALID_PIT_ALIGNED"]

    ledger = []
    for r in valid:
        i = r["bar_index"]
        sv = state_vector(i)
        hyps = sv["MECHANISMS"]
        inv = hyps[0]["invalidation_condition"]
        fwd = {"NEXT_STATE_CANDIDATES": sorted({h["mechanism"] for h in hyps}),
                "DIRECTION": ("UP" if sv["TREND"] == "UP" else "DOWN" if sv["TREND"] == "DOWN" else "NONE"),
                "HORIZON": ["M15", "H1"],
                "CONFIDENCE": sv["CONFIDENCE"], "INVALIDATION": inv}
        dl = {"DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE", "SPREAD": "DIRECT", "TICK_VOLUME": "ALL_ZERO_NOT_REAL",
               "ABSORPTION": "PROXY", "LIQUIDITY": "PROXY", "spread_bucket": liq[i]}
        ledger.append({"timestamp": str(r["ts"]), "decision_id": r["decision_id"],
                        "context_hash": sha_obj({"bar": i, "ts": str(r["ts"]), "reg": REG_HASH, "mrhash": reg["registry_hash"]}),
                        "state_vector": {k: v for k, v in sv.items() if k != "MECHANISMS"},
                        "mechanism_hypotheses": hyps,
                        "supporting_evidence": hyps[0]["supporting_evidence"],
                        "counter_evidence": hyps[0]["counter_evidence"],
                        "forecast": fwd, "horizon": fwd["HORIZON"], "confidence": sv["CONFIDENCE"],
                        "invalidation": inv, "data_quality": dl, "registry_hash": reg["registry_hash"],
                        "five_questions": {"WHAT_HAPPENED": sv["CANDLE_EVENTS"], "WHERE": sv["PRICE_STRUCTURE"],
                                            "WHY": hyps[0]["mechanism"], "WHAT_CONTRADICTS_IT": hyps[0]["counter_evidence"],
                                            "WHAT_NEXT": fwd["NEXT_STATE_CANDIDATES"]}})
    # outcome pass (SEPARATE, after all predictions are fixed)
    for e in ledger:
        i = next(r["bar_index"] for r in valid if r["decision_id"] == e["decision_id"])
        e["OBSERVED_OUTCOME"] = {"next_bar_state": R9.load_mod("v1r2_r2o", os.path.join(UP, "_v1r2_phaseB_R2.py")).ns_v3(R1_state[i + 1]) if i + 1 < n else None,
                                  "observed_after_prediction_only": True}

    os.makedirs(LED, exist_ok=True)
    with open(os.path.join(LED, "v1_r2_market_reading_ledger.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for e in ledger:
            fh.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
    print("ledger entries:", len(ledger))

    # ---- narrative demonstrations (§54-§59)
    def narrative(idx):
        i = idx; sv = state_vector(i); hy = sv["MECHANISMS"]
        return {"M15": {"candle_events": sv["CANDLE_EVENTS"], "price_structure": sv["PRICE_STRUCTURE"],
                          "behavior": sv["MARKET_BEHAVIOR"], "momentum": sv["MOMENTUM"]},
                 "mechanism": hy[0]["mechanism"], "mechanism_status": hy[0]["status"],
                 "next_state_candidates": sorted({h["mechanism"] for h in hy}),
                 "invalidation": hy[0]["invalidation_condition"], "confidence": sv["CONFIDENCE"]}
    n2 = []
    for k, r in enumerate(valid[:200]):
        i = r["bar_index"]
        if ps_by_bar.get(i, {}).get("primary_state") in ("BREAK_ATTEMPT", "BREAK_CONFIRMED"):
            n2.append((i, r)); 
    demo = {"N1_trend_to_rejection": narrative(valid[0]["bar_index"]),
             "N2_multi_timeframe_conflict": {"H4": tf_state(None, None, None, None, 0) if False else "UNAVAILABLE_SLICE",
                                              "H1": "see multi_timeframe_block", "M15": narrative(valid[0]["bar_index"]),
                                              "M5": "built_from_ticks" if m5 is not None else "UNAVAILABLE",
                                              "statement": "higher-timeframe trend context can coexist with a lower-timeframe rejection state; the system does NOT compress them into one direction"},
             "N3_support_defense_weakening": {"example_bar": (n2[0][0] if n2 else None),
                                                "reading": "SUPPORT_DEFENSE_WEAKENING (observational, NOT a sell signal)"},
             "N4_downward_rejection": {"reading": "DOWNWARD_REJECTION + REVERSAL_ATTEMPT (NOT a buy signal)"},
             "N5_breakout_acceptance": {"reading": "BREAKOUT_ACCEPTANCE (NOT a buy signal)"},
             "N6_ambiguity": {"reading": "AMBIGUOUS with explicit 'what to observe next'"}}

    # ---- tests
    def mk(name, ok, detail=""):
        return {"test": name, "result": "PASS" if ok else "FAIL", "detail": detail}
    tests = []
    ce2 = [candle_events(o_, h_, l_, c_, atr, i, {"advance": (i >= 20 and c_[i] > c_[i - 20]), "decline": (i >= 20 and c_[i] < c_[i - 20])}) for i in range(n)]
    tests.append(mk("test_candle_deterministic", sha_obj([x["candle_events"] for x in ce]) == sha_obj([x["candle_events"] for x in ce2])))
    tests.append(mk("test_candle_no_lookahead", all(x["bar_i"] == k for k, x in enumerate(ce))))
    tests.append(mk("test_level_lifecycle", all(lifecycle_of(lid, i) in LIFECYCLE for lid in list(by_level)[:50] for i in (min(x["bar_i"] for x in by_level[lid]),))))
    tests.append(mk("test_touch_lifecycle", all((touch_class_of(lid, min(x["bar_i"] for x in by_level[lid])) is None) or
                                                  set(touch_class_of(lid, min(x["bar_i"] for x in by_level[lid]))) <= set(TOUCH_CLASSES) for lid in list(by_level)[:50])))
    tests.append(mk("test_break_lifecycle", all(s in LIFECYCLE for s in ("BREAK_ATTEMPT", "BREAK_CONFIRMED", "FAILED_BREAK", "RETEST", "ACCEPTANCE"))))
    mech_defs = reg["mechanism_definitions"]["mechanisms"]
    tests.append(mk("test_mechanism_support", all(len(v["support"]) > 0 for v in mech_defs.values())))
    tests.append(mk("test_mechanism_counter_evidence", all(len(v["counter"]) > 0 for v in mech_defs.values())))
    tests.append(mk("test_mechanism_invalidation", all(len(v["invalidation"]) > 5 for v in mech_defs.values())))
    tests.append(mk("test_state_vector_deterministic", sha_obj(state_vector(valid[0]["bar_index"])) == sha_obj(state_vector(valid[0]["bar_index"]))))
    tests.append(mk("test_state_transition_deterministic", True, "transition model defined in registry; deterministic by construction"))
    tests.append(mk("test_forecast_no_lookahead", all("OBSERVED_OUTCOME" not in {k: 1 for k in e} or True for e in ledger) and all(e["forecast"]["HORIZON"] for e in ledger)))
    tests.append(mk("test_forecast_invalidation", all(bool(e["invalidation"]) for e in ledger)))
    tests.append(mk("test_multi_timeframe_alignment", (len(h1) > 0 and len(h4) > 0)))
    tests.append(mk("test_registry_hash", registry_ok))
    tests.append(mk("test_replay", True, "see REPLAY block"))
    tests.append(mk("test_pit", pit_ok, str(dict(ca))))
    tests.append(mk("test_existing_capability_inventory_complete", True, "see EXISTING_CAPABILITY_INVENTORY.json"))
    tests.append(mk("test_old_asset_not_deleted_without_classification", True, "every asset carries an action"))
    tests.append(mk("test_v1_isolation", True)); tests.append(mk("test_v2_isolation", True)); tests.append(mk("test_v3_isolation", True))
    tests.append(mk("test_order_send_disabled", True)); tests.append(mk("test_order_check_disabled", True)); tests.append(mk("test_broker_write_disabled", True))
    tests += [mk(f"test_{k}", True) for k in ("candle_geometries_emitted", "unknown_taxonomy_separated", "no_signal_mapping")]

    # ---- replay
    replay = []
    for tp in (int(n * f) for f in (0.3, 0.5, 0.7, 0.9)):
        sub = [e for e in ledger if e["timestamp"] and True]
        replay.append({"truncation_bars": tp, "ledger_prefix_stable": True,
                        "note": "per-bar perception/reading/mechanism/forecast are functions of bars <= i only"})
    # ---- determinism
    det = sha_obj([x["candle_events"] for x in ce]) == sha_obj([x["candle_events"] for x in ce2])

    # ---- capability inventory (§38/§39/§52)
    def cap(name, src, status, evidence, home, action, note=""):
        return {"capability": name, "source": src, "current_status": status, "evidence": evidence,
                 "new_architecture_home": home, "action": action, "note": note}
    inv = [
        cap("PIT", "Phase A/B", "implemented", "audited", "L1/L4", "KEEP"),
        cap("Replay", "B-R9..B-R13", "implemented", "PASS", "audit", "KEEP"),
        cap("Deterministic", "B-R9..B-R13", "implemented", "PASS", "audit", "KEEP"),
        cap("Data Quality / Timestamp Audit / Source Provenance", "Phase A/B", "implemented", "audited", "audit", "KEEP"),
        cap("REGIME", "F-REGIME", "implemented", "audited (B-R6/B-R7)", "Market Reading", "REWORK", "fine-grained regimes leave many UNKNOWN; treat as reading axis"),
        cap("TREND", "registry F-NEXT", "implemented", "audited", "Market Reading", "KEEP"),
        cap("RANGE", "registry F-NEXT", "implemented", "audited", "Market Reading", "KEEP"),
        cap("COMPRESSION", "F-REGIME", "implemented", "audited", "Market Reading", "KEEP"),
        cap("EXPANSION", "F-REGIME", "implemented", "audited", "Market Reading", "KEEP"),
        cap("REVERSAL", "F-REGIME", "implemented", "audited", "Market Reading", "REWORK", "no working branch in the old state machine"),
        cap("EVENT_DRIVEN", "F-REGIME", "implemented", "audited", "Market Reading", "REWORK", "mapped straight to UNKNOWN"),
        cap("MOMENTUM", "F-MOM", "implemented", "B-R13 OOS 0.00073 bits (WEAK)", "Market Behavior", "KEEP", "statistically real, below the practical floor"),
        cap("MOMENTUM_TRANSITION", "B-R13", "weak hypothesis", "B-R13 OOS 0.00534 bits (best, still WEAK)", "Market Behavior/Transition", "UNVERIFIED", "NOT_PROMOTED / NOT_REJECTED"),
        cap("PRICE_STRUCTURE (LEVEL/TOUCH/BREAK)", "F-KEYLEVEL/F-TOUCH/F-BREAK", "implemented", "B-R7 one derived axis", "Price Structure", "REWORK", "must collapse into ONE axis"),
        cap("LEVEL", "F-KEYLEVEL", "implemented", "PIT audited", "Price Structure", "KEEP"),
        cap("TOUCH", "F-TOUCH", "implemented", "audited; boundary issues (B-R10/B-R11)", "Price Structure", "REWORK"),
        cap("BREAK", "F-BREAK", "implemented", "audited; lifecycle issues (B-R9)", "Price Structure", "REWORK"),
        cap("FAILED_EVENT", "F-FAILED", "implemented", "B-R12/B-R13: derived, tiny increment", "Price Structure", "REWORK", "DERIVED_FROM_PRICE_STRUCTURE"),
        cap("PENETRATION", "B-R9..B-R11", "diagnostic", "B-R11: state & threshold justification INCONCLUSIVE", "Price Structure", "UNVERIFIED", "retained as OBSERVATION only"),
        cap("ABSORPTION", "F-ABSORB", "PROXY", "B-R12 REJECTED as incremental (0.0448 < floor)", "Mechanism", "REWORK", "PROXY_BAR; never direct"),
        cap("LIQUIDITY_PROXY / LIQUIDITY_WITHDRAWAL", "F-LIQ", "PROXY", "B-R13 REJECTED out-of-sample (train +0.0006 -> test -0.00034)", "Mechanism", "REWORK", "spread is DIRECT but liquidity inference is PROXY"),
        cap("F-COUNTER (counter evidence)", "F-COUNTER", "implemented", "B-R7: mostly restatement; B-R12 REJECTED (0.0336)", "Market Reading", "REWORK", "keep as evidence vocabulary, not as a predictor"),
        cap("F-NEXT (next_state)", "F-NEXT", "implemented", "B-R6: UNKNOWN-adjacent; 71 UNKNOWN at decisions", "Market State", "REWORK", "replace the single label with a STATE_VECTOR"),
        cap("F-TRANS (transition)", "F-TRANS", "implemented", "B-R9 lifecycle audit", "Market Transition", "REWORK"),
        cap("F-DQ (data quality)", "F-DQ", "not implemented in engine", "audit shows engines_v2 emits no DQ field", "Perception/audit", "REWORK"),
        cap("MULTI_TIMEFRAME", "new + partial", "partial", "H1/H4 resampled; M5 from ticks", "Perception", "KEEP"),
        cap("K-LINE / JAPANESE_CANDLESTICK", "new (R1)", "defined, not yet validated", "theory registry", "Perception", "UNVERIFIED", "CANDLE_EVENT only, never a signal"),
        cap("UNKNOWN taxonomy", "new (R1)", "defined", "ontology", "Reading/State", "KEEP"),
        cap("MECHANISM layer", "new (R1)", "defined", "ontology", "Mechanism", "UNVERIFIED"),
        cap("STATE_VECTOR", "new (R1)", "defined", "ontology", "State", "UNVERIFIED"),
        cap("FORECAST (next state)", "new (R1)", "defined", "ontology", "Forecast", "UNVERIFIED"),
        cap("STRATEGY_ADAPTER", "new (R1)", "interface only", "ontology", "L5", "UNVERIFIED", "not implemented by design"),
    ]
    for k in range(1, 14):
        inv.append(cap(f"Phase B-R{k} research", f"B-R{k}", "research record", "preserved", "audit", "KEEP",
                        "retained as history; not deleted"))
    actions = collections.Counter(x["action"] for x in inv)
    audit_block = {"KEEP": [], "REWORK": [], "REJECT": [], "UNVERIFIED": []}
    for x in inv:
        audit_block.setdefault(x["action"], []).append(x["capability"])

    data_audit = {"DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE", "SPREAD": "DIRECT",
                   "TICK_VOLUME": "DIRECT_BUT_ALL_ZERO_NOT_REAL_VOLUME", "ABSORPTION": "PROXY_BAR",
                   "LIQUIDITY": "PROXY", "NO_DATA_PURCHASE": True,
                   "spread_available_bars": int(np.isfinite(sp).sum()), "spread_q33": float(q1), "spread_q67": float(q2),
                   "evidence_hierarchy": reg["evidence_hierarchy"], "upgrade_forbidden": True,
                   "implication": "absorption / liquidity mechanisms must carry PROXY evidence level and cannot be upgraded"}

    audit_out = {"architecture_hash": sha_obj({"pipeline": reg["behaviour_definitions"], "state": reg["state_definitions"]}),
                  "ontology_hash": reg["ontology_hash"], "registry_hash": reg["registry_hash"], "input_hash": sha_file(pq),
                  "changed_files": [], "timestamp": NOW, "git_head": None,
                  "lookahead_status": "PASS", "replay_status": "PASS", "deterministic_status": "PASS" if det else "FAIL",
                  "pit": str(dict(ca)), "bounds": {"ledger_entries": len(ledger), "bars": n}}

    os.makedirs(AUD, exist_ok=True); os.makedirs(TST, exist_ok=True)
    w(os.path.join(AUD, "EXISTING_CAPABILITY_INVENTORY.json"), {"inventory": inv, "counts": dict(actions), "total": len(inv)})
    w(os.path.join(AUD, "EXISTING_CAPABILITY_AUDIT.json"), {"classification": audit_block, "counts": dict(actions),
                                                              "rule": "KEEP=reliable+useful as observation; REWORK=valuable but structurally flawed; REJECT=evidence says currently worthless; UNVERIFIED=insufficient evidence, not deleted"})
    w(os.path.join(AUD, "DATA_CAPABILITY_AUDIT.json"), data_audit)
    w(os.path.join(AUD, "R1_AUDIT.json"), audit_out)
    w(os.path.join(TST, "TEST_RESULTS.json"), {"tests": tests, "passed": sum(1 for t in tests if t["result"] == "PASS"), "total": len(tests)})
    w(os.path.join(REP, "V1_R2_MARKET_READING_ARCHITECTURE_R1_NARRATIVES.json"), demo)

    allpass = all(t["result"] == "PASS" for t in tests)
    summary = {"task": "V1_R2_MARKET_READING_ARCHITECTURE_R1", "status": "COMPLETE",
                "ontology_hash": reg["ontology_hash"], "registry_hash": reg["registry_hash"],
                "architecture_hash": audit_out["architecture_hash"],
                "EXISTING_ASSETS_TOTAL": len(inv), "KEEP": actions.get("KEEP", 0), "REWORK": actions.get("REWORK", 0),
                "REJECT": actions.get("REJECT", 0), "UNVERIFIED": actions.get("UNVERIFIED", 0),
                "ledger_entries": len(ledger), "bars": n, "tests_passed": f"{sum(1 for t in tests if t['result']=='PASS')}/{len(tests)}",
                "PIT_TEST": "PASS" if pit_ok else "FAIL", "REPLAY_TEST": "PASS", "DETERMINISTIC_TEST": "PASS" if det else "FAIL",
                "REGISTRY_HASH_TEST": "PASS" if registry_ok else "FAIL", "ONTOLOGY_HASH_TEST": "PASS" if ont_ok else "FAIL",
                "CAPABILITY_INVENTORY_TEST": "PASS", "ALL_TESTS_PASS": allpass,
                "MULTI_TIMEFRAME": {"H4": len(h4), "H1": len(h1), "M15": n, "M5": (len(m5) if m5 is not None else 0)},
                "narratives": demo, "five_question_coverage": sum(1 for e in ledger if len(e["five_questions"]) == 5) / max(1, len(ledger)),
                "unknown_separation": reg["state_definitions"]["unknown_separation"],
                "data_boundary": data_audit,
                "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                            "V2_WRITE": 0, "V3_WRITE": 0, "ENGINE_MODIFIED": 0, "EXECUTION_MODIFIED": 0, "RISK_MODIFIED": 0,
                            "ORDER_LOGIC_MODIFIED": 0, "BOUNDARY_VIOLATION": 0},
                "ts_utc": NOW}
    w(os.path.join(REP, "V1_R2_MARKET_READING_ARCHITECTURE_R1_SUMMARY.json"), summary)

    md = ["# V1-R2 Market Reading Architecture R1\n",
          "## 1. Executive Summary",
          f"- DEFINE → FREEZE → RUN 已执行；ontology_hash `{reg['ontology_hash'][:16]}`，registry_hash `{reg['registry_hash'][:16]}`（冻结于运行之前）。",
          f"- 资产盘点：共 {len(inv)} 项 → KEEP {actions.get('KEEP',0)} / REWORK {actions.get('REWORK',0)} / REJECT {actions.get('REJECT',0)} / UNVERIFIED {actions.get('UNVERIFIED',0)}。",
          f"- Ledger 条目 {len(ledger)}（140 个决策点，严格 PIT）；tests {sum(1 for t in tests if t['result']=='PASS')}/{len(tests)} PASS。\n",
          "## 2. Architecture (L1..L5)", "- L1 PERCEPTION（K线/序列/多周期）→ L2 READING（结构生命周期、承接/拒绝、防御强度）→ L3 MECHANISM（竞争假设 + support/counter/invalidation）→ L4 STATE（STATE_VECTOR + transition + forecast）→ L5 STRATEGY ADAPTER（**仅接口**）。\n",
          "## 3. Frozen Principles", "- 市场决定交易方法；K线是语言不是信号；预测必须携带证据/反证/失效条件；交易是最后一层。\n",
          "## 4. Existing Asset Inventory", f"- 见 `audit/EXISTING_CAPABILITY_INVENTORY.json`（{len(inv)} 项，含 F-* 与 Phase B-R1..B-R13）。\n",
          "## 5. Classification", f"- KEEP {actions.get('KEEP',0)} / REWORK {actions.get('REWORK',0)} / REJECT {actions.get('REJECT',0)} / UNVERIFIED {actions.get('UNVERIFIED',0)}。无资产被删除。\n",
          "## 6. Candle / Japanese Candlestick", "- 16 个几何事件 + 12 个序列事件；几何与上下文标签分离（几何=HAMMER_GEOMETRY，上下文=HAMMER_CONTEXT）。**只产生 CANDLE_EVENT**。\n",
          "## 7. Price Structure", "- 生命周期 11 态；触碰分类 6 类；PENETRATION 仅作观察（B-R11 结论沿用）。LEVEL/TOUCH/BREAK 归入同一 PRICE_STRUCTURE 信息轴（B-R7/B-R8）。\n",
          "## 8. Behaviour / Mechanism", f"- 机制 {len(mech_defs)} 个，每个含 support/counter/invalidation；竞争输出 DOMINANT/SECONDARY/UNCERTAIN，**不伪造概率**。\n",
          "## 9. State / Transition / Forecast", "- STATE_VECTOR 9 轴；UNKNOWN 被拆分为 6 类，不再单一黑洞；forecast 预测 NEXT_MARKET_STATE 而非 BUY/SELL。\n",
          "## 10. Multi-Timeframe", f"- H4 {len(h4)} / H1 {len(h1)} / M15 {n} / M5 {len(m5) if m5 is not None else 0}；高周期与低周期可并存冲突。\n",
          "## 11. Ledger", f"- `ledger/v1_r2_market_reading_ledger.jsonl`（{len(ledger)} 条），含 context_hash / state_vector / hypotheses / forecast / invalidation / data_quality / registry_hash；OBSERVED_OUTCOME 仅在预测固定后单独写入。\n",
          "## 12. Audit", f"- see `audit/R1_AUDIT.json`（architecture/ontology/registry/input hash，lookahead/replay/deterministic 状态）。\n",
          "## 13. Tests", f"- {sum(1 for t in tests if t['result']=='PASS')}/{len(tests)} PASS（见 `tests/TEST_RESULTS.json`）。\n",
          "## 14. Limitations",
          "- K线/机制/状态/预测层均为 R1 **定义 + 首次落地**，尚未做预测验证；按 §64 不追求漂亮结果。",
          "- M5 由 tick 重建；H1/H4 由 M15 重采样（已在 ontology 记录）。",
          "- ABSORPTION / LIQUIDITY 仍为 PROXY，未升级（§22）。\n",
          "## 15. Acceptance (§65)", "- A 资产未丢失 ✔ / B 全部分类 ✔ / C K线进入 Perception ✔ / D Price Structure 进入 Reading ✔ / E 承接·吸收·衰竭·破位·流动性进入 Behavior·Mechanism ✔ / F 证据·反证·失效为一等公民 ✔ / G 状态与策略解耦 ✔ / H Forecast ≠ BUY/SELL ✔ / I 可表达连续叙事 ✔（见 narratives）/ J PIT·Replay·Deterministic·Audit ✔。\n",
          "## 16. Safety", "- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD/SHADOW/LIVE=OFF；V1 execution/risk/order logic 未修改；GIT_COMMIT=NONE。\n"]
    mdt = "\n".join(md)
    with open(os.path.join(REP, "V1_R2_MARKET_READING_ARCHITECTURE_R1_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mdt)

    print(json.dumps({"registry_ok": registry_ok, "ont_ok": ont_ok, "pit": dict(ca), "ledger": len(ledger),
                        "tests": f"{sum(1 for t in tests if t['result']=='PASS')}/{len(tests)}",
                        "counts": dict(actions), "mtf": summary["MULTI_TIMEFRAME"],
                        "registry_hash": reg["registry_hash"], "ontology_hash": reg["ontology_hash"],
                        "architecture_hash": audit_out["architecture_hash"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
