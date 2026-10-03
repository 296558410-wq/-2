"""Remaining program stages: GPU search, brain, hub, memory, failure,
retirement, portfolio, evolution, experiments, replay."""
from __future__ import annotations
import json
import os
import sys
import numpy as np
import pandas as pd
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from program import (SEED, DECAY_LAB, V1_DB, _regime_at)
from common import data as D, eval as E, metrics as M, hashing, cost as C
from strategy_factory import factory as F, mechanisms as MECH
from strategy_brain import brain as BRAIN
from strategy_memory import StrategyMemory
from evolution import engine as EVO
from opportunity_hub import hub as HUB
from gpu_research import engine as GE, benchmark as GB

SPLITS = D.SPLITS


# --------------------------------------------------------------------------
# Stage: GPU large-scale strategy search
# --------------------------------------------------------------------------
def gpu_search(df, cost_price, top_k=60, chunk=256):
    c = GE.to_device(df["close"].to_numpy())
    n = c.shape[0]
    d = pd.to_datetime(df["bar_end_utc"], utc=True).dt.date
    def rng(a, b):
        return int(np.searchsorted(d.to_numpy(), np.datetime64(a))), int(
            np.searchsorted(d.to_numpy(), np.datetime64(b), side="right"))
    disc = rng(SPLITS["discovery"][0], SPLITS["discovery"][1])
    val = rng(SPLITS["validation"][0], SPLITS["validation"][1])
    oos = rng(SPLITS["oos"][0], SPLITS["oos"][1])

    h = 20
    fr = GE.forward_return_gpu(df["close"].to_numpy(), h)  # price units

    grid = {"fast": list(range(3, 41, 2)), "slow": list(range(10, 121, 5)),
            "thr": [0.0002, 0.0005, 0.001, 0.002, 0.003], "sign": [1, -1]}
    combos = []
    for f in grid["fast"]:
        for s in grid["slow"]:
            if f >= s:
                continue
            for t in grid["thr"]:
                for sg in grid["sign"]:
                    combos.append((f, s, t, sg))
    ma_cache = {w: GE.rolling_mean(c, w) for w in set(grid["fast"]) | set(grid["slow"])}

    searched = len(combos)
    rows = []
    for start in range(0, len(combos), chunk):
        batch = combos[start:start + chunk]
        sigs = []
        for (f, s, t, sg) in batch:
            gap = (ma_cache[f] - ma_cache[s]) / ma_cache[s]
            sig = torch.zeros(n, device=c.device)
            sig[gap > t] = 1.0 * sg
            sig[gap < -t] = -1.0 * sg
            sigs.append(sig)
        S = torch.stack(sigs, 0)
        G = fr.unsqueeze(0).expand_as(S)
        net = torch.where(S != 0, S * G - cost_price, torch.full_like(S, float("nan")))
        for j, combo in enumerate(batch):
            row = net[j]
            def stat(lo, hi):
                seg = row[lo:hi]
                seg = seg[torch.isfinite(seg)]
                if seg.numel() == 0:
                    return 0, float("nan")
                return int(seg.numel()), float(seg.mean().item())
            dn, de = stat(*disc)
            vn, ve = stat(*val)
            on, oe = stat(*oos)
            rows.append({"fast": combo[0], "slow": combo[1], "thr": combo[2], "sign": combo[3],
                         "disc_n": dn, "disc_exp": de, "val_n": vn, "val_exp": ve,
                         "oos_n": on, "oos_exp": oe})
    tbl = pd.DataFrame(rows)
    # discovery ranking requires a minimum sample
    elig = tbl[(tbl.disc_n >= 30)].copy()
    elig = elig.sort_values("disc_exp", ascending=False)
    selected = elig.head(top_k).copy()
    return {"searched_hypotheses": searched, "eligible": int(len(elig)),
            "selected_top_k": top_k, "splits_idx": {"disc": disc, "val": val, "oos": oos},
            "table": tbl, "selected": selected}


# --------------------------------------------------------------------------
# Stage: Multi-Strategy Brain
# --------------------------------------------------------------------------
def brain_run(df, specs, results, cost):
    masks = E.split_masks(df)
    sigs = {s.strategy_id: F.run_mechanism(df, s) for s in specs}
    # calibrate confidence/stability on DISCOVERY only (no leakage)
    calib = {}
    for s in specs:
        r = results[s.strategy_id]["splits"]["discovery"]
        prec = r["precision"] if np.isfinite(r["precision"]) else 0.5
        calib[s.strategy_id] = {
            "confidence": float(min(0.95, max(0.3, prec))),
            "recent_stability": float(r["stability"]) if np.isfinite(r["stability"]) else 0.5,
        }
    med_h = int(np.median([s.expected_horizon for s in specs]))
    decisions = []
    seg_masks = {"discovery": masks["discovery"], "validation": masks["validation"], "oos": masks["oos"]}
    idx_all = np.arange(len(df))
    for seg, m in seg_masks.items():
        idxs = idx_all[m]
        for i in idxs:
            votes = []
            for s in specs:
                v = sigs[s.strategy_id][i]
                if v != 0:
                    votes.append(BRAIN.vote_from_signal(
                        s.strategy_id, s.mechanism, v, calib[s.strategy_id]["confidence"],
                        df["regime"].iloc[i], s.applicable_regime,
                        calib[s.strategy_id]["recent_stability"]))
            d = BRAIN.decide(votes, data_ok=True, risk_allows=True, min_votes=2, min_confidence=0.55)
            decisions.append({"seg": seg, "i": int(i), "decision": d.final_decision,
                              "conflict": d.conflict_state, "direction": int(d.direction),
                              "n_votes": len(votes), "conf": d.confidence})
    dec = pd.DataFrame(decisions)
    # evaluate brain trades per segment
    mid = df["close"].to_numpy()
    stats = {}
    for seg in ("discovery", "validation", "oos"):
        sub = dec[(dec.seg == seg) & (dec.decision.isin(["ENTER_LONG", "ENTER_SHORT"]))]
        nets = []
        for _, row in sub.iterrows():
            i = int(row.i)
            if i + med_h >= len(mid):
                continue
            sg = 1 if row.decision == "ENTER_LONG" else -1
            nets.append(sg * (mid[i + med_h] - mid[i]) - cost)
        nets = np.asarray(nets)
        stats[seg] = {
            "n_decisions": int(len(dec[dec.seg == seg])),
            "n_enter": int(len(sub)),
            "n_eff": int(nets.size),
            "expectancy": float(nets.mean()) if nets.size else float("nan"),
            "total": float(nets.sum()) if nets.size else float("nan"),
            "precision": float((nets > 0).mean()) if nets.size else float("nan"),
        }
    conflict_counts = dec.groupby("seg")["conflict"].value_counts().unstack(fill_value=0).to_dict()
    return {"stats": stats, "conflict_counts": conflict_counts,
            "median_horizon": med_h, "calibration": calib}


# --------------------------------------------------------------------------
# Stage: Opportunity Hub
# --------------------------------------------------------------------------
def hub_run(df):
    rows = []
    # sample every 5 bars to bound compute
    for i in range(60, len(df), 5):
        rows.append(HUB.generate(df, i))
    conc = HUB.concentration(rows)
    return {"concentration": conc, "n_opportunity_bars": len(rows)}


# --------------------------------------------------------------------------
# Stage: Strategy Memory + Failure Analysis
# --------------------------------------------------------------------------
def memory_and_failure(df, specs, cost, mem_path):
    mem = StrategyMemory(mem_path)
    failure = {}
    for s in specs:
        sig = F.run_mechanism(df, s)
        t = E.trade_table(df, sig, s.expected_horizon, cost)
        regs = _regime_at(df, t["t0"])
        for k in range(t["net"].size):
            ftype = classify_failure(t["net"][k], t["gross"][k], t["mfe"][k], t["mae"][k],
                                     regs[k] if k < len(regs) else "UNKNOWN", s.applicable_regime)
            mem.record_prediction(strategy_id=s.strategy_id, decision_time=t["t0"][k],
                                  direction=int(t["side"][k]), confidence=0.5,
                                  regime=regs[k] if k < len(regs) else "UNKNOWN",
                                  price=float(df["close"].iloc[0]), horizon=s.expected_horizon,
                                  strategy_age_bars=0)
            mem.attach_outcome(len(mem.records) - 1, outcome_time=t["t1"][k],
                               mfe=float(t["mfe"][k]), mae=float(t["mae"][k]),
                               net=float(t["net"][k]), failure_type=ftype)
            if ftype:
                key = (s.mechanism, ftype)
                failure[key] = failure.get(key, 0) + 1
    mem.flush()
    return {"records": len(mem.records), "failure_counts": {"|".join(k): v for k, v in failure.items()}}


def classify_failure(net, gross, mfe, mae, regime, applicable):
    if net >= 0:
        return None
    if gross > 0:
        return "COST_ERROR"
    if mfe > 0 and abs(gross) < mfe:
        return "TIMING_ERROR"
    if regime not in applicable:
        return "REGIME_ERROR"
    if gross < 0:
        return "DIRECTION_ERROR"
    return "NO_IDENTIFIABLE_ERROR"


# --------------------------------------------------------------------------
# Stage: Portfolio layer
# --------------------------------------------------------------------------
def portfolio(df, specs, results, cost):
    masks = E.split_masks(df)
    d = pd.to_datetime(df["bar_end_utc"], utc=True).dt.date
    valid = masks["validation"] | masks["oos"]
    series = {}
    for s in specs:
        sig = F.run_mechanism(df, s)
        t = E.trade_table(df, sig, s.expected_horizon, cost)
        if t["net"].size == 0:
            continue
        dates = pd.to_datetime([x for x in t["t0"]], utc=True).date
        sr = pd.Series(t["net"], index=dates)
        sr = sr.groupby(level=0).sum()
        series[s.strategy_id] = sr
    if not series:
        return {"note": "no strategies with trades", "corr": {}}
    mat = pd.DataFrame(series).fillna(0.0)
    corr = mat.corr()
    vals = corr.to_numpy()
    off = vals[~np.eye(len(vals), dtype=bool)]
    # weights from DISCOVERY only
    disc_exp = {s.strategy_id: results[s.strategy_id]["splits"]["discovery"]["expectancy"]
                for s in specs if s.strategy_id in series}
    fin = {k: v for k, v in disc_exp.items() if np.isfinite(v)}
    equal_w = {k: 1.0 / len(fin) for k in fin} if fin else {}
    tot = sum(max(v, 0) for v in fin.values())
    conf_w = {k: (max(v, 0) / tot if tot > 0 else 0) for k, v in fin.items()}
    def combo_oos(w):
        tot_net = 0.0
        for sid, wt in w.items():
            r = results[sid]["splits"]["oos"]
            if np.isfinite(r["total"]):
                tot_net += wt * r["total"]
        return tot_net
    # single best by discovery expectancy
    best = max(fin, key=fin.get) if fin else None
    out = {
        "n_strategies_with_trades": len(series),
        "corr_mean_offdiag": float(np.nanmean(off)) if off.size else float("nan"),
        "corr_max_offdiag": float(np.nanmax(off)) if off.size else float("nan"),
        "same_factor_flag": bool(off.size and np.nanmax(off) > 0.6),
        "single_best_discovery": best,
        "single_best_oos_total": float(results[best]["splits"]["oos"]["total"]) if best else float("nan"),
        "equal_weight_oos_total": combo_oos(equal_w),
        "confidence_weight_oos_total": combo_oos(conf_w),
        "note": "weights fixed from discovery; OOS strict; correlation of daily net",
    }
    return out


# --------------------------------------------------------------------------
# Stage: Evolution
# --------------------------------------------------------------------------
def evolution_run(specs, results):
    out = {}
    for s in specs:
        disc = results[s.strategy_id]["splits"]["discovery"]
        val = results[s.strategy_id]["splits"]["validation"]
        oos = results[s.strategy_id]["splits"]["oos"]
        m = EVO.MonitorState(
            strategy_id=s.strategy_id,
            edge=val["expectancy"] if np.isfinite(val["expectancy"]) else 0.0,
            edge_baseline=disc["expectancy"] if np.isfinite(disc["expectancy"]) else 0.0,
            mfe=val["mfe"], mae=val["mae"], confidence_mean=0.5,
            hit_rate=val["precision"] if np.isfinite(val["precision"]) else 0.0,
            regime_now="UNKNOWN", regime_then="UNKNOWN",
            cost_sens=(results[s.strategy_id]["cost_robust_2x"] - 1.0) if np.isfinite(
                results[s.strategy_id]["cost_robust_2x"]) else 0.0,
        )
        hist = {"pass": bool(np.isfinite(val["expectancy"]) and val["expectancy"] > 0 and val["n_eff"] >= 5)}
        oosr = {"pass": bool(np.isfinite(oos["expectancy"]) and oos["expectancy"] > 0 and oos["n_eff"] >= 5)}
        out[s.strategy_id] = EVO.evolve(m, oos_result=oosr, historical_result=hist)
    counts = {}
    for v in out.values():
        counts[v["state"]] = counts.get(v["state"], 0) + 1
    return {"states": out, "counts": counts}
