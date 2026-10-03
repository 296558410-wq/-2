# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION R1 — PHASE 1: AUTONOMOUS DIAGNOSIS (RESEARCH ONLY).

Question: WHY is the frozen C1/C1.5 MARKET_BEHAVIOR sequence dominated by 1-bar duration?
Method:  instrument gate (H) first, then attribute across A/B/C/D/E/F/G with pre-registered deltas.
Read-only on all frozen artifacts. Writes ONLY under v1_r2_full_autonomous_optimization_r1/.
No orders / no broker / no live. No future return, PnL or win-rate anywhere.
"""
from __future__ import annotations

import collections
import glob
import hashlib
import importlib.util
import json
import math
import os
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
MR = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading")
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
C15 = os.path.join(MR, "c1_5_target_validation")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
B4 = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_20260926T123252", "m15_tick_bid.parquet")
NOW = datetime.now(timezone.utc).isoformat()
HORIZONS = {"M5": 24, "M15": 8, "H1": 2}
BAR_MIN = {"M5": 5, "M15": 15, "H1": 60}
SEEDS = [20260927, 20260928, 20260929]
PUBLISHED = {"persistence_M15": 0.1447, "churn_M15": 0.6473, "dur_median_M15": 1.0,
              "dur_mean_M15": 1.544, "trans_entropy_M15": 3.0114}
NOISE_FRAC = 0.01          # 0.01 * ATR20, pre-registered
HYST_KS = [2, 3, 5]
NULL_BLOCK = 48
MARGIN_CHURN, MARGIN_DUR = 0.05, 1.0


def load_labelmod():
    p = os.path.join(C15, "_c1_5_run.py")
    spec = importlib.util.spec_from_file_location("c15mod", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def entropy(c):
    t = sum(c.values())
    if t <= 0:
        return 0.0
    return round(-sum((v / t) * math.log2(v / t) for v in c.values()), 4)


def labels_of(rows):
    return [r["MARKET_BEHAVIOR"] for r in rows]


def churn_of(beh):
    if len(beh) < 2:
        return 0.0
    return round(sum(1 for a, b in zip(beh, beh[1:]) if a != b) / (len(beh) - 1), 4)


def runs_of(beh):
    if not beh:
        return []
    r = []; cur = 1
    for a, b in zip(beh, beh[1:]):
        if a == b:
            cur += 1
        else:
            r.append(cur); cur = 1
    r.append(cur)
    return r


def dur_stats(beh):
    r = runs_of(beh)
    if not r:
        return {}
    return {"runs": len(r), "median": float(statistics.median(r)), "mean": round(sum(r) / len(r), 3),
             "p75": float(np.percentile(r, 75)), "p90": float(np.percentile(r, 90)), "max": int(max(r))}


def persistence(beh, h, states):
    out = {}
    for s in states:
        idx = [i for i, b in enumerate(beh) if b == s]
        ok = [i for i in idx if i + h < len(beh)]
        if ok:
            out[s] = round(sum(1 for i in ok if beh[i + h] == s) / len(ok), 4)
    return out


def overall_persistence(beh, h, states):
    per = persistence(beh, h, states)
    return round(statistics.mean(per.values()), 4) if per else 0.0, per


# ---------------- H: instrument gate ----------------
def build_inputs(mod):
    m15 = pd.read_parquet(B4)
    m15df = m15[["o", "h", "l", "c"]].copy()
    h1df = m15df.resample("60min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    parts = []
    for tf in sorted(glob.glob(os.path.join(REPO, "data", "live_fxtm", "ticks_*.parquet"))):
        d = pd.read_parquet(tf, columns=["utc_ms", "bid"])
        t = pd.to_datetime(d["utc_ms"], unit="ms", utc=True)
        g = pd.DataFrame({"b": t.dt.floor("5min"), "p": d["bid"].to_numpy(float)}).groupby("b")["p"]
        parts.append(pd.DataFrame({"o": g.first(), "h": g.max(), "l": g.min(), "c": g.last()}))
    m5df = pd.concat(parts).sort_index()
    m5df = m5df[~m5df.index.duplicated(keep="first")]
    return {"M5": m5df, "M15": m15df, "H1": h1df}


def atr20(df):
    h, l, c = df["h"], df["l"], df["c"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(20).mean()


# ---------------- A: assignment-source decomposition (replayed from returned sub-labels) ----------------
def assign_source(reg, mom, ps, cs):
    if ps == "BREAK_CONFIRMED":
        return "BREAKOUT_CONFIRMATION"
    if ps == "FAILED_BREAK":
        return "BREAKOUT_FAILURE"
    if ps == "BREAK_ATTEMPT":
        return "BREAKOUT_ATTEMPT"
    if cs == "REJECTION":
        return "REJECTION"
    if reg == "TREND" and mom == "DECELERATING":
        return "DECELERATION"
    if reg == "TREND":
        return "TREND"
    if reg == "EXPANSION":
        return "EXPANSION"
    if reg == "COMPRESSION":
        return "COMPRESSION"
    if reg == "REVERSAL":
        return "REVERSAL_ATTEMPT(deadbranch)"
    if ps in ("FIRST_TEST", "REPEATED_TEST") and cs == "ENGULFING":
        return "ACCEPTANCE"
    if reg == "RANGE":
        return "ROTATION"
    return "NO_DEFINED_STATE"


def phase1_short(mod):
    inp = build_inputs(mod)
    print("inputs:", {k: len(v) for k, v in inp.items()})
    series = {tf: mod.label_series(inp[tf], tf) for tf in inp}
    rep = {"inputs_rows": {k: len(v) for k, v in inp.items()}, "H_instrument": {}}

    # ---- H gate ----
    beh15 = labels_of(series["M15"])
    op15, per15 = overall_persistence(beh15, HORIZONS["M15"], mod.L1_BEHAVIOR + ["NO_DEFINED_STATE"])
    d15 = dur_stats(beh15)
    c15 = churn_of(beh15)
    tm = collections.Counter((beh15[i], beh15[i + HORIZONS["M15"]]) for i in range(len(beh15) - HORIZONS["M15"]))
    tent = entropy(collections.Counter(beh15[HORIZONS["M15"]:]))
    got = {"persistence_M15": op15, "churn_M15": c15, "dur_median_M15": d15["median"],
            "dur_mean_M15": d15["mean"], "trans_entropy_M15": tent}
    diffs = {k: round(abs(got[k] - PUBLISHED[k]), 6) for k in PUBLISHED}
    gate_pass = max(diffs["persistence_M15"], diffs["churn_M15"]) <= 0.001 and diffs["dur_median_M15"] <= 0.5
    rep["H_instrument"] = {"published": PUBLISHED, "reproduced": got, "abs_diff": diffs,
                            "INSTRUMENT_GATE": "PASS" if gate_pass else "FAIL"}
    print("INSTRUMENT_GATE:", rep["H_instrument"]["INSTRUMENT_GATE"], diffs)
    if not gate_pass:
        rep["ATTRIBUTION"] = "BLOCKED_BY_INSTRUMENT_GATE"

    # ---- B: granularity (bars vs hours) ----
    b = {}
    for tf, rows in series.items():
        beh = labels_of(rows)
        d = dur_stats(beh)
        b[tf] = {"bars": len(beh), "distinct_states": len(set(beh)), "label_entropy": entropy(collections.Counter(beh)),
                  "churn": churn_of(beh), "dur_bars_median": d.get("median"), "dur_bars_mean": d.get("mean"),
                  "dur_hours_median": round(d.get("median", 0) * BAR_MIN[tf] / 60, 3),
                  "persistence": overall_persistence(beh, HORIZONS[tf], mod.L1_BEHAVIOR + ["NO_DEFINED_STATE"])[0],
                  "no_defined_rate": round(sum(1 for x in beh if x == "NO_DEFINED_STATE") / len(beh), 4)}
    rep["B_granularity"] = b

    # ---- A: assignment source + conflict ----
    src = collections.Counter()
    conflict = 0
    for r in series["M15"]:
        s = assign_source(r["REGIME"], r["MOMENTUM"], r["PRICE_STRUCTURE"], r["CANDLE_STRUCTURE"])
        src[s] += 1
        if r["REGIME"] in ("TREND", "EXPANSION") and r["CANDLE_STRUCTURE"] == "REJECTION":
            conflict += 1
    rep["A_ontology_conflict"] = {
        "assignment_source_counts_M15": dict(src.most_common()),
        "source_switch_churn": churn_of([assign_source(r["REGIME"], r["MOMENTUM"], r["PRICE_STRUCTURE"], r["CANDLE_STRUCTURE"]) for r in series["M15"]]),
        "trend_or_expansion_with_rejection_bars": conflict,
        "dead_branch_reversal_attempt_hits": src.get("REVERSAL_ATTEMPT(deadbranch)", 0),
        "note": "REVERSAL_ATTEMPT branch is unreachable because the frozen labeler never emits REGIME=REVERSAL"}

    # ---- C: boundary aliasing ----
    idx = inp["M15"].index
    bh = labels_of(series["M15"])
    bnd = [i for i in range(1, len(bh)) if idx[i].date() != idx[i - 1].date()]
    interior = [i for i in range(1, len(bh)) if i not in set(bnd)]
    cb = sum(1 for i in bnd if bh[i] != bh[i - 1])
    ci = sum(1 for i in interior if bh[i] != bh[i - 1])
    rep["C_boundary_aliasing"] = {"day_boundary_bars": len(bnd), "boundary_churn": round(cb / max(1, len(bnd)), 4),
                                    "interior_churn": round(ci / max(1, len(interior)), 4),
                                    "boundary_over_interior_ratio": round((cb / max(1, len(bnd))) / max(1e-9, ci / max(1, len(interior))), 3)}

    # ---- D: measurement noise ----
    d_res = {}
    a15 = atr20(inp["M15"]).to_numpy(float)
    base = np.array(bh, dtype=object)
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        dn = inp["M15"].copy()
        for col in ("o", "h", "l", "c"):
            v = dn[col].to_numpy(float)
            v = v + rng.normal(0, 1, len(v)) * NOISE_FRAC * np.nan_to_num(a15, nan=0.0)
            dn[col] = v
        dn["h"] = np.maximum.reduce([dn["o"].to_numpy(float), dn["c"].to_numpy(float), dn["h"].to_numpy(float)])
        dn["l"] = np.minimum.reduce([dn["o"].to_numpy(float), dn["c"].to_numpy(float), dn["l"].to_numpy(float)])
        nl = labels_of(mod.label_series(dn, "M15"))
        agree = sum(1 for x, y in zip(base, nl) if x == y) / len(base)
        d_res[f"seed_{seed}"] = {"label_agreement": round(agree, 4), "churn": churn_of(nl),
                                  "dur_median": dur_stats(nl).get("median")}
    rep["D_measurement_noise"] = {"noise_frac_atr": NOISE_FRAC, "per_seed": d_res,
                                   "mean_agreement": round(statistics.mean(v["label_agreement"] for v in d_res.values()), 4),
                                   "baseline_churn": c15}

    # ---- E: genuine churn (surrogates) ----
    m15df = inp["M15"]
    c = m15df["c"].to_numpy(float)
    ret = np.diff(np.log(c))
    ow = (m15df["h"] - np.maximum(m15df["o"], m15df["c"])).to_numpy(float)[1:]
    dw = (np.minimum(m15df["o"], m15df["c"]) - m15df["l"]).to_numpy(float)[1:]
    e_res = {}
    for name, seed in (("iid_gaussian", SEEDS[0]), ("block_bootstrap", SEEDS[1])):
        rng = np.random.default_rng(seed)
        if name == "iid_gaussian":
            rs = rng.normal(ret.mean(), ret.std(), len(ret))
        else:
            nb = len(ret) // NULL_BLOCK + 1
            starts = rng.integers(0, max(1, len(ret) - NULL_BLOCK), nb)
            chunks = [ret[s:s + NULL_BLOCK] for s in starts]
            rs = np.concatenate(chunks)[:len(ret)]
        cc = c[0] * np.exp(np.cumsum(rs))
        oo = np.concatenate([[c[0]], cc[:-1]])
        ws_up = rng.choice(ow, len(cc)); ws_dn = rng.choice(dw, len(cc))
        hh = np.maximum(oo, cc) + ws_up; ll = np.minimum(oo, cc) - ws_dn
        syn = pd.DataFrame({"o": oo, "h": hh, "l": ll, "c": cc}, index=m15df.index[:len(cc)])
        bl = labels_of(mod.label_series(syn, "M15"))
        e_res[name] = {"churn": churn_of(bl), "dur_median": dur_stats(bl).get("median"),
                        "label_entropy": entropy(collections.Counter(bl))}
    rep["E_genuine_market_churn"] = {"observed_churn": c15, "observed_dur_median": d15["median"],
                                      "surrogates": e_res,
                                      "interpretation_rule": "surrogate churn >= observed - margin => churn not market-specific"}

    # ---- F: hysteresis on the SAME frozen labels ----
    def hysteresis(labels, k):
        if not labels:
            return []
        out = [labels[0]]; cur = labels[0]; pend = None; plen = 0
        for x in labels[1:]:
            if x == cur:
                out.append(cur); pend = None; plen = 0
            else:
                if pend == x:
                    plen += 1
                else:
                    pend = x; plen = 1
                if plen >= k:
                    cur = x; out.append(cur); pend = None; plen = 0
                else:
                    out.append(cur)
        return out
    f_res = {"baseline": {"churn": c15, "dur_median": d15["median"], "dur_mean": d15["mean"]}}
    for k in HYST_KS:
        hl = hysteresis(bh, k)
        ds = dur_stats(hl)
        f_res[f"k={k}"] = {"churn": churn_of(hl), "dur_median": ds["median"], "dur_mean": ds["mean"],
                            "delta_churn": round(c15 - churn_of(hl), 4), "delta_dur_median": round(ds["median"] - d15["median"], 3)}
    rep["F_no_hysteresis"] = f_res

    # ---- G: UNKNOWN / NO_DEFINED carry-forward ----
    carried = []
    last = None
    for x in bh:
        if x in ("NO_DEFINED_STATE",):
            carried.append(last if last is not None else x)
        else:
            last = x; carried.append(x)
    g_ds = dur_stats(carried)
    rep["G_unknown_leakage"] = {"no_defined_bars": sum(1 for x in bh if x == "NO_DEFINED_STATE"),
                                 "no_defined_rate": round(sum(1 for x in bh if x == "NO_DEFINED_STATE") / len(bh), 4),
                                 "churn_if_carry_forward": churn_of(carried),
                                 "delta_churn": round(c15 - churn_of(carried), 4),
                                 "dur_median_if_carry": g_ds.get("median")}
    return rep


def phase1_long(mod):
    m = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m["dt"] = pd.to_datetime(m["dt_utc"], utc=True)
    m = m.set_index("dt").sort_index()
    m15 = pd.DataFrame({"o": m["open"].resample("15min").first(), "h": m["high"].resample("15min").max(),
                         "l": m["low"].resample("15min").min(), "c": m["close"].resample("15min").last()}).dropna()
    h1 = m15.resample("60min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    out = {"H_instrument": "N/A_LONG", "rows": {"M15": len(m15), "H1": len(h1)}}
    for tf, df in (("M15", m15), ("H1", h1)):
        beh = labels_of(mod.label_series(df, tf))
        d = dur_stats(beh)
        op, _ = overall_persistence(beh, HORIZONS[tf], mod.L1_BEHAVIOR + ["NO_DEFINED_STATE"])
        src = collections.Counter(assign_source(r["REGIME"], r["MOMENTUM"], r["PRICE_STRUCTURE"], r["CANDLE_STRUCTURE"])
                                   for r in mod.label_series(df, tf))
        out[tf] = {"bars": len(beh), "churn": churn_of(beh), "dur_median": d.get("median"), "dur_mean": d.get("mean"),
                    "dur_p90": d.get("p90"), "dur_hours_median": round(d.get("median", 0) * BAR_MIN[tf] / 60, 3),
                    "persistence": op, "label_entropy": entropy(collections.Counter(beh)),
                    "no_defined_rate": round(sum(1 for x in beh if x == "NO_DEFINED_STATE") / len(beh), 4),
                    "assignment_source": dict(src.most_common())}
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "short"
    os.makedirs(os.path.join(R1, "reports"), exist_ok=True)
    os.makedirs(os.path.join(R1, "ledger"), exist_ok=True)
    os.makedirs(os.path.join(R1, "runs"), exist_ok=True)
    mod = load_labelmod()
    pre_path = os.path.join(R1, "registry", "v1_r2_r1_phase1_preregistration.json")
    pre_hash = hashlib.sha256(open(pre_path, "rb").read()).hexdigest()
    print("preregistration_hash:", pre_hash[:16], "| mode:", mode)
    if mode == "short":
        rep = phase1_short(mod)
    else:
        rep = phase1_long(mod)
    rep.update({"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_1_AUTONOMOUS_DIAGNOSIS",
                 "mode": mode, "preregistration_hash": pre_hash, "ts_utc": NOW,
                 "search_space_hash": sha_obj({"noise": NOISE_FRAC, "hyst": HYST_KS, "block": NULL_BLOCK, "seeds": SEEDS}),
                 "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF",
                             "LIVE": "OFF", "FROZEN_ARTIFACT_WRITE": 0, "ONTOLOGY_MODIFIED": 0, "PARAM_MODIFIED": 0,
                             "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO"}})
    outp = os.path.join(R1, "reports", f"V1_R2_R1_PHASE1_DIAGNOSIS_{mode.upper()}.json")
    wjson(outp, rep)
    led = os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl")
    with open(led, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_1", "mode": mode, "report": os.path.relpath(outp, REPO),
                              "preregistration_hash": pre_hash}, ensure_ascii=False) + "\n")
    print("WROTE", outp)
    print(json.dumps(rep, ensure_ascii=False, default=str)[:3000])


if __name__ == "__main__":
    main()
