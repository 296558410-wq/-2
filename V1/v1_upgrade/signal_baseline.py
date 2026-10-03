# -*- coding: utf-8 -*-
"""v1_upgrade/signal_baseline.py — BASELINE_TRANSITION control arm (NOT Hermes, NOT alpha).

signal_family = argmax_successor( family(t) )      from the FROZEN dev transition table
order mapping  = NEW explicitly-defined minimal rule (this file is its frozen definition):
    DIRECTIONAL -> trade along the M15 trend sign
    RANGE/QUIET -> no trade
    SL = 1.0 x ATR(14) on M15 , TP = 1.5 x ATR(14) on M15 , lots = 0.01
"""
from __future__ import annotations

import collections
import hashlib
import json
import os

import pandas as pd

FAMILY = {"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL",
           "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE",
           "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}
H = 4
DEV_END = "2026-06-01"
LOTS = 0.01
SL_ATR = 1.0
TP_ATR = 1.5
ATR_N = 14
MAPPING_ID = "v1up-baseline-transition-order-map-v1"


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_table(cache_path):
    df = pd.read_parquet(cache_path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    fam = df["state"].map(FAMILY)
    cnt = collections.defaultdict(collections.Counter)
    for i in range(len(df) - H):
        if df["ts"].iloc[i] < pd.Timestamp(DEV_END + "T00:00Z") and isinstance(fam.iloc[i], str) and isinstance(fam.iloc[i + H], str):
            cnt[fam.iloc[i]][fam.iloc[i + H]] += 1
    table = {k: v.most_common(1)[0][0] for k, v in cnt.items() if v}
    detail = {k: dict(v) for k, v in cnt.items()}
    return table, detail


def freeze(reg_dir, cache_path):
    table, detail = build_table(cache_path)
    rec = {"mapping_id": MAPPING_ID, "family_map": FAMILY, "H": H, "dev_end": DEV_END,
            "successor_table": table, "counts": detail, "lots": LOTS, "sl_atr": SL_ATR, "tp_atr": TP_ATR, "atr_n": ATR_N,
            "order_rule": "DIRECTIONAL -> along M15 trend sign; RANGE/QUIET -> no trade",
            "disclaimer": "CONTROL ARM. NOT Hermes capability, NOT alpha, NOT the R8-B predictor."}
    rec["mapping_hash"] = sha_obj({k: v for k, v in rec.items() if k != "mapping_hash"})
    os.makedirs(reg_dir, exist_ok=True)
    p = os.path.join(reg_dir, "baseline_transition_mapping.json")
    json.dump(rec, open(p, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    return rec


def load_mapping(path):
    return json.load(open(path, encoding="utf-8"))


def signal_for_state(state_now, mapping):
    fam = FAMILY.get(str(state_now).upper())
    nxt = (mapping.get("successor_table") or {}).get(fam) if fam else None
    return {"family_now": fam, "signal_family": nxt, "known": fam is not None and nxt is not None}


def order_intent(signal, m15_trend20, atr, price, digits=2):
    """Return the frozen order mapping, or a no-trade reason."""
    if not signal.get("known"):
        return {"trade": False, "reason": "UNKNOWN_FAMILY"}
    if signal["signal_family"] != "DIRECTIONAL":
        return {"trade": False, "reason": f"FAMILY_{signal['signal_family']}_NO_TRADE"}
    if m15_trend20 is None or atr is None or atr <= 0:
        return {"trade": False, "reason": "MISSING_TREND_OR_ATR"}
    side = "LONG" if m15_trend20 > 0 else "SHORT"
    sl_d, tp_d = SL_ATR * atr, TP_ATR * atr
    if side == "LONG":
        sl, tp = price - sl_d, price + tp_d
    else:
        sl, tp = price + sl_d, price - tp_d
    return {"trade": True, "side": side, "lots": LOTS, "sl": round(sl, digits), "tp": round(tp, digits),
             "atr": round(atr, 4), "m15_trend20": m15_trend20, "mapping_id": MAPPING_ID}
