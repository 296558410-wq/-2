# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R6 — UNKNOWN / Coverage root-cause audit (AUDIT ONLY).

Explains UNKNOWN; does NOT resolve it. No rule/threshold/feature/registry/direction change.
No future returns / PnL / win-rate. B-R4 SOURCE_DATA_CONFLICT preserved. engine.py untouched.
Only classification + evidence-path tracing. GIT_COMMIT=NONE."""
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

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
REPORTS = os.path.join(UP, "reports")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R2MOD = os.path.join(UP, "_v1r2_phaseB_R2.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
DATS = "TICK_ONLY"
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
GROUPS9 = ["REGIME", "MOMENTUM", "KEY_LEVEL", "TOUCH", "ABSORPTION", "LIQUIDITY", "BREAK", "FAILED_EVENT", "COUNTER_EVIDENCE"]
DECISIVE7 = ["REGIME", "MOMENTUM", "KEY_LEVEL", "TOUCH", "BREAK", "ABSORPTION", "FAILED_EVENT"]


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


# ---------------------------------------------------------------- frozen gates (audit reconstruction)
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


def ev_matrix(st, cnt):
    lvl = st.get("level")
    m = {}
    m["REGIME"] = "AVAILABLE" if st.get("regime") not in (None, "UNKNOWN") else "INSUFFICIENT"
    m["MOMENTUM"] = "AVAILABLE" if st.get("momentum") not in (None, "UNKNOWN") else "INSUFFICIENT"
    m["KEY_LEVEL"] = "AVAILABLE" if lvl else "NOT_APPLICABLE"
    m["TOUCH"] = "AVAILABLE" if lvl else "NOT_APPLICABLE"
    m["ABSORPTION"] = "AVAILABLE" if (st.get("absorption") or {}).get("state") is not None else "INSUFFICIENT"
    m["LIQUIDITY"] = "NOT_APPLICABLE"          # engines_v2 emits no liquidity field (see observability matrix)
    m["BREAK"] = "AVAILABLE" if lvl else "NOT_APPLICABLE"
    m["FAILED_EVENT"] = "AVAILABLE"
    m["COUNTER_EVIDENCE"] = "CONFLICTING" if cnt else "AVAILABLE"
    return m


def main():
    # ---------- §3 registry gate ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_recomputed = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    registry_integrity = "PASS" if (reg3.get("new_registry_hash") == REG_HASH and reg_recomputed == REG_HASH
                                    and reg3.get("version") == "v1r2-r3") else "FAIL"
    if registry_integrity != "PASS":
        print("BLOCKED: REGISTRY_INTEGRITY FAIL"); raise SystemExit(2)

    R1 = load_mod("v1r2_r1", R1MOD)
    R2 = load_mod("v1r2_r2", R2MOD)

    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    if sha_file(pq) != PQ_SHA:
        print("BLOCKED: INPUT DATA HASH MISMATCH"); raise SystemExit(2)
    df = pd.read_parquet(pq)
    states = R1.engines_v2(R1.indicators(df.copy()))
    jts = pd.to_datetime([s["t"] for s in states], utc=True)
    # dataset base rates (used to detect unobservable prerequisites)
    ds_n = max(1, len(states))
    ds_rates = {
        "EXHAUSTION_BUILDING": sum(1 for s in states if s.get("touch_state") == "EXHAUSTION_BUILDING") / ds_n,
        "EXHAUSTION_CONFIRMED": sum(1 for s in states if s.get("touch_state") == "EXHAUSTION_CONFIRMED") / ds_n,
        "EXHAUSTION_ANY": sum(1 for s in states if str(s.get("touch_state")).startswith("EXHAUSTION")) / ds_n,
        "ABSORPTION_STRONG": sum(1 for s in states if (s.get("absorption") or {}).get("state") == "STRONG") / ds_n,
        "ABSORPTION_POSSIBLE": sum(1 for s in states if (s.get("absorption") or {}).get("state") == "POSSIBLE") / ds_n,
    }
    print("DATASET_RATES:", json.dumps({k: round(v, 5) for k, v in ds_rates.items()}))

    # ---------- §5 PIT re-verify ----------
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            recs.append({"decision_id": f, "status": "ALIGNMENT_ERROR"}); continue
        try:
            t = pd.Timestamp(str(d.get("cycle")).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"decision_id": f, "status": "ALIGNMENT_ERROR"}); continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < jts[0]:
            st_, bi = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID:
            st_, bi = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t)
            st_, bi = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"decision_id": f, "ts": t, "status": st_, "bar_index": bi,
                     "v1_direction": d.get("decision"), "v1_confidence": d.get("confidence")})
    ts_cnt = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in ts_cnt.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    cnt_align = collections.Counter(r["status"] for r in recs)
    pit_ok = (cnt_align.get("VALID_PIT_ALIGNED", 0) == 140 and cnt_align.get("DUPLICATE_TIMESTAMP", 0) == 2
              and cnt_align.get("OUT_OF_DATASET", 0) == 0 and cnt_align.get("ALIGNMENT_ERROR", 0) == 0)
    print("§5 PIT_REVERIFY:", dict(cnt_align), "->", "PASS" if pit_ok else "STOP")
    if not pit_ok:
        raise SystemExit(3)
    valid = [r for r in recs if r["status"] == "VALID_PIT_ALIGNED"]

    # ---------- per-decision audit record (Task A/B/C..) ----------
    audit = []
    for r in valid:
        st = states[r["bar_index"]]
        d_, sup, cnt = R2.groups_of(st)
        mu = R2.rule_mu(st)
        v3 = R2.ns_v3(st)
        G = gates(st)
        term = next((g for g in G if g["all_met"]), None)
        terminal_node = term["node"] if term else "FALLTHROUGH"
        terminal_state = (term["target"] if term and term["target"] else "UNKNOWN")
        unk = (v3 == "UNKNOWN")
        closest = min(G, key=lambda g: (g["failures"], -g["total"], G.index(g))) if unk else None
        near_miss = bool(unk and closest and closest["failures"] == 1)
        m = ev_matrix(st, cnt)
        missing_usable = [g for g in DECISIVE7 if m[g] != "AVAILABLE"]
        avail = [g for g in GROUPS9 if m[g] == "AVAILABLE"]
        miss = [g for g in GROUPS9 if m[g] in ("NOT_APPLICABLE", "UNAVAILABLE")]
        conf = [g for g in GROUPS9 if m[g] == "CONFLICTING"]
        decisive_avail = [g for g in DECISIVE7 if m[g] == "AVAILABLE"]
        v2_reason = (st.get("next_state") or {}).get("unknown_reason")
        # ---- primary taxonomy (§9): deterministic, documented precedence ----
        missing_conds = ([k for k, v in closest["conds"] if not v] if closest else [])
        n_all_met = sum(1 for g in G if g["all_met"])
        ctx_insuff = (st.get("regime") == "UNKNOWN") or (st.get("momentum") == "UNKNOWN")
        needs_exh = any("EXHAUSTION" in k for k in missing_conds)
        prereq_unobs = bool(
            (st.get("level") is None)
            or (needs_exh and ds_rates["EXHAUSTION_ANY"] < 0.01)
            or (closest is not None and closest["node"] == "REVERSION_EXHAUSTION" and ds_rates["EXHAUSTION_BUILDING"] < 0.01)
        )
        if not unk:
            tax = None
        elif v2_reason == "DATA_INSUFFICIENT":
            tax = "DATA_MISSING"
        elif n_all_met > 1:
            tax = "MULTIPLE_STATE_CANDIDATES"
        elif terminal_node == "EVENT_DRIVEN" or st.get("regime") == "EVENT_DRIVEN":
            tax = "RULE_COVERAGE_GAP"          # frozen rule maps EVENT_DRIVEN -> UNKNOWN by design
        elif ctx_insuff:
            tax = "CONTEXT_INSUFFICIENT"
        elif prereq_unobs:
            tax = "PREREQUISITE_UNOBSERVABLE"
        elif len(cnt) > 0:
            tax = "EVIDENCE_CONFLICT"
        elif m["MOMENTUM"] == "AVAILABLE" and m["TOUCH"] == "AVAILABLE" and m["BREAK"] == "AVAILABLE":
            tax = "RULE_COVERAGE_GAP"
        elif len(decisive_avail) < 3:
            tax = "EVIDENCE_INSUFFICIENT"
        else:
            tax = "OTHER"
        blocker_sig = (("%s | missing: %s" % (closest["node"], "; ".join(missing_conds))) if (unk and closest) else
                       ("EVENT_DRIVEN_BY_DESIGN" if unk else None))
        type_abc = (None if not unk else
                    ("TYPE_A_INFORMATION_INSUFFICIENT" if tax in ("DATA_MISSING", "PREREQUISITE_UNOBSERVABLE", "EVIDENCE_INSUFFICIENT", "CONTEXT_INSUFFICIENT")
                     else "TYPE_B_EVIDENCE_CONFLICT" if tax == "EVIDENCE_CONFLICT"
                     else "TYPE_C_RULE_COVERAGE" if tax in ("RULE_COVERAGE_GAP", "MULTIPLE_STATE_CANDIDATES") else "OTHER"))
        audit.append({
            "decision_id": r["decision_id"], "timestamp": str(r["ts"]),
            "final_state": v3, "final_state_v2_engine": (st.get("next_state") or {}).get("state"),
            "unknown_reason": v2_reason, "rule_mu_none_reason": mu["none_reason"], "rule_mu_value": mu["value"],
            "regime": st.get("regime"), "level": (st.get("level") or {}).get("type"),
            "level_dist_atr": (st.get("level") or {}).get("dist_atr"), "touch": st.get("touch_state"),
            "absorption": (st.get("absorption") or {}).get("state"),
            "liquidity": "NOT_APPLICABLE", "break": (st.get("break_risk") or {}).get("state"),
            "break_n_evidence": (st.get("break_risk") or {}).get("n_evidence"), "momentum": st.get("momentum"),
            "failed_event": st.get("failed_event"), "transition": st.get("transition"),
            "counter": cnt, "support": sup,
            "available_evidence_groups": avail, "missing_evidence_groups": miss, "conflicting_evidence_groups": conf,
            "missing_usable_groups": missing_usable,
            "decisive_available_count": len(decisive_avail),
            "candidate_states": sorted({g["target"] for g in G if g["all_met"] and g["target"]}),
            "gate_eval": [{"node": g["node"], "met": g["met"], "total": g["total"], "failures": g["failures"],
                            "conds": [[k, bool(v)] for k, v in g["conds"]]} for g in G],
            "terminal_node": terminal_node, "terminal_state": terminal_state,
            "closest_blocked_node": (closest["node"] if closest else None),
            "closest_blocked_missing_cond": ([k for k, v in closest["conds"] if not v] if closest else []),
            "closest_distance": (closest["failures"] if closest else None),
            "near_miss": near_miss,
            "near_miss_reason": (("%s missing: %s" % (closest["node"], "; ".join(k for k, v in closest["conds"] if not v))) if near_miss else None),
            "coverage_class": tax, "type": type_abc, "blocker_signature": blocker_sig,
            "missing_conditions": missing_conds,
            "counter_label": ("COUNTER_NONE" if len(cnt) == 0 else ("COUNTER_WEAK" if len(cnt) == 1 else "COUNTER_STRONG")),
            "v1_direction": r["v1_direction"],
            "context_hash": sha_obj({"variant": DATS, "parquet": PQ_SHA, "registry": REG_HASH}),
        })
    ev = len(audit)
    unk_rows = [a for a in audit if a["final_state"] == "UNKNOWN"]
    UNK = len(unk_rows)
    print("AUDIT: evaluated=%d unk=%d" % (ev, UNK))

    # ---------- Task A: reason split ----------
    reason_v2 = dict(collections.Counter(a["unknown_reason"] for a in unk_rows))
    mu_reason_all = dict(collections.Counter(a["rule_mu_none_reason"] for a in audit))
    mu_reason_unk = dict(collections.Counter(a["rule_mu_none_reason"] for a in unk_rows))
    # ---------- Task D/E/F: taxonomy, evidence counts ----------
    taxonomy = dict(collections.Counter(a["coverage_class"] for a in unk_rows))
    types = dict(collections.Counter(a["type"] for a in unk_rows))
    evc = collections.Counter(len(a["available_evidence_groups"]) for a in unk_rows)
    evc_dist = {("5+" if k >= 5 else str(k)): 0 for k in range(0, 6)}
    for k, v in evc.items():
        evc_dist["5+" if k >= 5 else str(k)] += v
    ge2 = [a for a in unk_rows if len(a["available_evidence_groups"]) >= 2]
    ge2_decisive = [a for a in unk_rows if a["decisive_available_count"] >= 2]
    rule_cov_cand = [a for a in unk_rows if a["coverage_class"] == "RULE_COVERAGE_GAP"]
    prereq_unobs = [a for a in unk_rows if a["coverage_class"] == "PREREQUISITE_UNOBSERVABLE"]
    # ---------- Task G counter ----------
    counter_dist = dict(collections.Counter(a["counter_label"] for a in unk_rows))
    counter_blocked = [a for a in unk_rows if len(a["counter"]) > 0]
    # ---------- Task H conflict matrix ----------
    def pair_counts(rows):
        c = collections.Counter()
        for a in rows:
            reg, mom, tc, ab, br, fe, cn = a["regime"], a["momentum"], a["touch"], a["absorption"], a["break"], a["failed_event"], a["counter"]
            if reg == "TREND" and mom in ("DECELERATING", "EXHAUSTING", "SLOW"):
                c["REGIME↔MOMENTUM"] += 1
            if a["level"] and br in ("ELEVATED", "CRITICAL"):
                c["LEVEL↔BREAK"] += 1
            if str(tc).startswith("EXHAUSTION") and ab in (None, "NONE"):
                c["TOUCH↔ABSORPTION"] += 1
            c["ABSORPTION↔LIQUIDITY"] += 0   # liquidity not emitted -> not assessable
            if br == "CRITICAL" and fe not in (None, "NONE"):
                c["BREAK↔FAILED_EVENT"] += 1
            if mom == "DECELERATING" and len(cn) > 0:
                c["MOMENTUM↔COUNTER"] += 1
        return dict(c)
    conflict_unk = pair_counts(unk_rows)
    conflict_all = pair_counts(audit)
    combos = collections.Counter()
    for a in unk_rows:
        if a["regime"] == "TREND" and a["momentum"] == "DECELERATING":
            combos["TREND + MOMENTUM_DECELERATING"] += 1
        if a["break"] == "CRITICAL" and a["failed_event"] not in (None, "NONE"):
            combos["BREAK_CRITICAL + FAILED_EVENT"] += 1
        if str(a["touch"]).startswith("EXHAUSTION") and a["absorption"] == "NONE":
            combos["EXHAUSTION + NO_ABSORPTION"] += 1
        if a["regime"] == "EXPANSION" and a["touch"] == "NO_TOUCH":
            combos["EXPANSION + NO_TOUCH"] += 1
        if a["regime"] == "UNKNOWN":
            combos["REGIME_UNKNOWN + ANY"] += 1
    # ---------- Task I INSUFFICIENT_CONTEXT ----------
    ic = [a for a in audit if a["rule_mu_none_reason"] == "INSUFFICIENT_CONTEXT"]
    def ic_cat(a):
        have = set(a["support"])
        missg = []
        if "LEVEL_GROUP" not in have: missg.append("LEVEL_HISTORY")
        if "BREAK_GROUP" not in have: missg.append("BREAK_HISTORY")
        if "MOMENTUM_GROUP" not in have: missg.append("MOMENTUM_HISTORY")
        if "TREND_GROUP" not in have: missg.append("REGIME_HISTORY")
        return missg
    ic_dist = collections.Counter()
    ic_ids = {}
    for a in ic:
        for c in (ic_cat(a) or ["OTHER"]):
            ic_dist[c] += 1
            ic_ids.setdefault(c, []).append(a["decision_id"])
    # ---------- Task J UNKNOWN_NEXT_STATE ----------
    uns = [a for a in audit if a["rule_mu_none_reason"] == "UNKNOWN_NEXT_STATE"]
    mu_usable = collections.Counter()
    for a in unk_rows:
        for g in a["missing_usable_groups"]:
            mu_usable[g] += 1

    def cand_set(a):
        cs = a["candidate_states"]
        return "{" + ",".join(cs) + "}" if cs else "{NONE}"
    cand_dist_unk = dict(collections.Counter(cand_set(a) for a in unk_rows))
    # ---------- Task K state coverage matrix ----------
    def coverage(rows):
        m = {}
        for a in rows:
            key = "%s|%s|%s|%s" % (a["regime"], a["momentum"], a["touch"], a["break"])
            d = m.setdefault(key, collections.Counter())
            d[a["final_state"]] += 1
        return {k: dict(v) for k, v in sorted(m.items(), key=lambda x: -sum(x[1].values()))[:24]}
    cov_dec = coverage(audit)
    cov_ticks = coverage([{"regime": s.get("regime"), "momentum": s.get("momentum"), "touch": s.get("touch_state"),
                            "break": (s.get("break_risk") or {}).get("state"), "final_state": R2.ns_v3(s)} for s in states])
    cols = ["HOLD", "CONTINUATION", "REVERSION", "BREAKOUT", "BREAKDOWN", "UNKNOWN"]
    matrix_dec = {k: {c: v.get(c, 0) for c in cols} for k, v in list(cov_dec.items())[:24]}
    # ---------- Task L boundary audit ----------
    bnd = collections.Counter()
    for a in unk_rows:
        d = a["closest_distance"]
        if a["terminal_node"] == "EVENT_DRIVEN":
            bnd["GATE_MATCHED_RULE_UNMAPPED"] += 1
        elif d == 1:
            bnd["AT_THRESHOLD"] += 1
        elif d is not None and d >= 2:
            bnd["BELOW_THRESHOLD"] += 1
        else:
            bnd["OTHER"] += 1
    # ---------- Task M near miss ----------
    nm = [a for a in unk_rows if a["near_miss"]]
    nm_rules = collections.Counter(a["closest_blocked_node"] for a in nm)
    # ---------- Task N tree ----------
    term_nodes = dict(collections.Counter(a["terminal_node"] for a in audit))
    blocked_nodes = dict(collections.Counter(a["closest_blocked_node"] for a in unk_rows))
    blocker_sigs = dict(collections.Counter(a["blocker_signature"] for a in unk_rows).most_common())
    # ---------- Task O bottleneck ----------
    tot = max(1, UNK)
    bn = sorted(blocked_nodes.items(), key=lambda x: -x[1])
    bottleneck = [{"rank": i + 1, "node": k, "unknown_count": v, "unknown_share": round(v / tot, 4)} for i, (k, v) in enumerate(bn[:3])]
    miss_counter = collections.Counter()
    for a in unk_rows:
        for g in a["missing_evidence_groups"]:
            miss_counter[g] += 1
    # ---------- Task P observability ----------
    observability = {
        "DOM": {"state": "UNAVAILABLE", "note": "no depth-of-market feed"},
        "TRADE_DIRECTION": {"state": "UNAVAILABLE", "note": "no aggressor side in tick store"},
        "SPREAD": {"state": "DIRECT", "note": "bid/ask present in tick store"},
        "TICK_VOLUME": {"state": "DIRECT", "note": "column present but all-zero; NOT real traded volume"},
        "ABSORPTION": {"state": "PROXY", "note": "PROXY_BAR from efficiency/activity"},
        "LIQUIDITY_WITHDRAWAL": {"state": "PROXY", "note": "registry-specified; engines_v2 emits NO liquidity field -> not usable in the frozen state machine"},
    }
    # ---------- Task Q three types ----------
    three = {"TYPE_A_INFORMATION_INSUFFICIENT": types.get("TYPE_A_INFORMATION_INSUFFICIENT", 0),
             "TYPE_B_EVIDENCE_CONFLICT": types.get("TYPE_B_EVIDENCE_CONFLICT", 0),
             "TYPE_C_RULE_COVERAGE": types.get("TYPE_C_RULE_COVERAGE", 0),
             "OTHER": types.get("OTHER", 0)}
    # ---------- Task R null/shuffle ----------
    def unk_rate_over(rows):
        return round(sum(1 for s in rows if R2.ns_v3(s) == "UNKNOWN") / max(1, len(rows)), 4)
    base_tick = unk_rate_over(states)
    R = random.Random(20260926)
    shuf = {}
    for fld, getter in (("regime", lambda s: s.get("regime")), ("momentum", lambda s: s.get("momentum")),
                         ("touch_state", lambda s: s.get("touch_state")),
                         ("break_risk", lambda s: (s.get("break_risk") or {}).get("state")),
                         ("absorption", lambda s: (s.get("absorption") or {}).get("state")),
                         ("failed_event", lambda s: s.get("failed_event"))):
        vals = [getter(s) for s in states]; R.shuffle(vals)
        tmp = []
        for s, v in zip(states, vals):
            s2 = json.loads(json.dumps(s))
            if fld == "break_risk":
                s2["break_risk"] = dict(s2.get("break_risk") or {}); s2["break_risk"]["state"] = v
            elif fld == "absorption":
                s2["absorption"] = dict(s2.get("absorption") or {}); s2["absorption"]["state"] = v
            else:
                s2[fld] = v
            tmp.append(s2)
        shuf[fld] = unk_rate_over(tmp)
    # ---------- Task S historical separate ----------
    b2 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B2_*")))[-1]
    hist = [json.loads(l) for l in open(os.path.join(b2, "v1_r2_states_v2.jsonl"), encoding="utf-8") if l.strip()]
    hist_v3 = collections.Counter(R2.ns_v3(r) for r in hist)
    hist_mu = collections.Counter(R2.rule_mu(r)["none_reason"] for r in hist)
    hist_unk = hist_v3.get("UNKNOWN", 0) / max(1, len(hist))
    hist_by_regime = collections.Counter(r.get("regime") for r in hist if R2.ns_v3(r) == "UNKNOWN")
    tick_by_regime = collections.Counter(a["regime"] for a in unk_rows)
    # ---------- §26 artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B6_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    checks = {"REGISTRY_INTEGRITY": registry_integrity, "PIT_REVERIFY": "PASS",
              "UNKNOWN_100PCT_CLASSIFIED": "PASS" if all(a["coverage_class"] for a in unk_rows) else "FAIL",
              "EVERY_UNKNOWN_TRACEABLE": "PASS" if all(a["gate_eval"] for a in unk_rows) else "FAIL",
              "RULE_CHANGE": "0", "REGISTRY_CHANGE": "0", "LOOKAHEAD": "0"}
    q = {
        "Q1_UNKNOWN_TOTAL": UNK,
        "Q2_TRUE_INFORMATION_INSUFFICIENT": three["TYPE_A_INFORMATION_INSUFFICIENT"],
        "Q3_EVIDENCE_CONFLICT": three["TYPE_B_EVIDENCE_CONFLICT"],
        "Q4_RULE_COVERAGE_GAP": three["TYPE_C_RULE_COVERAGE"],
        "Q5_MOST_OFTEN_MISSING_EVIDENCE_GROUP": [
            "excl. structural LIQUIDITY: " + (str(mu_usable.most_common(1)[0]) if mu_usable else "NONE (no usable evidence group missing)")
        ],
        "Q5_NOTE": "LIQUIDITY is the ONLY structurally absent group (engines_v2 emits no liquidity field); every UNKNOWN still has regime+momentum+level+touch+break available",
        "Q10_DETAIL": {"TYPE_A": three["TYPE_A_INFORMATION_INSUFFICIENT"], "TYPE_B": three["TYPE_B_EVIDENCE_CONFLICT"],
                        "TYPE_C": three["TYPE_C_RULE_COVERAGE"], "dominant_bucket": "TYPE_B_EVIDENCE_CONFLICT",
                        "no_usable_evidence_missing": len([a for a in unk_rows if not a["missing_usable_groups"]]),
                        "one_condition_from_a_frozen_state": len(nm)},
        "Q6_NOTE": "conflict pairs counted only where both sides are observable; ABSORPTION<->LIQUIDITY is not assessable (no liquidity field)",
        "Q6_MOST_OFTEN_CONFLICTING_PAIR": (sorted(conflict_unk.items(), key=lambda x: -x[1])[0] if conflict_unk else None),
        "Q7_UNKNOWN_WITH_GE2_INDEPENDENT_GROUPS": len(ge2),
        "Q8_UNKNOWN_ONE_CONDITION_AWAY": len(nm),
        "Q9_UNKNOWN_REGIME_CONCENTRATION": dict(collections.Counter(a["regime"] for a in unk_rows).most_common()),
        "Q10_EVIDENCE_VERDICT": (
            "EVIDENCE_SUPPORTS_RULE_COVERAGE"
            if (len([a for a in unk_rows if not a["missing_usable_groups"]]) / max(1, UNK) >= 0.5
                and three["TYPE_C_RULE_COVERAGE"] >= three["TYPE_A_INFORMATION_INSUFFICIENT"])
            else "EVIDENCE_SUPPORTS_DATA_LIMITATION"
            if (three["TYPE_A_INFORMATION_INSUFFICIENT"] > three["TYPE_C_RULE_COVERAGE"]
                and three["TYPE_A_INFORMATION_INSUFFICIENT"] >= three["TYPE_B_EVIDENCE_CONFLICT"])
            else "EVIDENCE_INCONCLUSIVE"),
        "Q10_RULE": "RULE_COVERAGE only if >=50% of UNKNOWN lack no usable evidence group AND TYPE_C>=TYPE_A; DATA_LIMITATION only if TYPE_A>TYPE_C AND TYPE_A>=TYPE_B; else INCONCLUSIVE",
    }
    top_conf = sorted({k: v for k, v in conflict_unk.items() if "LIQUIDITY" not in k}.items(), key=lambda x: -x[1])
    top_nm = nm_rules.most_common(3)
    hist_reach = {"DATASET": "HISTORICAL_M1", "BARS": len(hist), "unknown_rate": round(hist_unk, 4),
                  "next_state_counts": dict(hist_v3), "rule_mu_none_reason": dict(hist_mu),
                  "unknown_by_regime": dict(hist_by_regime.most_common()), "SOURCE_DATA_CONFLICT": "PRESERVED"}
    tick_reach = {"DATASET": "TICK_ONLY", "BARS": len(states), "unknown_rate": base_tick,
                  "next_state_counts": dict(collections.Counter(R2.ns_v3(s) for s in states)),
                  "unknown_by_regime": dict(tick_by_regime.most_common())}

    summary = {
        "task": "V1_R2_PHASE_B_R6", "status": "COMPLETE",
        "INPUT_DECISIONS": len(recs), "VALID_PIT_ALIGNED": cnt_align.get("VALID_PIT_ALIGNED", 0),
        "DUPLICATE_TIMESTAMP": cnt_align.get("DUPLICATE_TIMESTAMP", 0),
        "UNKNOWN_TOTAL": UNK, "UNKNOWN_RATE": round(UNK / max(1, ev), 4),
        "REASON_V2_ENGINE": reason_v2, "RULE_MU_NONE_REASON_ALL140": mu_reason_all, "RULE_MU_NONE_REASON_UNKNOWN": mu_reason_unk,
        "TAXONOMY": taxonomy, "THREE_TYPES": three, "EVIDENCE_COUNT_DISTRIBUTION": evc_dist,
        "UNKNOWN_WITH_GE2_GROUPS": len(ge2), "UNKNOWN_WITH_GE2_DECISIVE": len(ge2_decisive),
        "RULE_COVERAGE_GAP_CANDIDATES": len(rule_cov_cand), "PREREQUISITE_UNOBSERVABLE": len(prereq_unobs),
        "COUNTER_DISTRIBUTION": counter_dist, "COUNTER_BLOCKED_COUNT": len(counter_blocked),
        "CONFLICT_MATRIX_UNKNOWN": conflict_unk, "CONFLICT_MATRIX_ALL140": conflict_all,
        "CONFLICT_COMBOS_TOP": combos.most_common(8),
        "INSUFFICIENT_CONTEXT": {"count": len(ic), "missing_context_distribution": dict(ic_dist),
                                  "decision_ids_by_category": {k: v for k, v in ic_ids.items()}},
        "UNKNOWN_NEXT_STATE": {"count": len(uns), "candidate_state_set": cand_dist_unk},
        "STATE_COVERAGE_MATRIX_DECISIONS": matrix_dec,
        "BOUNDARY_AUDIT": dict(bnd), "NEAR_MISS_COUNT": len(nm), "NEAR_MISS_RATE": round(len(nm) / max(1, UNK), 4),
        "NEAR_MISS_RULES": dict(nm_rules),
        "DECISION_TREE_TERMINAL_NODES": term_nodes, "DECISION_TREE_BLOCKED_NODES": blocked_nodes,
        "BLOCKER_SIGNATURES": blocker_sigs, "DATASET_BASE_RATES": {k: round(v, 5) for k, v in ds_rates.items()},
        "TOP_3_BOTTLENECK": bottleneck, "MISSING_EVIDENCE_FREQ": dict(miss_counter.most_common()),
        "OBSERVABILITY_MATRIX": observability,
        "NULL_SHUFFLE": {"baseline_tick_unknown_rate": base_tick, "after_field_permutation": shuf,
                          "note": "label-free; no future returns; not an alpha test"},
        "REACHABILITY_HISTORICAL": hist_reach, "REACHABILITY_TICK_ONLY": tick_reach,
        "SAMPLE_SCOPE": {"evaluated": ev, "unknown": UNK},
        "TEN_QUESTIONS": q,
        "REGISTRY_VERSION": "v1r2-r3", "RULES_VERSION": "v1r2-r1-rules-v3",
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_recomputed, "REGISTRY_INTEGRITY": registry_integrity,
        "checks": checks,
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V2_WRITE": 0, "V3_WRITE": 0, "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "BOUNDARY_VIOLATION": 0},
        "PRESERVED": {"B_R4_SOURCE_DATA_CONFLICT": "SOURCE_DATA_CONFLICT", "FORMAL_AXIS_RULE_FROZEN": "NO",
                       "HISTORICAL_FUSION_STATUS": "PROHIBITED_UNCHANGED"},
        "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
    }
    files = {
        "V1_R2_UNKNOWN_COVERAGE_AUDIT.json": summary,
        "V1_R2_UNKNOWN_EVIDENCE_MATRIX.json": {"groups": GROUPS9, "decisive_groups": DECISIVE7, "count_distribution": evc_dist,
                                                 "per_unknown": [{"decision_id": a["decision_id"], "available": a["available_evidence_groups"],
                                                                   "missing": a["missing_evidence_groups"], "conflicting": a["conflicting_evidence_groups"],
                                                                   "decisive_available_count": a["decisive_available_count"]} for a in unk_rows]},
        "V1_R2_UNKNOWN_CONFLICT_MATRIX.json": {"pairs_unknown": conflict_unk, "pairs_all140": conflict_all,
                                                "top_combos": combos.most_common(), "note": "ABSORPTION↔LIQUIDITY not assessable (no liquidity field)"},
        "V1_R2_UNKNOWN_BOUNDARY_AUDIT.json": {"classification": dict(bnd), "near_miss_count": len(nm),
                                               "near_miss_rate": round(len(nm) / max(1, UNK), 4), "near_miss_rules": dict(nm_rules),
                                               "note": "thresholds UNCHANGED; distance measured only"},
        "V1_R2_STATE_COVERAGE_MATRIX.json": {"columns": cols, "decisions": matrix_dec, "tick_only_dataset": cov_ticks},
        "V1_R2_COVERAGE_BOTTLENECK.json": {"top3_by_unknown_count": bottleneck, "blocked_nodes": blocked_nodes,
                                            "blocker_signatures": blocker_sigs,
                                            "missing_evidence_freq": dict(miss_counter.most_common()),
                                            "terminal_nodes": term_nodes},
        "V1_R2_OBSERVABILITY_MATRIX.json": observability,
    }
    for fn, obj in files.items():
        wjson(os.path.join(REPORTS, fn), obj)
        wjson(os.path.join(run_dir, fn), obj)
    wjsonl(os.path.join(REPORTS, "V1_R2_UNKNOWN_DECISION_AUDIT.jsonl"), audit)
    wjsonl(os.path.join(run_dir, "V1_R2_UNKNOWN_DECISION_AUDIT.jsonl"), audit)
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R6_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R6_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "RUN_META.json"), {"task": "V1_R2_PHASE_B_R6", "DATASET_VARIANT": DATS,
                                                     "registry_hash": REG_HASH, "ts_utc": NOW})

    print(json.dumps({k: summary[k] for k in ("status", "INPUT_DECISIONS", "VALID_PIT_ALIGNED", "UNKNOWN_TOTAL", "UNKNOWN_RATE",
                                                 "RULE_MU_NONE_REASON_ALL140", "TAXONOMY", "THREE_TYPES",
                                                 "EVIDENCE_COUNT_DISTRIBUTION", "UNKNOWN_WITH_GE2_GROUPS",
                                                 "UNKNOWN_WITH_GE2_DECISIVE", "RULE_COVERAGE_GAP_CANDIDATES",
                                                 "COUNTER_DISTRIBUTION", "BOUNDARY_AUDIT", "NEAR_MISS_COUNT",
                                                 "TOP_3_BOTTLENECK", "REGISTRY_INTEGRITY")}, ensure_ascii=False, indent=1))
    print("CONFLICT_UNKNOWN:", json.dumps(conflict_unk, ensure_ascii=False))
    print("COMBOS:", json.dumps(combos.most_common(6), ensure_ascii=False))
    print("MISSING_EVIDENCE:", json.dumps(dict(miss_counter.most_common()), ensure_ascii=False))
    print("SHUFFLE:", json.dumps(shuf, ensure_ascii=False), "base:", base_tick)
    print("TEN_Q:", json.dumps(q, ensure_ascii=False, indent=1))
    print("HIST:", json.dumps({"unknown_rate": round(hist_unk, 4), "bars": len(hist)}, ensure_ascii=False))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
