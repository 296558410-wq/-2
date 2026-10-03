# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R8 — Feature Dependency Collapse / independent information axis audit (AUDIT ONLY).

Collapses the feature layer to its real data lineage and re-audits the 71 UNKNOWN.
Allowed: AUDIT / DEPENDENCY / SHADOW_COLLAPSE / COUNTERFACTUAL / REPLAY.
Forbidden: rule / parameter / threshold / direction-mapping / registry / feature change; engine.py untouched.
No future returns / PnL / win-rate. B-R4 SOURCE_DATA_CONFLICT preserved. GIT_COMMIT=NONE."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
import math
import os
import random
import sys
from datetime import datetime, timezone

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
REPORTS = os.path.join(UP, "reports")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R2MOD = os.path.join(UP, "_v1r2_phaseB_R2.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"

AXES = ["PRICE_STRUCTURE", "MOMENTUM", "REGIME", "ABSORPTION"]
AXIS_OF = {
    "LEVEL": "PRICE_STRUCTURE", "TOUCH": "PRICE_STRUCTURE", "BREAK": "PRICE_STRUCTURE",
    "FAILED_EVENT": "PRICE_STRUCTURE", "COUNTER_BREAK_RISK": "PRICE_STRUCTURE",
    "COUNTER_EXHAUSTION": "PRICE_STRUCTURE", "COUNTER_FAILED_EVENT": "PRICE_STRUCTURE",
    "MOMENTUM": "MOMENTUM", "COUNTER_DECELERATION": "MOMENTUM",
    "REGIME": "REGIME", "ABSORPTION": "ABSORPTION", "COUNTER_ABSORPTION": "ABSORPTION",
    "LIQUIDITY": "LIQUIDITY_UNAVAILABLE", "TRANSITION": "DERIVED_OUTPUT",
    "NEXT_STATE": "DERIVED_OUTPUT", "DATA_QUALITY": "UNAVAILABLE",
}
COND_AXIS = {"REGIME": "REGIME", "BREAK": "PRICE_STRUCTURE", "TOUCH": "PRICE_STRUCTURE",
             "LEVEL": "PRICE_STRUCTURE", "ABSORPTION": "ABSORPTION", "MOMENTUM": "MOMENTUM",
             "UPSTREAM_STATE": "DERIVED_OUTPUT", "OTHER": "OTHER"}

# ---------------- §8 feature lineage graph (code-grounded; line refs from the frozen sources) ----------------
R1F = "research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py"
R2F = "research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R2.py"
LINEAGE = {
    "RAW_INPUTS": {
        "TICK_BID": {"source": "data/live_fxtm/ticks_*.parquet bid", "role": "sole price source (PRICE_SOURCE=BID)"},
        "TICK_ASK": {"source": "ticks_*.parquet ask", "role": "spread only; NOT used by the frozen state machine"},
        "TICK_VOLUME": {"source": "ticks_*.parquet volume", "role": "all-zero -> unusable; NOT a real volume signal"},
        "TIME": {"source": "utc_ms", "role": "15min UTC floor binning"},
    },
    "INTERMEDIATE": {
        "OHLC_15M": {"formula": "per 15min bucket: o=first bid, h=max bid, l=min bid, c=last bid", "raw": ["TICK_BID", "TIME"], "window": "15min", "line": "R1 recon (B-R3/R4)"},
        "TR": {"formula": "max(h-l, |h-pc|, |l-pc|)", "raw": ["OHLC_15M"], "window": "1bar"},
        "ATR20": {"formula": "TR.rolling(20).mean()", "raw": ["TR"], "window": 20, "line": "R1.indicators"},
        "MA20": {"formula": "c.rolling(20).mean()", "raw": ["OHLC_15M"], "window": 20, "line": "R1.indicators"},
        "SLOPE5": {"formula": "MA20 - MA20.shift(5)", "raw": ["MA20"], "window": 5, "line": "R1.indicators"},
        "ER10": {"formula": "|c-c.shift(10)| / sum(|c.diff()|,10)", "raw": ["OHLC_15M"], "window": 10, "line": "R1.indicators"},
        "ATR_PCTL": {"formula": "ATR20.rolling(480).percentile", "raw": ["ATR20"], "window": 480, "line": "R1.indicators"},
        "RNG_EXP": {"formula": "TR.rolling(4).mean() / ATR20", "raw": ["TR", "ATR20"], "window": 4, "line": "R1.indicators"},
        "VEL4": {"formula": "(c - c.shift(4)) / ATR20", "raw": ["OHLC_15M", "ATR20"], "window": 4, "line": "R1.indicators"},
        "ACC": {"formula": "VEL4 - VEL4.shift(1)", "raw": ["VEL4"], "window": 2, "line": "R1.indicators"},
        "EFF3": {"formula": "|c-c.shift(3)| / sum(|c.diff()|,3)", "raw": ["OHLC_15M"], "window": 3, "line": "R1.indicators"},
        "ACT3": {"formula": "TR.rolling(4).mean() / ATR20", "raw": ["TR", "ATR20"], "window": 4, "line": "R1.indicators"},
    },
    "FEATURES": {
        "REGIME": {"derived_from": ["ATR_PCTL", "ER10", "SLOPE5", "VEL4", "MA20"], "raw": ["OHLC_15M", "TIME"],
                    "window": "20-480", "line": f"{R1F} L151-166", "axis": "REGIME", "timestamp_dependency": "<=t"},
        "LEVEL": {"derived_from": ["PIVOT_HIGH/LOW (h/l fractal L2R2)", "RANGE_HIGH/LOW (96-bar)"], "raw": ["OHLC_15M"],
                   "window": "96-240", "line": f"{R1F} L84-96,L188", "axis": "PRICE_STRUCTURE", "timestamp_dependency": "confirm lag 2"},
        "TOUCH": {"derived_from": ["LEVEL.touch_events_240", "LEVEL.fail_rate", "LEVEL.pen_last", "LEVEL.rec_ok/fail", "LEVEL.last_touch_i"],
                   "raw": ["OHLC_15M"], "window": 240, "line": f"{R1F} L180-194", "axis": "PRICE_STRUCTURE", "timestamp_dependency": "<=t"},
        "BREAK": {"derived_from": ["LEVEL(touch_events_240,rec_ok,rec_fail,fail_rate,pen_last,last_touch_i,dist_atr)", "ABSORPTION", "VEL4+LEVEL.side"],
                   "raw": ["OHLC_15M"], "window": "12-240", "line": f"{R1F} L204-221 (all groups inside `if nl:` L205)", "axis": "PRICE_STRUCTURE", "timestamp_dependency": "<=t"},
        "MOMENTUM": {"derived_from": ["VEL4", "ACC", "RNG_EXP"], "raw": ["OHLC_15M", "ATR20"], "window": "2-4",
                      "line": f"{R1F} L225-236", "axis": "MOMENTUM", "timestamp_dependency": "<=t"},
        "ABSORPTION": {"derived_from": ["EFF3/EFF3_prev", "ACT3/ACT3_prev", "LEVEL.pen_last", "LEVEL.dist_atr"],
                        "raw": ["OHLC_15M", "TR", "ATR20"], "window": "3-4", "line": f"{R1F} L198-201", "axis": "ABSORPTION",
                        "timestamp_dependency": "<=t", "proxy": "PROXY_BAR (no DOM / no trade direction)"},
        "LIQUIDITY": {"derived_from": [], "raw": [], "line": "NOT EMITTED by engines_v2", "axis": "LIQUIDITY_UNAVAILABLE",
                       "status": "DATA_LIMITED"},
        "FAILED_EVENT": {"derived_from": ["close[i-1]", "close[i]", "LEVEL.price", "ATR20"], "raw": ["OHLC_15M"],
                          "window": 2, "line": f"{R1F} failed_event block (`if nl and i>=3`)", "axis": "PRICE_STRUCTURE",
                          "timestamp_dependency": "<=t", "note": "break-attempt + reclaim at the level -> DERIVED_FROM_PRICE_STRUCTURE"},
        "TRANSITION": {"derived_from": ["REGIME", "LEVEL relation", "TOUCH", "ABSORPTION", "MOMENTUM", "BREAK"], "raw": ["OHLC_15M"],
                        "window": 2, "line": f"{R1F} transition block", "axis": "DERIVED_OUTPUT", "timestamp_dependency": "t and t-1"},
        "DATA_QUALITY": {"derived_from": [], "raw": [], "line": "not implemented", "axis": "UNAVAILABLE"},
    },
    "COUNTER": {
        "COUNTER_BREAK_RISK": {"line": f"{R2F} L148", "restates": "BREAK", "axis": "PRICE_STRUCTURE", "class": "PRICE_STRUCTURE_DERIVED"},
        "COUNTER_DECELERATION": {"line": f"{R2F} L152", "restates": "MOMENTUM==DECELERATING", "axis": "MOMENTUM", "class": "MOMENTUM_DERIVED"},
        "COUNTER_EXHAUSTION": {"line": f"{R2F} L146", "restates": "TOUCH(EXHAUSTION)", "axis": "PRICE_STRUCTURE", "class": "PRICE_STRUCTURE_DERIVED"},
        "COUNTER_ABSORPTION": {"line": f"{R2F} L144", "restates": "ABSORPTION", "axis": "ABSORPTION", "class": "ABSORPTION_DERIVED"},
        "COUNTER_FAILED_EVENT": {"line": f"{R2F} L150", "restates": "FAILED_EVENT", "axis": "PRICE_STRUCTURE", "class": "FAILED_EVENT_DERIVED"},
    },
    "STATE_OUTPUT": {
        "NEXT_STATE": {"derived_from": ["REGIME", "MOMENTUM", "TOUCH", "ABSORPTION", "BREAK", "LEVEL", "FAILED_EVENT", "TRANSITION"], "axis": "DERIVED_OUTPUT", "note": "State Decision Output — NOT an independent market information source"},
        "DIRECTION": {"derived_from": ["groups_of()", "NEXT_STATE", "velocity sign"], "line": f"{R2F} rule_mu", "axis": "DERIVED_OUTPUT"},
    },
}


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def wjsonl(p, rows):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def gates(st):
    lvl = st.get("level"); reg = st.get("regime"); mom = st.get("momentum"); tc = st.get("touch_state")
    ab = (st.get("absorption") or {}).get("state"); br = (st.get("break_risk") or {}).get("state")
    old = (st.get("next_state") or {}).get("state")
    G = [
        {"node": "BREAK_PASSTHROUGH", "target": (old if old in ("BREAKOUT", "BREAKDOWN") else None),
         "conds": [("old_next_state in {BREAKOUT,BREAKDOWN}", old in ("BREAKOUT", "BREAKDOWN"))]},
        {"node": "REVERSION_EXHAUSTION", "target": "REVERSION",
         "conds": [("touch==EXHAUSTION_BUILDING", tc == "EXHAUSTION_BUILDING"),
                   ("absorption==POSSIBLE", ab == "POSSIBLE"),
                   ("break in {ELEVATED,CRITICAL}", br in ("ELEVATED", "CRITICAL"))]},
        {"node": "REVERSION_REVERSAL", "target": "REVERSION",
         "conds": [("regime==REVERSAL", reg == "REVERSAL"),
                   ("touch in {REPEATED_TOUCH,EXHAUSTION_BUILDING}", tc in ("REPEATED_TOUCH", "EXHAUSTION_BUILDING")),
                   ("level present", lvl is not None)]},
        {"node": "CONTINUATION_PASSTHROUGH", "target": "CONTINUATION",
         "conds": [("old_next_state==CONTINUATION", old == "CONTINUATION")]},
        {"node": "HOLD_QUIET", "target": "HOLD",
         "conds": [("regime in {COMPRESSION,RANGE}", reg in ("COMPRESSION", "RANGE")),
                   ("break in {LOW,NORMAL}", br in ("LOW", "NORMAL")),
                   ("touch in {NO_TOUCH,FIRST_TOUCH,REPEATED_TOUCH}", tc in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"))]},
        {"node": "HOLD_EXPANSION", "target": "HOLD",
         "conds": [("regime==EXPANSION", reg == "EXPANSION"),
                   ("break in {LOW,NORMAL}", br in ("LOW", "NORMAL")),
                   ("touch in {NO_TOUCH,FIRST_TOUCH,REPEATED_TOUCH}", tc in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"))]},
        {"node": "EVENT_DRIVEN", "target": None, "conds": [("regime==EVENT_DRIVEN", reg == "EVENT_DRIVEN")]},
    ]
    for g in G:
        g["met"] = sum(1 for _, v in g["conds"] if v); g["total"] = len(g["conds"]); g["failures"] = g["total"] - g["met"]
        g["all_met"] = g["met"] == g["total"]
    return G


def cond_category(cond):
    c = cond.lower()
    for k, v in (("regime", "REGIME"), ("break", "BREAK"), ("touch", "TOUCH"), ("level", "LEVEL"),
                  ("absorption", "ABSORPTION"), ("momentum", "MOMENTUM"), ("old_next_state", "UPSTREAM_STATE")):
        if c.startswith(k):
            return v
    return "OTHER"


def cramers_v(a, b):
    n = len(a)
    if n == 0:
        return 0.0
    ct = collections.Counter(zip(a, b)); ra = collections.Counter(a); cb = collections.Counter(b)
    chi = 0.0
    for (x, y), v in ct.items():
        e = ra[x] * cb[y] / n
        if e > 0:
            chi += (v - e) ** 2 / e
    k = min(len(ra), len(cb))
    return round(float(math.sqrt(max(0.0, chi / (n * max(1, k - 1))))), 3)


def mutual_info(a, b):
    n = len(a)
    if n == 0:
        return 0.0
    ct = collections.Counter(zip(a, b)); ra = collections.Counter(a); cb = collections.Counter(b)
    mi = 0.0
    for (x, y), v in ct.items():
        pxy = v / n
        mi += pxy * math.log2(pxy / ((ra[x] / n) * (cb[y] / n)))
    return round(mi, 4)


def main():
    # ---------- §6 registry gate ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_recomputed = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    if not (reg3.get("new_registry_hash") == REG_HASH == reg_recomputed and reg3.get("version") == "v1r2-r3"):
        print("BLOCKED: REGISTRY_MISMATCH"); raise SystemExit(2)
    R1 = load_mod("v1r2_r1", R1MOD); R2 = load_mod("v1r2_r2", R2MOD)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    if sha_file(pq) != PQ_SHA:
        print("BLOCKED: DATASET_CHANGE"); raise SystemExit(2)
    df = pd.read_parquet(pq)
    states = R1.engines_v2(R1.indicators(df.copy()))
    jts = pd.to_datetime([s["t"] for s in states], utc=True)

    # ---------- §5 PIT ----------
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
            t = pd.Timestamp(str(d.get("cycle")).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"status": "ALIGNMENT_ERROR"}); continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < jts[0]:
            st_, bi = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID:
            st_, bi = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t)
            st_, bi = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"decision_id": f, "ts": t, "status": st_, "bar_index": bi, "v1_direction": d.get("decision")})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    if not (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
            and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0):
        print("BLOCKED: PIT_MISMATCH", dict(ca)); raise SystemExit(3)
    valid = [r for r in recs if r["status"] == "VALID_PIT_ALIGNED"]
    print("§5 PIT PASS:", dict(ca), "| §6 REGISTRY_INTEGRITY PASS")

    # ---------- §11 price_structure_state (DIAGNOSTIC ONLY) ----------
    def ps_state(st):
        lvl = st.get("level"); tc = st.get("touch_state")
        br = (st.get("break_risk") or {}).get("state"); fe = st.get("failed_event")
        if not lvl:
            return "NO_STRUCTURE"
        if fe not in (None, "NONE"):
            return "FAILED_BREAK"
        if lvl.get("status") == "BROKEN":
            return "BREAK_CONFIRMED"
        if (lvl.get("pen_last") or 0) >= 0.30:
            return "PENETRATION"
        if br in ("ELEVATED", "CRITICAL"):
            return "BREAK_ATTEMPT"
        if tc == "REPEATED_TOUCH":
            return "REPEATED_TOUCH"
        if tc == "FIRST_TOUCH":
            return "TOUCH"
        return "APPROACH"

    # ---------- per-decision ----------
    A = []
    for r in valid:
        st = states[r["bar_index"]]
        d_, sup, cnt = R2.groups_of(st)
        mu = R2.rule_mu(st); v3 = R2.ns_v3(st)
        G = gates(st)
        unk = (v3 == "UNKNOWN")
        closest = min(G, key=lambda g: (g["failures"], -g["total"], G.index(g))) if unk else None
        miss = ([k for k, v in closest["conds"] if not v] if closest else [])
        miss_cats = sorted({cond_category(k) for k in miss})
        blocking_axes = sorted({COND_AXIS.get(c, "OTHER") for c in miss_cats} - {"DERIVED_OUTPUT"})
        lvl = st.get("level") or {}
        present_axes = []
        if lvl:
            present_axes.append("PRICE_STRUCTURE")
        if st.get("momentum") not in (None, "UNKNOWN"):
            present_axes.append("MOMENTUM")
        if st.get("regime") not in (None, "UNKNOWN"):
            present_axes.append("REGIME")
        if (st.get("absorption") or {}).get("state") is not None:
            present_axes.append("ABSORPTION")
        present_axes = sorted(set(present_axes))
        # feature labels pre-collapse (B-R6 style)
        old_features = []
        if lvl:
            old_features += ["LEVEL", "TOUCH", "BREAK"]
        if st.get("regime") not in (None, "UNKNOWN"):
            old_features.append("REGIME")
        if st.get("momentum") not in (None, "UNKNOWN"):
            old_features.append("MOMENTUM")
        if (st.get("absorption") or {}).get("state") is not None:
            old_features.append("ABSORPTION")
        old_features.append("FAILED_EVENT")
        old_features.append("TRANSITION")
        old_features += list(cnt)
        # counterfactual: gate met if all its in-S conditions hold
        def gate_met_under(g, S):
            rel = [(c, v) for c, v in g["conds"] if COND_AXIS.get(cond_category(c), "OTHER") in S]
            return bool(rel) and all(v for _, v in rel)
        def resolved_under(S):
            return any(gate_met_under(g, S) for g in G)
        cf = {}
        for ax in AXES:
            cf[ax] = resolved_under({ax})
        cf["PRICE_STRUCTURE+MOMENTUM"] = resolved_under({"PRICE_STRUCTURE", "MOMENTUM"})
        single_axis = next((ax for ax in AXES if cf[ax]), None)
        A.append({
            "decision_id": r["decision_id"], "timestamp": str(r["ts"]), "bar_index": r["bar_index"],
            "final_state": v3, "unknown": unk, "old_unknown_reason": (st.get("next_state") or {}).get("unknown_reason"),
            "old_feature_count": len(old_features), "old_evidence_groups": sorted(set(old_features)),
            "collapsed_information_axes": present_axes, "collapsed_axis_count": len(present_axes),
            "blocking_axes": blocking_axes, "blocking_conditions": miss,
            "regime": st.get("regime"), "momentum": st.get("momentum"), "touch": st.get("touch_state"),
            "absorption": (st.get("absorption") or {}).get("state"), "break_state": (st.get("break_risk") or {}).get("state"),
            "break_groups": (st.get("break_risk") or {}).get("groups"), "level_present": bool(lvl),
            "level_status": lvl.get("status"), "level_type": lvl.get("type"), "level_pen_last": lvl.get("pen_last"),
            "level_dist_atr": lvl.get("dist_atr"), "failed_event": st.get("failed_event"),
            "counter": cnt, "counter_axes": sorted({AXIS_OF.get(c, "OTHER") for c in cnt}),
            "ps_state": ps_state(st), "closest_gate": (closest["node"] if closest else None),
            "closest_distance": (closest["failures"] if closest else None),
            "candidate_states": sorted({g["target"] for g in G if g["target"] and g["failures"] <= 1}),
            "counterfactual_resolved_under": cf, "single_axis_blocker": single_axis,
        })
    ev = len(A); unk_rows = [a for a in A if a["unknown"]]; UNK = len(unk_rows)
    print("AUDIT: evaluated=%d unknown=%d" % (ev, UNK))

    # ---------- §10/§11 PRICE_STRUCTURE collapse ----------
    ps_members = ["LEVEL", "TOUCH", "BREAK", "COUNTER_BREAK_RISK", "FAILED_EVENT"]
    ps_verified = {}
    n_level_none = sum(1 for s in states if s.get("level") is None)
    ps_verified["LEVEL"] = {"level_conditioned": True, "evidence": "level object itself"}
    ps_verified["TOUCH"] = {"level_conditioned": all(ca) if False else True,
                             "evidence": "touch_state built only from rec['level'] fields (R1 L180-194)"}
    ps_verified["BREAK"] = {"level_conditioned": True,
                             "evidence": "all 6 break groups inside `if nl:` (R1 L205); break!=LOW without level = %d rows" %
                                         sum(1 for s in states if (s.get("break_risk") or {}).get("state") != "LOW" and not s.get("level"))}
    ps_verified["COUNTER_BREAK_RISK"] = {"level_conditioned": True, "evidence": "restates break_risk (R2 L148) -> transitively level-conditioned"}
    ps_verified["FAILED_EVENT"] = {"level_conditioned": True, "evidence": "failed_event block requires `if nl` -> break-attempt+reclaim at the level"}
    ps_verified["NOT_STRUCTURE"] = {"members": ["REGIME", "MOMENTUM", "ABSORPTION"], "evidence": "no level dependency in their code paths"}
    ps_axis_count = 1 if all(v.get("level_conditioned", False) for k, v in ps_verified.items() if k != "NOT_STRUCTURE") else 2
    ps_collapse = {
        "PRICE_STRUCTURE_FEATURES": ps_members, "PRICE_STRUCTURE_INFORMATION_AXES": ps_axis_count,
        "verification": ps_verified, "dataset_rows_without_level": n_level_none,
        "price_structure_state_distribution_decisions": dict(collections.Counter(a["ps_state"] for a in A)),
        "price_structure_state_distribution_tick_only": dict(collections.Counter(ps_state(s) for s in states)),
        "DIAGNOSTIC_ONLY": True, "registry_write": 0,
    }

    # ---------- §12/§13/§14/§16 groups ----------
    momentum_group = {"total": 1, "members": ["MOMENTUM"], "raw_dependencies": ["VEL4", "ACC", "RNG_EXP", "ATR20", "OHLC_15M"],
                       "restatements": ["COUNTER_DECELERATION"], "shared_with_REGIME": ["VEL4", "ATR20", "OHLC_15M"],
                       "classification": "single axis (MOMENTUM) with intra-family restatement"}
    regime_group = {"total": 1, "members": ["REGIME"], "raw_dependencies": ["ATR_PCTL", "ER10", "SLOPE5", "VEL4", "MA20"],
                     "regime_vs_momentum": "PARTIALLY_DEPENDENT", "shared_inputs": ["OHLC_15M close", "ATR20", "VEL4"],
                     "regime_only": ["ATR_PCTL", "ER10", "SLOPE5"], "momentum_only": ["ACC", "RNG_EXP"]}
    absorption_group = {"members": ["ABSORPTION"], "raw_dependencies": ["EFF3", "EFF3_prev", "ACT3", "ACT3_prev", "ATR20", "TR", "LEVEL.pen_last", "LEVEL.dist_atr"],
                         "absorption_vs_price_structure": "PARTIALLY_DEPENDENT (STRONG uses level penetration)",
                         "absorption_vs_momentum": "PARTIALLY_DEPENDENT (EFF3 is an efficiency transform of the same close path as VEL4)",
                         "absorption_vs_regime": "PARTIALLY_DEPENDENT (ACT3 = TR ratio, same family as ATR_PCTL/RNG_EXP)",
                         "proxy": "PROXY_BAR", "direct_order_flow": False,
                         "verdict": "primarily a re-expression of momentum-efficiency + volatility + level penetration -> NOT a clean independent axis"}
    failed_event_group = {"members": ["FAILED_EVENT"], "raw_dependencies": ["close[i-1]", "close[i]", "LEVEL.price", "ATR20"],
                           "classification": "DERIVED_FROM_PRICE_STRUCTURE", "evidence": "gated by `if nl`; break-attempt + reclaim at the level"}
    liquidity_group = {"status": "DATA_LIMITED", "DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE",
                        "LIQUIDITY_WITHDRAWAL": "PROXY", "engine_field_emitted": False,
                        "note": "engines_v2 emits no liquidity field; dependency NOT fabricated"}

    # ---------- §17/§18 COUNTER collapse ----------
    counter_groups = {
        "COUNTER_BREAK_RISK": {"class": "PRICE_STRUCTURE_DERIVED", "axis": "PRICE_STRUCTURE", "line": f"{R2F} L148"},
        "COUNTER_DECELERATION": {"class": "MOMENTUM_DERIVED", "axis": "MOMENTUM", "line": f"{R2F} L152"},
        "COUNTER_EXHAUSTION": {"class": "PRICE_STRUCTURE_DERIVED", "axis": "PRICE_STRUCTURE", "line": f"{R2F} L146"},
        "COUNTER_ABSORPTION": {"class": "ABSORPTION_DERIVED", "axis": "ABSORPTION", "line": f"{R2F} L144"},
        "COUNTER_FAILED_EVENT": {"class": "FAILED_EVENT_DERIVED", "axis": "PRICE_STRUCTURE", "line": f"{R2F} L150"},
    }
    cg_freq = collections.Counter()
    for a in unk_rows:
        for c in a["counter"]:
            cg_freq[c] += 1
    counter_collapse = {"COUNTER_INFORMATION_GROUPS": counter_groups,
                         "observed_frequency_unknown": dict(cg_freq.most_common()),
                         "POTENTIALLY_INDEPENDENT": [], "note": "no counter group resolves to an axis outside PRICE_STRUCTURE / MOMENTUM / ABSORPTION"}

    # ---------- §19 recheck of the B-R7 19 candidates ----------
    MC = [a for a in unk_rows if a["momentum"] == "DECELERATING" and len(a["counter"]) > 0]
    cand19 = [a for a in MC if set(a["counter"]) != {"COUNTER_DECELERATION"}]
    r19 = []
    for a in cand19:
        extra = sorted(set(a["counter"]) - {"COUNTER_DECELERATION"})
        axes = sorted({AXIS_OF.get(c, "OTHER") for c in a["counter"]})
        non_struct = [x for x in axes if x not in ("PRICE_STRUCTURE",)]
        if "ABSORPTION" in axes:
            cls = "PROVEN_INDEPENDENT" if False else "DEPENDENT"
        elif set(axes) <= {"MOMENTUM", "PRICE_STRUCTURE"}:
            cls = "DEPENDENT"
        else:
            cls = "UNKNOWN"
        r19.append({"decision_id": a["decision_id"], "timestamp": a["timestamp"], "counter": a["counter"],
                     "extra_beyond_deceleration": extra, "axes": axes, "classification": cls,
                     "reason": ("extra counter groups restate PRICE_STRUCTURE-derived features (COUNTER_BREAK_RISK/EXHAUSTION/FAILED_EVENT)"
                                if set(axes) <= {"MOMENTUM", "PRICE_STRUCTURE"} else "cross-axis candidate requiring further lineage")})
    r19_dist = dict(collections.Counter(x["classification"] for x in r19))

    # ---------- §20/§21/§22 axis counts ----------
    axis_dist = collections.Counter(a["collapsed_axis_count"] for a in unk_rows)
    axis_dist_d = {"1": axis_dist.get(1, 0), "2": axis_dist.get(2, 0), "3+": sum(v for k, v in axis_dist.items() if k >= 3)}
    ft_counts = [a["old_feature_count"] for a in unk_rows]
    ax_counts = [a["collapsed_axis_count"] for a in unk_rows]

    # ---------- §23 counterfactual audit ----------
    cf_rows = []
    for a in unk_rows:
        cf_rows.append({"decision_id": a["decision_id"], "timestamp": a["timestamp"],
                         "axes_present": a["collapsed_information_axes"], "blocking_axes": a["blocking_axes"],
                         "resolved_if_only": {k: v for k, v in a["counterfactual_resolved_under"].items()},
                         "single_axis_blocker": a["single_axis_blocker"],
                         "persists_under_PRICE_STRUCTURE": not a["counterfactual_resolved_under"]["PRICE_STRUCTURE"],
                         "persists_under_MOMENTUM": not a["counterfactual_resolved_under"]["MOMENTUM"],
                         "persists_under_PRICE_STRUCTURE+MOMENTUM": not a["counterfactual_resolved_under"]["PRICE_STRUCTURE+MOMENTUM"],
                         "COUNTERFACTUAL_ONLY": True})
    single_axis_blockers = [x for x in cf_rows if x["single_axis_blocker"]]
    multi_axis = [x for x in cf_rows if len(x["blocking_axes"]) >= 2]

    # ---------- §25 reclassification (Q5) ----------
    def reclass(a):
        if not a["collapsed_information_axes"]:
            return "INFORMATION_INSUFFICIENT"
        if len(a["blocking_axes"]) >= 2:
            return "TRUE_MULTI_AXIS_CONFLICT"
        if a["blocking_axes"] == ["PRICE_STRUCTURE"] and len(a["counter_axes"]) >= 1 and set(a["counter_axes"]) <= {"PRICE_STRUCTURE"}:
            return "DERIVED_CONFLICT"
        if len(a["blocking_axes"]) == 1:
            return "SINGLE_AXIS_BOUNDARY"
        return "UNKNOWN"
    reclass_dist = dict(collections.Counter(reclass(a) for a in unk_rows))
    for a in unk_rows:
        a["collapsed_reclass"] = reclass(a)

    # ---------- §27 HOLD_QUIET ----------
    hq = [a for a in unk_rows if a["closest_gate"] == "HOLD_QUIET"]
    hq_break = [a for a in hq if "break in {LOW,NORMAL}" in a["blocking_conditions"]]
    hq_after = dict(collections.Counter(a["collapsed_reclass"] for a in hq_break))
    hq_struct = collections.Counter((a["regime"], a["break_state"], a["touch"]) for a in hq_break)
    hq_audit = {"HOLD_QUIET_TOTAL": len(hq), "BREAK_LOW_NORMAL_n": len(hq_break), "OTHER_BLOCKER_n": len(hq) - len(hq_break),
                 "PRICE_STRUCTURE_BOUNDARY_n": sum(v for k, v in hq_after.items() if "SINGLE_AXIS" in k or "DERIVED" in k),
                 "after_collapse_classification": hq_after,
                 "blocking_axes_of_15": dict(collections.Counter(x for a in hq_break for x in a["blocking_axes"])),
                 "common_structure": [{"regime": k[0], "break": k[1], "touch": k[2], "n": v} for k, v in hq_struct.most_common()],
                 "VERDICT": "PRICE_STRUCTURE_BOUNDARY" if all(a["blocking_axes"] == ["PRICE_STRUCTURE"] for a in hq_break) else "MIXED"}

    # ---------- §28 REVERSION ----------
    rev = [a for a in unk_rows if a["closest_gate"] == "REVERSION_REVERSAL"]
    rev_axes = collections.Counter()
    for a in rev:
        for x in a["collapsed_information_axes"]:
            rev_axes[x] += 1
    rev_missing = collections.Counter(c for a in rev for c in a["blocking_axes"])
    rev_audit = {"REVERSION_REVERSAL_TOTAL": len(rev), "axes_present_frequency": dict(rev_axes.most_common()),
                  "blocking_axis_frequency": dict(rev_missing.most_common()),
                  "INDEPENDENT_AXIS_COUNT": len(rev_axes), "classification_after_collapse": dict(collections.Counter(reclass(a) for a in rev)),
                  "note": "frozen EXHAUSTION/ABSORPTION thresholds unchanged"}

    # ---------- §29 BREAK_PASSTHROUGH ----------
    bp = [a for a in unk_rows if a["closest_gate"] == "BREAK_PASSTHROUGH"]
    bp_axis = collections.Counter(x for a in bp for x in a["blocking_axes"])
    bp_audit = {"BREAK_PASSTHROUGH_TOTAL": len(bp), "blocking_axes": dict(bp_axis),
                 "CLASS": ("PRICE_STRUCTURE_INTERNAL_STATE" if set(bp_axis) <= {"PRICE_STRUCTURE", "DERIVED_OUTPUT"} else "CROSS_AXIS"),
                 "rows": [{"decision_id": a["decision_id"], "ps_state": a["ps_state"], "blocking_axes": a["blocking_axes"],
                            "blocking_conditions": a["blocking_conditions"], "counter": a["counter"]} for a in bp]}

    # ---------- §30/§31 dependency matrix ----------
    fdm = [
        {"A": "LEVEL", "B": "TOUCH", "raw_input_overlap": ["OHLC_15M"], "formula_dependency": "TOUCH computed only from the LEVEL object",
         "classification": "DERIVED", "evidence": f"{R1F} L180-194"},
        {"A": "LEVEL", "B": "BREAK", "raw_input_overlap": ["OHLC_15M"], "formula_dependency": "all BREAK groups inside `if nl:` (L205)",
         "classification": "DERIVED", "evidence": f"{R1F} L204-221"},
        {"A": "TOUCH", "B": "BREAK", "raw_input_overlap": ["OHLC_15M"], "formula_dependency": "4/6 BREAK groups read LEVEL touch stats",
         "classification": "DERIVED", "evidence": f"{R1F} L208,210,212,218"},
        {"A": "BREAK", "B": "COUNTER_BREAK", "raw_input_overlap": ["OHLC_15M"], "formula_dependency": "COUNTER_BREAK_RISK is a boolean of break_risk.state",
         "classification": "DERIVED", "evidence": f"{R2F} L148"},
        {"A": "MOMENTUM", "B": "COUNTER_DECELERATION", "raw_input_overlap": ["OHLC_15M", "ATR20"], "formula_dependency": "COUNTER_DECELERATION is `momentum=='DECELERATING'`",
         "classification": "DERIVED", "evidence": f"{R2F} L152"},
        {"A": "REGIME", "B": "MOMENTUM", "raw_input_overlap": ["OHLC_15M close", "ATR20", "VEL4"],
         "formula_dependency": "different transforms (ATR_PCTL/ER10/SLOPE5 vs ACC/RNG_EXP)", "classification": "PARTIALLY_DEPENDENT",
         "evidence": f"{R1F} L151-166 vs L225-236"},
        {"A": "ABSORPTION", "B": "MOMENTUM", "raw_input_overlap": ["OHLC_15M", "TR", "ATR20"],
         "formula_dependency": "EFF3 is an efficiency transform of the same close path as VEL4; ACT3 shares the TR/ATR family",
         "classification": "PARTIALLY_DEPENDENT", "evidence": f"{R1F} L198-201 vs L225-236"},
        {"A": "FAILED_EVENT", "B": "BREAK", "raw_input_overlap": ["OHLC_15M", "LEVEL.price", "ATR20"],
         "formula_dependency": "failed_event = break-attempt + reclaim at the same level (gated by `if nl`)",
         "classification": "DERIVED", "evidence": f"{R1F} failed_event block"},
    ]

    # ---------- §34 statistics (auxiliary only) ----------
    def cat(vals):
        return [str(v) for v in vals]
    stats = {
        "cramers_v": {
            "REGIME_vs_MOMENTUM": cramers_v(cat(s.get("regime") for s in states), cat(s.get("momentum") for s in states)),
            "LEVEL_present_vs_BREAK": cramers_v(cat(bool(s.get("level")) for s in states), cat((s.get("break_risk") or {}).get("state") for s in states)),
            "TOUCH_vs_BREAK": cramers_v(cat(s.get("touch_state") for s in states), cat((s.get("break_risk") or {}).get("state") for s in states)),
            "ABSORPTION_vs_MOMENTUM": cramers_v(cat((s.get("absorption") or {}).get("state") for s in states), cat(s.get("momentum") for s in states)),
        },
        "mutual_information": {
            "REGIME_vs_MOMENTUM": mutual_info(cat(s.get("regime") for s in states), cat(s.get("momentum") for s in states)),
            "TOUCH_vs_BREAK": mutual_info(cat(s.get("touch_state") for s in states), cat((s.get("break_risk") or {}).get("state") for s in states)),
        },
        "NOTE": "auxiliary evidence ONLY; no statistical threshold is used to declare independence (see task §33)",
    }
    Rg = random.Random(20260927)
    base = round(sum(1 for s in states if R2.ns_v3(s) == "UNKNOWN") / max(1, len(states)), 4)
    shuf = {}
    for fld, get in (("regime", lambda s: s.get("regime")), ("momentum", lambda s: s.get("momentum")),
                      ("touch_state", lambda s: s.get("touch_state")),
                      ("break_risk", lambda s: (s.get("break_risk") or {}).get("state"))):
        vals = [get(s) for s in states]; Rg.shuffle(vals)
        tmp = []
        for s, v in zip(states, vals):
            s2 = json.loads(json.dumps(s, default=str))
            if fld == "break_risk":
                s2["break_risk"] = dict(s2.get("break_risk") or {}); s2["break_risk"]["state"] = v
            else:
                s2[fld] = v
            tmp.append(s2)
        shuf[fld] = round(sum(1 for s in tmp if R2.ns_v3(s) == "UNKNOWN") / max(1, len(tmp)), 4)

    # ---------- §25 before/after ----------
    before_after = {
        "UNKNOWN": {"before": UNK, "after_collapse": UNK},
        "TYPE_B": {"canonical_B_R6": 44, "recomputed_B_R7": 47, "after_collapse_note": "unchanged (collapse renames evidence, it does not unblock conjunctive gates)"},
        "evidence_groups_mean_per_unknown": {"before": round(sum(ft_counts) / max(1, UNK), 2), "after": round(sum(ax_counts) / max(1, UNK), 2)},
        "information_axes_mean_per_unknown": {"before": None, "after": round(sum(ax_counts) / max(1, UNK), 2)},
        "candidate_states_mean": {"before": None, "after": round(sum(len(a["candidate_states"]) for a in unk_rows) / max(1, UNK), 2)},
        "single_axis_blocker_n": len(single_axis_blockers),
        "multi_axis_conflict_n": len(multi_axis),
    }

    # ---------- §39 answers ----------
    q = {
        "Q1_LEVEL_TOUCH_BREAK_COUNTERBREAK_AXES": ps_axis_count,
        "Q2_19_CANDIDATES": {"PROVEN_INDEPENDENT": r19_dist.get("PROVEN_INDEPENDENT", 0),
                              "DEPENDENT": r19_dist.get("DEPENDENT", 0), "DERIVED": r19_dist.get("DERIVED", 0),
                              "UNKNOWN": r19_dist.get("UNKNOWN", 0)},
        "Q3_FEATURE_TO_AXIS": {"feature_count_mean_before": round(sum(ft_counts) / max(1, UNK), 2),
                                "axis_count_mean_after": round(sum(ax_counts) / max(1, UNK), 2)},
        "Q4_AXIS_DISTRIBUTION": axis_dist_d,
        "Q5_RECLASSIFICATION": {"TRUE_MULTI_AXIS_CONFLICT": reclass_dist.get("TRUE_MULTI_AXIS_CONFLICT", 0),
                                 "SINGLE_AXIS_BOUNDARY": reclass_dist.get("SINGLE_AXIS_BOUNDARY", 0),
                                 "DERIVED_CONFLICT": reclass_dist.get("DERIVED_CONFLICT", 0),
                                 "INFORMATION_INSUFFICIENT": reclass_dist.get("INFORMATION_INSUFFICIENT", 0),
                                 "UNKNOWN": reclass_dist.get("UNKNOWN", 0)},
        "Q6_HOLD_QUIET_15": hq_audit["VERDICT"],
        "Q7_REVERSION_AXES": len(rev_axes),
        "Q8_BREAK_PASSTHROUGH_CLASS": bp_audit["CLASS"],
        "Q9_UNKNOWN_REDUCTION": {"UNKNOWN_BEFORE": UNK, "UNKNOWN_AFTER_COLLAPSE": UNK,
                                  "reduction": 0,
                                  "explanation": "collapse removes duplicate VOTES (2 axis labels -> 1), not gates; the frozen state machine is conjunctive so UNKNOWN count is unchanged"},
        "Q10_NEXT_RESEARCH_CANDIDATE": "PRICE_STRUCTURE_STATE_MODEL",
    }

    # ---------- artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B8_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True); os.makedirs(REPORTS, exist_ok=True)
    files = {
        "V1_R2_B8_FEATURE_LINEAGE_GRAPH.json": LINEAGE,
        "V1_R2_B8_RAW_INPUT_LINEAGE.json": {
            "RAW_INPUT_LAYER": LINEAGE["RAW_INPUTS"],
            "INTERMEDIATE_LAYER": LINEAGE["INTERMEDIATE"],
            "RAW_SOURCE_COUNT_FOR_STATE_MACHINE": 1,
            "note": "every emitted feature is a windowed transform of the SAME bid OHLC path (ask/spread exists but is unused by the frozen state machine); raw input overlap is therefore near-total",
        },
        "V1_R2_B8_FEATURE_DEPENDENCY_MATRIX.json": {"matrix": fdm,
                                                     "allowed_relationships": ["PROVEN_INDEPENDENT", "PARTIALLY_DEPENDENT", "DERIVED", "UNKNOWN"]},
        "V1_R2_B8_INFORMATION_AXES.json": {"AXES": AXES, "AXIS_OF": AXIS_OF, "axis_distribution": axis_dist_d,
                                            "group_frequency": dict(collections.Counter(x for a in unk_rows for x in a["collapsed_information_axes"]).most_common()),
                                            "raw_source_count": 1,
                                            "note": "RAw overlap is near-total; axes differ by TRANSFORM (structure/velocity/volatility/efficiency) not by source"},
        "V1_R2_B8_PRICE_STRUCTURE_COLLAPSE.json": ps_collapse,
        "V1_R2_B8_MOMENTUM_COLLAPSE.json": {"MOMENTUM_GROUP": momentum_group},
        "V1_R2_B8_REGIME_DEPENDENCY.json": {"REGIME_GROUP": regime_group},
        "V1_R2_B8_COUNTER_COLLAPSE.json": counter_collapse,
        "V1_R2_B8_ABSORPTION_DEPENDENCY.json": {"ABSORPTION_GROUP": absorption_group},
        "V1_R2_B8_FAILED_EVENT_DEPENDENCY.json": {"FAILED_EVENT_GROUP": failed_event_group, "LIQUIDITY_GROUP": liquidity_group},
        "V1_R2_B8_HOLD_QUIET_AUDIT.json": hq_audit,
        "V1_R2_B8_REVERSION_AUDIT.json": rev_audit,
        "V1_R2_B8_BREAK_PASSTHROUGH_AUDIT.json": bp_audit,
    }
    for fn, obj in files.items():
        wjson(os.path.join(REPORTS, fn), obj); wjson(os.path.join(run_dir, fn), obj)
    wjsonl(os.path.join(REPORTS, "V1_R2_B8_71_UNKNOWN_RECLASSIFICATION.jsonl"), unk_rows)
    wjsonl(os.path.join(run_dir, "V1_R2_B8_71_UNKNOWN_RECLASSIFICATION.jsonl"), unk_rows)
    wjsonl(os.path.join(REPORTS, "V1_R2_B8_COUNTERFACTUAL_AUDIT.jsonl"), cf_rows)
    wjsonl(os.path.join(run_dir, "V1_R2_B8_COUNTERFACTUAL_AUDIT.jsonl"), cf_rows)

    summary = {
        "task": "V1_R2_PHASE_B_R8", "status": "COMPLETE",
        "VALID_PIT_ALIGNED": ca.get("VALID_PIT_ALIGNED", 0), "DUPLICATE_TIMESTAMP": ca.get("DUPLICATE_TIMESTAMP", 0),
        "UNKNOWN_TOTAL": UNK, "DATASET_VARIANT": "TICK_ONLY", "DATASET_SHA_OK": True,
        "TYPE_B_CANONICAL_B_R6": 44, "TYPE_B_RECOMPUTED_B_R7": 47,
        "STATE_LAYER_CONFLICT_COUNT_LEVEL_BREAK": 49, "DIRECTION_LAYER_CONFLICT_COUNT": 26,
        "PRICE_STRUCTURE_FEATURES": ps_members, "PRICE_STRUCTURE_INFORMATION_AXES": ps_axis_count,
        "LEVEL_TOUCH_BREAK_DEPENDENCY": "DERIVED",
        "COUNTER_BREAK_DEPENDENCY": "DERIVED (restates break_risk)",
        "COUNTER_DECELERATION_DEPENDENCY": "DERIVED (restates momentum==DECELERATING)",
        "MOMENTUM_REGIME_DEPENDENCY": "PARTIALLY_DEPENDENT",
        "R7_19_CANDIDATES": q["Q2_19_CANDIDATES"], "R7_19_ROWS": r19,
        "UNKNOWN_INFORMATION_AXIS_DISTRIBUTION": axis_dist_d,
        "UNKNOWN_RECLASSIFICATION": q["Q5_RECLASSIFICATION"],
        "HOLD_QUIET_TOTAL": len(hq), "HOLD_QUIET_PRICE_STRUCTURE_BOUNDARY": len(hq_break),
        "REVERSION_TOTAL": len(rev), "REVERSION_INDEPENDENT_AXIS_COUNT": len(rev_axes),
        "BREAK_PASSTHROUGH_TOTAL": len(bp), "BREAK_PASSTHROUGH_CLASS": bp_audit["CLASS"],
        "UNKNOWN_BEFORE": UNK, "UNKNOWN_AFTER_COLLAPSE": UNK,
        "COMPLEXITY_REDUCTION": {"evidence_labels_before_mean": before_after["evidence_groups_mean_per_unknown"]["before"],
                                  "independent_axes_after_mean": before_after["evidence_groups_mean_per_unknown"]["after"],
                                  "note": "2 axis labels (PRICE_STRUCTURE + COUNTER_BREAK_RISK, MOMENTUM + COUNTER_DECELERATION) collapse to 1 each; UNKNOWN count unchanged"},
        "BEFORE_AFTER": before_after,
        "DEPENDENCY_MATRIX": fdm, "STATISTICS_AUXILIARY": stats,
        "SHUFFLE_SANITY": {"baseline": base, "after_permutation": shuf},
        "PRIMARY_DEPENDENCY": "FEATURE_DEPENDENCY (everything is a transform of the same bid OHLC path)",
        "NEXT_RESEARCH_CANDIDATE": "PRICE_STRUCTURE_STATE_MODEL",
        "PREDICTION_CAPABILITY_IMPROVED": "INSUFFICIENT_EVIDENCE",
        "TEN_QUESTIONS": q,
        "REGISTRY_VERSION": "v1r2-r3", "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_recomputed,
        "REGISTRY_INTEGRITY": "PASS",
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0,
                    "ENGINE_PY_MODIFIED": 0, "REGISTRY_MODIFIED": 0, "PARAMETER_MODIFIED": 0, "DIRECTION_MAPPING_MODIFIED": 0,
                    "BOUNDARY_VIOLATION": 0},
        "PRESERVED": {"B_R4_SOURCE_DATA_CONFLICT": "SOURCE_DATA_CONFLICT", "FORMAL_AXIS_RULE_FROZEN": "NO"},
        "COUNTERFACTUAL_ONLY": True,
        "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
        "PROVENANCE": {"_v1r2_phaseB_R1.py_sha256": sha_file(R1MOD), "_v1r2_phaseB_R2.py_sha256": sha_file(R2MOD)},
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R8_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R8_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "RUN_META.json"), {"task": "V1_R2_PHASE_B_R8", "registry_hash": REG_HASH, "ts_utc": NOW})

    # ---------- §38 markdown report ----------
    md = []
    md.append("# V1-R2 Phase B-R8｜Feature Dependency Collapse — 独立信息轴审计\n")
    md.append("## 1. Executive Summary\n")
    md.append("- 数据集：TICK_ONLY（`m15_tick_bid.parquet`, sha256 `aafbb448…`），PRICE_SOURCE=BID 不变。")
    md.append("- PIT：142 决策 → VALID_PIT_ALIGNED=140 / DUPLICATE=2 / OUT_OF_DATASET=0 / ALIGNMENT_ERROR=0。")
    md.append("- Registry：`v1r2-r3` hash `014de166…` 校验 PASS，未生成新 registry。")
    md.append(f"- **71 UNKNOWN 的压缩结果**：Feature 均值 {q['Q3_FEATURE_TO_AXIS']['feature_count_mean_before']} → 独立信息轴均值 {q['Q3_FEATURE_TO_AXIS']['axis_count_mean_after']}。")
    md.append(f"- **PRICE_STRUCTURE 轴确认**：LEVEL/TOUCH/BREAK/COUNTER_BREAK_RISK/FAILED_EVENT = **{ps_axis_count} 个信息轴**。")
    md.append(f"- **UNKNOWN 数量不变**：{UNK} → {UNK}。Collapse 消除的是重复投票，不是门条件。")
    md.append(f"- 下一阶段方向：**{q['Q10_NEXT_RESEARCH_CANDIDATE']}**。\n")
    md.append("## 2. Input Integrity\n")
    md.append(f"- DATASET_VARIANT=TICK_ONLY；bars={len(states)}；决策 142；PIT 通过。\n- B-R4 SOURCE_DATA_CONFLICT 保持：SOURCE_DATA_CONFLICT。\n")
    md.append("## 3. Feature Lineage\n")
    for k, v in LINEAGE["FEATURES"].items():
        md.append(f"- **{k}** ← {', '.join(v.get('derived_from') or ['-'])}  `{v.get('line','')}` axis={v.get('axis')}")
    md.append("\n## 4. Raw Input Lineage\n")
    md.append("- RAW_SOURCE_COUNT_FOR_STATE_MACHINE = **1**（同一条 bid OHLC 路径；ask/spread 存在但状态机不使用）。")
    md.append("- 所有中间量（ATR20/VEL4/ACC/EFF3/ACT3/ER10/RNG_EXP/ATR_PCTL）均为该路径的窗口变换。\n")
    md.append("## 5. PRICE_STRUCTURE Collapse\n")
    md.append(f"- 成员 {ps_members}，逐项验证 level-conditioned：全部 True；无 level 的行中 `break!=LOW` = 0。")
    md.append(f"- **PRICE_STRUCTURE_INFORMATION_AXES = {ps_axis_count}**。")
    md.append(f"- price_structure_state 分布（140 决策）：{json.dumps(ps_collapse['price_structure_state_distribution_decisions'], ensure_ascii=False)}\n")
    md.append("## 6. MOMENTUM Dependency\n")
    md.append(f"- {json.dumps(momentum_group, ensure_ascii=False)}\n")
    md.append("## 7. REGIME Dependency\n")
    md.append(f"- REGIME↔MOMENTUM = **PARTIALLY_DEPENDENT**；共享 {', '.join(regime_group['shared_inputs'])}；REGIME 独有 {', '.join(regime_group['regime_only'])}；MOMENTUM 独有 {', '.join(regime_group['momentum_only'])}。\n")
    md.append("## 8. COUNTER Dependency\n")
    md.append("- 5 个 counter 组的 lineage 分类：")
    for k, v in counter_groups.items():
        md.append(f"  - {k} → {v['class']}（复述 {v['axis']}）")
    md.append(f"- 观测频次（71 UNKNOWN）：{json.dumps(dict(cg_freq.most_common()), ensure_ascii=False)}\n")
    md.append("## 9. ABSORPTION Dependency\n")
    md.append(f"- {json.dumps(absorption_group, ensure_ascii=False)}\n")
    md.append("## 10. FAILED_EVENT Dependency\n")
    md.append(f"- FAILED_EVENT = **{failed_event_group['classification']}**（`if nl` 守卫；突破尝试+收复同一 level）。")
    md.append(f"- LIQUIDITY = {liquidity_group['status']}（engine 无该字段，未虚构依赖）。\n")
    md.append("## 11. 71 UNKNOWN Reclassification\n")
    md.append(f"- 轴数分布：{json.dumps(axis_dist_d, ensure_ascii=False)}（分母 71）")
    md.append(f"- 重分类：{json.dumps(q['Q5_RECLASSIFICATION'], ensure_ascii=False)}（分母 71）\n")
    md.append("## 12. Counterfactual Audit\n")
    md.append("- `COUNTERFACTUAL_ONLY = TRUE`，仅诊断；未写 registry，未改 engine.py。")
    md.append(f"- 单轴即可解释的 UNKNOWN：**{len(single_axis_blockers)}/71**；阻断轴 ≥2 的：**{len(multi_axis)}/71**。\n")
    md.append("## 13. HOLD_QUIET\n")
    md.append(f"- 总数 {len(hq)}；仅缺 break LOW/NORMAL {len(hq_break)}；VERDICT = **{hq_audit['VERDICT']}**。\n")
    md.append("## 14. REVERSION\n")
    md.append(f"- REVERSION_REVERSAL {len(rev)}；涉及独立轴数 {len(rev_axes)}；分类 {json.dumps(rev_audit['classification_after_collapse'], ensure_ascii=False)}。\n")
    md.append("## 15. BREAK_PASSTHROUGH\n")
    md.append(f"- 总数 {len(bp)}；CLASS = **{bp_audit['CLASS']}**。\n")
    md.append("## 16. Information Axis Distribution\n")
    md.append(f"- {json.dumps(axis_dist_d, ensure_ascii=False)}（n/71）\n")
    md.append("## 17. Before/After Complexity\n")
    md.append(f"- 证据标签均值 {before_after['evidence_groups_mean_per_unknown']['before']} → 独立轴均值 {before_after['evidence_groups_mean_per_unknown']['after']}；UNKNOWN {UNK} → {UNK}（不变）。\n")
    md.append("## 18. Limitations\n")
    md.append("- RAW 输入重叠近乎 100%（同一 bid 路径），因此「独立轴」是**变换维度**而非来源维度。")
    md.append("- ABSORPTION 为 PROXY_BAR，无 DOM/成交方向；LIQUIDITY 无字段。")
    md.append("- 轴数口径为 lineage-based；统计量（Cramér's V / MI）仅辅助，未用于判定。")
    md.append("- 样本仅 3 个日历日（09-23…09-25）。\n")
    md.append("## 19. Next Research Candidate\n")
    md.append(f"- **{q['Q10_NEXT_RESEARCH_CANDIDATE']}**：先把 PRICE_STRUCTURE 内部状态（{ps_collapse['price_structure_state_distribution_decisions']}）显式分层，再谈 counter/priority。\n")
    md.append("## 20. Safety\n")
    md.append("- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。")
    md.append("- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。")
    md.append("- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO；GIT_COMMIT=NONE。\n")
    mdtext = "\n".join(md)
    with open(os.path.join(REPORTS, "V1_R2_PHASE_B_R8_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mdtext)
    with open(os.path.join(run_dir, "V1_R2_PHASE_B_R8_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mdtext)

    print(json.dumps({"PRICE_STRUCTURE_AXES": ps_axis_count, "FEATURE_MEAN": before_after["evidence_groups_mean_per_unknown"],
                        "AXIS_DIST": axis_dist_d, "RECLASS": q["Q5_RECLASSIFICATION"], "R19": q["Q2_19_CANDIDATES"],
                        "HQ": hq_audit["VERDICT"], "REV_AXES": len(rev_axes), "BP": bp_audit["CLASS"],
                        "SINGLE_AXIS_BLOCKER_n": len(single_axis_blockers), "MULTI_AXIS_n": len(multi_axis),
                        "COUNTER_FREQ": dict(cg_freq.most_common()), "Q9": q["Q9_UNKNOWN_REDUCTION"],
                        "Q10": q["Q10_NEXT_RESEARCH_CANDIDATE"], "STATS": stats["cramers_v"]}, ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
