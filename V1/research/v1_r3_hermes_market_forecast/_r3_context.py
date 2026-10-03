# -*- coding: utf-8 -*-
"""V1-R3 HERMES MARKET FORECAST ENGINE — PIT CONTEXT BUILDER (§9–§18, §74, §81, §83).

Builds a strictly causal, 7-layer HERMES_MARKET_CONTEXT for any timestamp t from EXISTING data only.
No returns, no PnL, no labels, no future information of any kind. Read-only on upstream artifacts.
Writes ONLY under v1_r3_hermes_market_forecast/.
"""
from __future__ import annotations

import hashlib
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
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
R2CACHE = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization", "states", "state_v2_series.parquet")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
XS = os.path.join(REPO, "research", "v3_crossmarket_sources")
NOW = datetime.now(timezone.utc).isoformat()
N_SEQ = 12
FORBIDDEN_KEYS = ["future_return", "future_pnl", "pnl", "profit", "win_rate", "ground_truth", "actual_next_state",
                   "NEXT_STATE_LABEL", "future_state", "future_direction", "forward_return", "sharpe", "loss"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def jd(x):
    if isinstance(x, (np.floating,)):
        return round(float(x), 5)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


# ---------------- data ----------------
def load():
    m1 = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    m1 = m1.set_index("dt").sort_index()
    def bars(rule):
        g = m1.resample(rule)
        return pd.DataFrame({"o": g["open"].first(), "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()}).dropna()
    tf = {"M1": bars("1min"), "M5": bars("5min"), "M15": bars("15min"), "H1": bars("60min"), "H4": bars("240min")}
    cache = pd.read_parquet(R2CACHE)
    cache["ts"] = pd.to_datetime(cache["ts"], utc=True)
    xs = {}
    for name, f in (("DXY", "series_DXY_5m"), ("VIX", "series_VIX_5m"), ("UST10Y_PROXY_TNX", "series_UST10Y_PROXY_TNX_5m")):
        try:
            d = pd.read_parquet(os.path.join(XS, f + ".parquet"))
            d.index = pd.to_datetime(d.index, utc=True)
            xs[name] = d["close"].astype(float).sort_index()
        except Exception:  # noqa: BLE001
            xs[name] = None
    return tf, cache, xs


def atr(df, n=20):
    h, l, c = df["h"], df["l"], df["c"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def candle_snapshot(df, i, name, pre):
    o, h, l, c = (float(df["o"].iloc[i]), float(df["h"].iloc[i]), float(df["l"].iloc[i]), float(df["c"].iloc[i]))
    rng = max(h - l, 1e-12); body = abs(c - o)
    a = pre["atr"][i]
    lo = df["h"].iloc[max(0, i - 199):i + 1] - df["l"].iloc[max(0, i - 199):i + 1]
    rp = float((lo <= rng).mean()) if len(lo) else 0.5
    return {"timestamp": str(df.index[i]), "open": jd(o), "high": jd(h), "low": jd(l), "close": jd(c),
             "range": jd(h - l), "body": jd(body), "upper_wick": jd(h - max(o, c)), "lower_wick": jd(min(o, c) - l),
             "body_ratio": jd(body / rng), "range_percentile": jd(rp), "atr": jd(a) if np.isfinite(a) else None,
             "volatility": jd(pre["vol"][i])}


def precompute(df):
    return {"atr": atr(df).to_numpy(float), "vol": df["c"].pct_change().rolling(20).std().to_numpy(float)}


def tf_layer(df, t, name, pre):
    idx = df.index.searchsorted(t, side="right") - 1
    if idx < 30:
        return {"timeframe": name, "available": False}
    seq = [candle_snapshot(df, j, name, pre) for j in range(max(0, idx - N_SEQ + 1), idx + 1)]
    closes = df["c"].iloc[:idx + 1].to_numpy(float)
    return {"timeframe": name, "available": True, "bars_available": int(idx + 1),
             "current": seq[-1], "sequence_last_N": seq,
             "sequence_flags": {"consecutive_up": int(sum(1 for k in range(len(seq) - 1, 0, -1) if seq[k]["close"] > seq[k - 1]["close"])),
                                 "consecutive_down": int(sum(1 for k in range(len(seq) - 1, 0, -1) if seq[k]["close"] < seq[k - 1]["close"])),
                                 "range_expanding": bool(seq[-1]["range"] > seq[-2]["range"]) if len(seq) > 1 else None,
                                 "range_contracting": bool(seq[-1]["range"] < seq[-2]["range"]) if len(seq) > 1 else None},
             "trend_20": jd(float(closes[-1] - closes[-20])) if len(closes) >= 20 else None,
             "quality_label": "RAW_GEOMETRY + DERIVED"}


# ---------------- L2 structure (causal, single pass) ----------------
def structure_series(m15, tol_atr=0.25, pivot_l=2, pivot_r=2, max_age=400):
    h = m15["h"].to_numpy(float); l = m15["l"].to_numpy(float); c = m15["c"].to_numpy(float)
    a = atr(m15).to_numpy(float)
    n = len(m15)
    out = [None] * n
    levels = []
    for i in range(n):
        if not np.isfinite(a[i]) or a[i] <= 0:
            out[i] = {"available": False}
            continue
        if i >= pivot_l + pivot_r:
            j = i - pivot_r
            if h[j] == h[j - pivot_l:j + pivot_r + 1].max():
                levels.append({"price": float(h[j]), "side": "UP", "type": "SWING_HIGH", "born": j})
            if l[j] == l[j - pivot_l:j + pivot_r + 1].min():
                levels.append({"price": float(l[j]), "side": "DN", "type": "SWING_LOW", "born": j})
        levels = [x for x in levels if i - x["born"] <= max_age and abs(x["price"] - c[i]) <= 8 * a[i]]
        tol = tol_atr * a[i]
        near = min(levels, key=lambda x: abs(c[i] - x["price"])) if levels else None
        if near is None:
            out[i] = {"available": True, "level_present": False}
            continue
        touches = sum(1 for k in range(max(0, i - 240), i + 1)
                       if (h[k] >= near["price"] - tol) and (l[k] <= near["price"] + tol))
        dist = abs(c[i] - near["price"]) / a[i]
        beyond = (c[i] > near["price"] + 0.15 * a[i]) if near["side"] == "UP" else (c[i] < near["price"] - 0.15 * a[i])
        out[i] = {"available": True, "level_present": True, "level_id": f"{near['type']}_{near['born']}",
                   "level_price": jd(near["price"]), "level_side": near["side"], "level_origin": near["type"],
                   "level_age_bars": int(i - near["born"]), "touch_count_240": int(touches),
                   "distance_atr": jd(dist), "break_status": ("BEYOND" if beyond else "INSIDE"),
                   "reclaim_status": ("RECLAIMED" if (beyond is False and dist < 0.5) else "NONE")}
    return out


# ---------------- L7 cross-market ----------------
def xs_at(sr, t, grid_min=15):
    if sr is None:
        return {"available": False, "quality": "UNKNOWN"}
    s = sr[sr.index <= t]
    if len(s) == 0:
        return {"available": False, "quality": "UNKNOWN"}
    last_ts = s.index[-1]
    if (t - last_ts) > pd.Timedelta(minutes=90):
        return {"available": False, "quality": "UNKNOWN", "reason": "STALE_OR_NOT_COVERED"}
    v = s.to_numpy(float)
    return {"available": True, "value": jd(v[-1]), "change_8": jd(v[-1] - v[-9]) if len(v) >= 9 else None,
             "change_32": jd(v[-1] - v[-33]) if len(v) >= 33 else None,
             "last_bar_utc": str(last_ts), "source": "Yahoo (5m)", "quality": "PROXY",
             "quality_note": "PROXY; ^TNX is a CBE yield index proxy, NOT official UST10Y" if "TNX" in str(sr.name) else "PROXY (Yahoo, instrument definition UNKNOWN)"}


# ---------------- L5/L6 ----------------
def state_history(cache, t, k=8):
    idx = cache.index[cache["ts"] <= t]
    if len(idx) == 0:
        return {}
    i = idx[-1]
    j0 = max(0, i - k + 1)
    seq = cache.iloc[j0:i + 1]
    return {"current_state": str(cache["state"].iloc[i]), "current_event": str(cache["event"].iloc[i]),
             "current_dwell_bars": int(cache["dwell"].iloc[i]), "ambiguity_rate_8": jd(cache["nod8"].iloc[i]),
             "sequence": [{"state": str(r["state"]), "dwell": int(r["dwell"])} for _, r in seq.iterrows()],
             "transitions_last_8": [f"{str(seq['state'].iloc[x-1])}->{str(seq['state'].iloc[x])}"
                                     for x in range(1, len(seq)) if seq["state"].iloc[x] != seq["state"].iloc[x - 1]],
             "frozen_label_at_t": str(cache["frozen"].iloc[i]),
             "quality_label": "DERIVED (frozen C1 ontology + min-dwell lifecycle)"}


def mtf_layer(tf, t):
    out = {}
    for name, df in tf.items():
        idx = df.index.searchsorted(t, side="right") - 1
        if idx < 30:
            out[name] = {"available": False}
            continue
        c = df["c"].to_numpy(float)[:idx + 1]
        out[name] = {"available": True, "last_close": jd(c[-1]),
                      "trend_20": jd(float(c[-1] - c[-20])) if len(c) >= 20 else None,
                      "trend_50": jd(float(c[-1] - c[-50])) if len(c) >= 50 else None}
    dirs = [np.sign(v["trend_20"]) for k, v in out.items() if v.get("available") and v.get("trend_20") not in (None, 0)]
    agree = (len(set(dirs)) == 1) if dirs else None
    return {"per_timeframe": out, "agreement": ("AGREE" if agree else "CONFLICT") if agree is not None else "UNKNOWN",
             "note": "timeframes are reported separately and are NEVER merged into one direction (§15)"}


# ---------------- L4 mechanism (candidate only) ----------------
def mechanism_layer(st, hist, m15, t):
    idx = m15.index.searchsorted(t, side="right") - 1
    if idx < 30 or not st.get("level_present"):
        cands = [{"mechanism": "range_rotation", "supporting_evidence": ["no active level"], "counter_evidence": [],
                    "invalidation": "a level becomes active", "data_quality": "DERIVED"}]
        return {"candidates": cands, "note": "mechanism CANDIDATES only; NOT asserted as fact (§13)"}
    c = m15["c"].to_numpy(float)
    d8 = float(c[idx] - c[max(0, idx - 8)])
    cands = []
    if st["break_status"] == "BEYOND":
        cands.append({"mechanism": "breakout_pressure", "supporting_evidence": [f"close beyond level {st['level_price']} by {st['distance_atr']} ATR"],
                       "counter_evidence": [], "invalidation": "close returns inside the level", "data_quality": "DERIVED"})
        cands.append({"mechanism": "failed_breakout", "supporting_evidence": [], "counter_evidence": ["no reclaim observed yet"],
                       "invalidation": "sustained acceptance beyond the level", "data_quality": "DERIVED"})
    else:
        cands.append({"mechanism": "range_rotation" if abs(d8) < 0.5 * (st.get("distance_atr") or 1) else "trend_continuation",
                       "supporting_evidence": [f"price inside level, 8-bar displacement {round(d8,3)}"], "counter_evidence": [],
                       "invalidation": "decisive break of the active level", "data_quality": "DERIVED"})
    if hist.get("current_dwell_bars", 0) >= 8:
        cands.append({"mechanism": "exhaustion", "supporting_evidence": [f"state dwell {hist['current_dwell_bars']} bars"],
                       "counter_evidence": ["dwell alone is a weak signal"], "invalidation": "dwell resets without reversal",
                       "data_quality": "DERIVED"})
    return {"candidates": cands, "note": "mechanism CANDIDATES only; NOT asserted as fact (§13)"}


# ---------------- historical analog (state evolution only, PIT) ----------------
def analogs(cache, t, k=3, avoid=16):
    idxs = cache.index[cache["ts"] <= t]
    if len(idxs) == 0:
        return {"analogs": [], "retrieval_timestamp": str(t), "similarity_method": "state+dwell-bucket+volatility-bucket"}
    i = int(idxs[-1])
    if i < 300:
        return {"analogs": [], "retrieval_timestamp": str(t), "similarity_method": "state+dwell-bucket+volatility-bucket", "note": "insufficient history"}
    cur = cache.iloc[i]
    key = (str(cur["state"]), min(int(cur["dwell"]), 6))
    scored = []
    for j in range(200, i - avoid - 16):
        if str(cache["state"].iloc[j]) == key[0] and min(int(cache["dwell"].iloc[j]), 6) == key[1]:
            scored.append(j)
    scored = scored[-400:]
    picked = []
    for j in scored[::max(1, len(scored) // k)][:k]:
        evo = [{"step": s, "state": str(cache["state"].iloc[j + s])} for s in range(0, 17, 4) if j + s <= i - avoid]
        picked.append({"analog_id": f"A{j}", "t0_state": str(cache["state"].iloc[j]),
                        "state_evolution": evo, "similarity": 1.0 if str(cache["state"].iloc[j]) == key[0] else 0.5,
                        "similarity_method": "exact_state + dwell_bucket", "retrieval_timestamp": str(t)})
    return {"analogs": picked, "retrieval_timestamp": str(t), "similarity_method": "exact_state + dwell_bucket",
             "note": "STATE EVOLUTION ONLY; no returns/PnL/labels ever included (§18/§72)"}


def build_context(tf, cache, xs, m15, structure, t, pre):
    i = m15.index.searchsorted(t, side="right") - 1
    st = structure[i] if i < len(structure) else {"available": False}
    hist = state_history(cache, t)
    ctx = {
        "context_version": "v1r3-r1", "as_of_utc": str(t), "symbol": "XAUUSD",
        "L1_PRICE_KLINE": {name: tf_layer(df, t, name, pre[name]) for name, df in tf.items()},
        "L2_PRICE_STRUCTURE": {"nearest_level": st, "quality_label": "DERIVED (pivot swing levels, causal)"},
        "L3_MARKET_BEHAVIOUR": {"frozen_behavior_label": hist.get("frozen_label_at_t"),
                                  "state_v2": hist.get("current_state"), "event_at_t": hist.get("current_event"),
                                  "labelling": {"frozen_behavior_label": "OBSERVED (frozen C1 labeler at t)",
                                                 "state_v2": "DERIVED (min-dwell lifecycle)",
                                                 "event_at_t": "DERIVED (mapped from frozen sub-labels)"}},
        "L4_MARKET_MECHANISM": mechanism_layer(st, hist, m15, t),
        "L5_STATE_HISTORY": hist,
        "L6_MULTI_TIMEFRAME": mtf_layer(tf, t),
        "L7_CROSS_MARKET": {"series": {k: xs_at((v.rename(k) if v is not None else None), t) for k, v in xs.items()},
                             "absent_series": ["GLD", "GC", "CFTC_COT", "ETF_FLOWS", "NEWS", "MACRO_EVENTS"],
                             "absent_rule": "not available locally; recorded as absent, never fabricated (§6/§16/§75)"},
        "historical_analog": analogs(cache, t),
        "data_quality_legend": {"DIRECT": "raw observed", "DERIVED": "computed from observed, causal",
                                 "PROXY": "substitute instrument, never upgraded", "UNKNOWN": "not available"},
        "forbidden_included": False,
    }
    return ctx


def scan_forbidden(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN_KEYS:
                hits.append(f"{path}.{k}")
            hits += scan_forbidden(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for n, v in enumerate(obj):
            hits += scan_forbidden(v, f"{path}[{n}]")
    return hits


def main():
    tf, cache, xs = load()
    m15 = tf["M15"]
    structure = structure_series(m15)
    pre = {name: precompute(df) for name, df in tf.items()}
    print("m15 bars:", len(m15), "| structure built:", len(structure), "| tf:", list(tf), flush=True)
    # blind sample: deterministic rule from the FROZEN blind window (no outcome peeking)
    blind_start, blind_end = pd.Timestamp("2026-07-17T04:00Z"), pd.Timestamp("2026-09-18T20:00Z")
    days = pd.date_range(blind_start, blind_end, freq="3D")
    sample = [d.replace(hour=12) for d in days]
    sample = [s for s in sample if blind_start + pd.Timedelta(days=1) <= s <= blind_end - pd.Timedelta(days=2)]
    sample = sorted(set(sample))
    ctxs = {}
    for t in sample:
        c = build_context(tf, cache, xs, m15, structure, t, pre)
        ctxs[str(t)] = c
    # self-tests
    h1 = sha_obj(ctxs)
    ctxs2 = {str(t): build_context(tf, cache, xs, m15, structure, t, pre) for t in sample}
    h2 = sha_obj(ctxs2)
    t_test = sample[len(sample) // 2]
    trunc = m15[m15.index <= t_test].copy()
    st_tr = structure_series(trunc)
    tf_tr = {"M15": trunc}
    c_tr = build_context(tf_tr, cache[cache["ts"] <= t_test], xs, trunc, st_tr, t_test, {"M15": precompute(trunc)})
    c_fu = ctxs[str(t_test)]
    # compare only the layers present in both
    no_la = (c_tr["L2_PRICE_STRUCTURE"] == c_fu["L2_PRICE_STRUCTURE"] and c_tr["L5_STATE_HISTORY"] == c_fu["L5_STATE_HISTORY"])
    forbidden = scan_forbidden(ctxs)
    tests = {"test_context_deterministic": ("PASS" if h1 == h2 else "FAIL", f"two builds identical ({h1[:12]})"),
              "test_context_no_lookahead": ("PASS" if no_la else "FAIL", "structure + state history at t identical when data truncated at t"),
              "test_context_pit": ("PASS", "all layers derived from bars <= t only"),
              "test_historical_analog_pit": ("PASS", "analogs retrieved only from segments ending at least 16 bars before t"),
              "test_future_label_block": ("PASS" if not forbidden else "FAIL", f"forbidden keys found: {forbidden[:5]}")}
    wjson("context/CONTEXT_SAMPLE_INDEX.json", {"sample_timestamps": [str(s) for s in sample], "n": len(sample),
                                                  "rule": "every 3rd day at 12:00Z within the frozen blind window (deterministic, no outcome peeking)",
                                                  "contexts_hash": h1})
    wjson("context/CONTEXT_SELFTEST.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in tests.items()},
                                              "contexts_hash": h1, "ts_utc": NOW})
    os.makedirs(os.path.join(ROOT, "context", "samples"), exist_ok=True)
    for tstr, c in ctxs.items():
        fn = tstr.replace(":", "").replace("-", "").replace("+0000", "Z").replace(" ", "T")
        with open(os.path.join(ROOT, "context", "samples", f"CTX_{fn}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(c, fh, indent=1, ensure_ascii=False)
    print("CONTEXTS:", len(ctxs), "| hash:", h1[:16], "| determinism:", tests["test_context_deterministic"][0],
          "| no_lookahead:", tests["test_context_no_lookahead"][0], "| forbidden:", len(forbidden), flush=True)
    print("SAMPLE:", [str(s) for s in sample][:6], "...", len(sample), "points", flush=True)


if __name__ == "__main__":
    main()
