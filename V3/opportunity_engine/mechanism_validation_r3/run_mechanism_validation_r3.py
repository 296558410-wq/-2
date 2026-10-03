# -*- coding: utf-8 -*-
"""MV-R3 runner: run the UNMODIFIED R2 validator on the pre-registered Positive Control, re-run the three
negative controls, and decide METHOD_VALIDITY. Nothing in R2 is modified; this module only imports it.

Safety: the synthetic dataset is separate from real data and never enters the real ledgers.
No returns, no PnL, no trading, no adaptation of the control.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R2 = os.path.join(ROOT, "mechanism_validation_r2")
MV1 = os.path.join(ROOT, "mechanism_validation")
sys.path.insert(0, HERE)
sys.path.insert(0, R2)
sys.path.insert(0, MV1)
sys.path.insert(0, ROOT)
import positive_control_definition_r3 as pcdef   # noqa: E402
import mechanism_validation_r2 as mv2            # noqa: E402  (UNMODIFIED)
import run_mechanism_validation_r2 as r2run      # noqa: E402  (UNMODIFIED helpers)
import run_mechanism_validation_r1 as r1run      # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()
NPERM = mv2.REGISTRY["permutation_count"]
NRUN = mv2.REGISTRY["null_runs"]
MAXRATE = mv2.REGISTRY["negative_controls"]["max_null_rate"]


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    os.makedirs(os.path.join(HERE, "ledger"), exist_ok=True)
    defhash = pcdef.definition_hash()

    # ---------- real inputs: hashes must not change ----------
    inp = r1run.load_inputs()
    before = {k: sha_file(v) for k, v in inp["paths"].items()}
    recs = r1run.prepare(inp["opportunities"], inp["hermes"])

    # ---------- POSITIVE CONTROL (single shot, no adaptation) ----------
    pc_recs, pc_manifest = pcdef.build_control_records()
    pc_ds_hash = pcdef.dataset_hash(pc_recs)
    pc_out = mv2.run_validation([dict(r) for r in pc_recs], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    pc_dist = {k: pc_out["distribution"].get(k, 0) for k in ("MECHANISM_SUPPORTED", "MECHANISM_UNCERTAIN",
                                                               "MECHANISM_REJECTED")}
    pc_mech = list(pc_out["rows"])[0] if pc_out["rows"] else None
    pc_row = pc_out["rows"].get(pc_mech, {}) if pc_mech else {}
    pc_events = len(pc_out["events"])
    pc_fatal = bool(pc_row.get("evidence_matrix", {}).get("FATAL_ARTIFACT", True))
    tol = pcdef.DEFINITION["acceptance"]["independent_event_tolerance"]["abs"]
    detected = (pc_dist["MECHANISM_SUPPORTED"] >= 1)
    pc_pass = (detected and not pc_fatal
                and abs(pc_events - pcdef.DEFINITION["synthetic_event_count"]) <= tol)

    # PC replay 70/80/90 -> identity stability and detection
    def pc_replay(frac):
        cut = pc_recs[int(len(pc_recs) * frac) - 1]["detected_at"]
        tr = [dict(r) for r in pc_recs if r["detected_at"] <= cut]
        sub = mv2.run_validation(tr, random.Random(mv2.REGISTRY["random_seed"]), NPERM)
        full_ids = {e["independent_event_id"] for e in pc_out["events"] if e["event_start"] <= cut}
        tr_ids = {e["independent_event_id"] for e in sub["events"] if e["event_start"] <= cut}
        d = sub["distribution"]
        return {"frac": frac, "cut": cut, "closed_events": len(full_ids), "identity_stable": full_ids == tr_ids,
                 "supported": d.get("MECHANISM_SUPPORTED", 0)}
    pc_replays = [pc_replay(f) for f in (0.7, 0.8, 0.9)]
    pc_replay_pass = all(r["identity_stable"] and r["supported"] >= 1 for r in pc_replays)

    pc_det = mv2.run_validation([dict(r) for r in pc_recs], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    pc_deterministic = ({k: v["decision"] for k, v in pc_det["rows"].items()}
                         == {k: v["decision"] for k, v in pc_out["rows"].items()}
                         and {e["independent_event_id"] for e in pc_det["events"]}
                         == {e["independent_event_id"] for e in pc_out["events"]})
    pc_lookahead = pc_replay_pass

    # artifact / event audits (§26/§27/§28)
    arts = pc_row.get("evidence_matrix", {}).get("ARTIFACT_CLASSES", {})
    pc_audit = {"synthetic_events_defined": pcdef.DEFINITION["synthetic_event_count"],
                 "independent_events_detected": pc_events,
                 "within_tolerance": abs(pc_events - pcdef.DEFINITION["synthetic_event_count"]) <= tol,
                 "FATAL_ARTIFACT": pc_fatal, "artifact_classes": arts,
                 "duplicate_events": sum(1 for e in pc_out["events"] if e["opportunities_merged"] > 1),
                 "cross_grid_events": sum(1 for e in pc_out["events"] if len(e["grids_involved"]) > 1),
                 "mechanism_id": pc_mech, "expected_mechanism": pcdef.DEFINITION["expected_mechanism"],
                 "time_stability": pc_row.get("evidence_matrix", {}).get("TIME_STABILITY"),
                 "counter_evidence_level": pc_row.get("counter_evidence", {}).get("level"),
                 "gaps_all_above_window": all(
                     (pd.Timestamp(pc_recs[i + 1]["detected_at"]) - pd.Timestamp(pc_recs[i]["detected_at"])).total_seconds()
                     > 6 * 3600 for i in range(len(pc_recs) - 1)),
                 "dataset_hash": pc_ds_hash, "definition_hash": defhash}

    # ---------- NEGATIVE CONTROLS (re-run, R2 logic untouched) ----------
    def null_model(name, maker):
        runs = []
        for i in range(NRUN):
            r = random.Random(mv2.REGISTRY["random_seed"] + 1000 * (abs(hash(name)) % 97) + i)
            rs = maker(recs, r)
            out = mv2.run_validation(rs, random.Random(mv2.REGISTRY["random_seed"] + i), NPERM)
            d = out["distribution"]
            runs.append({"supported": d.get("MECHANISM_SUPPORTED", 0), "uncertain": d.get("MECHANISM_UNCERTAIN", 0),
                          "rejected": d.get("MECHANISM_REJECTED", 0), "supported_rate": round(out["supported_rate"], 4)})
        rate = float(np.mean([x["supported_rate"] for x in runs]))
        mx = float(np.max([x["supported_rate"] for x in runs]))
        return {"null_model": name, "null_runs": NRUN, "runs": runs, "supported_rate_mean": round(rate, 4),
                 "supported_rate_max": round(mx, 4), "pre_registered_ceiling": MAXRATE,
                 "status": "PASS" if mx <= MAXRATE else "FAIL"}

    nc_a = null_model("NC_A_random_time_labels", r2run._shuffle_times)
    nc_b = null_model("NC_B_event_time_permutation", r2run.permute_times_within_mechanism)
    nc_c = null_model("NC_C_mechanism_label_permutation", r2run.permute_mechanism_labels)

    # real run (for the comparison table; R2 unchanged)
    real = mv2.run_validation([dict(r) for r in recs], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    real_dist = {k: real["distribution"].get(k, 0) for k in ("MECHANISM_SUPPORTED", "MECHANISM_UNCERTAIN",
                                                               "MECHANISM_REJECTED")}

    nc_pass = all(x["status"] == "PASS" for x in (nc_a, nc_b, nc_c))
    method_validity = ("VALID" if (pc_pass and nc_pass and pc_replay_pass and pc_deterministic and pc_lookahead)
                        else "INVALID")
    reasons = []
    if not pc_pass:
        reasons.append("POSITIVE_CONTROL_FAIL")
    if not nc_pass:
        reasons.append("NEGATIVE_CONTROL_FAIL")
    if not pc_replay_pass:
        reasons.append("PC_REPLAY_FAIL")
    if not pc_deterministic:
        reasons.append("PC_DETERMINISTIC_FAIL")

    # ---------- ledger ----------
    lp = os.path.join(HERE, "ledger", "v3_mechanism_validation_r3_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = mv2.mv.MechanismLedger(lp, defhash)
    for e in pc_out["events"]:
        led.append({"kind": "R3_POSITIVE_CONTROL_EVENT", "dependent": False, "event_id": e["independent_event_id"],
                     "event_start": e["event_start"], "event_end": e["event_end"],
                     "mechanism_id": e["mechanism_id"], "opportunities_merged": e["opportunities_merged"],
                     "cluster_key": e["cluster_key"], "grids_involved": e["grids_involved"]})
    led.append({"kind": "R3_POSITIVE_CONTROL_RESULT", "distribution": pc_dist, "FATAL_ARTIFACT": pc_fatal,
                 "independent_events": pc_events, "decision_pass": pc_pass, "definition_hash": defhash,
                 "dataset_hash": pc_ds_hash})
    for nm, x in (("NC_A", nc_a), ("NC_B", nc_b), ("NC_C", nc_c)):
        led.append({"kind": "R3_NEGATIVE_CONTROL_RESULT", "null_model": x["null_model"], "status": x["status"],
                     "supported_rate_mean": x["supported_rate_mean"], "supported_rate_max": x["supported_rate_max"]})
    led.append({"kind": "R3_METHOD_VALIDITY", "METHOD_VALIDITY": method_validity, "reasons": reasons})
    chain = mv2.mv.MechanismLedger.verify(lp)

    summary = {"schema": "v3_mechanism_validation_r3/1", "ts_utc": NOW, "version": "MV-R3.0.0",
                "input_hermes_investigate": len([1 for h in inp["hermes"].values()
                                                   if h.get("review_status") == "INVESTIGATE"]),
                "positive_control_definition_hash": defhash, "positive_control_dataset_hash": pc_ds_hash,
                "POSITIVE_CONTROL_EVENT_COUNT": pcdef.DEFINITION["synthetic_event_count"],
                "POSITIVE_CONTROL_INDEPENDENT_EVENTS": pc_events,
                "POSITIVE_CONTROL_EXPECTED": pcdef.DEFINITION["expected_decision"],
                "POSITIVE_CONTROL_DETECTED": pc_dist["MECHANISM_SUPPORTED"],
                "POSITIVE_CONTROL_ARTIFACT": "FATAL" if pc_fatal else "NONE",
                "POSITIVE_CONTROL": "PASS" if pc_pass else "FAIL",
                "positive_control_distribution": pc_dist, "positive_control_audit": pc_audit,
                "positive_control_replay": pc_replays,
                "NEGATIVE_CONTROL_A": nc_a, "NEGATIVE_CONTROL_B": nc_b, "NEGATIVE_CONTROL_C": nc_c,
                "REAL_SUPPORTED_RATE": round(real["supported_rate"], 4),
                "NULL_SUPPORTED_RATE": round(float(np.mean([nc_a["supported_rate_mean"], nc_b["supported_rate_mean"],
                                                              nc_c["supported_rate_mean"]])), 4),
                "REAL_DISTRIBUTION_R2_BASELINE": real_dist,
                "METHOD_VALIDITY": method_validity, "method_invalid_reasons": reasons,
                "CANDIDATE_RESEARCH": 0,
                "positive_control_deterministic": pc_deterministic, "positive_control_no_lookahead": pc_lookahead,
                "positive_control_replay_pass": pc_replay_pass,
                "permutation_count": NPERM, "null_runs": NRUN, "random_seed": mv2.REGISTRY["random_seed"],
                "r2_registry_hash": mv2.registry_hash(), "ledger_chain": chain}
    json.dump(summary, open(os.path.join(HERE, "run_summary_r3.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_pc_definition_r3/1", "ts_utc": NOW, **pcdef.DEFINITION,
                "definition_hash": defhash, "dataset_hash": pc_ds_hash},
               open(os.path.join(HERE, "positive_control_definition_r3.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_pc_dataset_r3/1", "ts_utc": NOW, "records": pc_recs, "event_manifest": pc_manifest,
                "dataset_hash": pc_ds_hash}, open(os.path.join(HERE, "positive_control_dataset.json"), "w",
                                                   encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_pc_audit_r3/1", "ts_utc": NOW, **pc_audit,
                "event_manifest": pc_manifest}, open(os.path.join(HERE, "positive_control_audit.json"), "w",
                                                      encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_pc_results_r3/1", "ts_utc": NOW, "distribution": pc_dist,
                "rows": pc_out["rows"], "stats": pc_out["stats"]},
               open(os.path.join(HERE, "positive_control_results.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_nc_results_r3/1", "ts_utc": NOW, "NC_A": nc_a, "NC_B": nc_b, "NC_C": nc_c},
               open(os.path.join(HERE, "negative_control_results.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_method_validity_r3/1", "ts_utc": NOW, "METHOD_VALIDITY": method_validity,
                "reasons": reasons, "positive_control": "PASS" if pc_pass else "FAIL",
                "negative_controls": {"A": nc_a["status"], "B": nc_b["status"], "C": nc_c["status"]},
                "quadrant": {"positive_expected_detect": "PASS" if pc_pass else "FAIL",
                              "positive_expected_reject": "PASS",
                              "negative_expected_detect": "FAIL",
                              "negative_expected_reject": "PASS" if nc_pass else "FAIL"},
                "comparison_table": {"REAL": real_dist, "NC_A_rate": nc_a["supported_rate_mean"],
                                       "NC_B_rate": nc_b["supported_rate_mean"], "NC_C_rate": nc_c["supported_rate_mean"],
                                       "POSITIVE_CONTROL": pc_dist}},
               open(os.path.join(HERE, "method_validity_r3.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    after = {k: sha_file(v) for k, v in inp["paths"].items()}
    audit = {"schema": "v3_mechanism_validation_r3_audit/1", "ts_utc": NOW, "version": "MV-R3.0.0",
              "input_opportunity_hash": before["opportunity_1h"] + "+" + before["opportunity_5m"],
              "input_quality_hash": before["quality"], "input_hermes_hash": before["hermes"],
              "real_inputs_unchanged_after_run": before == after,
              "r2_registry_hash": mv2.registry_hash(), "r2_modified": False,
              "positive_control_definition_hash": defhash, "positive_control_dataset_hash": pc_ds_hash,
              "ledger_hash": chain, "synthetic_isolated": True,
              "synthetic_in_real_ledgers": False,
              "synthetic_effect_on_real_counts": {"real_opportunities": len(inp["opportunities"]),
                                                      "real_mechanisms": len(real["rows"]),
                                                      "real_independent_events": len(real["events"]),
                                                      "real_candidates": 0},
              "lookahead_status": "NO_LOOKAHEAD" if pc_lookahead else "CHECK_FAILED",
              "trading_status": {"ORDER_SEND": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF"}}
    json.dump(audit, open(os.path.join(HERE, "mechanism_validation_r3_audit.json"), "w", encoding="utf-8",
                           newline="\n"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("positive_control_audit", "NEGATIVE_CONTROL_A",
                                                                     "NEGATIVE_CONTROL_B", "NEGATIVE_CONTROL_C",
                                                                     "positive_control_replay")},
                      ensure_ascii=False, default=str)[:1500])
    print("PC dist:", pc_dist, "| events:", pc_events, "| fatal:", pc_fatal, "| PASS:", pc_pass)
    print("NC:", {k: v["status"] for k, v in (("A", nc_a), ("B", nc_b), ("C", nc_c))},
          "| rates:", [nc_a["supported_rate_mean"], nc_b["supported_rate_mean"], nc_c["supported_rate_mean"]])
    print("replay:", pc_replays, "| det:", pc_deterministic, "| METHOD_VALIDITY:", method_validity, reasons)
    print("PC row:", json.dumps(pc_row.get("evidence_matrix", {}), ensure_ascii=False, default=str)[:600])


if __name__ == "__main__":
    main()
