# -*- coding: utf-8 -*-
"""Freeze the V3 D-R1 (event microstructure) protocol. Runs BEFORE any evaluation."""
import json, hashlib, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(HERE, exist_ok=True)

P = {
 "schema": "v3_d_r1_protocol/1",
 "task_id": "V3-PHASE2-D-R1",
 "round": "D-R1",
 "ts_utc": "2026-10-01T15:05:00+00:00",
 "frozen_before_evaluation": True,
 "bounds": {"order_send": "NO", "execution_mode": "RESEARCH_READONLY", "forward": "NO", "live": "NO", "v1_v2": "UNTOUCHED"},
 "inputs": {
   "snapshot": "V3-SNAP-PIT2-20261001T131500Z",
   "snapshot_rows": 1712560,
   "snapshot_span_utc": ["2026-09-21T01:08:06Z", "2026-10-01T12:54:06Z"],
   "calendar_vintages": [
     {"file": "V3_JIN10_EVENT_PIT.json", "captured_at_utc": "2026-09-25T09:05:59Z", "events": 158, "window_original": ["2026-09-21", "2026-09-26"], "importance_field": "present(1-4)", "raw_hash": "0c9c6ceabdec281dd1fcc887fac7636bf4deaae6a6a852eaa14f7952cdcef4e6"},
     {"file": "JIN10_CALENDAR_20261001T130733Z.json", "captured_at_utc": "2026-10-01T13:07:33Z", "events": 283, "window_original": ["2026-09-28 07:50", "2026-10-03 10:05"], "importance_field": "ABSENT", "raw_hash": "c28e56ddc0597bd7edc7465d"}
   ],
   "pit_rule": "calendar availability = its own pub_time_utc (Asia/Shanghai - 8h); nothing later may be used at T"
 },
 "cost_model": {"COST_MODEL_VERSION": "CALIBRATION_20RT_20260921", "REAL_RT_COST_BP": 0.914, "stress": [0.0, 1.0, 2.0, 3.0]},
 "execution_model": {
   "entry": "first tick with ts >= pub_time (+0s); long at ask, short at bid",
   "exit": "mid at first tick >= entry_ts + h",
   "mid_markout": "dir*(future_mid-entry_mid)",
   "exec_markout": "dir>0 ? future_mid-entry_ask : entry_bid-future_mid",
   "censoring": "forward window crossing a segment break (>60s gap) or the sample end = HORIZON_CENSORED, excluded and counted"
 },
 "frozen_thresholds": {
   "horizons_s": [1, 5, 15, 30, 60, 300],
   "pre_event_lookback_s": 60,
   "importance_high_ge": 3,
   "min_effective_n": 30,
   "a_priori": "no parameter scan; horizons/lookback/importance cut chosen before seeing any outcome"
 },
 "hypotheses": [
   {"id": "D1_EVENT_DRIFT_CONT", "kind": "directional", "mechanism": "event -> forward drift CONTINUES the pre-event 60s direction",
    "signal": "sign(mid(event) - mid(event-60s))", "entry": "first tick >= pub_time", "direction": "follow"},
   {"id": "D1_EVENT_DRIFT_FADE", "kind": "directional", "mechanism": "event -> forward drift FADES the pre-event 60s direction",
    "signal": "sign(mid(event) - mid(event-60s))", "entry": "first tick >= pub_time", "direction": "opposite"},
   {"id": "D2_EVENT_MAGNITUDE", "kind": "non_directional", "mechanism": "event window is MORE volatile than the matched non-event baseline",
    "metric": "|mid(entry+h)-mid(entry)| in bp, compared with a deterministic baseline sample (every 50th tick, same horizons)"},
   {"id": "D3_EVENT_SPREAD_RESPONSE", "kind": "descriptive", "mechanism": "spread at the event differs from the trailing 3000-tick median; quantify normalisation time",
    "metric": "spread_bp(entry)/trailing_median - 1, plus ticks-to-return-within-10%"}
 ],
 "statistics": {
   "is_oos_split": "time-ordered 70/30 by event time",
   "significance": "sign-flip permutation n=2000 + block bootstrap CI n=2000",
   "alpha": 0.05,
   "ladder": ["INSUFFICIENT_SAMPLE", "COST_INSUFFICIENT", "REJECT", "EDGE_UNCERTAIN", "EXECUTION_UNREALISTIC", "CANDIDATE"],
   "direction_policy": "every directional source frozen BOTH ways"
 },
 "known_limitations": [
   "THIN WINDOW: two non-overlapping calendar vintages; total in-window events ~156 + ~223; expectations must allow INSUFFICIENT_SAMPLE",
   "importance field absent in the 2026-10-01 vintage -> importance-stratified tests can only use the 2026-09-25 vintage",
   "calendar is a rolling window; history is not retrievable -> this window cannot be extended retroactively",
   "no pre-event (scheduled-ahead) test: availability is pub_time only, so pre-event drift is NOT_TESTABLE_PIT"
 ]
}
body = json.dumps(P, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
P["registry_hash_sha256"] = hashlib.sha256(body).hexdigest()
json.dump(P, open(os.path.join(HERE, "FROZEN_PROTOCOL.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote FROZEN_PROTOCOL.json")
print("registry_hash_sha256 =", P["registry_hash_sha256"])
print("hypotheses:", [h["id"] for h in P["hypotheses"]])
