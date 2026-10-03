# -*- coding: utf-8 -*-
"""V3 Opportunity Mechanism Validation R1 — orchestrator.

Inputs (IMMUTABLE): R1 opportunity ledgers + quality ledger + hermes quality reviews.
Primary subject: the 404 Hermes INVESTIGATE opportunities.
Outputs: mechanism clusters / independent events / evidence / decisions / research cache /
candidate research / audit / ledger.
NO trading path. NO future-return input. NO mutation of any prior ledger.
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
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import mechanism_validation as mv  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()


def sha_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_inputs() -> dict:
    opp, qual, hermes = {}, {}, {}
    for grid in ("1h", "5m"):
        p = os.path.join(ROOT, "ledger", f"v3_opportunity_ledger_{grid}.jsonl")
        for line in open(p, encoding="utf-8"):
            if line.strip():
                pl = json.loads(line)["payload"]
                pl["_grid"] = grid
                opp[pl["opportunity_id"]] = pl
    qp = os.path.join(ROOT, "ledger", "v3_opportunity_quality_ledger.jsonl")
    for line in open(qp, encoding="utf-8"):
        if line.strip():
            pl = json.loads(line)["payload"]
            qual[pl["opportunity_id"]] = pl
    hp = os.path.join(ROOT, "hermes", "hermes_quality_reviews.json")
    for r in json.load(open(hp, encoding="utf-8"))["reviews"]:
        hermes[r["opportunity_id"]] = r
    return {"opportunities": opp, "quality": qual, "hermes": hermes,
             "paths": {"opportunity_1h": os.path.join(ROOT, "ledger", "v3_opportunity_ledger_1h.jsonl"),
                        "opportunity_5m": os.path.join(ROOT, "ledger", "v3_opportunity_ledger_5m.jsonl"),
                        "quality": qp, "hermes": hp}}


def prepare(opp: dict, hermes: dict, restrict_ids: list[str] | None = None) -> list[dict]:
    """Build mechanism-ready records from the Hermes INVESTIGATE set (or any supplied id set)."""
    recs = []
    for oid, h in hermes.items():
        if restrict_ids is not None and oid not in restrict_ids:
            continue
        if h.get("review_status") != "INVESTIGATE":
            continue
        o = opp.get(oid)
        if not o:
            continue
        sig = mv.signature(o)
        mech = mv.classify(sig, o)
        recs.append({"opportunity_id": oid, "cluster_id": o.get("cluster_id"), "detected_at": o["detected_at"],
                      "grid": o["_grid"], "opportunity_type": o["opportunity_type"], "signals": sig,
                      "mechanism_id": mech, "cluster_key": mv.cluster_key(sig, mech),
                      "market_state_signature": sig["market_state_signature"], "time_signature": sig["time_signature"],
                      "crossmarket_signature": sig["crossmarket_signature"], "is_continuation": bool(o.get("is_cluster_continuation")),
                      "review": h.get("hermes_review", {})})
    recs.sort(key=lambda r: r["detected_at"])
    return recs


def run_pipeline(recs: list[dict]) -> dict:
    events_sorted, events = mv.build_events(recs)
    by_mech: dict[str, list[dict]] = {}
    for e in events:
        by_mech.setdefault(e["mechanism_id"], []).append(e)
    codes_by_mech, dq_by_mech = {}, {}
    for m, evs in by_mech.items():
        codes, dq = {}, {}
        for e in evs:
            rep = e["opportunities"][0]
            for c in mv.counter_codes(rep, rep.get("review", {}), e):   # EVENT-level codes
                codes[c] = codes.get(c, 0) + 1
            for r in e["opportunities"]:
                q = r.get("review", {}).get("data_quality") or "PARTIAL"
                dq[q] = dq.get(q, 0) + 1
        codes_by_mech[m], dq_by_mech[m] = codes, dq
    ems, decs = {}, {}
    for m, evs in by_mech.items():
        em = mv.evidence_matrix(events, m, codes_by_mech[m], dq_by_mech[m])
        codes_by_mech[m] = em.get("counter_codes_used", codes_by_mech[m])   # decisions and the report share one code set
        ems[m] = em
        decs[m] = mv.decide(em, codes_by_mech[m])
    return {"events_sorted": events_sorted, "events": events, "by_mech": by_mech,
             "codes": codes_by_mech, "evidence": ems, "decisions": decs}


def main():
    os.makedirs(os.path.join(HERE, "ledger"), exist_ok=True)
    inp = load_inputs()
    reg_hash = mv.registry_hash()
    in_hashes_before = {k: sha_file(v) for k, v in inp["paths"].items()}

    invest = [oid for oid, h in inp["hermes"].items() if h.get("review_status") == "INVESTIGATE"]
    recs = prepare(inp["opportunities"], inp["hermes"])
    P = run_pipeline(recs)

    # ---- counter-evidence aggregation per mechanism ----
    counter_rows = {}
    for m, codes in P["codes"].items():
        sc, sname = mv.strongest(codes)
        counter_rows[m] = {"SUPPORTING_EVIDENCE": len([e for e in P["by_mech"][m]]),
                             "COUNTER_EVIDENCE": {k: codes[k] for k in sorted(codes)},
                             "ARTIFACT_EVIDENCE": {k: codes[k] for k in sorted(codes) if k in ("C01", "C02", "C03")},
                             "UNKNOWN": codes.get("C10", 0),
                             "counter_evidence_count": sum(codes.values()),
                             "strongest_counter_evidence": [sc, sname],
                             "proxy_dependency": ("HIGH" if ("C03" in codes) else "LOW")}

    # ---- decisions + candidate gate ----
    cands, dec_rows = [], {}
    for m, evs in P["by_mech"].items():
        em = P["evidence"][m]
        dec, rule, why = P["decisions"][m]
        sc, sname = mv.strongest(P["codes"][m])
        n = em["detail"]["events"]
        gate_ok = (dec == "MECHANISM_SUPPORTED" and n >= mv.REGISTRY["minimum_independent_events"]
                    and em["ARTIFACT_RISK"] != "HIGH" and sc != "C08")
        times = sorted(pd.Timestamp(e["event_start"]) for e in evs)
        row = {"mechanism_id": m, "mechanism_name": mv.TAXONOMY.get(m, "UNKNOWN"),
                "opportunity_count": sum(len(e["opportunities"]) for e in evs),
                "cluster_count": len({e["cluster_key"] for e in evs}), "independent_event_count": n,
                "cross_grid_event_count": len({e["cross_grid_event_id"] for e in evs}),
                "first_seen": str(times[0]), "last_seen": str(times[-1]),
                "evidence_matrix": em, "decision": dec, "decision_rule": rule, "decision_reason": why,
                "counter_evidence": counter_rows[m], "candidate_gate_passed": bool(gate_ok),
                "lifecycle": ("SUPPORTED" if dec == "MECHANISM_SUPPORTED" else
                               ("REJECTED" if dec == "MECHANISM_REJECTED" else "UNCERTAIN")),
                "causality_level": "CO_MOVEMENT",
                "semantic_dependencies": ({"SEMANTIC_DEPENDENCY": "UNKNOWN",
                                             "UST10Y": "PROXY (^TNX), never official"} if m in ("M03", "M04")
                                            else {"SEMANTIC_DEPENDENCY": "PARTIAL"})}
        dec_rows[m] = row
        if gate_ok:
            cands.append({"mechanism_id": m, "mechanism_definition": mv.TAXONOMY.get(m),
                            "trigger_definition": sorted({e["cluster_key"].split("|")[1] for e in evs}),
                            "boundary_conditions": {"sessions": em["detail"]["session_distribution"],
                                                     "states": em["detail"]["state_distribution"],
                                                     "time_stability": em["TIME_STABILITY"]},
                            "independent_event_count": n, "recurrence": em["RECURRENCE"],
                            "counter_evidence": counter_rows[m], "artifact_risk": em["ARTIFACT_RISK"],
                            "data_quality": em["DATA_QUALITY"],
                            "semantic_dependencies": row["semantic_dependencies"],
                            "next_stage": "INDEPENDENT_MECHANISM_VALIDATION",
                            "forbidden_next": ["FORWARD", "SHADOW", "LIVE", "ORDER"]})

    # ---- hermes research cache (§44/§45) ----
    cache = {}
    for m, evs in P["by_mech"].items():
        ordered = sorted(evs, key=lambda e: e["event_start"])
        first, rest = ordered[0], ordered[1:]
        cache[m] = {"mechanism_id": m, "first_event": {"event_id": first["independent_event_id"],
                                                          "review_type": "FULL_REVIEW",
                                                          "supported_by": len(first["opportunities"])},
                     "subsequent_events": [{"event_id": e["independent_event_id"],
                                              "review_type": ("INCREMENTAL_REVIEW" if e["opportunities"] else "NO_NEW_EVIDENCE"),
                                              "delta": ("NEW_EVIDENCE" if len(e["grids"]) > 1 else "NO_NEW_EVIDENCE"),
                                              "changes_mechanism_decision": False} for e in rest],
                     "total_events": len(evs)}

    # ---- negative control (§48) ----
    rnd = random.Random(20260925)
    shuffled = [dict(r) for r in recs]
    ts = [r["detected_at"] for r in shuffled]
    rnd.shuffle(ts)
    for r, t in zip(shuffled, ts):
        r["detected_at"] = t
    shuffled.sort(key=lambda r: r["detected_at"])
    PN = run_pipeline(shuffled)
    nc_dec = {}
    for m, d in PN["decisions"].items():
        nc_dec[d[0]] = nc_dec.get(d[0], 0) + 1
    real_dec = {}
    for m, r in dec_rows.items():
        real_dec[r["decision"]] = real_dec.get(r["decision"], 0) + 1
    nc = {"real": real_dec, "shuffled": nc_dec,
           "status": ("PASS" if nc_dec.get("MECHANISM_SUPPORTED", 0) <= max(1, real_dec.get("MECHANISM_SUPPORTED", 0))
                       else "FAIL"),
           "note": "shuffling timestamps must not manufacture MORE supported mechanisms than the real run"}
    # A failed negative control means the method cannot distinguish real structure from randomness.
    # Per the task rules the rules are NOT tuned to pass it: instead the method is declared invalid and its
    # decisions become provisional and unusable, and no candidate may be emitted.
    method_validity = "VALID" if nc["status"] == "PASS" else "INVALID_NEGATIVE_CONTROL_FAILED"
    nc["outputs_usable"] = (nc["status"] == "PASS")
    nc["structural_finding"] = ("time stability is computed from the placement of events across time thirds; a uniformly "
                                  "shuffled timestamp series satisfies it trivially, so the rule rewards randomness. "
                                  "A corrected method needs a randomness-resistant stability measure (e.g. a burstiness "
                                  "or permutation-based statistic) - not implemented here, because adjusting the rule "
                                  "after seeing this result is exactly what the task forbids.")
    for m, r in dec_rows.items():
        r["provisional"] = (nc["status"] != "PASS")
        r["usable"] = (nc["status"] == "PASS")
    if nc["status"] != "PASS":
        cands = []

    # ---- ablations (§49) ----
    def abl(drop):
        out = {}
        for m, em in P["evidence"].items():
            e2 = dict(em)
            if drop == "drop_time_stability":
                e2["TIME_STABILITY"] = "HIGH"
            if drop == "drop_session_stability":
                e2["SESSION_STABILITY"] = "HIGH"
            if drop == "drop_state_stability":
                e2["STATE_STABILITY"] = "HIGH"
            if drop == "drop_counter_evidence":
                e2["COUNTER_EVIDENCE"] = "LOW"
            if drop == "drop_recurrence":
                e2["RECURRENCE"] = "HIGH"
                e2["INDEPENDENT_EVENTS"] = "SUFFICIENT"
            d, _, _ = mv.decide(e2, P["codes"][m])
            out[d] = out.get(d, 0) + 1
        return out
    ablations = {k: abl(k) for k in ("drop_time_stability", "drop_session_stability", "drop_state_stability",
                                       "drop_counter_evidence", "drop_recurrence")}
    ablations["none"] = real_dec

    # ---- ledger + outputs ----
    lp = os.path.join(HERE, "ledger", "v3_mechanism_validation_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = mv.MechanismLedger(lp, reg_hash)
    for m in sorted(dec_rows):
        led.append({"kind": "MECHANISM_DECISION", **dec_rows[m]})
    for m, evs in sorted(P["by_mech"].items()):
        for e in evs:
            led.append({"kind": "INDEPENDENT_EVENT", "mechanism_id": m, "independent_event_id": e["independent_event_id"],
                         "cross_grid_event_id": e["cross_grid_event_id"], "event_start": e["event_start"],
                         "event_end": e["event_end"], "grids_involved": e["grids_involved"],
                         "opportunities_merged": e["opportunities_merged"],
                         "cluster_key": e["cluster_key"], "state_signature": sorted(e["states"]),
                         "crossmarket_signature": sorted(e["crossmarket"]),
                         "why_same_event": "same cluster key and inside the frozen separation window (6 bars on the "
                                            "record's own grid); cross-grid partners merged within 2h"})
    chain = mv.MechanismLedger.verify(lp)

    tot_events = sum(r["independent_event_count"] for r in dec_rows.values())
    merged_opp = sum(r["opportunity_count"] for r in dec_rows.values()) - tot_events
    crossgrid = sum(1 for m, evs in P["by_mech"].items() for e in evs if "cross_grid_merged_with" in e)
    out = {"schema": "v3_mechanism_validation/1", "ts_utc": NOW,
            "input_hermes_investigate": len(invest),
            "input_opportunities": len(inp["opportunities"]), "mechanism_count": len(dec_rows),
            "independent_event_count": tot_events,
            "decisions": real_dec, "candidate_research": len(cands),
            "opportunities_merged": merged_opp, "cross_grid_duplicates_merged": crossgrid,
            "artifact_risk_high": sum(1 for r in dec_rows.values() if r["evidence_matrix"]["ARTIFACT_RISK"] == "HIGH"),
            "counter_evidence_high": sum(1 for r in dec_rows.values()
                                          if r["evidence_matrix"]["COUNTER_EVIDENCE"] == "HIGH"),
            "mechanism_with_8plus_events": sum(1 for r in dec_rows.values()
                                                 if r["independent_event_count"] >= mv.REGISTRY["minimum_independent_events"]),
            "mechanism_with_time_stability": sum(1 for r in dec_rows.values()
                                                   if r["evidence_matrix"]["TIME_STABILITY"] in ("HIGH", "MEDIUM")),
            "mechanism_with_state_stability": sum(1 for r in dec_rows.values()
                                                    if r["evidence_matrix"]["STATE_STABILITY"] == "HIGH"),
            "negative_control": nc, "method_validity": method_validity, "ablations": ablations,
            "registry_hash": reg_hash, "version": mv.MV_VERSION}
    for f, obj in (("mechanism_clusters.json", {"schema": "v3_mechanism_clusters/1", "ts_utc": NOW,
                                                  "clusters": {m: sorted({e["cluster_key"] for e in evs})
                                                                for m, evs in P["by_mech"].items()}}),
                    ("mechanism_events.json", {"schema": "v3_mechanism_events/1", "ts_utc": NOW,
                                                 "events": [{"mechanism_id": e["mechanism_id"],
                                                              "independent_event_id": e["independent_event_id"],
                                                              "cross_grid_event_id": e["cross_grid_event_id"],
                                                              "event_start": e["event_start"], "event_end": e["event_end"],
                                                              "grids_involved": e["grids_involved"],
                                                              "opportunities_merged": e["opportunities_merged"],
                                                              "cluster_key": e["cluster_key"]}
                                                             for m, evs in P["by_mech"].items() for e in evs]}),
                    ("mechanism_evidence.json", {"schema": "v3_mechanism_evidence/1", "ts_utc": NOW,
                                                   "evidence": P["evidence"], "counter_evidence": counter_rows}),
                    ("mechanism_decisions.json", {"schema": "v3_mechanism_decisions/1", "ts_utc": NOW,
                                                    "decisions": dec_rows}),
                    ("mechanism_research_cache.json", {"schema": "v3_mechanism_research_cache/1", "ts_utc": NOW,
                                                         "cache": cache}),
                    ("candidate_research.json", {"schema": "v3_candidate_research/1", "ts_utc": NOW,
                                                   "entries": cands,
                                                   "note": "stage-2 input only (INDEPENDENT_MECHANISM_VALIDATION); "
                                                            "no entry/exit/size/order fields exist"})):
        json.dump(obj, open(os.path.join(HERE, f), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    json.dump(mv.REGISTRY, open(os.path.join(HERE, "mechanism_validation_registry.json"), "w", encoding="utf-8",
                                 newline="\n"), indent=1, ensure_ascii=False)
    in_hashes_after = {k: sha_file(v) for k, v in inp["paths"].items()}
    out_hash = hashlib.sha256(json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    audit = {"schema": "v3_mechanism_validation_audit/1", "ts_utc": NOW, "version": mv.MV_VERSION,
              "input_opportunity_hash": in_hashes_before["opportunity_1h"] + "+" + in_hashes_before["opportunity_5m"],
              "input_quality_hash": in_hashes_before["quality"], "input_hermes_hash": in_hashes_before["hermes"],
              "input_hashes_full_length": 64,
              "inputs_unchanged_after_run": in_hashes_before == in_hashes_after,
              "registry_hash": reg_hash, "mechanism_output_hash": out_hash, "ledger_hash": chain,
              "data_sources": ["R1 opportunity ledger (immutable)", "quality ledger (immutable)",
                                "hermes quality reviews (immutable)", "state parquet (read-only)"],
              "timestamp_policy": ("all features use bars <= detected_at; the post-event RESPONSE observation "
                                    "(3 bars) is descriptive and excluded from every decision"),
              "lookahead_status": "NO_LOOKAHEAD",
              "negative_control_status": nc["status"],
              "causality_policy": "same-bar external/XAU => CO_MOVEMENT only; TRANSMISSION is never asserted"}
    json.dump(audit, open(os.path.join(HERE, "mechanism_validation_audit.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump(out, open(os.path.join(HERE, "run_summary.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ("ablations",)}, ensure_ascii=False, default=str)[:1600])
    print("ablations:", json.dumps(ablations, ensure_ascii=False))
    print("immutable_ok:", audit["inputs_unchanged_after_run"], "| chain:", chain)
    for m, r in sorted(dec_rows.items()):
        print(f"  {m} {r['mechanism_name'][:28]:30s} opp={r['opportunity_count']:>5} ev={r['independent_event_count']:>4} "
               f"clu={r['cluster_count']:>3} artifact={r['evidence_matrix']['ARTIFACT_RISK']:4s} "
               f"ce={r['evidence_matrix']['COUNTER_EVIDENCE']:6s} -> {r['decision']}")


if __name__ == "__main__":
    main()
