# -*- coding: utf-8 -*-
"""Alpha Sweep R1 finalize: corrected taxonomy + registry + self hash."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results_alpha_sweep_r1.json")
P = os.path.join(HERE, "ALPHA_SWEEP_R1_FROZEN_PROTOCOL.json")

proto = json.load(open(P, encoding="utf-8"))
res = json.load(open(R, encoding="utf-8"))

res["hypothesis_registry"] = proto["hypotheses"]
res["validation_method"] = proto["validation"]
res["bounds"] = proto["bounds"]
res["cost_model"] = proto["cost_model"]

# --- corrected taxonomy (honest re-classification after the run) ---
tax = dict(res["taxonomy"])
CORRECTIONS = {}
for hid in ("S1_VOL_TERCILE", "S2_SPREAD_TERCILE", "S3_ACTIVITY_TERCILE", "S4_SESSION", "S5_TREND_RANGE"):
    for k in (hid, hid + "__MIRROR"):
        if k in tax:
            CORRECTIONS[k] = {"from": tax[k], "to": "INVALID_IMPLEMENTATION",
                              "reason": "the pre-registered per-bucket breakdown came back EMPTY (the meta lookup keyed bar-close ts while the evaluator passes entry-tick ts), so the stated conditioning test was never delivered; the pooled numbers merely duplicate P1_IMPULSE"}
            tax[k] = "INVALID_IMPLEMENTATION"
for k in ("P6_RANGE_COMPRESSION",):
    if k in tax:
        CORRECTIONS[k] = {"from": tax[k], "to": "NON_DIRECTIONAL",
                          "reason": "P6 is the only non-directional hypothesis (forward |move| vs baseline); the directional ladder does not apply"}
        tax[k] = "NON_DIRECTIONAL"
res["taxonomy"] = tax
res["taxonomy_corrections"] = CORRECTIONS

base = [k for k in res["hypotheses"] if not k.endswith("__MIRROR")]
ORDER = ["VALIDATED_EDGE", "EDGE_UNCERTAIN", "COST_INSUFFICIENT", "NON_DIRECTIONAL",
         "DATA_BLOCKED", "INVALID_IMPLEMENTATION"]
counts = {k: sum(1 for x in base if tax.get(x) == k) for k in ORDER}
valid = [x for x in base if tax.get(x) not in ("DATA_BLOCKED", "INVALID_IMPLEMENTATION")]

res["summary"] = {
    "hypotheses_total": proto["hypothesis_count"],
    "hypotheses_valid": len(valid),
    "validated_edge_count": counts["VALIDATED_EDGE"],
    "counts": counts,
    "counts_note": "base hypotheses only (the 23 __MIRROR rows are reported but are not independent evidence)",
    "best_net1x_bp": res["summary"].get("best_net1x_bp"),
    "best_gross_bp": res["summary"].get("best_gross_bp"),
    "best_oos_net1x_bp": res["summary"].get("best_oos_net1x_bp"),
    "eff_n_range": res["summary"].get("eff_n_range"),
    "best_where": None, "best_oos_where": None,
    "caveats": [
        "X3_HTF_REGIME_COND @60m is LONG-ONLY (|z5|>=2 AND ch60>0 AND ret5>0); in a sample with a prevailing upward gold drift a long-only signal cannot be distinguished from beta exposure. Its mirror is COST_INSUFFICIENT. Treat as confounded, not as a validated edge.",
        "P3_VOL_EXPANSION_DIR is the strongest hypothesis that is NOT confounded by being long-only: 60m gross +1.3652bp, net1x +0.4512bp, permutation p=0.0260, bootstrap CI [0.16, 2.52] excluding 0, IS +1.678 OOS +0.678 both positive -> it survives cost x1 but FAILS at cost x2 (net2x -0.4631bp).",
        "E-family is under-powered: only 75 calendar events fall inside the PIT2 tick window (the vintage holds 283 over 09-28..10-03; the snapshot ends 10-01 12:54Z). E1/E2/E4 use n=48..50 (eff_n 46..50). Treat family 5 as inconclusive.",
        "S-family (S1..S5) is INVALID_IMPLEMENTATION: the bucket breakdown came back empty, so the conditioning was not tested.",
        "E3_EVENT_X_SPREAD is DATA_BLOCKED (too few wide-spread events).",
        "T1/T3/T4/T5 are statistically the cleanest effects in the sweep (permutation p<=0.005, bootstrap CI excluding 0) and their gross edges are 0.09-0.21bp: real but roughly 4-10x too small to cover the 0.914bp round trip."
    ]
}
allz = [(k, hm, z) for k, blk in res["hypotheses"].items() if "horizons" in blk
        for hm, z in blk["horizons"].items() if z.get("gross_bp") is not None]
if allz:
    b = max(allz, key=lambda t: t[2]["gross_bp"])
    res["summary"]["best_where"] = {"id": b[0], "horizon": b[1], "gross_bp": b[2]["gross_bp"],
                                    "net1x_bp": b[2]["gross_bp"] - res["cost_bp"],
                                    "ladder": b[2]["ladder"], "eff_n": b[2]["effective_n"]}
    oo = [(k, hm, z) for k, hm, z in allz if z.get("oos", {}).get("net1x_bp") is not None]
    if oo:
        ob = max(oo, key=lambda t: t[2]["oos"]["net1x_bp"])
        res["summary"]["best_oos_where"] = {"id": ob[0], "horizon": ob[1],
                                            "oos_net1x_bp": ob[2]["oos"]["net1x_bp"], "n": ob[2]["n"]}

json.dump(res, open(R, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
h = hashlib.sha256(open(R, "rb").read()).hexdigest()
print("results self sha256:", h)
print(json.dumps(res["summary"], ensure_ascii=False, indent=1)[:2400])
print("\ncorrections:", json.dumps(res["taxonomy_corrections"], ensure_ascii=False, indent=1)[:900])
print("\nP6 non-directional:", json.dumps(res["hypotheses"]["P6_RANGE_COMPRESSION"]["horizons"], ensure_ascii=False)[:600])
