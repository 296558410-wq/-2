"""Experiments A-F and historical replay."""
from __future__ import annotations
import json
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from program import SEED, DECAY_LAB, V1_DB, _regime_at
from common import data as D, eval as E, metrics as M, hashing, cost as C
from strategy_factory import factory as F
from strategy_brain import brain as BRAIN

VERDICTS = ["PASS", "FAIL", "INCONCLUSIVE", "NOT_SUPPORTED", "NOT_EVALUABLE"]


def max_drawdown(net: np.ndarray) -> float:
    if net.size == 0:
        return float("nan")
    cum = np.cumsum(net)
    peak = np.maximum.accumulate(cum)
    return float((cum - peak).min())


def _factory_oos_ensemble(df, specs, results, cost, direction_filter=None):
    """Equal-weight ensemble (by discovery-positive strategies) OOS trades."""
    good = [s for s in specs if np.isfinite(results[s.strategy_id]["splits"]["discovery"]["expectancy"])
            and results[s.strategy_id]["splits"]["discovery"]["expectancy"] > 0]
    masks = E.split_masks(df)
    d = pd.to_datetime(df["bar_end_utc"], utc=True).dt.date
    nets = []
    for s in good:
        sig = F.run_mechanism(df, s)
        t = E.trade_table(df, np.where(masks["oos"], sig, 0.0), s.expected_horizon, cost)
        nets.extend(t["net"].tolist())
    return np.asarray(nets), [s.strategy_id for s in good]


def experiment_A(baselines, df, specs, results, cost):
    ensemble, used = _factory_oos_ensemble(df, specs, results, cost)
    single_v1 = baselines["V1_M15_vs_MA20"]["oos"]
    single_ref = baselines["V2_REFERENCE_PROXY"]["oos"]
    return {
        "single_v1_oos_total": single_v1["total"], "single_v1_n": single_v1["n_eff"],
        "single_reference_oos_total": single_ref["total"], "single_reference_n": single_ref["n_eff"],
        "multi_strategy_oos_total": float(ensemble.sum()) if ensemble.size else float("nan"),
        "multi_strategy_n": int(ensemble.size),
        "multi_strategies_used": used,
        "verdict": ("PASS" if ensemble.size >= 10 and np.isfinite(single_v1["total"])
                    and ensemble.sum() > max(single_v1["total"] or -1e9, single_ref["total"] or -1e9)
                    else "INCONCLUSIVE" if ensemble.size < 10 else "NOT_SUPPORTED"),
    }


def experiment_B(baselines, df, specs, results, cost):
    ensemble, used = _factory_oos_ensemble(df, specs, results, cost)
    single = None
    for s in specs:
        r = results[s.strategy_id]["splits"]["oos"]
        if np.isfinite(r["total"]) and (single is None or r["total"] > single[1]):
            single = (s.strategy_id, r["total"])
    if ensemble.size < 10:
        return {"verdict": "NOT_EVALUABLE", "reason": "insufficient multi-strategy OOS trades",
                "multi_n": int(ensemble.size)}
    dd_multi = max_drawdown(ensemble)
    # best single drawdown
    dd_single = float("nan")
    if single:
        s = next(x for x in specs if x.strategy_id == single[0])
        sig = F.run_mechanism(df, s)
        masks = E.split_masks(df)
        t = E.trade_table(df, np.where(masks["oos"], sig, 0.0), s.expected_horizon, cost)
        dd_single = max_drawdown(t["net"])
    false_multi = float((ensemble < 0).mean())
    return {
        "multi_max_drawdown": dd_multi, "single_best": single[0] if single else None,
        "single_max_drawdown": dd_single,
        "multi_false_signal_rate": false_multi,
        "reduces_drawdown": bool(np.isfinite(dd_single) and dd_multi > dd_single),
        "verdict": "INCONCLUSIVE",
    }


def experiment_C(brain_stats, df, specs, results, cost):
    ensemble, used = _factory_oos_ensemble(df, specs, results, cost)
    fixed_total = float(ensemble.sum()) if ensemble.size else float("nan")
    brain_oos = brain_stats["stats"]["oos"]
    return {
        "fixed_combo_oos_total": fixed_total,
        "brain_oos_total": brain_oos["total"], "brain_oos_n": brain_oos["n_eff"],
        "brain_oos_enter": brain_oos["n_enter"], "brain_oos_decisions": brain_oos["n_decisions"],
        "verdict": ("PASS" if brain_oos["n_eff"] >= 5 and np.isfinite(brain_oos["total"])
                    and np.isfinite(fixed_total) and brain_oos["total"] > fixed_total
                    else "INCONCLUSIVE"),
    }


def experiment_D(evolution, results=None):
    counts = evolution["counts"]
    triggered = sum(1 for v in evolution["states"].values() if v["triggers"])
    released = [sid for sid, v in evolution["states"].items() if v["state"] == "CANDIDATE_RELEASE"]
    supported = [sid for sid in released if results and results.get(sid, {}).get("fdr_pass")]
    if supported:
        verdict = "PASS"
    elif released:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "NOT_SUPPORTED"
    return {
        "states": counts,
        "n_strategies_with_triggers": triggered,
        "n_release": counts.get("CANDIDATE_RELEASE", 0),
        "n_shadow": counts.get("SHADOW", 0),
        "released_ids": released,
        "released_with_fdr_support": supported,
        "verdict": verdict,
        "note": "no fixed 48h; triggers evidence-based; release requires FDR support to count as evidence",
    }


def experiment_E(gpu, results, specs, df, cost):
    sel = gpu["selected"]
    stable = 0
    for _, row in sel.iterrows():
        if np.isfinite(row.val_exp) and row.val_exp > 0 and np.isfinite(row.oos_exp) and row.oos_exp > 0 \
                and row.oos_n >= 10:
            stable += 1
    manual_stable = 0
    for s in specs:
        r = results[s.strategy_id]["splits"]
        if np.isfinite(r["validation"]["expectancy"]) and r["validation"]["expectancy"] > 0 \
                and np.isfinite(r["oos"]["expectancy"]) and r["oos"]["expectancy"] > 0 \
                and r["oos"]["n_eff"] >= 5:
            manual_stable += 1
    return {
        "manual_mechanism_candidates": len(specs), "manual_stable": manual_stable,
        "gpu_searched_hypotheses": gpu["searched_hypotheses"],
        "gpu_selected": len(sel), "gpu_stable_after_validation_and_oos": int(stable),
        "verdict": ("PASS" if stable > manual_stable else
                    "INCONCLUSIVE" if stable == manual_stable else "NOT_SUPPORTED"),
        "note": "objective is enumerable stability, not a return champion",
    }


def experiment_F(df, specs, results, cost):
    trades = [json.loads(l) for l in open(V1_DB, encoding="utf-8") if l.strip()]
    v1 = [t for t in trades if t.get("system") == "V1_OLD" and t.get("closed")]
    sigs = {s.strategy_id: F.run_mechanism(df, s) for s in specs}
    times = pd.to_datetime(df["bar_end_utc"], utc=True)
    idx = pd.Series(range(len(df)), index=times)
    hits, total = 0, 0
    for t in v1:
        try:
            i = idx.asof(pd.Timestamp(t["entry_ts"]))
        except Exception:
            continue
        if i is None or not np.isfinite(i):
            continue
        i = int(i)
        v1dir = 1 if t["direction"] == "LONG" else -1
        agree = sum(1 for sid, sg in sigs.items() if sg[i] == v1dir)
        total += 1
        if agree >= 2:
            hits += 1
    rate = hits / total if total else float("nan")
    return {
        "v1_old_trades": len(v1), "replayed": total,
        "captured_by_factory_ge2_agree": hits, "capture_rate": rate,
        "verdict": ("PASS" if total and rate >= 0.5 else
                    "NOT_SUPPORTED" if total >= 20 else "NOT_EVALUABLE"),
        "note": "PIT features at V1 entry timestamps; no V1 outcome used as label",
    }


def replay_v1(df, specs):
    """Section 二十一: replay Factory/Brain on real V1 executable history."""
    trades = [json.loads(l) for l in open(V1_DB, encoding="utf-8") if l.strip()]
    out = {}
    for system in ("V1_OLD", "V1_NEW"):
        rows = [t for t in trades if t.get("system") == system and t.get("closed")]
        if not rows:
            continue
        pnl = np.array([t["net"] for t in rows], dtype=float)
        out[system] = {
            "n_trades": len(rows),
            "net_total": float(pnl.sum()),
            "win_rate": float((pnl > 0).mean()),
            "entry_ts_min": min(t["entry_ts"] for t in rows),
            "entry_ts_max": max(t["entry_ts"] for t in rows),
        }
    return out
