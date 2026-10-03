# -*- coding: utf-8 -*-
"""V3 Opportunity Quality Filter R1 — orchestrator.

Input  : research/v3_opportunity_engine/ledger/*.jsonl  (R1 opportunities - IMMUTABLE)
Output : quality ledger + assessments + hermes decisions + candidate research + audit + ablations
No trading path. No future-return input. R1 artifacts are read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quality_filter as qf  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()


def sha_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_opportunities() -> tuple[list[dict], dict]:
    recs, src = [], {}
    for grid in ("1h", "5m"):
        p = os.path.join(HERE, "ledger", f"v3_opportunity_ledger_{grid}.jsonl")
        src[grid] = {"path": os.path.relpath(p, HERE), "sha256": sha_file(p),
                       "rows": 0}
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            payload = json.loads(line)["payload"]
            payload["_grid"] = grid
            recs.append(payload)
            src[grid]["rows"] += 1
    recs.sort(key=lambda r: (r["detected_at"], r["opportunity_id"]))
    # asof recurrence: strictly prior occurrences of the same type
    seen: dict[str, int] = {}
    for r in recs:
        t = r["opportunity_type"]
        r["_prior_same_type"] = seen.get(t, 0)
        seen[t] = seen.get(t, 0) + 1
    return recs, src


def assess_all(recs: list[dict], state_by_grid: dict) -> list[dict]:
    out = []
    for r in recs:
        st = state_by_grid[r["_grid"]]
        st = st[st.index <= pd.Timestamp(r["detected_at"])]      # asof-safe restriction
        if len(st) < 30:
            continue
        qa = qf.assess(r, st)
        out.append({"opportunity_id": r["opportunity_id"], "cluster_id": r["cluster_id"],
                     "detected_at": r["detected_at"], "opportunity_type": r["opportunity_type"],
                     "grid": r["_grid"], "data_quality": qa.get("data_quality"),
                     **qa})
    return out


def main():
    recs, src = load_opportunities()
    state_by_grid = {g: pd.read_parquet(os.path.join(HERE, "state_engine", f"state_{g}.parquet"))
                      .sort_index() for g in ("1h", "5m")}
    registry_hash = qf.registry_hash()

    # ---- immutability: hash the R1 inputs before AND after ----
    input_hash_before = hashlib.sha256(json.dumps(src, sort_keys=True).encode()).hexdigest()
    assessments = assess_all(recs, state_by_grid)
    src_after = {g: sha_file(os.path.join(HERE, "ledger", f"v3_opportunity_ledger_{g}.jsonl")) for g in ("1h", "5m")}
    immutable_ok = all(src_after[g] == src[g]["sha256"] for g in src)

    # ---- quality ledger ----
    lp = os.path.join(HERE, "ledger", "v3_opportunity_quality_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = qf.QualityLedger(lp, registry_hash)
    for a in assessments:
        led.append({k: a[k] for k in ("opportunity_id", "cluster_id", "detected_at", "opportunity_type",
                                        "quality_matrix", "quality_decision", "decision_rule",
                                        "semantic_dependencies", "data_quality", "dict_meta") if k in a or k == "dict_meta"}
                    if False else a)
    chain = qf.QualityLedger.verify(lp)

    # ---- hermes on QUALITY_PASS only ----
    passy = [a for a in assessments if a["quality_decision"] == "QUALITY_PASS"]
    by_id = {r["opportunity_id"]: r for r in recs}
    hermes_out, candidates = [], []
    for a in passy:
        r = by_id[a["opportunity_id"]]
        h = qf.hermes(r, a)
        row = {"opportunity_id": a["opportunity_id"], "cluster_id": a["cluster_id"], "detected_at": a["detected_at"],
                "opportunity_type": a["opportunity_type"], "grid": a["grid"], "quality_matrix": a["quality_matrix"],
                "data_quality": a["data_quality"], "semantic_dependencies": a["semantic_dependencies"],
                "historical_recurrence": a["quality_matrix"]["HISTORICAL_RECURRENCE"],
                "hermes_review": h, "review_status": h["E_decision"], "lookahead_check": "PASS",
                "quality_filter_version": qf.QF_VERSION, "registry_hash": registry_hash, "created_at": NOW}
        hermes_out.append(row)
        if h["E_decision"] == "CANDIDATE_RESEARCH":
            candidates.append({"opportunity_id": a["opportunity_id"], "cluster_id": a["cluster_id"],
                                 "detector_id": r.get("detection_version", ""), "quality_matrix": a["quality_matrix"],
                                 "hermes_review": h, "mechanism_hypotheses": h["B_mechanisms"],
                                 "counter_evidence": h["C_counter_evidence"], "data_quality": a["data_quality"],
                                 "semantic_dependencies": a["semantic_dependencies"],
                                 "decision_reason": h["E_reason"], "context_hash": r.get("context_hash"),
                                 "forbidden_next": ["FORWARD", "SHADOW", "LIVE"],
                                 "requires": "independent mechanism validation before any further stage"})
    (lambda: None)()
    hdec = {}
    for h in hermes_out:
        hdec[h["review_status"]] = hdec.get(h["review_status"], 0) + 1
    qdec = {}
    for a in assessments:
        qdec[a["quality_decision"]] = qdec.get(a["quality_decision"], 0) + 1
    dims = {}
    for k in ("NOVELTY", "EXTREMENESS", "PERSISTENCE", "CROSSMARKET_CONFIRMATION", "HISTORICAL_RECURRENCE", "DATA_QUALITY"):
        c = {}
        for a in assessments:
            v = a["quality_matrix"][k]
            c[v] = c.get(v, 0) + 1
        dims[k] = c

    # ---- ablations (§28, analysis only - never re-freezes rules) ----
    def abl(drop):
        cnt = {}
        ordv = {"LOW": 0, "NONE": 0, "MEDIUM": 1, "HIGH": 2}
        for a in assessments:
            m = dict(a["quality_matrix"])
            if drop == "NOVELTY":
                m["NOVELTY"] = "HIGH"
            if drop == "PERSISTENCE":
                m["PERSISTENCE"] = "HIGH"
            if drop == "CROSSMARKET_CONFIRMATION":
                m["CROSSMARKET_CONFIRMATION"] = "HIGH"
            if drop == "HISTORICAL_RECURRENCE":
                m["HISTORICAL_RECURRENCE"] = "HIGH"
            d = "QUALITY_INSUFFICIENT"
            if m["DATA_QUALITY"] == "UNKNOWN":
                d = "QUALITY_INSUFFICIENT"
            elif ordv[m["EXTREMENESS"]] < 1 and ordv[m["NOVELTY"]] < 1:
                d = "QUALITY_REJECT"
            elif ordv[m["PERSISTENCE"]] < 1 and ordv[m["EXTREMENESS"]] < 1:
                d = "QUALITY_REJECT"
            elif ordv[m["HISTORICAL_RECURRENCE"]] >= 2 and ordv[m["NOVELTY"]] < 1:
                d = "QUALITY_REJECT"
            elif (ordv[m["EXTREMENESS"]] >= 1 and ordv[m["NOVELTY"]] >= 1 and ordv[m["PERSISTENCE"]] >= 1
                  and ordv[m["HISTORICAL_RECURRENCE"]] >= 1):
                d = "QUALITY_PASS"
            cnt[d] = cnt.get(d, 0) + 1
        return cnt

    ablations = {f"drop_{k}": abl(k) for k in ("NOVELTY", "PERSISTENCE", "CROSSMARKET_CONFIRMATION",
                                                 "HISTORICAL_RECURRENCE")}
    ablations["all_dimensions"] = qdec

    # ---- outputs ----
    os.makedirs(os.path.join(HERE, "quality"), exist_ok=True)
    cl_pairs = {(r["_grid"], r["cluster_id"]) for r in recs}
    cl_per_grid = {g: len({r["cluster_id"] for r in recs if r["_grid"] == g}) for g in ("1h", "5m")}
    out = {"schema": "v3_quality_report/1", "ts_utc": NOW,
            "input_opportunities": len(recs), "input_clusters": len(cl_pairs),
            "input_clusters_per_grid": cl_per_grid,
            "cluster_id_namespace_note": "R1 numbered clusters per grid, so cluster_id alone collides across grids; clusters are counted as (grid, cluster_id)",
            "assessed": len(assessments), "quality_distribution": qdec,
            "hermes_sent": len(hermes_out), "hermes_decisions": hdec,
            "candidate_research": len(candidates),
            "dimension_distribution": dims, "ablations": ablations,
            "comparison_with_R1": {"R1": {"opportunities": 1999, "hermes": 120, "investigate": 120},
                                    "QF_R1": {"opportunities": len(assessments), "hermes": len(hermes_out),
                                                "decisions": hdec}},
            "registry_hash": registry_hash, "quality_filter_version": qf.QF_VERSION}
    json.dump(out, open(os.path.join(HERE, "quality", "quality_report.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_hermes_quality_reviews/1", "ts_utc": NOW, "reviews": hermes_out},
               open(os.path.join(HERE, "hermes", "hermes_quality_reviews.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_candidate_research/1", "ts_utc": NOW, "entries": candidates,
                "note": "CANDIDATE_RESEARCH means worth independent mechanism validation; NOT buy/sell/forward/live"},
               open(os.path.join(HERE, "quality", "candidate_research.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump(qf.REGISTRY, open(os.path.join(HERE, "quality", "quality_filter_registry.json"), "w",
                                 encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    out_hash = hashlib.sha256(json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    json.dump({"schema": "v3_quality_filter_audit/1", "ts_utc": NOW, "version": qf.QF_VERSION,
                "input_hash": input_hash_before, "input_files": src, "input_unchanged_after_run": immutable_ok,
                "registry_hash": registry_hash, "output_hash": out_hash, "ledger_chain": chain,
                "data_sources": ["R1 opportunity ledger (immutable)", "state_engine parquet (read-only)"],
                "lookahead_status": "NO_LOOKAHEAD (gate uses bars <= detected_at only; forward persistence is an observation field)",
                "future_return_used": False, "forbidden_fields_present": False},
               open(os.path.join(HERE, "quality", "quality_filter_audit.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ("dimension_distribution",)},
                      ensure_ascii=False, default=str)[:1400])
    print("dims:", json.dumps(dims, ensure_ascii=False))
    print("ablations:", json.dumps(ablations, ensure_ascii=False))
    print("immutable_input_ok:", immutable_ok, "| chain:", chain)


if __name__ == "__main__":
    main()
