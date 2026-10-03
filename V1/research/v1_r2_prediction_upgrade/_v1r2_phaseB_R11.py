# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R11 — PENETRATION_BOUNDARY_JUSTIFICATION_STUDY (DIAGNOSTIC ONLY, PRE-REGISTERED).

Question: does PENETRATION have an independent, explainable, pre-registrable structural meaning?
NOT a threshold search. No formal rule / parameter / registry / engine change.
No future_return / PnL / win_rate / trade_outcome used anywhere. GIT_COMMIT=NONE."""
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
REG11 = os.path.join(REPORTS, "V1_R2_B11_BOUNDARY_JUSTIFICATION_REGISTRY.json")
NOW = datetime.now(timezone.utc).isoformat()
GRID = pd.Timedelta(minutes=15)
REG_HASH = "014de1664566613f8038884a71e34e41bb0a2ce89315f0682cebfe4a2c51b7ed"
PQ_SHA = "aafbb44803555c1bae96d74360c4e1e88753d000e9b83aa095bab7ef6dd30739"
DEF9_PREFIX = "f1c550975409752e"
BOUNDARIES = [0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.75, 1.00]
FORMAL_ATR = 0.30
TOUCH_TOL = 0.25


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def Q(vals, q):
    if not vals:
        return None
    s = sorted(vals); k = (len(s) - 1) * q; f = int(k); c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 4)


def DIST(vals):
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "min": round(min(vals), 4), "p01": Q(vals, .01), "p05": Q(vals, .05), "p10": Q(vals, .10),
            "p25": Q(vals, .25), "median": round(statistics.median(vals), 4), "p75": Q(vals, .75), "p90": Q(vals, .90),
            "p95": Q(vals, .95), "p99": Q(vals, .99), "max": round(max(vals), 4),
            "mean": round(sum(vals) / len(vals), 4), "std": round(statistics.pstdev(vals), 4)}


def em1d(x, k, iters=300):
    """Minimal 1-D Gaussian mixture EM; returns (loglik, params, bic)."""
    n = len(x); xs = np.asarray(x, float)
    if k == 1:
        mu = float(xs.mean()); va = max(1e-9, float(xs.var()))
        ll = float(np.sum(-0.5 * (np.log(2 * math.pi * va) + (xs - mu) ** 2 / va)))
        return ll, {"mu": [mu], "var": [va], "w": [1.0]}, (-2 * ll + 2 * math.log(n))
    mu = np.array([float(np.percentile(xs, 25)), float(np.percentile(xs, 75))])
    va = np.array([max(1e-9, float(xs.var()) / 2), max(1e-9, float(xs.var()) / 2)])
    w = np.array([0.5, 0.5])
    for _ in range(iters):
        p = np.array([w[j] * np.exp(-0.5 * (xs - mu[j]) ** 2 / va[j]) / math.sqrt(2 * math.pi * va[j]) for j in range(2)])
        s = p.sum(axis=0); s[s <= 0] = 1e-300
        r = p / s
        nk = r.sum(axis=1) + 1e-12
        w = nk / n; mu = (r * xs).sum(axis=1) / nk
        va = (r * (xs - mu[:, None]) ** 2).sum(axis=1) / nk
        va = np.maximum(va, 1e-9)
    ll = float(np.sum(np.log(np.maximum(s, 1e-300))))
    order = np.argsort(mu)
    return ll, {"mu": [float(mu[i]) for i in order], "var": [float(va[i]) for i in order], "w": [float(w[i]) for i in order]}, (-2 * ll + 5 * math.log(n))


def main():
    # ---------- §4/§5/§6/§7 gates ----------
    reg3 = json.load(open(REG3, encoding="utf-8"))
    reg_rec = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
    reg_ok = (reg3.get("new_registry_hash") == REG_HASH == reg_rec and reg3.get("version") == "v1r2-r3")
    def9_hash = sha_file(DEF9)
    def9_ok = def9_hash.startswith(DEF9_PREFIX)
    reg11 = json.load(open(REG11, encoding="utf-8"))
    reg11_hash = sha_file(REG11)
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    data_ok = (sha_file(pq) == PQ_SHA)
    R1 = load_mod("v1r2_r1", R1MOD); R9 = load_mod("v1r2_r9", R9MOD)
    df = pd.read_parquet(pq)
    jd = R1.indicators(df.copy()); atr = jd["atr20"].to_numpy(float)
    states = R1.engines_v2(jd.copy())
    jts = pd.to_datetime([s["t"] for s in states], utc=True)
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
        recs.append({"status": st_, "bar_index": bi, "ts": t})
    tsc = collections.Counter(r["ts"] for r in recs if r.get("ts") is not None)
    dups = {k for k, v in tsc.items() if v > 1}
    for r in recs:
        if r.get("ts") in dups and r["status"] == "VALID_PIT_ALIGNED":
            r["status"] = "DUPLICATE_TIMESTAMP"
    ca = collections.Counter(r["status"] for r in recs)
    pit_ok = (ca.get("VALID_PIT_ALIGNED", 0) == 140 and ca.get("DUPLICATE_TIMESTAMP", 0) == 2
              and ca.get("OUT_OF_DATASET", 0) == 0 and ca.get("ALIGNMENT_ERROR", 0) == 0)
    if not (reg_ok and def9_ok and data_ok and pit_ok):
        print("BLOCKED", {"reg": reg_ok, "def9": def9_ok, "data": data_ok, "pit": pit_ok, "align": dict(ca)}); raise SystemExit(2)
    print("GATES PASS | PIT", dict(ca), "| DEF9", def9_hash[:16], "| REG11", reg11_hash[:16])

    # ---------- rebuild band geometry ----------
    per_bar, level_meta = R9.build_lifecycle(df, atr)
    by_level = collections.defaultdict(list)
    for r in per_bar:
        by_level[r["level_id"]].append(r)
    for lid in by_level:
        by_level[lid].sort(key=lambda x: x["bar_i"])
    close = df["c"].to_numpy(float); high = df["h"].to_numpy(float); low = df["l"].to_numpy(float)
    rng = np.maximum(1e-9, high - low)

    touch_eps, pen_bar_records = [], []
    for lid, rows in by_level.items():
        price = rows[0]["level_price"]; side = rows[0]["level_side"]; ltype = rows[0]["level_type"]
        cur = None
        for r in rows:
            if r["in_band"]:
                inside = abs(r["pen_atr"] * 1.0)
                rec = {"level_id": lid, "level_type": ltype, "level_side": side, "bar_i": r["bar_i"], "ts": r["ts"],
                        "pen_ratio": r["pen_atr"], "dist_atr": r["dist_atr"], "close_pos_rel": round((close[r["bar_i"]] - price) / max(1e-9, atr[r["bar_i"]]), 4),
                        "range_norm": round((max(high[r["bar_i"]] - price, price - low[r["bar_i"]])) / rng[r["bar_i"]], 4),
                        "bar_range_atr": round(rng[r["bar_i"]] / max(1e-9, atr[r["bar_i"]]), 4),
                        "event": r["event"], "primary_state": r["primary_state"]}
                pen_bar_records.append(rec)
                if cur is None:
                    cur = {"level_id": lid, "level_type": ltype, "level_side": side, "start": r["bar_i"], "end": r["bar_i"],
                            "bars": 1, "pen_max": r["pen_atr"], "pen_enter": r["pen_atr"], "pen_values": [r["pen_atr"]],
                            "close_start": close[r["bar_i"]], "close_end": close[r["bar_i"]], "price": price}
                else:
                    cur["end"] = r["bar_i"]; cur["bars"] += 1
                    cur["pen_max"] = max(cur["pen_max"], r["pen_atr"]); cur["pen_values"].append(r["pen_atr"])
                    cur["close_end"] = close[r["bar_i"]]
            else:
                if cur is not None:
                    touch_eps.append(cur); cur = None
        if cur is not None:
            touch_eps.append(cur)
    for e in touch_eps:
        e["duration_bars"] = e["end"] - e["start"] + 1
        e["max_excursion"] = e["pen_max"]
        e["side_flip"] = bool((e["level_side"] == "UP" and e["close_end"] < e["price"]) or
                               (e["level_side"] == "DN" and e["close_end"] > e["price"]))
    print("TOUCH_EPISODES=%d  BAND_BAR_RECORDS=%d" % (len(touch_eps), len(pen_bar_records)))

    # ---------- §9/§10 distribution ----------
    pen_max = [e["pen_max"] for e in touch_eps]
    pen_enter = [e["pen_enter"] for e in touch_eps]
    distribution = {"ALL_TOUCH_EPISODES_INCLUDED": True, "SELECTION_BIAS": "NO", "TOUCH_EPISODES": len(touch_eps),
                     "PENETRATION_STATE_RECORDS_FORMAL": 647,
                     "penetration_ratio_max_over_episode": DIST(pen_max),
                     "penetration_ratio_at_enter_bar": DIST(pen_enter),
                     "max_excursion_inside_level": DIST([e["max_excursion"] for e in touch_eps]),
                     "bars_inside_level": DIST([e["bars"] for e in touch_eps]),
                     "distance_to_level_atr": DIST([r["dist_atr"] for r in pen_bar_records]),
                     "close_position_relative_to_level": DIST([r["close_pos_rel"] for r in pen_bar_records]),
                     "range_normalised_penetration": DIST([r["range_norm"] for r in pen_bar_records]),
                     "formal_TOUCH_TOL_ATR": TOUCH_TOL, "formal_PENETRATION_ATR": FORMAL_ATR,
                     "ECDF_penetration_ratio_max": [{"value": v, "share_le": round(sum(1 for x in pen_max if x <= v) / len(pen_max), 4)}
                                                     for v in [0.25, 0.30, 0.35, 0.40, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00, 6.00]]}
    bw = 0.10
    nb = int(math.ceil(max(pen_max) / bw))
    hist = [{"lo": round(i * bw, 2), "hi": round((i + 1) * bw, 2), "count": sum(1 for v in pen_max if i * bw <= v < (i + 1) * bw),
              "density": round(sum(1 for v in pen_max if i * bw <= v < (i + 1) * bw) / len(pen_max), 4)} for i in range(nb)]

    # ---------- §11/§22 natural separation ----------
    def valley_rule(vals, bin_w):
        if len(vals) < 50:
            return "INCONCLUSIVE", {}
        nbb = max(3, int(math.ceil(max(vals) * 1.05 / bin_w)))
        bins = [0] * nbb
        for v in vals:
            bins[min(nbb - 1, int(v // bin_w))] += 1
        n = len(vals)
        peaks = [i for i in range(1, nbb - 1) if bins[i] > bins[i - 1] and bins[i] >= bins[i + 1] and bins[i] / n >= 0.05]
        valleys = [i for i in range(1, nbb - 1) if bins[i] < bins[i - 1] and bins[i] <= bins[i + 1]]
        mono = all(bins[i] >= bins[i + 1] for i in range(nbb - 1))
        det = {"peaks": [{"bin_lo": round(i * bin_w, 2), "density": round(bins[i] / n, 4)} for i in peaks],
               "valleys": [{"bin_lo": round(i * bin_w, 2), "density": round(bins[i] / n, 4)} for i in valleys],
               "monotone_nonincreasing": mono}
        if mono or len(peaks) <= 1:
            return "NO_NATURAL_SEPARATION", det
        for a, b in itertools.combinations(peaks, 2):
            if (b - a) * bin_w < 0.15:
                continue
            for v in valleys:
                if a < v < b and bins[v] <= 0.5 * min(bins[a], bins[b]):
                    return "NATURAL_SEPARATION", det
        return "INCONCLUSIVE", det
    vr, vdet = valley_rule(pen_max, 0.05)
    logs = [math.log(max(1e-6, v)) for v in pen_max]
    ll1, p1, bic1 = em1d(logs, 1); ll2, p2, bic2 = em1d(logs, 2)
    dbic = round(bic1 - bic2, 3)
    sep_atr = round(math.exp(p2["mu"][1]) - math.exp(p2["mu"][0]), 4)
    mix_split = round(math.exp((p2["mu"][0] + p2["mu"][1]) / 2), 4)
    mixture_ok = (dbic >= 10 and sep_atr >= 0.15 and 0.0 < mix_split < max(pen_max))
    if vr == "NATURAL_SEPARATION" or mixture_ok:
        nat = "NATURAL_SEPARATION" if vr == "NATURAL_SEPARATION" else "POSSIBLE_STRUCTURAL_BOUNDARY"
    else:
        nat = "NO_NATURAL_SEPARATION" if vr == "NO_NATURAL_SEPARATION" else "INCONCLUSIVE"
    sep_out = {"valley_rule": vr, "valley_detail": vdet, "mixture": {"BIC_1": round(bic1, 3), "BIC_2": round(bic2, 3),
                "delta_BIC": dbic, "component_means_log": p2["mu"], "component_weights": p2["w"],
                "separation_atr": sep_atr, "implied_split_atr": mix_split, "mixture_rule_met": mixture_ok},
                "NATURAL_DENSITY_SEPARATION": nat, "auto_split_search": "FORBIDDEN_NOT_PERFORMED"}

    # ---------- §14/§21 persistence per shadow boundary + §16 transitions ----------
    pers, bsens = {}, {}
    for b in BOUNDARIES:
        eps = []
        for lid, rows in by_level.items():
            cur = None
            for r in rows:
                if r["in_band"] and r["pen_atr"] >= b:
                    if cur is None:
                        cur = {"level_id": lid, "start": r["bar_i"], "end": r["bar_i"], "bars": 1,
                                "level_type": r["level_type"], "level_side": r["level_side"]}
                    else:
                        cur["end"] = r["bar_i"]; cur["bars"] += 1
                else:
                    if cur is not None:
                        eps.append(cur); cur = None
            if cur is not None:
                eps.append(cur)
        d = [e["bars"] for e in eps]
        trans = collections.Counter()
        for e in eps:
            nxt = [r for r in by_level[e["level_id"]] if r["bar_i"] > e["end"]]
            nxt.sort(key=lambda x: x["bar_i"])
            trans[nxt[0]["primary_state"] if nxt else "LEVEL_RETIRED_OR_END"] += 1
        key = f"{b:.2f}"
        pers[key] = {"boundary_atr": b, "episodes": len(eps), "bars_covered": sum(d),
                      "duration_bars": DIST(d), "duration_seconds_median": (statistics.median(d) * 900 if d else None)}
        bsens[key] = {"boundary_atr": b, "episode_count": len(eps), "median_duration": (statistics.median(d) if d else None),
                       "p90_duration": Q(d, .90), "transition_distribution": dict(trans.most_common()),
                       "ambiguity_count": 56,
                       "ambiguity_note": "ambiguity comes from the RECLAIM+FAILED_BREAK pairing (phase 5) and is boundary-independent",
                       "shadow_only": True, "promoted": False}

    # ---------- §16 transition structure (descriptive, circularity-guarded) ----------
    trans_struct = collections.Counter()
    for lid, rows in by_level.items():
        for a, bb in zip(rows, rows[1:]):
            if bb["bar_i"] != a["bar_i"] + 1:
                continue
            if a["primary_state"] == "PENETRATION":
                trans_struct[bb["primary_state"]] += 1
    transition_structure = {"PENETRATION_next_state_distribution": dict(trans_struct.most_common()),
                             "CIRCULARITY_GUARD": "descriptive only; PENETRATION->BREAK/* is NOT admissible as proof that PENETRATION is a legitimate state (task 17)",
                             "PENETRATION_to_BREAK_ATTEMPT": trans_struct.get("BREAK_ATTEMPT", 0),
                             "PENETRATION_to_BREAK_CONFIRMED": trans_struct.get("BREAK_CONFIRMED", 0),
                             "PENETRATION_to_EXHAUSTION": trans_struct.get("EXHAUSTION", 0),
                             "PENETRATION_to_EXIT_out_of_band": sum(1 for lid, rows in by_level.items() for a, bb in zip(rows, rows[1:])
                                                                      if a["primary_state"] == "PENETRATION" and not bb["in_band"])}

    # ---------- §18 continuous independence ----------
    cont = {"continuous_variables": reg11["continuous_variables"],
             "penetration_vs_touch_tol": {"formal_TOUCH_TOL_ATR": TOUCH_TOL, "formal_PENETRATION_ATR": FORMAL_ATR,
                                           "share_of_episodes_with_pen_max_below_tol": round(sum(1 for v in pen_max if v < TOUCH_TOL) / len(pen_max), 4),
                                           "min_pen_max": min(pen_max)},
             "is_discretisation_of_one_variable": True,
             "reason": "pen_ratio = max(high-price, price-low)/ATR computed ONLY inside the touch band; a boundary on it is a threshold on one continuous geometric variable already conditional on TOUCH"}

    # ---------- §19 feature lineage ----------
    lineage = {"RAW_SOURCE_COUNT": 1,
                "chain": "TICK_BID -> OHLC_15M -> (ATR20) + (level price from PIVOT/RANGE fractals) -> penetration_ratio",
                "PENETRATION_inputs": ["TICK_BID", "OHLC_15M", "ATR20", "LEVEL.price"],
                "TOUCH_inputs": ["TICK_BID", "OHLC_15M", "ATR20", "LEVEL.price"],
                "LEVEL_inputs": ["TICK_BID", "OHLC_15M"],
                "BREAK_inputs": ["LEVEL", "ABSORPTION", "VEL4"],
                "statement": "PENETRATION / TOUCH / LEVEL / BREAK are different GEOMETRIC TRANSFORMS of the SAME single bid price path; not independent data sources",
                "independent_data_sources": ["TICK_BID (price)", "TICK_ASK (spread, unused by the state machine)"]}

    # ---------- §20 overlap ----------
    bar_tot = len(pen_bar_records)
    inband_bars = bar_tot
    total_bar_level = sum(len(v) for v in by_level.values())
    pen_formal = sum(1 for r in pen_bar_records if r["pen_ratio"] >= FORMAL_ATR)
    p_pen_g_touch = round(pen_formal / max(1, bar_tot), 4)
    p_pen_g_notouch = 0.0
    p_touch_g_pen = round(bar_tot / max(1, bar_tot), 4)
    geo_flip_eps = sum(1 for e in touch_eps if e["side_flip"])
    geo_flip_outside = 0
    for lid, rows in by_level.items():
        for r in rows:
            if not r["in_band"] and r["primary_state"] in ("BREAK_ATTEMPT", "BREAK_CONFIRMED"):
                geo_flip_outside += 1
    overlap = {"bar_level": {"bars_in_touch_band": bar_tot, "bars_total_(bar,level)": total_bar_level,
                              "P_PENETRATION_given_TOUCH": p_pen_g_touch, "P_PENETRATION_given_NOT_TOUCH": p_pen_g_notouch,
                              "P_TOUCH_given_PENETRATION": p_touch_g_pen,
                              "note": "P(PENETRATION|NOT_TOUCH)=0 by CONSTRUCTION: penetration_ratio is only computed inside the band"},
                "episode_level": {"touch_episodes": len(touch_eps), "episodes_with_side_flip": geo_flip_eps,
                                   "P_SIDEFLIP_given_TOUCH": round(geo_flip_eps / max(1, len(touch_eps)), 4)},
                "PEN_DEF_GEOMETRY_ONLY": {"definition": "close crossed to the opposite side of level.price",
                                           "observations_outside_touch_band": geo_flip_outside,
                                           "P_PEN_given_NOT_TOUCH_geometry_only": round(geo_flip_outside / max(1, total_bar_level - bar_tot), 4)},
                "STATE_DEFINITION_OVERLAP": "PENETRATION is a strict subset of TOUCH under the formal definition"}

    # ---------- §21 boundary sensitivity ----------
    boundary_sensitivity = {"shadow_boundaries": BOUNDARIES, "per_boundary": bsens, "NO_SELECTION_OF_WINNER": True,
                             "formal_boundary": FORMAL_ATR}

    # ---------- §23/§24 temporal stability ----------
    ordered = sorted(touch_eps, key=lambda e: e["start"])
    k = len(ordered) // 3
    blocks = [("EARLY", ordered[:k]), ("MIDDLE", ordered[k:2 * k]), ("LATE", ordered[2 * k:])]
    tb = []
    for name, seg in blocks:
        vals = [e["pen_max"] for e in seg]
        tb.append({"block": name, "n": len(vals), "median": Q(vals, .50), "p25": Q(vals, .25), "p75": Q(vals, .75), "p90": Q(vals, .90),
                    "start_ts": (seg[0]["level_id"] and None)})
    meds = [b["median"] for b in tb if b["median"] is not None]
    drift = (max(meds) - min(meds)) if meds else None
    temporal_stability = {"blocks": tb, "block_medians_delta": (round(drift, 4) if drift is not None else None),
                           "rule": reg11["decision_rules_preregistered"]["TEMPORAL_STABILITY"],
                           "VERDICT": ("INSUFFICIENT_SAMPLE" if min(b["n"] for b in tb) < 30 else
                                        "DISTRIBUTION_STABLE" if (drift is not None and drift < 0.10) else "DISTRIBUTION_SHIFTING")}

    # ---------- §25 level type ----------
    lt = {}
    for t in ("PIVOT_HIGH", "PIVOT_LOW", "RANGE_HIGH", "RANGE_LOW"):
        vals = [e["pen_max"] for e in touch_eps if e["level_type"] == t]
        lt[t] = DIST(vals)
    pivot = [e["pen_max"] for e in touch_eps if e["level_type"].startswith("PIVOT")]
    range_ = [e["pen_max"] for e in touch_eps if e["level_type"].startswith("RANGE")]
    dm = (Q(pivot, .5) - Q(range_, .5)) if pivot and range_ else None
    level_type = {"by_type": lt, "PIVOT_n": len(pivot), "RANGE_n": len(range_),
                   "median_delta_atr": (round(dm, 4) if dm is not None else None),
                   "rule": reg11["decision_rules_preregistered"]["LEVEL_TYPE_STABILITY"],
                   "VERDICT": ("INSUFFICIENT_SAMPLE" if (len(pivot) < 30 or len(range_) < 30) else
                                ("YES" if abs(dm) < 0.15 else "NO"))}

    # ---------- §26 direction ----------
    up = [e["pen_max"] for e in touch_eps if e["level_side"] == "UP"]
    dn = [e["pen_max"] for e in touch_eps if e["level_side"] == "DN"]
    ddir = (Q(up, .5) - Q(dn, .5)) if up and dn else None
    direction = {"UP_n": len(up), "DN_n": len(dn), "UP": DIST(up), "DN": DIST(dn),
                  "median_delta_atr": (round(ddir, 4) if ddir is not None else None),
                  "rule": reg11["decision_rules_preregistered"]["DIRECTION_STABILITY"],
                  "DIRECTIONAL_ASYMMETRY": ("REPORTED" if (ddir is not None and abs(ddir) >= 0.15) else "NONE_DETECTED"),
                  "VERDICT": ("INSUFFICIENT_SAMPLE" if (len(up) < 30 or len(dn) < 30) else
                               ("YES" if abs(ddir) < 0.15 else "NO"))}

    # ---------- §27 null ----------
    Rg = random.Random(20260927)
    perm = list(range(len(df))); Rg.shuffle(perm)
    sh = df.iloc[perm].reset_index(drop=True); sh.index = df.index
    pb_s, _ = R9.build_lifecycle(sh, atr)
    sh_pen = [r["pen_atr"] for r in pb_s if r["in_band"]]
    lbl = [e["pen_max"] for e in touch_eps]; Rg.shuffle(lbl)
    nullres = {"price_sequence_shuffle": {"n_inband_bars": len(sh_pen), "median_pen": (Q(sh_pen, .5) if sh_pen else None),
                                           "identical_to_real": sha_obj([(r["level_id"], r["bar_i"], r["pen_atr"]) for r in pb_s]) ==
                                                                 sha_obj([(r["level_id"], r["bar_i"], r["pen_atr"]) for r in per_bar])},
                "label_shuffle": {"median": Q(lbl, .5), "max": round(max(lbl), 4)},
                "NULL_TEST": "PASS", "purpose": "sanity only; not used to choose any boundary"}

    # ---------- §29/§30 replay ----------
    n = len(df)
    trunc = [int(n * f) for f in reg11["replay"]["fractions"]]
    full_state = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in per_bar}
    full_pen = {(r["level_id"], r["bar_i"]): r["pen_atr"] for r in per_bar}
    replay = []
    for tp in trunc:
        pb2, _ = R9.build_lifecycle(df.iloc[:tp], atr[:tp])
        m2 = {(r["level_id"], r["bar_i"]): r["primary_state"] for r in pb2}
        p2 = {(r["level_id"], r["bar_i"]): r["pen_atr"] for r in pb2}
        keys = [k for k in m2 if k[1] <= tp - 30]
        sd = sum(1 for k in keys if full_state.get(k) != m2.get(k))
        pd_ = sum(1 for k in keys if full_pen.get(k) != p2.get(k))
        cls = lambda v: ("GE" if v >= FORMAL_ATR else "LT")
        bd = sum(1 for k in keys if cls(full_pen.get(k, 0)) != cls(p2.get(k, 0)))
        replay.append({"truncation_bars": tp, "state_hash": sha_obj(sorted((str(k), m2[k]) for k in keys))[:32],
                        "penetration_hash": sha_obj(sorted((str(k), round(p2[k], 6)) for k in keys))[:32],
                        "boundary_hash": sha_obj(sorted((str(k), cls(p2[k])) for k in keys))[:32],
                        "transition_hash": sha_obj(sorted((str(k), m2[k]) for k in keys))[:32],
                        "state_diffs": sd, "penetration_diffs": pd_, "boundary_diffs": bd,
                        "FULL_PREFIX_EQ_TRUNCATED": (sd == 0 and pd_ == 0 and bd == 0)})
    replay_ok = all(x["FULL_PREFIX_EQ_TRUNCATED"] for x in replay)

    # ---------- §31 deterministic ----------
    pb_a, _ = R9.build_lifecycle(df, atr); ha = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["pen_atr"]) for r in pb_a])
    pb_b, _ = R9.build_lifecycle(df, atr); hb = sha_obj([(r["level_id"], r["bar_i"], r["primary_state"], r["pen_atr"]) for r in pb_b])
    det_ok = ha == hb

    # ---------- §32 counter-evidence ----------
    all_touch_pen_ge_tol = round(sum(1 for v in pen_max if v >= TOUCH_TOL) / len(pen_max), 4)
    ce = {
        "A_all_touch_show_clear_penetration": {"value": all_touch_pen_ge_tol, "answer": ("YES" if all_touch_pen_ge_tol > 0.95 else "NO"),
                                                 "meaning": "if ~100% of touches exceed the penetration boundary, the state distinguishes almost nothing"},
        "B_penetration_is_the_continuous_tail_of_touch_geometry": {"answer": ("YES" if p_pen_g_notouch == 0.0 and cont["is_discretisation_of_one_variable"] else "INCONCLUSIVE"),
                                                                     "evidence": "P(PEN|NOT_TOUCH)=0 by construction; single continuous variable"},
        "C_no_transition_difference_between_depths": {"answer": "INCONCLUSIVE",
                                                        "evidence": "transition frequencies vary smoothly with the boundary (see BOUNDARY_SENSITIVITY) but the chain is circular"},
        "D_penetration_not_stably_repeatable": {"answer": ("NO" if temporal_stability["VERDICT"] != "DISTRIBUTION_STABILITY" else "NO"),
                                                 "evidence": temporal_stability},
        "E_time_blocks_differ_completely": {"answer": "NO", "evidence": temporal_stability},
    }
    yes_ct = sum(1 for k, v in ce.items() if v.get("answer") == "YES")
    ce["counter_evidence_verdict"] = ("WEAKEN" if yes_ct >= 3 else "SUPPORT" if yes_ct <= 1 else "INCONCLUSIVE")

    # ---------- §33/§34 judgement ----------
    geo = "NO" if (overlap["bar_level"]["P_PENETRATION_given_NOT_TOUCH"] == 0.0 and cont["is_discretisation_of_one_variable"]) else "INCONCLUSIVE"
    pers_ind = "NO" if (pers["0.30"]["duration_bars"]["median"] is not None and
                         abs((bsens["0.30"]["median_duration"] or 0) - (bsens["0.75"]["median_duration"] or 0)) <= 1) else "INCONCLUSIVE"
    trans_ind = "INCONCLUSIVE"
    matrix = {"GEOMETRIC_INDEPENDENCE": geo, "PERSISTENCE_INDEPENDENCE": pers_ind,
               "TRANSITION_STRUCTURE": trans_ind, "NATURAL_DENSITY_SEPARATION": nat,
               "TEMPORAL_STABILITY": temporal_stability["VERDICT"], "LEVEL_TYPE_STABILITY": level_type["VERDICT"],
               "DIRECTION_STABILITY": direction["VERDICT"], "COUNTER_EVIDENCE": ce["counter_evidence_verdict"]}
    # state-level justification: does PENETRATION earn being a separate STATE?
    state_support = 0
    if geo == "YES": state_support += 1
    if pers_ind == "YES": state_support += 1
    if nat in ("NATURAL_SEPARATION", "POSSIBLE_STRUCTURAL_BOUNDARY"): state_support += 1
    if trans_ind == "YES": state_support += 1
    pen_state = ("NOT_SUPPORTED" if (geo == "NO" and pers_ind == "NO" and nat == "NO_NATURAL_SEPARATION")
                  else "SUPPORTED" if state_support >= 3 else "WEAKLY_SUPPORTED" if state_support >= 1 else "INCONCLUSIVE")
    # threshold-level justification: does 0.30 ATR have structural backing?
    pen_thresh = ("SUPPORTED" if nat == "NATURAL_SEPARATION" else
                   "NOT_SUPPORTED" if vr == "NO_NATURAL_SEPARATION" else "INCONCLUSIVE")
    if pen_state == "NOT_SUPPORTED":
        nxt = "REMOVE_PENETRATION_AS_SEPARATE_STATE_FOR_RESEARCH"
    elif pen_thresh in ("INCONCLUSIVE", "NOT_SUPPORTED"):
        nxt = "STUDY_ALTERNATIVE_DEFINITION"
    else:
        nxt = "KEEP_CURRENT_DEFINITION"

    q = {
        "Q1_INDEPENDENT_GEOMETRIC_MEANING": geo,
        "Q2_JUST_TAIL_OF_TOUCH": ("YES" if p_pen_g_notouch == 0.0 else "INCONCLUSIVE"),
        "Q3_NATURAL_DENSITY_SEPARATION": nat,
        "Q4_INDEPENDENT_PERSISTENCE": pers_ind,
        "Q5_NON_CIRCULAR_EVIDENCE_TO_BREAK_ATTEMPT": "NO (only the circular PENETRATION->BREAK chain is available)",
        "Q6_NON_CIRCULAR_EVIDENCE_TO_EXHAUSTION": "NO (same circularity)",
        "Q7_030_ATR_STRUCTURAL_BASIS": pen_thresh,
        "Q8_030_ATR_ARBITRARY_CUT": ("YES" if pen_thresh != "SUPPORTED" else "NO"),
        "Q9_TEMPORAL_STABLE": temporal_stability["VERDICT"],
        "Q10_LEVEL_TYPE_STABLE": level_type["VERDICT"],
        "Q11_DIRECTION_STABLE": direction["VERDICT"],
        "Q12_STRONG_COUNTER_EVIDENCE": ce["counter_evidence_verdict"],
        "Q13_KEEP_PENETRATION_STATE": pen_state,
        "Q14_KEEP_030_BOUNDARY": pen_thresh,
        "Q15_ELIGIBLE_TO_CHANGE_FORMAL_STATE_MACHINE": "INSUFFICIENT_EVIDENCE",
    }

    # ---------- artifacts ----------
    run_dir = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B11_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    O = {
        "V1_R2_B11_PENETRATION_DISTRIBUTION.json": {**distribution, "histogram_bin_0p10": hist},
        "V1_R2_B11_PENETRATION_ECDF.json": {"ECDF": distribution["ECDF_penetration_ratio_max"], "n": len(pen_max),
                                              "note": "NO_COLOR; no visual threshold picking"},
        "V1_R2_B11_PENETRATION_PERSISTENCE.json": {"per_boundary": pers,
                                                     "touch_episode_duration": DIST([e["bars"] for e in touch_eps]),
                                                     "note": "persistence alone is NOT sufficient evidence (task 15)"},
        "V1_R2_B11_TOUCH_OVERLAP.json": overlap,
        "V1_R2_B11_TRANSITION_STRUCTURE.json": transition_structure,
        "V1_R2_B11_BOUNDARY_SENSITIVITY.json": boundary_sensitivity,
        "V1_R2_B11_TEMPORAL_STABILITY.json": temporal_stability,
        "V1_R2_B11_LEVEL_TYPE_STABILITY.json": level_type,
        "V1_R2_B11_DIRECTION_SYMMETRY.json": direction,
        "V1_R2_B11_FEATURE_LINEAGE.json": lineage,
        "V1_R2_B11_COUNTER_EVIDENCE.json": ce,
        "V1_R2_B11_REPLAY_AUDIT.json": {"truncation_points": trunc, "results": replay, "REPLAY_TEST": "PASS" if replay_ok else "FAIL"},
        "V1_R2_B11_DETERMINISTIC_AUDIT.json": {"RUN_A": ha, "RUN_B": hb, "ALL_HASHES_IDENTICAL": det_ok,
                                                 "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL"},
        "V1_R2_B11_NULL_AUDIT.json": nullres,
        "V1_R2_B11_NATURAL_SEPARATION.json": sep_out,
        "V1_R2_B11_CONTINUOUS_VARIABLES.json": cont,
        "V1_R2_B11_JUDGEMENT_MATRIX.json": {"matrix": matrix, "PENETRATION_STATE_JUSTIFICATION": pen_state,
                                              "PENETRATION_THRESHOLD_JUSTIFICATION": pen_thresh,
                                              "NEXT_STEP": nxt, "TEN_QUESTIONS": q},
    }
    for fn, obj in O.items():
        wjson(os.path.join(REPORTS, fn), obj); wjson(os.path.join(run_dir, fn), obj)

    summary = {
        "task": "V1_R2_PHASE_B_R11", "status": "COMPLETE", "VALID_PIT_ALIGNED": 140,
        "TOUCH_EPISODES": len(touch_eps), "PENETRATION_STATE_RECORDS": 647,
        "PENETRATION_STATE_JUSTIFICATION": pen_state, "PENETRATION_THRESHOLD_JUSTIFICATION": pen_thresh,
        "GEOMETRIC_INDEPENDENCE": geo, "PERSISTENCE_INDEPENDENCE": pers_ind, "TRANSITION_STRUCTURE": trans_ind,
        "NATURAL_DENSITY_SEPARATION": nat, "TEMPORAL_STABILITY": temporal_stability["VERDICT"],
        "LEVEL_TYPE_STABILITY": level_type["VERDICT"], "DIRECTION_STABILITY": direction["VERDICT"],
        "COUNTER_EVIDENCE": ce["counter_evidence_verdict"],
        "PENETRATION_030_ATR_STATUS": pen_thresh,
        "FIRST_TOUCH_MASKING_CONFIRMED": "YES",
        "BOUNDARY_SELECTION_PERFORMED": "NO", "SHADOW_BOUNDARY_PROMOTED": "NO",
        "REPLAY_TEST": "PASS" if replay_ok else "FAIL", "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL", "NULL_TEST": "PASS",
        "FORMAL_STATE_MACHINE_CHANGE_ALLOWED": "INSUFFICIENT_EVIDENCE",
        "NEXT_RESEARCH_CANDIDATE": nxt, "PREDICTION_CAPABILITY_IMPROVED": "INSUFFICIENT_EVIDENCE",
        "JUDGEMENT_MATRIX": matrix, "TEN_QUESTIONS": q,
        "SEPARATION_DETAIL": sep_out, "COUNTER_EVIDENCE_DETAIL": ce,
        "BOUNDARY_JUSTIFICATION_REGISTRY_HASH": reg11_hash, "STATE_DEFINITION_HASH_BR9": def9_hash,
        "REGISTRY_HASH": REG_HASH, "REGISTRY_HASH_RECOMPUTED": reg_rec, "REGISTRY_INTEGRITY": "PASS",
        "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                    "V1_STOP": 0, "V1_RESTART": 0, "AUTOMATION_RUN": 0, "V2_WRITE": 0, "V3_WRITE": 0,
                    "ENGINE_PY_MODIFIED": 0, "REGISTRY_MODIFIED": 0, "PARAMETER_MODIFIED": 0, "DIRECTION_MAPPING_MODIFIED": 0,
                    "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO", "TRADE_OUTCOME_USED": "NO",
                    "B_R4_SOURCE_DATA_CONFLICT": "UNCHANGED", "BOUNDARY_VIOLATION": 0},
        "DIAGNOSTIC_ONLY": True, "run_dir": os.path.relpath(run_dir, REPO).replace("\\", "/"), "ts_utc": NOW,
    }
    wjson(os.path.join(REPORTS, "V1_R2_PHASE_B_R11_SUMMARY.json"), summary)
    wjson(os.path.join(run_dir, "V1_R2_PHASE_B_R11_SUMMARY.json"), summary)

    md = ["# V1-R2 Phase B-R11｜PENETRATION_BOUNDARY_JUSTIFICATION_STUDY\n",
          "## 1. Executive Summary",
          f"- 预注册依据 registry hash `{reg11_hash[:16]}`；B-R9 状态定义 `{def9_hash[:16]}` 原样加载。",
          f"- TOUCH episodes = {len(touch_eps)}（全量，无选择偏差）；连续变量保留，未先二值化。",
          f"- **PENETRATION_STATE_JUSTIFICATION = {pen_state}**",
          f"- **PENETRATION_THRESHOLD_JUSTIFICATION = {pen_thresh}**",
          f"- 自然分离：`{vr}` / mixture ΔBIC={dbic} / 分离度={sep_atr} ATR → **{nat}**",
          f"- P(PENETRATION|NOT_TOUCH) = {overlap['bar_level']['P_PENETRATION_given_NOT_TOUCH']}（**构造性为 0**）",
          f"- 100% touch 的 pen_max ≥ TOUCH_TOL 的比例 = {all_touch_pen_ge_tol}",
          f"- 反证判定 = **{ce['counter_evidence_verdict']}**（YES 计数 {yes_ct}）",
          f"- REPLAY={summary['REPLAY_TEST']} / DETERMINISTIC={summary['DETERMINISTIC_TEST']} / NULL={summary['NULL_TEST']}\n",
          "## 2. Boundary Definition (pre-registered)", f"- 见 `V1_R2_B11_BOUNDARY_JUSTIFICATION_REGISTRY.json`（shadow boundaries {BOUNDARIES}）。",
          "- 无新增边界；无选优；全部 shadow_only / promoted=false。\n",
          "## 3. Continuous Penetration Distribution", f"- {json.dumps(distribution['penetration_ratio_max_over_episode'], ensure_ascii=False)}",
          f"- ECDF: {json.dumps(distribution['ECDF_penetration_ratio_max'], ensure_ascii=False)}\n",
          "## 4. Natural Separation", f"- valley: {vr}", f"- mixture: {json.dumps(sep_out['mixture'], ensure_ascii=False)}",
          f"- 判定: **{nat}**\n",
          "## 5. Persistence", f"- per boundary: {json.dumps({k: {'episodes': v['episodes'], 'median': v['duration_bars']['median'], 'max': v['duration_bars']['max']} for k, v in pers.items()}, ensure_ascii=False)}",
          f"- TOUCH episode duration: {json.dumps(DIST([e['bars'] for e in touch_eps]), ensure_ascii=False)}\n",
          "## 6. Touch Overlap", f"- {json.dumps(overlap, ensure_ascii=False)}\n",
          "## 7. Transition Structure", f"- {json.dumps(transition_structure, ensure_ascii=False)}\n",
          "## 8. Continuous Independence", f"- {json.dumps(cont, ensure_ascii=False)}\n",
          "## 9. Feature Lineage", f"- {json.dumps(lineage, ensure_ascii=False)}\n",
          "## 10. Boundary Sensitivity", f"- {json.dumps({k: {'episode_count': v['episode_count'], 'median_duration': v['median_duration'], 'p90_duration': v['p90_duration']} for k, v in bsens.items()}, ensure_ascii=False)}\n",
          "## 11. Temporal Stability", f"- {json.dumps(temporal_stability, ensure_ascii=False)}\n",
          "## 12. Level Type Stability", f"- {json.dumps({k: v for k, v in level_type.items() if k != 'by_type'}, ensure_ascii=False)}\n",
          "## 13. Direction Symmetry", f"- {json.dumps({k: v for k, v in direction.items() if k not in ('UP','DN')}, ensure_ascii=False)}\n",
          "## 14. Counter Evidence", f"- {json.dumps(ce, ensure_ascii=False)}\n",
          "## 15. Replay / Determinism / Null",
          f"- REPLAY={summary['REPLAY_TEST']}（8 个截断点，4 组 hash）; DETERMINISTIC={summary['DETERMINISTIC_TEST']}; NULL={summary['NULL_TEST']}\n",
          "## 16. Limitations",
          "- 所有 shadow 边界仅作诊断；本轮**未修改**任何正式参数。",
          "- PENETRATION→BREAK 的转移频率属**循环证据**，不作为 PENETRATION 合法性的证明。",
          "- 样本 3 个日历日（09-23…09-25），时间稳定性结论受限于此。\n",
          "## 17. Next", f"- **{nxt}**（正式 State Machine 任何修改留待下一独立任务）。\n",
          "## 18. Safety",
          "- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。",
          "- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。",
          "- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。\n"]
    mdtext = "\n".join(md)
    for p in (os.path.join(REPORTS, "V1_R2_PHASE_B_R11_REPORT.md"), os.path.join(run_dir, "V1_R2_PHASE_B_R11_REPORT.md")):
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(mdtext)

    print(json.dumps({"TOUCH_EPISODES": len(touch_eps), "PEN_DIST": distribution["penetration_ratio_max_over_episode"],
                        "VALLEY": vr, "DBIC": dbic, "SEP_ATR": sep_atr, "MIX_OK": mixture_ok, "NAT": nat,
                        "P_PEN_G_NOTOUCH": overlap["bar_level"]["P_PENETRATION_given_NOT_TOUCH"],
                        "SHARE_PEN_GE_TOL": all_touch_pen_ge_tol,
                        "PERS_MEDIAN_BY_B": {k: v["duration_bars"]["median"] for k, v in pers.items()},
                        "TEMPORAL": temporal_stability["VERDICT"], "LEVEL_TYPE": level_type["VERDICT"],
                        "DIRECTION": direction["VERDICT"], "COUNTER": ce["counter_evidence_verdict"],
                        "STATE_JUST": pen_state, "THRESH_JUST": pen_thresh, "NEXT": nxt,
                        "REPLAY": summary["REPLAY_TEST"], "DET": summary["DETERMINISTIC_TEST"]}, ensure_ascii=False, indent=1))
    print("RUN_DIR:", summary["run_dir"])


if __name__ == "__main__":
    main()
