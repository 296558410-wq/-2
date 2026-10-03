# -*- coding: utf-8 -*-
"""V1-R4 HERMES-B INDEPENDENT AUDIT ENGINE — SCAFFOLD + REGISTRY + R3 IMMUTABILITY BASELINE.

Creates research/hermes/trader_v1/v1_r4_hermes_audit/, freezes the audit protocol, records sha256
baselines for EVERY R3 artifact (must stay IMMUTABLE), stages the audit contexts and the three
Hermes-B prompt templates, and creates the append-only sha256-chained audit ledger.
Read-only on R3. Writes ONLY under v1_r4_hermes_audit/.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
R3 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r4_hermes_audit")
LEDGER = os.path.join(ROOT, "ledger", "v1_r4_audit_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["context", "blind_audits", "adversarial_audits", "post_outcome", "ledger", "reports", "registry", "tests", "prompt"]

BLIND_PROMPT = """You are HERMES-B, an INDEPENDENT market-structure analyst for XAUUSD.

You are given ONLY a point-in-time (PIT) market context. You have NOT been shown any other analyst's
forecast, and you must not ask for one. You have no access to the future.

Produce your OWN independent judgement strictly from the context:
CURRENT_STATE, STRUCTURE, MECHANISM, PRIMARY_SCENARIO, ALTERNATIVE_SCENARIO, EXPECTED_TRANSITION,
DIRECTION, HORIZON, CONFIDENCE, COUNTER_EVIDENCE, INVALIDATION.

RULES
- Respect every data_quality tag (DIRECT/DERIVED/PROXY/UNKNOWN). UST10Y is a PROXY (^TNX), never DIRECT.
- DIRECTION may be UP | DOWN | NEUTRAL | UNDEFINED | NO_DIRECTIONAL_EDGE. You are not forced to be directional.
- HORIZON may be IMMEDIATE | SHORT_TERM | INTRADAY | HIGHER_TIMEFRAME | TIMING_UNCERTAIN.
- CONFIDENCE is your subjective confidence in [0,1], NOT a statistical probability.
- Never invent data. If the context is insufficient or self-contradictory, say so and lower confidence.

OUTPUT: exactly one JSON object with keys:
audit_id, timestamp, current_state, structure, mechanism, primary_scenario{scenario,confidence,horizon,trigger,invalidation},
alternative_scenario{scenario,confidence,horizon,trigger,invalidation}, expected_transition, direction, horizon,
confidence, counter_evidence[], invalidation, data_quality_flags[], reasoning_trace[]"""

ADVERSARIAL_PROMPT = """You are HERMES-B, an INDEPENDENT AUDITOR. Your job is to find what is WRONG with another
analyst's forecast (Hermes-A). Do NOT be agreeable. Do NOT defend it. Try to falsify it.

You are given: the same PIT context Hermes-A saw, and Hermes-A's forecast. You do NOT see the future.

Audit each dimension and assign one verdict per dimension:
AGREE | PARTIAL_AGREE | DISAGREE | INSUFFICIENT_EVIDENCE
Dimensions: CURRENT_STATE, STRUCTURE, MECHANISM, PRIMARY_SCENARIO, ALTERNATIVE_SCENARIO,
EXPECTED_TRANSITION, DIRECTION, HORIZON, CONFIDENCE, INVALIDATION, ABSTENTION.

Actively look for:
- factual errors (claims not supported by the context)
- insufficient evidence / over-inference
- MISSED counter-evidence
- mechanism jumps (leaping from observation to mechanism)
- time-window problems (claims that need longer history than available)
- data-quality problems (using PROXY as DIRECT, using UNKNOWN as if known)
- hindsight / post-hoc rationalisation
- explanation dressed up as prediction (describing the present instead of forecasting)
- over-reliance on K-line alone, or ignoring MTF conflict

RULES
- Every verdict MUST carry concrete evidence quoted/paraphrased from the context or forecast.
- Never invent facts. If you cannot decide, use INSUFFICIENT_EVIDENCE.

OUTPUT: exactly one JSON object:
audit_id, timestamp, overall_verdict (AGREE|PARTIAL_AGREE|DISAGREE|INSUFFICIENT_EVIDENCE),
dimension_verdicts {CURRENT_STATE, STRUCTURE, MECHANISM, PRIMARY_SCENARIO, ALTERNATIVE_SCENARIO,
EXPECTED_TRANSITION, DIRECTION, HORIZON, CONFIDENCE, INVALIDATION, ABSTENTION},
factual_errors[], insufficient_evidence[], missed_counter_evidence[], mechanism_jumps[],
over_inference[], time_window_issues[], data_quality_issues[], hindsight_flags[],
explanation_not_prediction_flags[], kline_overreliance_flags[], mtf_conflict_ignored_flags[],
evidence[] (each item must state the claim and the contradicting/absent evidence),
strongest_objection, reasoning_trace[]"""

POST_PROMPT = """You are HERMES-B, an INDEPENDENT post-outcome auditor.

You are given, in this order: the PIT context Hermes-A saw, Hermes-A's forecast, and the ACTUAL OUTCOME
that occurred after the context timestamp. The outcome is available to you ONLY here, for audit; it must
never be written back into the context or the forecast.

Assess, honestly and without defending Hermes-A:
- which of Hermes-A's calls were CORRECT
- which were WRONG
- where it was correct but for the WRONG REASON
- where DIRECTION was right but STATE was wrong (or vice versa)
- where Hermes-A SHOULD HAVE ABSTAINED
- whether the invalidation condition it gave actually occurred
- whether an earlier adversarial auditor's concerns materialised
- any hindsight in Hermes-A's reasoning (claims that only make sense knowing the present)

OUTPUT: exactly one JSON object:
audit_id, timestamp, correct_calls[], wrong_calls[], right_but_wrong_reason[],
direction_ok_state_wrong, state_ok_direction_wrong, should_have_abstained (bool),
invalidation_occurred (bool), prior_concerns_materialised (bool|null),
hindsight_detected (bool), hindsight_evidence[], outcome_alignment_verdict
(CORRECT|PARTIALLY_CORRECT|INCORRECT|UNSCORABLE), reasoning_trace[]"""


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def wtext(rel, s):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    return p


def ledger_append(entries):
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["current_hash"]; seq += 1
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    # ---- R3 immutability baseline ----
    r3_files = {}
    for sub in ["registry", "prompt", "forecasts", "evaluation", "tests", "baselines", "ablation", "reports", "ledger", "context"]:
        p = os.path.join(R3, sub)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            fp = os.path.join(p, f)
            if os.path.isfile(fp):
                r3_files[f"{sub}/{f}"] = sha_file(fp)
    r3_hashes = {"file_count": len(r3_files), "files": r3_files,
                  "registry_hash": json.load(open(os.path.join(R3, "registry", "v1_r3_hermes_forecast_registry.json"), encoding="utf-8"))["registry_hash"],
                  "prompt_hash": json.load(open(os.path.join(R3, "registry", "v1_r3_hermes_forecast_registry.json"), encoding="utf-8"))["prompt_hash"]}
    r3_hashes["baseline_hash"] = sha_obj(r3_files)
    wjson("registry/R3_IMMUTABILITY_BASELINE.json", r3_hashes)

    # ---- R4 audit registry (frozen before any audit) ----
    ev = json.load(open(os.path.join(R3, "evaluation", "BLIND_EVALUATION.json"), encoding="utf-8"))
    matched = sorted(set(t for t in [p["ts"] for p in ev["points"]]))
    reg = {
        "task": "V1_R4_HERMES_B_INDEPENDENT_AUDIT_ENGINE", "registry_id": "v1r4-audit-registry-r1",
        "frozen": True, "frozen_before_any_audit": True, "frozen_at_utc": NOW,
        "r3_immutable": True, "r3_baseline_hash": r3_hashes["baseline_hash"],
        "stages": ["BLIND_AUDIT", "ADVERSARIAL_AUDIT", "POST_OUTCOME_AUDIT"],
        "blind_rule": "Blind Audit receives ONLY the PIT context — no Hermes-A forecast, no outcome",
        "adversarial_rule": "Adversarial Audit receives PIT context + Hermes-A forecast — still NO outcome",
        "post_outcome_rule": "Post-Outcome Audit receives PIT context + Hermes-A forecast + ACTUAL outcome; outcome must never be written back into R3",
        "verdicts": ["AGREE", "PARTIAL_AGREE", "DISAGREE", "INSUFFICIENT_EVIDENCE"],
        "dimensions": ["CURRENT_STATE", "STRUCTURE", "MECHANISM", "PRIMARY_SCENARIO", "ALTERNATIVE_SCENARIO",
                        "EXPECTED_TRANSITION", "DIRECTION", "HORIZON", "CONFIDENCE", "INVALIDATION", "ABSTENTION"],
        "sample": {"source": "R3 frozen paired blind points", "points": matched, "n": len(matched),
                    "selection_rule": "inherited from R3 (deterministic 3-day sample); NOT re-selected for this audit",
                    "seed": "n/a (inherited)", "effective_n": len(matched), "no_reselection": True},
        "metrics_mandatory": ["agreement_rate", "partial_agreement_rate", "disagreement_rate", "insufficient_rate",
                               "state_audit", "transition_audit", "scenario_audit", "direction_audit", "timing_audit",
                               "counter_evidence_detection", "invalidation_quality", "confidence_calibration", "abstention_quality"],
        "forbidden_outputs": ["profit_score", "win_probability", "expected_profit", "future_return", "pnl"],
        "focus_checks": ["explanation_vs_prediction", "kline_overreliance", "mtf_conflict_ignored", "crossmarket_misuse",
                          "proxy_as_direct", "hindsight"],
        "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                         "V2_WRITE": 0, "V3_WRITE": 0, "BOUNDARY_VIOLATION": 0},
        "prompt_hashes": {"blind": hashlib.sha256(BLIND_PROMPT.encode()).hexdigest(),
                           "adversarial": hashlib.sha256(ADVERSARIAL_PROMPT.encode()).hexdigest(),
                           "post_outcome": hashlib.sha256(POST_PROMPT.encode()).hexdigest()},
    }
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r4_audit_registry.json", reg)
    wtext("prompt/hermes_b_blind_prompt.txt", BLIND_PROMPT)
    wtext("prompt/hermes_b_adversarial_prompt.txt", ADVERSARIAL_PROMPT)
    wtext("prompt/hermes_b_post_outcome_prompt.txt", POST_PROMPT)

    # ---- stage audit contexts (copies of the FROZEN R3 contexts; read-only source) ----
    ctx_map = {}
    for t in matched:
        src = os.path.join(R3, "context", "samples", f"CTX_{t}T120000Z.json")
        dst = os.path.join(ROOT, "context", f"CTX_{t}T120000Z.json")
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            ctx_map[t] = {"context_copy": f"context/CTX_{t}T120000Z.json", "source_sha256": sha_file(src), "copy_sha256": sha_file(dst)}
    wjson("registry/AUDIT_CONTEXT_MAP.json", {"n": len(ctx_map), "points": ctx_map,
                                                "note": "byte-identical copies of the frozen R3 contexts; the audit never alters them"})

    ledger_append([{"event": "registry_frozen", "registry_hash": reg["registry_hash"], "r3_baseline_hash": r3_hashes["baseline_hash"]},
                    {"event": "contexts_staged", "n": len(ctx_map)},
                    {"event": "prompts_frozen", "prompt_hashes": reg["prompt_hashes"]}])
    print("ROOT:", ROOT)
    print("registry_hash:", reg["registry_hash"][:16], "| R3 baseline:", r3_hashes["baseline_hash"][:16], "| R3 files:", r3_hashes["file_count"])
    print("audit points:", len(matched), matched[:6], "...")


if __name__ == "__main__":
    main()
