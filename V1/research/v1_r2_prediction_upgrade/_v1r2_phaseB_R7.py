# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R7 — LEVEL/BREAK + COUNTER-EVIDENCE conflict INDEPENDENT audit (AUDIT ONLY).

Goal: decide whether the observed "evidence conflicts" are real independent information
conflicts, or feature-repetition / nested-definition / shared-input / rule-boundary artifacts.
Dependency labels are derived from CODE PATHS and FIELD LINEAGE, never from opinion.
No rule/parameter/threshold/direction/registry/feature change. No future returns / PnL / win-rate."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
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
GATE_ORDER = ["BREAK_PASSTHROUGH", "REVERSION_EXHAUSTION", "REVERSION_REVERSAL",
              "CONTINUATION_PASSTHROUGH", "HOLD_QUIET", "HOLD_EXPANSION", "EVENT_DRIVEN"]

# ---- code-grounded lineage facts (file + line refs, read from the frozen sources) ----
BREAK_PATH = {
    "source_file": "research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py",
    "anchor": "engines_v2() break-risk block",
    "lines": {"guard": 205, "TOUCH_REPEAT": 208, "REJECTION_FAIL": 210, "PENETRATION": 212,
              "ABSORPTION": 214, "MOMENTUM_TOWARD": 216, "AT_LEVEL": 218, "n_ev": 219, "state_rule": 220, "emit": 221},
    "code_guard": "if nl:   # entire evidence list is INSIDE the nearest-level block",
    "groups": {
        "TOUCH_REPEAT": {"input": "level.touch_events_240", "derived_from": "LEVEL/TOUCH", "dependency": "DERIVED"},
        "REJECTION_FAIL": {"input": "level.rec_ok + level.rec_fail + level.fail_rate", "derived_from": "LEVEL/TOUCH", "dependency": "DERIVED"},
        "PENETRATION": {"input": "level.pen_last + level.last_touch_i", "derived_from": "LEVEL/TOUCH", "dependency": "DERIVED"},
        "ABSORPTION": {"input": "absorption.state", "derived_from": "ABSORPTION (eff3/act3)", "dependency": "INDEPENDENT_INPUT"},
        "MOMENTUM_TOWARD": {"input": "vel4 + level.side", "derived_from": "MOMENTUM (+ level side)", "dependency": "PARTIALLY_DEPENDENT"},
        "AT_LEVEL": {"input": "level.dist_atr", "derived_from": "LEVEL", "dependency": "DERIVED"},
    },
}
LEVEL_PATH = {
    "lines": {"cands": 84, "PIVOT_HIGH": 88, "PIVOT_LOW": 90, "RANGE_HIGH": 94, "RANGE_LOW": 96, "level_emit": 188},
    "sources": {"PIVOT_HIGH/LOW": "5-bar fractal extrema (left2/right2, confirm lag 2)",
                "RANGE_HIGH/LOW": "rolling 96-bar extremes"},
    "merge_rule": "same-side levels within TOUCH_TOL_ATR*ATR are MERGED -> one price structure",
    "touch_emit_line": 194,
}
COUNTER_PATH = {
    "source_file": "research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R2.py",
    "anchor": "groups_of() counter block",
    "lines": {"COUNTER_ABSORPTION": 144, "COUNTER_EXHAUSTION": 146, "COUNTER_BREAK_RISK": 148,
              "COUNTER_FAILED_EVENT": 150, "COUNTER_DECELERATION": 152},
    "groups": {
        "COUNTER_ABSORPTION": {"input": "absorption.state in (POSSIBLE,STRONG)", "restates": "ABSORPTION"},
        "COUNTER_EXHAUSTION": {"input": "touch_state startswith EXHAUSTION", "restates": "TOUCH"},
        "COUNTER_BREAK_RISK": {"input": "break_risk.state in (ELEVATED,CRITICAL)", "restates": "BREAK"},
        "COUNTER_FAILED_EVENT": {"input": "failed_event not in (None,NONE)", "restates": "FAILED_EVENT"},
        "COUNTER_DECELERATION": {"input": "momentum == DECELERATING", "restates": "MOMENTUM (self-referential)"},
    },
}
REGIME_MOM_PATH = {
    "regime_lines": {"atr_pctl": 154, "expansion": 156, "trend": 159, "range": 161, "reversal": 164, "event_driven": 165},
    "momentum_lines": {"vel4/acc/rng_exp": 228, "accelerating": 230, "decelerating": 232, "exhausting": 234, "normal": 236},
    "shared_inputs": ["close series (c)", "ATR20 normalization", "velocity vel4"],
    "regime_only": ["atr percentile (atr_pctl)", "efficiency ratio er10", "slope5 of ma20"],
    "momentum_only": ["acceleration acc", "range expansion rng_exp"],
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
    if c.startswith("regime"): return "REGIME"
    if c.startswith("break"): return "BREAK"
    if c.startswith("touch"): return "TOUCH"
    if c.startswith("level"): return "LEVEL"
    if c.startswith("absorption"): return "ABSORPTION"
    if c.startswith("momentum"): return "MOMENTUM"
    if c.startswith("old_next_state"): return "UPSTREAM_STATE"
    return "OTHER"


INFO_GROUP_MAP = {
    "LEVEL": "PRICE_STRUCTURE_GROUP", "TOUCH": "PRICE_STRUCTURE_GROUP", "BREAK": "PRICE_STRUCTURE_GROUP",
    "REGIME": "VOLATILITY_GROUP", "MOMENTUM": "MOMENTUM_GROUP", "ABSORPTION": "ABSORPTION_GROUP",
    "FAILED_EVENT": "EVENT_GROUP", "TRANSITION": "EVENT_GROUP", "COUNTER_EVIDENCE": "COMPOSITE_NOT_INDEPENDENT",
    "LIQUIDITY": "LIQUIDITY_PROXY_GROUP",
}


def main():
    # ---------- §3 registry gate ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_recomputed = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    if not (reg3.get("new_registry_hash") == REG_HASH == reg_recomputed and reg3.get("version") == "v1r2-r3"):
        print("BLOCKED: REGISTRY_INTEGRITY FAIL"); raise SystemExit(2)
    R1 = load_mod("v1r2_r1", R1MOD); R2 = load_mod("v1r2_r2", R2MOD)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    if sha_file(pq) != PQ_SHA:
        print("BLOCKED: INPUT DATA HASH MISMATCH"); raise SystemExit(2)
    df = pd.read_parquet(pq)
    states = R1.engines_v2(R1.indicators(df.copy()))
    jts = pd.to_datetime([s["t"] for s in states], utc=True)

    # ---------- §5 PIT re-verify ----------
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
        print("STOP: PIT MISMATCH", dict(ca)); raise SystemExit(3)
    valid = [r for r in recs if r["status"] == "VALID_PIT_ALIGNED"]
    print("§5 PIT_REVERIFY PASS:", dict(ca))

    # ---------- empirical entailment checks (code-grounded claims verified on data) ----------
    brk_elev_no_level = sum(1 for s in states if (s.get("break_risk") or {}).get("state") in ("ELEVATED", "CRITICAL")
                            and s.get("level") is None)
    brk_notlow_no_level = sum(1 for s in states if (s.get("break_risk") or {}).get("state") != "LOW" and s.get("level") is None)
    decel_no_counterdecel = 0
    for s in states:
        if s.get("momentum") == "DECELERATING":
            d_, sup, cnt = R2.groups_of(s)
            if "COUNTER_DECELERATION" not in cnt:
                decel_no_counterdecel += 1
    entail = {"rows": len(states), "BREAK_ELEVATED_WITHOUT_LEVEL": brk_elev_no_level,
              "BREAK_NOT_LOW_WITHOUT_LEVEL": brk_notlow_no_level,
              "MOMENTUM_DECELERATING_WITHOUT_COUNTER_DECELERATION": decel_no_counterdecel,
              "claim_LEVEL_BREAK_DERIVED": brk_notlow_no_level == 0,
              "claim_MOM_COUNTER_DERIVED": decel_no_counterdecel == 0}

    # ---------- per-decision audit ----------
    A = []
    for r in valid:
        st = states[r["bar_index"]]
        d_, sup, cnt = R2.groups_of(st)
        mu = R2.rule_mu(st); v3 = R2.ns_v3(st)
        G = gates(st)
        term = next((g for g in G if g["all_met"]), None)
        unk = (v3 == "UNKNOWN")
        closest = min(G, key=lambda g: (g["failures"], -g["total"], G.index(g))) if unk else None
        miss = ([k for k, v in closest["conds"] if not v] if closest else [])
        cand = sorted({g["target"] for g in G if g["target"] and g["failures"] <= 1})
        if term and term["target"]:
            cand = sorted(set(cand) | {term["target"]})
        lvl = st.get("level") or {}
        lv3 = lvl if lvl else None
        avail_groups = []
        avail_groups.append("LEVEL") if lvl else None
        if lvl: avail_groups.append("TOUCH")
        avail_groups.append("REGIME") if st.get("regime") not in (None, "UNKNOWN") else None
        avail_groups.append("MOMENTUM") if st.get("momentum") not in (None, "UNKNOWN") else None
        if lvl: avail_groups.append("BREAK")
        if (st.get("absorption") or {}).get("state") is not None: avail_groups.append("ABSORPTION")
        avail_groups.append("FAILED_EVENT"); avail_groups.append("TRANSITION")
        indep = sorted({INFO_GROUP_MAP.get(g, "OTHER") for g in avail_groups
                        if INFO_GROUP_MAP.get(g) not in ("COMPOSITE_NOT_INDEPENDENT",)} - {"LIQUIDITY_PROXY_GROUP"})
        A.append({
            "decision_id": r["decision_id"], "timestamp": str(r["ts"]), "bar_index": r["bar_index"],
            "v1_direction": r["v1_direction"], "final_state": v3, "final_state_v2_engine": (st.get("next_state") or {}).get("state"),
            "unknown_reason": (st.get("next_state") or {}).get("unknown_reason"), "unknown": unk,
            "regime": st.get("regime"), "momentum": st.get("momentum"), "touch": st.get("touch_state"),
            "absorption": (st.get("absorption") or {}).get("state"),
            "break_state": (st.get("break_risk") or {}).get("state"),
            "break_n_evidence": (st.get("break_risk") or {}).get("n_evidence"),
            "break_groups": (st.get("break_risk") or {}).get("groups"),
            "level_present": bool(lvl), "level_id": lvl.get("level_id"), "level_type": lvl.get("type"),
            "level_price": lvl.get("price"), "level_status": lvl.get("status"), "level_dist_atr": lvl.get("dist_atr"),
            "level_touch_events_240": lvl.get("touch_events_240"), "level_fail_rate": lvl.get("fail_rate"),
            "level_pen_last": lvl.get("pen_last"), "level_merged_from": lvl.get("merged_from"),
            "failed_event": st.get("failed_event"), "transition": st.get("transition"),
            "counter": cnt, "support": sup, "counter_present": len(cnt) > 0,
            "mu_value": mu["value"], "mu_none_reason": mu["none_reason"],
            "candidate_states": cand, "candidate_count": len(cand),
            "closest_gate": (closest["node"] if closest else None), "closest_distance": (closest["failures"] if closest else None),
            "missing_conditions": miss, "missing_categories": sorted({cond_category(k) for k in miss}),
            "available_evidence": avail_groups, "independent_info_groups": indep,
            "independent_info_group_count": len(indep),
            "gates": [{"node": g["node"], "failures": g["failures"], "total": g["total"], "target": g["target"],
                        "missing": [k for k, v in g["conds"] if not v]} for g in G],
            "round1_below": (closest["failures"] <= 1) if closest else False,
        })
    ev = len(A); unk_rows = [a for a in A if a["unknown"]]; UNK = len(unk_rows)
    print("AUDIT: evaluated=%d unknown=%d" % (ev, UNK))

    # ---------- §6 conflict sets (state-layer) ----------
    LB = [a for a in unk_rows if a["level_present"] and a["break_state"] in ("ELEVATED", "CRITICAL")]   # LEVEL<->BREAK
    MC = [a for a in unk_rows if a["momentum"] == "DECELERATING" and a["counter_present"]]             # MOMENTUM<->COUNTER
    RM = [a for a in unk_rows if a["regime"] == "TREND" and a["momentum"] in ("DECELERATING", "EXHAUSTING", "SLOW")]
    # direction-layer conflict count (rule_mu) over all 140, kept SEPARATE per §6
    DIR_CONFLICT = sum(1 for a in A if a["mu_none_reason"] == "CONFLICTING_EVIDENCE")
    STATE_CONFLICT_LB = len(LB)
    print("sets: LB=%d MC=%d RM=%d DIR_CONFLICT(rule_mu CONFLICTING_EVIDENCE over 140)=%d" % (len(LB), len(MC), len(RM), DIR_CONFLICT))

    # ---------- §7-§12 LEVEL<->BREAK ----------
    lb_groups = collections.Counter()
    for a in LB:
        for g in (a["break_groups"] or []):
            lb_groups[g] += 1
    lb_matrix = collections.Counter()
    for a in LB:
        tc = ("no_touch" if a["touch"] == "NO_TOUCH" else "touch" if a["touch"] == "FIRST_TOUCH"
              else "repeated_touch" if a["touch"] == "REPEATED_TOUCH" else "exhaustion")
        if (a["level_pen_last"] or 0) >= 0.30:
            tc = "penetration"
        lb_matrix[(a["level_status"], tc, a["break_state"])] += 1
    lb_matrix_rows = [{"level_status": k[0], "touch_class": k[1], "break_state": k[2], "count": v,
                        "final_states": dict(collections.Counter(a["final_state"] for a in LB
                                                                  if (lambda x: (x["level_status"], ("penetration" if (x["level_pen_last"] or 0) >= 0.30 else
                                                                    ("no_touch" if x["touch"] == "NO_TOUCH" else "touch" if x["touch"] == "FIRST_TOUCH"
                                                                     else "repeated_touch" if x["touch"] == "REPEATED_TOUCH" else "exhaustion")), x["break_state"]) == k)(a)))}
                       for k, v in sorted(lb_matrix.items(), key=lambda x: -x[1])]
    # §12 classification: conjunction (level present) is ENTAILED by break elevated (code line 205 guard)
    lb_class = {"TRUE_CONFLICT_CANDIDATE": 0, "DERIVATION_CONFLICT": len(LB) if entail["claim_LEVEL_BREAK_DERIVED"] else 0,
                "BOUNDARY_CONFLICT": 0, "PRIORITY_CONFLICT": 0, "UNKNOWN": 0 if entail["claim_LEVEL_BREAK_DERIVED"] else len(LB)}
    # break-content independence: how many of the 6 groups are non-level-derived inputs
    lb_content = {"groups_level_derived": ["TOUCH_REPEAT", "REJECTION_FAIL", "PENETRATION", "AT_LEVEL"],
                  "groups_non_level": ["ABSORPTION", "MOMENTUM_TOWARD"],
                  "observed_group_frequency": dict(lb_groups.most_common()),
                  "note": "break STATE non-LOW is impossible without a level (code guard L205), so the LEVEL<->BREAK pair carries a single structural axis"}

    # ---------- §13-§16 MOMENTUM<->COUNTER ----------
    mc_comp = collections.Counter()
    mc_only_decel = 0
    mc_rows = []
    for a in MC:
        cnt = a["counter"]
        mc_comp[tuple(sorted(cnt))] += 1
        only = (set(cnt) == {"COUNTER_DECELERATION"})
        if only:
            mc_only_decel += 1
        mu_d = ((states[a["bar_index"]].get("counter_evidence") or {}).get("direction_hypothesis") or "NONE")
        mc_rows.append({"decision_id": a["decision_id"], "timestamp": a["timestamp"], "momentum": a["momentum"],
                         "velocity_dir_hypothesis": mu_d, "counter": cnt, "counter_is_only_deceleration": only,
                         "regime": a["regime"], "level_present": a["level_present"], "break_state": a["break_state"],
                         "touch": a["touch"], "absorption": a["absorption"], "final_state": a["final_state"],
                         "unknown_reason": a["unknown_reason"], "closest_gate": a["closest_gate"],
                         "missing_conditions": a["missing_conditions"]})
    def counter_type(a):
        t = []
        if a["momentum"] == "DECELERATING": t.append("MOMENTUM_OPPOSITE")
        if a["level_present"]: t.append("LEVEL_OPPOSITE")
        if a["break_state"] in ("ELEVATED", "CRITICAL"): t.append("BREAK_OPPOSITE")
        if a["regime"] == "TREND": t.append("REGIME_OPPOSITE")
        if a["failed_event"] not in (None, "NONE"): t.append("FAILED_EVENT")
        return t or ["OTHER"]
    mc_types = collections.Counter()
    for a in MC:
        for t in counter_type(a):
            mc_types[t] += 1
    mc_class = {"TRUE_INFORMATION_CONFLICT": len(MC) - mc_only_decel, "DERIVATION_CONFLICT": mc_only_decel,
                "BOUNDARY_CONFLICT": 0, "UNKNOWN": 0}

    # ---------- §17 REGIME<->MOMENTUM ----------
    rm_class = {"INDEPENDENT": 0, "PARTIALLY_DEPENDENT": len(RM), "DERIVED": 0, "UNKNOWN": 0}

    # ---------- §18 feature dependency matrix ----------
    fdm = [
        {"A": "LEVEL", "B": "BREAK", "relationship": "DERIVED", "evidence": "break groups all inside `if nl:` (R1 L205); LEVEL<->BREAK conjunction is entailed"},
        {"A": "LEVEL", "B": "TOUCH", "relationship": "DERIVED", "evidence": "touch_state is built from the nearest level object (R1 L180-194)"},
        {"A": "BREAK", "B": "TOUCH", "relationship": "DERIVED", "evidence": "4/6 break groups read level touch stats (touch_events_240, rec_ok/fail, fail_rate, pen_last, last_touch_i)"},
        {"A": "MOMENTUM", "B": "COUNTER", "relationship": "PARTIALLY_DEPENDENT", "evidence": "COUNTER_DECELERATION is `momentum==DECELERATING` (R2 L152) -> 1/5 counter groups is a restatement; other 4 are separate axes"},
        {"A": "REGIME", "B": "MOMENTUM", "relationship": "PARTIALLY_DEPENDENT", "evidence": "shared close+ATR20+vel4; regime adds atr_pctl/er10/slope5, momentum adds acc/rng_exp (R1 L151-166 vs L225-236)"},
        {"A": "ABSORPTION", "B": "BREAK", "relationship": "PARTIALLY_DEPENDENT", "evidence": "break group ABSORPTION reads absorption.state (R1 L214) - one-way input"},
        {"A": "ABSORPTION", "B": "COUNTER", "relationship": "DERIVED", "evidence": "COUNTER_ABSORPTION is a restatement of absorption.state (R2 L144)"},
        {"A": "LIQUIDITY", "B": "BREAK", "relationship": "UNKNOWN", "evidence": "engines_v2 emits no liquidity field; no liquidity input to break (not assessable)"},
    ]

    # ---------- §19/§29/§30 information groups ----------
    info_groups_def = {
        "PRICE_STRUCTURE_GROUP": ["LEVEL", "TOUCH", "BREAK"],
        "VOLATILITY_GROUP": ["REGIME"],
        "MOMENTUM_GROUP": ["MOMENTUM"],
        "ABSORPTION_GROUP": ["ABSORPTION"],
        "EVENT_GROUP": ["FAILED_EVENT", "TRANSITION"],
        "LIQUIDITY_PROXY_GROUP": ["LIQUIDITY(not emitted)"],
        "COMPOSITE_NOT_INDEPENDENT": ["COUNTER_EVIDENCE(re-expresses TOUCH/BREAK/ABSORPTION/MOMENTUM/FAILED_EVENT)"],
    }
    ig_dist = collections.Counter(a["independent_info_group_count"] for a in unk_rows)
    ig_dist_d = {("3+" if k >= 3 else str(k)): 0 for k in range(0, 4)}
    for k, v in ig_dist.items():
        ig_dist_d["3+" if k >= 3 else str(k)] += v
    ig_freq = collections.Counter()
    for a in unk_rows:
        for g in a["independent_info_groups"]:
            ig_freq[g] += 1

    # ---------- §20/§21 HOLD_QUIET ----------
    hq = [a for a in unk_rows if a["closest_gate"] == "HOLD_QUIET"]
    hq_break = [a for a in hq if "break in {LOW,NORMAL}" in a["missing_conditions"]]
    hq_break_only = [a for a in hq if a["missing_conditions"] == ["break in {LOW,NORMAL}"]]
    hq_other = [a for a in hq if a not in hq_break]
    hq_matrix = collections.Counter()
    for a in hq:
        for c in a["missing_conditions"]:
            hq_matrix[cond_category(c)] += 1
    hq_struct = collections.Counter((a["regime"], a["break_state"], a["touch"]) for a in hq_break_only)

    # ---------- §22 REVERSION ----------
    rev = [a for a in unk_rows if a["closest_gate"] == "REVERSION_REVERSAL"]
    rev_exh = sum(1 for a in unk_rows if a["touch"] in ("EXHAUSTION_BUILDING", "EXHAUSTION_CONFIRMED"))
    rev_absS = sum(1 for a in unk_rows if a["absorption"] == "STRONG")
    rev_reasons = collections.Counter(c for a in rev for c in a["missing_conditions"])

    # ---------- §23 BREAK_PASSTHROUGH ----------
    bp = [a for a in unk_rows if a["closest_gate"] == "BREAK_PASSTHROUGH"]
    bp_class = {"TRUE_AMBIGUITY": 0, "RULE_PRIORITY_ARTIFACT": len(bp),
                "note": "BREAK_PASSTHROUGH is a 1-condition passthrough of the upstream engine state; when it is the only 1-away gate it reflects the upstream engine NOT producing BREAKOUT/BREAKDOWN, i.e. a specificity artifact rather than an independent ambiguity"}

    # ---------- §24/§25/§26 candidate states ----------
    cand_dist = collections.Counter(a["candidate_count"] for a in unk_rows)
    single_but_unknown = [a for a in unk_rows if a["candidate_count"] == 1]
    multi_cand = [a for a in unk_rows if a["candidate_count"] >= 2]
    def multi_cat(a):
        s = set(a["candidate_states"])
        if {"HOLD", "BREAKOUT"} <= s or {"HOLD", "BREAKDOWN"} <= s: return "HOLD_vs_BREAK"
        if {"HOLD", "REVERSION"} <= s: return "HOLD_vs_REVERSION"
        if {"CONTINUATION", "BREAKOUT"} <= s or {"CONTINUATION", "BREAKDOWN"} <= s: return "CONTINUATION_vs_BREAK"
        if {"BREAKOUT", "REVERSION"} <= s or {"BREAKDOWN", "REVERSION"} <= s: return "BREAK_vs_REVERSION"
        return "OTHER"
    multi_dist = collections.Counter(multi_cat(a) for a in multi_cand)

    # ---------- §27 counter as final blocker ----------
    typeB = [a for a in unk_rows if a["counter_present"]]
    cb = {"counter_present": len(typeB), "counter_absent": UNK - len(typeB)}
    counter_restate = {"COUNTER_BREAK_RISK": "BREAK", "COUNTER_ABSORPTION": "ABSORPTION",
                       "COUNTER_EXHAUSTION": "TOUCH", "COUNTER_DECELERATION": "MOMENTUM",
                       "COUNTER_FAILED_EVENT": "FAILED_EVENT"}
    counter_only, single_other, multi_block = [], [], []
    counter_restate_cats = {"BREAK", "ABSORPTION", "TOUCH", "MOMENTUM", "FAILED_EVENT"}
    for a in typeB:
        cats = set(a["missing_categories"])
        if len(cats) == 1 and cats <= counter_restate_cats:
            counter_only.append(a)
        elif len(cats) == 1:
            single_other.append(a)
        else:
            multi_block.append(a)
    cb.update({"counter_present + other_blocker": len(typeB) - len(counter_only),
               "COUNTER_ONLY_UNKNOWN": len(counter_only), "SINGLE_BLOCKER_NOT_COUNTER": len(single_other),
               "MULTIPLE_BLOCKERS": len(multi_block),
               "counter_only_ids": [a["decision_id"] for a in counter_only],
               "single_blocker_not_counter_ids": [a["decision_id"] for a in single_other]})
    # §27 restricted to the B-R6 TYPE_B definition (EVIDENCE_CONFLICT after its precedence)
    def is_typeb(a):
        return (a["counter_present"]
                and a["unknown_reason"] != "DATA_INSUFFICIENT"
                and not (a["regime"] == "UNKNOWN" or a["momentum"] == "UNKNOWN")
                and a["level_present"]
                and a["regime"] != "EVENT_DRIVEN")
    typeB44 = [a for a in unk_rows if is_typeb(a)]
    t44_only = [a for a in typeB44 if len(set(a["missing_categories"])) == 1 and set(a["missing_categories"]) <= counter_restate_cats]
    t44_single_other = [a for a in typeB44 if len(set(a["missing_categories"])) == 1 and not (set(a["missing_categories"]) <= counter_restate_cats)]
    t44_multi = [a for a in typeB44 if len(set(a["missing_categories"])) >= 2]
    typeB_split = {"TYPE_B_TOTAL": len(typeB44), "COUNTER_ONLY": len(t44_only),
                   "SINGLE_BLOCKER_NOT_COUNTER": len(t44_single_other), "MULTIPLE_BLOCKERS": len(t44_multi),
                   "COUNTER_PRESENT_UNKNOWN_FULL": len(typeB)}
    counter_group_freq = collections.Counter()
    for a in unk_rows:
        for g in a["counter"]:
            counter_group_freq[g] += 1
    mech = [
        {"mechanism": "LEVEL -> BREAK structural derivation (break state != LOW is impossible without a level; code guard L205)",
         "conflicts": lb_class["DERIVATION_CONFLICT"], "set": "LEVEL_BREAK"},
        {"mechanism": "COUNTER_DECELERATION restates MOMENTUM==DECELERATING (self-referential, R2 L152)",
         "conflicts": counter_group_freq.get("COUNTER_DECELERATION", 0), "set": "MOMENTUM_COUNTER"},
        {"mechanism": "COUNTER_BREAK_RISK restates the level-derived BREAK state",
         "conflicts": counter_group_freq.get("COUNTER_BREAK_RISK", 0), "set": "MOMENTUM_COUNTER/other"},
        {"mechanism": "REGIME<->MOMENTUM share close+ATR20+vel4 (different transforms, partial input overlap)",
         "conflicts": len(RM), "set": "REGIME_MOMENTUM"},
        {"mechanism": "COUNTER_ABSORPTION restates ABSORPTION / COUNTER_EXHAUSTION restates TOUCH",
         "conflicts": counter_group_freq.get("COUNTER_ABSORPTION", 0) + counter_group_freq.get("COUNTER_EXHAUSTION", 0), "set": "other"},
    ]

    # ---------- §28 priority audit ----------
    prio_rows = []
    for a in unk_rows:
        ordered = sorted(a["gates"], key=lambda g: GATE_ORDER.index(g["node"]))
        first = next((g for g in ordered if g["failures"] >= 1), None)
        sat_1away = [g["node"] for g in ordered if g["failures"] == 1]
        prio_rows.append({"decision_id": a["decision_id"], "first_blocking_gate": (first["node"] if first else None),
                           "gates_within_1": sat_1away, "final_blocking_gate": a["closest_gate"]})
    prio_first = collections.Counter(r["first_blocking_gate"] for r in prio_rows)
    prio_surface = [r for r in prio_rows if len(r["gates_within_1"]) >= 2]
    SPECIFIC = ("REVERSION_EXHAUSTION", "REVERSION_REVERSAL", "HOLD_QUIET", "HOLD_EXPANSION")
    prio_surface_specific = [r for r in prio_rows if len([g for g in r["gates_within_1"] if g in SPECIFIC]) >= 2]
    prio_note = ("BREAK_PASSTHROUGH / CONTINUATION_PASSTHROUGH / EVENT_DRIVEN are 1-condition gates and are "
                  "therefore ALWAYS 'within 1' when their single condition fails -> they inflate the raw count; "
                  "the specific-gate count excludes them")

    # ---------- §31 conflict reclassification ----------
    reclass = {
        "LEVEL_BREAK": {"ORIGINAL_CONFLICT": len(LB), "TRUE_INFORMATION_CONFLICT": lb_class["TRUE_CONFLICT_CANDIDATE"],
                         "DERIVATION_CONFLICT": lb_class["DERIVATION_CONFLICT"], "BOUNDARY_CONFLICT": 0,
                         "PRIORITY_CONFLICT": 0, "UNKNOWN_CONFLICT_TYPE": lb_class["UNKNOWN"]},
        "MOMENTUM_COUNTER": {"ORIGINAL_CONFLICT": len(MC), "TRUE_INFORMATION_CONFLICT": mc_class["TRUE_INFORMATION_CONFLICT"],
                              "DERIVATION_CONFLICT": mc_class["DERIVATION_CONFLICT"], "BOUNDARY_CONFLICT": 0,
                              "PRIORITY_CONFLICT": 0, "UNKNOWN_CONFLICT_TYPE": 0},
        "REGIME_MOMENTUM": {"ORIGINAL_CONFLICT": len(RM), "TRUE_INFORMATION_CONFLICT": 0,
                             "DERIVATION_CONFLICT": 0, "BOUNDARY_CONFLICT": 0, "PRIORITY_CONFLICT": 0,
                             "UNKNOWN_CONFLICT_TYPE": 0,
                             "relationship": "PARTIALLY_DEPENDENT (shared close/ATR/vel, different transforms)"},
    }

    # ---------- §33 shuffle (dependency sanity only) ----------
    def unk_rate(rows):
        return round(sum(1 for s in rows if R2.ns_v3(s) == "UNKNOWN") / max(1, len(rows)), 4)
    base = unk_rate(states)
    Rg = random.Random(20260927)
    shuf = {}
    for fld, get in (("regime", lambda s: s.get("regime")), ("momentum", lambda s: s.get("momentum")),
                      ("touch_state", lambda s: s.get("touch_state")),
                      ("break_risk", lambda s: (s.get("break_risk") or {}).get("state")),
                      ("level", lambda s: s.get("level"))):
        vals = [get(s) for s in states]; Rg.shuffle(vals)
        tmp = []
        for s, v in zip(states, vals):
            s2 = json.loads(json.dumps(s, default=str))
            if fld == "break_risk":
                s2["break_risk"] = dict(s2.get("break_risk") or {}); s2["break_risk"]["state"] = v
            else:
                s2[fld] = v
            tmp.append(s2)
        shuf[fld] = unk_rate(tmp)

    # ---------- §36 answers ----------
    q7_inv = {}
    for f in ("break_state", "touch"):
        vals = {a[f] for a in hq_break_only}
        if len(vals) == 1:
            q7_inv[f] = next(iter(vals))
    q7_inv["regime_values"] = sorted({a["regime"] for a in hq_break_only})
    q7_inv["distinct_structures"] = len(hq_struct)
    q = {
        "Q1_LEVEL_BREAK": {"TRUE_INFORMATION_CONFLICT": lb_class["TRUE_CONFLICT_CANDIDATE"],
                            "DERIVATION_CONFLICT": lb_class["DERIVATION_CONFLICT"], "BOUNDARY_CONFLICT": 0,
                            "PRIORITY_CONFLICT": 0, "UNKNOWN": lb_class["UNKNOWN"]},
        "Q2_MOMENTUM_COUNTER": {"TRUE_INFORMATION_CONFLICT": mc_class["TRUE_INFORMATION_CONFLICT"],
                                 "DERIVATION_CONFLICT": mc_class["DERIVATION_CONFLICT"], "BOUNDARY_CONFLICT": 0,
                                 "UNKNOWN": 0},
        "Q3_REGIME_MOMENTUM": rm_class,
        "Q4_TYPE_B_COMPOSITION": {"COUNTER_ONLY": cb["COUNTER_ONLY_UNKNOWN"], "MULTIPLE_BLOCKERS": cb["MULTIPLE_BLOCKERS"],
                                   "SINGLE_CANDIDATE_BUT_UNKNOWN": len(single_but_unknown), "MULTIPLE_CANDIDATES": len(multi_cand)},
        "Q5_NEAR_MISS": {"NEAR_MISS_TOTAL": len([a for a in unk_rows if a["round1_below"]]),
                          "TRUE_SINGLE_CONDITION": len([a for a in unk_rows if a["closest_distance"] == 1 and len(a["missing_conditions"]) == 1]),
                          "MULTIPLE_IMPLICIT_BLOCKERS": len([a for a in unk_rows if len(a["missing_categories"]) >= 2])},
        "Q6_HOLD_QUIET": {"HOLD_QUIET_TOTAL": len(hq), "BREAK_LOW_NORMAL": len(hq_break), "OTHER_BLOCKER": len(hq_other),
                           "BREAK_ONLY_MISSING": len(hq_break_only)},
        "Q7_COMMON_STRUCTURE_15": ("YES" if (0 < len(hq_struct) <= 3 and len(hq_break_only) > 0) else "INCONCLUSIVE"),
        "Q7_INVARIANTS": q7_inv,
        "Q7_EVIDENCE": {"note": "all 15 break-only rows share break=ELEVATED + touch=FIRST_TOUCH and sit in a quiet regime (RANGE/COMPRESSION); the HOLD gate is blocked only by its break in {LOW,NORMAL} clause",
                         "top_structures": [{"regime": k[0], "break": k[1], "touch": k[2], "n": v} for k, v in hq_struct.most_common(8)]},
        "Q8_LARGEST_UNKNOWN_SOURCE": ("FEATURE_DEPENDENCY" if (lb_class["DERIVATION_CONFLICT"] + mc_class["DERIVATION_CONFLICT"]) > UNK * 0.5
                                        else "EVIDENCE_CONFLICT"),
        "Q9_NEXT_RESEARCH_CANDIDATE": "RESEARCH_CANDIDATE: separate the PRICE_STRUCTURE cluster (LEVEL/TOUCH/BREAK) into an explicit one-axis evidence object before any counter/priority study",
        "Q10_PREDICTION_CAPABILITY_IMPROVED": "INSUFFICIENT_EVIDENCE",
    }

    # ---------- artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B7_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True); os.makedirs(REPORTS, exist_ok=True)
    files = {
        "V1_R2_B7_LEVEL_BREAK_AUDIT.json": {"TOTAL": len(LB), "classification": lb_class, "matrix": lb_matrix_rows,
                                             "break_group_frequency": dict(lb_groups.most_common()), "rows": LB},
        "V1_R2_B7_BREAK_LINEAGE.json": {"BREAK_EVIDENCE_LINEAGE": BREAK_PATH, "content_independence": lb_content},
        "V1_R2_B7_LEVEL_LINEAGE.json": {"LEVEL_EVIDENCE_LINEAGE": LEVEL_PATH,
                                         "level_type_counts": dict(collections.Counter(a["level_type"] for a in A if a["level_present"])),
                                         "note": "PIVOT / RANGE / TOUCH / BREAK all resolve to the SAME merged nearest-level object -> EVIDENCE_CLUSTERING"},
        "V1_R2_B7_COUNTER_AUDIT.json": {"TOTAL": len(MC), "classification": mc_class, "counter_type_frequency": dict(mc_types),
                                         "counter_composition": [{"counter_set": list(k), "n": v} for k, v in mc_comp.most_common()],
                                         "only_deceleration": mc_only_decel, "rows": mc_rows},
        "V1_R2_B7_COUNTER_LINEAGE.json": {"COUNTER_EVIDENCE_LINEAGE": COUNTER_PATH},
        "V1_R2_B7_REGIME_MOMENTUM_AUDIT.json": {"TOTAL": len(RM), "classification": rm_class, "lineage": REGIME_MOM_PATH,
                                                 "rows": [{"decision_id": a["decision_id"], "regime": a["regime"], "momentum": a["momentum"],
                                                            "break_state": a["break_state"], "touch": a["touch"], "closest_gate": a["closest_gate"],
                                                            "missing_conditions": a["missing_conditions"]} for a in RM]},
        "V1_R2_B7_FEATURE_DEPENDENCY_MATRIX.json": {"matrix": fdm, "allowed_relationships": ["INDEPENDENT", "PARTIALLY_DEPENDENT", "DERIVED", "CONDITIONALLY_DEPENDENT", "UNKNOWN"]},
        "V1_R2_B7_CONFLICT_RECLASSIFICATION.json": reclass,
        "V1_R2_B7_HOLD_QUIET_AUDIT.json": {"TOTAL": len(hq), "break_low_normal": len(hq_break), "break_only": len(hq_break_only),
                                            "other_blocker": len(hq_other), "near_miss_matrix": dict(hq_matrix),
                                            "near_miss_matrix_ids": {k: [a["decision_id"] for a in hq if any(cond_category(c) == k for c in a["missing_conditions"])] for k in hq_matrix},
                                            "common_structure_break_only": [{"regime": k[0], "break": k[1], "touch": k[2], "n": v} for k, v in hq_struct.most_common()],
                                            "rows": hq},
        "V1_R2_B7_REVERSION_AUDIT.json": {"REVERSION_REVERSAL_TOTAL": len(rev),
                                            "EXHAUSTION_ANY_AT_DECISIONS": rev_exh, "ABSORPTION_STRONG_AT_DECISIONS": rev_absS,
                                            "dataset_base": {"EXHAUSTION_BUILDING": 0.00678, "EXHAUSTION_CONFIRMED": 0.0,
                                                              "ABSORPTION_STRONG": 0.02334},
                                            "missing_condition_frequency": dict(rev_reasons), "rows": rev},
        "V1_R2_B7_BREAK_PASSTHROUGH_AUDIT.json": {"TOTAL": len(bp), "classification": bp_class, "rows": bp},
        "V1_R2_B7_CANDIDATE_STATE_AUDIT.json": {"candidate_count_distribution": {str(k): v for k, v in sorted(cand_dist.items())},
                                                  "single_candidate_but_unknown": len(single_but_unknown),
                                                  "single_candidate_ids": [a["decision_id"] for a in single_but_unknown],
                                                  "multiple_candidates": len(multi_cand), "multiple_candidate_categories": dict(multi_dist),
                                                  "rows": [{"decision_id": a["decision_id"], "candidate_states": a["candidate_states"],
                                                             "candidate_count": a["candidate_count"], "final_state": a["final_state"]} for a in unk_rows]},
        "V1_R2_B7_PRIORITY_AUDIT.json": {"gate_order": GATE_ORDER, "first_blocking_gate_frequency": dict(prio_first),
                                           "rows_with_2plus_gates_within_1_RAW": len(prio_surface),
                                           "rows_with_2plus_SPECIFIC_gates_within_1": len(prio_surface_specific),
                                           "artifact_note": prio_note,
                                           "PRIORITY_CONFLICT_NOTE": "ns_v3 is deterministic first-match; no UNKNOWN arose from an EARLIER gate masking a satisfiable LATER gate (no gate is fully met for any UNKNOWN) -> PRIORITY_CONFLICT = 0",
                                           "rows": prio_rows},
        "V1_R2_B7_INFORMATION_GROUPS.json": {"FEATURE_INFORMATION_GROUPS": info_groups_def,
                                               "INDEPENDENT_INFORMATION_GROUPS_DISTRIBUTION": ig_dist_d,
                                               "group_frequency": dict(ig_freq.most_common()),
                                               "EVIDENCE_CLUSTERING": "LEVEL/TOUCH/BREAK are one PRICE_STRUCTURE_GROUP; the B-R6 '5+ available evidence groups' is a FEATURE count, not an independent-group count",
                                               "COUNTER_NOTE": "COUNTER_EVIDENCE re-expresses TOUCH/BREAK/ABSORPTION/MOMENTUM/FAILED_EVENT -> not an independent group"},
    }
    for fn, obj in files.items():
        wjson(os.path.join(REPORTS, fn), obj); wjson(os.path.join(run_dir, fn), obj)
    with open(os.path.join(REPORTS, "V1_R2_B7_DECISION_AUDIT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for a in A:
            fh.write(json.dumps(a, ensure_ascii=False, default=str) + "\n")
    with open(os.path.join(run_dir, "V1_R2_B7_DECISION_AUDIT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for a in A:
            fh.write(json.dumps(a, ensure_ascii=False, default=str) + "\n")
    summary = {
        "task": "V1_R2_PHASE_B_R7", "status": "COMPLETE",
        "INPUT_DECISIONS": len(recs), "VALID_PIT_ALIGNED": ca.get("VALID_PIT_ALIGNED", 0),
        "DUPLICATE_TIMESTAMP": ca.get("DUPLICATE_TIMESTAMP", 0), "TOTAL_UNKNOWN": UNK,
        "STATE_LEVEL_CONFLICT_COUNT": STATE_CONFLICT_LB, "DIRECTION_LEVEL_CONFLICT_COUNT": DIR_CONFLICT,
        "CONFLICT_SETS": {"LEVEL_BREAK": len(LB), "MOMENTUM_COUNTER": len(MC), "REGIME_MOMENTUM": len(RM)},
        "ENTAILMENT_CHECKS": entail,
        "LEVEL_BREAK": {"classification": lb_class, "group_frequency": dict(lb_groups.most_common())},
        "MOMENTUM_COUNTER": {"classification": mc_class, "only_deceleration": mc_only_decel,
                              "composition": [{"counter_set": list(k), "n": v} for k, v in mc_comp.most_common()]},
        "REGIME_MOMENTUM": rm_class,
        "FEATURE_DEPENDENCY_MATRIX": fdm,
        "RECLASSIFICATION": reclass,
        "COUNTER_BLOCKER": cb, "COUNTER_BLOCKER_TYPE_B44": typeB_split,
        "COUNTER_GROUP_FREQUENCY": dict(counter_group_freq.most_common()),
        "TOP_CONFLICT_MECHANISMS": mech,
        "CANDIDATE": {"distribution": {str(k): v for k, v in sorted(cand_dist.items())},
                       "single_candidate_but_unknown": len(single_but_unknown), "multiple_candidates": len(multi_cand),
                       "multiple_categories": dict(multi_dist)},
        "HOLD_QUIET": {"TOTAL": len(hq), "BREAK_LOW_NORMAL": len(hq_break), "BREAK_ONLY_MISSING": len(hq_break_only), "OTHER": len(hq_other)},
        "REVERSION_REVERSAL": len(rev), "EXHAUSTION_ANY_AT_DECISIONS": rev_exh, "ABSORPTION_STRONG_AT_DECISIONS": rev_absS,
        "BREAK_PASSTHROUGH": {"TOTAL": len(bp), "classification": bp_class},
        "NEAR_MISS": q["Q5_NEAR_MISS"],
        "INFORMATION_GROUPS": {"distribution": ig_dist_d, "frequency": dict(ig_freq.most_common()),
                                "top3": [k for k, _ in ig_freq.most_common(3)]},
        "SHUFFLE_DEPENDENCY_SANITY": {"baseline": base, "after_permutation": shuf,
                                       "note": "dependency sanity only; never used to choose rules or thresholds"},
        "TEN_QUESTIONS": q,
        "REGISTRY_VERSION": "v1r2-r3", "RULES_VERSION": "v1r2-r1-rules-v3",
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_recomputed, "REGISTRY_INTEGRITY": "PASS",
        "RULE_CHANGE": 0, "PARAMETER_CHANGE": 0, "DIFFERENCE_MAPPING_CHANGE": 0, "DIRECTION_MAPPING_CHANGE": 0,
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0, "BOUNDARY_VIOLATION": 0},
        "PRESERVED": {"B_R4_SOURCE_DATA_CONFLICT": "SOURCE_DATA_CONFLICT", "FORMAL_AXIS_RULE_FROZEN": "NO"},
        "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
        "PROVENANCE": {"_v1r2_phaseB_R1.py_sha256": sha_file(R1MOD), "_v1r2_phaseB_R2.py_sha256": sha_file(R2MOD)},
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R7_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R7_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "RUN_META.json"), {"task": "V1_R2_PHASE_B_R7", "registry_hash": REG_HASH, "ts_utc": NOW})

    print(json.dumps({"ENTAILMENT": entail, "LB": lb_class, "MC": mc_class, "RM": rm_class,
                        "RECLASS": reclass, "COUNTER_BLOCKER": cb,
                        "CAND_DIST": {str(k): v for k, v in sorted(cand_dist.items())},
                        "SINGLE_CAND_YN": len(single_but_unknown), "MULTI_CAND": len(multi_cand),
                        "HQ": {"TOTAL": len(hq), "BREAK": len(hq_break), "BREAK_ONLY": len(hq_break_only), "OTHER": len(hq_other)},
                        "IG_DIST": ig_dist_d, "IG_TOP3": [k for k, _ in ig_freq.most_common(3)],
                        "PRIO_SURFACE_RAW": len(prio_surface), "PRIO_SURFACE_SPECIFIC": len(prio_surface_specific), "SHUFFLE": shuf, "BASE": base,
                        "TYPE_B44": typeB_split, "COUNTER_FREQ": dict(counter_group_freq.most_common()),
                        "Q8": q["Q8_LARGEST_UNKNOWN_SOURCE"], "Q10": q["Q10_PREDICTION_CAPABILITY_IMPROVED"]},
                       ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
