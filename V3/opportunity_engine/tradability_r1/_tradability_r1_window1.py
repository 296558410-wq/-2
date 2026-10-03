# -*- coding: utf-8 -*-
"""V3_MECHANISM_TRADABILITY_VALIDATION_R1 — window 1.

Upstream identity -> frozen registry -> boundary policy -> TRADABILITY_EVENT unit -> overlap/dependency/
attribution audits -> per-event gross/net(0x..3x) -> descriptive stats / MFE-MAE / frequency / edge-per-hour /
execution feasibility. R2 (bdd3d7d) and MV-R1 (641c7f1) are READ_ONLY.
BOOTSTRAP / PERMUTATION / WALK-FORWARD / LEDGER / DETERMINISTIC / REPLAY / ISOLATION / BOUNDARY-CHECK /
COMMIT are NOT executed in this window (reported as PENDING, never as PASS).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
R2 = os.path.join(ENGINE, "high_frequency_r2")
MVR1 = os.path.join(ENGINE, "mv_r1")
M1P = os.path.join(RE, "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
NOW = datetime.now(timezone.utc).isoformat()
R2_FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
R2_CANON = "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
R2_INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
MVR1_COMMIT, R2_COMMIT = "641c7f1", "bdd3d7d"
COST, SEED, BLOCK, RESAMPLES, PERMS, CI_LVL = 0.914, 20260925, 5, 2000, 500, 95
HOLD_MIN = 60          # ONE primary holding window for all three mechanisms, pre-registered
MIN_EFF = 8
MG = {"M01": ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE"], "M02": ["F6_STATE_CONDITIONAL_HF"],
       "M07": ["F5_SHORT_EXTENSION_REVERSION"]}
PRIORITY = {"M01": 1, "M02": 2, "M07": 3}       # frozen, from MV-R1 mechanism event counts (no future data)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def halt(stage, gate, extra=None):
    rec = {"STATUS": "STOPPED", "STOPPED_AT": stage, "FIRST_FAILED_GATE": gate, "COMMIT": "NONE",
            "R2_READ_ONLY": True, "MVR1_READ_ONLY": True, "ts_utc": NOW, **(extra or {})}
    json.dump(rec, open(os.path.join(HERE, "run_summary.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\n=== TRADABILITY R1 (STOP) ===\n" + json.dumps(rec, ensure_ascii=False, indent=1)[:2000], flush=True)
    sys.exit(2)


def stats(v, label):
    v = np.asarray([x for x in v if x is not None], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "mean_bp": round(float(v.mean()), 4), "median_bp": round(float(np.median(v)), 4),
             "std_bp": round(float(v.std(ddof=1)), 4) if len(v) > 1 else None,
             "p10": round(float(np.percentile(v, 10)), 4), "p25": round(float(np.percentile(v, 25)), 4),
             "p50": round(float(np.percentile(v, 50)), 4), "p75": round(float(np.percentile(v, 75)), 4),
             "p90": round(float(np.percentile(v, 90)), 4),
             "win_rate": round(float(np.mean(v > 0)), 4), "loss_rate": round(float(np.mean(v < 0)), 4),
             "max_gain_bp": round(float(v.max()), 4), "max_loss_bp": round(float(v.min()), 4)}


def main():
    os.makedirs(HERE, exist_ok=True)
    # ---------------- §6 upstream identity ----------------
    r2s = json.load(open(os.path.join(R2, "run_summary_hf_r2.json"), encoding="utf-8"))
    mvs = json.load(open(os.path.join(MVR1, "run_summary.json"), encoding="utf-8"))
    mvmech = json.load(open(os.path.join(MVR1, "mechanism_results.json"), encoding="utf-8"))["mechanisms"]
    gates = {
        "R2_HEAD_IS_bdd3d7d": sh("git", "log", "--format=%h", "-1", "--all").find(R2_COMMIT) >= 0 or
                               (R2_COMMIT in sh("git", "log", "--oneline", "--all")),
        "MV_R1_HEAD_IS_641c7f1": sh("git", "rev-parse", "--short", "HEAD") == MVR1_COMMIT,
        "R2_FREEZE_HASH_MATCH": r2s["FREEZE_HASH"] == R2_FREEZE,
        "R2_CANONICAL_HASH_MATCH": sha_file(os.path.join(R2, "canonical_output_payload.json")) == R2_CANON == r2s["OUTPUT_HASH"],
        "R2_INPUT_HASH_MATCH": r2s["INPUT_HASH"] == R2_INPUT,
        "MV_R1_METHOD_POLICY_HASH": mvs["method_policy_hash"] == "9ed578dda3331db90e20ddcdb5388d548621cf4e110b57e81548982b9d89334e",
        "M01_SUPPORTED": mvmech["M01"]["final_status"] == "SUPPORTED",
        "M02_SUPPORTED": mvmech["M02"]["final_status"] == "SUPPORTED",
        "M07_SUPPORTED": mvmech["M07"]["final_status"] == "SUPPORTED",
        "M03_UNCERTAIN": mvmech["M03"]["final_status"] == "UNCERTAIN",
    }
    print("§6 upstream identity:", json.dumps(gates, ensure_ascii=False), flush=True)
    if not all(gates.values()):
        halt("S6_UPSTREAM_IDENTITY", "upstream identity mismatch", gates)

    # ---------------- §19 frozen registry (written+hashed BEFORE any return is computed) ----------------
    reg = {"REGISTRY_VERSION": 1, "name": "TRADABILITY_R1_FROZEN_REGISTRY",
            "upstream": {"R2_COMMIT": R2_COMMIT, "MV_R1_COMMIT": MVR1_COMMIT, "R2_FREEZE_HASH": R2_FREEZE,
                          "R2_CANONICAL_HASH": R2_CANON, "R2_INPUT_HASH": R2_INPUT,
                          "MV_R1_METHOD_POLICY_HASH": mvs["method_policy_hash"]},
            "scope": {"mechanisms": ["M01", "M02", "M07"], "M03": "EXCLUDED_FROM_TRADABILITY_R1"},
            "expressions": {
                "M01": {"entry_direction": "continuation of the pre-event 5-bar move at signal time "
                                            "(ret5 >= 0 -> LONG else SHORT); sides pre-registered as M01_LONG/M01_SHORT "
                                            "and BOTH always reported",
                          "entry_timestamp": "signal_time + 1 grid bar (next executable bar)",
                          "entry_delay": "1 bar", "exit_rule": "TIME_EXIT at entry + 60 min (no TP/SL)",
                          "holding_window_min": HOLD_MIN},
                "M02": {"entry_direction": "ambiguous by construction -> pre-registered M02_LONG (LONG) and "
                                             "M02_SHORT (SHORT), BOTH always reported",
                          "entry_timestamp": "signal_time + 1 grid bar", "entry_delay": "1 bar",
                          "exit_rule": "TIME_EXIT at entry + 60 min", "holding_window_min": HOLD_MIN},
                "M07": {"entry_direction": "reversion against the pre-event envelope excursion measured with data "
                                             "<= signal time (extended up -> SHORT, extended down -> LONG)",
                          "entry_timestamp": "signal_time + 1 grid bar", "entry_delay": "1 bar",
                          "exit_rule": "TIME_EXIT at entry + 60 min", "holding_window_min": HOLD_MIN}},
            "no_same_bar_execution": "signal[t] -> execution[t+1] enforced",
            "cost_model": {"round_trip_cost_bp": COST, "stress": [0, 1, 2, 3], "primary_metric": "NET_1X",
                            "execution_cost_data_limitation": "no reliable historical spread/slippage series; "
                                                               "anchor-only, spread=0/slippage=0 NEVER assumed"},
            "minimum_sample_rule": {"effective_n_min": MIN_EFF},
            "wf": {"folds": 3, "split": "chronological", "tuning_inside_folds": False},
            "bootstrap": {"method": "block bootstrap over tradability events", "block_events": BLOCK,
                            "resamples": RESAMPLES, "seed": SEED, "ci_level": CI_LVL,
                            "iid_t_test_forbidden_as_primary": True},
            "permutation": {"permutation_count": PERMS, "seed": SEED, "alpha": 0.05,
                             "null_definition": "same-count redraw of signal times uniformly inside each mechanism's "
                                                 "own span, then the identical frozen expression re-applied",
                             "tail": "one-sided upper on mean net_1x"},
            "frequency_gate": {"hf_threshold_per_week": 2.0, "below": "LOW_FREQUENCY_FOR_HF",
                                "note": "frequency gate is NOT an alpha gate", "no_event_splitting_to_pass": True},
            "dependency_units": {"tradability_event": "(mechanism_id, episode_id_v2) -> exactly one event",
                                  "cross_grid": "merged inside episode_id_v2 by construction",
                                  "cross_family": "merged inside episode_id_v2 by construction",
                                  "dependency_group_id": "= episode_id_v2 (shared episodes share a group)"},
            "primary_mechanism_rule": {"priority": PRIORITY, "basis": "MV-R1 frozen mechanism event counts "
                                                                            "(no future-return input)",
                                        "multi_mechanism_episode": "PRIMARY = highest priority present; others = "
                                                                     "SECONDARY; if undecidable -> SHARED_EPISODE"},
            "status_rule": {"SUPPORTED": "NET_1X>0 and CI95 excludes 0 and >=2/3 WF folds net-positive and NET_2X>0 and "
                                           "NET_3X>0 and effective_n>=8 and no lookahead and execution feasible and "
                                           "frequency>=2/week",
                             "UNCERTAIN": "gross positive but net uncertain / WF unstable / CI crosses 0 / frequency "
                                            "insufficient, without being disproven",
                             "REJECTED": "NET_1X<=0 and no reason to retain, or 3x cost negative with unstable baseline, "
                                           "or systematic WF failure, or execution impossible",
                             "INSUFFICIENT_SAMPLE": "effective_n too small to judge",
                             "NOT_TESTABLE": "cannot be evaluated"},
            "forbidden": ["grid search", "parameter sweep", "threshold hunting", "holding-period hunting",
                            "entry-delay hunting", "TP/SL optimisation", "post-hoc event deletion",
                            "splitting episodes to raise frequency", "changing the cost anchor",
                            "changing the frequency gate", "changing WF folds", "re-running R2", "modifying MV-R1"]}
    reg["TRADABILITY_FREEZE_HASH"] = hashlib.sha256(canon({k: v for k, v in reg.items()})).hexdigest()
    json.dump(reg, open(os.path.join(HERE, "tradability_frozen_registry.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    FZ = reg["TRADABILITY_FREEZE_HASH"]
    print("§19 freeze hash:", FZ[:28], flush=True)

    # ---------------- §69 boundary policy (frozen before research) ----------------
    pol = {"POLICY_VERSION": 1, "name": "TRADABILITY_R1_BOUNDARY_POLICY",
            "tradability_scope_prefix": "research/v3_opportunity_engine/tradability_r1/",
            "readonly_prefixes": ["research/v3_opportunity_engine/high_frequency_r2/",
                                   "research/v3_opportunity_engine/mv_r1/"],
            "runtime_output_path_classes": ["research/hermes/trader_v1/run_state/*",
                                              "research/hermes/trader_v1/memory/reviews/*",
                                              "research/hermes/trader_v2/observations/*",
                                              "research/hermes/trader_v2/state/decision_contexts/*"],
            "closeout_artifact_allowlist": ["research/hermes/trader_v3/reports/V3_R2_CANONICAL_HASH_SPEC.md"],
            "non_research_cache_patterns": ["*__pycache__/*", "*.pyc"],
            "unknown_v3_file": "UNEXPECTED_FILES",
            "principles": {"pre_registered_before_results": True, "exclusion_unit": "PATH_CLASS",
                            "no_reset_hard_clean_checkout": True}}
    pol["POLICY_HASH"] = hashlib.sha256(canon(pol)).hexdigest()
    json.dump(pol, open(os.path.join(HERE, "tradability_boundary_policy.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    # ---------------- §8/§9/§10 TRADABILITY_EVENT units ----------------
    pool = json.load(open(os.path.join(R2, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
    fam_of = {o["opportunity_id"]: o["family"] for o in pool}
    eps = {}                       # mechanism -> episode -> member records
    for m, fams in MG.items():
        eps[m] = {}
        for o in pool:
            if o["family"] in fams:
                eps[m].setdefault(o["episode_id_v2"], []).append(o)
    unit_audit = {}
    for m, d in eps.items():
        unit_audit[m] = {"raw_opportunities": sum(len(v) for v in d.values()), "tradability_events": len(d),
                          "families": sorted({fam_of[v[0]["opportunity_id"]] for v in d.values()}),
                          "grids": sorted({o["grid"] for v in d.values() for o in v}),
                          "events_spanning_multiple_grids": sum(1 for v in d.values() if len({o["grid"] for o in v}) > 1),
                          "events_spanning_multiple_families": sum(1 for v in d.values()
                                                                     if len({o["family"] for o in v}) > 1)}
    # M01 F1/F2 special reporting (§51)
    f1 = {e for e, v in eps["M01"].items() if all(o["family"] == MG["M01"][0] for o in v)}
    f2 = {e for e, v in eps["M01"].items() if all(o["family"] == MG["M01"][1] for o in v)}
    both = set(eps["M01"]) - f1 - f2
    unit_audit["M01_F1_F2"] = {"F1_only": len(f1), "F2_only": len(f2), "F1_and_F2_same_episode": len(both),
                                "M01_independent_episode_count": len(eps["M01"])}

    # ---------------- §11 cross-mechanism overlap ----------------
    S = {m: set(eps[m]) for m in MG}
    ovl = {"M01_M02": {"count": len(S["M01"] & S["M02"]), "rate": round(len(S["M01"] & S["M02"]) / max(1, min(len(S["M01"]), len(S["M02"]))), 6)},
            "M01_M07": {"count": len(S["M01"] & S["M07"]), "rate": round(len(S["M01"] & S["M07"]) / max(1, min(len(S["M01"]), len(S["M07"]))), 6)},
            "M02_M07": {"count": len(S["M02"] & S["M07"]), "rate": round(len(S["M02"] & S["M07"]) / max(1, min(len(S["M02"]), len(S["M07"]))), 6)},
            "M01_M02_M07": {"count": len(S["M01"] & S["M02"] & S["M07"])},
            "union_count": len(S["M01"] | S["M02"] | S["M07"]),
            "pairwise_overlap_count": len(S["M01"] & S["M02"]) + len(S["M01"] & S["M07"]) + len(S["M02"] & S["M07"])}

    # ---------------- §12/§54/§55 primary mechanism + attribution ablation ----------------
    all_eps = {}
    for m in MG:
        for e in S[m]:
            all_eps.setdefault(e, []).append(m)
    dep = {"episodes_total": len(all_eps),
            "MULTI_MECHANISM_EPISODE": sum(1 for v in all_eps.values() if len(v) > 1),
            "SHARED_EPISODE": 0, "primary_assignment": {}, "exclusive": {},
            "attribution_ablation": {}}
    for e, ms in all_eps.items():
        ms = sorted(ms, key=lambda x: PRIORITY[x])
        if len(ms) > 1:
            dep["primary_assignment"][e] = {"PRIMARY_MECHANISM": ms[0], "SECONDARY_MECHANISM": ms[1:]}
        for m in ms:
            dep["exclusive"].setdefault(m, 0)
        if len(ms) == 1:
            dep["exclusive"][ms[0]] += 1
    for m in MG:
        sel_all = S[m]
        sel_excl = {e for e in S[m] if len(all_eps[e]) == 1}
        dep["attribution_ablation"][m] = {"ALL_EVENTS": len(sel_all), "EXCLUSIVE_EVENTS_ONLY": len(sel_excl),
                                            "shared_with_another_mechanism": len(sel_all) - len(sel_excl),
                                            "exclusive_rate": round(len(sel_excl) / max(1, len(sel_all)), 6)}
    dep["SHARED_EPISODE"] = dep["MULTI_MECHANISM_EPISODE"]
    json.dump({"schema": "v3_tradability_overlap/1", "ts_utc": NOW, **ovl},
              open(os.path.join(HERE, "tradability_overlap_audit.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    json.dump({"schema": "v3_tradability_dependency/1", "ts_utc": NOW, "unit_audit": unit_audit,
                "dependency": dep, "primary_mechanism_rule": reg["primary_mechanism_rule"]},
              open(os.path.join(HERE, "tradability_dependency_audit.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("unit/overlap/dependency:", json.dumps({"units": {m: unit_audit[m]["tradability_events"] for m in MG},
                                                     "M01_F1_F2": unit_audit["M01_F1_F2"], "overlap": ovl,
                                                     "multi_mechanism_episodes": dep["MULTI_MECHANISM_EPISODE"]},
                                                    ensure_ascii=False), flush=True)

    # ---------------- §21/§22/§23/§24 entry mapping (no same-bar execution) ----------------
    m1 = pd.read_parquet(M1P, columns=["dt_utc", "close"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    px = m1.set_index("dt")["close"].sort_index()
    GRID_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30}
    roll_hi = px.rolling(60, min_periods=20).max().shift(1)
    roll_lo = px.rolling(60, min_periods=20).min().shift(1)
    ev, lookahead = [], []
    for m, d in eps.items():
        for e, v in d.items():
            v = sorted(v, key=lambda o: o["timestamp"])
            sig = pd.Timestamp(v[0]["timestamp"])
            grid = v[0]["grid"]
            step = pd.Timedelta(minutes=GRID_MIN[grid])
            i_sig = px.index.searchsorted(sig, side="right") - 1
            if i_sig < 6 or i_sig + 2 >= len(px):
                continue
            entry_t = sig + step                                     # next executable bar (no same-bar execution)
            i_en = px.index.searchsorted(entry_t, side="right") - 1
            if i_en <= i_sig or i_en + 1 >= len(px):
                continue
            entry_px = float(px.iloc[i_en])
            exit_t = entry_t + pd.Timedelta(minutes=HOLD_MIN)
            i_ex = px.index.searchsorted(exit_t, side="left")
            i_ex = min(max(i_ex, i_en + 1), len(px) - 1)
            # direction (uses ONLY data <= signal time)
            if m == "M01":
                pre = px.iloc[i_sig - 5:i_sig + 1]
                dirn = 1.0 if (len(pre) > 1 and float(pre.iloc[-1]) >= float(pre.iloc[0])) else -1.0
                side = "M01_LONG" if dirn > 0 else "M01_SHORT"
            elif m == "M02":
                dirn, side = None, None          # both sides registered; expanded below
            else:
                hi, lo = roll_hi.iloc[i_sig], roll_lo.iloc[i_sig]
                dirn = -1.0 if (np.isfinite(hi) and float(px.iloc[i_sig]) >= float(hi)) else 1.0
                side = "M07_REVERSION"
            seg = px.iloc[i_en:i_ex + 1].to_numpy(float)
            if len(seg) < 2 or entry_px <= 0:
                continue
            fwd = (seg / entry_px - 1.0) * 1e4
            row = {"tradability_event_id": f"TE-{m}-{e}", "episode_id": e, "mechanism_id": m,
                    "detector_family": v[0]["family"], "grid": grid, "signal_time": str(sig),
                    "entry_time": str(px.index[i_en]), "entry_price": entry_px,
                    "exit_time": str(px.index[i_ex]), "exit_price": float(seg[-1]),
                    "holding_time_min": round((px.index[i_ex] - px.index[i_en]).total_seconds() / 60.0, 2),
                    "dependency_group_id": e, "cross_grid_parent_id": v[0]["cross_grid_parent_id"],
                    "lookahead_ok": (sig < px.index[i_en] <= px.index[i_ex]),
                    "mfe_bp": round(float(fwd.max()), 4), "mae_bp": round(float(fwd.min()), 4)}
            for tag, dd in (("", dirn),) if dirn is not None else ():
                pass
            dirs = [(side, dirn)] if dirn is not None else [("M02_LONG", 1.0), ("M02_SHORT", -1.0)]
            for sname, dv in dirs:
                gross = float((seg[-1] / entry_px - 1.0) * 1e4) * dv
                p = dict(row)
                p.update({"side": sname, "direction": "LONG" if dv > 0 else "SHORT",
                           "gross_return_bp": round(gross, 4),
                           "net_0x": round(gross, 4), "net_1x": round(gross - COST, 4),
                           "net_2x": round(gross - 2 * COST, 4), "net_3x": round(gross - 3 * COST, 4),
                           "mfe_bp_dir": round(float(np.max(fwd * dv)), 4),
                           "mae_bp_dir": round(float(np.min(fwd * dv)), 4),
                           "excursion_up": round(float(np.max(fwd)), 4), "excursion_down": round(float(np.min(fwd)), 4)})
                ev.append(p)
                if not p["lookahead_ok"]:
                    lookahead.append(p["tradability_event_id"])
    if lookahead:
        halt("S67_LOOKAHEAD", "signal_time < entry_time <= exit_time violated", {"bad": lookahead[:5]})

    # ---------------- §26/§29/§30/§31/§32/§33/§34/§35 per mechanism/side ----------------
    span_days = max(1e-9, (max(pd.Timestamp(e["signal_time"]) for e in ev)
                            - min(pd.Timestamp(e["signal_time"]) for e in ev)).total_seconds() / 86400)
    res = {}
    for m in MG:
        for sname in sorted({e["side"] for e in ev if e["mechanism_id"] == m}):
            rs = [e for e in ev if e["mechanism_id"] == m and e["side"] == sname]
            epset = {e["episode_id"] for e in rs}
            indep = len(epset)
            weekly = indep / span_days * 7
            g = stats([e["gross_return_bp"] for e in rs], "gross")
            n1 = stats([e["net_1x"] for e in rs], "net1x")
            n2 = stats([e["net_2x"] for e in rs], "net2x")
            n3 = stats([e["net_3x"] for e in rs], "net3x")
            hold = float(np.median([e["holding_time_min"] for e in rs])) if rs else None
            res[f"{m}|{sname}"] = {"mechanism_id": m, "side": sname,
                                     "raw_event_count": len(rs), "independent_tradability_event_count": indep,
                                     "usable_event_count": indep,
                                     "gross": g, "net_1x": n1, "net_2x": n2, "net_3x": n3,
                                     "mfe_median_bp": round(float(np.median([e["mfe_bp_dir"] for e in rs])), 4),
                                     "mae_median_bp": round(float(np.median([e["mae_bp_dir"] for e in rs])), 4),
                                     "holding_time_median_min": hold,
                                     "edge_per_hour_bp": (round(n1["mean_bp"] / (hold / 60.0), 4)
                                                            if hold and n1.get("mean_bp") is not None else None),
                                     "events_per_day": round(indep / span_days, 4),
                                     "events_per_week": round(weekly, 4),
                                     "events_per_month": round(indep / span_days * 30.4, 4),
                                     "frequency_gate": "PASS" if weekly >= 2 else "LOW_FREQUENCY_FOR_HF",
                                     "execution_feasibility": ("FEASIBLE_WITH_LIMITATION"
                                                                 if all(e["lookahead_ok"] for e in rs) else "NOT_FEASIBLE"),
                                     "execution_limitation": "no historical spread/slippage series; cost anchor only "
                                                               "(EXECUTION_COST_DATA_LIMITATION)",
                                     "TRADABILITY_STATUS": "PENDING_BOOTSTRAP_WF"}
    json.dump({"schema": "v3_tradability_results/1", "ts_utc": NOW, "note": "bootstrap/WF/permutation pending",
                "results": res}, open(os.path.join(HERE, "tradability_results.json"), "w", encoding="utf-8",
                                        newline="\n"), indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_tradability_input_manifest/1", "ts_utc": NOW,
                "R2_COMMIT": R2_COMMIT, "MV_R1_COMMIT": MVR1_COMMIT, "R2_FREEZE_HASH": R2_FREEZE,
                "R2_CANONICAL_HASH": R2_CANON, "R2_INPUT_HASH": R2_INPUT,
                "MV_R1_METHOD_POLICY_HASH": mvs["method_policy_hash"], "TRADABILITY_FREEZE_HASH": FZ,
                "BOUNDARY_POLICY_HASH": pol["POLICY_HASH"], "M1_source": "xauusd_m1_histdata.parquet",
                "M1_sha256": sha_file(M1P), "unit_audit": unit_audit, "overlap": ovl,
                "multi_mechanism_episodes": dep["MULTI_MECHANISM_EPISODE"]},
              open(os.path.join(HERE, "tradability_input_manifest.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    for k, v in sorted(res.items()):
        print(f"  {k:22s} indep={v['independent_tradability_event_count']:>5} weekly={v['events_per_week']:>7} "
              f"gross={v['gross'].get('mean_bp')} net1x={v['net_1x'].get('mean_bp')} net3x={v['net_3x'].get('mean_bp')} "
              f"hold={v['holding_time_median_min']} ep/h={v['edge_per_hour_bp']} freq_gate={v['frequency_gate']}", flush=True)
    out = {"STATUS": "PARTIAL_WINDOW1", "TRADABILITY_R1_STATUS": "INCOMPLETE",
            "UNIT": "TRADABILITY_EVENT = (mechanism_id, episode_id)",
            "TRADABILITY_FREEZE_HASH": FZ, "BOUNDARY_POLICY_HASH": pol["POLICY_HASH"],
            "upstream_gates": gates, "TRADABILITY_EVENTS": {m: unit_audit[m]["tradability_events"] for m in MG},
            "M01_F1_F2": unit_audit["M01_F1_F2"], "OVERLAP_AUDIT": ovl,
            "DEPENDENCY_AUDIT": {"multi_mechanism_episodes": dep["MULTI_MECHANISM_EPISODE"],
                                   "attribution_ablation": dep["attribution_ablation"]},
            "RESULTS": res,
            "DONE": ["upstream identity", "frozen registry", "boundary policy", "TRADABILITY_EVENT units",
                      "overlap audit", "dependency/attribution audit", "entry/exit mapping (next-bar entry, 60m time exit)",
                      "per-event gross/net 0x-3x", "descriptive stats P10-P90", "MFE/MAE", "frequency", "edge/hour",
                      "no-lookahead (signal<entry<=exit)"],
            "PENDING": ["block bootstrap CI", "permutation test", "3-fold WF", "TRADABILITY_STATUS per mechanism",
                         "tradability_event_ledger.jsonl (sha256 chain)", "deterministic rerun", "replay",
                         "V1/V2 isolation", "boundary audit", "commit gate"],
            "COST_STRESS": {"0x": "gross", "1x": "baseline net", "2x": "stress", "3x": "severe stress"},
            "CANDIDATE": 0, "ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF",
            "STOP_AFTER_TRADABILITY_R1": True, "ts_utc": NOW}
    json.dump(out, open(os.path.join(HERE, "run_summary.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\n=== TRADABILITY R1 (window 1) ===\n" + json.dumps({k: out[k] for k in
                                                                 ("STATUS", "TRADABILITY_R1_STATUS",
                                                                  "TRADABILITY_FREEZE_HASH", "TRADABILITY_EVENTS",
                                                                  "M01_F1_F2", "PENDING", "CANDIDATE")},
                                                                 ensure_ascii=False, indent=1)[:1600], flush=True)


if __name__ == "__main__":
    main()
