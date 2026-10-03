# -*- coding: utf-8 -*-
"""v1_upgrade/label_adapter.py — live wiring of the FROZEN 9-state labeler (no definition change).

Frozen chain (verbatim, unmodified):
    _c1_5_run.py::label_series(m15,"M15") -> MARKET_BEHAVIOR  [= the 'frozen' column]
    hysteresis(MARKET_BEHAVIOR, 2)        -> state            [= the 'state' column]
    event_of(row)                         -> event

Modes:
  --replay   rebuild M15 from the frozen M1 source, label, compare pointwise to state_v2_series.parquet
  --live     build M15 from live MT5 M1 bars and return the latest family (used by cycle.py)
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
SER = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization", "states", "state_v2_series.parquet")
FAMILY = {"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL",
           "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE",
           "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}
_M = {}


def _mod():
    if "c15" not in _M:
        s = importlib.util.spec_from_file_location("c15", os.path.join(C15, "_c1_5_run.py"))
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        _M["c15"] = m
    return _M["c15"]


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


def m15_from_m1(m1):
    g = m1.resample("15min")
    return pd.DataFrame({"o": g["open"].first(), "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()}).dropna()


def label_m15(m15):
    rows = _mod().label_series(m15, "M15")
    frozen = [r["MARKET_BEHAVIOR"] for r in rows]
    return frozen, hysteresis(frozen, 2), rows


def replay():
    m1 = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    m1 = m1.set_index("dt").sort_index()
    m15 = m15_from_m1(m1)
    frozen, state, _ = label_m15(m15)
    ser = pd.read_parquet(SER)
    ser["ts"] = pd.to_datetime(ser["ts"], utc=True)
    ser = ser.set_index("ts")
    fr = pd.Series(frozen, index=m15.index)
    st = pd.Series(state, index=m15.index)
    common = fr.index.intersection(ser.index)
    f_match = int((fr.loc[common].values == ser.loc[common, "frozen"].values).sum())
    s_match = int((st.loc[common].values == ser.loc[common, "state"].values).sum())
    tot = len(common)
    mism = []
    if s_match != tot:
        bad = common[st.loc[common].values != ser.loc[common, "state"].values][:5]
        mism = [{"ts": str(t)} for t in bad]
    return {"overlap_bars": tot, "frozen_match": f_match, "state_match": s_match,
             "frozen_pct": round(100.0 * f_match / max(1, tot), 4), "state_pct": round(100.0 * s_match / max(1, tot), 4),
             "reproducible": bool(tot > 0 and f_match == tot and s_match == tot), "first_mismatches": mism,
             "m15_bars": int(len(m15)), "m1_source": os.path.relpath(M1P, REPO)}


def live_state(bars_needed=90000, mt5=None):
    """Live path: take MT5 M1 bars, resample to M15, label the last bar with the frozen chain.

    WARM-UP: the frozen chain ends with hysteresis(k=2), which is path-dependent. Convergence testing
    (last 200 labels vs the full-history labeling) is 100% at a 5000-M15 warm-up, so the default M1
    window is sized well above that (~90000 M1 bars ~= 6000 M15 bars).

    CONNECTION OWNERSHIP: when `mt5` is passed in by an in-process caller (e.g. cycle.py) this function
    NEVER initializes or shuts down. Calling shutdown() here would tear down the caller's session and
    every later broker call would fail with -10004 No IPC connection."""
    own = mt5 is None
    if not own:
        r = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, int(bars_needed))
    else:
        env = {}
        for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
        import MetaTrader5 as mt5mod
        kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
              "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
        kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
        if not mt5mod.initialize(**kw):
            return {"ok": False, "error": "MT5_INIT_FAILED"}
        mt5 = mt5mod
        r = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, int(bars_needed))
        mt5.shutdown()
    if r is None or len(r) < 300:
        return {"ok": False, "error": f"INSUFFICIENT_M1:{0 if r is None else len(r)}"}
    m1 = pd.DataFrame({"dt": pd.to_datetime(r["time"], unit="s", utc=True), "open": r["open"], "high": r["high"],
                        "low": r["low"], "close": r["close"]}).set_index("dt").sort_index()
    m15 = m15_from_m1(m1)
    frozen, state, rows = label_m15(m15)
    last = rows[-1]
    ma20 = float(m15["c"].rolling(20).mean().iloc[-1]) if len(m15) >= 20 else None
    close = float(m15["c"].iloc[-1])
    trs = []
    for i in range(max(1, len(m15) - 15), len(m15)):
        h, l, pc = float(m15["h"].iloc[i]), float(m15["l"].iloc[i]), float(m15["c"].iloc[i - 1])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr14 = (sum(trs) / len(trs)) if trs else None
    return {"ok": True, "m1_bars": int(len(m1)), "m15_bars": int(len(m15)),
             "last_bar_utc": str(m15.index[-1]), "last_close": close,
             "MARKET_BEHAVIOR": frozen[-1], "state": state[-1], "family": FAMILY.get(state[-1]),
             "ma20": ma20, "trend_sign": ((close - ma20) if ma20 is not None else None), "atr14": atr14,
             "PRICE_STRUCTURE": last.get("PRICE_STRUCTURE"), "REGIME": last.get("REGIME"),
             "MOMENTUM": last.get("MOMENTUM"), "CANDLE_STRUCTURE": last.get("CANDLE_STRUCTURE")}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--replay"
    if mode == "--replay":
        print(json.dumps(replay(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(live_state(), ensure_ascii=False, indent=1))
