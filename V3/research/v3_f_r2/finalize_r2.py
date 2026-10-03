# -*- coding: utf-8 -*-
"""F2b-R2 finalize: add registry/method/sub-sample summary + self hash; print sub-sample tables."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results_f2b_r2.json")
P = os.path.join(HERE, "F2B_R2_FROZEN_PROTOCOL.json")

proto = json.load(open(P, encoding="utf-8"))
res = json.load(open(R, encoding="utf-8"))
res["hypothesis_registry"] = proto["hypotheses"]
res["validation_method"] = proto["validation"]
res["corrected_definition"] = proto["corrected_definition"]
res["cost_model"] = proto["cost_model"]
res["session_definition"] = proto["session_definition"]
res["order_of_execution"] = ["A1 synthetic scale", "A2 synthetic rate", "A3 realised rate", "A4 no-silent-fix", "frozen return validation"]

# sub-sample stability summary: for each hypothesis x horizon, is the sign the same in every
# session bucket and every volatility tercile?
stab = {}
for hid, blk in res["hypotheses"].items():
    for hm, z in blk["horizons"].items():
        s = z.get("subsamples")
        if not s:
            continue
        row = {}
        for dim in ("session", "vol_tercile"):
            vals = {k: v["mean_bp"] for k, v in s[dim].items() if v["n"] >= 20}
            row[dim] = {"n_buckets": len(vals), "means": {k: round(v, 4) for k, v in vals.items()},
                        "all_same_sign": (len({(v > 0) for v in vals.values()}) == 1) if vals else None}
        stab[f"{hid}@{hm}m"] = row
res["subsample_stability"] = stab
res["artifacts_note"] = "run_f2b_r2.py contains one unused helper (meta_fn) left over from an earlier draft of the sub-sample code; it is never called and does not affect any number. The results file was produced by exactly this script revision."

json.dump(res, open(R, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
h = hashlib.sha256(open(R, "rb").read()).hexdigest()
print("results self sha256:", h)

print("\n=== FADE sub-samples (net-before-cost mean bp; buckets with n>=20) ===")
fade = res["hypotheses"]["F2bR2_MA_REVERSION_FADE"]
for hm, z in fade["horizons"].items():
    s = z.get("subsamples") or {}
    sess = {k: round(v["mean_bp"], 3) for k, v in (s.get("session") or {}).items() if v["n"] >= 20}
    vol = {k: round(v["mean_bp"], 3) for k, v in (s.get("vol_tercile") or {}).items() if v["n"] >= 20}
    print(f"  {hm:>3}m session={sess}")
    print(f"        vol    ={vol}")
print("\n=== cost stress (FADE, net bp) ===")
for hm, z in fade["horizons"].items():
    print(f"  {hm:>3}m", {k: round(v, 4) for k, v in z["net_bp_by_cost"].items()})
print("\nSTATUS =", res["STATUS"])
print("verdict_basis =", json.dumps(res.get("verdict_basis"), ensure_ascii=False))
