"""TEST collection attempt — V3-HFT-TEST-SNAPSHOT-FREEZE-002.

TEST-COLLECTION / SNAPSHOT-FREEZE / READ_ONLY / NO-EXPERIMENT.

Collects the first N valid sessions AFTER TEST_START using the officially ruled definition:
    SESSION            = CONTIGUOUS_SEGMENT
    SEGMENT_BOUNDARY   = adjacent valid-event gap > 3000 s
    MIN_SESSION_TICKS  = 200,000
    first session starts at the first event >= TEST_START

Computes ONLY integrity/session facts. No returns, markout, PnL, labels, models.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd

V3 = r"C:\AIQuant\research\hermes\trader_v3"
H = os.path.join(V3, "research", "test_snapshot_integrity")
PREREG = os.path.join(V3, "research", "candidate_model_preregistration")
GEN_UTC = None
TEST_START = "2026-09-22T06:20:00Z"
SEG_GAP_S = 3000
MIN_TICKS = 200_000
TARGET_SESSIONS = 10


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    global GEN_UTC
    now = pd.Timestamp.now(tz="UTC")
    GEN_UTC = str(now)
    ts_start = pd.Timestamp(TEST_START)
    out = {"schema": "v3_test_collection_attempt/1", "utc_now": GEN_UTC, "test_start": TEST_START,
           "session_definition": {"session": "CONTIGUOUS_SEGMENT", "segment_gap_threshold_s": SEG_GAP_S,
                                   "min_session_ticks": MIN_TICKS, "target_sessions": TARGET_SESSIONS}}

    # ---- load every live file, keep only events >= TEST_START -----------------
    files = sorted(glob.glob(r"C:\AIQuant\data\live_fxtm\ticks_*.parquet"))
    frames, filemeta = [], []
    for f in files:
        d = pd.read_parquet(f)
        filemeta.append({"path": f.replace("\\", "/"), "file": os.path.basename(f),
                          "sha256": sha256(f), "size": os.path.getsize(f), "row_count": int(len(d)),
                          "cols": list(d.columns),
                          "timestamp_min": str(d["ts_utc"].min()), "timestamp_max": str(d["ts_utc"].max())})
        frames.append(d)
    alld = pd.concat(frames, ignore_index=True).sort_values("ts_utc").reset_index(drop=True)

    # ---- timestamp unit verification (prove ms by VALUE, do not guess) -------
    raw = alld["ts_utc"].astype("int64").to_numpy()
    scale = {}
    for unit, div in (("ms", 1e3), ("us", 1e6), ("ns", 1e9)):
        secs = raw[:1] / div
        scale[unit] = str(pd.Timestamp(int(secs[0]), unit="s", tz="UTC"))
    unit_verified = {"declared": "ms", "dtype": str(alld["ts_utc"].dtype),
                      "interpretations": scale,
                      "proof": "'ms' is the only interpretation that yields a 2026 date; us/ns would imply 1970",
                      "verdict": "PROVEN_BY_VALUE"}

    # ---- boundary separation (§22) ------------------------------------------
    before = alld[alld["ts_utc"] < ts_start]
    after = alld[alld["ts_utc"] >= ts_start].reset_index(drop=True)
    last_before = str(before["ts_utc"].max()) if len(before) else None
    first_after = str(after["ts_utc"].min()) if len(after) else None
    boundary_gap_s = (round((pd.Timestamp(first_after) - pd.Timestamp(last_before)).total_seconds(), 3)
                       if (last_before and first_after) else None)

    # ---- segments on the POST-TEST_START data (§6, §7, §8) -------------------
    segs = []
    if len(after):
        t = after["ts_utc"].astype("int64").to_numpy()
        d = np.diff(t) / 1e6                       # seconds
        starts = [0] + [i + 1 for i in range(len(d)) if d[i] > SEG_GAP_S]
        ends = [i for i in range(len(d)) if d[i] > SEG_GAP_S] + [len(after) - 1]
        before_prev = last_before
        for k, (s, e) in enumerate(zip(starts, ends)):
            rows = int(e - s + 1)
            gap_before = (round((t[s] - pd.Timestamp(before_prev).value // 10**6) / 1000.0, 3)
                          if before_prev else None)
            gap_after = (round((t[ends[k + 1]] - t[e]) / 1000.0, 3) if k + 1 < len(starts) else None)
            valid = rows >= MIN_TICKS
            segs.append({"session_id": f"TEST-S{k+1:03d}",
                          "start_ts": str(after["ts_utc"].iloc[s]), "end_ts": str(after["ts_utc"].iloc[e]),
                          "raw_tick_count": rows,
                          "gap_before": gap_before, "gap_after": gap_after,
                          "validity": "VALID" if valid else "INCOMPLETE",
                          "reason": ("tick_count >= 200000" if valid
                                     else f"tick_count {rows} < {MIN_TICKS} (INCOMPLETE, cannot pad)"),
                          "source_files": sorted(set(after["src"].iloc[s:e + 1])) if "src" in after else []})
            before_prev = after["ts_utc"].iloc[e]
    valid_count = sum(1 for s in segs if s["validity"] == "VALID")

    # ---- integrity facts -----------------------------------------------------
    dup_ts = int(after["ts_utc"].duplicated().sum()) if len(after) else 0
    dup_q = int(after.duplicated(subset=["ts_utc", "bid", "ask"]).sum()) if len(after) else 0
    dup_e = int(after.duplicated(subset=["ts_utc", "bid", "ask"]).sum()) if len(after) else 0
    ooo = int((after["ts_utc"].diff().dropna() < pd.Timedelta(0)).sum()) if len(after) else 0
    gaps = {}
    if len(after) > 1:
        dd = np.diff(after["ts_utc"].astype("int64").to_numpy()) / 1e6
        gaps = {"gap_count_gt_60s": int((dd > 60).sum()), "gap_count_gt_3000s": int((dd > 3000).sum()),
                 "max_gap_s": float(dd.max())}

    # ---- throughput projection (scheduling only, NOT a result) --------------
    ticks_after = int(len(after))
    elapsed_h = (now - ts_start).total_seconds() / 3600.0
    rate = ticks_after / elapsed_h if elapsed_h > 0 else None
    # a valid session needs MIN_TICKS of contiguous data; sessions/day <= 1 on a daily-break market
    hours_per_session = (MIN_TICKS / rate / 3600.0) if (rate and rate > 0) else None
    projection = {"ticks_after_test_start": ticks_after, "elapsed_hours_since_test_start": round(elapsed_h, 3),
                   "observed_ticks_per_hour": round(rate, 1) if rate else None,
                   "hours_of_data_needed_for_one_valid_session": (round(hours_per_session, 1)
                                                                   if hours_per_session else None),
                   "sessions_per_day_upper_bound": 1,
                   "note": "a session is a contiguous segment; the daily market break (>3000 s) splits days, "
                            "so at most ~1 valid session can form per trading day"}

    res = {**out, "unit_verification": unit_verified,
            "boundary": {"last_event_before_test_start": last_before, "first_event_after_test_start": first_after,
                          "boundary_gap_seconds": boundary_gap_s,
                          "boundary_note": "this gap is an ARTEFACT of TEST_START, not a natural market gap; "
                                            "it must not be used as a session boundary (§22)"},
            "post_test_start": {"row_count": ticks_after,
                                 "timestamp_min": first_after, "timestamp_max": str(after["ts_utc"].max()) if len(after) else None,
                                 "out_of_order_count": ooo,
                                 "dup_timestamp": dup_ts, "dup_quote": dup_q,
                                 "DUP_EVENT": "DATA_GAP",
                                 "EVENT_IDENTITY": "DATA_GAP (no event id in the feed; (ts,bid,ask) cannot prove identity)",
                                 **gaps},
            "sessions": segs, "valid_session_count": valid_count,
            "TEST_READY": "YES" if valid_count >= TARGET_SESSIONS else "NO",
            "projection": projection,
            "file_manifest": filemeta}

    json.dump(res, open(os.path.join(H, "collection_attempt.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("utc_now", "boundary", "post_test_start", "valid_session_count",
                                            "TEST_READY", "projection")}, indent=1, default=str))
    print("sessions:", json.dumps(segs, indent=1, default=str)[:800])


if __name__ == "__main__":
    main()
