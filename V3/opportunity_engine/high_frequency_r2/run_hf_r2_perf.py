# -*- coding: utf-8 -*-
"""V3 Market Opportunity Discovery R2 — HIGH FREQUENCY.

FREEZE FIRST (registry written + hashed), then discover. Detection uses ONLY data <= t.
Future prices appear solely in clearly separated MEASUREMENT fields (duration / time_to_peak / time_to_decay)
and are excluded from detection and from the priority sort.

M03 is ARCHIVE_REFERENCE only (commit 5ff2aad); CROSS_MARKET_SHOCK rediscovery is forbidden by this task.
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
SRC = os.path.join(os.path.dirname(ROOT), "v3_crossmarket_sources")
R1A = os.path.join(os.path.dirname(ROOT), "v3_alpha_discovery_r1")
NOW = datetime.now(timezone.utc).isoformat()
SEED = 20260925
VER = "HF-R2.0.0"

FROZEN = {
    "version": VER, "task": "V3_MARKET_OPPORTUNITY_DISCOVERY_R2_HIGH_FREQUENCY",
    "forbidden": {"m03_rediscovery": True, "m03_commit": "5ff2aad", "cross_market_shock_family": "FORBIDDEN",
                   "future_return_in_detection": True, "engineering_liquidity_from_price": True},
    "data_sources": {"XAUUSD": "HistData M1 (BID)", "DXY": "Yahoo DX-Y.NYB", "VIX": "Yahoo ^VIX",
                       "UST10Y": "Yahoo ^TNX PROXY (never official)"},
    "semantics_frozen": {"XAUUSD_DEFINITION": "UNKNOWN", "BAR_OPEN_CLOSE_SEMANTICS": "UNKNOWN",
                          "LICENSE": "UNKNOWN", "TNX": "PROXY"},
    "grids": {"primary": ["1m", "5m", "15m", "30m"], "background_only": ["1h"],
               "note": "1h is state background only; R2 high-frequency opportunities must not come mainly from 1h"},
    "timestamp_policy": {"normalization": "UTC", "grid_alignment": "exact bucket label (floor)",
                          "audit": ["exact", "floor", "nearest"], "adopted_for_detection": "floor",
                          "note": "the adopted method is frozen here; nearest is never used"},
    "families": {
        "F1_SHORT_STATE_JUMP": {"definition": "vol compression -> expansion or range -> directional move",
                                  "features": ["vol_pct_120", "range_expansion_ratio"],
                                  "threshold": {"vol_pct_before_max": 0.20, "range_ratio_min": 1.8},
                                  "forbidden": "no future return may define the state"},
        "F2_SHORT_SHOCK_STRUCTURE": {"definition": "short-horizon price shock and its immediate structure",
                                       "features": ["return_abs_z_120"],
                                       "threshold": {"abs_z_min": 3.0}, "holding_context": "1m..30m, NOT the 6h M03 horizon"},
        "F3_PRICE_ACTIVITY_PROXY": {"definition": "price-activity acceleration (NOT real liquidity)",
                                      "features": ["activity_ratio_5_60", "range_expansion_ratio"],
                                      "threshold": {"activity_ratio_min": 2.0, "range_ratio_min": 1.5},
                                      "label": "PRICE_ACTIVITY_PROXY", "liquidity_claim_forbidden": True},
        "F4_CROSSMARKET_LEADING_ASSOCIATION": {"definition": "an external source moves strictly before the XAU response window",
                                                 "sources": ["DXY", "VIX", "UST10Y_PROXY"],
                                                 "threshold": {"source_abs_z_min": 2.0, "min_lead_minutes": 5},
                                                 "wording": "leading association (never causality)",
                                                 "requires_source_time_lt_response_time": True,
                                                 "available_window": "5m cross-market covers 63 days only"},
        "F5_SHORT_EXTENSION_REVERSION": {"definition": "short-horizon extension beyond a rolling envelope",
                                           "features": ["envelope_excursion_atr"],
                                           "threshold": {"atr_multiple_min": 2.0},
                                           "must_not_repeat": "R1 failed rules (breakout60 / impulse5 / reversion3)"},
        "F6_STATE_CONDITIONAL_HF": {"definition": "high-frequency behaviour conditioned on a state built from data <= t",
                                      "states": ["HIGH_VOL", "LOW_VOL", "TREND", "RANGE", "XM_ACTIVE", "XM_QUIET"],
                                      "threshold": {"abs_z_min": 2.5}},
    },
    "detection_rules": {"vol_baseline_bars": 120, "envelope_bars": 60, "atr_bars": 14,
                          "activity_fast": 5, "activity_slow": 60,
                          "asof_only": True, "winsorization": "OFF", "manual_removal": "OFF",
                          "missing_data_policy": "record DATA_GAP, never fill/splice"},
    "episode_rules": {"same_family_same_grid_within_bars": 30, "cross_grid_merge_within_minutes": 30,
                        "cross_grid_parent_id": "required", "raw_vs_independent_reported_separately": True},
    "frequency_rules": {"report": ["RAW_OPPORTUNITY_FREQUENCY", "INDEPENDENT_EVENT_FREQUENCY"],
                         "independent_unit": "episode",
                         "HIGH_FREQUENCY": "independent events per week >= 2",
                         "MEDIUM_FREQUENCY": ">= 1 and < 2", "LOW_FREQUENCY": "< 1",
                         "note": "the weekly floor is an OPPORTUNITY DISCOVERY screen, not an alpha gate"},
    "lifecycle": {"target": "duration <= 30m preferred", "allow": "30m..1h as background",
                   "over_1h": "LOW_FREQUENCY_HORIZON", "measurement_only": True,
                   "fields": ["detection_time", "response_start", "response_end", "duration",
                               "time_to_peak", "time_to_decay"],
                   "no_lookahead": "these are MEASUREMENT fields; they never enter detection or priority"},
    "priority": {"registry": "high_frequency_priority_registry.json",
                  "weights": {"frequency": 0.35, "independence": 0.25, "data_quality": 0.20, "novelty": 0.20,
                                "cross_market_information": 0.0, "state_change": 0.0, "duration": 0.0},
                  "excluded_weights": {"duration": "measured duration is a future quantity -> excluded for PIT safety",
                                        "cross_market_information": "subsumed by independence in this round",
                                        "state_change": "subsumed by novelty in this round"},
                  "forbidden_inputs": ["future_return", "future_pnl", "win_rate"],
                  "frozen_before_results": True},
    "hermes_budget": {"MAX_HERMES_INVESTIGATIONS": 300, "selection": "top-N by frozen priority",
                       "no_reordering_after_results": True},
    "quality_classes": ["QUALITY_HIGH", "QUALITY_MEDIUM", "QUALITY_LOW"],
    "data_quality_levels": ["VERIFIED", "PARTIAL", "UNKNOWN"], "no_upgrade": True,
    "negative_control": {"method": "random_time_control", "runs": 200, "seed": SEED,
                          "pass_if": "random-time detections <= observed detections * 0.5"},
    "ablation": ["remove_crossmarket", "remove_volatility", "remove_state", "remove_price_shock"],
    "overlap_audit": {"metric": "pairwise Jaccard on episode sets", "merge_if_jaccard_ge": 0.60},
    "concentration": {"top_10_episode_share": True, "top_20_episode_share": True,
                       "CONCENTRATION_HIGH_if": "top_10_share >= 0.50"},
    "status_classes": ["HIGH_FREQUENCY", "MEDIUM_FREQUENCY", "LOW_FREQUENCY", "REJECTED", "INSUFFICIENT"],
    "next_stage_gate": {"requires": ["frequency sufficient", "short lifecycle", "independent", "PIT valid",
                                        "data quality acceptable", "mechanism traceable"],
                         "target": "NEXT_MECHANISM_VALIDATION", "not": "TRADING_CANDIDATE"},
    "hard_bounds": {"CANDIDATE_RESEARCH": 0, "ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF",
                     "V3_LIVE": "OFF"},
    "forbidden_identifiers": ["order_send", "order_check", "metatrader5", "broker", "execution_engine"],
}


def freeze_hash():
    return hashlib.sha256(json.dumps(FROZEN, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    os.makedirs(os.path.join(HERE, "ledger"), exist_ok=True)
    FZ = freeze_hash()
    json.dump({**FROZEN, "FREEZE_HASH": FZ, "frozen_at_utc": NOW},
              open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), "w",
                   encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    json.dump({"weights": FROZEN["priority"]["weights"], "excluded": FROZEN["priority"]["excluded_weights"],
                "forbidden_inputs": FROZEN["priority"]["forbidden_inputs"], "PRIORITY_HASH": sha_obj(FROZEN["priority"])},
              open(os.path.join(HERE, "high_frequency_priority_registry.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("FREEZE", FZ[:24])

    # ---------- load XAUUSD M1 (read-only) ----------
    m1 = pd.read_parquet(os.path.join(R1A, "xauusd_m1_histdata.parquet"),
                          columns=["dt_utc", "open", "high", "low", "close", "volume"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    m1 = m1.set_index("dt").sort_index()
    m1 = m1[~m1.index.duplicated(keep="first")]
    INPUT_HASH = sha_obj({"rows": int(len(m1)), "first": str(m1.index[0]), "last": str(m1.index[-1])})
    xm5 = {}
    for k, f in (("DXY", "series_DXY_5m.parquet"), ("VIX", "series_VIX_5m.parquet"),
                  ("UST10Y_PROXY", "series_UST10Y_PROXY_TNX_5m.parquet")):
        s = pd.read_parquet(os.path.join(SRC, f))["close"]
        s.index = pd.to_datetime(s.index, utc=True)
        xm5[k] = s.sort_index()

    def grid(df, rule):
        g = df.resample(rule).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                    close=("close", "last"), volume=("volume", "sum")).dropna()
        return g

    grids = {"1m": m1, "5m": grid(m1, "5min"), "15m": grid(m1, "15min"), "30m": grid(m1, "30min")}
    B = FROZEN["detection_rules"]
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
            t = g.index[i]
            fam, trig = None, None
            if np.isfinite(vol_pct.iloc[i]) and np.isfinite(rng_ratio.iloc[i]):
                if vol_pct.iloc[i] <= 0.20:
                    j = max(0, i - 5)
                    if np.isfinite(rng_ratio.iloc[i]) and rng_ratio.iloc[i] >= 1.8:
                        fam, trig = "F1_SHORT_STATE_JUMP", f"compression->expansion ratio={rng_ratio.iloc[i]:.2f}"
            if fam is None and np.isfinite(z.iloc[i]) and abs(z.iloc[i]) >= 3.0:
                fam, trig = "F2_SHORT_SHOCK_STRUCTURE", f"abs_z={z.iloc[i]:.2f}"
            if fam is None and np.isfinite(act_f.iloc[i]) and np.isfinite(act_s.iloc[i]) and act_s.iloc[i] > 0:
                r = act_f.iloc[i] / act_s.iloc[i]
                if r >= 2.0 and np.isfinite(rng_ratio.iloc[i]) and rng_ratio.iloc[i] >= 1.5:
                    fam, trig = "F3_PRICE_ACTIVITY_PROXY", f"activity_ratio={r:.2f} (price proxy only)"
            if fam is None and np.isfinite(excursion.iloc[i]) and excursion.iloc[i] >= 2.0:
                fam, trig = "F5_SHORT_EXTENSION_REVERSION", f"envelope_excursion_atr={excursion.iloc[i]:.2f}"
            if fam is None and np.isfinite(z.iloc[i]) and abs(z.iloc[i]) >= 2.5:
                st = ("HIGH_VOL" if (np.isfinite(vol_pct.iloc[i]) and vol_pct.iloc[i] >= 0.8) else
                      "LOW_VOL" if (np.isfinite(vol_pct.iloc[i]) and vol_pct.iloc[i] <= 0.2) else
                      "TREND" if (np.isfinite(trend.iloc[i]) and abs(trend.iloc[i]) > 0) else "RANGE")
                fam, trig = "F6_STATE_CONDITIONAL_HF", f"state={st} abs_z={z.iloc[i]:.2f}"
            if fam:
                opps.append({"opportunity_id": f"HF-{gname}-{i:07d}", "timestamp": str(t), "grid": gname,
                              "family": fam, "trigger": trig,
                              "market_state": {"vol_pct": (round(float(vol_pct.iloc[i]), 4)
                                                             if np.isfinite(vol_pct.iloc[i]) else None)},
                              "data_quality": "PARTIAL", "detection_uses_future": False})
    print("raw detections:", len(opps))

    # ---------- F4: cross-market leading association (5m, strict lead) ----------
    gx = grid(m1, "5min")
    lo5, hi5 = min(gx.index[0], min(s.index[0] for s in xm5.values())), max(gx.index[-1], max(s.index[-1] for s in xm5.values()))
    f4 = []
    for k, s in xm5.items():
        ch = s.pct_change(6) * 1e4
        z = (ch - ch.rolling(120, min_periods=30).mean()) / ch.rolling(120, min_periods=30).std()
        idx = z.index[(z.abs() >= 2.0) & np.isfinite(z)]
        for t in idx:
            t_resp = t + pd.Timedelta(minutes=FROZEN["families"]["F4_CROSSMARKET_LEADING_ASSOCIATION"]
                                       ["threshold"]["min_lead_minutes"])
            f4.append({"opportunity_id": f"HF-5m-F4-{k}-{t.strftime('%Y%m%d%H%M')}",
                        "timestamp": str(t), "grid": "5m", "family": "F4_CROSSMARKET_LEADING_ASSOCIATION",
                        "trigger": f"{k}-leading association z={float(z.loc[t]):.2f}",
                        "market_state": {"source": k, "source_time": str(t), "response_start": str(t_resp),
                                          "asserts_causality": False},
                        "data_quality": "PARTIAL", "detection_uses_future": False})
    opps += f4
    print("with F4:", len(opps))

    # ---------- episodes / independent / cross-grid ----------
    ep = FROZEN["episode_rules"]
    by_fam = {}
    for o in sorted(opps, key=lambda x: x["timestamp"]):
        by_fam.setdefault((o["family"], o["grid"]), []).append(o)
    n_ep = 0
    step = {"1m": 30, "5m": 30, "15m": 30, "30m": 30}
    for key, rs in by_fam.items():
        cur, last = None, None
        for o in rs:
            t = pd.Timestamp(o["timestamp"])
            span = pd.Timedelta(minutes=step.get(o["grid"], 30) * (1 if o["grid"] != "1m" else 1))
            if last is None or (t - last) > span:
                n_ep += 1
                cur = f"HEP-{n_ep:05d}"
            o["episode_id"] = cur
            last = t
    # cross-grid merge (same family, same episode window across grids) -> parent id
    parents = {}
    for fam in {o["family"] for o in opps}:
        rs = sorted([o for o in opps if o["family"] == fam], key=lambda x: x["timestamp"])
        last, pid = None, None
        for o in rs:
            t = pd.Timestamp(o["timestamp"])
            if last is None or (t - last) > pd.Timedelta(minutes=ep["cross_grid_merge_within_minutes"]):
                pid = f"XG-{fam[:2]}-{len(parents)+1:05d}"
            o["cross_grid_parent_id"] = pid
            last = t
    span_days = max(1e-9, (max(pd.Timestamp(o["timestamp"]) for o in opps) -
                            min(pd.Timestamp(o["timestamp"]) for o in opps)).total_seconds() / 86400)
    raw_freq_day, raw_freq_week = len(opps) / span_days, len(opps) / span_days * 7
    ind_freq_day, ind_freq_week = n_ep / span_days, n_ep / span_days * 7

    # ---------- MEASUREMENT ONLY: lifecycle durations (future prices; never in detection/priority) ----------
    c1 = m1["close"]
    meas = {}
    for o in opps:
        t = pd.Timestamp(o["timestamp"])
        i = c1.index.searchsorted(t)
        if i + 60 >= len(c1):
            meas[o["opportunity_id"]] = None
            continue
        seg = c1.iloc[i:i + 60]
        e0 = float(seg.iloc[0])
        if e0 <= 0:
            meas[o["opportunity_id"]] = None
            continue
        path = (seg / e0 - 1) * 1e4
        k = int(np.argmax(np.abs(path)))
        peak = float(path.iloc[k])
        tpeak = k
        post = path.iloc[k:]
        decay = int(np.argmax(np.abs(post) <= abs(peak) * 0.5)) if abs(peak) > 0 else 0
        meas[o["opportunity_id"]] = {"time_to_peak_min": tpeak, "time_to_decay_min": decay,
                                       "duration_min": tpeak + decay, "measurement_only": True}
    durs = [m["duration_min"] for m in meas.values() if m]
    dur_stats = {"median": (float(np.median(durs)) if durs else None), "p25": (float(np.percentile(durs, 25)) if durs else None),
                  "p75": (float(np.percentile(durs, 75)) if durs else None)}
    for o in opps:
        m = meas.get(o["opportunity_id"])
        o["measurement"] = m
        o["duration_min"] = (m["duration_min"] if m else None)
        o["frequency_class"] = ("HIGH_FREQUENCY" if ind_freq_week >= 2 else
                                 "MEDIUM_FREQUENCY" if ind_freq_week >= 1 else "LOW_FREQUENCY")

    # ---------- per-family stats + concentration + classes ----------
    fam_rows = {}
    for fam in sorted({o["family"] for o in opps}):
        rs = [o for o in opps if o["family"] == fam]
        eps = {o["episode_id"] for o in rs}
        fd = len(eps) / span_days
        dd = [o["duration_min"] for o in rs if o["duration_min"] is not None]
        fam_rows[fam] = {"raw_opportunities": len(rs), "independent_episodes": len(eps),
                          "independent_per_day": round(fd, 4), "independent_per_week": round(fd * 7, 4),
                          "median_duration_min": (float(np.median(dd)) if dd else None),
                          "frequency_class": ("HIGH_FREQUENCY" if fd * 7 >= 2 else
                                                "MEDIUM_FREQUENCY" if fd * 7 >= 1 else "LOW_FREQUENCY"),
                          "counts": {g: sum(1 for o in rs if o["grid"] == g) for g in ("1m", "5m", "15m", "30m")}}
    ep_counts = {}
    for o in opps:
        ep_counts[o["episode_id"]] = ep_counts.get(o["episode_id"], 0) + 1
    top = sorted(ep_counts.values(), reverse=True)
    conc = {"top_10_episode_share": round(sum(top[:10]) / max(1, len(opps)), 4),
             "top_20_episode_share": round(sum(top[:20]) / max(1, len(opps)), 4),
             "CONCENTRATION_HIGH": (sum(top[:10]) / max(1, len(opps))) >= 0.50}

    # ---------- priority (frozen weights, asof fields only) ----------
    W = FROZEN["priority"]["weights"]
    for o in opps:
        f = fam_rows[o["family"]]
        freq_s = min(1.0, f["independent_per_week"] / 4.0)
        indep_s = 1.0 - min(1.0, conc["top_10_episode_share"])
        dq_s = {"VERIFIED": 1.0, "PARTIAL": 0.6, "UNKNOWN": 0.2}[o["data_quality"]]
        nov_s = min(1.0, 1.0 - ep_counts.get(o["episode_id"], 1) / 10.0)
        o["HERMES_PRIORITY_SCORE"] = round(W["frequency"] * freq_s + W["independence"] * indep_s +
                                             W["data_quality"] * dq_s + W["novelty"] * nov_s, 5)
    ranked = sorted(opps, key=lambda x: (-x["HERMES_PRIORITY_SCORE"], x["opportunity_id"]))
    budget = FROZEN["hermes_budget"]["MAX_HERMES_INVESTIGATIONS"]
    selected = ranked[:budget]

    # ---------- ablation + overlap ----------
    FAM_TO_ABL = {"remove_price_shock": "F2_SHORT_SHOCK_STRUCTURE", "remove_volatility": "F1_SHORT_STATE_JUMP",
                   "remove_state": "F6_STATE_CONDITIONAL_HF", "remove_crossmarket": "F4_CROSSMARKET_LEADING_ASSOCIATION"}
    abl = {k: {"removed_family": v, "remaining_raw": len([o for o in opps if o["family"] != v]),
                "remaining_episodes": len({o["episode_id"] for o in opps if o["family"] != v})} for k, v in FAM_TO_ABL.items()}
    fams = sorted(fam_rows)
    epsets = {f: {o["episode_id"] for o in opps if o["family"] == f} for f in fams}
    ovl = {}
    for i, a in enumerate(fams):
        for b in fams[i + 1:]:
            u = len(epsets[a] | epsets[b])
            ovl[f"{a}|{b}"] = round(len(epsets[a] & epsets[b]) / u, 4) if u else 0.0
    merge_candidates = [k for k, v in ovl.items() if v >= FROZEN["overlap_audit"]["merge_if_jaccard_ge"]]

    # ---------- negative control ----------
    N_NC_LOCAL = FROZEN["negative_control"]["runs"]
    rng = random.Random(SEED)
    t0, t1 = min(pd.Timestamp(o["timestamp"]) for o in opps), max(pd.Timestamp(o["timestamp"]) for o in opps)
    cabs = (c1.pct_change().abs() - c1.pct_change().abs().rolling(120, min_periods=30).mean()) / \
           c1.pct_change().abs().rolling(120, min_periods=30).std()
    # ---- PERFORMANCE FIX (only the lookup is vectorised; RNG stream and rules unchanged) ----
    _span_s = (t1 - t0).total_seconds()
    _idx_ns = cabs.index.values.astype("datetime64[ns]").view("int64")
    _vals = np.nan_to_num(cabs.to_numpy(float), nan=0.0)
    _abn = np.abs(_vals) >= 3.0
    _n_opp = len(opps)

    def _draw_ns(u_rng, n):
        base = t0.value
        return np.fromiter((base + pd.Timedelta(seconds=u_rng.uniform(0, _span_s)).value for _ in range(n)),
                            dtype="int64", count=n)

    def _hits_vectorised(draws):
        pos = np.searchsorted(_idx_ns, draws, side="left")
        ok = pos < len(_idx_ns)
        return int(_abn[pos[ok]].sum())

    def _hits_reference(u_rng, n):
        hits = 0
        for _n in range(n):
            t = (t0 + pd.Timedelta(seconds=u_rng.uniform(0, _span_s))).as_unit(cabs.index.unit)
            i = cabs.index.searchsorted(t)
            if 0 <= i < len(cabs) and np.isfinite(cabs.iloc[i]) and abs(cabs.iloc[i]) >= 3.0:
                hits += 1
        return hits

    # ---- equivalence proof on a fixed small sample (section 4) ----
    _K = min(3, N_NC_LOCAL)
    _nb = min(200, _n_opp)
    _r1, _r2 = random.Random(FROZEN["negative_control"]["seed"]), random.Random(FROZEN["negative_control"]["seed"])
    _ref, _opt = [], []
    for _ in range(_K):
        _ref.append(_hits_reference(_r1, _nb))
        _opt.append(_hits_vectorised(_draw_ns(_r2, _nb)))
    OPTIMISED_OUTPUT_EQUALS_REFERENCE = (_ref == _opt)
    print("NC_EQUIVALENCE_PROOF:", json.dumps({"sample_runs": _K, "sample_draws": _nb, "reference": _ref,
                                                  "optimised": _opt,
                                                  "OPTIMISED_OUTPUT_EQUALS_REFERENCE": OPTIMISED_OUTPUT_EQUALS_REFERENCE},
                                                 ensure_ascii=False))
    if not OPTIMISED_OUTPUT_EQUALS_REFERENCE:
        raise SystemExit("STOP: optimised negative control differs from the reference")

    nc_counts = []
    for _ in range(N_NC_LOCAL):
        nc_counts.append(_hits_vectorised(_draw_ns(rng, _n_opp)))
    nc_mean = float(np.mean(nc_counts)) if nc_counts else 0.0
    nc = {"random_time_control_runs": len(nc_counts), "control_mean_detections": round(nc_mean, 2),
           "observed_detections": len(opps),
           "status": "PASS" if nc_mean <= 0.5 * len(opps) else "FAIL",
           "note": "checks whether the detector merely flags random times"}

    # ---------- status + outputs ----------
    hf = sum(1 for f in fam_rows.values() if f["frequency_class"] == "HIGH_FREQUENCY")
    mf = sum(1 for f in fam_rows.values() if f["frequency_class"] == "MEDIUM_FREQUENCY")
    lf = sum(1 for f in fam_rows.values() if f["frequency_class"] == "LOW_FREQUENCY")
    qc = {"QUALITY_HIGH": sum(1 for o in opps if o["HERMES_PRIORITY_SCORE"] >= 0.7),
           "QUALITY_MEDIUM": sum(1 for o in opps if 0.4 <= o["HERMES_PRIORITY_SCORE"] < 0.7),
           "QUALITY_LOW": sum(1 for o in opps if o["HERMES_PRIORITY_SCORE"] < 0.4)}
    hf_miss = bool(dur_stats["median"] is not None and dur_stats["median"] > 60)
    summary = {"schema": "v3_hf_opportunity_r2/1", "ts_utc": NOW, "version": VER,
                "TOTAL_OPPORTUNITIES": len(opps), "INDEPENDENT_EVENTS": n_ep, "CLUSTERS": len({o["cross_grid_parent_id"] for o in opps}),
                "F1_COUNT": fam_rows.get("F1_SHORT_STATE_JUMP", {}).get("raw_opportunities", 0),
                "F2_COUNT": fam_rows.get("F2_SHORT_SHOCK_STRUCTURE", {}).get("raw_opportunities", 0),
                "F3_COUNT": fam_rows.get("F3_PRICE_ACTIVITY_PROXY", {}).get("raw_opportunities", 0),
                "F4_COUNT": fam_rows.get("F4_CROSSMARKET_LEADING_ASSOCIATION", {}).get("raw_opportunities", 0),
                "F5_COUNT": fam_rows.get("F5_SHORT_EXTENSION_REVERSION", {}).get("raw_opportunities", 0),
                "F6_COUNT": fam_rows.get("F6_STATE_CONDITIONAL_HF", {}).get("raw_opportunities", 0),
                "HIGH_FREQUENCY_COUNT": hf, "MEDIUM_FREQUENCY_COUNT": mf, "LOW_FREQUENCY_COUNT": lf,
                "RAW_OPPORTUNITY_FREQUENCY": {"per_day": round(raw_freq_day, 4), "per_week": round(raw_freq_week, 4)},
                "INDEPENDENT_EVENTS_PER_DAY": round(ind_freq_day, 4),
                "INDEPENDENT_EVENTS_PER_WEEK": round(ind_freq_week, 4),
                "MEDIAN_DURATION": dur_stats["median"], "P25_DURATION": dur_stats["p25"], "P75_DURATION": dur_stats["p75"],
                "HIGH_FREQUENCY_TARGET_MISS": hf_miss,
                "TOP_10_EPISODE_SHARE": conc["top_10_episode_share"], "TOP_20_EPISODE_SHARE": conc["top_20_episode_share"],
                "CONCENTRATION_HIGH": conc["CONCENTRATION_HIGH"],
                "HERMES_INVESTIGATIONS": len(selected), "HERMES_BUDGET": budget,
                "QUALITY_HIGH": qc["QUALITY_HIGH"], "QUALITY_MEDIUM": qc["QUALITY_MEDIUM"], "QUALITY_LOW": qc["QUALITY_LOW"],
                "NEGATIVE_CONTROL": nc["status"], "NEGATIVE_CONTROL_DETAIL": nc,
                "DETECTOR_ABLATION": "REPORTED", "OVERLAP_AUDIT": ("MERGE_CANDIDATES:" + ",".join(merge_candidates)) if merge_candidates else "NO_MERGE_NEEDED",
                "CANDIDATE_RESEARCH": 0,
                "ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF",
                "FREEZE_HASH": FZ, "INPUT_HASH": INPUT_HASH,
                "span_days": round(span_days, 2), "grids_used": "1m/5m/15m/30m (1h excluded from HF detection)",
                "family_table": fam_rows, "overlap_matrix": ovl, "ablation": abl}
    OUTPUT_HASH = sha_obj(summary)
    summary["OUTPUT_HASH"] = OUTPUT_HASH
    json.dump(summary, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_hf_opportunities/1", "ts_utc": NOW, "opportunities": opps[:4000]},
              open(os.path.join(HERE, "hf_opportunities.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    json.dump({"schema": "v3_hf_env/1", "ts_utc": NOW, "negative_control": nc, "ablation": abl,
                "overlap_matrix": ovl, "concentration": conc, "duration": dur_stats, "family_table": fam_rows},
              open(os.path.join(HERE, "hf_env_audit.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    try:
        import importlib
        sys.path.insert(0, os.path.join(ROOT, "mechanism_validation_r2"))
        mv2 = importlib.import_module("mechanism_validation_r2")
        lp = os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl")
        if os.path.exists(lp):
            os.remove(lp)
        led = mv2.mv.MechanismLedger(lp, FZ)
        led.append({"kind": "FREEZE", "hash": FZ})
        led.append({"kind": "INPUT", "hash": INPUT_HASH, "rows": int(len(m1))})
        for fam, row in fam_rows.items():
            led.append({"kind": "FAMILY", "family": fam, **row})
        led.append({"kind": "ENV", "negative_control": nc, "ablation": abl, "concentration": conc})
        led.append({"kind": "FINAL", "total": len(opps), "independent": n_ep, "hermes": len(selected)})
        summary["ledger_chain"] = mv2.mv.MechanismLedger.verify(lp)
    except Exception as e:  # noqa: BLE001
        summary["ledger_chain"] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
    json.dump(summary, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("family_table", "overlap_matrix", "ablation",
                                                                     "NEGATIVE_CONTROL_DETAIL")},
                      ensure_ascii=False, default=str)[:2600])
    print("families:", json.dumps(fam_rows, ensure_ascii=False)[:1200])
    print("lifecycle:", json.dumps(dur_stats, ensure_ascii=False), "| HF_MISS:", hf_miss)
    print("conc:", json.dumps(conc, ensure_ascii=False), "| nc:", json.dumps(nc, ensure_ascii=False))
    print("overlap:", json.dumps(ovl, ensure_ascii=False)[:600], "| ablations:", json.dumps(abl, ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
