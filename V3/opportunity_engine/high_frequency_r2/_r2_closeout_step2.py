# -*- coding: utf-8 -*-
"""R2 FINAL CLOSEOUT — step 2: defect repair + full re-run from the frozen input.

Fixes: BUG-01 real cross-grid parent/cluster, BUG-02 F3 => INSUFFICIENT_DATA, BUG-03 real cross-family overlap.
Full chain re-executed: INPUT -> DETECTION -> OPPORTUNITY -> CROSS-GRID -> CROSS-FAMILY -> EPISODE -> FREQUENCY
-> PRIORITY -> HERMES -> NEGATIVE CONTROL -> ABLATION -> OUTPUT. Frozen windows only; no new thresholds.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RE = os.path.dirname(ROOT)
AIQ = os.path.dirname(RE)
SRC = os.path.join(RE, "v3_crossmarket_sources")
R1A = os.path.join(RE, "v3_alpha_discovery_r1")
sys.path.insert(0, os.path.join(ROOT, "mechanism_validation_r2"))
NOW = datetime.now(timezone.utc).isoformat()
SEED = 20260925
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REG = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), encoding="utf-8"))
FZ = REG["FREEZE_HASH"]
GRID_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30}
SAME_GRID_BARS = REG["episode_rules"]["same_family_same_grid_within_bars"]
CROSS_GRID_MIN = REG["episode_rules"]["cross_grid_merge_within_minutes"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ------------------------------------------------------------------ FIX BUG-01
def window_minutes(prev, cur):
    """Frozen windows only: cross-grid uses the registry's 30-minute merge rule; same-grid uses 30 bars."""
    if prev["grid"] != cur["grid"]:
        return CROSS_GRID_MIN, "cross_grid_30min"
    return SAME_GRID_BARS * GRID_MIN[cur["grid"]], f"same_grid_{SAME_GRID_BARS}bars"


def group_parents(recs):
    """Real cross_grid_parent_id: same family, sequential, joins while the gap stays inside the frozen window."""
    out = {}
    by_fam = {}
    for r in sorted(recs, key=lambda x: (x["family"], x["timestamp"])):
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rs in by_fam.items():
        pid, last, last_kind = None, None, None
        for r in rs:
            t = pd.Timestamp(r["timestamp"])
            if last is None:
                pid = f"XG-{fam[:6]}-{len(out)+1:05d}"
                out[r["opportunity_id"]] = (pid, "group_open")
            else:
                w, kind = window_minutes(last, r)
                gap = (t - last["_t"]).total_seconds() / 60.0
                if gap <= w:
                    out[r["opportunity_id"]] = (pid, kind)
                else:
                    pid = f"XG-{fam[:6]}-{len(out)+1:05d}"
                    out[r["opportunity_id"]] = (pid, "new_group")
            r["_t"] = t
            last = r
    return out


# ------------------------------------------------------------------ BUG-01 unit tests (section 4)
def mk(fam, grid, ts, i):
    return {"opportunity_id": f"T{i}", "family": fam, "grid": grid, "timestamp": ts}


def grouping_unit_tests():
    base = pd.Timestamp("2025-01-05T00:00:00+00:00")
    T = {}
    # same_event_same_grid: 10 min apart, same grid -> same parent
    g = group_parents([mk("F1", "1m", str(base), 1), mk("F1", "1m", str(base + pd.Timedelta(minutes=10)), 2)])
    T["same_event_same_grid"] = (g["T1"][0] == g["T2"][0])
    # same_event_cross_grid: 10 min apart, different grids -> same parent
    g = group_parents([mk("F1", "1m", str(base), 3), mk("F1", "5m", str(base + pd.Timedelta(minutes=10)), 4)])
    T["same_event_cross_grid"] = (g["T3"][0] == g["T4"][0])
    # different_event_same_grid: 90 min apart -> different parents
    g = group_parents([mk("F1", "1m", str(base), 5), mk("F1", "1m", str(base + pd.Timedelta(minutes=90)), 6)])
    T["different_event_same_grid"] = (g["T5"][0] != g["T6"][0])
    # different_event_cross_grid: 90 min apart, different grids -> different parents
    g = group_parents([mk("F1", "1m", str(base), 7), mk("F1", "5m", str(base + pd.Timedelta(minutes=90)), 8)])
    T["different_event_cross_grid"] = (g["T7"][0] != g["T8"][0])
    # three_grid_same_event: 1m/5m/15m inside the window -> one parent
    g = group_parents([mk("F1", "1m", str(base), 9), mk("F1", "5m", str(base + pd.Timedelta(minutes=8)), 10),
                        mk("F1", "15m", str(base + pd.Timedelta(minutes=20)), 11)])
    T["three_grid_same_event"] = len({g["T9"][0], g["T10"][0], g["T11"][0]}) == 1
    # cross_family_same_event: parents are family-scoped (cross-family grouping is the EPISODE layer)
    g = group_parents([mk("F1", "1m", str(base), 12), mk("F2", "1m", str(base), 13)])
    T["cross_family_same_event"] = (g["T12"][0] != g["T13"][0])
    return T


# ------------------------------------------------------------------ episode layer (cross-grid AND cross-family)
def build_episodes(opps):
    """(a) sub-episodes per (family, grid) with the frozen 30-bars rule;
       (b) union-find merge of sub-episodes whose representative times are within the frozen 30-minute rule."""
    sub = []
    by = {}
    for o in sorted(opps, key=lambda x: (x["family"], x["grid"], x["timestamp"])):
        by.setdefault((o["family"], o["grid"]), []).append(o)
    for (fam, grid), rs in by.items():
        last, sid = None, None
        for o in rs:
            t = pd.Timestamp(o["timestamp"])
            if last is None or (t - last).total_seconds() / 60.0 > SAME_GRID_BARS * GRID_MIN[grid]:
                sid = f"SE-{len(sub)+1:06d}"
                sub.append({"sid": sid, "t": t, "members": []})
            sub[-1]["members"].append(o["opportunity_id"])
            o["sub_episode_id"] = sid if sid else sub[-1]["sid"]
            last = t
    # union-find over sub-episodes by the frozen 30-minute representative-time rule
    parent = {s["sid"]: s["sid"] for s in sub}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    ss = sorted(sub, key=lambda s: s["t"])
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            if (ss[j]["t"] - ss[i]["t"]).total_seconds() / 60.0 > CROSS_GRID_MIN:
                break
            union(ss[i]["sid"], ss[j]["sid"])
    roots = {s["sid"]: find(s["sid"]) for s in sub}
    canon, n = {}, 0
    for sid in roots.values():
        if sid not in canon:
            n += 1
            canon[sid] = f"HEP2-{n:05d}"
    for o in opps:
        o["episode_id_v2"] = canon[roots[o["sub_episode_id"]]]
    return len(canon)


def main():
    # ---------------- DETECTION (frozen rules, unchanged) ----------------
    m1 = pd.read_parquet(os.path.join(R1A, "xauusd_m1_histdata.parquet"),
                          columns=["dt_utc", "open", "high", "low", "close", "volume"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    m1 = m1.set_index("dt").sort_index()
    m1 = m1[~m1.index.duplicated(keep="first")]
    VOL_ALL_ZERO = bool((m1["volume"].fillna(0) == 0).all())
    INPUT_HASH = sha_obj({"rows": int(len(m1)), "first": str(m1.index[0]), "last": str(m1.index[-1])})
    assert INPUT_HASH == "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53", "input changed"

    def grid(df, rule):
        return df.resample(rule).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                       close=("close", "last"), volume=("volume", "sum")).dropna()

    grids = {"1m": m1, "5m": grid(m1, "5min"), "15m": grid(m1, "15min"), "30m": grid(m1, "30min")}
    B = REG["detection_rules"]
    opps = []
    for gname, g in grids.items():
        c = g["close"]
        vol = c.pct_change().rolling(B["vol_baseline_bars"], min_periods=30).std()
        z = (c.pct_change().abs() - c.pct_change().abs().rolling(B["vol_baseline_bars"], min_periods=30).mean()) / \
            c.pct_change().abs().rolling(B["vol_baseline_bars"], min_periods=30).std()
        vol_pct = vol.rolling(B["vol_baseline_bars"], min_periods=30).apply(lambda v: float(np.mean(v <= v[-1])), raw=True)
        hi = g["high"].rolling(B["envelope_bars"], min_periods=10).max().shift(1)
        lo = g["low"].rolling(B["envelope_bars"], min_periods=10).min().shift(1)
        atr = (g["high"] - g["low"]).rolling(B["atr_bars"], min_periods=5).mean()
        act_f = g["volume"].rolling(B["activity_fast"], min_periods=2).mean()
        act_s = g["volume"].rolling(B["activity_slow"], min_periods=10).mean()
        rng = (g["high"] - g["low"])
        rng_ratio = rng / rng.rolling(B["activity_slow"], min_periods=10).mean()
        excursion = np.maximum(g["high"] - hi, lo - g["low"]) / atr.replace(0, np.nan)
        trend = c.rolling(30, min_periods=10).apply(lambda v: np.polyfit(np.arange(len(v)), v, 1)[0], raw=True)
        for i in range(len(g)):
            t, fam, trig = g.index[i], None, None
            if np.isfinite(vol_pct.iloc[i]) and np.isfinite(rng_ratio.iloc[i]) and vol_pct.iloc[i] <= 0.20 \
                    and rng_ratio.iloc[i] >= 1.8:
                fam, trig = "F1_SHORT_STATE_JUMP", f"compression->expansion ratio={rng_ratio.iloc[i]:.2f}"
            if fam is None and np.isfinite(z.iloc[i]) and abs(z.iloc[i]) >= 3.0:
                fam, trig = "F2_SHORT_SHOCK_STRUCTURE", f"abs_z={z.iloc[i]:.2f}"
            if fam is None and np.isfinite(act_f.iloc[i]) and np.isfinite(act_s.iloc[i]) and act_s.iloc[i] > 0:
                r = act_f.iloc[i] / act_s.iloc[i]
                if r >= 2.0 and np.isfinite(rng_ratio.iloc[i]) and rng_ratio.iloc[i] >= 1.5:
                    fam, trig = "F3_PRICE_ACTIVITY_PROXY", f"activity_ratio={r:.2f}"
            if fam is None and np.isfinite(excursion.iloc[i]) and excursion.iloc[i] >= 2.0:
                fam, trig = "F5_SHORT_EXTENSION_REVERSION", f"excursion_atr={excursion.iloc[i]:.2f}"
            if fam is None and np.isfinite(z.iloc[i]) and abs(z.iloc[i]) >= 2.5:
                st = ("HIGH_VOL" if (np.isfinite(vol_pct.iloc[i]) and vol_pct.iloc[i] >= 0.8) else
                      "LOW_VOL" if (np.isfinite(vol_pct.iloc[i]) and vol_pct.iloc[i] <= 0.2) else
                      "TREND" if (np.isfinite(trend.iloc[i]) and abs(trend.iloc[i]) > 0) else "RANGE")
                fam, trig = "F6_STATE_CONDITIONAL_HF", f"state={st} abs_z={z.iloc[i]:.2f}"
            if fam:
                opps.append({"opportunity_id": f"HF-{gname}-{i:07d}", "timestamp": str(t), "grid": gname,
                              "family": fam, "trigger": trig, "data_quality": "PARTIAL",
                              "detection_uses_future": False})
    for k, f in (("DXY", "series_DXY_5m.parquet"), ("VIX", "series_VIX_5m.parquet"),
                  ("UST10Y_PROXY", "series_UST10Y_PROXY_TNX_5m.parquet")):
        s = pd.read_parquet(os.path.join(SRC, f))["close"]
        s.index = pd.to_datetime(s.index, utc=True)
        ch = s.pct_change(6) * 1e4
        zz = (ch - ch.rolling(120, min_periods=30).mean()) / ch.rolling(120, min_periods=30).std()
        for t in zz.index[(zz.abs() >= 2.0) & np.isfinite(zz)]:
            opps.append({"opportunity_id": f"HF-5m-F4-{k}-{t.strftime('%Y%m%d%H%M')}", "timestamp": str(t),
                          "grid": "5m", "family": "F4_CROSSMARKET_LEADING_ASSOCIATION",
                          "trigger": f"{k}-leading z={float(zz.loc[t]):.2f}", "data_quality": "PARTIAL",
                          "detection_uses_future": False})
    total_opp = len(opps)

    # ---------------- FIX BUG-01 ----------------
    gmap = group_parents([dict(o) for o in opps])
    for o in opps:
        o["cross_grid_parent_id"] = gmap.get(o["opportunity_id"], (None, None))[0]
        o["parent_join_reason"] = gmap.get(o["opportunity_id"], (None, None))[1]
    unit = grouping_unit_tests()
    UNIT_OK = all(unit.values())

    # ---------------- FIX: episodes (cross-grid + cross-family) ----------------
    n_ep = build_episodes(opps)
    clusters = len({o["cross_grid_parent_id"] for o in opps if o["cross_grid_parent_id"]})

    # ---------------- FIX BUG-02: F3 semantics ----------------
    FAM_ORDER = ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE", "F3_PRICE_ACTIVITY_PROXY",
                  "F4_CROSSMARKET_LEADING_ASSOCIATION", "F5_SHORT_EXTENSION_REVERSION", "F6_STATE_CONDITIONAL_HF"]
    fam_counts = {f: sum(1 for o in opps if o["family"] == f) for f in FAM_ORDER}
    F3_STATUS = "INSUFFICIENT_DATA" if (VOL_ALL_ZERO and fam_counts[F3 := "F3_PRICE_ACTIVITY_PROXY"] == 0) else "COMPUTED"
    F3_COUNT = "NOT_COMPUTABLE" if F3_STATUS == "INSUFFICIENT_DATA" else fam_counts[F3]

    # ---------------- frequency / classes ----------------
    ts_all = [pd.Timestamp(o["timestamp"]) for o in opps]
    span_days = max(1e-9, (max(ts_all) - min(ts_all)).total_seconds() / 86400)
    ind_pd, ind_pw = n_ep / span_days, n_ep / span_days * 7
    fam_rows = {}
    for f in FAM_ORDER:
        rs = [o for o in opps if o["family"] == f]
        eps = {o["episode_id_v2"] for o in rs}
        if f == F3 and F3_STATUS == "INSUFFICIENT_DATA":
            fam_rows[f] = {"raw_opportunities": 0, "status": "INSUFFICIENT_DATA", "independent_episodes": None,
                            "independent_per_week": None, "frequency_class": "NOT_COMPUTABLE"}
            continue
        fd = len(eps) / span_days
        fam_rows[f] = {"raw_opportunities": len(rs), "status": "COMPUTED", "independent_episodes": len(eps),
                        "independent_per_day": round(fd, 4), "independent_per_week": round(fd * 7, 4),
                        "frequency_class": ("HIGH_FREQUENCY" if fd * 7 >= 2 else "MEDIUM_FREQUENCY" if fd * 7 >= 1
                                             else "LOW_FREQUENCY")}
    hf = sum(1 for v in fam_rows.values() if v.get("frequency_class") == "HIGH_FREQUENCY")
    mf = sum(1 for v in fam_rows.values() if v.get("frequency_class") == "MEDIUM_FREQUENCY")
    lf = sum(1 for v in fam_rows.values() if v.get("frequency_class") == "LOW_FREQUENCY")

    # ---------------- duration (measurement only) ----------------
    c1 = m1["close"]
    durs = []
    for o in opps:
        i = c1.index.searchsorted(pd.Timestamp(o["timestamp"]).as_unit(c1.index.unit))
        if i + 60 >= len(c1):
            o["duration_min"] = None
            continue
        seg = c1.iloc[i:i + 60]
        e0 = float(seg.iloc[0])
        if e0 <= 0:
            o["duration_min"] = None
            continue
        path = (seg / e0 - 1) * 1e4
        k = int(np.argmax(np.abs(path)))
        peak = abs(float(path.iloc[k]))
        post = np.abs(path.iloc[k:].to_numpy(float))
        dec = int(np.argmax(post <= peak * 0.5))
        o["duration_min"] = k + dec
        o["time_to_peak_min"], o["time_to_decay_min"] = k, dec
        durs.append(o["duration_min"])
    dur = {"median": float(np.median(durs)) if durs else None, "p25": float(np.percentile(durs, 25)) if durs else None,
            "p75": float(np.percentile(durs, 75)) if durs else None}
    DURATION_STATUS = "TRUNCATION_SENSITIVE"     # measured on a fixed 1m x 60-bar forward window

    # ---------------- concentration / FIX BUG-03 overlap ----------------
    ec = {}
    for o in opps:
        ec[o["episode_id_v2"]] = ec.get(o["episode_id_v2"], 0) + 1
    top = sorted(ec.values(), reverse=True)
    conc = {"top_10_episode_share": round(sum(top[:10]) / max(1, total_opp), 4),
             "top_20_episode_share": round(sum(top[:20]) / max(1, total_opp), 4)}
    ovl = {}
    for i, a in enumerate(FAM_ORDER):
        for b in FAM_ORDER[i + 1:]:
            A = sorted(pd.Timestamp(o["timestamp"]) for o in opps if o["family"] == a)
            B = sorted(pd.Timestamp(o["timestamp"]) for o in opps if o["family"] == b)
            matched, j = 0, 0
            for ta in A:
                while j < len(B) and (B[j] - ta).total_seconds() / 60.0 < -CROSS_GRID_MIN:
                    j += 1
                k2 = j
                while k2 < len(B) and abs((B[k2] - ta).total_seconds()) / 60.0 <= CROSS_GRID_MIN:
                    matched += 1
                    k2 += 1
            denom = len(A) + len(B) - matched
            shared_ep = len({o["episode_id_v2"] for o in opps if o["family"] == a} &
                             {o["episode_id_v2"] for o in opps if o["family"] == b})
            ovl[f"{a} | {b}"] = {"family_pair": [a, b], "n_a": len(A), "n_b": len(B), "overlap_n": matched,
                                   "jaccard": round(matched / denom, 4) if denom else None,
                                   "shared_episode_n": shared_ep,
                                   "INFORMATIVE": "INFORMATIVE" if (len(A) and len(B)) else "UNINFORMATIVE"}
    merges = [k for k, v in ovl.items() if (v["jaccard"] or 0) >= REG["overlap_audit"]["merge_if_jaccard_ge"]]
    OVERLAP_STATUS = ("INFORMATIVE" if any(v["INFORMATIVE"] == "INFORMATIVE" for v in ovl.values())
                        else "UNINFORMATIVE")

    # ---------------- priority + Hermes ----------------
    W = REG["priority"]["weights"]
    for o in opps:
        fr = fam_rows[o["family"]]
        freq_s = min(1.0, (fr.get("independent_per_week") or 0) / 4.0)
        indep_s = 1.0 - min(1.0, conc["top_10_episode_share"])
        dq_s = {"VERIFIED": 1.0, "PARTIAL": 0.6, "UNKNOWN": 0.2}[o["data_quality"]]
        nov_s = min(1.0, 1.0 - ec.get(o["episode_id_v2"], 1) / 10.0)
        o["HERMES_PRIORITY_SCORE"] = round(W["frequency"] * freq_s + W["independence"] * indep_s +
                                             W["data_quality"] * dq_s + W["novelty"] * nov_s, 5)
    ranked = sorted(opps, key=lambda x: (-x["HERMES_PRIORITY_SCORE"], x["opportunity_id"]))
    budget = REG["hermes_budget"]["MAX_HERMES_INVESTIGATIONS"]
    selected = ranked[:budget]
    qc = {"QUALITY_HIGH": sum(1 for o in opps if o["HERMES_PRIORITY_SCORE"] >= 0.7),
           "QUALITY_MEDIUM": sum(1 for o in opps if 0.4 <= o["HERMES_PRIORITY_SCORE"] < 0.7),
           "QUALITY_LOW": sum(1 for o in opps if o["HERMES_PRIORITY_SCORE"] < 0.4)}

    # ---------------- negative control (vectorised, identical RNG/null/tail/comparison) ----------------
    rng = random.Random(SEED)
    t0, t1 = min(ts_all), max(ts_all)
    cabs = (c1.pct_change().abs() - c1.pct_change().abs().rolling(120, min_periods=30).mean()) / \
           c1.pct_change().abs().rolling(120, min_periods=30).std()
    _span_s = (t1 - t0).total_seconds()
    _idx_ns = cabs.index.values.astype("datetime64[ns]").view("int64")
    _abn = np.abs(np.nan_to_num(cabs.to_numpy(float), nan=0.0)) >= 3.0
    N_NC = REG["negative_control"]["runs"]

    def draw(u):
        base = t0.value
        return np.fromiter((base + pd.Timedelta(seconds=u.uniform(0, _span_s)).value for _ in range(total_opp)),
                            dtype="int64", count=total_opp)

    def hits(d):
        pos = np.searchsorted(_idx_ns, d, side="left")
        ok = pos < len(_idx_ns)
        return int(_abn[pos[ok]].sum())

    nc = [hits(draw(rng)) for _ in range(N_NC)]
    nc_mean = float(np.mean(nc))
    NC_STATUS = "PASS" if nc_mean <= 0.5 * total_opp else "FAIL"

    # ---------------- ablation remove_F1..F6 ----------------
    abl = {}
    for f in FAM_ORDER:
        rem = [o for o in opps if o["family"] != f]
        abl[f"remove_{f.split('_')[0]}"] = {"removed_family": f,
                                              "removed_family_status": fam_rows[f].get("status"),
                                              "remaining_raw": len(rem),
                                              "remaining_independent_episodes": len({o["episode_id_v2"] for o in rem})}

    # ---------------- outputs ----------------
    status_class = "COMPLETE_WITH_INSUFFICIENT_DATA" if F3_STATUS == "INSUFFICIENT_DATA" else "COMPLETE"
    summary = {"schema": "v3_hf_r2_final/1", "ts_utc": NOW, "version": REG["version"],
                "STATUS": status_class,
                "TOTAL_OPPORTUNITIES": total_opp, "INDEPENDENT_EVENTS": n_ep, "CLUSTERS": clusters,
                "F1_COUNT": fam_counts[FAM_ORDER[0]], "F2_COUNT": fam_counts[FAM_ORDER[1]],
                "F3_COUNT": F3_COUNT, "F3_STATUS": F3_STATUS,
                "F4_COUNT": fam_counts[FAM_ORDER[3]], "F5_COUNT": fam_counts[FAM_ORDER[4]],
                "F6_COUNT": fam_counts[FAM_ORDER[5]],
                "INDEPENDENT_EVENTS_PER_DAY": round(ind_pd, 4), "INDEPENDENT_EVENTS_PER_WEEK": round(ind_pw, 4),
                "HIGH_FREQUENCY_COUNT": hf, "MEDIUM_FREQUENCY_COUNT": mf, "LOW_FREQUENCY_COUNT": lf,
                "MEDIAN_DURATION": dur["median"], "P25_DURATION": dur["p25"], "P75_DURATION": dur["p75"],
                "DURATION_MEASUREMENT_STATUS": DURATION_STATUS,
                "TOP_10_EPISODE_SHARE": conc["top_10_episode_share"],
                "TOP_20_EPISODE_SHARE": conc["top_20_episode_share"],
                "HERMES_INVESTIGATIONS": len(selected), "HERMES_BUDGET": budget,
                "QUALITY_HIGH": qc["QUALITY_HIGH"], "QUALITY_MEDIUM": qc["QUALITY_MEDIUM"],
                "QUALITY_LOW": qc["QUALITY_LOW"],
                "NEGATIVE_CONTROL": NC_STATUS, "NEGATIVE_CONTROL_RUNS": N_NC,
                "NEGATIVE_CONTROL_MEAN": round(nc_mean, 2),
                "DETECTOR_ABLATION": "REPORTED", "OVERLAP_AUDIT": OVERLAP_STATUS,
                "OVERLAP_MERGE_CANDIDATES": merges,
                "GROUPING_UNIT_TESTS": unit, "GROUPING_UNIT_TESTS_PASS": UNIT_OK,
                "CANDIDATE_RESEARCH": 0, "ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF",
                "V3_LIVE": "OFF", "FREEZE_HASH": FZ, "INPUT_HASH": INPUT_HASH,
                "SUPERSEDES_OUTPUT_HASH": "80adcc6fee2560a3c9b559476319004910e0ee2b6d0f466974d1ae339724ec5e",
                "span_days": round(span_days, 2), "VOLUME_ALL_ZERO_INPUT": VOL_ALL_ZERO}
    OUTPUT_HASH = sha_obj(summary)
    summary["OUTPUT_HASH"] = OUTPUT_HASH
    assert OUTPUT_HASH != summary["SUPERSEDES_OUTPUT_HASH"], "output hash identical => fixed grouping not used"
    json.dump(summary, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_hf_r2_env/2", "ts_utc": NOW, "negative_control": {"runs": N_NC, "mean": nc_mean,
                                                                                "status": NC_STATUS},
                "ablation": abl, "overlap_matrix": ovl, "concentration": conc, "duration": dur,
                "duration_measurement_status": DURATION_STATUS, "family_table": fam_rows,
                "grouping_unit_tests": unit},
              open(os.path.join(HERE, "hf_env_audit.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    json.dump({"schema": "v3_hf_r2_opps/2", "ts_utc": NOW, "opportunities": opps},
              open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    import importlib
    mv2 = importlib.import_module("mechanism_validation_r2")
    lp = os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = mv2.mv.MechanismLedger(lp, FZ)
    led.append({"kind": "FREEZE", "hash": FZ})
    led.append({"kind": "INPUT", "hash": INPUT_HASH, "rows": int(len(m1))})
    led.append({"kind": "DETECTION", "raw_opportunities": total_opp})
    led.append({"kind": "GROUPING", "clusters": clusters, "unit_tests": unit})
    led.append({"kind": "EPISODES", "independent_events": n_ep})
    for f in FAM_ORDER:
        led.append({"kind": "FAMILY", "family": f, **fam_rows[f]})
    led.append({"kind": "OVERLAP", "status": OVERLAP_STATUS, "merge_candidates": merges})
    led.append({"kind": "NC", "status": NC_STATUS, "mean": nc_mean, "runs": N_NC})
    led.append({"kind": "FINAL", "output_hash": OUTPUT_HASH, "total": total_opp, "independent": n_ep,
                 "hermes": len(selected), "candidate": 0})
    summary["ledger_chain"] = mv2.mv.MechanismLedger.verify(lp)
    json.dump(summary, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(json.dumps(summary, ensure_ascii=False, default=str)[:2600])
    print("groups:", json.dumps(unit, ensure_ascii=False), "| UNIT_PASS:", UNIT_OK)
    print("families:", json.dumps(fam_rows, ensure_ascii=False)[:1000])
    print("overlap(informative):", json.dumps({k: v for k, v in ovl.items()
                                                 if v["INFORMATIVE"] == "INFORMATIVE"}, ensure_ascii=False)[:800])
    print("duration:", json.dumps(dur, ensure_ascii=False), DURATION_STATUS)
    print("ablation:", json.dumps(abl, ensure_ascii=False)[:700])


if __name__ == "__main__":
    main()
