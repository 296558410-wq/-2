# -*- coding: utf-8 -*-
"""V1-R5 HERMES FORECAST DISCIPLINE — SCAFFOLD + REGISTRY + R3/R4 IMMUTABILITY BASELINE.

Freezes the R5 discipline prompt (strict observation/inference separation), pins R3 and R4 as
IMMUTABLE, pre-registers the R5 sample (EFFECTIVE_N declared), and creates the sha256-chained ledger.
Read-only on R3/R4. Writes ONLY under v1_r5_hermes_forecast_discipline/.
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
R4 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r4_hermes_audit")
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r5_hermes_forecast_discipline")
LEDGER = os.path.join(ROOT, "ledger", "v1_r5_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["registry", "context", "prompt", "forecasts", "blind_audits", "adversarial_audits", "post_outcome",
        "evaluation", "ledger", "reports", "tests", "audit"]

R5_PROMPT = """You are HERMES-A. You forecast XAUUSD market structure from a point-in-time (PIT) context.
You have NO access to the future. Your discipline matters more than your confidence.

STRICT SEPARATION IS MANDATORY. Never turn an OBSERVATION into a FACT CONCLUSION.
Every mechanism must carry a status: SUPPORTED | POSSIBLE | WEAK | UNKNOWN.

You MUST answer, explicitly, these seven questions:
Q1 what_do_i_know (only what the context actually states)
Q2 what_do_i_not_know (explicit gaps, and which data are PROXY / UNKNOWN / stale)
Q3 evidence_for_primary (observations supporting the primary scenario)
Q4 evidence_against_primary (observations against it — you must actively look)
Q5 mechanism_that_is_only_possible (name the mechanism you are NOT entitled to assert)
Q6 what_would_change_my_mind (concrete, checkable evidence that would flip your view)
Q7 should_i_abstain_now (true/false and why)

CONFIDENCE DISCIPLINE
- Report THREE separate fields: evidence_strength, confidence, uncertainty (each in [0,1]).
- A complete story does NOT by itself raise confidence.
- Give confidence_reason and uncertainty_reason in words.
- If the context is insufficient or self-contradictory you MUST set abstain=true with abstain_reason.

OUTPUT: exactly one JSON object with keys:
forecast_id, timestamp, observations[], what_i_know[], what_i_do_not_know[],
evidence[], counter_evidence[], possible_mechanisms[{mechanism,status,why}],
primary_scenario{scenario,horizon,trigger,invalidation}, alternative_scenario{scenario,horizon,trigger,invalidation},
expected_transition, direction_bias (UP|DOWN|NEUTRAL|UNDEFINED|NO_DIRECTIONAL_EDGE), time_horizon,
evidence_strength, confidence, uncertainty, confidence_reason, uncertainty_reason,
invalidation, change_my_mind[], abstain (bool), abstain_reason, questions{Q1..Q7}, reasoning_trace[]"""

IMM_AUDIT_PROMPT = """You are HERMES-B, an INDEPENDENT AUDITOR. Your job is to find what is WRONG with
Hermes-A's forecast. Do NOT help it. Do NOT defend it. Try to falsify it.

You see the PIT context and Hermes-A's forecast. You do NOT see the outcome.

Audit these R5 focus areas and assign AGREE | PARTIAL_AGREE | DISAGREE | INSUFFICIENT_EVIDENCE for each:
OBSERVATION_DISCIPLINE (did it keep observations separate from conclusions?)
MECHANISM_DISCIPLINE (were mechanism statuses honest: SUPPORTED/POSSIBLE/WEAK/UNKNOWN?)
COUNTER_EVIDENCE (did it actually seek evidence against itself?)
CONFIDENCE (are evidence_strength / confidence / uncertainty justified and distinct?)
ABSTENTION (should it have abstained?)
INVALIDATION (are the invalidation conditions checkable?)

Also list concrete instances of: over_inference, mechanism_jump, missing_counter_evidence,
unjustified_confidence, observation_as_fact. Each item must quote the context or the forecast.

OUTPUT: exactly one JSON object:
audit_id, timestamp, overall_verdict (AGREE|PARTIAL_AGREE|DISAGREE|INSUFFICIENT_EVIDENCE),
focus_verdicts{OBSERVATION_DISCIPLINE, MECHANISM_DISCIPLINE, COUNTER_EVIDENCE, CONFIDENCE, ABSTENTION, INVALIDATION},
over_inference[], mechanism_jump[], missing_counter_evidence[], unjustified_confidence[], observation_as_fact[],
strongest_objection, evidence[], reasoning_trace[]"""

POST_PROMPT = """You are HERMES-B, an INDEPENDENT post-outcome auditor.
You see the PIT context, Hermes-A's forecast, and the ACTUAL outcome (audit-only; never written back).

Judge: correct_calls[], wrong_calls[], right_but_wrong_reason[], direction_ok_state_wrong (bool),
state_ok_direction_wrong (bool), should_have_abstained (bool), invalidation_occurred (bool),
hindsight_detected (bool), hindsight_evidence[],
outcome_alignment_verdict (CORRECT|PARTIALLY_CORRECT|INCORRECT|UNSCORABLE), reasoning_trace[].
Do not defend Hermes-A. Output exactly one JSON object with those keys."""


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
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def baseline(root, name):
    files = {}
    for sub in ["registry", "prompt", "forecasts", "evaluation", "tests", "reports", "ledger", "context",
                 "blind_audits", "adversarial_audits", "post_outcome", "audit"]:
        p = os.path.join(root, sub)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            fp = os.path.join(p, f)
            if os.path.isfile(fp):
                files[f"{sub}/{f}"] = sha_file(fp)
    return {"name": name, "file_count": len(files), "baseline_hash": sha_obj(files), "files": files}


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    b3, b4 = baseline(R3, "R3"), baseline(R4, "R4")
    wjson("registry/R3_IMMUTABILITY_BASELINE.json", b3)
    wjson("registry/R4_IMMUTABILITY_BASELINE.json", b4)
    # pre-registered R5 sample: every 2nd of the frozen R3 18 paired points (fixed rule, no cherry-picking)
    r4reg = json.load(open(os.path.join(R4, "registry", "v1_r4_audit_registry.json"), encoding="utf-8"))
    allpts = r4reg["sample"]["points"]
    sample = allpts[::2]
    ctx_map = {}
    for t in sample:
        src = os.path.join(R3, "context", "samples", f"CTX_{t}T120000Z.json")
        dst = os.path.join(ROOT, "context", f"CTX_{t}T120000Z.json")
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            ctx_map[t] = {"copy": f"context/CTX_{t}T120000Z.json", "sha256": sha_file(dst)}
    reg = {"task": "V1_R5_HERMES_FORECAST_DISCIPLINE", "registry_id": "v1r5-discipline-registry-r1",
            "frozen": True, "frozen_before_any_forecast": True, "frozen_at_utc": NOW,
            "r3_immutable": True, "r4_immutable": True, "r3_baseline_hash": b3["baseline_hash"], "r4_baseline_hash": b4["baseline_hash"],
            "focus": ["OVER_INFERENCE", "MECHANISM_JUMP", "COUNTER_EVIDENCE_MISSING", "OVERCONFIDENCE"],
            "mandatory_answers": ["what_i_know", "what_i_do_not_know", "evidence_for_primary", "evidence_against_primary",
                                    "mechanism_only_possible", "what_would_change_my_mind", "should_i_abstain_now"],
            "mechanism_status_vocabulary": ["SUPPORTED", "POSSIBLE", "WEAK", "UNKNOWN"],
            "confidence_fields": ["evidence_strength", "confidence", "uncertainty", "confidence_reason", "uncertainty_reason"],
            "sample": {"declared_pool": allpts, "r5_sample": sample, "n": len(sample),
                        "rule": "every 2nd point of the frozen R3 R4 sample (fixed rule; no re-selection)",
                        "EFFECTIVE_N": len(sample), "small_sample_declared": True},
            "comparisons": ["R3_BASELINE", "R5_HERMES", "SIMPLE_BASELINES"],
            "metrics": ["State", "Transition", "Scenario", "Direction", "Timing", "Calibration", "Abstention"],
            "gate": {"rule": "if R5 does not beat baseline -> CAPABILITY_GATE = CLOSED; discipline-only improvement -> PREDICTION = UNSUPPORTED"},
            "prompt_hashes": {"hermes_a_r5": hashlib.sha256(R5_PROMPT.encode()).hexdigest(),
                               "hermes_b_adversarial": hashlib.sha256(IMM_AUDIT_PROMPT.encode()).hexdigest(),
                               "hermes_b_post": hashlib.sha256(POST_PROMPT.encode()).hexdigest()},
            "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                             "V2_WRITE": 0, "V3_WRITE": 0, "BOUNDARY_VIOLATION": 0}}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r5_registry.json", reg)
    wtext("prompt/hermes_a_r5_prompt.txt", R5_PROMPT)
    wtext("prompt/hermes_b_adversarial_r5_prompt.txt", IMM_AUDIT_PROMPT)
    wtext("prompt/hermes_b_post_r5_prompt.txt", POST_PROMPT)
    wjson("registry/R5_CONTEXT_MAP.json", {"n": len(ctx_map), "points": ctx_map})
    ledger_append([{"event": "registry_frozen", "registry_hash": reg["registry_hash"], "r3": b3["baseline_hash"], "r4": b4["baseline_hash"]},
                    {"event": "contexts_staged", "n": len(ctx_map)},
                    {"event": "prompts_frozen", "prompt_hashes": reg["prompt_hashes"]}])
    print("ROOT:", ROOT)
    print("registry_hash:", reg["registry_hash"][:16], "| R3 baseline:", b3["baseline_hash"][:16], f"({b3['file_count']} files)",
          "| R4 baseline:", b4["baseline_hash"][:16], f"({b4['file_count']} files)")
    print("R5 sample (EFFECTIVE_N=%d):" % len(sample), sample)


if __name__ == "__main__":
    main()
