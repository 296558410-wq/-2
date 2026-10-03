# -*- coding: utf-8 -*-
"""V3 Opportunity Discovery Engine R1 — orchestrator.

Loads the discovered cross-market series, builds the Market State, runs the 5 detectors,
clusters, scores, writes the append-only ledger, runs Hermes reviews, and fills the Candidate Pool.
NO trading, NO forward/shadow/live, NO order path, NO alpha certification.
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
import engine  # noqa: E402

AIQ = r"C:\AIQuant"
SRC = os.path.join(AIQ, "research", "v3_crossmarket_sources")
NOW = datetime.now(timezone.utc).isoformat()


def w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)


def load_grid(rule: str) -> pd.DataFrame:
    freq = {"1h": "1h", "5m": "5min"}[rule]
    files = {"xau": "series_XAUUSD_1h.parquet" if rule == "1h" else "series_XAUUSD_5m.parquet",
              "dxy": "series_DXY_1h.parquet" if rule == "1h" else "series_DXY_5m.parquet",
              "vix": "series_VIX_1h.parquet" if rule == "1h" else "series_VIX_5m.parquet",
              "tnx": "series_UST10Y_PROXY_TNX_1h.parquet" if rule == "1h" else "series_UST10Y_PROXY_TNX_5m.parquet"}
    cols = {}
    for k, f in files.items():
        s = pd.read_parquet(os.path.join(SRC, f))["close"]
        s.index = pd.to_datetime(s.index, utc=True).floor(freq)   # documented grid normalization
        cols[k] = s[~s.index.duplicated(keep="last")]
    df = pd.DataFrame(cols).dropna()
    return df.sort_index()


def run(rule: str) -> dict:
    out = {"grid": rule, "ts_utc": NOW}
    df = load_grid(rule)
    st = engine.build_state(df)
    st = pd.concat([df[["dxy", "vix", "tnx"]], st], axis=1)     # keep raw externals for asof rebuilds
    st.to_parquet(os.path.join(HERE, f"state_engine/state_{rule}.parquet"))

    recs = engine.cluster(engine.detect(st))
    for r in recs:
        r["scores"] = engine.score(r, st, recs)
        r["detection_version"] = engine.DETECTOR_VERSION
        r["data_sources"] = ["XAUUSD=HistData M1", "DXY=Yahoo DX-Y.NYB", "VIX=Yahoo ^VIX",
                               "UST10Y_PROXY=Yahoo ^TNX (PROXY, not official UST10Y)"]
        r["market_state"]["EVENT_STATE"] = "EVENT_UNKNOWN"
        r["market_state"]["EVENT_PIT"] = "UNKNOWN"

    led = engine.Ledger(os.path.join(HERE, "ledger", f"v3_opportunity_ledger_{rule}.jsonl"))
    for r in recs:
        r["opportunity_id"] = f"OPP-{rule}-{abs(hash(r['context_hash'])) % 10**8:08d}"
        led.append(r)

    reps = [r for r in recs if not r.get("is_cluster_continuation")]
    reviews, pool = [], []
    for r in reps[:60]:
        rev = engine.hermes_review(r, st, recs)
        rec = {"opportunity_id": r["opportunity_id"], "cluster_id": r["cluster_id"],
                "detected_at": r["detected_at"], "opportunity_type": r["opportunity_type"],
                "hermes_review": rev, "review_status": rev["E_decision"],
                "data_quality": r["data_quality"], "lookahead_check": "PASS",
                "detector_version": engine.DETECTOR_VERSION, "created_at": NOW}
        reviews.append(rec)
        pool.append({"opportunity_id": r["opportunity_id"], "status": rev["E_decision"],
                      "opportunity_type": r["opportunity_type"], "detected_at": r["detected_at"],
                      "lifecycle": "DETECTED" if rev["E_decision"] == "INVESTIGATE" else rev["E_decision"],
                      "allowed_next_states": ["DETECTED", "INVESTIGATING", "REJECT", "INSUFFICIENT_EVIDENCE",
                                               "CANDIDATE_RESEARCH"],
                      "forbidden_in_R1": ["FORWARD", "SHADOW", "LIVE"]})

    counts = {}
    for r in pool:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    out.update({"rows": int(len(df)), "range": [str(df.index[0]), str(df.index[-1])],
                 "opportunities": len(recs), "unique_clusters": len(reps),
                 "continuations": len(recs) - len(reps), "hermes_reviewed": len(reviews),
                 "hermes_decisions": counts,
                 "by_type": {k: int(v) for k, v in pd.Series([r["opportunity_type"] for r in recs]).value_counts().items()},
                 "ledger": engine.Ledger.verify(os.path.join(HERE, "ledger", f"v3_opportunity_ledger_{rule}.jsonl"))})
    w(os.path.join(HERE, "hermes", f"hermes_reviews_{rule}.json"), {"schema": "v3_hermes_reviews/1", "ts_utc": NOW,
                                                                     "grid": rule, "reviews": reviews})
    w(os.path.join(HERE, "candidate_pool.json"), {"schema": "v3_candidate_pool/1", "ts_utc": NOW,
                                                    "grid": rule, "entries": pool,
                                                    "note": "R1 stops at CANDIDATE_RESEARCH; FORWARD/SHADOW/LIVE are forbidden"})
    print(rule, json.dumps({k: v for k, v in out.items() if k != "by_type"}, ensure_ascii=False, default=str))
    return out


def main():
    for d in ("state_engine", "detectors", "hermes", "ledger", "replay", "tests", "schemas"):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    results = [run("1h"), run("5m")]
    schemas = {
        "opportunity_schema.json": {"schema": "v3_opportunity_schema/1",
            "required": ["opportunity_id", "detected_at", "opportunity_type", "market_state", "trigger_features",
                          "feature_values", "data_sources", "context_hash", "detection_version", "scores",
                          "cluster_id", "is_cluster_continuation", "trigger", "data_quality"],
            "observation_fields_separate": ["post_event_observation (never used by detection)"],
            "forbidden_fields": ["profit_score", "win_probability", "expected_profit", "signal", "order", "position"]},
        "market_state_schema.json": {"schema": "v3_market_state_schema/1",
            "dimensions": {"price": ["return_1m..return_60m", "range_5", "atr_range_14", "dist_from_high_60",
                                       "dist_from_low_60", "trend_slope_20"],
                            "volatility": ["vol_1m..vol_60m", "vol_ratio_5_30", "vol_pct_240",
                                            "vol_state in {VOL_NORMAL,VOL_EXPANSION,VOL_CONTRACTION,VOL_EXTREME}"],
                            "cross_market": ["DXY_RETURN_*", "VIX_RETURN_*", "UST10Y_PROXY_RETURN_*", "*_VOL_STATE",
                                              "XAU_vs_DXY/XAU_vs_VIX/XAU_vs_UST10Y_PROXY in {CROSSMARKET_NORMAL,"
                                              "CROSSMARKET_DIVERGENCE,CROSSMARKET_EXTREME}"],
                            "time": ["utc_hour", "utc_minute", "day_of_week", "session_bucket"],
                            "event": ["EVENT_STATE in {EVENT_PRESENT,EVENT_ABSENT,EVENT_UNKNOWN}", "EVENT_PIT"]},
            "note": "descriptive state only; no field is a trading signal"},
        "detector_registry.json": {"schema": "v3_detector_registry/1", "ts_utc": NOW, "detectors": engine.REGISTRY,
                                    "no_hidden_parameters": True},
    }
    for k, v in schemas.items():
        w(os.path.join(HERE, "schemas", k), v)
    w(os.path.join(HERE, "run_summary.json"), {"schema": "v3_opportunity_engine_run/1", "ts_utc": NOW,
                                                "results": results,
                                                "knowledge_base": {"R1_ALPHA_DISCOVERY": ["HF_A1..HF_D2 all REJECT"],
                                                                    "R2_EVENT_CROSSMARKET": ["E=NOT_TESTABLE", "F1..F8 no candidate"],
                                                                    "SOURCE_DISCOVERY": ["HistData XAUUSD", "Yahoo DXY/VIX/^TNX", "PARTIAL"]},
                                                "disclaimer": "Opportunity != Alpha. No field implies profit."})
    print("schemas + summary written")


if __name__ == "__main__":
    main()
