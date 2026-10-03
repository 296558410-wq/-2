"""Grand Architecture program driver.

Runs the full read-only research program end to end and writes every deliverable
under V2_GRAND_ARCHITECTURE/. Nothing here touches production state.
"""
from __future__ import annotations
import json
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common import data as D, eval as E, metrics as M, hashing, protocol, cost as C
from strategy_factory import factory as F, mechanisms as MECH
from strategy_registry import StrategyRegistry
from strategy_brain import brain as BRAIN
from strategy_memory import StrategyMemory
from evolution import engine as EVO
from opportunity_hub import hub as HUB
from intelligence import IntelligenceInterface
from gpu_research import engine as GE, benchmark as GB
from common import pit as PIT

SEED = 20261003
DECAY_LAB = r"C:\AIQuant\research\hermes\trader_v2\V2_HISTORICAL_STRATEGY_DECAY_LAB"
V1_DB = r"C:\AIQuant\research\hermes\audit\hermes_alpha_drift_pit\V1_HERMES_TRADE_DATABASE.jsonl"


# --------------------------------------------------------------------------
# Stage 0: dataset
# --------------------------------------------------------------------------
def stage_dataset():
    df, man = D.load_research_dataset("1min")
    df15, man15 = D.load_research_dataset("15min")
    man["bars_15m"] = man15["n_bars"]
    return df, df15, man


def dataset_manifest(man: dict) -> dict:
    return {
        "schema": "grand_architecture_data_manifest/1",
        "code_commit": hashing.git_commit(),
        "created_utc": pd.Timestamp.utcnow().isoformat(),
        "generated_by": "pipeline/program.py:stage_dataset",
        "datasets": [
            {"name": "xauusd_1m", "freq": "1min", "n_bars": man["n_bars"],
             "date_min": man["date_min"], "date_max": man["date_max"],
             "dataset_hash": man["dataset_hash"]},
            {"name": "xauusd_15m", "freq": "15min", "n_bars": man["bars_15m"],
             "dataset_hash": man["dataset_hash"]},
        ],
        "source": man["source"], "source_dir": man["source_dir"],
        "n_tick_files": man["n_tick_files"], "n_ticks": man["n_ticks"],
        "file_hashes": man["file_hashes"],
        "observed_spread_median_price_units": man["observed_spread_median"],
        "splits": man["splits"],
        "pit_policy": "features use bars<=t; labels from t+1..t+h; OOS untouched until reveal",
        "note": "research-only; V2 production state untouched",
    }


# --------------------------------------------------------------------------
# Stage 1+2: factory + registry + evaluation
# --------------------------------------------------------------------------
def _regime_at(df, t0_list):
    reg = df["regime"].to_numpy()
    times = pd.to_datetime(df["bar_end_utc"], utc=True)
    idx = pd.Series(range(len(df)), index=times)
    out = []
    for t in t0_list:
        try:
            i = idx.asof(pd.Timestamp(t))
        except Exception:
            i = None
        out.append(reg[int(i)] if i is not None and np.isfinite(i) else "UNKNOWN")
    return out


def stage_factory_and_eval(df, man, reg: StrategyRegistry):
    specs = F.generate_specs()
    cost = C.round_trip_cost_price(df["spread"].to_numpy())
    masks = E.split_masks(df)
    results = {}
    for s in specs:
        reg.register(s)
        sig = F.run_mechanism(df, s)
        per = {}
        trades = {}
        for name, m in masks.items():
            t = E.trade_table(df, np.where(m, sig, 0.0), s.expected_horizon, cost)
            trades[name] = t
            per[name] = E.summarize(t)
        # discovery stats + GPU bootstrap/permutation
        dnet = trades["discovery"]["net"]
        boot = GE.gpu_bootstrap_ci(dnet, n_boot=4000, block=10, seed=SEED) if dnet.size >= 20 \
            else (float("nan"),) * 3
        pgross = trades["discovery"]["gross"]
        perm = GE.gpu_permutation_pvalue(pgross, n_perm=4000, seed=SEED) if pgross.size >= 10 \
            else (float("nan"), float("nan"))
        regs = _regime_at(df, trades["discovery"]["t0"]) if trades["discovery"]["t0"] else []
        fit = (float(np.mean([r in s.applicable_regime for r in regs])) if regs else float("nan"))
        # cost robustness: 2x cost still positive
        net2 = trades["discovery"]["net"] - cost
        cost_rob = float(np.nanmean(net2) > 0) if net2.size else float("nan")
        results[s.strategy_id] = {
            "mechanism": s.mechanism, "horizon": s.expected_horizon,
            "applicable_regime": s.applicable_regime,
            "splits": per,
            "bootstrap": {"mean": boot[0], "lo": boot[1], "hi": boot[2]},
            "permutation": {"obs": perm[0], "p": perm[1]},
            "regime_fit": fit, "cost_robust_2x": cost_rob,
            "discovery_regimes": {r: int(regs.count(r)) for r in set(regs)},
        }
    # FDR across strategies on discovery permutation p
    pvals = [results[s.strategy_id]["permutation"]["p"] for s in specs]
    q = M.benjamini_hochberg(pvals, 0.05)
    for s, ok in zip(specs, q):
        results[s.strategy_id]["fdr_pass"] = bool(ok)
    return specs, results, cost


def competition(results: dict) -> dict:
    """Combined competition score (NOT sort-by-return)."""
    ids = list(results)
    def norm(vals):
        a = np.asarray(vals, dtype=np.float64)
        finite = np.isfinite(a)
        if finite.sum() == 0:
            return np.zeros_like(a)
        lo, hi = np.nanmin(a[finite]), np.nanmax(a[finite])
        if hi == lo:
            return np.zeros_like(a)
        z = (a - lo) / (hi - lo)
        return np.where(finite, z, 0.0)
    perf = norm([results[i]["splits"]["discovery"]["expectancy"] for i in ids])
    stab = norm([results[i]["splits"]["discovery"]["stability"] for i in ids])
    fit = norm([results[i]["regime_fit"] for i in ids])
    samp = norm([min(results[i]["splits"]["discovery"]["n_eff"], 30) for i in ids])
    costr = norm([results[i]["cost_robust_2x"] for i in ids])
    out = {}
    for k, i in enumerate(ids):
        score = 0.25 * perf[k] + 0.20 * stab[k] + 0.20 * fit[k] + 0.15 * samp[k] + 0.20 * costr[k]
        out[i] = {"combined_score": round(float(score), 4),
                  "components": {"performance": round(float(perf[k]), 3),
                                 "stability": round(float(stab[k]), 3),
                                 "regime_fit": round(float(fit[k]), 3),
                                 "sample_size": round(float(samp[k]), 3),
                                 "cost_robustness": round(float(costr[k]), 3)}}
    return out


def assign_lifecycle(reg: StrategyRegistry, specs, results: dict, comp: dict):
    candidates = []
    for s in specs:
        r = results[s.strategy_id]
        oos = r["splits"]["oos"]
        val = r["splits"]["validation"]
        disc = r["splits"]["discovery"]
        reg.append_history(s.strategy_id, "validation", val)
        reg.append_history(s.strategy_id, "oos", oos)
        reg.append_history(s.strategy_id, "regime",
                           {"discovery_regimes": r["discovery_regimes"], "regime_fit": r["regime_fit"]})
        state = "RESEARCH"
        reason = "no statistically supported edge"
        if r["fdr_pass"] and disc["n_eff"] >= 10 and (oos["n_eff"] or 0) >= 5 \
                and np.isfinite(oos["expectancy"]) and oos["expectancy"] > 0:
            state, reason = "SHADOW", "FDR-pass on discovery + positive untouched OOS"
            if np.isfinite(val["expectancy"]) and val["expectancy"] > 0 and \
                    np.isfinite(disc["stability"]) and disc["stability"] >= 0.6:
                state, reason = "CANDIDATE", "FDR-pass + val>0 + oos>0 + stable"
            candidates.append(s.strategy_id)
        reg.records[s.strategy_id]["competition"] = comp[s.strategy_id]
        if state != "RESEARCH":
            reg.transition(s.strategy_id, state, reason)
        reg.records[s.strategy_id]["failure_reason"] = None if state != "RESEARCH" else reason
    return candidates


# --------------------------------------------------------------------------
# Stage: baselines + regime matrix
# --------------------------------------------------------------------------
def simple_baselines(df15, cost):
    base = {}
    masks = E.split_masks(df15)
    specs = {
        "V1_M15_vs_MA20": ("ma20_trend", 20),
        "SIMPLE_MOMENTUM": ("momentum", 20),
        "SIMPLE_MEANREV": ("meanrev", 20),
        "SIMPLE_BREAKOUT": ("breakout", 40),
        "V2_REFERENCE_PROXY": ("mtf", 30),
    }
    close = df15["close"].to_numpy()
    for name, (kind, w) in specs.items():
        n = len(df15)
        sig = np.zeros(n)
        if kind == "ma20_trend":
            ma = df15["ma20"].to_numpy()
            sig[close > ma] = 1.0; sig[close < ma] = -1.0
        elif kind == "momentum":
            r = df15[f"ret{20}"].to_numpy() if "ret20" in df15 else close - np.roll(close, 20)
            sig[r > 0] = 1.0; sig[r < 0] = -1.0
        elif kind == "meanrev":
            r = df15["ret20"].to_numpy()
            reg = df15["regime"].to_numpy()
            sig[(r > 0) & (reg == "RANGE")] = -1.0
            sig[(r < 0) & (reg == "RANGE")] = 1.0
        elif kind == "breakout":
            c = close; hh = df15["hh40"].to_numpy(); ll = df15["ll40"].to_numpy()
            sig[c > hh] = 1.0; sig[c < ll] = -1.0
        elif kind == "mtf":
            r5 = df15["ret5"].to_numpy(); r20 = df15["ret20"].to_numpy(); r60 = df15["ret60"].to_numpy()
            sig[(r5 > 0) & (r20 > 0) & (r60 > 0)] = 1.0
            sig[(r5 < 0) & (r20 < 0) & (r60 < 0)] = -1.0
        per = {}
        for nm, m in masks.items():
            t = E.trade_table(df15, np.where(m, sig, 0.0), w, cost)
            per[nm] = E.summarize(t)
        base[name] = per
    # random control
    rng = np.random.default_rng(SEED)
    rsig = rng.choice([-1.0, 0.0, 1.0], size=len(df15), p=[0.15, 0.7, 0.15])
    rper = {}
    for nm, m in masks.items():
        t = E.trade_table(df15, np.where(m, rsig, 0.0), 20, cost)
        rper[nm] = E.summarize(t)
    base["RANDOM_CONTROL"] = rper
    return base


def regime_strategy_matrix(df, specs, results, cost):
    """strategy_family x regime -> expectancy / n_eff / oos."""
    fam = {}
    masks = E.split_masks(df)
    for s in specs:
        sig = F.run_mechanism(df, s)
        for nm, m in masks.items():
            t = E.trade_table(df, np.where(m, sig, 0.0), s.expected_horizon, cost)
            regs = _regime_at(df, t["t0"])
            if not regs:
                continue
            regs = np.asarray(regs)
            for r in set(regs):
                sel = regs == r
                net = t["net"][sel]
                if net.size == 0:
                    continue
                key = s.mechanism
                e = fam.setdefault(key, {})
                d = e.setdefault(r, {"n_eff": 0, "net_sum": 0.0, "wins": 0})
                d["n_eff"] += int(net.size)
                d["net_sum"] += float(net.sum())
                d["wins"] += int((net > 0).sum())
    out = {}
    for mech, byreg in fam.items():
        out[mech] = {}
        for r, d in byreg.items():
            out[mech][r] = {
                "n_eff": d["n_eff"],
                "expectancy": round(d["net_sum"] / d["n_eff"], 4) if d["n_eff"] else float("nan"),
                "precision": round(d["wins"] / d["n_eff"], 3) if d["n_eff"] else float("nan"),
                "total": round(d["net_sum"], 3),
            }
    return out
