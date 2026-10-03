# -*- coding: utf-8 -*-
"""V3 deterministic PIT-safe signal generation (§6/§7/§15). No randomness, no hidden state."""
from __future__ import annotations
import hashlib
import json

import numpy as np
import pandas as pd

STRATEGY_VERSION = "v3-strategy/0.1.0"
SIGNAL_VERSION = "v3-signal/0.1.0"
SYMBOL = "XAUUSD"
EXECUTION_DELAY = "next bar open (t+1 bar) — never the signal bar close"


def _feature_hash(row_dict):
    return hashlib.sha256(json.dumps(row_dict, sort_keys=True, default=str, separators=(",", ":"))
                           .encode()).hexdigest()[:32]


def prepare(bars):
    """PIT features. Every column at row t uses only bars <= t (no shift(-n), no centred windows)."""
    b = bars.copy().reset_index(drop=True)
    b["ret"] = b["mid_close"].pct_change()
    b["sigma"] = b["ret"].rolling(60, min_periods=20).std()
    b["atr_pct"] = (b["mid_high"] - b["mid_low"]).rolling(60, min_periods=20).mean() / b["mid_close"]
    b["ema_fast"] = b["mid_close"].ewm(span=20, adjust=False).mean()
    b["ema_slow"] = b["mid_close"].ewm(span=50, adjust=False).mean()
    b["bb_mid"] = b["mid_close"].rolling(20, min_periods=10).mean()
    b["bb_sd"] = b["mid_close"].rolling(20, min_periods=10).std()
    b["bb_bw"] = (4.0 * b["bb_sd"]) / b["bb_mid"]
    b["bw_q20"] = b["bb_bw"].rolling(120, min_periods=40).quantile(0.20)
    b["spr_z"] = ((b["spread_mean"] - b["spread_mean"].rolling(120, min_periods=40).mean())
                   / b["spread_mean"].rolling(120, min_periods=40).std())
    b["tick_z"] = ((b["n_ticks"] - b["n_ticks"].rolling(120, min_periods=40).mean())
                    / b["n_ticks"].rolling(120, min_periods=40).std())
    b["vol_tercile"] = pd.qcut(b["atr_pct"].rank(method="first"), 3, labels=[0, 1, 2]) if b["atr_pct"].notna().sum() > 3 else np.nan
    return b


def _mk(b, i, direction, hyp, conf, reason):
    ts = str(b.at[i, "ts_utc"])
    feat = {"close": round(float(b.at[i, "mid_close"]), 4), "sigma": round(float(b.at[i, "sigma"] or 0), 8),
            "spread": round(float(b.at[i, "spread_mean"] or 0), 5), "n_ticks": int(b.at[i, "n_ticks"])}
    return {"i": int(i), "timestamp": ts, "direction": direction, "hypothesis_id": hyp,
            "confidence": round(float(conf), 4), "reason": reason, "entry_reference": float(b.at[i, "mid_close"]),
            "feature_snapshot_hash": _feature_hash(feat), "data_cutoff": ts,
            "execution_delay": EXECUTION_DELAY, "strategy_version": STRATEGY_VERSION,
            "signal_version": SIGNAL_VERSION, "feat": feat}


def generate(b, hyp_id):
    """Return the deterministic signal list for one frozen hypothesis."""
    out = []
    n = len(b)
    for i in range(n - 1):
        r = b.iloc[i]
        if not np.isfinite(r.get("sigma", np.nan)) or r["sigma"] == 0:
            continue
        d, conf, why = None, 0.0, ""
        if hyp_id == "H01_1M_SIGMA_FADE":
            z = r["ret"] / r["sigma"]
            if abs(z) >= 2.5:
                d = "SHORT" if z > 0 else "LONG"; conf = min(abs(z) / 5.0, 1.0); why = "2.5-sigma 1m move fade"
        elif hyp_id == "H02_5M_RANGE_BREAKOUT":
            hi = b["mid_high"].iloc[max(0, i - 20):i].max(); lo = b["mid_low"].iloc[max(0, i - 20):i].min()
            if i >= 20:
                if r["mid_close"] > hi:
                    d, conf, why = "LONG", 0.5, "close above prior 20-bar high"
                elif r["mid_close"] < lo:
                    d, conf, why = "SHORT", 0.5, "close below prior 20-bar low"
        elif hyp_id == "H03_LONDON_OPEN_MOMENTUM":
            if r["ts_utc"].hour == 7 and r["ts_utc"].minute == 0:
                d = "LONG" if r["ret"] > 0 else "SHORT"; conf = 0.4; why = "London open bar follow"
        elif hyp_id == "H04_LOWVOL_SIGMA_FADE":
            if r.get("vol_tercile") == 0:
                z = r["ret"] / r["sigma"]
                if abs(z) >= 2.0:
                    d = "SHORT" if z > 0 else "LONG"; conf = 0.4; why = "low-vol 2-sigma fade"
        elif hyp_id == "H05_SPREAD_SPIKE_FADE":
            if np.isfinite(r.get("spr_z", np.nan)) and r["spr_z"] >= 2.0 and abs(r["ret"]) > 0:
                d = "SHORT" if r["ret"] > 0 else "LONG"; conf = 0.4; why = "spread-spike fade"
        elif hyp_id == "H06_EMA_TREND_PULLBACK":
            if r["ema_fast"] > r["ema_slow"] and r["mid_low"] <= r["ema_fast"] and r["mid_close"] >= r["ema_fast"]:
                d, conf, why = "LONG", 0.5, "uptrend pullback to EMA20"
            elif r["ema_fast"] < r["ema_slow"] and r["mid_high"] >= r["ema_fast"] and r["mid_close"] <= r["ema_fast"]:
                d, conf, why = "SHORT", 0.5, "downtrend pullback to EMA20"
        elif hyp_id == "H07_ROUND_LEVEL_REJECTION":
            lvl = round(r["mid_close"] / 10.0) * 10.0
            if abs(r["mid_close"] - lvl) <= 0.40 and r["mid_high"] >= lvl > r["mid_close"]:
                d, conf, why = "SHORT", 0.35, "failed test of round level (from above)"
            elif abs(r["mid_close"] - lvl) <= 0.40 and r["mid_low"] <= lvl < r["mid_close"]:
                d, conf, why = "LONG", 0.35, "failed test of round level (from below)"
        elif hyp_id == "H08_SQUEEZE_BREAKOUT":
            if np.isfinite(r.get("bb_bw", np.nan)) and np.isfinite(r.get("bw_q20", np.nan)) and r["bb_bw"] <= r["bw_q20"]:
                if r["mid_close"] > r["bb_mid"] + 2.0 * r["bb_sd"]:
                    d, conf, why = "LONG", 0.4, "squeeze expansion up"
                elif r["mid_close"] < r["bb_mid"] - 2.0 * r["bb_sd"]:
                    d, conf, why = "SHORT", 0.4, "squeeze expansion down"
        elif hyp_id == "H09_ROLLOVER_REVERSAL":
            if r["ts_utc"].hour in (21, 22) and i >= 30:
                pm = b["mid_close"].iloc[i] - b["mid_close"].iloc[i - 30]
                if abs(pm) > 0:
                    d = "SHORT" if pm > 0 else "LONG"; conf = 0.35; why = "rollover fade of prior 30m move"
        elif hyp_id == "H10_DXY_CONFIRMED_REVERSAL":
            continue  # DATA_REQUIRED: no PIT-sourced DXY series is registered (see report §2)
        elif hyp_id == "H11_TICKRATE_SPIKE_FADE":
            if np.isfinite(r.get("tick_z", np.nan)) and r["tick_z"] >= 2.0 and abs(r["ret"]) > 0:
                d = "SHORT" if r["ret"] > 0 else "LONG"; conf = 0.35; why = "tick-rate spike fade"
        elif hyp_id == "H12_DAILY_GAP_FADE":
            if i >= 1 and r["ts_utc"].hour == 22 and r["ts_utc"].minute == 0:
                gap_bp = (b["mid_close"].iloc[i - 1] and
                           (r["mid_open"] - b["mid_close"].iloc[i - 1]) / b["mid_close"].iloc[i - 1] * 1e4)
                if gap_bp is not None and abs(gap_bp) >= 5.0:
                    d = "SHORT" if gap_bp > 0 else "LONG"; conf = 0.3; why = "daily gap fade"
        if d:
            out.append(_mk(b, i, d, hyp_id, conf, why))
    return out
