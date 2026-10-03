# -*- coding: utf-8 -*-
"""V3 Mechanism Validation R2 — orchestrator: real data + Positive Control + 3 Null Models + method validity.

Pre-registered before running (see REGISTRY): statistic definitions, permutation_count=500, random_seed,
null_runs=20, max_null_rate=0.25, positive-control expectation.
R1's clustering and mechanism identity are reused UNCHANGED. No profit quantity exists anywhere.
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
MV1 = os.path.join(ROOT, "mechanism_validation")
sys.path.insert(0, HERE)
sys.path.insert(0, MV1)
sys.path.insert(0, ROOT)
import mechanism_validation_r2 as mv2  # noqa: E402
import run_mechanism_validation_r1 as r1run  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()


def sha_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def permute_times_within_mechanism(recs: list[dict], rng: random.Random) -> list[dict]:
    out = []
    groups: dict[str, list[dict]] = {}
    for r in recs:
        groups.setdefault(r["mechanism_id"], []).append(r)
    for m, rs in groups.items():
        times = [r["detected_at"] for r in rs]
        rng.shuffle(times)
        for r, t in zip(rs, times):
            q = dict(r)
            q["detected_at"] = t
            out.append(q)
    out.sort(key=lambda r: r["detected_at"])
    return out


def permute_mechanism_labels(recs: list[dict], rng: random.Random) -> list[dict]:
    labels = [r["mechanism_id"] for r in recs]
    rng.shuffle(labels)
    out = []
    for r, lab in zip(recs, labels):
        q = dict(r)
        q["mechanism_id"] = lab
        q["cluster_key"] = mv2.mv.cluster_key(q["signals"], lab)
        out.append(q)
    return sorted(out, key=lambda r: r["detected_at"])


def main():
    os.makedirs(HERE, exist_ok=True)
    os.makedirs(os.path.join(HERE, "ledger"), exist_ok=True)
    reg_hash = mv2.registry_hash()
    NPERM = mv2.REGISTRY["permutation_count"]
    NRUN = mv2.REGISTRY["null_runs"]
    MAXRATE = mv2.REGISTRY["negative_controls"]["max_null_rate"]

    inp = r1run.load_inputs()
    paths = inp["paths"]
    before = {k: sha_file(v) for k, v in paths.items()}
    recs = r1run.prepare(inp["opportunities"], inp["hermes"])
    rng = random.Random(mv2.REGISTRY["random_seed"])

    # ---------------- REAL ----------------
    real = mv2.run_validation([dict(r) for r in recs], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    real_dist = {k: real["distribution"].get(k, 0) for k in ("MECHANISM_SUPPORTED", "MECHANISM_UNCERTAIN",
                                                               "MECHANISM_REJECTED")}

    # ---------------- POSITIVE CONTROL ----------------
    pc = mv2.run_validation(mv2.positive_control_records(), random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    pc_dist = {k: pc["distribution"].get(k, 0) for k in ("MECHANISM_SUPPORTED", "MECHANISM_UNCERTAIN",
                                                           "MECHANISM_REJECTED")}
    pc_pass = pc_dist["MECHANISM_SUPPORTED"] >= 1

    # ---------------- NULL MODELS ----------------
    def null_model(name, maker):
        runs = []
        for i in range(NRUN):
            r2 = random.Random(mv2.REGISTRY["random_seed"] + 1000 * (hash(name) % 97) + i)
            rs = maker(recs, r2)
            out = mv2.run_validation(rs, random.Random(mv2.REGISTRY["random_seed"] + i), NPERM)
            d = out["distribution"]
            runs.append({"supported": d.get("MECHANISM_SUPPORTED", 0),
                          "uncertain": d.get("MECHANISM_UNCERTAIN", 0),
                          "rejected": d.get("MECHANISM_REJECTED", 0),
                          "supported_rate": round(out["supported_rate"], 4)})
        rate = float(np.mean([r["supported_rate"] for r in runs]))
        max_rate = float(np.max([r["supported_rate"] for r in runs]))
        return {"null_model": name, "null_runs": NRUN, "runs": runs,
                 "supported_rate_mean": round(rate, 4), "supported_rate_max": round(max_rate, 4),
                 "status": ("PASS" if max_rate <= MAXRATE else "FAIL"),
                 "pre_registered_ceiling": MAXRATE}

    nc_a = null_model("NC_A_random_time_labels", lambda rs, r: _shuffle_times(rs, r))
    nc_b = null_model("NC_B_event_time_permutation", permute_times_within_mechanism)
    nc_c = null_model("NC_C_mechanism_label_permutation", permute_mechanism_labels)

    # ---------------- replay / deterministic / lookahead gates ----------------
    def replay_frac(frac):
        cut = recs[int(len(recs) * frac) - 1]["detected_at"]
        tr = [r for r in recs if r["detected_at"] <= cut]
        sub = mv2.run_validation([dict(r) for r in tr], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
        full_ids = {e["independent_event_id"] for e in real["events"] if e["event_start"] <= cut}
        tr_ids = {e["independent_event_id"] for e in sub["events"] if e["event_start"] <= cut}
        return {"frac": frac, "cut": cut, "closed_events": len(full_ids), "identity_stable": full_ids == tr_ids}

    replay = [replay_frac(f) for f in (0.7, 0.8, 0.9)]
    replay_pass = all(r["identity_stable"] for r in replay)
    det = mv2.run_validation([dict(r) for r in recs], random.Random(mv2.REGISTRY["random_seed"]), NPERM)
    deterministic_pass = ({k: v["decision"] for k, v in det["rows"].items()}
                           == {k: v["decision"] for k, v in real["rows"].items()})
    lookahead_pass = all(r["identity_stable"] for r in replay)   # a closed window's identity cannot change

    method_validity = ("VALID" if (pc_pass and nc_a["status"] == "PASS" and nc_b["status"] == "PASS"
                                     and nc_c["status"] == "PASS" and replay_pass and deterministic_pass
                                     and lookahead_pass) else "INVALID")
    reasons = []
    if not pc_pass:
        reasons.append("POSITIVE_CONTROL_FAIL")
    for nm, nmr in (("NC_A", nc_a), ("NC_B", nc_b), ("NC_C", nc_c)):
        if nmr["status"] != "PASS":
            reasons.append(f"{nm}_FAIL")
    if not replay_pass:
        reasons.append("REPLAY_FAIL")
    if not deterministic_pass:
        reasons.append("DETERMINISTIC_FAIL")
    if not lookahead_pass:
        reasons.append("LOOKAHEAD_FAIL")

    # ---------------- candidates (hard gate) ----------------
    cands = []
    if method_validity == "VALID":
        for m, r in real["rows"].items():
            if (r["decision"] == "MECHANISM_SUPPORTED" and r["events"] >= mv2.REGISTRY["minimum_independent_events"]
                    and not r["evidence_matrix"]["FATAL_ARTIFACT"]):
                cands.append({"mechanism_id": m, "mechanism_name": r["mechanism_name"],
                                "independent_event_count": r["events"],
                                "trigger_definition": sorted(r["evidence_matrix"]["detail"].keys()) or [],
                                "evidence_matrix": r["evidence_matrix"], "counter_evidence": r["counter_evidence"],
                                "causality_level": r["causality_level"], "proxy_dependency": r["proxy_dependency"],
                                "next_stage": "INDEPENDENT_MECHANISM_VALIDATION",
                                "forbidden_next": ["FORWARD", "SHADOW", "LIVE", "ORDER"]})

    # ---------------- ablations ----------------
    def ablate(drop):
        out = {}
        for m, r in real["rows"].items():
            em = dict(r["evidence_matrix"])
            if drop == "drop_temporal_stability":
                em["TIME_STABILITY"] = "HIGH"
            elif drop == "drop_session_stability":
                em["SESSION_STABILITY"] = "HIGH"
            elif drop == "drop_state_stability":
                em["STATE_STABILITY"] = "HIGH"
            elif drop == "drop_counter_evidence":
                em["COUNTER_EVIDENCE_LEVEL"] = "UNKNOWN"
            elif drop == "drop_recurrence":
                em["INDEPENDENT_EVENTS"] = "SUFFICIENT"
            elif drop == "drop_artifact_gate":
                em["FATAL_ARTIFACT"] = False
            elif drop == "drop_duplication_evidence":
                em["ARTIFACT_CLASSES"] = {k: v for k, v in em["ARTIFACT_CLASSES"].items()
                                            if k != "DUPLICATION_ARTIFACT"}
            d, _, _ = mv2.decide_r2(em, em["COUNTER_EVIDENCE_LEVEL"], em["FATAL_ARTIFACT"])
            out[d] = out.get(d, 0) + 1
        return out
    ablations = {k: ablate(k) for k in ("drop_temporal_stability", "drop_session_stability", "drop_state_stability",
                                          "drop_counter_evidence", "drop_recurrence", "drop_artifact_gate",
                                          "drop_duplication_evidence")}
    ablations["none"] = real_dist

    # ---------------- ledger + outputs ----------------
    lp = os.path.join(HERE, "ledger", "v3_mechanism_validation_r2_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = mv2.mv.MechanismLedger(lp, reg_hash)
    for m, r in sorted(real["rows"].items()):
        led.append({"kind": "R2_MECHANISM_DECISION", **r})
    for e in real["events"]:
        led.append({"kind": "R2_INDEPENDENT_EVENT", "mechanism_id": e["mechanism_id"],
                     "independent_event_id": e["independent_event_id"], "event_start": e["event_start"],
                     "event_end": e["event_end"], "grids_involved": e["grids_involved"],
                     "opportunities_merged": e["opportunities_merged"], "cluster_key": e["cluster_key"]})
    chain = mv2.mv.MechanismLedger.verify(lp)

    summary = {"schema": "v3_mechanism_validation_r2/1", "ts_utc": NOW, "version": mv2.MV2_VERSION,
                "input_hermes_investigate": len([1 for h in inp["hermes"].values()
                                                   if h.get("review_status") == "INVESTIGATE"]),
                "mechanism_count": len(real["rows"]), "independent_event_count": len(real["events"]),
                "decisions": real_dist, "candidate_research": len(cands),
                "METHOD_VALIDITY": method_validity, "method_invalid_reasons": reasons,
                "POSITIVE_CONTROL": {"detected": pc_dist["MECHANISM_SUPPORTED"],
                                       "decision": "PASS" if pc_pass else "FAIL", "distribution": pc_dist,
                                       "definition": mv2.REGISTRY["positive_control"]["definition"]},
                "NEGATIVE_CONTROL_A": nc_a, "NEGATIVE_CONTROL_B": nc_b, "NEGATIVE_CONTROL_C": nc_c,
                "REAL_SUPPORTED_RATE": round(real["supported_rate"], 4),
                "NULL_SUPPORTED_RATE": round(float(np.mean([nc_a["supported_rate_mean"], nc_b["supported_rate_mean"],
                                                              nc_c["supported_rate_mean"]])), 4),
                "EXCESS_SUPPORTED": round(real["supported_rate"] - float(np.mean([nc_a["supported_rate_mean"],
                                                                                    nc_b["supported_rate_mean"],
                                                                                    nc_c["supported_rate_mean"]])), 4),
                "artifact_risk_high": sum(1 for r in real["rows"].values()
                                            if r["evidence_matrix"]["ARTIFACT_CLASSES"]
                                            and any(v["count"] for k, v in r["evidence_matrix"]["ARTIFACT_CLASSES"].items()
                                                     if k != "FATAL_ARTIFACT" and v.get("count"))),
                "counter_evidence_high": sum(1 for r in real["rows"].values()
                                               if r["counter_evidence"]["level"] in ("FATAL", "STRONG")),
                "permutation_count": NPERM, "random_seed": mv2.REGISTRY["random_seed"],
                "replay": replay, "deterministic": deterministic_pass, "lookahead": lookahead_pass,
                "evidence_dependency": mv2.evidence_independence(), "ablations": ablations,
                "registry_hash": reg_hash}
    files = {
        "mechanism_validation_r2_registry.json": mv2.REGISTRY,
        "positive_control_definition.json": mv2.REGISTRY["positive_control"],
        "negative_control_definition.json": mv2.REGISTRY["negative_controls"],
        "null_distributions.json": {"schema": "v3_null_distributions/1", "ts_utc": NOW,
                                      "REAL": {"distribution": real_dist, "supported_rate": round(real["supported_rate"], 4)},
                                      "NC_A": nc_a, "NC_B": nc_b, "NC_C": nc_c,
                                      "POSITIVE_CONTROL": {"distribution": pc_dist, "detected": pc_dist["MECHANISM_SUPPORTED"]},
                                      "mechanism_level_stats": {m: real["stats"][m] for m in real["stats"]}},
        "method_validity_report.json": {"schema": "v3_method_validity/1", "ts_utc": NOW,
                                          "METHOD_VALIDITY": method_validity, "reasons": reasons,
                                          "positive_control": "PASS" if pc_pass else "FAIL",
                                          "negative_control_a": nc_a["status"], "negative_control_b": nc_b["status"],
                                          "negative_control_c": nc_c["status"], "replay": replay_pass,
                                          "deterministic": deterministic_pass, "no_lookahead": lookahead_pass,
                                          "comparison_table": {
                                              "Real": real_dist, "NC_A": nc_a["runs"][0] and {"supported_rate": nc_a["supported_rate_mean"]},
                                              "NC_B": {"supported_rate": nc_b["supported_rate_mean"]},
                                              "NC_C": {"supported_rate": nc_c["supported_rate_mean"]},
                                              "Positive_Control": pc_dist}},
        "mechanism_clusters_r2.json": {"schema": "v3_mechanism_clusters_r2/1", "ts_utc": NOW,
                                         "clusters": {m: sorted({e["cluster_key"] for e in evs})
                                                       for m, evs in real["by_mech"].items()}},
        "mechanism_events_r2.json": {"schema": "v3_mechanism_events_r2/1", "ts_utc": NOW,
                                       "events": [{"mechanism_id": e["mechanism_id"],
                                                    "independent_event_id": e["independent_event_id"],
                                                    "event_start": e["event_start"], "event_end": e["event_end"],
                                                    "grids_involved": e["grids_involved"],
                                                    "opportunities_merged": e["opportunities_merged"],
                                                    "cluster_key": e["cluster_key"]} for e in real["events"]]},
        "mechanism_evidence_r2.json": {"schema": "v3_mechanism_evidence_r2/1", "ts_utc": NOW,
                                         "evidence": {m: real["rows"][m]["evidence_matrix"] for m in real["rows"]},
                                         "counter_evidence": {m: real["rows"][m]["counter_evidence"] for m in real["rows"]},
                                         "evidence_dependency": mv2.evidence_independence()},
        "mechanism_decisions_r2.json": {"schema": "v3_mechanism_decisions_r2/1", "ts_utc": NOW,
                                          "decisions": real["rows"]},
        "candidate_research_r2.json": {"schema": "v3_candidate_research_r2/1", "ts_utc": NOW, "entries": cands,
                                         "note": "only produced when METHOD_VALIDITY == VALID; stage-2 input only"},
    }
    for name, obj in files.items():
        json.dump(obj, open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n"), indent=1,
                  ensure_ascii=False)
    after = {k: sha_file(v) for k, v in paths.items()}
    summary["ledger_chain"] = chain
    json.dump(summary, open(os.path.join(HERE, "run_summary_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    audit = {"schema": "v3_mechanism_validation_r2_audit/1", "ts_utc": NOW, "version": mv2.MV2_VERSION,
              "input_opportunity_hash": before["opportunity_1h"] + "+" + before["opportunity_5m"],
              "input_quality_hash": before["quality"], "input_hermes_hash": before["hermes"],
              "inputs_unchanged_after_run": before == after,
              "registry_hash": reg_hash,
              "mechanism_output_hash": hashlib.sha256(json.dumps(summary, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
              "ledger_hash": chain, "data_sources": ["R1 opportunity ledger (immutable)", "quality ledger (immutable)",
                                                       "hermes quality reviews (immutable)"],
              "timestamp_policy": "permutation statistics use the mechanism's own event times only; no future data",
              "lookahead_status": "NO_LOOKAHEAD" if lookahead_pass else "CHECK_FAILED",
              "negative_control_status": [nc_a["status"], nc_b["status"], nc_c["status"]],
              "positive_control_status": "PASS" if pc_pass else "FAIL",
              "causality_policy": "CO_MOVEMENT only; UST10Y is always the ^TNX PROXY"}
    json.dump(audit, open(os.path.join(HERE, "mechanism_validation_r2_audit.json"), "w", encoding="utf-8",
                           newline="\n"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("ablations", "replay")}, ensure_ascii=False,
                      default=str)[:1800])
    print("NC:", json.dumps({"A": nc_a["status"], "B": nc_b["status"], "C": nc_c["status"],
                              "A_rate": nc_a["supported_rate_mean"], "B_rate": nc_b["supported_rate_mean"],
                              "C_rate": nc_c["supported_rate_mean"]}, ensure_ascii=False))
    print("PC:", pc_dist, "| REAL:", real_dist, "| METHOD_VALIDITY:", method_validity, reasons)
    print("replay:", replay, "| det:", deterministic_pass, "| chain:", chain)
    for m, r in sorted(real["rows"].items()):
        print(f"  {m} ev={r['events']:>3} time={r['evidence_matrix']['TIME_STABILITY']:8s} "
               f"session={r['evidence_matrix']['SESSION_STABILITY']:16s} state={r['evidence_matrix']['STATE_STABILITY']:16s} "
               f"ce={r['counter_evidence']['level']:8s} fatal={r['evidence_matrix']['FATAL_ARTIFACT']} -> {r['decision']}")


def _shuffle_times(recs, rng):
    out = [dict(r) for r in recs]
    ts = [r["detected_at"] for r in out]
    rng.shuffle(ts)
    for r, t in zip(out, ts):
        r["detected_at"] = t
    return sorted(out, key=lambda r: r["detected_at"])


if __name__ == "__main__":
    main()
