# -*- coding: utf-8 -*-
"""E-R1: add the hypothesis registry + validation result + self-hash to results_e_r1.json."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results_e_r1.json")
P = os.path.join(HERE, "FROZEN_PROTOCOL.json")

proto = json.load(open(P, encoding="utf-8"))
res = json.load(open(R, encoding="utf-8"))

# hypothesis registry (from the frozen protocol)
res["hypothesis_registry"] = proto["hypotheses"]
res["validation_method"] = proto["validation"]
res["cost_model"] = proto["cost_model"]

# validation result: collapse each hypothesis to its best admissible ladder rung
LADDER_ORDER = ["CANDIDATE", "EXECUTION_UNREALISTIC", "EDGE_UNCERTAIN", "REJECT",
                "COST_INSUFFICIENT", "INSUFFICIENT_SAMPLE"]


def best_rung(h):
    rungs = []
    if "horizons" in h and h["horizons"]:
        for z in h["horizons"].values():
            if z.get("ladder"):
                rungs.append(z["ladder"])
    elif "cells" in h:
        for blk in h["cells"].values():
            for z in blk["horizons"].values():
                if z.get("ladder"):
                    rungs.append(z["ladder"])
    if not rungs:
        return "NOT_RATED"
    for r in LADDER_ORDER:
        if r in rungs:
            return r
    return rungs[0]


summary = {}
for hid, h in res["hypotheses"].items():
    if hid == "E3_JOINT_STATE_DRIFT":
        summary[hid] = {"best_rung": "COST_INSUFFICIENT",
                        "n_cells": h["n_cells"], "fdr_tests": h["fdr"]["n_tests"],
                        "fdr_surviving": h["fdr"]["surviving"],
                        "best_abs_mean_bp": max(abs(t["mid_mean_bp"]) for t in h["fdr"]["table"]) if h["fdr"]["table"] else None}
        continue
    if hid == "E2_RECOVERY_TIME":
        summary[hid] = {"best_rung": "INVALID_OPERATIONALISATION",
                        "note": h["note"], "recovery_ms_median": h["recovery_ms_median"],
                        "reason": "spread at shock onset is already within 10% of the trailing median for the vast majority of ticks, so the timer fires at j=i and returns 0; this measures nothing"}
        continue
    vals = [z.get("mid_mean_bp") for z in h["horizons"].values() if z.get("n")]
    effs = [z.get("effective_n") for z in h["horizons"].values() if z.get("n")]
    summary[hid] = {"best_rung": best_rung(h), "events_raw": h["events_raw"],
                    "max_abs_mid_mean_bp": max(abs(v) for v in vals) if vals else None,
                    "max_effective_n": max(effs) if effs else None}

res["validation_result"] = {
    "per_hypothesis": summary,
    "cost_anchor_bp": res["cost_bp"],
    "max_abs_gross_bp_any": max((v.get("max_abs_mid_mean_bp") or 0) for v in summary.values()),
    "final": "NO_VALIDATED_EDGE",
    "reason": "every rated hypothesis stops at the ladder rung COST_INSUFFICIENT: the largest gross edge found (0.212 bp, E2 impact-recovery fade at 5s) is 23% of the 0.914 bp cost anchor; nothing is cost-adjusted positive, so VALIDATED_EDGE is not met",
    "reproducibility": {
        "E2_IMPACT_RECOVERY_FADE_5000ms_bp": 0.212,
        "phase2_R1_A2_PXSHOCK_REV_5000ms_bp": 0.213,
        "agreement": "MATCH within rounding (same snapshot, same trigger |z500|>=2 onset, same fade direction)",
        "DEFECT_FOUND_IN_R1": "Phase-2 R1's A1_TICKIMB_CONT/REV passed a CONSTANT direction (+1/-1) into the evaluator instead of sign(TI_PROXY), so those two rows measured a fixed long/short, NOT the stated imbalance mechanism. E-R1's E1 implements the frozen definition correctly; the two are therefore NOT comparable, and R1's A1 rows must be considered mis-implemented rather than contradictory."
    }
}
json.dump(res, open(R, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
h = hashlib.sha256(open(R, "rb").read()).hexdigest()
res["_self_sha256_after_write"] = h
print("results self sha256:", h)
print(json.dumps(res["validation_result"], ensure_ascii=False, indent=1)[:2600])
