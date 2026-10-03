# -*- coding: utf-8 -*-
"""V3 Opportunity Quality Filter R1 — the Quality Gate.

DESIGN LAWS (frozen before any assessment is computed):
  * Quality != Alpha. This module contains NO profit / win / expectancy / return field anywhere.
  * The gate answers only: "is this worth spending Hermes resources on?"
  * Six dimensions produce an EVIDENCE MATRIX of ordinal labels. There is NO weighted total score.
  * Every dimension is computed from data at or before the detection timestamp (asof-safe).
  * Forward-looking quantities are stored ONLY as clearly-named *_observation fields and never
    enter the decision (so truncating future data cannot change a past decision).
  * The decision is a fixed, published rule list, not a learned model.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

QF_VERSION = "QF-R1.0.0"
SCHEMA_QF = "v3_quality_assessment/1"

# ------------------------------------------------------------------ frozen registry

REGISTRY = {
    "version": QF_VERSION,
    "frozen_at_utc": "2026-09-25",
    "novelty_definition": {
        "question": "is the current state rare relative to recent history?",
        "window": 240, "min_periods": 60, "window_unit": "bars",
        "rule": "rarity = mean over the trailing window of (|primary_feature| >= |primary_feature at t0|); NOVELTY = 1 - rarity",
        "labels": {"HIGH": "rarity <= 0.02", "MEDIUM": "rarity <= 0.10", "LOW": "rarity > 0.10"},
        "primary_feature_by_type": {"OPP_STATE_BREAK": "return_60m", "OPP_STATE_TRANSITION": "vol_pct_240",
                                     "OPP_CROSSMARKET_SHOCK": "external_z", "OPP_CROSSMARKET_DIVERGENCE": "external_z",
                                     "OPP_VOL_TRANSITION": "vol_ratio_5_30"},
        "no_future_data": True},
    "extremeness_definition": {
        "question": "how far from normal is the state?",
        "rule": "REUSES the R1 frozen thresholds verbatim; no retuning",
        "labels": {"HIGH": "abs(z)>=3 or vol_pct>=0.95 or abs(external_z)>=3",
                    "MEDIUM": "abs(z)>=2 or vol_pct>=0.90 or abs(external_z)>=2", "LOW": "otherwise"}},
    "persistence_definition": {
        "question": "is this a state event or a single-bar spike?",
        "rule": "BACKWARD ONLY: count consecutive preceding bars (including t0) whose vol_state equals the vol_state at t0",
        "labels": {"HIGH": ">=3 bars", "MEDIUM": "2 bars", "LOW": "1 bar"},
        "forward_persistence": "stored as post_event_persistence_observation ONLY (never used in the decision)",
        "no_future_data": True},
    "crossmarket_definition": {
        "question": "do independent markets confirm the state?",
        "rule": "count of {DXY, VIX, UST10Y_PROXY} with abs(z) >= 2 in the same bar or the preceding 2 bars",
        "labels": {"HIGH": ">=2 confirm", "MEDIUM": "1 confirm", "NONE": "0 confirm"},
        "note": "NONE is not a rejection; a single-market opportunity may still be worth research"},
    "recurrence_definition": {
        "rule": "number of strictly PRIOR opportunities of the same opportunity_type (asof, no future info)",
        "labels": {"HIGH": ">=20 prior", "MEDIUM": "5..19 prior", "LOW": "1..4 prior"},
        "forbidden_inputs": ["future return", "pnl", "win rate", "sharpe"]},
    "data_quality_definition": {
        "inherit": "from the R1 opportunity record",
        "semantic_dependency": "cross-market opportunities carry SEMANTIC_DEPENDENCY=UNKNOWN "
                                "(XAUUSD bar semantics UNKNOWN; Yahoo bar semantics UNKNOWN; UST10Y is a PROXY)",
        "never_upgrade_to_verified": True},
    "decision_matrix_ordered": [
        {"id": "R1", "if": "data_quality == UNKNOWN", "then": "QUALITY_INSUFFICIENT",
         "why": "cannot judge, rather than not worth it"},
        {"id": "R2", "if": "recurrence == LOW", "then": "QUALITY_INSUFFICIENT",
         "why": "too rare to investigate yet"},
        {"id": "R3", "if": "extremeness == LOW and novelty == LOW", "then": "QUALITY_REJECT",
         "why": "ordinary repeated state"},
        {"id": "R4", "if": "persistence == LOW and extremeness == LOW", "then": "QUALITY_REJECT",
         "why": "single-bar noise without extremeness"},
        {"id": "R5", "if": "recurrence == HIGH and novelty == LOW", "then": "QUALITY_REJECT",
         "why": "very common state"},
        {"id": "R6", "if": "extremeness>=MEDIUM and novelty>=MEDIUM and persistence>=MEDIUM and recurrence>=MEDIUM",
         "then": "QUALITY_PASS", "why": "worth spending Hermes resources"},
        {"id": "R7", "if": "otherwise", "then": "QUALITY_INSUFFICIENT", "why": "unresolved combination"}],
    "no_black_box_total_score": True,
    "forbidden_fields": ["profit_score", "win_probability", "expected_profit", "expected_return", "sharpe",
                          "profit_factor", "pnl", "future_return", "win_rate", "forward_return",
                          "signal", "order", "position"],
    "lifecycle_allowed_states": ["OBSERVED", "QUALITY_PASS", "QUALITY_REJECT", "QUALITY_INSUFFICIENT",
                                   "INVESTIGATE", "REJECT", "INSUFFICIENT_EVIDENCE", "CANDIDATE_RESEARCH"],
}


def registry_hash() -> str:
    return hashlib.sha256(json.dumps(REGISTRY, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ------------------------------------------------------------------ dimensions

def _lab(v, hi, med, higher_is_better=True):
    """Ordinal labeller kept for reference; the gate uses explicit branches so the rule stays readable."""
    if higher_is_better:
        return "HIGH" if v >= hi else ("MEDIUM" if v >= med else "LOW")
    return "LOW" if v >= hi else ("MEDIUM" if v >= med else "HIGH")


def primary_feature_value(rec: dict) -> tuple[str, float]:
    fv = rec.get("feature_values", {})
    t = rec["opportunity_type"]
    if t == "OPP_STATE_BREAK":
        return "return_60m", abs(float(fv.get("return_60m") or 0.0))
    if t == "OPP_STATE_TRANSITION":
        return "vol_pct_240", float(fv.get("vol_pct_240") or 0.0)
    if t == "OPP_VOL_TRANSITION":
        return "vol_ratio_5_30", abs(float(fv.get("vol_ratio_5_30") or 1.0))
    best, name = 0.0, "external_z"
    for nm in ("DXY", "VIX", "UST10Y_PROXY"):
        z = abs(float(fv.get(f"{nm}_RETURN_60M_z") or 0.0))
        if z > best:
            best = z
    return name, best


def assess(rec: dict, state: pd.DataFrame) -> dict:
    """Six-dimension evidence matrix. asof-safe: uses only bars <= detected_at."""
    t = pd.Timestamp(rec["detected_at"])
    i = state.index.get_indexer([t])[0]
    if i < 0:
        return {"error": "timestamp not in state index", "quality_decision": "QUALITY_INSUFFICIENT"}
    row = state.iloc[i]
    fv = rec.get("feature_values", {})

    # --- novelty (trailing window rarity) ---
    feat, v0 = primary_feature_value(rec)
    label = {"return_60m": "return_60m", "vol_pct_240": "vol_pct_240", "vol_ratio_5_30": "vol_ratio_5_30"}.get(feat)
    if label and label in state.columns:
        w = state[label].iloc[max(0, i - REGISTRY["novelty_definition"]["window"] + 1):i + 1].dropna()
        rarity = float(np.mean(np.abs(w.to_numpy(float)) >= abs(v0))) if len(w) >= 20 else None
    else:
        w = None
        zs = [abs(float(fv.get(f"{nm}_RETURN_60M_z") or 0.0)) for nm in ("DXY", "VIX", "UST10Y_PROXY")
               if f"{nm}_RETURN_60M_z" in state.columns]
        if zs:
            col = f"{['DXY','VIX','UST10Y_PROXY'][int(np.argmax(zs))]}_RETURN_60M_z"
            w = state[col].iloc[max(0, i - 239):i + 1].dropna()
            rarity = float(np.mean(np.abs(w.to_numpy(float)) >= abs(float(fv.get(col) or 0.0)))) if len(w) >= 20 else None
        else:
            rarity = None
    if rarity is None:
        novelty = "LOW"
    elif rarity <= 0.02:
        novelty = "HIGH"
    elif rarity <= 0.10:
        novelty = "MEDIUM"
    else:
        novelty = "LOW"

    # --- extremeness (R1 thresholds reused verbatim) ---
    z60 = abs(float(fv.get("return_60m") or 0.0))
    vp = float(fv.get("vol_pct_240") or 0.0)
    ez = max([abs(float(fv.get(f"{nm}_RETURN_60M_z") or 0.0)) for nm in ("DXY", "VIX", "UST10Y_PROXY")] or [0.0])
    ext = "HIGH" if (z60 >= 300 or vp >= 0.95 or ez >= 3.0) else ("MEDIUM" if (z60 >= 200 or vp >= 0.90 or ez >= 2.0) else "LOW")

    # --- persistence (BACKWARD only) ---
    vs = str(row.get("vol_state"))
    n = 1
    j = i - 1
    while j >= 0 and str(state["vol_state"].iloc[j]) == vs:
        n += 1
        j -= 1
    pers = "HIGH" if n >= 3 else ("MEDIUM" if n == 2 else "LOW")
    # forward observation only (never used in the decision)
    fwd = 0
    k = i + 1
    while k < len(state) and str(state["vol_state"].iloc[k]) == vs:
        fwd += 1
        k += 1

    # --- cross-market confirmation (asof) ---
    conf = 0
    for nm in ("DXY", "VIX", "UST10Y_PROXY"):
        col = f"{nm}_RETURN_60M_z"
        if col in state.columns:
            seg = state[col].iloc[max(0, i - 2):i + 1].abs().dropna()
            if len(seg) and float(seg.max()) >= 2.0:
                conf += 1
    cm = "HIGH" if conf >= 2 else ("MEDIUM" if conf == 1 else "NONE")

    # --- recurrence (strictly prior, same type) ---
    prior = rec.get("_prior_same_type", 0)
    rec_label = "HIGH" if prior >= 20 else ("MEDIUM" if prior >= 5 else "LOW")

    dq = rec.get("data_quality", "UNKNOWN")
    sem = "UNKNOWN" if rec["opportunity_type"].startswith("OPP_CROSSMARKET") else "PARTIAL"

    matrix = {"NOVELTY": novelty, "EXTREMENESS": ext, "PERSISTENCE": pers,
               "CROSSMARKET_CONFIRMATION": cm, "HISTORICAL_RECURRENCE": rec_label, "DATA_QUALITY": dq}
    dec, rule, why = "QUALITY_INSUFFICIENT", "R7", "unresolved combination"
    ordv = {"LOW": 0, "NONE": 0, "MEDIUM": 1, "HIGH": 2}
    for r in REGISTRY["decision_matrix_ordered"]:
        i_ = r["if"]
        hit = False
        if i_ == "data_quality == UNKNOWN":
            hit = (dq == "UNKNOWN")
        elif i_ == "recurrence == LOW":
            hit = (rec_label == "LOW")
        elif i_ == "extremeness == LOW and novelty == LOW":
            hit = (ext == "LOW" and novelty == "LOW")
        elif i_ == "persistence == LOW and extremeness == LOW":
            hit = (pers == "LOW" and ext == "LOW")
        elif i_ == "recurrence == HIGH and novelty == LOW":
            hit = (rec_label == "HIGH" and novelty == "LOW")
        elif i_.startswith("extremeness>=MEDIUM"):
            hit = (ordv[ext] >= 1 and ordv[novelty] >= 1 and ordv[pers] >= 1 and ordv[rec_label] >= 1)
        elif i_ == "otherwise":
            hit = True
        if hit:
            dec, rule, why = r["then"], r["id"], r["why"]
            break

    return {"quality_matrix": matrix, "quality_decision": dec, "decision_rule": rule, "decision_reason": why,
             "detail": {"rarity": (round(rarity, 5) if rarity is not None else None), "primary_feature": feat,
                         "backward_persistence_bars": n, "crossmarket_confirms": conf, "prior_same_type": prior},
             "post_event_persistence_observation": {"forward_bars": fwd,
                                                      "note": "OBSERVATION ONLY - excluded from the decision"},
             "semantic_dependencies": {"SEMANTIC_DEPENDENCY": sem,
                                        "depends_on": (["XAUUSD bar open/close semantics (UNKNOWN)",
                                                         "Yahoo bar semantics (UNKNOWN)",
                                                         "UST10Y_PROXY is ^TNX, not the official UST10Y"]
                                                        if sem == "UNKNOWN" else ["XAUUSD bar open/close semantics (UNKNOWN)"])},
             "data_quality": dq, "quality_filter_version": QF_VERSION}


# ------------------------------------------------------------------ hermes (three-way, PASS only)

def hermes(rec: dict, qa: dict) -> dict:
    m = qa["quality_matrix"]
    conf = qa["detail"]["crossmarket_confirms"]
    sem = qa["semantic_dependencies"]["SEMANTIC_DEPENDENCY"]
    proxy_only = (conf == 1 and rec["opportunity_type"].startswith("OPP_CROSSMARKET"))
    artifacts = ["timestamp artifact (bar open/close semantics UNKNOWN on both XAUUSD and the Yahoo sources)",
                  "bar construction artifact (XAUUSD 1h/5m derived by resampling HistData 1m)",
                  "data source artifact (XAUUSD from HistData vs externals from Yahoo - two vendors)",
                  "proxy artifact (UST10Y is ^TNX, a yield index proxy, not the official series)",
                  "duplicate state (cluster continuations already collapsed; check residual co-occurrence)",
                  "selection artifact (only states flagged abnormal by the frozen detectors are reviewed)"]
    if m["EXTREMENESS"] == "LOW":
        dec, why = "REJECT", "extremeness is LOW - the state is not distinguishable from normal conditions"
    elif proxy_only:
        dec, why = "REJECT", "the only cross-market confirmation comes from the ^TNX PROXY - measurement-artifact priority"
    elif m["HISTORICAL_RECURRENCE"] == "MEDIUM" and sem == "UNKNOWN":
        dec, why = "INSUFFICIENT_EVIDENCE", "recurrence is only MEDIUM and the cross-market semantics are UNKNOWN"
    elif sem == "UNKNOWN":
        dec, why = "INVESTIGATE", "recurrent, extreme and persistent; worth research despite UNKNOWN semantics (flagged)"
    else:
        dec, why = "INVESTIGATE", "recurrent, extreme and persistent with single-source semantics"
    return {"A_what_happened": (f"{rec['opportunity_type']} at {rec['detected_at']} ({rec.get('trigger')}); "
                                  f"vol_state={rec['market_state'].get('vol_state')}, "
                                  f"session={rec['market_state'].get('session_bucket')}"),
             "B_mechanisms": ["volatility-regime mechanics (clustering / mean reversion of volatility)",
                                "cross-asset information flow (DXY / VIX / UST10Y_PROXY leading or lagging XAUUSD)",
                                "liquidity and session structure (Asia vs London vs New York)",
                                "measurement artifact (see the prioritized artifact list)"],
             "C_counter_evidence": artifacts + [f"quality matrix is {json.dumps(m, ensure_ascii=False)}",
                                                  "sample length limits: 1h=624d, 5m=63d"],
             "D_reproducible": {"same_type_prior_count": qa["detail"]["prior_same_type"],
                                  "state_recurrence": m["HISTORICAL_RECURRENCE"],
                                  "event_recurrence_note": "recurrence is defined from state/type, never from returns",
                                  "note": "recurrence only - profitability is out of scope for this stage"},
             "E_decision": dec, "E_reason": why,
             "measurement_artifact_priority": {"proxy_artifact_applies": proxy_only,
                                                 "checks": artifacts}}


# ------------------------------------------------------------------ ledger

class QualityLedger:
    def __init__(self, path: str, registry_hash_value: str):
        self.path = path
        self._prev = "GENESIS"
        self.registry_hash_value = registry_hash_value
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    self._prev = json.loads(line)["chain_hash"]

    def append(self, rec: dict) -> str:
        body = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256((self._prev + body).encode()).hexdigest()
        row = {"seq": (sum(1 for l in open(self.path, encoding="utf-8") if l.strip()) if os.path.exists(self.path) else 0),
                "prev_hash": self._prev, "chain_hash": h, "registry_hash": self.registry_hash_value, "payload": rec}
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        self._prev = h
        return h

    @staticmethod
    def verify(path: str) -> dict:
        if not os.path.exists(path):
            return {"rows": 0, "chain_ok": True, "bad_seq": None}
        prev, n, ok, bad = "GENESIS", 0, True, None
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            body = json.dumps(row["payload"], sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256((prev + body).encode()).hexdigest()
            if h != row["chain_hash"] or row["prev_hash"] != prev:
                ok, bad = False, row["seq"]
                break
            prev, n = h, n + 1
        return {"rows": n, "chain_ok": ok, "bad_seq": bad}
