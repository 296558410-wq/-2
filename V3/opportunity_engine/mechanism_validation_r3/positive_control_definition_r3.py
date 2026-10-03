# -*- coding: utf-8 -*-
"""MV-R3 — Positive Control definition (pre-registered) + synthetic dataset builder.

Design rationale (derived from the R2 failure, not from tuning):
  * R2's control used a rigid 6h cadence -> equal to the frozen event separation window -> the gap test is
    "> 6h", so every planted event merged into ONE event -> identical signatures -> DATA_ARTIFACT -> FATAL.
  * R2's decision rule also requires TIME_STABILITY == HIGH, i.e. event times must be MORE clustered than a
    random null. A regular or merely spread-out schedule cannot satisfy that.
  => A FAIR control must express the pre-registered structural definition of a mechanism: episodes of
     trigger -> transition -> persistence -> decay, recurring in bursts, separated by long silences.
     Every gap stays strictly greater than the separation window so nothing merges.

Nothing here uses returns, PnL or any future quantity. The synthetic dataset is fully separate from real data
and never touches the real ledgers.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.join(os.path.dirname(HERE), "mechanism_validation_r2")
import sys
sys.path.insert(0, R2)
import mechanism_validation_r2 as mv2  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat()

# ---- frozen schedule: 4 episodes x 4 events, intra-episode gaps in 7..11h (all > 6h), inter-episode 240..300h
INTRA = [7, 9, 8, 11]                 # hours between events INSIDE an episode
INTER = [240, 300, 264]               # hours of silence BETWEEN episodes (3 gaps for 4 episodes)
PERSISTENCE_BOUNDS = [2, 5]           # bars
INTENSITY_BOUNDS = [1.00, 1.60]       # normalised, pre-registered, not fitted
DURATION_BOUNDS = [3, 6]              # bars
EPISODES = 4
PER_EPISODE = 4

DEFINITION = {
    "control_id": "PC_R3_SYNTHETIC_STATE_TRANSITION",
    "mechanism_type": "SYNTHETIC_STATE_TRANSITION",
    "expected_mechanism": "M01",
    "expected_decision": "MECHANISM_SUPPORTED",
    "structure": ["BASE_STATE", "TRIGGER", "TRANSITION", "PERSISTENCE", "DECAY", "RETURN_TO_BASE_STATE"],
    "synthetic_event_count": EPISODES * PER_EPISODE,
    "episodes": EPISODES, "events_per_episode": PER_EPISODE,
    "event_separation": {"intra_episode_gaps_hours": INTRA, "inter_episode_gaps_hours": INTER,
                          "separation_window_hours": 6,
                          "guarantee": "every gap is strictly greater than the frozen 6h separation window"},
    "variation_bounds": {"persistence_bars": PERSISTENCE_BOUNDS, "intensity": INTENSITY_BOUNDS,
                           "duration_bars": DURATION_BOUNDS,
                           "note": "per-event variation inside frozen bounds so that signatures are NOT identical, "
                                    "which is what tripped R2's degeneracy rule"},
    "trigger_definition": "trigger signature held constant at PRICE_EXTREME (the planted trigger)",
    "transition_definition": "one transition per event from BASE to the planted abnormal state",
    "persistence_definition": f"persistence drawn from {PERSISTENCE_BOUNDS} bars, deterministic per event",
    "decay_definition": "decay returns to BASE within the frozen duration bounds",
    "random_seed": mv2.REGISTRY["random_seed"],
    "grid": "1h",
    "pre_registered": True,
    "single_shot": True,
    "no_adaptation": True,
    "no_returns": True,
    "no_lookahead": True,
    "isolation": {"separate_dataset": True, "never_enters_real_ledgers": True,
                   "real_data_hash_unchanged_required": True},
    "acceptance": {"expected_decision": "MECHANISM_SUPPORTED", "fatal_artifact_allowed": False,
                    "min_independent_events": mv2.REGISTRY["minimum_independent_events"],
                    "independent_event_tolerance": {"abs": 2,
                                                     "reason": "a boundary event may fall outside the synthetic span"},
                    "no_duplicate": True, "no_cross_grid_double_count": True},
}


def definition_hash() -> str:
    return hashlib.sha256(json.dumps(DEFINITION, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def build_control_records() -> tuple[list[dict], list[dict]]:
    """Deterministic synthetic events. Returns (records, event_manifest)."""
    base = pd.Timestamp("2025-01-05T00:00:00+00:00")          # Sunday, avoids the real dataset's UTC span edges
    t = base
    recs, manifest = [], []
    n = 0
    for ep in range(EPISODES):
        if ep:
            t = t + pd.Timedelta(hours=INTER[ep - 1])
        for k in range(PER_EPISODE):
            if k:
                t = t + pd.Timedelta(hours=INTRA[k - 1])
            n += 1
            eid = "PCE-" + hashlib.sha1(f"{DEFINITION['control_id']}|{n}".encode()).hexdigest()[:8]
            persistence = PERSISTENCE_BOUNDS[0] + (n % (PERSISTENCE_BOUNDS[1] - PERSISTENCE_BOUNDS[0] + 1))
            duration = DURATION_BOUNDS[0] + (n % (DURATION_BOUNDS[1] - DURATION_BOUNDS[0] + 1))
            intensity = round(INTENSITY_BOUNDS[0] + (n % 7) * 0.1, 2)
            sig = {"trigger_signature": "PRICE_EXTREME",
                    "transmission_signature": "DIRECT",
                    "response_signature": f"PERSIST_{persistence}",
                    "time_signature": "London",                      # constant -> same cluster
                    "market_state_signature": "VOL_NORMAL",          # constant -> M01, not M08
                    "crossmarket_signature": "NONE",                 # no proxy -> no proxy artifact
                    "artifact_signature": f"SYNTH_D{duration}_I{intensity}"}
            key = mv2.mv.cluster_key(sig, "M01")
            rec = {"opportunity_id": eid, "cluster_id": "PC_R3", "detected_at": t.isoformat(), "grid": "1h",
                    "opportunity_type": "OPP_STATE_BREAK", "signals": sig, "mechanism_id": "M01",
                    "cluster_key": key, "market_state_signature": "VOL_NORMAL", "time_signature": "London",
                    "crossmarket_signature": "NONE", "is_continuation": False,
                    "review": {"data_quality": "VERIFIED", "synthetic": True}}
            recs.append(rec)
            manifest.append({"event_id": eid, "event_start": t.isoformat(),
                              "event_end": (t + pd.Timedelta(hours=duration)).isoformat(),
                              "trigger": "PRICE_EXTREME", "transition": "BASE->VOL_NORMAL_ABNORMAL",
                              "persistence_bars": persistence, "decay_bars": duration, "intensity": intensity})
    recs.sort(key=lambda r: r["detected_at"])
    return recs, manifest


def dataset_hash(recs: list[dict]) -> str:
    return hashlib.sha256(json.dumps(recs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


if __name__ == "__main__":
    r, m = build_control_records()
    print(json.dumps({"definition_hash": definition_hash(), "records": len(r), "events": len(m),
                       "dataset_hash": dataset_hash(r), "first": r[0]["detected_at"], "last": r[-1]["detected_at"]},
                      ensure_ascii=False))
    gaps = [round((pd.Timestamp(r[i + 1]["detected_at"]) - pd.Timestamp(r[i]["detected_at"])).total_seconds() / 3600, 2)
            for i in range(len(r) - 1)]
    print("gaps_hours:", gaps)
    print("all_gaps_gt_6h:", all(g > 6 for g in gaps), "| min_gap:", min(gaps))
