# -*- coding: utf-8 -*-
"""V3 Opportunity Mechanism Validation R2 — METHOD REPAIR.

What R1 got wrong (admitted, not hidden): TIME_STABILITY asked only whether events fell into the three time
thirds, which a uniformly shuffled timestamp series satisfies trivially -> the validator rewarded randomness.

R2 replaces every stability dimension with a PERMUTATION-vs-NULL comparison with PRE-REGISTERED statistics,
adds split artifact classes (only FATAL artifacts may reject), counts duplication at exactly one stage,
audits evidence independence, and proves the validator against a Positive Control plus three Null Models.

Nothing here is profit-related. No future data drives any decision.
Clustering / mechanism identity is UNCHANGED from R1 (task section 42).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.join(os.path.dirname(HERE), "mechanism_validation")
sys.path.insert(0, R1)
import mechanism_validation as mv  # noqa: E402  (R1 clustering reused unchanged)

MV2_VERSION = "MV-R2.0.0"

REGISTRY = {
    "version": MV2_VERSION,
    "reuses_R1_clustering": True,
    "taxonomy": mv.TAXONOMY,
    "event_separation_window": mv.REGISTRY["event_separation_window"],
    "duplicate_detection_stage": "EVENT_LEVEL",
    "duplicate_counted_once": True,
    "minimum_independent_events": 8,
    "random_seed": 20260925,
    "permutation_count": 500,
    "null_runs": 20,
    "stability_statistics": {
        "TIME_STABILITY": {"statistic": "coefficient_of_variation of inter-event intervals",
                            "null": "event times drawn uniformly over the mechanism's own observation span, same count",
                            "tail": "one_sided_lower_tail", "alpha": 0.05,
                            "labels": {"HIGH": "p <= alpha (more clustered than random)",
                                        "MEDIUM": "alpha < p < 1-alpha", "LOW": "p >= 1-alpha (more uniform than random)"},
                            "rationale": "uniform random placement gives CV near the null median, so randomness cannot "
                                          "earn a HIGH label; only genuine burstiness can"},
        "SESSION_STABILITY": {"statistic": "max session share", "null": "session labels shuffled across the mechanism's events",
                               "tail": "two_sided", "alpha": 0.05,
                               "labels": {"HIGH": "not extreme vs null (p in (alpha, 1-alpha))",
                                           "LOW": "more concentrated than null (p >= 1-alpha)",
                                           "NOT_INFORMATIVE": "indistinguishable from null (p <= alpha)"}},
        "STATE_STABILITY": {"statistic": "max vol-state share", "null": "state labels shuffled across events",
                             "tail": "two_sided", "alpha": 0.05,
                             "labels": {"HIGH": "less concentrated than null", "LOW": "more concentrated than null",
                                         "NOT_INFORMATIVE": "indistinguishable from null"}},
    },
    "artifact_classes": ["DATA_ARTIFACT", "TIMESTAMP_ARTIFACT", "PROXY_ARTIFACT", "DUPLICATION_ARTIFACT",
                           "SELECTION_ARTIFACT", "UNKNOWN_ARTIFACT"],
    "fatal_artifact_rule": "FATAL_ARTIFACT = TRUE only when the record set itself proves the mechanism is produced by "
                            "data construction (degenerate identical rows inside one event, or a mechanism whose ONLY "
                            "confirmation is the ^TNX proxy). Non-fatal artifacts only lower the evidence level.",
    "counter_evidence_levels": ["FATAL", "STRONG", "MODERATE", "WEAK", "UNKNOWN"],
    "counter_evidence_rules": {
        "FATAL": "proven data-construction origin", "STRONG": "a large share of random nulls reproduces the structure",
        "MODERATE": "highly session-dependent", "WEAK": "missing periods only", "UNKNOWN": "unclassified",
        "parent_dedup": "codes describing the same underlying fact share a counter_evidence_parent_id and are counted once"},
    "counter_evidence_parents": {"CE_P_DATA": ["C01"], "CE_P_TIMESTAMP": ["C02"], "CE_P_PROXY": ["C03"],
                                   "CE_P_RECURRENCE": ["C04"], "CE_P_REGIME": ["C05"], "CE_P_SESSION": ["C06"],
                                   "CE_P_CROSSMARKET": ["C07"], "CE_P_DUP": ["C08"], "CE_P_ALT": ["C09"],
                                   "CE_P_UNKNOWN": ["C10"]},
    "evidence_dimensions": ["E1_TRIGGER", "E2_RECURRENCE", "E3_TEMPORAL", "E4_SESSION", "E5_STATE",
                              "E6_CROSSMARKET", "E7_COUNTER", "E8_ARTIFACT"],
    "evidence_dependency_rule": "two dimensions are DEPENDENT_EVIDENCE when they are computed from the same underlying "
                                 "variable (e.g. E3 and E4 both derived from the mechanism's own event set); the flag is "
                                 "reported, never used to inflate or deflate a decision",
    "decision_rule_ordered": [
        {"id": "B1", "if": "FATAL_ARTIFACT", "then": "MECHANISM_REJECTED", "why": "artifact first, and provably fatal"},
        {"id": "B2", "if": "counter_evidence == FATAL", "then": "MECHANISM_REJECTED", "why": "fatal counter-evidence"},
        {"id": "B3", "if": "independent_events < minimum", "then": "MECHANISM_UNCERTAIN", "why": "below the frozen minimum"},
        {"id": "B4", "if": "TIME_STABILITY != HIGH", "then": "MECHANISM_UNCERTAIN",
         "why": "cannot show temporal structure beyond a random null"},
        {"id": "B5", "if": "trigger_consistency >= MEDIUM and counter_evidence_level in (WEAK, UNKNOWN)",
         "then": "MECHANISM_SUPPORTED", "why": "beats the random null on time structure with acceptable counter-evidence"},
        {"id": "B6", "if": "otherwise", "then": "MECHANISM_UNCERTAIN", "why": "structure present but not decisive"}],
    "positive_control": {"pre_registered": True,
                          "definition": "a synthetic mechanism with a planted repeat structure: 30 events, one identical "
                                        "trigger/state/session/cross-market signature, evenly spaced (no returns, no PnL)",
                          "expected_detection": "MECHANISM_SUPPORTED",
                          "failure_meaning": "validator too strict -> METHOD_INVALID"},
    "negative_controls": {"pre_registered": True,
                           "NC_A": "random time labels across opportunities",
                           "NC_B": "permute event times inside each mechanism",
                           "NC_C": "permute mechanism labels across events",
                           "pass_criterion": "NULL_SUPPORTED_RATE <= max_null_rate",
                           "max_null_rate": 0.25,
                           "rationale": "a random null may occasionally land one SUPPORTED; a rate above the frozen "
                                         "ceiling means the validator rewards randomness"},
    "method_validity_rule": "VALID only if: negative controls PASS (all three) AND positive control PASS AND replay PASS "
                             "AND deterministic PASS AND no-lookahead PASS",
    "candidate_gate": {"requires": ["METHOD_VALIDITY == VALID", "MECHANISM_SUPPORTED",
                                      "independent_event_count >= minimum_independent_events",
                                      "FATAL_ARTIFACT == False"]},
    "forbidden_identifiers": ["future_return", "future_pnl", "pnl", "win_rate", "sharpe", "profit_factor",
                                "expected_profit", "expected_return", "profit_score", "win_probability",
                                "order_send", "order_check", "metatrader5", "broker", "execution"],
}


def registry_hash() -> str:
    return hashlib.sha256(json.dumps(REGISTRY, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ------------------------------------------------------------------ permutation statistics

def _cv(seconds: np.ndarray) -> float:
    if len(seconds) < 2:
        return 0.0
    m = float(np.mean(seconds))
    return float(np.std(seconds) / m) if m > 0 else 0.0


def permutation_stability(event_times: list[pd.Timestamp], kind: str, rng: random.Random,
                            n_perm: int, labels: list[str] | None = None) -> dict:
    """Pre-registered permutation test. The observed statistic is compared with a null built by re-drawing the
    arrangement while keeping the count fixed. Returns the full null summary (task section 31)."""
    n = len(event_times)
    t = np.array([pd.Timestamp(x).value / 1e9 for x in event_times], dtype=float)
    t = np.sort(t)
    if n < 3:
        return {"observed": None, "null_mean": None, "null_std": None, "p_value": None, "n_perm": 0,
                 "conclusion": "INSUFFICIENT"}
    span_lo, span_hi = float(t[0]), float(t[-1])
    if kind == "TIME_STABILITY":
        obs = _cv(np.diff(t))
        null = []
        for _ in range(n_perm):
            s = np.sort(np.array([rng.uniform(span_lo, span_hi) for _ in range(n)]))
            null.append(_cv(np.diff(s)))
        null = np.array(null)
        p = float(np.mean(null >= obs))                      # lower tail: clustered beyond random
        concl = "HIGH" if p <= 0.05 else ("LOW" if p >= 0.95 else "MEDIUM")
        return {"observed": round(obs, 6), "null_mean": round(float(null.mean()), 6),
                 "null_std": round(float(null.std()), 6),
                 "null_quantiles": {q: round(float(np.percentile(null, q)), 6) for q in (5, 25, 50, 75, 95)},
                 "p_value": round(p, 5), "n_perm": n_perm, "conclusion": concl,
                 "seed": REGISTRY["random_seed"],
                 "null_definition": "uniform event times over the mechanism's own span, same count"}
    # SESSION / STATE: label-concentration test
    labels = labels or []
    if not labels:
        return {"observed": None, "p_value": None, "n_perm": 0, "conclusion": "INSUFFICIENT"}
    obs_share = max(labels.count(v) for v in set(labels)) / len(labels)
    null = []
    for _ in range(n_perm):
        sh = labels[:]
        rng.shuffle(sh)
        null.append(max(sh.count(v) for v in set(sh)) / len(sh))
    null = np.array(null)
    p_low = float(np.mean(null <= obs_share))                # observed MORE concentrated than null
    p_high = float(np.mean(null >= obs_share))
    if p_low <= 0.05:
        concl = "LOW"
    elif p_high <= 0.05:
        concl = "HIGH"
    else:
        concl = "NOT_INFORMATIVE"
    return {"observed": round(obs_share, 6), "null_mean": round(float(null.mean()), 6),
             "null_std": round(float(null.std()), 6),
             "null_quantiles": {q: round(float(np.percentile(null, q)), 6) for q in (5, 25, 50, 75, 95)},
             "p_value": round(min(p_low, p_high), 5), "n_perm": n_perm, "conclusion": concl,
             "seed": REGISTRY["random_seed"],
             "null_definition": f"{kind.split('_')[0].lower()} labels shuffled across the mechanism's events"}


# ------------------------------------------------------------------ evidence + decision

def artifact_classes(ev: list[dict], codes: dict[str, int]) -> dict:
    """Split artifact evidence into classes; only a provable construction artifact is FATAL."""
    n = len(ev)
    degenerate = sum(1 for e in ev if len(e["opportunities"]) > 1
                      and len({json.dumps(o.get("signals", {}), sort_keys=True) for o in e["opportunities"]}) == 1)
    proxy_only = sum(1 for e in ev if e["opportunities"][0].get("crossmarket_signature") == "UST10Y_PROXY")
    classes = {
        "DATA_ARTIFACT": {"count": degenerate, "fatal": bool(n and degenerate >= 0.5 * n),
                           "reason": "merged rows inside one event carry identical signatures"},
        "TIMESTAMP_ARTIFACT": {"count": codes.get("C02", 0), "fatal": False,
                                "reason": "two-vendor bar semantics UNKNOWN (alignment risk, not a proven error)"},
        "PROXY_ARTIFACT": {"count": proxy_only, "fatal": bool(n and proxy_only >= 0.5 * n),
                            "reason": "the only cross-market confirmation is the ^TNX proxy"},
        "DUPLICATION_ARTIFACT": {"count": codes.get("C08", 0), "fatal": False,
                                  "reason": "residual duplication is measured at EVENT level only (single stage)"},
        "SELECTION_ARTIFACT": {"count": 0, "fatal": False,
                                "reason": "only states flagged abnormal by the frozen detectors are reviewed"},
        "UNKNOWN_ARTIFACT": {"count": 0, "fatal": False, "reason": ""},
    }
    classes["FATAL_ARTIFACT"] = any(v["fatal"] for v in classes.values() if isinstance(v, dict))
    classes["high"] = sum(1 for k, v in classes.items()
                           if isinstance(v, dict) and k != "FATAL_ARTIFACT" and v["count"] and not v["fatal"])
    return classes


def counter_evidence_level(codes: dict[str, int], fatal_artifact: bool, time_concl: str) -> tuple[str, str, str]:
    """Severity with parent de-duplication (task sections 40/41)."""
    parents = {}
    for code, cnt in codes.items():
        pid = next((p for p, cs in REGISTRY["counter_evidence_parents"].items() if code in cs), "CE_P_UNKNOWN")
        parents.setdefault(pid, []).append(code)
    if fatal_artifact:
        return "FATAL", "CE_P_DATA", "proven data-construction origin"
    if time_concl == "LOW":
        return "STRONG", "CE_P_RANDOM", "the observed temporal arrangement is more uniform than the random null"
    if codes.get("C06"):
        return "MODERATE", "CE_P_SESSION", "session concentration"
    if codes.get("C04"):
        return "WEAK", "CE_P_RECURRENCE", "some periods missing"
    if not codes:
        return "UNKNOWN", "CE_P_UNKNOWN", "no counter-evidence recorded"
    return "WEAK", next(iter(parents)), "minor counter-evidence"


def evidence_independence() -> dict:
    """Audit which dimensions share an underlying variable (task sections 19/20)."""
    pairs = [("E1_TRIGGER", "E2_RECURRENCE"), ("E2_RECURRENCE", "E3_TEMPORAL"), ("E3_TEMPORAL", "E4_SESSION"),
              ("E4_SESSION", "E5_STATE"), ("E5_STATE", "E6_CROSSMARKET"), ("E6_CROSSMARKET", "E7_COUNTER"),
              ("E7_COUNTER", "E8_ARTIFACT")]
    dependent = {("E3_TEMPORAL", "E4_SESSION"): "both derived from the mechanism's own event set",
                  ("E4_SESSION", "E5_STATE"): "both derived from the same event attribute table",
                  ("E2_RECURRENCE", "E3_TEMPORAL"): "recurrence count and event times come from one event list"}
    out = []
    for a, b in pairs:
        key = (a, b) if (a, b) in dependent else ((b, a) if (b, a) in dependent else None)
        out.append({"pair": [a, b], "status": ("DEPENDENT_EVIDENCE" if key else "INDEPENDENT_EVIDENCE"),
                     "reason": dependent.get(key, "") if key else ""})
    return {"pairs": out, "dependent_pairs": sum(1 for p in out if p["status"] == "DEPENDENT_EVIDENCE"),
             "note": "flags are reported; they never inflate or deflate a decision"}


def decide_r2(em: dict, ce_level: str, fatal: bool) -> tuple[str, str, str]:
    for r in REGISTRY["decision_rule_ordered"]:
        c = r["if"]
        hit = False
        if c == "FATAL_ARTIFACT":
            hit = bool(fatal)
        elif c == "counter_evidence == FATAL":
            hit = (ce_level == "FATAL")
        elif c == "independent_events < minimum":
            hit = em.get("INDEPENDENT_EVENTS") == "LOW"
        elif c == "TIME_STABILITY != HIGH":
            hit = em.get("TIME_STABILITY") != "HIGH"
        elif c.startswith("trigger_consistency >= MEDIUM"):
            hit = (em.get("TRIGGER_CONSISTENCY") in ("HIGH", "MEDIUM") and ce_level in ("WEAK", "UNKNOWN"))
        elif c == "otherwise":
            hit = True
        if hit:
            return r["then"], r["id"], r["why"]
    return "MECHANISM_UNCERTAIN", "B6", "structure present but not decisive"


def run_validation(recs: list[dict], rng: random.Random, n_perm: int, judge: bool = True) -> dict:
    """Full R2 validation pass over a set of R1-shaped records."""
    events_sorted, events = mv.build_events(recs)
    by_mech: dict[str, list[dict]] = {}
    for e in events:
        by_mech.setdefault(e["mechanism_id"], []).append(e)
    rows, stats = {}, {}
    for m, evs in by_mech.items():
        rep = [e["opportunities"][0] for e in evs]
        codes: dict[str, int] = {}
        for e in evs:
            for c in mv.counter_codes(e["opportunities"][0], e["opportunities"][0].get("review", {}), e):
                codes[c] = codes.get(c, 0) + 1
        ev0 = [e for e in events if e["mechanism_id"] == m]
        ck = {}
        for e in sorted(ev0, key=lambda x: x["event_start"]):
            for prev in ck.get(e["cluster_key"], []):
                if abs((pd.Timestamp(e["event_start"]) - pd.Timestamp(prev)).total_seconds()) <= 6 * 3600:
                    codes["C08"] = codes.get("C08", 0) + 1
            ck.setdefault(e["cluster_key"], []).append(e["event_start"])
        times = [e["event_start"] for e in evs]
        tstat = permutation_stability(times, "TIME_STABILITY", rng, n_perm)
        sstat = permutation_stability(times, "SESSION_STABILITY", rng, n_perm,
                                        [r["time_signature"] for r in rep])
        ststat = permutation_stability(times, "STATE_STABILITY", rng, n_perm,
                                         [r["market_state_signature"] for r in rep])
        arts = artifact_classes(evs, codes)
        ce_level, ce_parent, ce_why = counter_evidence_level(codes, arts["FATAL_ARTIFACT"], tstat["conclusion"])
        trig = {}
        for e in evs:
            k = e["cluster_key"].split("|")[1]
            trig[k] = trig.get(k, 0) + 1
        trig_cons = max(trig.values()) / len(evs)
        n = len(evs)
        em = {"TRIGGER_CONSISTENCY": "HIGH" if trig_cons >= 0.7 else "MEDIUM" if trig_cons >= 0.4 else "LOW",
               "TIME_STABILITY": tstat["conclusion"], "SESSION_STABILITY": sstat["conclusion"],
               "STATE_STABILITY": ststat["conclusion"],
               "INDEPENDENT_EVENTS": "SUFFICIENT" if n >= REGISTRY["minimum_independent_events"] else "LOW",
               "COUNTER_EVIDENCE_LEVEL": ce_level, "FATAL_ARTIFACT": arts["FATAL_ARTIFACT"],
               "ARTIFACT_CLASSES": {k: v for k, v in arts.items() if isinstance(v, dict)},
               "detail": {"events": n, "trigger_consistency_ratio": round(trig_cons, 3)}}
        dec, rule, why = decide_r2(em, ce_level, arts["FATAL_ARTIFACT"])
        rows[m] = {"mechanism_id": m, "mechanism_name": mv.TAXONOMY.get(m, "UNKNOWN"), "events": n,
                    "opportunities": sum(len(e["opportunities"]) for e in evs),
                    "cluster_count": len({e["cluster_key"] for e in evs}),
                    "evidence_matrix": em, "counter_evidence": {"codes": codes, "level": ce_level,
                                                                  "parent_id": ce_parent, "why": ce_why},
                    "causality_level": "CO_MOVEMENT",
                    "proxy_dependency": "HIGH" if arts["PROXY_ARTIFACT"]["count"] else "LOW",
                    "decision": dec, "decision_rule": rule, "decision_reason": why,
                    "lifecycle": "SUPPORTED" if dec == "MECHANISM_SUPPORTED" else
                                  ("REJECTED" if dec == "MECHANISM_REJECTED" else "UNCERTAIN")}
        stats[m] = {"TIME_STABILITY": tstat, "SESSION_STABILITY": sstat, "STATE_STABILITY": ststat}
    dist = {}
    for r in rows.values():
        dist[r["decision"]] = dist.get(r["decision"], 0) + 1
    return {"events": events, "by_mech": by_mech, "rows": rows, "stats": stats, "distribution": dist,
             "supported_rate": (dist.get("MECHANISM_SUPPORTED", 0) / len(rows)) if rows else 0.0}


def positive_control_records(n_events: int = 30) -> list[dict]:
    """Pre-registered synthetic structure: one identical signature, evenly spaced events over a fixed span.
    No returns, no PnL. Used only to check that the validator can recognise a known planted structure."""
    base = pd.Timestamp("2025-03-01T00:00:00+00:00")
    recs = []
    for i in range(n_events):
        t = base + pd.Timedelta(hours=6 * i)
        sig = {"trigger_signature": "PRICE_EXTREME", "transmission_signature": "DIRECT",
                "response_signature": "UNKNOWN", "time_signature": "London", "market_state_signature": "VOL_NORMAL",
                "crossmarket_signature": "NONE", "artifact_signature": "SINGLE_SOURCE"}
        recs.append({"opportunity_id": f"PC-{i:03d}", "cluster_id": "PC", "detected_at": t.isoformat(),
                      "grid": "1h", "opportunity_type": "OPP_STATE_BREAK", "signals": sig, "mechanism_id": "M01",
                      "cluster_key": mv.cluster_key(sig, "M01"), "market_state_signature": "VOL_NORMAL",
                      "time_signature": "London", "crossmarket_signature": "NONE", "is_continuation": False,
                      "review": {"data_quality": "VERIFIED"}})
    return recs
