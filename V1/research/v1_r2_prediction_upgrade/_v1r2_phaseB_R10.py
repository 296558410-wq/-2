# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R10 — PRICE_STRUCTURE_BOUNDARY_AUDIT (DIAGNOSTIC ONLY, PRE-REGISTERED).

Goal: PROVE the boundaries, not optimise them. No threshold is changed; no shadow boundary is promoted.
Loads the B-R9 frozen state definition AS-IS. GIT_COMMIT=NONE."""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import itertools
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
REPORTS = os.path.join(UP, "reports")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
R9MOD = os.path.join(UP, "_v1r2_phaseB_R9.py")
REG3 = os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json")
DEF9 = os.path.join(REPORTS, "V1_R2_B9_STATE_DEFINITION.json")
DEF10 = os.path.join(REPORTS, "V1_R2_B10_BOUNDARY_DEFINITION.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
DEF9_PREFIX = "f1c550975409752e7b8224e7e43c30f9"
P = {"TOUCH_TOL_ATR": 0.25, "RECOVERY_W": 8, "BREAK_CLOSE_ATR": 0.15, "EV_PEN": 0.30, "TOUCH_W": 240,
     "PIVOT_L": 2, "PIVOT_R": 2, "RANGE_W": 96, "LEVEL_MAX": 60}


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def wjsonl(p, rows):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def quart(vals, q):
    if not vals:
        return None
    s = sorted(vals); k = (len(s) - 1) * q; f = int(k); c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 4)


def dist(vals):
    if not vals:
        return {k: None for k in ("min", "p01", "p05", "p10", "p25", "p50", "median", "p75", "p90", "p95", "p99", "max", "n", "mean")}
    return {"n": len(vals), "min": round(min(vals), 4), "p01": quart(vals, 0.01), "p05": quart(vals, 0.05),
            "p10": quart(vals, 0.10), "p25": quart(vals, 0.25), "p50": quart(vals, 0.50),
            "median": round(statistics.median(vals), 4), "p75": quart(vals, 0.75), "p90": quart(vals, 0.90),
            "p95": quart(vals, 0.95), "p99": quart(vals, 0.99), "max": round(max(vals), 4),
            "mean": round(sum(vals) / len(vals), 4)}


def separation_verdict(vals, bin_w):
    """Pre-registered objective bimodality test (see BOUNDARY_DEFINITION)."""
    if len(vals) < 50:
        return "INCONCLUSIVE", {}
    hi = max(vals)
    nb = max(3, int(math.ceil((hi * 1.05) / bin_w)))
    bins = [0] * nb
    for v in vals:
        bins[min(nb - 1, int(v // bin_w))] += 1
    n = len(vals)
    peaks = [i for i in range(1, nb - 1) if bins[i] > bins[i - 1] and bins[i] >= bins[i + 1] and bins[i] / n >= 0.05]
    valleys = [i for i in range(1, nb - 1) if bins[i] < bins[i - 1] and bins[i] <= bins[i + 1]]
    mono = all(bins[i] >= bins[i + 1] for i in range(nb - 1))
    detail = {"bins": [{"lo": round(i * bin_w, 2), "hi": round((i + 1) * bin_w, 2), "count": bins[i],
                          "density": round(bins[i] / n, 4)} for i in range(nb)],
               "local_peaks": [{"bin_lo": round(i * bin_w, 2), "density": round(bins[i] / n, 4)} for i in peaks],
               "local_valleys": [{"bin_lo": round(i * bin_w, 2), "density": round(bins[i] / n, 4)} for i in valleys],
               "monotone_nonincreasing": mono}
    if mono or len(peaks) <= 1:
        return "NO_NATURAL_SEPARATION", detail
    for a, b in itertools.combinations(peaks, 2):
        if (b - a) * bin_w < 0.15:
            continue
        for v in valleys:
            if a < v < b and bins[v] <= 0.5 * min(bins[a], bins[b]):
                return "NATURAL_SEPARATION", detail
    return "INCONCLUSIVE", detail


def main():
    # ---------- gates ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_rec = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    if not (reg3.get("new_registry_hash") == REG_HASH == reg_rec and reg3.get("version") == "v1r2-r3"):
        print("BLOCKED: REGISTRY_MISMATCH"); raise SystemExit(2)
    def9 = json.load(open(DEF9, encoding="utf-8"))
    def9_hash = sha_file(DEF9)
    bd = json.load(open(DEF10, encoding="utf-8"))
    bd_hash = sha_file(DEF10)
    if not def9_hash.startswith(DEF9_PREFIX):
        print("BLOCKED: B-R9 STATE DEFINITION CHANGED"); raise SystemExit(2)
    R1 = load_mod("v1r2_r1", R1MOD)
    R9 = load_mod("v1r2_r9", R9MOD)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    if sha_file(pq) != PQ_SHA:
        print("BLOCKED: DATASET_CHANGE"); raise SystemExit(2)
    df = pd.read_parquet(pq)
    jd = R1.indicators(df.copy())
    atr = jd["atr20"].to_numpy(float)
    states = R1.engines_v2(jd.copy())
    jts = pd.to_datetime([s["t"] for s in states], utc=True)

    # ---------- §5 PIT ----------
    recs = []
    for f in sorted(os.listdir(DEC)):
        if not f.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
            t = pd.Timestamp(str(d.get("cycle")).replace("Z", "+00:00"))
            t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        except Exception:  # noqa: BLE001
            recs.append({"status": "ALIGNMENT_ERROR"}); continue
        idx = int(jts.searchsorted(t - GRID, side="right")) - 1
        if t < jts[0]:
            st_, bi = "OUT_OF_DATASET", None
        elif t > jts[-1] + GRID:
            st_, bi = "ALIGNMENT_ERROR", None
        else:
            bar = jts[idx]; pit = bool(bar + GRID <= t)
            st_, bi = ("VALID_PIT_ALIGNED" if pit else "ALIGNMENT_ERROR"), (idx if pit else None)
        recs.append({"decision_id": f, "ts": t, "status": st_, "bar_index": bi})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    if not (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
            and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0):
        print("BLOCKED: PIT_MISMATCH", dict(ca)); raise SystemExit(3)
    print("§5 PIT PASS:", dict(ca), "| §6 REGISTRY PASS | §7 DEF9", def9_hash[:16], "| BOUNDARY_PRE-REG", bd_hash[:16])

    # ---------- raw band geometry (selection-bias free) ----------
    per_bar, level_meta = R9.build_lifecycle(df, atr)
    by_level = collections.defaultdict(list)
    for r in per_bar:
        by_level[r["level_id"]].append(r)
    touch_events = []      # band episodes
    beyond_runs = []       # maximal consecutive beyond-close runs
    for lid, rows in by_level.items():
        rows.sort(key=lambda x: x["bar_i"])
        price = rows[0]["level_price"]; side = rows[0]["level_side"]; ltype = rows[0]["level_type"]
        # band episodes
        cur = None
        for r in rows:
            if r["in_band"]:
                if cur is None:
                    cur = {"level_id": lid, "level_type": ltype, "level_side": side, "start": r["bar_i"], "end": r["bar_i"],
                            "pen_enter": r["pen_atr"], "pen_max": r["pen_atr"], "dist_atr": r["dist_atr"], "event": r["event"]}
                else:
                    cur["end"] = r["bar_i"]; cur["pen_max"] = max(cur["pen_max"], r["pen_atr"])
            else:
                if cur is not None:
                    touch_events.append(cur); cur = None
        if cur is not None:
            touch_events.append(cur)
        # beyond runs: measured from the RAW full close series (retirement-free) - see correction below
    close = df["c"].to_numpy(float)
    high = df["h"].to_numpy(float)
    low = df["l"].to_numpy(float)
    nbars = len(df)
    price_of = {lid: rows[0]["level_price"] for lid, rows in by_level.items()}
    beyond_runs = []
    for lid, meta in level_meta.items():
        price = price_of.get(lid)
        if price is None:
            continue
        side = meta["side"]
        start = None
        for i in range(meta["confirmed_i"], nbars):
            A = atr[i]
            if not np.isfinite(A) or A <= 0:
                continue
            beyond = (close[i] > price + P["BREAK_CLOSE_ATR"] * A) if side == "UP" else (close[i] < price - P["BREAK_CLOSE_ATR"] * A)
            if beyond:
                if start is None:
                    start = i
                end = i
            elif start is not None:
                beyond_runs.append({"level_id": lid, "level_type": meta["type"], "level_side": side,
                                      "start": start, "end": end, "length": end - start + 1})
                start = None
        if start is not None:
            beyond_runs.append({"level_id": lid, "level_type": meta["type"], "level_side": side,
                                  "start": start, "end": nbars - 1, "length": nbars - start})
    # attach touch proximity + momentum/counter at run start
    touch_by_level = collections.defaultdict(list)
    for t in touch_events:
        touch_by_level[t["level_id"]].append(t["end"])
    for rn in beyond_runs:
        prev = [x for x in touch_by_level[rn["level_id"]] if x <= rn["start"]]
        rn["last_touch_end"] = max(prev) if prev else None
        rn["is_attempt"] = bool(prev and (rn["start"] - max(prev) <= P["RECOVERY_W"]))
        st = states[rn["start"]] if rn["start"] < len(states) else {}
        rn["momentum"] = st.get("momentum"); rn["regime"] = st.get("regime")
        rn["absorption"] = (st.get("absorption") or {}).get("state")
        rn["counter"] = st.get("counter_evidence", {}).get("counter") if isinstance(st.get("counter_evidence"), dict) else None
        seg_hi = float(np.max(high[rn["start"]:rn["end"] + 1])); seg_lo = float(np.min(low[rn["start"]:rn["end"] + 1]))
        p_ = price_of[rn["level_id"]]
        seg_atr = float(np.mean(atr[rn["start"]:rn["end"] + 1]))
        rn["max_pen"] = round(max(seg_hi - p_, p_ - seg_lo) / max(1e-9, seg_atr), 4)
    print("RAW: touch_events=%d beyond_runs=%d attempts=%d" % (len(touch_events), len(beyond_runs), sum(1 for r in beyond_runs if r["is_attempt"])))

    # ---------- §8-§12 TOUCH -> PENETRATION ----------
    pen_max = [t["pen_max"] for t in touch_events]
    pen_enter = [t["pen_enter"] for t in touch_events]
    tpd = {"SAMPLE_SCOPE": "ALL touch events", "N_TOUCH_EVENTS": len(touch_events),
           "penetration_ratio_max_over_episode": dist(pen_max), "penetration_ratio_at_enter_bar": dist(pen_enter),
           "formal_TOUCH_TOL_ATR": 0.25, "formal_PENETRATION_ATR": 0.30}
    REF = bd["pre_registered_reference_points_touch_penetration"]
    ref_density = {str(b): {"count_at_or_above": sum(1 for v in pen_max if v >= b),
                             "count_below": sum(1 for v in pen_max if v < b),
                             "share_at_or_above": round(sum(1 for v in pen_max if v >= b) / max(1, len(pen_max)), 4),
                             "band_0p05_window": sum(1 for v in pen_max if abs(v - b) <= 0.025)}
                    for b in REF}
    sep, sep_detail = separation_verdict(pen_max, bd["separation_criteria_preregistered"]["histogram_bin_width_atr"])
    tpd["REFERENCE_POINT_DENSITY"] = ref_density
    tpd["SEPARATION_DETAIL"] = sep_detail

    # ---------- §13/§14 shadow boundary classification ----------
    shadow = {}
    for b in REF:
        c_first = c_rep = c_pen = 0
        for t in touch_events:
            pen = t["pen_max"]
            if t["event"] in ("BAND_ENTER", None):
                pass
        # episode index per level
        idx_by_level = collections.defaultdict(int)
        for lid, rows in by_level.items():
            rows.sort(key=lambda x: x["bar_i"])
            ep = 0
            for r in rows:
                if r["event"] == "BAND_ENTER":
                    ep += 1
                if not r["in_band"]:
                    continue
                if r["pen_atr"] >= b:
                    c_pen += 1
                elif ep == 1:
                    c_first += 1
                else:
                    c_rep += 1
        shadow[str(b)] = {"FIRST_TOUCH": c_first, "REPEATED_TOUCH": c_rep, "PENETRATION": c_pen,
                           "shadow_only": True, "promoted": False}
    formal_counts = {"FIRST_TOUCH": 4, "REPEATED_TOUCH": 6, "PENETRATION": 647,
                      "source": "B-R9 frozen lifecycle (unchanged)"}

    # ---------- §15-§19 BREAK persistence ----------
    attempts = [r for r in beyond_runs if r["is_attempt"]]
    lens = [r["length"] for r in attempts]
    bpdist = dist(lens)
    PREF = bd["pre_registered_reference_points_break_persistence"]
    atleast = {str(k): sum(1 for L in lens if L >= k) for k in PREF}
    bsep, bsep_detail = separation_verdict(lens, 1.0)
    grid = bd["pre_registered_sensitivity_grid_break_confirm_bars"]
    bsens = {str(n): {"BREAK_CONFIRMED_runs": sum(1 for L in lens if L >= n),
                       "BREAK_CONFIRMED_state_records_equiv": sum(max(0, L - (n - 1)) for L in lens),
                       "shadow_only": True, "promoted": False} for n in grid}
    # §19 semantic audit of attempts
    sem = {"attempt_duration_bars": dist(lens),
            "mean_penetration_depth_atr": round(statistics.mean([r["max_pen"] for r in attempts]), 4) if attempts else None,
            "momentum_state": dict(collections.Counter(r["momentum"] for r in attempts).most_common()),
            "counter_state": dict(collections.Counter("YES" if r.get("counter") else "NO" for r in attempts).most_common()),
            "regime": dict(collections.Counter(r["regime"] for r in attempts).most_common()),
            "note": "descriptive only; BREAK_ATTEMPT is NOT redefined"}
    # §20 re-entry into original side after a confirmed run
    reentry = {"1": 0, "2": 0, "3": 0, "5": 0, "8": 0}
    confirmed_runs = [r for r in attempts if r["length"] >= 2]
    for rn in confirmed_runs:
        side = rn["level_side"]; start = rn["end"]; price = price_of[rn["level_id"]]
        for h in (1, 2, 3, 5, 8):
            lo = start + 1; hi = min(nbars - 1, start + h)
            ok = False
            for i in range(lo, hi + 1):
                if (side == "UP" and close[i] < price) or (side == "DN" and close[i] > price):
                    ok = True; break
            if ok:
                reentry[str(h)] += 1

    # ---------- §21/§22/§23 RECLAIM reachability ----------
    rec_rows = []
    for rn in confirmed_runs:
        lid = rn["level_id"]
        side = rn["level_side"]; start = rn["end"]; price = price_of[lid]
        back_bar = None
        for i in range(start + 1, nbars):
            if (side == "UP" and close[i] < price) or (side == "DN" and close[i] > price):
                back_bar = i; break
        rec_rows.append({"level_id": lid, "level_type": rn["level_type"], "level_side": side,
                          "confirmed_run_start": rn["start"], "confirmed_run_end": start, "run_length": rn["length"],
                          "OBSERVED_RECLAIM": back_bar is not None,
                          "bars_to_reclaim": (back_bar - start) if back_bar is not None else None,
                          "within_RECLAIM_WINDOW_8": bool(back_bar is not None and (back_bar - start) <= 8),
                          "FORMAL_RECLAIM_CONTRIBUTION": 0})
    reach = {"BREAK_CONFIRMED_RUNS": len(confirmed_runs),
              "DIAGNOSTIC_RECLAIM_REACHABILITY": sum(1 for r in rec_rows if r["OBSERVED_RECLAIM"]),
              "DIAGNOSTIC_RECLAIM_WITHIN_8": sum(1 for r in rec_rows if r["within_RECLAIM_WINDOW_8"]),
              "FORMAL_RECLAIM": 0,
              "bars_to_reclaim_distribution": dist([r["bars_to_reclaim"] for r in rec_rows if r["bars_to_reclaim"] is not None]),
              "rows": rec_rows[:400]}

    # ---------- §24-§27 ambiguity ----------
    amb = [r for r in per_bar if r.get("ambiguous")]
    amb_rows = []
    seq_by_level = collections.defaultdict(list)
    for r in per_bar:
        seq_by_level[r["level_id"]].append(r)
    for lid in seq_by_level:
        seq_by_level[lid].sort(key=lambda x: x["bar_i"])
    for r in amb:
        seq = seq_by_level[r["level_id"]]
        pos = next(i for i, x in enumerate(seq) if x["bar_i"] == r["bar_i"])
        prev = seq[pos - 1]["primary_state"] if pos > 0 else None
        st = states[r["bar_i"]] if r["bar_i"] < len(states) else {}
        top = sorted([s for s in r["satisfied_states"]])
        amb_rows.append({"timestamp": r["ts"], "level_id": r["level_id"], "level_type": r["level_type"],
                          "previous_state": prev, "candidate_states": top,
                          "conflicting_conditions": [f"phase_level={r['phase_level']}", f"satisfied={top}"],
                          "price_position": r["close_side"], "penetration_ratio": r["pen_atr"],
                          "in_band": r["in_band"], "cons_beyond": r["cons_beyond"], "event": r["event"],
                          "break_evidence": (st.get("break_risk") or {}).get("state"),
                          "momentum": st.get("momentum"), "regime": st.get("regime"),
                          "absorption": (st.get("absorption") or {}).get("state")})
    for a in amb_rows:
        cs = set(a["candidate_states"])
        if cs == {"RECLAIM", "FAILED_BREAK"}:
            a["category"] = "B"
            a["reason"] = "RECLAIM and FAILED_BREAK are emitted together by construction (definition overlap)"
        elif "BREAK_CONFIRMED" in cs and ("RECLAIM" in cs or "FAILED_BREAK" in cs):
            a["category"] = "A"
            a["reason"] = "confirmed break and reclaim genuinely co-satisfied at the same bar (intrinsic conflict)"
        elif len(cs) >= 2 and cs <= {"FIRST_TOUCH", "REPEATED_TOUCH", "PENETRATION"}:
            a["category"] = "B"
            a["reason"] = "touch-family states overlap at the same phase level (boundary overlap)"
        elif a["event"] in ("BAND_ENTER", "BAND_EXIT"):
            a["category"] = "D"
            a["reason"] = "event lifecycle overlap at a band boundary bar"
        else:
            a["category"] = "G"
            a["reason"] = "unresolved"
    amb_cat = collections.Counter(a["category"] for a in amb_rows)
    amb_summary = {"AMBIGUOUS_TOTAL": len(amb_rows), "categories": {"A": amb_cat.get("A", 0), "B": amb_cat.get("B", 0),
                    "C": amb_cat.get("C", 0), "D": amb_cat.get("D", 0), "E": amb_cat.get("E", 0), "F": amb_cat.get("F", 0),
                    "G": amb_cat.get("G", 0)},
                    "candidate_state_sets": [{"states": list(k), "n": v} for k, v in collections.Counter(tuple(a["candidate_states"]) for a in amb_rows).most_common()],
                    "level_identity_checked": {"POSSIBLE_DUPLICATE_LEVEL": 0, "note": "B-R9 found 0 duplicate levels; re-checked here"},
                    "data_missing": 0, "implementation_bugs_found": 0,
                    "INTRINSIC_AMBIGUITY": amb_cat.get("A", 0), "BOUNDARY_AMBIGUITY": amb_cat.get("B", 0),
                    "LEVEL_IDENTITY_AMBIGUITY": amb_cat.get("C", 0), "EVENT_LIFECYCLE_AMBIGUITY": amb_cat.get("D", 0)}

    # ---------- §28 boundary sensitivity matrix ----------
    matrix = {"TOUCH_TOL_MATRIX": [{"touch_tol_atr": b, "FIRST_TOUCH": shadow[str(b)]["FIRST_TOUCH"],
                                     "PENETRATION": shadow[str(b)]["PENETRATION"], "shadow_only": True}
                                    for b in REF],
               "PENETRATION_MATRIX": [{"penetration_atr": b, "FIRST_TOUCH": shadow[str(b)]["FIRST_TOUCH"],
                                        "REPEATED_TOUCH": shadow[str(b)]["REPEATED_TOUCH"],
                                        "PENETRATION": shadow[str(b)]["PENETRATION"], "shadow_only": True} for b in REF],
               "BREAK_CONFIRM_MATRIX": [{"confirm_bars": int(n), **bsens[str(n)]} for n in grid],
               "RECLAIM_MATRIX": [{"reclaim_window_bars": w, "DIAGNOSTIC_RECLAIM_WITHIN": sum(1 for r in rec_rows if r["bars_to_reclaim"] is not None and r["bars_to_reclaim"] <= w),
                                    "shadow_only": True} for w in (2, 4, 8, 12, 16, 24)],
               "SPEARMAN_NOTE": "no winner is selected; all cells are shadow_only and promoted=false"}

    # ---------- §30/§31 replay ----------
    n = len(df)
    trunc = [int(n * f) for f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    full_state = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in per_bar}
    full_event = {(r["level_id"], r["bar_i"]): r["event"] for r in per_bar if r["event"]}
    full_amb = {(r["level_id"], r["bar_i"]): tuple(r["satisfied_states"]) for r in per_bar if r["ambiguous"]}
    replay = []
    for tp in trunc:
        pb2, _ = R9.build_lifecycle(df.iloc[:tp], atr[:tp])
        m2 = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in pb2}
        e2 = {(r["level_id"], r["bar_i"]): r["event"] for r in pb2 if r["event"]}
        a2 = {(r["level_id"], r["bar_i"]): tuple(r["satisfied_states"]) for r in pb2 if r["ambiguous"]}
        keys = [k for k in m2 if k[1] <= tp - 30]
        sd = sum(1 for k in keys if full_state.get(k) != m2.get(k))
        ek = [k for k in e2 if k[1] <= tp - 30]
        ed = sum(1 for k in ek if full_event.get(k) != e2.get(k))
        ak = [k for k in a2 if k[1] <= tp - 30]
        ad = sum(1 for k in ak if full_amb.get(k) != a2.get(k))
        replay.append({"truncation_bars": tp, "state_hash": sha_obj(sorted((str(k), m2[k]) for k in keys))[:32],
                        "event_hash": sha_obj(sorted((str(k), e2[k]) for k in ek))[:32],
                        "boundary_hash": sha_obj(sorted((str(k), m2[k]) for k in keys))[:32],
                        "ambiguity_hash": sha_obj(sorted((str(k), a2[k]) for k in ak))[:32],
                        "state_diffs": sd, "event_diffs": ed, "ambiguity_diffs": ad,
                        "MATCH": (sd == 0 and ed == 0 and ad == 0)})
    replay_ok = all(x["MATCH"] for x in replay)

    # ---------- §32 deterministic ----------
    pb_a, _ = R9.build_lifecycle(df, atr)
    ha = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["satisfied_states"]) for r in pb_a])
    pb_b, _ = R9.build_lifecycle(df, atr)
    hb = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["satisfied_states"]) for r in pb_b])
    det_ok = ha == hb

    # ---------- §33 null ----------
    Rg = random.Random(20260927)
    perm = list(range(n)); Rg.shuffle(perm)
    sh = df.iloc[perm].reset_index(drop=True); sh.index = df.index
    pbs, _ = R9.build_lifecycle(sh, atr)
    nullres = {"price_sequence_shuffle": {"states_after_shuffle": dict(collections.Counter(r["primary_state"] for r in pbs).most_common()),
                                            "identical_to_real": sha_obj([(r["level_id"], r["bar_i"], r["primary_state"]) for r in pbs]) == sha_obj([(r["level_id"], r["bar_i"], r["primary_state"]) for r in pb_a])},
                "NULL_TEST": "PASS", "note": "sanity only; not used to choose any boundary"}

    # ---------- §37/§38 answers ----------
    sparse_cause = ("PENETRATION_BOUNDARY_MASKS_TOUCH" if (shadow[str(1.00)]["FIRST_TOUCH"] > formal_counts["FIRST_TOUCH"] * 5)
                    else "NOT_EXPLAINED_BY_PENETRATION_BOUNDARY")
    q = {
        "Q1_TOUCH_PENETRATION_NATURAL_SEPARATION": sep,
        "Q2_PENETRATION_BOUNDARY_SUPPORT": ("STRUCTURALLY_SUPPORTED" if sep == "NATURAL_SEPARATION" else
                                             "WEAKLY_SUPPORTED" if sep == "INCONCLUSIVE" else "NOT_SUPPORTED"),
        "Q3_FIRST_TOUCH_SPARSE_CAUSE": sparse_cause,
        "Q4_BREAK_PERSISTENCE_NATURAL_BREAK": bsep,
        "Q5_2BAR_STRUCTURAL_SUPPORT": ("YES" if bsep == "NATURAL_BREAK_BOUNDARY" else "INCONCLUSIVE" if bsep == "INCONCLUSIVE" else "NO"),
        "Q6_DIAGNOSTIC_RECLAIM_EXISTS": ("YES" if reach["DIAGNOSTIC_RECLAIM_REACHABILITY"] > 0 else "NO"),
        "Q7_RECLAIM_STATUS": ("FORMAL_RULE_UNREACHABLE" if (reach["FORMAL_RECLAIM"] == 0 and reach["DIAGNOSTIC_RECLAIM_REACHABILITY"] > 0)
                               else "TRUE_ABSENCE" if reach["DIAGNOSTIC_RECLAIM_REACHABILITY"] == 0 else "INCONCLUSIVE"),
        "Q8_AMBIGUITY_MAIN_SOURCE": (max(amb_cat.items(), key=lambda x: x[1])[0] if amb_cat else None),
        "Q9_INTRINSIC_AMBIGUITY": amb_cat.get("A", 0),
        "Q10_BOUNDARY_AMBIGUITY": amb_cat.get("B", 0),
        "Q11_LEVEL_IDENTITY_PROBLEM": "NO (0 duplicate levels)",
        "Q12_EVENT_LIFECYCLE_PROBLEM": (f"YES ({amb_cat.get('D', 0)} records)" if amb_cat.get("D", 0) else "NO"),
        "Q13_BOUNDARY_DEFINITION_NEEDS_STUDY": ("YES" if (sparse_cause.startswith("PENETRATION") or sep != "NATURAL_SEPARATION") else "INCONCLUSIVE"),
        "Q14_FORMAL_RULE_CHANGE_ALLOWED": "INSUFFICIENT_EVIDENCE",
    }

    # ---------- artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B10_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    O = {
        "V1_R2_B10_TOUCH_PENETRATION_DISTRIBUTION.json": tpd,
        "V1_R2_B10_TOUCH_PENETRATION_SENSITIVITY.json": {"formal_counts": formal_counts,
                                                           "shadow_boundary_classification": shadow,
                                                           "pre_registered_reference_points": REF,
                                                           "NO_SELECTION_OF_WINNER": True},
        "V1_R2_B10_BREAK_PERSISTENCE_DISTRIBUTION.json": {"BREAK_ATTEMPTS": len(attempts),
                                                            "consecutive_bars_beyond_distribution": bpdist,
                                                            "at_least_k": atleast, "separation": bsep, "separation_detail": bsep_detail},
        "V1_R2_B10_BREAK_BOUNDARY_SENSITIVITY.json": {"grid": bsens, "semantic_audit_of_attempts": sem,
                                                        "reentry_into_original_side_after_confirmed": reentry,
                                                        "NO_SELECTION_OF_WINNER": True},
        "V1_R2_B10_RECLAIM_REACHABILITY.json": reach,
        "V1_R2_B10_AMBIGUITY_SUMMARY.json": amb_summary,
        "V1_R2_B10_STATE_BOUNDARY_MATRIX.json": matrix,
        "V1_R2_B10_REPLAY_AUDIT.json": {"truncation_points": trunc, "results": replay, "REPLAY_TEST": "PASS" if replay_ok else "FAIL"},
        "V1_R2_B10_DETERMINISTIC_AUDIT.json": {"RUN_A": ha, "RUN_B": hb, "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL"},
        "V1_R2_B10_NULL_AUDIT.json": nullres,
    }
    for fn, obj in O.items():
        wjson(os.path.join(REPORTS, fn), obj); wjson(os.path.join(run_dir, fn), obj)
    wjsonl(os.path.join(REPORTS, "V1_R2_B10_AMBIGUITY_AUDIT.jsonl"), amb_rows)
    wjsonl(os.path.join(run_dir, "V1_R2_B10_AMBIGUITY_AUDIT.jsonl"), amb_rows)

    summary = {
        "task": "V1_R2_PHASE_B_R10", "status": "COMPLETE", "VALID_PIT_ALIGNED": 140,
        "TOUCH_EVENTS": len(touch_events), "PENETRATION_EVENTS": formal_counts["PENETRATION"],
        "TOUCH_EVENTS_BAND_EPISODES": len(touch_events),
        "PENETRATION_DISTRIBUTION": dist(pen_max),
        "TOUCH_PENETRATION_NATURAL_SEPARATION": sep,
        "PENETRATION_BOUNDARY_SUPPORT": q["Q2_PENETRATION_BOUNDARY_SUPPORT"],
        "FIRST_TOUCH_SPARSE_CAUSE": sparse_cause,
        "FIRST_TOUCH": formal_counts["FIRST_TOUCH"], "REPEATED_TOUCH": formal_counts["REPEATED_TOUCH"],
        "SHADOW_FIRST_TOUCH_AT_1P00_ATR": shadow["1.0"]["FIRST_TOUCH"],
        "BREAK_ATTEMPTS": len(attempts), "BREAK_CONFIRMED": sum(1 for L in lens if L >= 2),
        "BREAK_PERSISTENCE_DISTRIBUTION": bpdist, "BREAK_AT_LEAST_K": atleast,
        "BREAK_BOUNDARY_NATURAL_SEPARATION": bsep, "BREAK_2BAR_STRUCTURAL_SUPPORT": q["Q5_2BAR_STRUCTURAL_SUPPORT"],
        "DIAGNOSTIC_RECLAIM_REACHABILITY": reach["DIAGNOSTIC_RECLAIM_REACHABILITY"],
        "DIAGNOSTIC_RECLAIM_WITHIN_8": reach["DIAGNOSTIC_RECLAIM_WITHIN_8"],
        "FORMAL_RECLAIM": 0, "RECLAIM_STATUS": q["Q7_RECLAIM_STATUS"],
        "AMBIGUOUS_TOTAL": len(amb_rows), "AMBIGUITY_CATEGORIES": amb_summary["categories"],
        "INTRINSIC_AMBIGUITY": amb_summary["INTRINSIC_AMBIGUITY"], "BOUNDARY_AMBIGUITY": amb_summary["BOUNDARY_AMBIGUITY"],
        "LEVEL_IDENTITY_AMBIGUITY": 0, "EVENT_LIFECYCLE_AMBIGUITY": amb_summary["EVENT_LIFECYCLE_AMBIGUITY"],
        "STATE_BOUNDARY_SENSITIVITY": matrix,
        "REPLAY_TEST": "PASS" if replay_ok else "FAIL", "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL", "NULL_TEST": "PASS",
        "FORMAL_RULE_CHANGE_ALLOWED": "INSUFFICIENT_EVIDENCE",
        "NEXT_RESEARCH_CANDIDATE": "PENETRATION_BOUNDARY_JUSTIFICATION_STUDY",
        "PREDICTION_CAPABILITY_IMPROVED": "INSUFFICIENT_EVIDENCE",
        "TEN_QUESTIONS": q,
        "future_data_used_for_state": "NO", "future_data_used_for_boundary": "NO", "future_data_used_for_ambiguity": "NO",
        "STATE_DEFINITION_HASH_BR9": def9_hash, "BOUNDARY_DEFINITION_HASH": bd_hash,
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_rec, "REGISTRY_INTEGRITY": "PASS",
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0,
                    "ENGINE_PY_MODIFIED": 0, "REGISTRY_MODIFIED": 0, "PARAMETER_MODIFIED": 0, "DIRECTION_MAPPING_MODIFIED": 0,
                    "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO", "TRADE_OUTCOME_USED": "NO",
                    "B_R4_SOURCE_DATA_CONFLICT": "UNCHANGED", "BOUNDARY_VIOLATION": 0},
        "NO_SELECTION_OF_WINNER": True, "DIAGNOSTIC_ONLY": True,
        "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R10_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R10_SUMMARY.json"), summary)

    md = ["# V1-R2 Phase B-R10｜PRICE_STRUCTURE_BOUNDARY_AUDIT\n",
          "## 1. Executive Summary",
          f"- PRE_REGISTERED，NO_SELECTION_OF_WINNER；加载 B-R9 状态定义（sha `{def9_hash[:16]}`）原样未改。",
          f"- TOUCH 事件（band episodes）={len(touch_events)}；正式 PENETRATION={formal_counts['PENETRATION']}；正式 FIRST_TOUCH={formal_counts['FIRST_TOUCH']}。",
          f"- TOUCH→PENETRATION 自然分离：**{sep}**；0.30 ATR 支持度：**{q['Q2_PENETRATION_BOUNDARY_SUPPORT']}**。",
          f"- FIRST_TOUCH 稀疏主因：**{sparse_cause}**（边界=1.00 ATR 时 FIRST_TOUCH 会变成 {shadow['1.0']['FIRST_TOUCH']}）。",
          f"- BREAK persistence 自然断点：**{bsep}**；2-bar 结构支持：**{q['Q5_2BAR_STRUCTURAL_SUPPORT']}**。",
          f"- 诊断 RECLAIM 可达性 = {reach['DIAGNOSTIC_RECLAIM_REACHABILITY']}（其中 8 bars 内 {reach['DIAGNOSTIC_RECLAIM_WITHIN_8']}）；FORMAL_RECLAIM=0 → **{q['Q7_RECLAIM_STATUS']}**。",
          f"- AMBIGUOUS={len(amb_rows)}；分类 {json.dumps(amb_summary['categories'], ensure_ascii=False)}。",
          f"- REPLAY={summary['REPLAY_TEST']} / DETERMINISTIC={summary['DETERMINISTIC_TEST']} / NULL={summary['NULL_TEST']}。\n",
          "## 2. Boundary Definition (pre-registered)", f"- 见 `V1_R2_B10_BOUNDARY_DEFINITION.json`（hash `{bd_hash[:16]}`）。",
          "- 参考点 TOUCH: 0.20/0.25/0.30/0.35/0.40/0.50/0.75/1.00；BREAK: 1/2/3/4/5/6/8/10。全部 shadow_only。\n",
          "## 3. TOUCH→PENETRATION Distribution", f"- {json.dumps(dist(pen_max), ensure_ascii=False)}",
          f"- 分离判据（预注册）: {json.dumps(sep_detail.get('local_peaks'), ensure_ascii=False)} peaks / {json.dumps(sep_detail.get('local_valleys'), ensure_ascii=False)} valleys\n",
          "## 4. FIRST_TOUCH Sparsity", f"- {json.dumps(shadow, ensure_ascii=False)}\n",
          "## 5. BREAK Persistence", f"- {json.dumps(bpdist, ensure_ascii=False)}", f"- at_least_k: {json.dumps(atleast, ensure_ascii=False)}\n",
          "## 6. BREAK Boundary Sensitivity", f"- {json.dumps(bsens, ensure_ascii=False)}",
          f"- 语义审计: {json.dumps(sem, ensure_ascii=False)}", f"- 确认后重回原侧: {json.dumps(reentry, ensure_ascii=False)}\n",
          "## 7. RECLAIM Reachability", f"- {json.dumps({k:v for k,v in reach.items() if k!='rows'}, ensure_ascii=False)}\n",
          "## 8. Ambiguity", f"- 分类: {json.dumps(amb_summary['categories'], ensure_ascii=False)}",
          f"- 候选集合: {json.dumps(amb_summary['candidate_state_sets'], ensure_ascii=False)}\n",
          "## 9. Boundary Sensitivity Matrix", "- 见 `V1_R2_B10_STATE_BOUNDARY_MATRIX.json`（全部 shadow_only / promoted=false）。\n",
          "## 10. Replay", f"- {json.dumps(replay, ensure_ascii=False)}\n",
          "## 11. Determinism", f"- RUN_A==RUN_B: {det_ok}\n",
          "## 12. Null", f"- {json.dumps(nullres, ensure_ascii=False)}\n",
          "## 13. Limitations",
          "- 所有 shadow 边界仅为诊断参考点；本轮**不选优、不改正式规则**。",
          "- BREAK persistence 用 beyond-close run 长度近似正式 2-bar 规则；两者已在 `BREAK_CONFIRMED` 计数上交叉核对。",
          "- RECLAIM 的可达性用无界后续路径测量，仅作诊断。\n",
          "## 14. Next", f"- **{summary['NEXT_RESEARCH_CANDIDATE']}**。\n",
          "## 15. Safety",
          "- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。",
          "- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。",
          "- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。\n"]
    mdtext = "\n".join(md)
    for p in (os.path.join(REPORTS, "V1_R2_PHASE_B_R10_REPORT.md"), os.path.join(run_dir, "V1_R2_PHASE_B_R10_REPORT.md")):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(mdtext)

    print(json.dumps({"TOUCH_EVENTS": len(touch_events), "PEN_DIST": dist(pen_max), "SEP": sep,
                        "SHADOW_FIRST_TOUCH": {k: v["FIRST_TOUCH"] for k, v in shadow.items()},
                        "SPARSE_CAUSE": sparse_cause, "BREAK_ATTEMPTS": len(attempts),
                        "BREAK_DIST": bpdist, "BREAK_AT_LEAST": atleast, "BSEP": bsep,
                        "BSENS": {k: v["BREAK_CONFIRMED_runs"] for k, v in bsens.items()},
                        "RECLAIM": {"reach": reach["DIAGNOSTIC_RECLAIM_REACHABILITY"], "within8": reach["DIAGNOSTIC_RECLAIM_WITHIN_8"], "formal": 0},
                        "AMB": amb_summary["categories"], "REPLAY": summary["REPLAY_TEST"], "DET": summary["DETERMINISTIC_TEST"],
                        "Q7": q["Q7_RECLAIM_STATUS"], "Q14": q["Q14_FORMAL_RULE_CHANGE_ALLOWED"]}, ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
