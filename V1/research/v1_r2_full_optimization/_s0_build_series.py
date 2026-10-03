# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION — STAGE 0: BUILD + CACHE series (§13/§15/§40).

Builds STATE v2 (frozen label + k=2 lifecycle), the EVENT layer, dwell, ambiguity rate, price features
and MTF context on the 20-month XAUUSD M15 series, and caches them so later stages never re-run the
O(n^2) frozen labeler. Return-free. Writes ONLY under v1_r2_full_optimization/."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization")
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation")
R1MOD = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade", "_v1r2_phaseB_R1.py")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
NOW = datetime.now(timezone.utc).isoformat()


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def hysteresis(seq, k=2):
    out = [seq[0]]; cur = seq[0]; pend = None; plen = 0
    for x in seq[1:]:
        if x == cur:
            out.append(cur); pend = None; plen = 0
        else:
            plen = plen + 1 if pend == x else 1
            pend = x
            if plen >= k:
                cur = x; out.append(cur); pend = None; plen = 0
            else:
                out.append(cur)
    return out


def event_of(r):
    ps, cs, mom, reg = r["PRICE_STRUCTURE"], r["CANDLE_STRUCTURE"], r["MOMENTUM"], r["REGIME"]
    if ps == "FAILED_BREAK":
        return "FAILED_BREAK"
    if ps == "BREAK_CONFIRMED":
        return "BREAK"
    if ps == "BREAK_ATTEMPT":
        return "BREAK_ATTEMPT"
    if ps == "RETEST":
        return "RETEST"
    if cs == "REJECTION":
        return "REJECTION"
    if cs == "ENGULFING":
        return "ACCEPTANCE"
    if reg == "EXPANSION":
        return "VOL_EXPANSION"
    if reg == "COMPRESSION":
        return "VOL_CONTRACTION"
    if mom == "ACCELERATING":
        return "MOM_ACCELERATION"
    if mom == "DECELERATING":
        return "MOM_DECELERATION"
    return "NONE"


def main():
    mod = load_mod("c15", os.path.join(C15, "_c1_5_run.py"))
    r1 = load_mod("r1", R1MOD)
    m1 = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    m1 = m1.set_index("dt").sort_index()
    g = m1.resample("15min")
    m15 = pd.DataFrame({"o": g["open"].first(), "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()}).dropna()
    n = len(m15)
    print("M15 bars:", n, "| range:", m15.index.min(), m15.index.max())
    rows = mod.label_series(m15, "M15")
    frozen = [r["MARKET_BEHAVIOR"] for r in rows]
    events = [event_of(r) for r in rows]
    state = hysteresis(frozen, 2)
    dw = np.zeros(n, int); c = 1
    for i in range(n):
        c = c + 1 if (i and state[i] == state[i - 1]) else 1
        dw[i] = c
    nod = np.array([1.0 if r["UNKNOWN_REASON"] else 0.0 for r in rows])
    nod8 = pd.Series(nod).rolling(8, min_periods=1).mean().to_numpy()
    ind = r1.indicators(m15.copy())
    F = ["atr_pctl", "er10", "slope5", "rng_exp", "vel4", "acc", "eff3", "act3"]
    Xp = ind[F].to_numpy(float)
    # MTF context from H1 and H4
    def ctx(df):
        d = df.reindex(m15.index, method="ffill")
        pc = d["c"].shift(1)
        tr = pd.concat([(d["h"] - d["l"]), (d["h"] - pc).abs(), (d["l"] - pc).abs()], axis=1).max(axis=1)
        a = tr.rolling(20).mean()
        return np.column_stack([(d["c"] / d["c"].shift(4) - 1) * 1e4, tr / a,
                                 (d["c"].rolling(20).mean() - d["c"].rolling(20).mean().shift(2)) / a])
    def bars(rule):
        gg = m1.resample(rule)
        return pd.DataFrame({"o": gg["open"].first(), "h": gg["high"].max(), "l": gg["low"].min(), "c": gg["close"].last()}).dropna()
    h1, h4 = bars("60min"), bars("240min")
    MTF = np.hstack([ctx(h1), ctx(h4)])
    df = pd.DataFrame({"ts": m15.index.astype(str), "frozen": frozen, "state": state, "event": events,
                        "dwell": dw, "nod8": nod8, "o": m15["o"].to_numpy(), "h": m15["h"].to_numpy(),
                        "l": m15["l"].to_numpy(), "c": m15["c"].to_numpy(),
                        **{f"f_{c_}": Xp[:, i] for i, c_ in enumerate(F)},
                        **{f"mtf_{i}": MTF[:, i] for i in range(MTF.shape[1])}})
    os.makedirs(os.path.join(ROOT, "states"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "events"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "ontology"), exist_ok=True)
    cpath = os.path.join(ROOT, "states", "state_v2_series.parquet")
    df.to_parquet(cpath, index=False)
    # definitions
    state_def = {"definition_id": "V1_R2_FULL_STATE_V2", "status": "RESEARCH_ONLY", "k": 2,
                  "derivation": "frozen C1 MARKET_BEHAVIOR + min-dwell k=2 (pre-registered; not tuned)",
                  "levels": sorted(set(state)), "bars": n,
                  "lifecycle": {"entry": f"candidate observed >= 2 consecutive bars", "exit": "superseded by a new state",
                                 "persistence": "run length >= 2 by construction", "carry_forward": "true"},
                  "note": "STATE != BEHAVIOR EVENT (§13): this is the slow variable"}
    event_def = {"definition_id": "V1_R2_FULL_EVENT_LAYER", "status": "RESEARCH_ONLY",
                  "derivation": "mapped from frozen C1 sub-labels (PRICE_STRUCTURE / CANDLE_STRUCTURE / REGIME / MOMENTUM)",
                  "levels": sorted(set(events)), "bars": n,
                  "note": "EVENT = fast variable (§41/§15), evaluated separately from STATE"}
    for rel, o in (("states/STATE_V2_definition.json", state_def), ("events/EVENT_definition.json", event_def),
                    ("ontology/SERIES_CONTEXT.json", {"bars": n, "range": [str(m15.index.min()), str(m15.index.max())],
                                                        "tf_built": ["M15", "H1", "H4"], "source": os.path.relpath(M1P, REPO),
                                                        "no_history_expansion": True, "ts_utc": NOW})):
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(o, fh, indent=1, ensure_ascii=False)
    h = hashlib.sha256(open(cpath, "rb").read()).hexdigest()
    print("CACHED:", cpath)
    print("series_hash:", h[:16], "| states:", len(state_def["levels"]), "| events:", len(event_def["levels"]))
    print("state dist:", json.dumps(dict(pd.Series(state).value_counts().head(12)), ensure_ascii=False))
    print("event dist:", json.dumps(dict(pd.Series(events).value_counts().head(12)), ensure_ascii=False))
    print("SERIES_HASH", h)


if __name__ == "__main__":
    main()
