# -*- coding: utf-8 -*-
"""PIT registry + replay interface + the 5 mandatory leakage tests.

get_information_available_at(T) returns ONLY observations with availability_time <= T,
plus withheld_future count and registry_hash. Deterministic byte-for-byte.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP_ID = "V3-SNAP-PIT2-20261001T131500Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAP_ID)
REG_PATH = os.path.join(HERE, "PIT_REGISTRY.json")
OUT = os.path.join(HERE, "PIT_LEAKAGE_TESTS.json")

RULES = {
    "daily_market_bar_dated_D": "D+1T00:00:00Z",
    "calendar_event_with_pub_time": "its own pub_time_utc",
    "calendar_revision_value": "the vintage capture time (revision_time unprovable -> conservative)",
    "unfinished_bar": "FORBIDDEN",
    "tick_market_data": "its own timestamp",
}


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def parse_ts(s):
    if isinstance(s, str):
        try:
            return datetime.fromisoformat(s)
        except Exception:  # noqa: BLE001
            return None
    return None


def build_registry():
    man = json.load(open(os.path.join(SNAP, "MANIFEST.json"), encoding="utf-8"))
    obs = []
    for f in man["files"]:
        obs.append({"kind": "tick_series", "id": f["file"], "source": "FXTM demo (magic 90004)",
                    "observation_time": f["ts_min"], "publication_time": f["ts_min"],
                    "availability_time": f["ts_min"], "timezone_original": "UTC",
                    "granularity": "tick", "rows": f["rows"], "sha256": f["sha256"],
                    "status": "PASS", "reason": "execution-venue market data; available at observation"})
    vint_dir = os.path.join(HERE, "vintages")
    for fn in sorted(os.listdir(vint_dir)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(vint_dir, fn)
        v = json.load(open(p, encoding="utf-8"))
        cap = datetime.fromisoformat(v["captured_at_utc"])
        for e in v["events"]:
            pt = e.get("pub_time")
            if not pt:
                continue
            # original publication: available at pub_time (Asia/Shanghai -> UTC)
            pub_utc = datetime.strptime(pt, "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone(__import__("datetime").timedelta(hours=8))).astimezone(timezone.utc)
            obs.append({"kind": "calendar_event", "id": f"{v['schema']}|{fn}|{pt}|{e.get('event_name','')[:24]}",
                        "event_name": e.get("event_name"), "country": e.get("country"),
                        "importance": e.get("importance"), "observation_time": iso(pub_utc),
                        "publication_time": iso(pub_utc), "availability_time": iso(pub_utc),
                        "timezone_original": "Asia/Shanghai", "granularity": "event-time",
                        "vintage_file": fn, "vintage_captured_at_utc": v["captured_at_utc"],
                        "value_kind": "initial", "value": e.get("actual"),
                        "status": "PASS", "reason": "calendar pub_time is the publication time"})
            if e.get("revised") not in (None, ""):
                obs.append({"kind": "calendar_event_revision",
                            "id": f"{fn}|{pt}|{e.get('event_name','')[:20]}|rev",
                            "observation_time": iso(pub_utc), "publication_time": iso(pub_utc),
                            "availability_time": v["captured_at_utc"],
                            "timezone_original": "Asia/Shanghai", "granularity": "event-time",
                            "vintage_file": fn, "value_kind": "revision", "value": e.get("revised"),
                            "status": "CONDITIONAL",
                            "reason": "revision_time unprovable -> conservative availability = vintage capture"})
    # prior vintage (2026-09-25 pull)
    prior = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(V3)),
                                          "v3_long_history_data", "V3_JIN10_EVENT_PIT.json"))
    if os.path.exists(prior):
        pj = json.load(open(prior, encoding="utf-8"))
        cap = pj.get("retrieved_at_utc")
        for e in pj["events"]:
            obs.append({"kind": "calendar_event", "id": f"prior|{e['event_id']}",
                        "event_name": e.get("event_name"), "country": e.get("country"),
                        "importance": e.get("importance"),
                        "observation_time": e.get("pub_time_utc"),
                        "publication_time": e.get("pub_time_utc"),
                        "availability_time": e.get("pub_time_utc"),
                        "timezone_original": "Asia/Shanghai", "granularity": "event-time",
                        "vintage_file": "V3_JIN10_EVENT_PIT.json (2026-09-25)",
                        "vintage_captured_at_utc": cap, "value_kind": "initial",
                        "value": e.get("actual"), "status": "PASS",
                        "reason": "calendar pub_time is the publication time"})
            if e.get("revised") not in (None, ""):
                obs.append({"kind": "calendar_event_revision", "id": f"prior|{e['event_id']}|rev",
                            "observation_time": e.get("pub_time_utc"),
                            "publication_time": e.get("pub_time_utc"),
                            "availability_time": cap, "timezone_original": "Asia/Shanghai",
                            "granularity": "event-time", "vintage_file": "V3_JIN10_EVENT_PIT.json",
                            "value_kind": "revision", "value": e.get("revised"),
                            "status": "CONDITIONAL",
                            "reason": "revision_time unprovable -> conservative availability = vintage capture"})
    reg = {"schema": "v3_pit_registry/2", "SNAPSHOT_ID": SNAP_ID,
           "rules_FROZEN": RULES, "observation_count": len(obs),
           "series": {"tick_files": man["FILE_COUNT"], "calendar_vintages": man["calendar_vintages"]},
           "observations": obs}
    bad = [o for o in obs if parse_ts(o.get("availability_time")) is None]
    if bad:
        obs[:] = [o for o in obs if parse_ts(o.get("availability_time")) is not None]
        reg["dropped_unparsable"] = len(bad)
        reg["observation_count"] = len(obs)
    json.dump(reg, open(REG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return reg


def registry_hash(reg):
    return hashlib.sha256(json.dumps(reg["observations"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def get_information_available_at(T, reg):
    T = T.astimezone(timezone.utc)
    vis, withheld = [], 0
    for o in reg["observations"]:
        a = parse_ts(o["availability_time"])
        if a is not None and a <= T:
            vis.append(o)
        else:
            withheld += 1
    return {"registry_hash": registry_hash(reg), "as_of": iso(T),
            "returned": len(vis), "withheld_future": withheld, "observations": vis}


def main():
    reg = build_registry()
    rh = registry_hash(reg)
    res = {"schema": "v3_pit_leakage_tests/1", "registry_hash": rh,
           "observation_count": reg["observation_count"], "tests": {}}
    T = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

    # T1 future publication invisible
    v = get_information_available_at(T, reg)
    bad = [o for o in v["observations"]
           if datetime.fromisoformat(o["publication_time"]) > T]
    res["tests"]["T1_future_publication_invisible"] = {
        "pass": len(bad) == 0, "violations": len(bad), "withheld": v["withheld_future"]}

    # T2 future revision invisible
    rev_leak = [o for o in v["observations"] if o.get("value_kind") == "revision"]
    res["tests"]["T2_future_revision_invisible"] = {
        "pass": len(rev_leak) == 0, "revision_rows_visible_at_T": len(rev_leak)}

    # T3 determinism
    a = json.dumps(get_information_available_at(T, reg), sort_keys=True, ensure_ascii=False)
    b = json.dumps(get_information_available_at(T, reg), sort_keys=True, ensure_ascii=False)
    res["tests"]["T3_replay_deterministic"] = {"pass": a == b, "identical": a == b}

    # T4 hash integrity (tamper + missing detection)
    reg2 = json.loads(json.dumps(reg))
    reg2["observations"].append({"kind": "tick_series", "id": "tampered",
                                 "availability_time": "2020-01-01T00:00:00+00:00"})
    tamper_detected = registry_hash(reg2) != rh
    out_of_snapshot = []
    for o in reg["observations"]:
        if o["kind"] == "tick_series":
            p = os.path.join(SNAP, o["id"])
            h = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "MISSING"
            if h != o["sha256"]:
                out_of_snapshot.append(o["id"])
    res["tests"]["T4_hash_integrity"] = {
        "pass": tamper_detected and not out_of_snapshot,
        "tamper_detected": tamper_detected, "file_hash_mismatches": out_of_snapshot}

    # T5 timezone normalization preserves original
    tz_ok = all(o.get("timezone_original") for o in reg["observations"])
    norm_ok = all("+00:00" in o["availability_time"] for o in reg["observations"])
    res["tests"]["T5_timezone_normalized_preserving_original"] = {
        "pass": tz_ok and norm_ok, "all_have_original_tz": tz_ok, "all_utc_normalized": norm_ok}

    npass = sum(1 for t in res["tests"].values() if t["pass"])
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"=== PIT_LEAKAGE_TEST_COUNT={len(res['tests'])} PASS={npass} FAIL={len(res['tests'])-npass} ===")
    print("registry_hash:", rh[:24], "observations:", reg["observation_count"])
    print(json.dumps(res["tests"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
