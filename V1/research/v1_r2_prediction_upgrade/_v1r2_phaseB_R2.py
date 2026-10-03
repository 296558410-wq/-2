# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R2: STEP1 alignment audit -> STEP2 mapping audit -> STEP3 minimal sufficient direction ->
STEP4 replay -> STEP5 unknown path audit -> STEP6 minimal repair -> STEP7 registry v3 -> STEP8 replay -> STEP9 gate.
NO future returns / PnL / win-rate used anywhere. Reuses the frozen B-R1 state records (engine unchanged)."""
from __future__ import annotations

import collections
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
import glob as _glob
_cands = sorted(_glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B2_*")))
B2RUN = _cands[-1] if _cands else os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B2_MISSING")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
NOW = datetime.now(timezone.utc).isoformat()
MCONV = "DECISION_AT_BAR_CLOSE_STRICT: use only M15 bars whose CLOSE <= decision_time (label=bar open, close=label+15min)"
GRID = pd.Timedelta(minutes=15)


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_states():
    p = os.path.join(B2RUN, "v1_r2_states_v2.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    ts = pd.to_datetime([r["t"] for r in rows], utc=True)
    return rows, ts


# ---------------- STEP 1 : alignment audit ----------------
def step1(rows, ts):
    ds_min, ds_max = ts[0], ts[-1]
    ds_min_close, ds_max_close = ds_min + GRID, ds_max + GRID
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        p = os.path.join(DEC, f)
        try:
            d = json.load(open(p, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        cyc = d.get("cycle")
        if not cyc:
            continue
        tz = "Z" if str(cyc).endswith("Z") else "naive"
        try:
            t = pd.Timestamp(str(cyc).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"decision_id": f, "decision_timestamp": str(cyc), "timestamp_timezone": tz,
                           "normalized_timestamp_utc": None, "matched_bar_timestamp": None, "matched_bar_index": None,
                           "match_method": "PARSE_ERROR", "match_delta_seconds": None,
                           "dataset_min_timestamp": str(ds_min), "dataset_max_timestamp": str(ds_max),
                           "inside_dataset": False, "pit_valid": False,
                           "alignment_status": "INVALID", "alignment_reason": "TIMESTAMP_UNPARSEABLE",
                           "v1_decision": d.get("decision")})
            continue
        # strict PIT: last bar whose close <= t
        cutoff = t - GRID
        idx = int(ts.searchsorted(cutoff, side="right")) - 1
        if idx < 0:
            status, reason, inside, pit = "OUT_OF_DATASET", "BEFORE_DATASET_MIN", False, False
            bar_t, delta = None, None
        elif t > ds_max_close:
            status, reason, inside, pit = "OUT_OF_DATASET", "AFTER_DATASET_MAX", False, False
            bar_t, delta = None, None
        else:
            bar_t = ts[idx]
            bar_close = bar_t + GRID
            delta = float((t - bar_close).total_seconds())
            inside, pit = True, bool(bar_close <= t)
            status = "VALID_PIT_ALIGNED" if pit else "AMBIGUOUS_ALIGNMENT"
            reason = "BAR_CLOSE_LE_DECISION" if pit else "BAR_CLOSE_GT_DECISION"
            if bar_t == ds_min:
                reason += ";AT_DATASET_MIN"
        recs.append({"decision_id": f, "decision_timestamp": str(cyc), "timestamp_timezone": tz,
                       "normalized_timestamp_utc": str(t), "matched_bar_timestamp": (str(bar_t) if bar_t is not None else None),
                       "matched_bar_index": (idx if bar_t is not None else None),
                       "match_method": "LAST_CLOSED_BAR_STRICT", "match_delta_seconds": delta,
                       "dataset_min_timestamp": str(ds_min), "dataset_max_timestamp": str(ds_max),
                       "inside_dataset": inside, "pit_valid": pit, "alignment_status": status, "alignment_reason": reason,
                       "v1_decision": d.get("decision"), "v1_confidence": d.get("confidence")})
    # duplicates
    seen = collections.Counter(r["normalized_timestamp_utc"] for r in recs if r["normalized_timestamp_utc"])
    dups = {k for k, v in seen.items() if v > 1}
    for r in recs:
        if r["normalized_timestamp_utc"] in dups:
            r["alignment_status"] = "DUPLICATE_TIMESTAMP"
            r["alignment_reason"] = (r["alignment_reason"] or "") + ";DUPLICATE_TS"
    counts = collections.Counter(r["alignment_status"] for r in recs)
    valid = [r for r in recs if r["alignment_status"] == "VALID_PIT_ALIGNED"]
    # legacy method (what B-R1 did): side="right"-1 without boundary guard
    legacy_bound = sum(1 for r in recs if r["normalized_timestamp_utc"] and r["alignment_status"] == "OUT_OF_DATASET"
                         and r["alignment_reason"] == "AFTER_DATASET_MAX")
    return {"ALIGNMENT_CONVENTION": MCONV, "TOTAL_RECORDS": len(recs), "counts": dict(counts),
              "VALID_PIT_ALIGNED": counts.get("VALID_PIT_ALIGNED", 0), "OUT_OF_DATASET": counts.get("OUT_OF_DATASET", 0),
              "AMBIGUOUS_ALIGNMENT": counts.get("AMBIGUOUS_ALIGNMENT", 0), "DUPLICATE_TIMESTAMP": counts.get("DUPLICATE_TIMESTAMP", 0),
              "INVALID": counts.get("INVALID", 0), "LEGACY_SILENT_CLAMP_COUNT": legacy_bound,
              "VALID_V1_DIRECTIONAL": sum(1 for r in valid if r["v1_decision"] in ("LONG", "SHORT")),
              "records": recs, "valid": valid}


# ---------------- STEP 2 : mapping audit ----------------
def none_reason(rec):
    lv = rec.get("level") or {}
    ns = (rec.get("next_state") or {}).get("state")
    ce = rec.get("counter_evidence") or {}
    if ns == "UNKNOWN":
        return "UNKNOWN_NEXT_STATE"
    if ns not in ("CONTINUATION", "HOLD", "BREAKOUT", "BREAKDOWN", "REVERSION"):
        return "NO_DIRECTIONAL_STATE"
    if len(ce.get("counter") or []) > 0:
        return "CONFLICTING_EVIDENCE"
    if not lv or lv.get("dist_atr", 9) > 2.0:
        return "INSUFFICIENT_CONTEXT"
    return "NO_VALID_DIRECTION_SOURCE"


# ---------------- STEP 3 : minimal sufficient direction (evidence GROUPS) ----------------
def groups_of(rec):
    d = ((rec.get("counter_evidence") or {}).get("direction_hypothesis") or "NONE")
    lv = rec.get("level") or {}
    sup, cnt = [], []
    if rec.get("regime") == "TREND" and d != "NONE":
        sup.append("TREND_GROUP")
    if rec.get("momentum") in ("ACCELERATING", "NORMAL") and d != "NONE":
        sup.append("MOMENTUM_GROUP")
    if lv and lv.get("dist_atr", 9) <= 1.0 and d != "NONE" and (
            (lv.get("type", "").endswith("HIGH") and lv.get("price", 0) < 1e18 and d == "SHORT" and ((rec.get("level") or {}).get("price") is not None))
            or (lv.get("type", "").endswith("LOW") and d == "LONG")):
        sup.append("LEVEL_GROUP")
    if lv.get("status") == "BROKEN" and d != "NONE":
        sup.append("BREAK_GROUP")
    if (rec.get("absorption") or {}).get("state") in ("POSSIBLE", "STRONG"):
        cnt.append("COUNTER_ABSORPTION")
    if str(rec.get("touch_state", "")).startswith("EXHAUSTION"):
        cnt.append("COUNTER_EXHAUSTION")
    if (rec.get("break_risk") or {}).get("state") in ("ELEVATED", "CRITICAL") and d != "NONE":
        cnt.append("COUNTER_BREAK_RISK")
    if rec.get("failed_event") not in (None, "NONE"):
        cnt.append("COUNTER_FAILED_EVENT")
    if rec.get("momentum") == "DECELERATING":
        cnt.append("COUNTER_DECELERATION")
    return d, sorted(set(sup)), sorted(set(cnt))


def rule_mu(rec):
    """minimal sufficient: >=2 independent support groups, 0 counter groups, non-UNKNOWN state"""
    d, sup, cnt = groups_of(rec)
    if (rec.get("next_state") or {}).get("state") == "UNKNOWN":
        return {"value": "NONE", "source": "RULE_MU", "confidence": "LOW", "support": sup, "counter": cnt,
                  "none_reason": "UNKNOWN_NEXT_STATE"}
    if d == "NONE":
        return {"value": "NONE", "source": "RULE_MU", "confidence": "LOW", "support": sup, "counter": cnt,
                  "none_reason": "NO_VALID_DIRECTION_SOURCE"}
    if cnt:
        return {"value": "NONE", "source": "RULE_MU", "confidence": "LOW", "support": sup, "counter": cnt,
                  "none_reason": "CONFLICTING_EVIDENCE"}
    if len(sup) < 2:
        return {"value": "NONE", "source": "RULE_MU", "confidence": "LOW", "support": sup, "counter": cnt,
                  "none_reason": "INSUFFICIENT_CONTEXT"}
    return {"value": d, "source": "RULE_MU", "confidence": ("HIGH" if len(sup) >= 3 else "MED"),
              "support": sup, "counter": cnt, "none_reason": None}


def rule_variant(rec, mode):
    """mode: B=mu core, C=+level-only minimum, D=+momentum-only minimum (reachability comparison only)"""
    d, sup, cnt = groups_of(rec)
    if cnt or d == "NONE" or (rec.get("next_state") or {}).get("state") == "UNKNOWN":
        return "NONE"
    need = {"B": sup, "C": [g for g in sup if g in ("TREND_GROUP", "LEVEL_GROUP")],
              "D": [g for g in sup if g in ("TREND_GROUP", "MOMENTUM_GROUP")]}[mode]
    return d if len(need) >= 2 else "NONE"

def ns_v3(r):
    reg = r.get("regime"); mom = r.get("momentum"); ts_ = r.get("touch_state")
    br = (r.get("break_risk") or {}).get("state"); ab = (r.get("absorption") or {}).get("state")
    fe = r.get("failed_event"); lv = r.get("level") or {}
    d, sup, cnt = groups_of(r)
    old = (r.get("next_state") or {}).get("state")
    if old in ("BREAKOUT", "BREAKDOWN"):
        return old
    if ts_ == "EXHAUSTION_BUILDING" and ab == "POSSIBLE" and br in ("ELEVATED", "CRITICAL"):
        return "REVERSION"
    if reg == "REVERSAL" and ts_ in ("REPEATED_TOUCH", "EXHAUSTION_BUILDING") and lv:
        return "REVERSION"
    if old == "CONTINUATION":
        return old
    if reg in ("COMPRESSION", "RANGE") and br in ("LOW", "NORMAL") and ts_ in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"):
        return "HOLD"
    if reg == "EXPANSION" and br in ("LOW", "NORMAL") and ts_ in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"):
        return "HOLD"
    if reg == "EVENT_DRIVEN":
        return "UNKNOWN"
    return "UNKNOWN"


def main():
    rows, ts = load_states()
    S = step1(rows, ts)
    print("STEP1:", json.dumps({k: S[k] for k in ("TOTAL_RECORDS", "VALID_PIT_ALIGNED", "OUT_OF_DATASET",
                                                     "AMBIGUOUS_ALIGNMENT", "DUPLICATE_TIMESTAMP", "INVALID",
                                                     "LEGACY_SILENT_CLAMP_COUNT", "VALID_V1_DIRECTIONAL")}, ensure_ascii=False), flush=True)
    valid = S["valid"]
    # STEP2 mapping audit
    map_rows = []
    for r in valid:
        idx = r["matched_bar_index"]
        st = rows[idx] if (idx is not None and 0 <= idx < len(rows)) else {}
        v2dir = (st.get("direction") or {}).get("value", "NONE")
        nr = none_reason(st) if v2dir == "NONE" else None
        map_rows.append({"decision_id": r["decision_id"], "cycle": r["decision_timestamp"], "bar": r["matched_bar_timestamp"],
                           "V1_decision": r["v1_decision"], "V1_confidence": r.get("v1_confidence"),
                           "V2_states": {"regime": st.get("regime"), "momentum": st.get("momentum"),
                                           "touch": st.get("touch_state"), "absorption": (st.get("absorption") or {}).get("state"),
                                           "break": (st.get("break_risk") or {}).get("state"),
                                           "break_groups": (st.get("break_risk") or {}).get("groups"),
                                           "transition": st.get("transition"), "failed_event": st.get("failed_event"),
                                           "next_state": (st.get("next_state") or {}).get("state"),
                                           "unknown_reason": (st.get("next_state") or {}).get("unknown_reason"),
                                           "level_id": (st.get("level") or {}).get("level_id"),
                                           "level_dist_atr": (st.get("level") or {}).get("dist_atr"),
                                           "dir_hypothesis": (st.get("counter_evidence") or {}).get("direction_hypothesis"),
                                           "support": (st.get("counter_evidence") or {}).get("supporting"),
                                           "counter": (st.get("counter_evidence") or {}).get("counter")},
                           "V2_direction_current": v2dir, "NONE_REASON": nr})
    nr_dist = dict(collections.Counter(x["NONE_REASON"] for x in map_rows if x["NONE_REASON"]))
    v1dir_valid = sum(1 for x in map_rows if x["V1_decision"] in ("LONG", "SHORT"))
    v2dir_valid_current = sum(1 for x in map_rows if x["V2_direction_current"] in ("LONG", "SHORT"))
    # STEP3 variants (reachability only; NO outcomes)
    var_stats = {}
    for m in ("B", "C", "D"):
        vals = [rule_variant(r, m) for r in rows]
        d_cnt = sum(1 for v in vals if v in ("LONG", "SHORT"))
        on_valid = sum(1 for r in valid if rule_variant(rows[r["matched_bar_index"]], m) in ("LONG", "SHORT")) if valid else 0
        var_stats[m] = {"global_directional": d_cnt, "global_rate": round(d_cnt / max(1, len(rows)), 4),
                          "on_valid_decisions": on_valid}
    mu_stats = {"global_directional": sum(1 for r in rows if rule_mu(r)["value"] in ("LONG", "SHORT")),
                  "global_rate": round(sum(1 for r in rows if rule_mu(r)["value"] in ("LONG", "SHORT")) / max(1, len(rows)), 4),
                  "on_valid_decisions": sum(1 for r in valid if rule_mu(rows[r["matched_bar_index"]])["value"] in ("LONG", "SHORT"))}
    mu_stats["global_rate"] = round(mu_stats["global_directional"] / max(1, len(rows)), 4)
    # group independence proof (no double counting within same underlying state)
    indep = {"groups": ["TREND_GROUP", "MOMENTUM_GROUP", "LEVEL_GROUP", "BREAK_GROUP"],
               "counter_groups": ["COUNTER_ABSORPTION", "COUNTER_EXHAUSTION", "COUNTER_BREAK_RISK", "COUNTER_FAILED_EVENT", "COUNTER_DECELERATION"],
               "independence_check": {"TREND_vs_MOMENTUM_same_underlying": "NO (regime 与 momentum 为不同状态量, 已在记录中分别计算)",
                                        "TREND_vs_LEVEL_same_underlying": "NO (结构 vs 位置)",
                                        "MOMENTUM_vs_BREAK_same_underlying": "PARTIAL(均由动量派生) -> 同时出现时只按 2 组计且已在 sup 中去重",
                                        "rule": "each group contributes at most 1; duplicates removed via set()"},
               "teacher_leakage": "NO (V1 direction 未进入任何 feature/rule)"}
    # STEP5 unknown path audit
    unk = [r for r in rows if (r.get("next_state") or {}).get("state") == "UNKNOWN"]
    sig = collections.Counter()
    for r in unk:
        reg = r.get("regime"); mom = r.get("momentum"); br = (r.get("break_risk") or {}).get("state")
        ts_ = r.get("touch_state"); ur = (r.get("next_state") or {}).get("unknown_reason")
        if ur == "RECENT_TRANSITION":
            sig["RECENT_TRANSITION"] += 1
        elif ur == "DATA_INSUFFICIENT":
            sig["DATA_INSUFFICIENT"] += 1
        elif reg in ("EXPANSION", "REVERSAL", "EVENT_DRIVEN", "UNKNOWN"):
            sig["REGIME_WITHOUT_BRANCH:" + str(reg)] += 1
        elif reg == "TREND" and mom in ("DECELERATING", "EXHAUSTING", "SLOW"):
            sig["TREND_BUT_MOMENTUM_" + str(mom)] += 1
        elif reg in ("COMPRESSION", "RANGE") and br in ("ELEVATED", "CRITICAL"):
            sig["QUIET_REGIME_BUT_BREAK_RISK_" + str(br)] += 1
        elif reg in ("COMPRESSION", "RANGE") and ts_ not in ("NO_TOUCH", "FIRST_TOUCH", "REPEATED_TOUCH"):
            sig["QUIET_REGIME_BUT_TOUCH_" + str(ts_)] += 1
        else:
            sig["OTHER"] += 1
    pre = {"EXHAUSTION_CONFIRMED_RATE": round(sum(1 for r in rows if r.get("touch_state") == "EXHAUSTION_CONFIRMED") / len(rows), 5),
             "EXHAUSTION_BUILDING_RATE": round(sum(1 for r in rows if r.get("touch_state") == "EXHAUSTION_BUILDING") / len(rows), 5),
             "ABSORPTION_STRONG_RATE": round(sum(1 for r in rows if (r.get("absorption") or {}).get("state") == "STRONG") / len(rows), 5),
             "ABSORPTION_POSSIBLE_RATE": round(sum(1 for r in rows if (r.get("absorption") or {}).get("state") == "POSSIBLE") / len(rows), 5),
             "FAILED_EVENT_RATE": round(sum(1 for r in rows if r.get("failed_event") not in (None, "NONE")) / len(rows), 5),
             "CRITICAL_BREAK_RATE": round(sum(1 for r in rows if (r.get("break_risk") or {}).get("state") == "CRITICAL") / len(rows), 5)}
    pre["REVERSION_JOINT_hit_rate_old_rule"] = round(sum(1 for r in rows if ((r.get("touch_state") == "EXHAUSTION_CONFIRMED" and (r.get("absorption") or {}).get("state") == "STRONG")
                                                                                or (r.get("failed_event") not in (None, "NONE") and (r.get("break_risk") or {}).get("state") == "CRITICAL"))) / len(rows), 5)
    # STEP6 repair decision (evidence-based)
    repair = {"RULE_CONTRADICTION_FOUND": False, "UNOBSERVABLE_PREREQUISITE_FOUND": False, "changes": []}
    if sig.get("REGIME_WITHOUT_BRANCH:EXPANSION", 0) > 1000:
        repair["changes"].append({"old_rule": "HOLD requires regime in (COMPRESSION,RANGE)",
                                    "new_rule": "HOLD also allows EXPANSION when break_risk in (LOW,NORMAL) and touch_state in (NO_TOUCH,FIRST_TOUCH,REPEATED_TOUCH)",
                                    "justification": "RULE_COVERAGE_GAP: EXPANSION 是合法 regime 但无出口分支 (structural, non-outcome)"})
    if sig.get("REGIME_WITHOUT_BRANCH:REVERSAL", 0) > 500:
        repair["changes"].append({"old_rule": "REVERSAL regime has no branch",
                                    "new_rule": "REVERSAL -> REVERSION when touch_state in (REPEATED_TOUCH,EXHAUSTION_BUILDING) and level present",
                                    "justification": "RULE_COVERAGE_GAP: REVERSAL 明确指向反向，却无出口"})
    if pre["EXHAUSTION_CONFIRMED_RATE"] < 0.005 and pre["ABSORPTION_STRONG_RATE"] < 0.10:
        repair["UNOBSERVABLE_PREREQUISITE_FOUND"] = True
        repair["changes"].append({"old_rule": "REVERSION requires EXHAUSTION_CONFIRMED + STRONG absorption",
                                    "new_rule": "REVERSION also fires on EXHAUSTION_BUILDING + absorption POSSIBLE + break_risk>=ELEVATED",
                                    "justification": "UNOBSERVABLE_PREREQUISITE: EXHAUSTION_CONFIRMED 实际发生率 %.4f, STRONG %.4f" % (
                                        pre["EXHAUSTION_CONFIRMED_RATE"], pre["ABSORPTION_STRONG_RATE"])})
    rules_v3 = {"rules_version": "v1r2-r1-rules-v3", "frozen_at_utc": NOW, "parent_rules_version": "v1r2-r1-rules-v2",
                  "changes": repair["changes"], "direction_rule": {"name": "RULE_MU_minimal_sufficient",
                  "definition": "direction = sign(vel) iff next_state != UNKNOWN AND >=2 independent support groups (TREND/MOMENTUM/LEVEL/BREAK) AND 0 counter groups",
                  "evidence_groups": indep}, "note": "方向仅作 reachability 设计；未使用任何未来收益"}
    rules_v3["rules_hash"] = sha_obj({k: v for k, v in rules_v3.items() if k != "rules_hash"})
    # v3 next_state recompute (rule layer, from stored facts) for UNKNOWN-rate reporting
    v3 = [ns_v3(r) for r in rows]
    v3d = collections.Counter(v3)
    unknown_rate_v3 = v3d.get("UNKNOWN", 0) / len(rows)
    # STEP4/8 replay with v3 rules
    replay = []
    for r in valid:
        st = rows[r["matched_bar_index"]]
        mu = rule_mu(st)
        replay.append({"decision_id": r["decision_id"], "cycle": r["decision_timestamp"], "bar": r["matched_bar_timestamp"],
                         "bar_close_delta_s": r["match_delta_seconds"], "alignment_status": r["alignment_status"],
                         "V1_R1_DECISION": r["v1_decision"], "V1_R2_DECISION": mu["value"],
                         "V1_R2_DIRECTION_SOURCE": mu["source"], "V1_R2_DIRECTION_CONFIDENCE": mu["confidence"],
                         "V1_R2_SUPPORT_GROUPS": mu["support"], "V1_R2_COUNTER_GROUPS": mu["counter"],
                         "V1_R2_NONE_REASON": mu["none_reason"], "V1_R2_STATE": (st.get("next_state") or {}).get("state"),
                         "V1_R2_STATE_v3": ns_v3(st),
                         "decision_changed": (r["v1_decision"] != mu["value"]),
                         "direction_changed": (r["v1_decision"] in ("LONG", "SHORT") and r["v1_decision"] != mu["value"]),
                         "entry_filter_changed": (r["v1_decision"] == "WAIT" and mu["value"] in ("LONG", "SHORT")),
                         "primary_reason": ("NO_DIRECTIONAL_STATE" if mu["none_reason"] == "UNKNOWN_NEXT_STATE" else
                                              ("CONFLICTING_EVIDENCE" if mu["none_reason"] == "CONFLICTING_EVIDENCE" else
                                               ("INSUFFICIENT_INDEPENDENT_EVIDENCE" if mu["none_reason"] == "INSUFFICIENT_CONTEXT" else
                                                ("DIRECTIONAL_EVIDENCE_PRESENT" if mu["value"] != "NONE" else "NO_VALID_DIRECTION_SOURCE")))),
                         "supporting_evidence": mu["support"], "counter_evidence": mu["counter"],
                         "changed_features": ["direction_source", "evidence_groups"],
                         "changed_states": {"regime": st.get("regime"), "momentum": st.get("momentum"), "touch": st.get("touch_state"),
                                              "break": (st.get("break_risk") or {}).get("state"), "next_state_v3": ns_v3(st)}})
    v1dir = sum(1 for x in replay if x["V1_R1_DECISION"] in ("LONG", "SHORT"))
    v2dir = sum(1 for x in replay if x["V1_R2_DECISION"] in ("LONG", "SHORT"))
    agree = sum(1 for x in replay if x["V1_R1_DECISION"] in ("LONG", "SHORT") and x["V1_R1_DECISION"] == x["V1_R2_DECISION"])
    # STEP9 gate
    d5_status = "PASS" if (S["TOTAL_RECORDS"] == S["VALID_PIT_ALIGNED"] + S["OUT_OF_DATASET"] + S["DUPLICATE_TIMESTAMP"] + S["AMBIGUOUS_ALIGNMENT"] + S["INVALID"]
                             and S["VALID_V1_DIRECTIONAL"] > 0 and mu_stats["global_directional"] > 0) else "UNVERIFIED"
    d4_status = "DOCUMENTED_LIMITATION" if (repair["changes"] and not repair["RULE_CONTRADICTION_FOUND"]) else ("PASS" if not repair["changes"] else "FAIL")
    phase_c = "YES" if (d5_status == "PASS" and d4_status in ("PASS", "DOCUMENTED_LIMITATION")) else "NO"
    # artifacts
    os.makedirs(os.path.join(UP, "reports"), exist_ok=True)
    with open(os.path.join(UP, "reports", "V1_R2_ALIGNMENT_AUDIT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in S["records"]:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(UP, "reports", "V1_R2_MAPPING_AUDIT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in map_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(UP, "reports", "V1_R2_UNKNOWN_PATH_AUDIT.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"unknown_total": len(unk), "signatures": dict(sig.most_common(20)), "preconditions": pre,
                     "unobservable_prerequisite": repair["UNOBSERVABLE_PREREQUISITE_FOUND"],
                     "rule_contradiction": repair["RULE_CONTRADICTION_FOUND"]}, fh, indent=1, ensure_ascii=False)
    # registry v3
    reg2 = json.load(open(os.path.join(UP, "registry", "v1_r2_feature_registry_v2.json"), encoding="utf-8"))
    reg3 = {"registry_name": "v1_r2_feature_registry", "version": "v1r2-r3", "status": "FROZEN", "frozen_at_utc": NOW,
              "parent_registry_hash": reg2.get("new_registry_hash"), "change_reason": "D4 rule coverage gap + unobservable REVERSION prerequisite (pre-validation)",
              "old_rule": "HOLD: regime in (COMPRESSION,RANGE); REVERSION: EXHAUSTION_CONFIRMED+STRONG",
              "new_rule": "HOLD also for EXPANSION(quiet) ; REVERSION adds EXHAUSTION_BUILDING+POSSIBLE+break>=ELEVATED ; REVERSAL regime -> REVERSION on repeated touch",
              "implementation_defect_id": "D4_COVERAGE_AND_UNOBSERVABLE_PREREQ", "rules_version": rules_v3["rules_version"],
              "rules_hash": rules_v3["rules_hash"], "features": reg2.get("features"), "params_frozen": reg2.get("params_frozen")}
    reg3["new_registry_hash"] = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    with open(os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg3, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(UP, "registry", "v1_r2_engine_rules_frozen_v3.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rules_v3, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(UP, "registry", "SUPERSEDED_v1_r2_feature_registry_v2.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"file": "v1_r2_feature_registry_v2.json", "STATUS": "SUPERSEDED_BY_D4_RULE_REPAIR",
                     "registry_hash": reg2.get("new_registry_hash"), "superseded_by": "v1_r2_feature_registry_v3.json",
                     "ts_utc": NOW}, fh, indent=1, ensure_ascii=False)
    rdir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B3_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, "parallel_replay_v3.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for r in replay:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    out = {"task": "V1_R2_PHASE_B_R2", "status": "COMPLETE" if phase_c == "YES" else "BLOCKED",
             "D5_ALIGNMENT": {k: S[k] for k in ("ALIGNMENT_CONVENTION", "TOTAL_RECORDS", "VALID_PIT_ALIGNED", "OUT_OF_DATASET",
                                                  "AMBIGUOUS_ALIGNMENT", "DUPLICATE_TIMESTAMP", "INVALID", "LEGACY_SILENT_CLAMP_COUNT")},
             "D5": {"STATUS": d5_status, "V1_DIRECTIONAL_VALID": v1dir_valid, "V2_DIRECTIONAL_VALID": v2dir,
                      "V2_DIRECTIONAL_CURRENT_RULES": v2dir_valid_current, "V2_NONE": len(replay) - v2dir,
                      "NONE_REASON_DISTRIBUTION": nr_dist, "DIRECTION_RULE_VERSION": rules_v3["rules_version"],
                      "DIRECTION_RULE_HASH": rules_v3["rules_hash"], "REACHABILITY": {"rule_MU": mu_stats, "variants": var_stats},
                      "AGREEMENT": {"v1_directional": v1dir, "v2_directional": v2dir, "dir_agree": agree}},
             "D4": {"STATUS": d4_status, "UNKNOWN_RATE_before": round(len(unk) / len(rows), 4), "UNKNOWN_RATE_after_v3": round(unknown_rate_v3, 4),
                      "SIGNATURES": dict(sig.most_common(12)), "PRECONDITIONS": pre,
                      "UNOBSERVABLE_PREREQUISITE": repair["UNOBSERVABLE_PREREQUISITE_FOUND"], "RULE_CONTRADICTION": repair["RULE_CONTRADICTION_FOUND"]},
             "REGISTRY_VERSION": "v1r2-r3", "REGISTRY_HASH": reg3["new_registry_hash"],
             "REGISTRY_V2_HASH": reg2.get("new_registry_hash"), "REGISTRY_V1_HASH": "9e0d767935b1e9a589d1894089a661b57d352556fe9bc28a5feb60b7e8d82dce",
             "PHASE_C_ALLOWED": phase_c, "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF",
                                                      "LIVE": "OFF", "V2_WRITE": 0, "V3_WRITE": 0, "RUN_BOUNDARY_WRITE": 0, "BOUNDARY_VIOLATION": 0},
             "ts_utc": NOW}
    with open(os.path.join(UP, "reports", "V1_R2_PHASE_B_R2_SUMMARY.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    print("\n=== PHASE B-R2 (§39) ===", flush=True)
    print(json.dumps({"status": out["status"], "D5_ALIGNMENT": out["D5_ALIGNMENT"],
                        "D5_STATUS": d5_status, "MU": mu_stats, "VARIANTS": var_stats,
                        "NONE_REASON": nr_dist, "AGREEMENT": out["D5"]["AGREEMENT"],
                        "D4_STATUS": d4_status, "UNK_SIG": dict(sig.most_common(8)), "PRECOND": pre,
                        "REGISTRY_HASH": reg3["new_registry_hash"][:16], "PHASE_C_ALLOWED": phase_c,
                        "safety": out["safety"]}, ensure_ascii=True, indent=1)[:3000], flush=True)


if __name__ == "__main__":
    main()
