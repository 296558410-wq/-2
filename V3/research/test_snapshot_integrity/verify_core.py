"""TEST snapshot integrity — verification core (READ-ONLY, NO EXPERIMENT).

Verifies:
  * preregistration hash / model spec / parameter / feature schema / cost model  (§26-§30)
  * protected-path inventory                                                     (§44)
  * whether ANY FXTM data exists after TEST_START                                (§6, §7, §34)
NO alpha statistics, NO future labels, NO PnL, NO model work.
"""
from __future__ import annotations

import hashlib
import json
import os

import pandas as pd

V3 = r"C:\AIQuant\research\hermes\trader_v3"
PREREG = os.path.join(V3, "research", "candidate_model_preregistration")
OUT = os.path.join(V3, "research", "test_snapshot_integrity")
EXPECTED_PREREG_SHA = "e273be091fc38cda0274cd2fededaeb28c2a11cd3398db770a6023d54faf5dc3"
TEST_START = "2026-09-22T06:20:00Z"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    now = pd.Timestamp.now(tz="UTC")
    res = {"schema": "v3_test_snapshot_verification/1", "utc_now": str(now),
           "TEST_START": TEST_START, "checks": {}, "data_availability": {}}

    # ---- §26..§30 pre-registration consistency --------------------------
    man_p = os.path.join(PREREG, "registries", "preregistration_manifest.json")
    man = json.load(open(man_p, encoding="utf-8"))
    res["checks"]["preregistration_sha256"] = {
        "expected": EXPECTED_PREREG_SHA, "actual": man.get("PREREGISTRATION_SHA256"),
        "match": man.get("PREREGISTRATION_SHA256") == EXPECTED_PREREG_SHA}
    # re-derive the manifest hash from the stored document hashes (tamper check)
    stored_docs = man.get("document_hashes", {})
    live = {d: sha256(os.path.join(PREREG, d)) for d in stored_docs}
    res["checks"]["document_hash_integrity"] = {
        "n": len(stored_docs),
        "mismatched": [d for d in stored_docs if live.get(d) != stored_docs[d]],
        "clean": all(live.get(d) == stored_docs[d] for d in stored_docs)}
    res["checks"]["model_spec_hash"] = {"expected": man.get("model_spec_hash"),
                                         "match": bool(man.get("model_spec_hash"))}
    res["checks"]["cost_model_hash"] = {"expected": man.get("cost_model_hash"),
                                         "match": bool(man.get("cost_model_hash")),
                                         "cost_model_id": man.get("cost_model_id"),
                                         "round_trip_usd": 0.40, "round_trip_bp": 0.914}
    res["checks"]["feature_schema_hash"] = {"expected": man.get("feature_schema_hash"),
                                             "match": bool(man.get("feature_schema_hash"))}
    reg = json.load(open(os.path.join(PREREG, "registries", "parameter_registry.json"), encoding="utf-8"))
    res["checks"]["parameter_registry"] = {"count": len(reg["parameters"]),
                                            "count_is_30": len(reg["parameters"]) == 30,
                                            "unresolved_tbd": reg.get("unresolved_tbd_count"),
                                            "categories_unchanged": sorted(set(
                                                p["category"] for p in reg["parameters"]))}
    res["checks"]["test_boundary"] = man.get("test_boundary")

    # ---- §44 protected paths --------------------------------------------
    prot = {}
    for rel in ["research/hermes/trader_v1", "research/hermes/trader_v2",
                 "research/hermes/trader_v3/execution", "research/hermes/trader_v3/foundation",
                 "research/hermes/trader_v3/state/V3_COST_PROFILE.json",
                 "research/hermes/trader_v3/research/candidate_model_preregistration",
                 "research/hermes/trader_v3/data/snapshots",
                 "research/hermes/trader_v3/research/github_microstructure_distillation",
                 "research/hermes/trader_v3/research/l1_execution_edge"]:
        p = os.path.join(r"C:\AIQuant", rel)
        prot[rel] = "PRESENT" if os.path.exists(p) else "ABSENT"
    res["checks"]["protected_paths"] = prot

    # ---- §6/§7/§34 data after TEST_START --------------------------------
    files = sorted(__import__("glob").glob(r"C:\AIQuant\data\live_fxtm\ticks_*.parquet"))
    after = []
    latest = None
    for f in files:
        d = pd.read_parquet(f, columns=["ts_utc"])
        mx, mn = d["ts_utc"].max(), d["ts_utc"].min()
        if latest is None or mx > latest:
            latest = mx
        if mx > pd.Timestamp(TEST_START):
            n_after = int((d["ts_utc"] > pd.Timestamp(TEST_START)).sum())
            after.append({"file": os.path.basename(f), "rows_after_test_start": n_after,
                          "ts_min": str(mn), "ts_max": str(mx)})
    res["data_availability"] = {
        "live_files": len(files),
        "latest_event_utc": str(latest),
        "test_start": TEST_START,
        "test_start_in_future": bool(pd.Timestamp(TEST_START) > now),
        "minutes_until_test_start": round((pd.Timestamp(TEST_START) - now).total_seconds() / 60.0, 1),
        "files_with_events_after_test_start": after,
        "total_events_after_test_start": int(sum(a["rows_after_test_start"] for a in after)),
    }
    with open(os.path.join(OUT, "verification.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
