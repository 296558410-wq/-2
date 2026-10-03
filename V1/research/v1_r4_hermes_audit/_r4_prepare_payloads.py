# -*- coding: utf-8 -*-
"""V1-R4 — PREPARE AUDIT PAYLOADS (adversarial & post-outcome).

Adversarial payload = frozen PIT context + Hermes-A forecast (NO outcome).
Post-outcome payload = the above + the ACTUAL outcome taken from the independent R3 evaluator.
The outcome is written into the R4 tree ONLY; R3 artifacts are never modified.
"""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
R3 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r4_hermes_audit")


def main():
    reg = json.load(open(os.path.join(ROOT, "registry", "v1_r4_audit_registry.json"), encoding="utf-8"))
    pts = reg["sample"]["points"]
    ev = json.load(open(os.path.join(R3, "evaluation", "BLIND_EVALUATION.json"), encoding="utf-8"))
    by_ts = {p["ts"]: p for p in ev["points"]}
    n_adv = n_post = 0
    for t in pts:
        ctx = json.load(open(os.path.join(ROOT, "context", f"CTX_{t}T120000Z.json"), encoding="utf-8"))
        fcp = os.path.join(R3, "forecasts", f"HERMES_FULL_CTX_{t}T120000Z.json")
        if not os.path.exists(fcp):
            continue
        fc = json.load(open(fcp, encoding="utf-8"))
        adv = {"audit_id": f"ADV_{t}", "point": t,
                "instruction": "Audit Hermes-A's forecast against the PIT context. Find what is WRONG. You do NOT see the outcome.",
                "pit_context": ctx, "hermes_a_forecast": fc}
        with open(os.path.join(ROOT, "adversarial_audits", f"PAYLOAD_ADV_{t}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(adv, fh, indent=1, ensure_ascii=False)
        n_adv += 1
        p = by_ts.get(t)
        if p is None:
            continue
        outcome = {"actual_next_state": p["actual_next"], "actual_transition": p["actual_transition"],
                    "actual_direction": p["actual_direction"], "hermes_scenario_covered_actual": p["scenario_covers_actual"],
                    "baseline_persistence_state": p["persistence"], "baseline_previous_state": p["previous_state"]}
        post = {"audit_id": f"POST_{t}", "point": t,
                 "instruction": "Post-outcome audit: judge Hermes-A's forecast against what actually happened. Do not defend it.",
                 "pit_context": ctx, "hermes_a_forecast": fc, "actual_outcome": outcome}
        with open(os.path.join(ROOT, "post_outcome", f"PAYLOAD_POST_{t}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(post, fh, indent=1, ensure_ascii=False)
        n_post += 1
    print("adversarial payloads:", n_adv, "| post-outcome payloads:", n_post, "| points:", len(pts))


if __name__ == "__main__":
    main()
