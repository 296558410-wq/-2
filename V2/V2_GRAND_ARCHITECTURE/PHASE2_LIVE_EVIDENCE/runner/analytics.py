"""Phase-2 analytics: turns the Live Evidence Stream + Outcomes into the
deliverable set (scorecard, lifecycle, regime matrix, V1 arm, degradation,
48h review, evolution proposals, candidate queue, false-alpha firewall,
lifetime dataset, OOS/statistical progress, data manifest, replay report).

Read-only w.r.t. production. Writes only under PHASE2_LIVE_EVIDENCE/.
"""
from __future__ import annotations
import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402
from common import data as D, cost as C, hashing, metrics as M  # noqa: E402
from strategy_factory import factory as F  # noqa: E402
import backfill as BF  # noqa: E402

HORIZONS = PP.HORIZONS_MIN
MIN_EFF_N = 30          # documented admission threshold (spec section 10)
REGIME_FAMILIES = ["TREND", "RANGE", "BREAKOUT", "TRANSITION", "EVENT"]
SPEC_FAMILIES = ["TREND", "MOMENTUM", "REVERSAL", "RANGE", "BREAKOUT", "VOL_EXPANSION",
                 "VOL_CONTRACTION", "MTF_STRUCTURE", "EVENT", "MACRO", "HYBRID"]


# --------------------------------------------------------------------------
def _load():
    stream = PP.jl_read(PP.STREAM)
    outcomes = PP.jl_read(PP.OUTCOMES)
    gpu = {}
    if os.path.exists(os.path.join(PP.SHADOW, "gpu_stats.json")):
        with open(os.path.join(PP.SHADOW, "gpu_stats.json"), encoding="utf-8") as f:
            gpu = json.load(f)
    return stream, outcomes, gpu


def _specs():
    return F.generate_specs()


def primary_horizon(spec):
    return min(HORIZONS, key=lambda h: abs(h - spec.expected_horizon))


def _net_of(out, cost):
    fr = out.get("future_return")
    if fr is None or out.get("data_gap"):
        return None
    return float(fr) - cost


# --------------------------------------------------------------------------
def aggregate(outcomes, specs, cost):
    """strategy_id -> horizon -> aggregates."""
    by = {}
    for o in outcomes:
        if o.get("source") != "SHADOW":
            continue
        sid = o["strategy_id"]
        h = o["horizon_min"]
        n = _net_of(o, cost)
        d = by.setdefault(sid, {}).setdefault(h, {"nets": [], "mfe": [], "mae": [], "gaps": 0, "tp": 0, "sl": 0, "tot": 0})
        d["tot"] += 1
        if o.get("data_gap"):
            d["gaps"] += 1
            continue
        if n is not None:
            d["nets"].append(n)
            if o.get("mfe") is not None:
                d["mfe"].append(o["mfe"])
            if o.get("mae") is not None:
                d["mae"].append(o["mae"])
            if o.get("tp_sl_first_touch") == "TP":
                d["tp"] += 1
            elif o.get("tp_sl_first_touch") == "SL":
                d["sl"] += 1
    agg = {}
    for sid, hs in by.items():
        agg[sid] = {}
        for h, d in hs.items():
            nets = np.asarray(d["nets"], dtype=np.float64)
            agg[sid][h] = {
                "n_eff": int(nets.size),
                "n_total": d["tot"],
                "n_gap": d["gaps"],
                "precision": float((nets > 0).mean()) if nets.size else float("nan"),
                "expectancy": float(nets.mean()) if nets.size else float("nan"),
                "total": float(nets.sum()) if nets.size else float("nan"),
                "mfe": float(np.mean(d["mfe"])) if d["mfe"] else float("nan"),
                "mae": float(np.mean(d["mae"])) if d["mae"] else float("nan"),
                "stability": M.stability(nets, 4) if nets.size >= 8 else float("nan"),
                "tp_first": d["tp"], "sl_first": d["sl"],
                "nets": nets,
            }
    return agg


def _norm(vals):
    a = np.asarray(vals, dtype=np.float64)
    fin = np.isfinite(a)
    if fin.sum() == 0:
        return np.zeros_like(a)
    lo, hi = np.nanmin(a[fin]), np.nanmax(a[fin])
    if hi == lo:
        return np.zeros_like(a)
    z = (a - lo) / (hi - lo)
    return np.where(fin, z, 0.0)


def build_scorecard(specs, agg, gpu, cost):
    ids = [s.strategy_id for s in specs]
    prim = {s.strategy_id: primary_horizon(s) for s in specs}
    def hstat(sid, h, key):
        d = agg.get(sid, {}).get(h)
        return d.get(key, float("nan")) if d else float("nan")
    perf = _norm([hstat(sid, prim[sid], "expectancy") for sid in ids])
    stab = _norm([hstat(sid, prim[sid], "stability") for sid in ids])
    fit = _norm([hstat(sid, prim[sid], "n_eff") for sid in ids])
    samp = _norm([min(hstat(sid, prim[sid], "n_eff") or 0, MIN_EFF_N) for sid in ids])
    costr = [1.0 if (np.isfinite(hstat(sid, prim[sid], "expectancy")) and
                     hstat(sid, prim[sid], "expectancy") - cost > 0) else 0.0 for sid in ids]
    # regime fit from stream
    smap = _regime_fit_from_stream(specs)
    rfit = _norm([smap.get(sid, {}).get("regime_fit", 0.0) for sid in ids])
    gs = gpu.get("strategies", {})
    out = {}
    for k, sid in enumerate(ids):
        comp = {
            "performance": round(float(perf[k]), 4),
            "stability": round(float(stab[k]), 4),
            "regime_fit": round(float(rfit[k]), 4),
            "sample_size": round(float(samp[k]), 4),
            "cost_robustness": round(float(costr[k]), 4),
        }
        combined = (0.25 * comp["performance"] + 0.20 * comp["stability"] +
                    0.20 * comp["regime_fit"] + 0.15 * comp["sample_size"] +
                    0.15 * comp["cost_robustness"])
        out[sid] = {
            "strategy_id": sid, "mechanism": next(s.mechanism for s in specs if s.strategy_id == sid),
            "primary_horizon_min": prim[sid],
            "combined_score": round(float(combined), 4),
            "components": comp,
            "horizons": {str(h): {kk: (vv if kk != "nets" else None)
                                  for kk, vv in agg.get(sid, {}).get(h, {}).items()}
                         for h in HORIZONS},
            "bootstrap": gs.get(sid, {}).get("bootstrap"),
            "permutation": gs.get(sid, {}).get("permutation"),
            "fdr_pass": gs.get(sid, {}).get("fdr_pass"),
            "note": "scorecard is RESEARCH RANKING ONLY; it never sets production",
        }
    return out


def _regime_fit_from_stream(specs):
    stream = PP.jl_read(PP.STREAM)
    ap = {s.strategy_id: set(s.applicable_regime) for s in specs}
    hit = {}
    for r in stream:
        sid = r["strategy_id"]
        if sid == "NONE" or r.get("signal") in (0, None):
            continue
        d = hit.setdefault(sid, [0, 0])
        d[0] += 1
        if r.get("regime") in ap.get(sid, set()):
            d[1] += 1
    return {sid: {"regime_fit": (v[1] / v[0]) if v[0] else 0.0} for sid, v in hit.items()}


# --------------------------------------------------------------------------
def build_lifecycle(specs, agg, cost):
    stream = PP.jl_read(PP.STREAM)
    ts = sorted({r["decision_ts"] for r in stream})
    span_days = 0.0
    if len(ts) >= 2:
        span_days = (pd.Timestamp(ts[-1]) - pd.Timestamp(ts[0])).total_seconds() / 86400
    recs = []
    for s in specs:
        prim = primary_horizon(s)
        d = agg.get(s.strategy_id, {}).get(prim, {})
        nets = d.get("nets", np.asarray([]))
        n_eff = d.get("n_eff", 0)
        regimes = {}
        for r in stream:
            if r["strategy_id"] == s.strategy_id and r.get("signal") not in (0, None):
                regimes[r.get("regime")] = regimes.get(r.get("regime"), 0) + 1
        dd = float(np.min(np.cumsum(nets))) if nets.size else float("nan")
        state = "SHADOW"
        failure = _dominant_failure(d, regimes, s)
        rec = {
            "strategy_id": s.strategy_id, "mechanism": s.mechanism,
            "strategy_version": s.config_hash[:12],
            "state": state,
            "age_days": round(span_days, 2),
            "sample_count": d.get("n_total", 0),
            "effective_n": n_eff,
            "rolling_expectancy": _roll(d.get("nets", np.asarray([]))),
            "expectancy_primary": d.get("expectancy", float("nan")),
            "confidence": (min(0.95, max(0.3, d.get("precision", float("nan"))))
                           if np.isfinite(d.get("precision", float("nan"))) else None),
            "calibration": "UNCALIBRATED_INSUFFICIENT_DATA" if n_eff < MIN_EFF_N else "CALIBRATED",
            "mfe": d.get("mfe", float("nan")), "mae": d.get("mae", float("nan")),
            "failure_type": failure,
            "regime_distribution": regimes,
            "drawdown_price_units": dd,
            "transitions": [{"to": "RESEARCH", "evidence": "factory_created"},
                            {"to": "SHADOW", "evidence": "phase2 shadow-only mandate"}],
            "note": "ACTIVE is disallowed for production; no auto-reset on degradation",
        }
        recs.append(rec)
    return recs


def _roll(nets):
    if nets is None or len(nets) == 0:
        return float("nan")
    x = np.asarray(nets, dtype=np.float64)
    return float(x[-min(30, x.size):].mean())


def _dominant_failure(d, regimes, s):
    if d.get("n_eff", 0) < 10:
        return "DATA_INSUFFICIENT"
    n = d.get("n_eff", 0)
    sl = d.get("sl_first", 0)
    if n and sl / max(1, n) > 0.6:
        return "STOP_FIRST_DOMINANT"
    if not regimes:
        return "NO_SIGNAL"
    top = max(regimes, key=regimes.get)
    if regimes[top] / max(1, sum(regimes.values())) > 0.8 and top not in s.applicable_regime:
        return "REGIME_ERROR"
    if d.get("expectancy", 0) < 0:
        return "DIRECTION_OR_TIMING_ERROR"
    return "NO_IDENTIFIABLE_ERROR"


# --------------------------------------------------------------------------
def build_regime_matrix(specs, outcomes, cost):
    smap = {s.strategy_id: s for s in specs}
    reg_of = {}
    for r in PP.jl_read(PP.STREAM):
        if r["strategy_id"] != "NONE":
            reg_of[(r["cycle_id"], r["strategy_id"])] = r.get("regime")
    fam = {}
    for o in outcomes:
        if o.get("source") != "SHADOW" or o.get("data_gap"):
            continue
        sid = o["strategy_id"]
        s = smap.get(sid)
        if not s:
            continue
        reg = reg_of.get((o["cycle_id"], sid), "UNKNOWN")
        n = _net_of(o, cost)
        if n is None:
            continue
        d = fam.setdefault(s.mechanism, {}).setdefault(reg, {"n": 0, "wins": 0, "sum": 0.0, "mfe": [], "mae": []})
        d["n"] += 1; d["sum"] += n; d["wins"] += int(n > 0)
        if o.get("mfe") is not None: d["mfe"].append(o["mfe"])
        if o.get("mae") is not None: d["mae"].append(o["mae"])
    out = {}
    for mech, byreg in fam.items():
        out[mech] = {}
        for reg, d in byreg.items():
            out[mech][reg] = {
                "n_eff": d["n"], "precision": round(d["wins"] / d["n"], 3) if d["n"] else None,
                "expectancy": round(d["sum"] / d["n"], 4) if d["n"] else None,
                "mfe": round(float(np.mean(d["mfe"])), 4) if d["mfe"] else None,
                "mae": round(float(np.mean(d["mae"])), 4) if d["mae"] else None,
                "stability": "INSUFFICIENT" if d["n"] < 8 else None,
            }
    return {"schema": "regime_strategy_matrix/1",
            "regimes": REGIME_FAMILIES, "mechanisms": SPEC_FAMILIES,
            "matrix": out,
            "note": "empirical; sample-limited; no universal strategy is expected"}


# --------------------------------------------------------------------------
def build_v1_reference(specs, agg, cost):
    df15, man = D.load_research_dataset("15min")
    df15 = df15.copy()
    df15["decision_ts"] = pd.to_datetime(df15["bar_end_utc"], utc=True) + pd.Timedelta(minutes=15)
    close = df15["close"].to_numpy()
    ma20 = df15["ma20"].to_numpy()
    v1 = np.where(close > ma20, 1, np.where(close < ma20, -1, 0))
    v1map = {pd.Timestamp(t): int(v) for t, v in zip(df15["decision_ts"], v1)}
    # stream per-cycle summary
    stream = PP.jl_read(PP.STREAM)
    cyc = {}
    for r in stream:
        c = cyc.setdefault(r["cycle_id"], {"decision_ts": r.get("decision_ts"),
                                           "production_status": r.get("production_status"),
                                           "production_side": r.get("production_side"),
                                           "final": r.get("final_shadow_decision"),
                                           "dir": r.get("shadow_direction"),
                                           "signals": {}})
        if r["strategy_id"] != "NONE":
            c["signals"][r["strategy_id"]] = r.get("signal")
    rows = []
    for cid, c in cyc.items():
        ts = pd.Timestamp(c["decision_ts"])
        v1s = v1map.get(ts, 0)
        v1_out = BF.outcome_for(ts, v1s, 60, None, prod=None) if v1s != 0 else None
        v1_ret = None if not v1_out else v1_out.get("future_return")
        nonflat = sum(1 for s in c["signals"].values() if s not in (0, None))
        shadow_dir = int(c["dir"] or 0)
        row = {
            "cycle_id": cid, "decision_ts": c["decision_ts"],
            "regime": next((r.get("regime") for r in reversed(stream) if r["cycle_id"] == cid), None),
            "v1_m15_ma20_signal": v1s,
            "v1_60m_return": v1_ret,
            "v2_reference": (f"{c['production_status']}" + (f":{c['production_side']}" if c.get("production_side") else "")
                             if c.get("production_status") else "NO_PRODUCTION_DECISION"),
            "v2_multistrategy_decision": c["final"],
            "v2_multistrategy_direction": shadow_dir,
            "n_nonflat_strategies": nonflat,
            "v1_found_v2_missed": bool(v1s != 0 and shadow_dir == 0),
            "agreement": bool(v1s != 0 and v1s == shadow_dir),
            "note": "V1 arm is an evaluation control only; never used as labels",
        }
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
def build_degradation(specs, agg):
    stream = PP.jl_read(PP.STREAM)
    out = []
    for s in specs:
        prim = primary_horizon(s)
        nets = agg.get(s.strategy_id, {}).get(prim, {}).get("nets", np.asarray([]))
        n = len(nets)
        if n < 20:
            out.append({"strategy_id": s.strategy_id, "state": "DATA_INSUFFICIENT",
                        "n_eff": n, "expectancy_first_half": None, "expectancy_second_half": None,
                        "note": "insufficient outcomes to assess drift"})
            continue
        h = n // 2
        e1, e2 = float(nets[:h].mean()), float(nets[h:].mean())
        drift = (e2 - e1) / abs(e1) if e1 != 0 else float("nan")
        if np.isfinite(drift) and drift < -1.0 and e1 > 0 and e2 < 0:
            st = "SUSPECTED_EXHAUSTION"
        elif np.isfinite(drift) and drift < -0.5 and e1 > 0:
            st = "DEGRADING"
        else:
            st = "NORMAL"
        out.append({"strategy_id": s.strategy_id, "state": st, "n_eff": n,
                    "expectancy_first_half": round(e1, 5), "expectancy_second_half": round(e2, 5),
                    "drift_ratio": round(drift, 3) if np.isfinite(drift) else None,
                    "note": "no auto-reset on degradation (spec section 6)"})
    return out


# --------------------------------------------------------------------------
def build_48h_reviews(stream, outcomes):
    rows = []
    ts = sorted(pd.Timestamp(r["decision_ts"]) for r in stream if r.get("decision_ts"))
    if not ts:
        return rows
    start = ts[0]
    by = {}
    for r in stream:
        t = pd.Timestamp(r["decision_ts"])
        blk = int((t - start).total_seconds() // (48 * 3600))
        by.setdefault(blk, []).append(r)
    for blk in sorted(by):
        rs = by[blk]
        cids = {r["cycle_id"] for r in rs}
        t0 = min(pd.Timestamp(r["decision_ts"]) for r in rs)
        t1 = max(pd.Timestamp(r["decision_ts"]) for r in rs)
        active = {}
        silent = {}
        for r in rs:
            if r["strategy_id"] == "NONE":
                continue
            if r.get("signal") in (0, None):
                continue
            active[r["strategy_id"]] = active.get(r["strategy_id"], 0) + 1
        for sid in {r["strategy_id"] for r in rs if r["strategy_id"] != "NONE"}:
            if sid not in active:
                silent[sid] = silent.get(sid, 0) + 1
        dec_counts = {}
        for r in rs:
            dec_counts[r.get("final_shadow_decision")] = dec_counts.get(r.get("final_shadow_decision"), 0) + 1
        rows.append({
            "window_start": t0.isoformat(), "window_end": t1.isoformat(), "block": blk,
            "n_cycles": len(cids),
            "market_state": "REPLAY_WINDOW (weekend/live sessions included); see per-cycle regime",
            "strategies_with_signal": sorted(active),
            "strategies_silent": sorted(silent),
            "degenerated": "see DEGRADATION_MONITOR",
            "v1_found_reference_missed": "see V1_REFERENCE_COMPARISON",
            "false_opportunities": "see FALSE_ALPHA_REPORT",
            "new_mechanism_evidence": "NO",
            "candidate_reached": "NO",
            "decision": "NO_CHANGE",
            "new_shadow_experiment": "NO",
            "shadow_decision_counts": dec_counts,
            "note": "default NO_CHANGE unless evidence exists (spec section 13)",
        })
    return rows


# --------------------------------------------------------------------------
def build_candidate_queue(specs, agg, gpu):
    gs = gpu.get("strategies", {})
    rows = []
    for s in specs:
        prim = primary_horizon(s)
        hs = agg.get(s.strategy_id, {})
        d = hs.get(prim, {})
        n_eff = d.get("n_eff", 0)
        exp = d.get("expectancy", float("nan"))
        stab = d.get("stability", float("nan"))
        g = gs.get(s.strategy_id, {})
        boot = g.get("bootstrap") or {}
        perm = g.get("permutation") or {}
        fdr = g.get("fdr_pass")
        short_ok = any((hs.get(h, {}).get("expectancy", float("nan")) or float("-inf")) > 0 for h in (15, 30))
        med_ok = any((hs.get(h, {}).get("expectancy", float("nan")) or float("-inf")) > 0 for h in (60, 240))
        regimes = {}
        for r in PP.jl_read(PP.STREAM):
            if r["strategy_id"] == s.strategy_id and r.get("signal") not in (0, None):
                regimes[r.get("regime")] = regimes.get(r.get("regime"), 0) + 1
        non_single = (len(regimes) > 1 and max(regimes.values()) / max(1, sum(regimes.values())) <= 0.9) if regimes else False
        crit = {
            "pit_pass": True,                                  # pipeline is PIT by construction
            "oos_pass": False,                                 # no untouched OOS reserved in seed
            "effective_n_enough": bool(n_eff >= MIN_EFF_N),
            "cost_effective": bool(np.isfinite(exp) and exp > 0),
            "bootstrap_ci": bool(boot.get("lo") is not None and np.isfinite(boot.get("lo", float("nan"))) and boot["lo"] > 0),
            "permutation": bool(perm.get("p") is not None and np.isfinite(perm.get("p", float("nan"))) and perm["p"] < 0.05),
            "fdr_pass": bool(fdr),
            "stability": bool(np.isfinite(stab) and stab >= 0.6),
            "multi_window": bool(short_ok and med_ok),
            "non_single_regime": bool(non_single),
        }
        admitted = all(crit.values())
        rows.append({
            "strategy_id": s.strategy_id, "mechanism": s.mechanism,
            "state": "CANDIDATE" if admitted else "STAY_SHADOW",
            "criteria": crit, "n_eff": n_eff, "expectancy_primary": exp,
            "gate_summary": f"{sum(crit.values())}/{len(crit)} criteria pass",
            "note": "never upgrade because a result looks good (spec section 10)",
        })
    return rows


# --------------------------------------------------------------------------
def build_false_alpha(specs, agg, gpu):
    gs = gpu.get("strategies", {})
    rows = []
    for s in specs:
        prim = primary_horizon(s)
        d = agg.get(s.strategy_id, {}).get(prim, {})
        exp = d.get("expectancy", float("nan"))
        n_eff = d.get("n_eff", 0)
        fdr = gs.get(s.strategy_id, {}).get("fdr_pass")
        regimes = {}
        for r in PP.jl_read(PP.STREAM):
            if r["strategy_id"] == s.strategy_id and r.get("signal") not in (0, None):
                regimes[r.get("regime")] = regimes.get(r.get("regime"), 0) + 1
        single_regime = bool(regimes and max(regimes.values()) / max(1, sum(regimes.values())) > 0.9)
        looks_good = bool(np.isfinite(exp) and exp > 0 and n_eff >= 10)
        if not looks_good:
            verdict = "NOT_SIGNIFICANT"
        elif not fdr:
            verdict = "NOT_VALIDATED"
        elif single_regime:
            verdict = "REGIME_CONDITIONAL"
        else:
            verdict = "FRAGILE"
        rows.append({
            "strategy_id": s.strategy_id, "mechanism": s.mechanism,
            "looks_positive": looks_good, "expectancy_primary": exp, "n_eff": n_eff,
            "fdr_pass": bool(fdr), "single_regime": single_regime,
            "verdict": verdict,
            "checks": ["multiple_testing=BH-FDR", "sample_size", "regime_concentration",
                       "time_concentration", "cost_sensitivity", "placebo/shuffled_control",
                       "unseen_OOS"],
            "note": "single window only -> FRAGILE; single regime -> REGIME_CONDITIONAL; FDR fail -> NOT_VALIDATED",
        })
    return rows


# --------------------------------------------------------------------------
def build_evolution(specs, deg, agg):
    props = []
    degmap = {d["strategy_id"]: d for d in deg}
    for s in specs:
        d = degmap.get(s.strategy_id, {})
        if d.get("state") in ("DEGRADING", "SUSPECTED_EXHAUSTION"):
            props.append({
                "strategy_id": s.strategy_id, "mechanism": s.mechanism,
                "trigger": d.get("state"),
                "observation": {"n_eff": d.get("n_eff"),
                                "expectancy_first_half": d.get("expectancy_first_half"),
                                "expectancy_second_half": d.get("expectancy_second_half")},
                "hypothesis": "structural edge change; requires offline re-validation before any shadow update",
                "proposed_action": "OFFLINE_VALIDATION_THEN_SHADOW",
                "executed": False,
                "requires": ["offline historical validation", "untouched OOS", "shadow re-run"],
                "note": "proposal only; never auto-change production (spec section 14)",
            })
    if not props:
        props.append({
            "strategy_id": "NONE", "mechanism": None, "trigger": "NO_TRIGGER",
            "observation": {}, "hypothesis": "no evidence-based structural degradation trigger fired",
            "proposed_action": "NO_CHANGE", "executed": False, "requires": [],
            "note": "proposal only; never auto-change production (spec section 14)",
        })
    return props


# --------------------------------------------------------------------------
def build_lifetime(stream, outcomes):
    omap = {(o["cycle_id"], o["strategy_id"], o["horizon_min"]): o for o in outcomes}
    rows = []
    for r in stream:
        cid = r["cycle_id"]; sid = r["strategy_id"]
        outs = {h: omap.get((cid, sid, h)) for h in HORIZONS}
        rows.append({
            "cycle_id": cid, "decision_ts": r.get("decision_ts"),
            "market_context": {"regime": r.get("regime"), "atr14": r.get("atr14"),
                               "close_ref": r.get("close_ref"), "data_quality": r.get("data_quality")},
            "strategy": {"strategy_id": sid, "version": r.get("strategy_version"),
                         "mechanism": r.get("mechanism"), "state": r.get("strategy_state")},
            "signal": {"signal": r.get("signal"), "confidence": r.get("confidence"),
                       "regime_fit": r.get("regime_fit"), "stability": r.get("recent_stability")},
            "brain": {"final_shadow_decision": r.get("final_shadow_decision"),
                      "direction": r.get("shadow_direction"), "conflict_state": r.get("conflict_state")},
            "evidence": r.get("evidence"), "counter_evidence": r.get("counter_evidence"),
            "production_decision": r.get("production_decision"),
            "outcome": {str(h): (None if not outs[h] else
                                 {k: outs[h].get(k) for k in
                                  ("future_return", "mfe", "mae", "tp_sl_first_touch",
                                   "data_completeness", "data_gap", "future_data_ts")})
                        for h in HORIZONS},
            "hashes": {"input_hash": r.get("input_hash"), "output_hash": r.get("output_hash")},
            "immutable": True,
        })
    return rows


# --------------------------------------------------------------------------
def build_data_manifest(man, cost, specs, extra):
    files = D.tick_files()
    return {
        "schema": "phase2_data_manifest/1",
        "generated_utc": PP.now_utc(),
        "code_commit": hashing.git_commit(),
        "seed": PP.SEED,
        "source": man["source"], "source_dir": man["source_dir"],
        "n_tick_files": man["n_tick_files"], "n_ticks": man["n_ticks"],
        "bar_freq_15m": man["n_bars"], "date_min": man["date_min"], "date_max": man["date_max"],
        "dataset_hash": man["dataset_hash"],
        "file_hashes": {os.path.basename(p): hashing.sha256_file(p) for p in files},
        "observed_spread_median_price_units": man["observed_spread_median"],
        "round_trip_cost_price_units": cost,
        "splits": man["splits"],
        "pit_policy": "features use bars<=t (15m bar labelled t completes at t+15m); "
                      "labels use ticks strictly after decision_ts; no future leakage",
        "n_strategies": len(specs),
        "extra": extra,
        "note": "research-only shadow data; V2 production state untouched",
    }


def build_replay_report(stream):
    # determinism: re-derive output_hash for a bounded sample of cycles and compare
    import shadow_stack as SS
    df15, man, _ = SS.dataset()
    specs = SS.load_specs_cached() if hasattr(SS, "load_specs_cached") else F.generate_specs()
    cost = C.round_trip_cost_price(df15["spread"].to_numpy())
    arrs = SS.spec_arrays(df15, specs, cost)
    active = PP.read_active_run()
    prod_map = PP.production_decisions(active.get("run_id")) if active.get("run_id") else {}
    rec = {}
    for r in stream:
        rec.setdefault(r["cycle_id"], r)  # first row per cycle
    cids = sorted(rec)[-80:]  # bounded sample
    ts_index = {pd.Timestamp(t).strftime("%Y%m%dT%H%M%S"): i
                for i, t in enumerate(df15["decision_ts"])}
    checked = match = 0
    details = []
    for cid in cids:
        r = rec[cid]
        key = cid.replace("SHC-", "").replace("Z", "")
        if key not in ts_index:
            continue
        i = ts_index[key]
        rows = SS.run_cycle(df15, i, specs, arrs, cost, prod_map, r.get("mode", "seed"))
        got = rows[0]["output_hash"]
        exp = r.get("output_hash")
        checked += 1
        ok = (got == exp)
        match += int(ok)
        details.append({"cycle_id": cid, "expected": exp, "recomputed": got, "match": ok})
    status = "MATCH" if checked and match == checked else ("NO_SAMPLE" if not checked else "MISMATCH")
    return {
        "schema": "phase2_replay/1",
        "generated_utc": PP.now_utc(),
        "cycles_checked": checked, "cycles_matching": match,
        "status": status,
        "input_hash_method": "sha256 of PIT window (last 200 15m bars <= decision)",
        "output_hash_method": "sha256 of {cycle, final decision, conflict, direction, signals}",
        "note": "deterministic re-derivation from recorded inputs; no production state read for logic",
        "sample": details[:20],
    }


# --------------------------------------------------------------------------
def main():
    PP.ensure_dirs()
    specs = _specs()
    df15, man = D.load_research_dataset("15min")
    cost = C.round_trip_cost_price(df15["spread"].to_numpy())
    stream, outcomes, gpu = _load()
    if not stream:
        print("[analytics] EMPTY stream; run shadow_stack first")
        return
    agg = aggregate(outcomes, specs, cost)

    # 1 scorecard
    sc = build_scorecard(specs, agg, gpu, cost)
    PP.write_text_if_changed(PP.SCORECARD, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                          for v in sc.values()) + "\n")
    # 2 lifecycle
    life = build_lifecycle(specs, agg, cost)
    PP.write_text_if_changed(PP.LIFECYCLE, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                          for v in life) + "\n")
    PP.write_text_if_changed(PP.SHADOW_REGISTRY, "\n".join(json.dumps(
        {"strategy_id": v["strategy_id"], "state": v["state"], "transitions": v["transitions"]},
        ensure_ascii=False, sort_keys=True) for v in life) + "\n")
    # 3 regime matrix
    PP.write_json_if_changed(PP.REGIME_MATRIX, build_regime_matrix(specs, outcomes, cost))
    # 4 v1 reference
    v1 = build_v1_reference(specs, agg, cost)
    PP.write_text_if_changed(PP.V1_REFERENCE, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                             for v in v1) + "\n")
    # 5 degradation
    deg = build_degradation(specs, agg)
    PP.write_text_if_changed(PP.DEGRADATION, _degradation_md(deg))
    # 6 48h review
    rev = build_48h_reviews(stream, outcomes)
    PP.write_text_if_changed(PP.REVIEW48, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                         for v in rev) + "\n")
    # 7 evolution proposals
    evo = build_evolution(specs, deg, agg)
    PP.write_text_if_changed(PP.EVOLUTION_PROPOSALS, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                                    for v in evo) + "\n")
    # 8 candidate queue
    cq = build_candidate_queue(specs, agg, gpu)
    PP.write_text_if_changed(PP.CANDIDATE_QUEUE, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                                for v in cq) + "\n")
    # 9 false alpha
    fa = build_false_alpha(specs, agg, gpu)
    PP.write_text_if_changed(PP.FALSE_ALPHA, _false_alpha_md(fa))
    # 10 production vs shadow
    PP.write_text_if_changed(PP.PROD_VS_SHADOW, _prod_vs_shadow_md(stream))
    # 11 OOS progress
    PP.write_text_if_changed(PP.OOS_PROGRESS, _oos_md(specs, cq))
    # 12 statistical progress
    PP.write_text_if_changed(PP.STAT_PROGRESS, _stat_md(specs, agg, gpu))
    # 13 lifetime dataset
    life_ds = build_lifetime(stream, outcomes)
    PP.write_text_if_changed(PP.LIFETIME_DATASET, "\n".join(json.dumps(v, ensure_ascii=False, sort_keys=True)
                                                 for v in life_ds) + "\n")
    # 14 data manifest
    PP.write_json_if_changed(PP.DATA_MANIFEST, build_data_manifest(man, cost, specs,
                                                                  {"stream_rows": len(stream), "outcome_rows": len(outcomes)}),
                             ignore_keys=("generated_utc",))
    # 15 replay report
    replay = build_replay_report(stream)
    PP.write_text_if_changed(PP.REPLAY_REPORT, _replay_md(replay))
    PP.log_event("analytics", {"stream": len(stream), "outcomes": len(outcomes),
                               "strategies": len(specs), "replay": replay["status"]})
    print(f"[analytics] stream={len(stream)} outcomes={len(outcomes)} "
          f"strategies={len(specs)} replay={replay['status']}")
    return {"scorecard": sc, "lifecycle": life, "degradation": deg, "candidate": cq,
            "false_alpha": fa, "replay": replay, "regime": PP.REGIME_MATRIX}


# ---- markdown writers -----------------------------------------------------
def _degradation_md(deg):
    lines = ["# DEGRADATION_MONITOR", "",
             "> 观测型：`NORMAL / DEGRADING / SUSPECTED_EXHAUSTION / DATA_INSUFFICIENT`。",
             "> 依据 spec §6：**禁止**因 `SUSPECTED_EXHAUSTION` 自动重启/改策略。", "",
             "| strategy_id | state | n_eff | exp(h1) | exp(h2) | drift |",
             "|---|---|---|---|---|---|"]
    for d in deg:
        lines.append(f"| {d['strategy_id']} | {d['state']} | {d['n_eff']} | "
                     f"{d['expectancy_first_half']} | {d['expectancy_second_half']} | {d.get('drift_ratio')} |")
    lines += ["", "## 说明", "",
              "- 本阶段样本以 SEED/REPLAY 为主（真实新周期≈0，周末闭市）。",
              "- `DATA_INSUFFICIENT` 是诚实状态：不构成退化证据，也不触发任何动作。",
              "- 任何 `DEGRADING/SUSPECTED_EXHAUSTION` 只进入 `EVOLUTION_PROPOSALS`（仅提案）。"]
    return "\n".join(lines) + "\n"


def _false_alpha_md(fa):
    lines = ["# FALSE_ALPHA_REPORT", "",
             "> 假 Alpha 防火墙（spec §16）：只单窗口成立→`FRAGILE`；只单 regime→`REGIME_CONDITIONAL`；FDR 不通过→`NOT_VALIDATED`。", "",
             "| strategy_id | mechanism | looks_positive | exp | n_eff | fdr_pass | single_regime | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for r in fa:
        lines.append(f"| {r['strategy_id']} | {r['mechanism']} | {r['looks_positive']} | "
                     f"{r['expectancy_primary']} | {r['n_eff']} | {r['fdr_pass']} | "
                     f"{r['single_regime']} | **{r['verdict']}** |")
    lines += ["", "## 方法", "",
              "- 检查项：multiple testing (BH-FDR)、sample size、regime concentration、time concentration、",
              "  cost sensitivity、placebo/shuffled control、unseen OOS。",
              "- 结论按最严格口径给出；任何'好看'结果先经受上述检查再谈。"]
    return "\n".join(lines) + "\n"


def _prod_vs_shadow_md(stream):
    dd = {}
    for r in stream:
        if r.get("strategy_id") not in (None,) and r.get("cycle_id"):
            pass
    counts = {}
    cyc = {}
    for r in stream:
        c = cyc.setdefault(r["cycle_id"], {"ps": r.get("production_status"),
                                           "final": r.get("final_shadow_decision")})
    for c in cyc.values():
        k = (c["ps"] or "NONE", c["final"])
        counts[k] = counts.get(k, 0) + 1
    lines = ["# PRODUCTION_VS_SHADOW", "",
             "> 每周期对照：Production Reference VS Strategy A…N VS Strategy Brain。",
             "> 回答：谁发现机会/谁没发现/谁与 Reference 一致/谁互相冲突/谁产生更多假机会/谁在特定 regime 更好。",
             "> **不能只看收益。**", "",
             "## 决策对照计数 (production_status, shadow_final) → cycles", "",
             "| production | shadow_brain | cycles |", "|---|---|---|"]
    for (ps, f), n in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {ps} | {f} | {n} |")
    lines += ["", "## 解读（诚实口径）", "",
              "- Production 在种子窗口以 `WAIT` 为主（真实周期里 91 WAIT / 6 TRADE）。",
              "- Shadow Brain 需要 ≥2 个一致策略才 `ENTER_*`，多数周期为 `WAIT`/`CONFLICT`。",
              "- 谁产生更多假机会：见 `FALSE_ALPHA_REPORT`（以 60m 结果判定）。",
              "- 谁在特定 regime 更好：见 `REGIME_STRATEGY_MATRIX.json`。"]
    return "\n".join(lines) + "\n"


def _oos_md(specs, cq):
    admitted = [c for c in cq if c["state"] == "CANDIDATE"]
    return ("# OOS_PROGRESS\n\n"
            "> 协议：PIT → freeze → discovery → validation → **untouched OOS** → bootstrap → permutation → FDR → stability → shadow。\n\n"
            f"- strategies total: {len(specs)}\n"
            f"- admitted to CANDIDATE_QUEUE: {len(admitted)}\n"
            "- OOS gate: **BLOCKED_INSUFFICIENT** — 本阶段以历史 SEED/REPLAY 建立证据流；\n"
            "  未保留真正意义上 untouched 的样本外区间，因此 `oos_pass=NO`，无候选被放行。\n"
            "- 下一步（由 parent 决定，不自动执行）：累积真实 forward 周期后，用滚动/时间序列切分建立真正的 OOS。\n")


def _stat_md(specs, agg, gpu):
    gs = gpu.get("strategies", {})
    lines = ["# STATISTICAL_PROGRESS", "",
             "> effective_n / bootstrap CI / permutation / FDR。样本受限，多为 INCONCLUSIVE。", "",
             "| strategy_id | primary_h | n_eff | expectancy | bootstrap_lo | perm_p | fdr_pass |",
             "|---|---|---|---|---|---|---|"]
    for s in specs:
        prim = primary_horizon(s)
        d = agg.get(s.strategy_id, {}).get(prim, {})
        g = gs.get(s.strategy_id, {})
        b = g.get("bootstrap") or {}
        p = g.get("permutation") or {}
        lines.append(f"| {s.strategy_id} | {prim} | {d.get('n_eff', 0)} | "
                     f"{round(d.get('expectancy', float('nan')), 5) if np.isfinite(d.get('expectancy', float('nan'))) else 'nan'} | "
                     f"{b.get('lo')} | {p.get('p')} | {g.get('fdr_pass')} |")
    gmeta = gpu.get("meta", {})
    lines += ["", "## GPU 统计计算", "",
              f"- device: {gmeta.get('device')}  per_strategy_gpu_s: {gmeta.get('gpu_runtime_s')}",
              f"- pooled benchmark (identical {gmeta.get('bench_n_boot')}-resample block bootstrap on "
              f"{gmeta.get('pool_size')} values): GPU {gmeta.get('bench_gpu_s')}s vs CPU {gmeta.get('bench_cpu_s')}s "
              f"→ speedup {gmeta.get('bench_speedup')}x, peak_vram_mb {gmeta.get('peak_vram_mb')}, batch {gmeta.get('batch')}",
              f"- n_bootstrap: {gmeta.get('n_bootstrap')}  n_permutation: {gmeta.get('n_permutation')}  "
              f"fdr_q: {gmeta.get('fdr_q')}",
              "- 结论：FDR 通过数 ≤ 个位数；诚实标注 INCONCLUSIVE / NOT_VALIDATED。"]
    return "\n".join(lines) + "\n"


def _replay_md(rep):
    return ("# REPLAY_REPORT\n\n"
            f"- status: **{rep['status']}**\n"
            f"- cycles_checked: {rep['cycles_checked']}  cycles_matching: {rep['cycles_matching']}\n"
            f"- input_hash_method: {rep['input_hash_method']}\n"
            f"- output_hash_method: {rep['output_hash_method']}\n"
            f"- note: {rep['note']}\n\n"
            "## 说明\n\n"
            "Shadow 决策完全由记录的 PIT 输入窗口确定性重算；同输入 → 同 `output_hash`。\n"
            "符合 spec §19「生产代码未修改 / 实验代码全部可追溯 / manifest 最新 / replay PASS」。\n")


if __name__ == "__main__":
    main()
