# -*- coding: utf-8 -*-
"""Freeze the F2b-R2 protocol: DRAFT -> FROZEN (with registry hash). Run BEFORE any evaluation."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "F2B_R2_FROZEN_PROTOCOL_DRAFT.json")
FROZEN = os.path.join(HERE, "F2B_R2_FROZEN_PROTOCOL.json")

p = json.load(open(DRAFT, encoding="utf-8"))
p["status"] = "FROZEN"
p["frozen_at_utc"] = "2026-10-02T00:25:00+00:00"
p["frozen_before_evaluation"] = True
p["run_order"] = "A1 -> A2 -> A3 -> A4 -> (only if all PASS) return validation; A1 or A2 FAIL => STATUS=PROTOCOL_VALIDATION_FAILED and STOP"
p["verdict_rule"] = {
    "VALIDATED_EDGE": "A1-A4 PASS AND cost-adjusted positive on IS AND OOS at 1x AND permutation p<0.05 AND bootstrap CI excludes 0 AND effective_n>=30 AND not dependent on a single session or a single volatility tercile AND the FADE direction has independent evidence",
    "NO_VALIDATED_EDGE": "anything else, after A1-A4 PASS",
    "DATA_BLOCKED": "the data or protocol cannot complete the validation",
    "PROTOCOL_VALIDATION_FAILED": "A1 or A2 FAIL (pre-flight abort; no return is computed)"
}
p["session_definition"] = {"ASIA": "00:00-07:59 UTC", "LONDON": "08:00-15:59 UTC", "NY": "16:00-23:59 UTC"}
p["fdr"] = {"method": "Benjamini-Hochberg", "alpha": 0.05, "family": "all R2 directional tests (2 directions x 5 horizons = 10 permutation p-values)"}
p["bounds"].update({"order_send": "NO", "live": "NO", "execution": "NO", "v1_read_as_input": "NO", "v2_read_as_input": "NO"})

body = {k: v for k, v in p.items() if k != "registry_hash_sha256"}
p["registry_hash_sha256"] = hashlib.sha256(
    json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
json.dump(p, open(FROZEN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote F2B_R2_FROZEN_PROTOCOL.json")
print("registry_hash_sha256 =", p["registry_hash_sha256"])
print("K20 =", p["corrected_definition"]["K_20"], " abs_z =", p["frozen_thresholds"]["abs_z"])
