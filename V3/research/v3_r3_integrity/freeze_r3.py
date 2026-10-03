# -*- coding: utf-8 -*-
"""Freeze the V3 R3 protocol BEFORE any computation."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(HERE, exist_ok=True)

P = {
 "schema": "v3_r3_integrity_protocol/1",
 "task_id": "V3-R3-INTEGRITY",
 "ts_utc": "2026-10-02T10:20:00+08:00",
 "frozen_before_computation": True,
 "objective": "repair three confirmed V3 problems: (1) insufficient temporal coverage/stability, (2) the event-loader concurrent-event dedup defect, (3) X3 being long-only and inseparable from beta. NO new Alpha Sweep hypothesis is added this round.",
 "bounds": {
   "order_send": "NO", "live": "NO", "execution": "NO",
   "v1_v2_touched": "NO", "v1_v2_results_read": "NO",
   "r1_r2_results_modified": "NO", "cost_anchor_modified": "NO",
   "tuning_for_return": "NO", "future_data": "NO",
   "delete_unfavourable_period": "NO", "mirror_as_independent_evidence": "NO",
   "new_alpha_sweep_hypothesis": "NO",
   "output_dir": "research/hermes/trader_v3/research/v3_r3_integrity"
 },
 "data": {
   "TICK_MAIN": {"snapshot": "V3-SNAP-20260922T025312Z", "ticks": 7285000, "files": 36,
                 "sha256_verify": "36/36 MATCH",
                 "manifest_sha256": "13fb5d1720a3b25768d0bca59eda897e85e66ba6d7741d538fc32ed33ef8eb54"},
   "TICK_PIT2": {"snapshot": "V3-SNAP-PIT2-20261001T131500Z", "ticks": 1712560, "files": 9},
   "UNION": {"definition": "union(MAIN, PIT2) deduplicated on the exact (ts_utc,bid,ask) triple, sorted, re-segmented",
             "purpose": "the widest PIT-consistent temporal sample available",
             "note": "R2 noted the union changed the segment topology (53 vs 1055); this round records the topology explicitly and reports it rather than hiding it"},
   "calendar_vintage": "JIN10_CALENDAR_20261001T130733Z.json (283 rows) + any prior vintage found under the V3 research tree",
   "volume": "volume/volume_real/last are 0 on 100% of ticks in both snapshots => quote-based proxies only (TRUE_OFI_DATA_UNAVAILABLE)"
 },
 "cost_model": {"COST_MODEL_VERSION": "CALIBRATION_20RT_20260921", "REAL_RT_COST_BP": 0.914,
                "stress": [0.0, 1.0, 2.0, 3.0], "rule": "UNCHANGED; 0.314bp remains invalid"},

 "W1_temporal_audit": {
   "must_report": ["earliest/latest data ts", "calendar span days", "active trading days (distinct days with ticks)",
                   "ticks per week and per month", "per-block gross/net/effective_n for the reviewed candidate",
                   "time-ordered rolling stability", "IS and OOS actual date coverage", "market-phase coverage"],
   "blocks": {"monthly": "calendar month (UTC)", "weekly": "ISO week", "rolling": "20 trading-day window stepped by 5 days"},
   "no_deletion": "no period may be dropped for performing badly; all blocks are reported",
   "reported_candidate": "P3_VOL_EXPANSION_DIR at its frozen 60m horizon (definition inherited from R1/R2; no threshold change)"
 },
 "W1_temporal_gate": {
   "name": "TEMPORAL_GATE",
   "applies_to": "every future candidate before VALIDATED_EDGE",
   "G1_coverage": "evaluation sample must span >= 3 calendar months AND >= 40 distinct active trading days",
   "G2_monthly_consistency": "in months with >= 50 events, the sign of the monthly mean must match the overall sign in >= 2/3 of those months",
   "G3_rolling_stability": "the 20-trading-day rolling net(1x) edge must be positive in >= 60% of windows",
   "G4_is_oos": "both IS and OOS must be cost-positive at 1x (already required by the ladder)",
   "fail_G1": "TEMPORAL_EVIDENCE_INSUFFICIENT - a hard block on VALIDATED_EDGE",
   "fail_G2_or_G3": "TIME_INSTABILITY - a hard block on VALIDATED_EDGE",
   "high_effective_n_does_not_substitute": "a large effective_n may never mask a short span"
 },

 "W2_event_loader": {
   "defect_repaired": "R1's loader deduplicated on (ts, filename), collapsing simultaneous but DISTINCT events: 283 rows -> 75 distinct timestamps",
   "unique_key": "(pub_time_utc, event_name, country, source_file, vintage)",
   "rules": [
     "two rows with the SAME unique key are TRUE DUPLICATES and are collapsed to one",
     "two rows with the same pub_time but a DIFFERENT event_name/country are CONCURRENT DISTINCT EVENTS and are KEPT",
     "no synthetic events may be created; no window may be widened"
   ],
   "must_report": ["raw rows", "true duplicates", "concurrent distinct events", "PIT-qualified",
                   "inside the tick window", "with complete pre/post windows", "final researchable",
                   "the loss reason at every step"],
   "must_emit": "a new event registry with a SHA256"
 },

 "W3_event_tick_rebuild": {
   "scope": "data integrity and sample reconstruction ONLY",
   "forbidden": "inheriting any R1 F5 return conclusion",
   "note": "if F5 research is to be redone it needs its own new frozen protocol (not this round)"
 },

 "W4_x3_market_neutral": {
   "forbidden": ["changing the X3 threshold to chase a result", "selecting a favourable period",
                 "deleting losing samples", "back-adjusting the new definition using R2 results"],
   "design": {
     "X3MN_TWO_SIDED": "trigger |z5| >= 2.0 (unchanged, 20-bar sigma, 5-bar impulse); regime = 60-bar change sign (unchanged window); if regime > 0 take LONG, if regime < 0 take SHORT; if regime == 0 no trade",
     "direction_rule": "the SIDE is chosen by the regime, so the signal is two-sided by construction rather than always long",
     "MATCHED_EXPOSURE_BASELINE": "for each signal entry (time t, direction d) a control entry is drawn at the SAME minute-of-day on a different active day, taking the SAME direction d, using a fixed RNG seed; alpha_MEB = mean(signal_ret) - mean(control_ret)",
     "BETA_CHECK": "report mean return separately for the LONG and SHORT legs; if the SHORT leg is also positive in its own direction the effect cannot be pure market drift",
     "MARKET_NEUTRAL_PNL": "combined = (n_L*mean_L + n_S*mean_S) / (n_L+n_S)"
   },
   "must_report": ["n_L, n_S", "LONG/SHORT leg means", "combined gross/net at 0x/1x/2x/3x", "volatility",
                   "max drawdown", "IS/OOS", "effective_n", "block bootstrap CI", "permutation p",
                   "alpha_MEB", "beta/exposure summary", "temporal blocks and the TEMPORAL_GATE"],
   "blocked_rule": "if the SHORT leg has fewer than 30 effective observations, or the design cannot be built without changing a threshold, the verdict is X3_REDESIGN_BLOCKED and no performance claim is made"
 },

 "verdicts": ["VALIDATED_EDGE", "EDGE_UNCERTAIN", "COST_INSUFFICIENT",
              "TEMPORAL_EVIDENCE_INSUFFICIENT", "TIME_INSTABILITY",
              "X3_REDESIGN_BLOCKED", "DATA_BLOCKED"]
}
body = json.dumps(P, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
P["registry_hash_sha256"] = hashlib.sha256(body).hexdigest()
json.dump(P, open(os.path.join(HERE, "V3_R3_FROZEN_PROTOCOL.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote V3_R3_FROZEN_PROTOCOL.json")
print("registry_hash_sha256 =", P["registry_hash_sha256"])
