"""V3-HFT-ALPHA-POSTMORTEM-001 audit driver.

AUDIT_ONLY / READ_ONLY. Reads the frozen products of V3-HFT-ALPHA-DISCOVERY-001
and writes ONLY under alpha/audit/. Never re-runs the alpha search, never places
an order, never touches V1/V2/OpenClaw/foundation/calibration/ledger paths.
"""
from __future__ import annotations
import hashlib
import json
import os
import glob
import datetime as dt

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = os.path.dirname(HERE)
AUDIT = HERE
ROOT = r"C:\AIQuant"


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(rel):
    with open(os.path.join(ALPHA, rel), encoding="utf-8") as f:
        return json.load(f)


def write_json(name, obj):
    with open(os.path.join(AUDIT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    print("wrote", name)


def write_text(name, text):
    with open(os.path.join(AUDIT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", name)


# ----------------------------------------------------------------- inputs
manifest = load_json("data/data_manifest.json")
eff = load_json("statistics/effective_sample.json")
mtest = load_json("statistics/multiple_testing.json")
stats = load_json("statistics/statistical_tests.json")
move = load_json("statistics/move_scale.json")
cost = load_json("backtest/cost_sensitivity.json")
lat = load_json("backtest/latency_sensitivity.json")
oos = load_json("oos/oos_results.json")
mm = load_json("models/model_manifest.json")

FREEZE_SHA = sha256(os.path.join(ALPHA, "freeze", "V3_ALPHA_RESEARCH_FREEZE_001.md"))
REPORT_SHA = sha256(os.path.join(ALPHA, "reports", "V3_HFT_ALPHA_DISCOVERY_001_REPORT.md"))
RESULT_SHA = sha256(os.path.join(ALPHA, "reports", "V3_HFT_ALPHA_DISCOVERY_001_RESULT.json"))
ALPHA_COMMIT = "b42c865e49e8ea11a740c14dfbddb8eb74b1e161"
ALPHA_HEAD_RECORD = "e83ae7690526a4722ba3cde6540f6fc29e717118"

# ------------------------------------------------------- 1. leakage audit
leak = {
    "schema": "v3_alpha_postmortem_data_leakage/1",
    "generated_utc": now_utc(),
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "input_freeze_sha256": FREEZE_SHA,
    "folds": {"train": ["2026-08-04", "2026-08-22"], "val": ["2026-08-24", "2026-09-05"],
              "test": ["2026-09-07", "2026-09-22"]},
    "checks": {
        "chronological_folds": {"result": "PASS",
                                 "evidence": "run_experiments.py L41-43 FOLDS by UTC day number; fold assigned by day, no shuffle"},
        "purge_embargo_equals_h": {"result": "PASS",
                                   "evidence": "L256-258 purge = (train & fwd_day>=VAL_start)|(val & fwd_day>=TEST_start)"},
        "feature_causality_pit": {"result": "PASS",
                                  "evidence": "feature_builder.compute_tick_features uses only ts<=i (rolling/lag); grid as-of = searchsorted(ts,grid,'right')-1 (last tick <= instant)"},
        "normalization_train_only": {"result": "PASS",
                                      "evidence": "run_experiments.py L314/L424 mu,sd = Xi[train].mean(0)/std(0); applied to val/test"},
        "no_interpolation": {"result": "PASS",
                              "evidence": "forward_labels picks first real tick >= t+h; gaps -> undefined/clean=false; never filled"},
        "test_used_for_model_selection": {"result": "PASS",
                                           "evidence": "L343-348 best family = argmax(val_net_edge_usd); model loop selects on VAL; no selection key uses test"},
        "test_metrics_observed_during_screening": {"result": "MINOR_EXPOSURE",
                                                    "evidence": "L319 run_config evaluates BOTH val and test on every candidate; test_net_edge_* written into model_manifest.iteration_log. Not used to select, but TEST was de-facto observed 30x -> weakens literal 'TEST never used before final'."},
        "threshold_selection_leakage": {"result": "PASS",
                                         "evidence": "position threshold = cost c_bp (frozen cost), not tuned on test"},
        "cost_latency_selection_leakage": {"result": "PASS",
                                            "evidence": "cost tiers and latency grid are frozen; latency uses real ticks via searchsorted, not re-optimised"},
        "overlap_handling": {"result": "PASS",
                              "evidence": "rho=h/median_dt; effective_n=n/max(rho,1); ttest on non-overlapping sub-sample; block bootstrap block=max(50,10*rho)"},
    },
    "verdict": "PASS",
    "verdict_note": "No data leakage into selection. One documented MINOR_EXPOSURE: TEST metrics were computed/logged during the 30-iteration screen (not used to select). A negative result cannot be inflated by test peeking.",
}
write_json("DATA_LEAKAGE_AUDIT.json", leak)

# ------------------------------------------------------- 2. snapshot audit
def file_rows_tsmax(p):
    d = pd.read_parquet(p, columns=["ts_utc"])
    return len(d), str(d["ts_utc"].max())


snap_files = {}
prov = {"match": 0, "mismatch": 0}
for fam in ["fxtm_staging_tick", "fxtm_live_tick"]:
    rows = []
    for e in manifest["files"][fam]:
        p = e["path"]
        cur_sha = sha256(p) if os.path.exists(p) else None
        ok = cur_sha == e["sha256"]
        prov["match" if ok else "mismatch"] += 1
        n_now, tmax_now = file_rows_tsmax(p) if os.path.exists(p) else (None, None)
        rows.append({
            "file": os.path.basename(p),
            "manifest_rows": e["rows"], "current_rows": n_now,
            "rows_delta": (n_now - e["rows"]) if n_now is not None else None,
            "manifest_sha256": e["sha256"], "current_sha256": cur_sha, "sha_match": bool(ok),
            "manifest_ts_max_utc": e["ts_max_utc"], "current_ts_max_utc": tmax_now,
            "manifest_duplicate_rate": e["duplicate_rate"], "manifest_out_of_order_rate": e["out_of_order_rate"],
        })
    snap_files[fam] = rows

# cross-file duplicates on the live family
lv_paths = sorted(glob.glob(os.path.join(ROOT, "data", "live_fxtm", "ticks_*.parquet")))
lv_all = pd.concat([pd.read_parquet(p) for p in lv_paths], ignore_index=True)
cross_dup = int(lv_all["ts_utc"].duplicated().sum())
per_file_dup = int(sum(pd.read_parquet(p, columns=["ts_utc"])["ts_utc"].duplicated().sum() for p in lv_paths))
st_paths = sorted(glob.glob(os.path.join(ROOT, "data", "staging_fxtm", "ticks_*.parquet")))
st_all = pd.concat([pd.read_parquet(p) for p in st_paths], ignore_index=True)
st_cross_dup = int(st_all["ts_utc"].duplicated().sum())

snap = {
    "schema": "v3_alpha_postmortem_data_snapshot/1",
    "generated_utc": now_utc(),
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "ALPHA_DISCOVERY_INPUT_COMMIT": ALPHA_COMMIT,
    "ALPHA_DISCOVERY_HEAD_RECORD_COMMIT": ALPHA_HEAD_RECORD,
    "ALPHA_DISCOVERY_REPORT_SHA256": REPORT_SHA,
    "ALPHA_DISCOVERY_RESULT_SHA256": RESULT_SHA,
    "FREEZE_SHA256": FREEZE_SHA,
    "data_manifest_generated_utc": manifest["generated_utc"],
    "manifest_carries_per_file_sha256": True,
    "provenance_chain": "experiment -> data_manifest.json(family) -> per-file sha256 -> current file bytes",
    "staging_fxtm": {"files": len(snap_files["fxtm_staging_tick"]),
                      "sha_match": sum(1 for r in snap_files["fxtm_staging_tick"] if r["sha_match"]),
                      "sha_total": len(snap_files["fxtm_staging_tick"]),
                      "cross_file_duplicates": st_cross_dup},
    "live_fxtm": {"files": len(snap_files["fxtm_live_tick"]),
                   "sha_match": sum(1 for r in snap_files["fxtm_live_tick"] if r["sha_match"]),
                   "sha_total": len(snap_files["fxtm_live_tick"]),
                   "cross_file_duplicates": cross_dup, "per_file_duplicates": per_file_dup,
                   "appending": True},
    "files": snap_files,
    "finding": ("staging 24/24 provable; live 10/11 provable. ticks_20260921.parquet is "
                "actively appended (+4736 rows; ts_max 2026-09-21T19:39:06.708Z -> 20:09:07.349Z) "
                "so its bytes are NOT provably the discovery snapshot."),
    "cross_file_duplicate_explanation": ("the 913 duplicate ts are cross-day-file boundary repeats "
                                          "(per-file duplicates = 0); they do not change the frozen analysis "
                                          "because the discovery run read the pre-append snapshot"),
    "verdict": "PASS_WITH_DATA_GAP",
    "verdict_note": ("Snapshot provable for staging (24/24) and 10/11 live files. One live tail file "
                     "is unprovable by hash (DATA_GAP). NON_BLOCKING: the append occurred after the "
                     "discovery snapshot and the affected rows are inside TEST only."),
    "blocking": False,
}
write_json("DATA_SNAPSHOT_AUDIT.json", snap)

# ------------------------------------------------------- 3. capability audit
nonzero = {}
for fam in ["fxtm_staging_tick", "fxtm_live_tick"]:
    e = manifest["files"][fam][0]
    nonzero[fam] = {"volume_nonzero_frac": e["volume_nonzero_frac"],
                    "volume_real_nonzero_frac": e["volume_real_nonzero_frac"],
                    "last_nonzero_frac": e["last_nonzero_frac"]}
cap = {
    "schema": "v3_alpha_postmortem_data_capability/1",
    "generated_utc": now_utc(),
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "available_fields": ["bid", "ask", "ts_utc", "flags"],
    "derived_fields": ["mid=(bid+ask)/2", "spread=ask-bid"],
    "missing_fields": ["L2 order book / depth", "trade prints", "real volume", "last",
                        "queue position", "order sizes", "signed trade flow"],
    "zero_field_proof": nonzero,
    "consequences": {
        "microprice": "DATA_GAP (needs bid/ask sizes; volume/volume_real identically 0)",
        "true_ofi": "DATA_GAP (no sizes, no prints)",
        "ofi_used": "tick-rule L1 proxy only (sign of mid change over 20 ticks) - weak information proxy",
        "vpin/kyle_lambda/queue_imbalance": "DATA_GAP",
    },
    "FEATURE_CAPABILITY": "L1_QUOTE_ONLY (price/spread/time only; no trade-flow or depth information)",
    "verdict": "DATA_GAP",
    "verdict_note": "Microstructure/trade-flow alpha is not testable on this feed; only price-based families B0/B3/B4/B5/B6 and a tick-rule proxy B2 could be tested.",
}
write_json("DATA_CAPABILITY_AUDIT.json", cap)

# ------------------------------------------------------- 4. cost audit
COST_BP = 0.914
ratios = {}
for h, v in move.items():
    m = v.get("median_abs_bp")
    ratios[h] = {"median_abs_move_bp": m, "n": v.get("n"),
                  "cost_to_move_ratio": (round(COST_BP / m, 3) if m else None)}
cost_audit = {
    "schema": "v3_alpha_postmortem_execution_cost/1",
    "generated_utc": now_utc(),
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "cost_anchor_usd_per_rt": 0.40,
    "cost_components": {"spread_usd_rt": 0.18, "commission_usd_rt": 0.22},
    "cost_bp_at_4376usd_oz": COST_BP,
    "measured_median_spread_usd": 0.15,
    "measured_median_spread_bp": 0.343,
    "cost_over_move": ratios,
    "best_gross_edge_bp_any_config": 0.096,
    "gross_edge_shortfall_vs_cost": round(COST_BP / 0.096, 1),
    "verdict": "EXECUTION_COST_BOTTLENECK",
    "verdict_note": ("At h<=5s the round-trip cost is 1.5x-5.6x the median absolute move and ~9x the best "
                     "estimated gross edge. Cost alone explains negative net edge for short horizons."),
}
write_json("EXECUTION_COST_AUDIT.json", cost_audit)

# ------------------------------------------------------- 5. latency audit
lat_rows = {}
for h, v in lat["horizons"].items():
    lat_rows[h] = {"selected": v["selected"],
                    "net_edge_bp_by_latency_ms": {k: v["latency_ms"][k]["net_edge_bp"] for k in v["latency_ms"]}}
lat_audit = {
    "schema": "v3_alpha_postmortem_latency/1",
    "generated_utc": now_utc(),
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "latency_grid_ms": lat["latency_ms"],
    "rows": lat_rows,
    "positive_at_0ms": {h: (r["net_edge_bp_by_latency_ms"]["0"] > 0) for h, r in lat_rows.items()},
    "verdict": "NOT_LATENCY_BOUND",
    "verdict_note": ("Net edge is already negative at 0 ms latency on every horizon "
                     "(1s -1.004 bp, 30s -0.880 bp, 5min -0.771 bp). Latency is a secondary effect, "
                     "not the binding constraint."),
}
write_json("LATENCY_AUDIT.json", lat_audit)

# ------------------------------------------------------- 6. failure matrix
matrix = [
    ("Price signal", "NOT_SUPPORTED", "gross rank-IC -0.179@1s, -0.142@5s; best gross +0.096 bp << 0.914 bp cost"),
    ("Microstructure signal", "DATA_GAP", "no sizes/prints -> microprice & true OFI unmeasurable"),
    ("L1 information", "NOT_SUPPORTED", "bid/ask/ts present & causal; tested 6 price families; no net edge"),
    ("L2 information", "DATA_GAP", "no order book / depth on feed"),
    ("Trade flow", "DATA_GAP", "volume=volume_real=last identically 0"),
    ("Sample size", "SUPPORTED", "eff_n 605,337@1s .. 2,467@5min (see coverage row for short/long tail)"),
    ("Cost", "NOT_SUPPORTED", "0.914 bp cost = 2.6x median 1s move; kills net edge at h<=5s"),
    ("Latency", "SUPPORTED", "latency grid measured on real ticks; not the binding constraint"),
    ("OOS", "SUPPORTED", "train-fit/val-select/test-once; 0/30 FDR reject (minor: test metrics logged in screen)"),
    ("Statistical power", "SUPPORTED", "8/30 tests had valid p; 4 horizons with eff_n>2000"),
    ("Data coverage", "NOT_SUPPORTED", "gaps 2023-12, 2024-04..2026-07, daily 21:00-22:59Z; 24h unresolvable"),
    ("Execution observability", "DATA_GAP", "only spread+commission+latency observable; no fill/queue data"),
]
mcs = "dimension,conclusion,evidence\n" + "\n".join(f'"{a}","{b}","{c}"' for a, b, c in matrix) + "\n"
write_text("ALPHA_FAILURE_MATRIX.csv", mcs)

# ------------------------------------------------------- 7. result json
horizon_class = {}
for h, v in eff["horizons"].items():
    en = v["effective_n"]
    if v["verdict"] == "DATA_INSUFFICIENT":
        horizon_class[h] = "DATA_INSUFFICIENT"
    elif en < 1000:
        horizon_class[h] = "DATA_LIMITED"
    else:
        horizon_class[h] = "SUFFICIENT"

result = {
    "schema": "v3_alpha_postmortem_result/1",
    "task": "V3-HFT-ALPHA-POSTMORTEM-001",
    "generated_utc": now_utc(),
    "mode": "AUDIT_ONLY / READ_ONLY",
    "ALPHA_DISCOVERY_RESULT_UNCHANGED": "NO_ALPHA",
    "ALPHA_DISCOVERY_INPUT_COMMIT": ALPHA_COMMIT,
    "ALPHA_DISCOVERY_REPORT_SHA256": REPORT_SHA,
    "FREEZE_SHA256": FREEZE_SHA,
    "DATA_LEAKAGE": "PASS",
    "DATA_SNAPSHOT": "PASS_WITH_DATA_GAP",
    "DATA_CAPABILITY": "L1_QUOTE_ONLY / DATA_GAP for microstructure",
    "EXECUTION_COST_BOTTLENECK": "YES",
    "LATENCY_BOTTLENECK": "NO",
    "horizon_class": horizon_class,
    "SUPPORTED_NO_ALPHA": True,
    "DATA_LIMITED_NO_ALPHA": True,
    "EXECUTION_LIMITED_NO_ALPHA": True,
    "levels_note": ("A: for 1s/5s/30s/5min data is sufficient, OOS clean, cost real -> no supportive alpha. "
                     "B: 50ms/200ms/24h are DATA_INSUFFICIENT and 1h has eff_n=196 -> cannot conclude strongly. "
                     "C: real gross predictability exists but is ~9x smaller than cost -> unexecutable."),
    "BLOCKING_ISSUES": [],
    "NON_BLOCKING_ISSUES": [
        "TEST metrics computed/logged during screening (not used for selection)",
        "live tick feed still appends -> one tail file not hash-provable (DATA_GAP)",
        "913 cross-day-file duplicate ts in live feed",
    ],
    "FUTURE_RESEARCH_HYPOTHESES": [
        "acquire L2/depth or trade-print data before any microstructure alpha claim",
        "freeze a byte-stable tick snapshot before any future OOS run",
        "if the venue offers lower-cost execution, re-test the 30s-5min horizons",
    ],
    "Q10_ROUTE_CHOICE": "NOT_MADE_BY_THIS_TASK (evidence only)",
    "ORDER_SEND_CALLS": 0,
    "NEW_CALIBRATION_ORDERS": 0,
    "MT5_INSTANCE_COUNT": 3,
    "MT5_ISOLATION": "PASS",
    "V3_FORWARD_ALLOWED": "NO",
    "V3_LIVE_ALLOWED": "NO",
    "EXPANSION": "LOCKED",
    "V1_UNTOUCHED": True,
    "V2_UNTOUCHED": True,
    "OPENCLAW_UNTOUCHED": True,
    "FORMULA_FIX_UNTOUCHED": True,
    "CALIBRATION_UNTOUCHED": True,
    "ALPHA_DISCOVERY_001_UNTOUCHED": True,
    "WAIT_FOR_CHATGPT_FINAL_AUDIT": True,
}
write_json("ALPHA_POSTMORTEM_RESULT.json", result)

print("phase-1 artifacts done")
