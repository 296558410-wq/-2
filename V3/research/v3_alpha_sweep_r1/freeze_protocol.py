# -*- coding: utf-8 -*-
"""Freeze the V3 Alpha Sweep R1 protocol (registry of every hypothesis) BEFORE any evaluation."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(HERE, exist_ok=True)

H = []
def add(hid, fam, corpus, kind, feature, trigger, direction, horizons, note=""):
    H.append({"id": hid, "family": fam, "corpus": corpus, "kind": kind, "feature": feature,
              "trigger": trigger, "direction": direction, "horizons": horizons, "note": note})

TICK_H = [100, 250, 500, 1000, 2000, 5000]      # ms
BAR_H = [1, 5, 15, 30, 60]                       # minutes
EV_H = [1, 5, 15]                                # minutes

# ---- F1 tick / microstructure (corpus = TICK) ----
add("T1_TICK_IMBALANCE", "F1_tick_microstructure", "TICK", "directional",
    "TI = sum(sign(dmid), 100 ticks)/sqrt(100)", "|TI|>=2 onset", "follow", TICK_H,
    "quote-based _PROXY (volume identically 0)")
add("T2_PRESSURE_PERSIST", "F1_tick_microstructure", "TICK", "directional",
    "sign agreement ratio of dmid over 200 ticks", ">=0.85 same-sign, onset", "follow", TICK_H)
add("T3_LIQUIDITY_SHOCK", "F1_tick_microstructure", "TICK", "directional",
    "z(ret over 500 ticks) vs trailing 3000-tick std", "|z|>=2 onset", "fade", TICK_H,
    "liquidity shock / replenishment")
add("T4_SPREAD_STRESS", "F1_tick_microstructure", "TICK", "directional",
    "spread >= 1.5x trailing 3000-tick median AND |z(ret100)|>=1", "joint onset", "follow", TICK_H,
    "spread x pressure interaction")
add("T5_MICRO_REVERSAL", "F1_tick_microstructure", "TICK", "directional",
    "z(ret over 100 ticks)", "|z|>=2 onset", "fade", TICK_H)

# ---- F2 short-horizon price structure (corpus = BAR) ----
add("P1_IMPULSE", "F2_price_structure", "BAR", "directional",
    "z5 = ret5/(sigma20*sqrt5)", "|z5|>=2", "follow", BAR_H)
add("P2_ABNORMAL_REVERSAL", "F2_price_structure", "BAR", "directional",
    "z1 = ret1/sigma20", "|z1|>=3", "fade", BAR_H)
add("P3_VOL_EXPANSION_DIR", "F2_price_structure", "BAR", "directional",
    "rv5 crossing above trailing q67", "high-vol regime onset", "follow sign(ret1)", BAR_H)
add("P4_BREAKOUT", "F2_price_structure", "BAR", "directional",
    "close > max(close of prior 20 bars)", "20-bar Donchian breakout", "follow", BAR_H)
add("P5_FAILED_BREAKOUT", "F2_price_structure", "BAR", "directional",
    "made a 20-bar high then closed back below the prior 20-bar high", "failed breakout", "fade", BAR_H)
add("P6_RANGE_COMPRESSION", "F2_price_structure", "BAR", "non_directional",
    "rv5 in the trailing bottom quintile", "compression onset", "n/a", BAR_H,
    "forward |move| vs baseline (range expansion after compression)")

# ---- F3 cross-scale structure (corpus = BAR) ----
add("X1_SCALE_AGREEMENT", "F3_cross_scale", "BAR", "directional",
    "sign(ret5) == sign(60-bar change), z5 trigger", "|z5|>=2 AND agreement", "follow", BAR_H)
add("X2_SCALE_DISAGREEMENT", "F3_cross_scale", "BAR", "directional",
    "sign(ret5) != sign(60-bar change), z5 trigger", "|z5|>=2 AND disagreement", "follow", BAR_H)
add("X3_HTF_REGIME_COND", "F3_cross_scale", "BAR", "directional",
    "1m impulse z5 inside an up-trending 60m regime", "|z5|>=2 AND 60m trend up", "follow", BAR_H,
    "short signal x higher-timeframe regime")

# ---- F4 market-state conditioning (corpus = BAR) ----
for sid, dim in (("S1_VOL_TERCILE", "volatility tercile"), ("S2_SPREAD_TERCILE", "spread tercile"),
                 ("S3_ACTIVITY_TERCILE", "tick-count-per-bar tercile"), ("S4_SESSION", "session"),
                 ("S5_TREND_RANGE", "trend/range state (efficiency ratio)")):
    add(sid, "F4_state_conditioning", "BAR", "directional",
        "follow sign(ret5) with |z5|>=2, evaluated inside each %s bucket" % dim,
        "|z5|>=2 AND bucket", "follow", BAR_H, "bucket must also be reported separately")

# ---- F5 event x microstructure (corpus = EVENT, PIT2 snapshot + frozen calendar vintages) ----
add("E1_EVENT_X_MICRO", "F5_event_interaction", "EVENT", "directional",
    "event proximity (<=5 min after a PIT calendar event) AND tick imbalance |TI|>=2", "joint", "follow", EV_H)
add("E2_EVENT_X_VOL", "F5_event_interaction", "EVENT", "directional",
    "pre-event 60s return, taken at the event", "event", "follow", EV_H,
    "event x volatility response")
add("E3_EVENT_X_SPREAD", "F5_event_interaction", "EVENT", "directional",
    "event AND spread at the event >= 1.2x trailing median", "joint", "fade", EV_H)
add("E4_POST_EVENT_CONT", "F5_event_interaction", "EVENT", "directional",
    "first 1m move after the event", "event + first 1m close", "follow", EV_H)
add("E5_POST_EVENT_FADE", "F5_event_interaction", "EVENT", "directional",
    "first 1m move after the event", "event + first 1m close", "fade", EV_H)

P = {
 "schema": "v3_alpha_sweep_r1_protocol/1", "task_id": "V3-ALPHA-SWEEP-R1",
 "ts_utc": "2026-10-02T07:30:00+08:00", "frozen_before_evaluation": True,
 "objective": "mechanism-level, broad-coverage, strictly frozen XAUUSD high-frequency alpha sweep. Not parameter tuning.",
 "bounds": {
   "order_send": "NO", "live": "NO", "execution": "NO", "demo_shadow_live": "NO",
   "v1_v2_read_as_input": "NO", "v1_v2_modified": "NO", "historical_profit_used": "NO",
   "lookahead": "NO", "future_function": "NO",
   "retune_after_results": "NO", "delete_unfavourable_samples": "NO",
   "subsamples_for_selection": "NO (robustness audit only)",
   "closed_f2b_repackaged": "NO", "closed_dr1_er1_fr1_failures_used_as_sample_or_label": "NO",
   "global_fdr": "BH across the whole sweep at alpha=0.05"
 },
 "data": {
   "TICK": {"snapshot": "V3-SNAP-20260922T025312Z", "files": 36, "ticks": 7285000,
            "span_utc": ["2026-08-04T01:05:00.093Z", "2026-09-22T02:39:05.572Z"],
            "sha256_verify": "36/36 MATCH",
            "manifest_sha256": "13fb5d1720a3b25768d0bca59eda897e85e66ba6d7741d538fc32ed33ef8eb54",
            "timestamp_field": "ts_utc", "unit": "ms", "tz": "UTC",
            "volume": "DATA_GAP (identically 0) => every flow feature is a quote-based _PROXY"},
   "BAR": {"derived_from": "TICK snapshot, 1m bars per segment", "bars": "MEASURED_AT_RUN"},
   "EVENT": {"snapshot": "V3-SNAP-PIT2-20261001T131500Z", "ticks": 1712560,
             "span_utc": ["2026-09-21T01:08:06.326Z", "2026-10-01T12:54:06.646Z"],
             "calendar_vintages": ["JIN10_CALENDAR_20261001T130733Z.json (283 events, captured 2026-10-01T13:07:33Z)",
                                   "V3_JIN10_EVENT_PIT.json (158 events, captured 2026-09-25T09:05:59Z)"],
             "pit_rule": "availability = the event's own pub_time (Asia/Shanghai - 8h); nothing later may be used at T"}
 },
 "cost_model": {"COST_MODEL_VERSION": "CALIBRATION_20RT_20260921", "REAL_RT_COST_BP": 0.914,
                "stress": [0.0, 1.0, 2.0, 3.0], "rule": "0.314bp is HISTORICAL_INVALID and must not be used"},
 "frozen_thresholds": {
   "abs_z_2": 2.0, "abs_z_1": 1.0, "abs_z_3": 3.0,
   "ti_window_ticks": 100, "pressure_window_ticks": 200, "pressure_ratio": 0.85,
   "shock_window_ticks": 500, "sd_window_ticks": 3000, "micro_window_ticks": 100,
   "spread_ratio_1p5": 1.5, "spread_ratio_1p2": 1.2,
   "sigma_window_bars": 20, "impulse_window_bars": 5, "donchian_bars": 20, "h2_bars": 60,
   "segment_gap_ms": 60000, "min_effective_n": 30, "alpha": 0.05,
   "quantiles": {"tercile": [0.33, 0.67], "quintile_low": 0.20}
 },
 "execution_model": {
   "entry": "first tick with ts > the signal tick/bar-close; long at ask, short at bid",
   "exit": "mid at the first tick with ts >= entry_ts + h",
   "censoring": "HORIZON_CENSORED when the forward window leaves the segment (tick gap > 60s) or the sample ends",
   "mid_markout": "dir*(future_mid - entry_mid)", "cost_adjusted": "mid_markout_bp - 0.914 * stress_mult"
 },
 "hypotheses": H,
 "hypothesis_count": len(H),
 "mirror_rule": "every directional hypothesis is reported BOTH ways; the mirror is NOT independent evidence",
 "validation": {
   "is_oos": "time-ordered 70/30 by event time, no shuffle",
   "permutation": "sign-flip n=2000 two-sided; PRE-REGISTERED adaptive rule for very large event counts: reps = min(2000, max(500, floor(2e7 / n))). The point estimate, CI, effective_n and the ladder use the FULL sample; only the permutation repetition count adapts.",
   "bootstrap": "block bootstrap over events n=2000, 50 blocks",
   "overlap": "raw n, overlap ratio, effective_n = greedy non-overlapping count, floor 30",
   "cost_ladder": [0.0, 1.0, 2.0, 3.0],
   "robustness": ["session", "volatility tercile", "spread tercile", "activity tercile", "trend/range state"],
   "multiple_testing": "BH-FDR at 0.05 over the WHOLE sweep",
   "taxonomy": ["VALIDATED_EDGE", "EDGE_UNCERTAIN", "COST_INSUFFICIENT", "DATA_BLOCKED", "INVALID_IMPLEMENTATION"],
   "VALIDATED_EDGE_requires": "preflight valid + cost-adjusted positive on IS AND OOS at 1x + permutation p<0.05 + bootstrap CI excluding 0 + effective_n>=30 + not reliant on a single bucket + survives 2x cost + survives global BH-FDR. The standard is NOT lowered for a small count.",
   "ladder": ["INSUFFICIENT_SAMPLE", "COST_INSUFFICIENT", "REJECT", "EDGE_UNCERTAIN", "EXECUTION_UNREALISTIC", "CANDIDATE"]
 },
 "preflight": {
   "mandatory": True,
   "P1_synthetic_scale": "for every standardised feature used (TI, z500, z100, z5, z1, zma), on 200k iid Gaussian ticks/bars the empirical std must land in [0.85, 1.15]",
   "P2_synthetic_rate": "the synthetic trigger rate must be within a factor 3 of the Gaussian-implied rate for the same cut",
   "P3_failure_action": "a feature failing P1/P2 => every hypothesis using it is INVALID_IMPLEMENTATION and no return is computed for it"
 }
}
body = json.dumps(P, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
P["registry_hash_sha256"] = hashlib.sha256(body).hexdigest()
json.dump(P, open(os.path.join(HERE, "ALPHA_SWEEP_R1_FROZEN_PROTOCOL.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote ALPHA_SWEEP_R1_FROZEN_PROTOCOL.json")
print("registry_hash_sha256 =", P["registry_hash_sha256"])
print("hypotheses =", len(H))
for hid in (h["id"] for h in H):
    print("  ", hid)
