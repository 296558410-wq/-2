# -*- coding: utf-8 -*-
"""V3 Market Opportunity Discovery Engine — R1 core.

Design invariants (frozen for R1):
  * Market State is DESCRIPTIVE. No state variable is a trading signal.
  * Every feature is computed with rolling/expanding windows only -> asof-safe by construction.
  * Detection at bar t may use only data with timestamp <= t. post_event_observation is stored SEPARATELY
    and never feeds detection.
  * Opportunity != Alpha. No profit/win/edge field exists anywhere in this module.

Grids: 1h (624-day four-market overlap, primary) and 5m (63-day overlap, secondary).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

DETECTOR_VERSION = "R1.0.0"
SCHEMA_OPP = "v3_opportunity/1"
SCHEMA_STATE = "v3_market_state/1"

# ---------------------------------------------------------------- market state

def build_state(df: pd.DataFrame) -> pd.DataFrame:
    """df: indexed by UTC timestamp with columns xau, dxy, vix, tnx (tnx = UST10Y_PROXY)."""
    s = pd.DataFrame(index=df.index)
    x = df["xau"].astype(float)
    s["xau"] = x
    for k in (1, 3, 5, 15, 30, 60):
        s[f"return_{k}m"] = x.pct_change(k) * 1e4
    s["range_5"] = (x.rolling(5).max() - x.rolling(5).min()) / x * 1e4
    s["atr_range_14"] = (x.rolling(14).max() - x.rolling(14).min()) / x * 1e4
    s["dist_from_high_60"] = (x - x.rolling(60).max()) / x * 1e4
    s["dist_from_low_60"] = (x - x.rolling(60).min()) / x * 1e4
    s["trend_slope_20"] = x.rolling(20).apply(lambda v: np.polyfit(np.arange(len(v)), v, 1)[0] / v.mean() * 1e4,
                                                raw=True)

    # volatility states (asof-safe rolling quantiles; no full-history statistics)
    for k in (1, 5, 15, 30, 60):
        s[f"vol_{k}m"] = s["return_1m"].rolling(k).std()
    rv = s["return_1m"].rolling(30).std()
    s["vol_ratio_5_30"] = s["return_1m"].rolling(5).std() / rv.replace(0, np.nan)
    q = rv.rolling(240, min_periods=60)
    q33 = q.apply(lambda v: np.nanpercentile(v, 33), raw=True)
    q66 = q.apply(lambda v: np.nanpercentile(v, 66), raw=True)
    q95 = q.apply(lambda v: np.nanpercentile(v, 95), raw=True)
    s["vol_pct_240"] = q.apply(lambda v: float(np.mean(v <= v[-1])), raw=True)
    state = pd.Series("VOL_NORMAL", index=rv.index, dtype=object)
    state = state.mask(rv >= q95, "VOL_EXTREME")
    state = state.mask((rv >= q66) & (rv < q95), "VOL_EXPANSION")
    state = state.mask(rv < q33, "VOL_CONTRACTION")
    s["vol_state"] = state

    # cross-market (each source named explicitly; tnx is always the PROXY)
    for name, col in (("DXY", "dxy"), ("VIX", "vix"), ("UST10Y_PROXY", "tnx")):
        v = df[col].astype(float)
        for k in (5, 15, 60):
            ch = v.pct_change(k) * 1e4
            s[f"{name}_RETURN_{k}M"] = ch
            s[f"{name}_RETURN_{k}M_z"] = (ch - ch.rolling(240, min_periods=60).mean()) / ch.rolling(240, min_periods=60).std()
        s[f"{name}_VOL_STATE"] = v.pct_change().rolling(30).std()

    # divergence states (relationship deviation, NOT a direction call)
    for name in ("DXY", "VIX", "UST10Y_PROXY"):
        ez = s[f"{name}_RETURN_60M_z"]
        xz = s["return_60m"] / s["return_60m"].rolling(240, min_periods=60).std()
        div = (ez.abs() >= 2.0) & (xz.abs() <= 0.5)
        s[f"XAU_vs_{name}"] = np.where(div, "CROSSMARKET_DIVERGENCE", "CROSSMARKET_NORMAL")
        s.loc[ez.abs() >= 3.0, f"XAU_vs_{name}"] = "CROSSMARKET_EXTREME"

    # time state
    s["utc_hour"] = df.index.hour
    s["utc_minute"] = df.index.minute
    s["day_of_week"] = df.index.dayofweek
    h = df.index.hour
    s["session_bucket"] = np.where((h >= 0) & (h < 7), "Asia", np.where((h >= 7) & (h < 13), "London",
                             np.where((h >= 13) & (h < 21), "NewYork", "Overlap")))

    # event state: no reliable PIT event coverage in this window -> explicitly UNKNOWN
    s["EVENT_STATE"] = "EVENT_UNKNOWN"
    s["EVENT_PIT"] = "UNKNOWN"
    s["data_quality"] = np.where(df[["xau", "dxy", "vix", "tnx"]].notna().all(axis=1), "PARTIAL", "UNKNOWN")
    return s


# ---------------------------------------------------------------- detectors

REGISTRY = [
    {"detector_id": "D1_STATE_BREAK", "detector_name": "State Break", "version": DETECTOR_VERSION,
     "description": "current state deviates strongly from its recent rolling distribution",
     "input_features": ["return_60m", "vol_pct_240", "vol_state"],
     "threshold_definition": {"return_z_abs": 3.0, "vol_pct": 0.95}, "lookback_definition": "rolling 240 bars (min 60)",
     "cooldown_bars": 6, "clustering_rule": "consecutive same-type detections within 3 bars join one cluster",
     "data_dependencies": ["xau"], "output_type": "OPP_STATE_BREAK"},
    {"detector_id": "D2_STATE_TRANSITION", "detector_name": "State Transition", "version": DETECTOR_VERSION,
     "description": "volatility regime transition between adjacent bars",
     "input_features": ["vol_state"], "threshold_definition": {"transitions": ["VOL_NORMAL->VOL_EXTREME",
                                                                                "VOL_CONTRACTION->VOL_EXPANSION",
                                                                                "VOL_EXTREME->VOL_NORMAL"]},
     "lookback_definition": "1 bar", "cooldown_bars": 6, "clustering_rule": "same as D1",
     "data_dependencies": ["xau"], "output_type": "OPP_STATE_TRANSITION"},
    {"detector_id": "D3_CROSSMARKET_SHOCK", "detector_name": "Cross-Market Shock", "version": DETECTOR_VERSION,
     "description": "external market shows an abnormal move; XAU response is observed only after the fact",
     "input_features": ["DXY_RETURN_60M_z", "VIX_RETURN_60M_z", "UST10Y_PROXY_RETURN_60M_z"],
     "threshold_definition": {"abs_z": 2.0}, "lookback_definition": "rolling 240 bars",
     "cooldown_bars": 6, "clustering_rule": "same as D1", "data_dependencies": ["dxy", "vix", "tnx"],
     "output_type": "OPP_CROSSMARKET_SHOCK"},
    {"detector_id": "D4_CROSSMARKET_DIVERGENCE", "detector_name": "Cross-Market Divergence", "version": DETECTOR_VERSION,
     "description": "external shock without a normal XAU response (or the reverse)",
     "input_features": ["XAU_vs_DXY", "XAU_vs_VIX", "XAU_vs_UST10Y_PROXY"],
     "threshold_definition": {"external_abs_z": 2.0, "xau_abs_z_max": 0.5}, "lookback_definition": "rolling 240 bars",
     "cooldown_bars": 6, "clustering_rule": "same as D1", "data_dependencies": ["xau", "dxy", "vix", "tnx"],
     "output_type": "OPP_CROSSMARKET_DIVERGENCE"},
    {"detector_id": "D5_VOL_TRANSITION", "detector_name": "Volatility Regime Transition", "version": DETECTOR_VERSION,
     "description": "low->abnormal volatility or abnormally fast volatility decay",
     "input_features": ["vol_pct_240", "vol_ratio_5_30"],
     "threshold_definition": {"low": 0.2, "high": 0.9, "ratio_jump": 2.0, "ratio_decay": 0.5},
     "lookback_definition": "rolling 240 bars", "cooldown_bars": 6, "clustering_rule": "same as D1",
     "data_dependencies": ["xau"], "output_type": "OPP_VOL_TRANSITION"},
]


def _z(s, k=240, m=60):
    return (s - s.rolling(k, min_periods=m).mean()) / s.rolling(k, min_periods=m).std()


def detect(state: pd.DataFrame) -> list[dict]:
    """Deterministic, asof-safe detection. Returns opportunity records (detection fields only)."""
    out = []
    rz = _z(state["return_60m"])
    vp = state["vol_pct_240"]
    vs = state["vol_state"]
    for i in range(len(state)):
        t = state.index[i]
        trig, otype, det = None, None, None

        if np.isfinite(rz.iloc[i]) and abs(rz.iloc[i]) >= 3.0:
            otype, det = "OPP_STATE_BREAK", f"return_60m z={rz.iloc[i]:.2f}"
        elif np.isfinite(vp.iloc[i]) and vp.iloc[i] >= 0.95:
            otype, det = "OPP_STATE_BREAK", f"vol_pct={vp.iloc[i]:.2f}"
        if otype is None and i > 0 and isinstance(vs.iloc[i - 1], str):
            tr = f"{vs.iloc[i-1]}->{vs.iloc[i]}"
            if tr in ("VOL_NORMAL->VOL_EXTREME", "VOL_CONTRACTION->VOL_EXPANSION", "VOL_EXTREME->VOL_NORMAL"):
                otype, det = "OPP_STATE_TRANSITION", tr
        if otype is None:
            for nm in ("DXY", "VIX", "UST10Y_PROXY"):
                zz = state[f"{nm}_RETURN_60M_z"].iloc[i]
                if np.isfinite(zz) and abs(zz) >= 2.0:
                    otype, det = "OPP_CROSSMARKET_SHOCK", f"{nm} z={zz:.2f}"
                    break
        if otype is None:
            for nm in ("DXY", "VIX", "UST10Y_PROXY"):
                if state[f"XAU_vs_{nm}"].iloc[i] in ("CROSSMARKET_DIVERGENCE", "CROSSMARKET_EXTREME"):
                    otype, det = "OPP_CROSSMARKET_DIVERGENCE", f"XAU_vs_{nm}={state[f'XAU_vs_{nm}'].iloc[i]}"
                    break
        if otype is None:
            r5, r30 = state["vol_ratio_5_30"].iloc[i], None
            if np.isfinite(vp.iloc[i]) and np.isfinite(r5):
                if vp.iloc[i] < 0.2 and r5 >= 2.0:
                    otype, det = "OPP_VOL_TRANSITION", f"low->expansion ratio={r5:.2f}"
                elif vp.iloc[i] > 0.9 and r5 <= 0.5:
                    otype, det = "OPP_VOL_TRANSITION", f"extreme->decay ratio={r5:.2f}"
        if otype is None:
            continue

        snap = {c: (None if (isinstance(state[c].iloc[i], float) and not np.isfinite(state[c].iloc[i]))
                    else state[c].iloc[i]) for c in state.columns}
        fm = {k: v for k, v in snap.items() if isinstance(v, (int, float, np.floating, np.integer)) and v is not None}
        ctx = hashlib.sha256(json.dumps({"t": str(t), "type": otype, "det": det, "feat": {k: round(float(v), 6) for k, v in fm.items()}},
                                          sort_keys=True).encode()).hexdigest()
        out.append({"detected_at": str(t), "opportunity_type": otype, "trigger": det,
                     "market_state": {k: str(snap.get(k)) for k in ("vol_state", "session_bucket", "EVENT_STATE", "EVENT_PIT")},
                     "trigger_features": sorted(fm.keys())[:14], "feature_values": {k: round(float(v), 6) for k, v in fm.items()},
                     "data_sources": ["XAUUSD=HistData M1", "DXY=Yahoo", "VIX=Yahoo", "UST10Y_PROXY=Yahoo^TNX"],
                     "data_quality": str(snap.get("data_quality")),
                     "context_hash": ctx, "detection_version": DETECTOR_VERSION})
    return out


# ---------------------------------------------------------------- scoring / clustering

def score(rec: dict, state: pd.DataFrame, all_recs: list[dict]) -> dict:
    """Descriptive scores only. No profit/expectancy/win field exists by design."""
    i = state.index.get_loc(pd.Timestamp(rec["detected_at"]))
    look = state.iloc[max(0, i - 240):i + 1]
    ext = 0.0
    for k in ("return_60m", "vol_pct_240"):
        if k in look:
            v = look[k].dropna()
            if len(v) > 5:
                ext = max(ext, float(abs(v.iloc[-1] - v.mean()) / (v.std() + 1e-9)) / 3.0)
    novel = float(np.mean([np.mean(look[k].dropna() <= (look[k].dropna().iloc[-1] if len(look[k].dropna()) else 0))
                            for k in ("vol_pct_240",) if k in look])) if "vol_pct_240" in look else 0.5
    same = [r for r in all_recs if r["opportunity_type"] == rec["opportunity_type"]]
    days = max(1.0, (state.index[-1] - state.index[0]).total_seconds() / 86400)
    rep = min(1.0, len(same) / days)
    cm = 1.0 if rec["opportunity_type"].startswith("OPP_CROSSMARKET") else 0.0
    dq = {"VERIFIED": 1.0, "PARTIAL": 0.6, "UNKNOWN": 0.2}.get(rec["data_quality"], 0.2)
    return {"novelty_score": round(float(min(1.0, novel)), 4), "extremeness_score": round(float(min(1.0, ext)), 4),
             "crossmarket_score": cm, "data_quality_score": dq, "repeatability_score": round(float(rep), 4)}


def cluster(recs: list[dict]) -> list[dict]:
    """Cooldown + clustering: adjacent same-type detections join one cluster (fixed, interpretable rule)."""
    reg = {d["detector_id"]: d for d in REGISTRY}
    otype2det = {d["output_type"]: d for d in REGISTRY}
    last_seq: dict[str, list] = {}
    n = 0
    for r in recs:
        det = otype2det.get(r["opportunity_type"], {"cooldown_bars": 6})
        key = r["opportunity_type"]
        lst = last_seq.setdefault(key, [])
        t = pd.Timestamp(r["detected_at"])
        if lst and (t - pd.Timestamp(lst[-1]["detected_at"])).total_seconds() <= 3 * 3600:
            r["cluster_id"] = lst[-1]["cluster_id"]
            r["is_cluster_continuation"] = True
        else:
            lst.clear()
            lst.append(r)
            n += 1
            r["cluster_id"] = f"OPP_CLUSTER_{n:03d}"
            r["is_cluster_continuation"] = False
        lst.append(r)
    return recs


# ---------------------------------------------------------------- ledger

class Ledger:
    """Append-only JSONL with a sha256 hash chain. Supports replay + audit."""

    def __init__(self, path: str):
        self.path = path
        self._prev = "GENESIS"
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    self._prev = json.loads(line)["chain_hash"]

    def append(self, rec: dict) -> str:
        body = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256((self._prev + body).encode()).hexdigest()
        row = {"seq": self._next_seq(), "prev_hash": self._prev, "chain_hash": h, "payload": rec}
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        self._prev = h
        return h

    def _next_seq(self) -> int:
        if not os.path.exists(self.path):
            return 0
        return sum(1 for l in open(self.path, encoding="utf-8") if l.strip())

    @staticmethod
    def verify(path: str) -> dict:
        prev, n, ok = "GENESIS", 0, True
        bad = None
        if not os.path.exists(path):
            return {"rows": 0, "chain_ok": True, "bad_seq": None}
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            body = json.dumps(row["payload"], sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256((prev + body).encode()).hexdigest()
            if h != row["chain_hash"] or row["prev_hash"] != prev:
                ok, bad = False, row["seq"]
                break
            prev, n = h, n + 1
        return {"rows": n, "chain_ok": ok, "bad_seq": bad}


# ---------------------------------------------------------------- hermes

def hermes_review(rec: dict, state: pd.DataFrame, hist: pd.DataFrame) -> dict:
    """Hermes receives an Opportunity Record and answers A-E. Never BUY/SELL/LIVE."""
    t = pd.Timestamp(rec["detected_at"])
    pre = state.loc[state.index < t].tail(6)
    post = state.loc[state.index > t].head(6)       # OBSERVATION ONLY - never used by detection
    hist_same = [r for r in hist if r["opportunity_type"] == rec["opportunity_type"]]
    days = max(1.0, (state.index[-1] - state.index[0]).total_seconds() / 86400)
    # descriptive repeat statistics (no returns, no edge)
    fwd = []
    for r in hist_same:
        tt = pd.Timestamp(r["detected_at"])
        a = state.loc[state.index > tt, "return_60m"]
        if len(a):
            fwd.append(float(a.iloc[0]))
    fwd = np.array(fwd)
    A = (f"at {rec['detected_at']} the engine recorded {rec['opportunity_type']} ({rec['trigger']}); "
          f"vol_state={rec['market_state'].get('vol_state')}, session={rec['market_state'].get('session_bucket')}")
    B = ["volatility-regime mechanics (vol clustering / mean reversion of vol)",
          "cross-asset information flow (DXY/VIX/UST10Y_PROXY leading or lagging XAUUSD)",
          "liquidity/session structure (Asia vs London vs NY behaviour)",
          "measurement artifact (semantics UNKNOWN: bar open/close, and UST10Y_PROXY is not the official series)"]
    C = ["the same state occurs at a similar rate in random windows (permutation idea)",
          "the pattern may be a data artifact from mixed sources (HistData XAUUSD vs Yahoo externals)",
          "the observation window may be too short (624d at 1h / 63d at 5m)",
          "selection bias: only states that look 'abnormal' get reviewed"]
    D = {"same_type_historical_count": len(hist_same), "per_day": round(len(hist_same) / days, 4),
          "descriptive_next_60m_move_bp": {"n": int(len(fwd)),
                                             "mean": (round(float(fwd.mean()), 3) if len(fwd) else None),
                                             "median": (round(float(np.median(fwd)), 3) if len(fwd) else None),
                                             "note": "DESCRIPTIVE ONLY - not an edge, not a signal"},
          "recurring": bool(len(hist_same) >= 5)}
    if D["same_type_historical_count"] < 5:
        decision, why = "INSUFFICIENT_EVIDENCE", "fewer than 5 historical occurrences of this state"
    elif rec["data_quality"] == "UNKNOWN":
        decision, why = "INSUFFICIENT_EVIDENCE", "data_quality=UNKNOWN"
    else:
        decision, why = "INVESTIGATE", "state is recurrent and the data quality allows investigation"
    return {"A_what_happened": A, "B_mechanism_hypotheses": B, "C_counter_evidence": C,
             "D_historical_repetition": D, "E_decision": decision, "E_reason": why,
             "semantic_dependency": ({"SEMANTIC_DEPENDENCY": "UNKNOWN", "depends_on": ["XAUUSD bar open/close semantics",
                                                                                       "UST10Y_PROXY is not official UST10Y"]}
                                      if rec["opportunity_type"].startswith("OPP_CROSSMARKET") else {"SEMANTIC_DEPENDENCY": "PARTIAL"}),
             "observation_only": {"pre_event_context_tail": str(pre[["return_60m"]].tail(1).to_dict()),
                                    "post_event_observation_head": str(post[["return_60m"]].head(1).to_dict())}}


# ---------------------------------------------------------------- replay

def replay(state_full: pd.DataFrame, cut: int) -> tuple[list[dict], list[dict]]:
    """Strict replay: mask everything after `cut`, detect, and compare with the full-history run."""
    det_cut = detect(state_full.iloc[:cut + 1])
    return det_cut, detect(state_full)
