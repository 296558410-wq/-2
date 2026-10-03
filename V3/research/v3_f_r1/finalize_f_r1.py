# -*- coding: utf-8 -*-
"""F-R1: add hypothesis registry + validation result + self-hash to results_f_r1.json."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results_f_r1.json")
P = os.path.join(HERE, "FROZEN_PROTOCOL.json")

proto = json.load(open(P, encoding="utf-8"))
res = json.load(open(R, encoding="utf-8"))

res["hypothesis_registry"] = proto["hypotheses"]
res["validation_method"] = proto["validation"]
res["cost_model"] = proto["cost_model"]
res["data"] = proto["data"]

LADDER_ORDER = ["CANDIDATE", "EXECUTION_UNREALISTIC", "EDGE_UNCERTAIN", "REJECT",
                "COST_INSUFFICIENT", "INSUFFICIENT_SAMPLE"]


def best_rung(h):
    rungs = [z["ladder"] for z in h.get("horizons", {}).values() if z.get("ladder")]
    if not rungs:
        return "NOT_RATED"
    for r in LADDER_ORDER:
        if r in rungs:
            return r
    return rungs[0]


summary = {}
for hid, h in res["hypotheses"].items():
    if hid == "F1c_RETURN_AUTOCORR":
        summary[hid] = {"best_rung": "DESCRIPTIVE",
                        "lags": {k: round(v["autocorr"], 5) for k, v in h["lags"].items()}}
        continue
    if hid == "F3a_VOL_EXPANSION":
        summary[hid] = {"best_rung": "NON_DIRECTIONAL", "n_onsets": h["n_onsets"],
                        "max_abs_lift": max(abs(z.get("lift") or 0) for z in h["horizons"].values())}
        continue
    if hid == "F3b_VOL_DECAY":
        summary[hid] = {"best_rung": "DESCRIPTIVE", "onsets": h["n_onsets"],
                        "median_half_life_bars": h["half_life_bars_median"]}
        continue
    vals = [z.get("mid_mean_bp") for z in h["horizons"].values() if z.get("n")]
    summary[hid] = {"best_rung": best_rung(h), "events_raw": h["events_raw"],
                    "max_abs_mid_mean_bp": max(abs(v) for v in vals) if vals else None,
                    "horizons_bp": {k: round(z["mid_mean_bp"], 4) for k, z in h["horizons"].items() if z.get("n")}}

res["validation_result"] = {
    "per_hypothesis": summary,
    "cost_anchor_bp": res["cost_bp"],
    "final": "NO_VALIDATED_EDGE",
    "reason": "no hypothesis satisfied the VALIDATED_EDGE requirement (cost-adjusted positive on IS AND OOS at 1x, permutation p<0.05, bootstrap CI excluding 0, effective_n>=30, sign stable across sub-segments, survives 2x). The two that cleared cost x1 gross (F2b 5m = +3.514bp, F1b 60m = +1.433bp) both fail elsewhere: F1b 60m has a bootstrap CI spanning 0 ([-1.779,+4.661]) and a NEGATIVE OOS (-1.152bp); F2b 5m rests on only 102 raw events selected by a mis-scaled threshold (see defects).",
    "must_see": [
        {"id": "F2b_MA_REVERSION", "horizon_min": 5, "mid_mean_bp": 3.514, "effective_n": 68,
         "n_raw": 101, "perm_p": 0.01499, "boot_ci": [0.973, 6.651], "is_bp": 2.378, "oos_bp": 6.790,
         "rung": "CANDIDATE",
         "caveat": "NOT a validated edge: raw n=102 over 35 days (~3/day) and the trigger threshold is mis-scaled (see defects) so only ~5-sigma outliers were selected; std=14.88bp is 4x the mean. Needs a NEW frozen protocol with a correctly scaled z before any weight is placed on it."},
        {"id": "F1b_VOLADJ_MOMENTUM_CONT", "horizon_min": 60, "mid_mean_bp": 1.433, "effective_n": 323,
         "n_raw": 2089, "perm_p": 0.0290, "boot_ci": [-1.779, 4.661], "is_bp": 2.526, "oos_bp": -1.152,
         "rung": "EDGE_UNCERTAIN",
         "caveat": "gross clears cost x1 but the bootstrap CI includes 0 and OOS goes negative -> not stable"}
    ],
    "defects_found": [
        {"id": "F2b_ZMA_MISSCALED", "severity": "measurement",
         "detail": "zma = (close - sma20) / (close * sig20 * sqrt(20)). For a random walk the numerator has std ~1.82*sig1 while the denominator is 4.47*sig1, so the statistic is scaled down by ~2.46x and |zma|>=2 selects ~4.9-sigma outliers. Only 102 of 47,963 bars triggered (0.21%) instead of the ~4.6% a true 2-sigma cut would give. The F2b numbers therefore describe extreme-tail reversion, NOT the stated MA-reversion hypothesis.",
         "action": "do NOT re-tune inside this round (the protocol is frozen). If MA-reversion is worth pursuing, freeze a NEW protocol with a correctly scaled z and re-run."},
        {"id": "F3A_NANMAX_WARNING", "severity": "minor",
         "detail": "the F3a regime-switch probability loop hit an all-NaN slice on some bars (RuntimeWarning); the switch probabilities are therefore approximate, but they are a by-product metric and do not affect any ladder verdict."}
    ],
    "reproducibility_notes": [
        "F3a lift is ~0 at every horizon (max |lift| 0.0088) -> no volatility-expansion effect at 1m-60m on this corpus",
        "F1c lag-1 autocorrelation of 1m returns = -0.0197 (lag-3 -0.0286): a small negative (reverting) autocorrelation, consistent with the tiny 1m fade seen in F2a but far too small to cover cost",
        "F2a is the exact mirror of F1a, and the 60m pair (+0.854 / -0.854) again shows the mirror signature: no directional transmission"
    ]
}
json.dump(res, open(R, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
h = hashlib.sha256(open(R, "rb").read()).hexdigest()
print("results self sha256:", h)
print(json.dumps(res["validation_result"], ensure_ascii=False, indent=1)[:3000])
