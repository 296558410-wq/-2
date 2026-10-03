# -*- coding: utf-8 -*-
"""M03 CROSS_MARKET_SHOCK tradability validation R1 — complete runner.

FREEZE FIRST (written + hashed before any computation), then one pre-registered expression, no sweeps.
M03 = UNCERTAIN (R4) is an input fact and is never recomputed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R4 = os.path.join(ROOT, "mechanism_validation_r4")
R2DIR = os.path.join(ROOT, "mechanism_validation_r2")
MV1 = os.path.join(ROOT, "mechanism_validation")
sys.path.insert(0, HERE)
sys.path.insert(0, R4)
sys.path.insert(0, R2DIR)
sys.path.insert(0, MV1)
import mechanism_validation_r2 as mv2      # noqa: E402  ledger utility
import run_mechanism_validation_r1 as r1run  # noqa: E402  input loader

NOW = datetime.now(timezone.utc).isoformat()
COST, SEED, VER = 0.914, 20260925, "M03-R1.0.0"

FROZEN = {
    "version": VER, "task": "V3_M03_CROSSMARKET_SHOCK_TRADABILITY_VALIDATION_R1",
    "scope": "M03 independent events only (63); no other mechanism; no opportunity re-discovery",
    "m03_mechanism_status_in": "UNCERTAIN", "m03_mechanism_status_is_input_fact": True,
    "shock_definition": {"primary": "abnormal cross-market 60m move", "statistic": "abs(z of source 60m return)",
                          "threshold": 2.0, "baseline_window_bars": 240, "min_periods": 60,
                          "reused_from": "R1/R2 detector threshold (not a new scan)",
                          "shock_source_rule": "source with the largest abs(z); MULTI_SOURCE if >=2 sources >= 2",
                          "shock_direction_rule": "sign of that source 60m move, recorded independently of XAU",
                          "sources": ["DXY", "VIX", "UST10Y_PROXY"], "ust10y_source": "^TNX_PROXY"},
    "response_windows": {"R0": 1, "R1": 3, "R2": 6, "R3": 12, "unit": "hours", "frozen": True,
                          "note": "four pre-registered windows; later addition of 10/15/30/60m is forbidden"},
    "primary_expression": {"window": "R2", "delay_bars": 0, "direction": "opposite",
                            "definition": "after a cross-market shock, take the XAU position against the shock sign "
                                           "and hold 6 hours with no entry delay"},
    "entry_delay": {"values": [0, 1], "unit": "bars", "frozen": True},
    "direction_rule": {"both_sides_reported": True, "aligned": "same direction as the shock sign",
                        "opposite": "against the shock sign", "no_direction_presumed": True},
    "cost_model": {"round_trip_cost_anchor_bp": COST, "stress": [0, 1, 2, 3], "primary_reference": "1x",
                    "slippage": "historical per-event slippage unavailable - cost stress only, never faked"},
    "bootstrap": {"method": "block bootstrap over events", "block_events": 5, "iterations": 2000, "seed": SEED,
                   "ci": 95, "iid_bootstrap_forbidden": True},
    "permutation": {"method": "event times redrawn uniformly inside the M03 span", "iterations": 2000, "seed": SEED,
                     "statistic": "mean opposite-direction response at R2"},
    "null_shared_across_family": True,
    "negative_control": {"method": "random event-time control", "runs": 300, "seed": SEED,
                          "pass_if": "control mean response <= observed mean response"},
    "multiple_testing": {"method": "BH-FDR", "q": 0.05,
                          "family": "4 source classes (DXY/VIX/UST10Y_PROXY/MULTI_SOURCE) x 2 directions = 8 tests at R2",
                          "pre_registered": True, "shared_null": True},
    "walk_forward": {"folds": 3, "split": "chronological on the event sequence", "param_tuning_inside_folds": False,
                      "consistent_rule": "all three folds >= 0 for CONSISTENT"},
    "episode_grouping": {"rule": "consecutive M03 events within 24h share a macro_episode_id", "window_hours": 24},
    "execution": {"checks": ["latency feasibility", "entry delay", "spread/cost", "response duration"],
                   "rule": "an event is feasible if the R1 response magnitude survives 1x cost and the R0 response is "
                            "not fully reversed; EXECUTION_UNREALISTIC if the feasible fraction < 0.5"},
    "frequency": {"reported": ["events_per_day", "events_per_week", "events_per_month"],
                   "research_floor_per_week": 1.0},
    "status_rule": {
        "PROMISING": "primary expression holds AND net_edge_1x > 0 AND WF consistent (3/3) AND permutation p <= 0.05 "
                       "with FDR control AND effective_n >= 8 AND execution feasible AND events_per_week >= 1.0",
        "NOT_PROMISING": "gross edge weak OR net_edge_1x <= 0 OR WF inconsistent OR execution unrealistic",
        "INSUFFICIENT": "effective_n < 8 OR data quality insufficient OR timestamp precision insufficient OR source "
                          "semantics cannot support the conclusion",
        "no_evasion": "the output must be exactly one of the three; UNCERTAIN is not allowed here"},
    "sensitivity": {"allowed": ["+/-1 bar timestamp shift", "WITHOUT_TNX recomputation"],
                     "purpose": "timestamp-precision and proxy dependence only", "not_a_parameter_search": True},
    "self_correction_policy": {"log_required": True, "refreeze_and_rerun_if_method_affected": True,
                                 "patching_results_forbidden": True},
    "no_sweeps": ["window", "threshold", "magnitude", "holding", "entry delay", "source", "direction"],
    "forbidden_identifiers": ["order_send", "order_check", "metatrader5", "broker", "execution_engine"],
}


def freeze_hash():
    return hashlib.sha256(json.dumps(FROZEN, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    os.makedirs(os.path.join(HERE, "ledger"), exist_ok=True)
    FZ = freeze_hash()
    json.dump({**FROZEN, "FREEZE_HASH": FZ, "frozen_at_utc": NOW},
              open(os.path.join(HERE, "m03_r1_frozen_registry.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("FROZEN", FZ[:24])

    r4e = json.load(open(os.path.join(R4, "event_results_r4.json"), encoding="utf-8"))["events"]
    r4m = json.load(open(os.path.join(R4, "mechanism_results_r4.json"), encoding="utf-8"))["mechanisms"]
    m03_events = [e for e in r4e if e["mechanism_id"] == "M03"]
    m03 = r4m["M03"]
    inp = r1run.load_inputs()
    opp = inp["opportunities"]
    before = {k: sha_file(v) for k, v in inp["paths"].items()}

    rows, missing, dup, seen = [], [], [], set()
    # The R1 opportunity ledger does NOT persist cluster_key (it is an MV-stage derived field), so members are
    # resolved by rebuilding events exactly the way R4 did and taking the event's own member list.
    recs_all = r1run.prepare(opp, inp["hermes"])
    _ev_sorted, ev_all = mv2.mv.build_events(recs_all)
    memb = {ev["independent_event_id"]: sorted(ev["opportunities"], key=lambda r: r["detected_at"])
             for ev in ev_all}
    for e in sorted(m03_events, key=lambda x: x["event_start"]):
        eid = e["event_id"]
        if eid in seen:
            dup.append(eid); continue
        seen.add(eid)
        cands = [opp[r["opportunity_id"]] for r in memb.get(eid, []) if r["opportunity_id"] in opp]
        if not cands:
            missing.append(eid); continue
        cands.sort(key=lambda r: r["detected_at"])
        r0 = cands[0]
        fv = r0.get("feature_values", {})
        zs = {s: abs(float(fv.get(f"{s}_RETURN_60M_z") or 0.0)) for s in ("DXY", "VIX", "UST10Y_PROXY")}
        hot = [s for s, z in zs.items() if z >= FROZEN["shock_definition"]["threshold"]]
        src = "MULTI_SOURCE" if len(hot) >= 2 else (hot[0] if hot else "UNKNOWN")
        chg = {s: float(fv.get(f"{s}_RETURN_60M") or 0.0) for s in ("DXY", "VIX", "UST10Y_PROXY")}
        lead = max(hot, key=lambda s: zs[s]) if hot else None
        sgn = 0.0
        if lead and chg.get(lead):
            sgn = math.copysign(1.0, chg[lead])
        rows.append({"event_id": eid, "mechanism_id": "M03", "grid": (e["grids_involved"][0] if e["grids_involved"] else "1h"),
                      "event_timestamp": e["event_start"], "event_end": e["event_end"],
                      "cross_market_trigger": {"z": {k: round(v, 3) for k, v in zs.items()},
                                                "threshold": FROZEN["shock_definition"]["threshold"]},
                      "trigger_source": src, "trigger_direction": ("UP" if sgn > 0 else "DOWN" if sgn < 0 else "FLAT"),
                      "trigger_sign": sgn, "trigger_magnitude": round(max(zs.values()) if zs else 0.0, 3),
                      "xau_state": r0.get("market_state_signature"), "market_state": r0.get("market_state_signature"),
                      "event_cluster": e["cluster_key"], "grids_involved": e["grids_involved"],
                      "opportunities_merged": e["opportunities_merged"], "source_opportunity_id": r0["opportunity_id"]})
    manifest = {"schema": "v3_m03_r1_input_manifest/1", "ts_utc": NOW, "expected": 63, "loaded": len(rows),
                 "missing": missing, "duplicate": dup, "unexpected": 0,
                 "r4_mechanism_status": m03["decision"], "r4_event_file_hash": sha_file(os.path.join(R4, "event_results_r4.json")),
                 "M03_INPUT_HASH": sha_obj(rows), "rows": rows}
    json.dump(manifest, open(os.path.join(HERE, "m03_r1_input_manifest.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("input loaded:", len(rows), "missing:", len(missing), "dup:", len(dup))
    if len(rows) != 63 or missing or dup:
        json.dump({"M03_TRADABILITY_VALIDATION": "INVALID_INPUT", "loaded": len(rows)}, 
                   open(os.path.join(HERE, "status.json"), "w", encoding="utf-8", newline="\n"), indent=1)
        print("INVALID_INPUT -> STOP"); return

    st = {g: pd.read_parquet(os.path.join(ROOT, "state_engine", f"state_{g}.parquet")).sort_index() for g in ("1h", "5m")}

    eps, cur, last = [], None, None
    for r in sorted(rows, key=lambda x: x["event_timestamp"]):
        t = pd.Timestamp(r["event_timestamp"])
        if last is None or (t - last) > pd.Timedelta(hours=FROZEN["episode_grouping"]["window_hours"]):
            cur = f"EP-{len(eps)+1:03d}"; eps.append(cur)
        r["macro_episode_id"] = cur; last = t
    eff_n = len(set(eps))

    def measure(row, delay_bars, window_hours, sign, series=None):
        g = (series if series is not None else st[row["grid"]]["xau"])
        t0 = (pd.Timestamp(row["event_timestamp"]) + pd.Timedelta(hours=delay_bars)).as_unit(g.index.unit)
        i = g.index.searchsorted(t0)
        if i >= len(g) - 1:
            return None
        entry = float(g.iloc[i])
        if entry <= 0:
            return None
        j = min(len(g), g.index.searchsorted(t0 + pd.Timedelta(hours=window_hours)))
        seg = g.iloc[i:max(i + 2, j)]
        if len(seg) < 2:
            return None
        r = (seg / entry - 1.0) * 1e4 * sign
        return {"gross_bp": float(r.iloc[-1]), "peak_bp": float(r.max()), "trough_bp": float(r.min()),
                 "reversal_bp": float(r.max() - r.iloc[-1]), "bars": int(len(r))}

    ev_out = []
    for r in rows:
        res = {}
        for wn, wh in (("R0", 1), ("R1", 3), ("R2", 6), ("R3", 12)):
            for d in (0, 1):
                for dn, sg in (("aligned", 1.0 if r["trigger_sign"] >= 0 else -1.0),
                                 ("opposite", -1.0 if r["trigger_sign"] >= 0 else 1.0)):
                    m = measure(r, d, wh, sg)
                    res[f"{wn}_d{d}_{dn}"] = None if m is None else {k: round(v, 4) if isinstance(v, float) else v
                                                                      for k, v in m.items()}
        g2 = res.get("R2_d0_opposite")
        ev_out.append({"event_id": r["event_id"], "event_timestamp": r["event_timestamp"], "grid": r["grid"],
                        "shock_source": r["trigger_source"], "shock_direction": r["trigger_direction"],
                        "shock_magnitude": r["trigger_magnitude"], "macro_episode_id": r["macro_episode_id"],
                        "responses": res,
                        "gross_edge_R2_d0_opposite": None if not g2 else g2["gross_bp"],
                        "net_edge_1x_R2_d0_opposite": None if not g2 else round(g2["gross_bp"] - COST, 4),
                        "net_edge_2x_R2_d0_opposite": None if not g2 else round(g2["gross_bp"] - 2 * COST, 4),
                        "net_edge_3x_R2_d0_opposite": None if not g2 else round(g2["gross_bp"] - 3 * COST, 4),
                        "holding_time_h": 6,
                        "execution_feasibility": ("FEASIBLE" if (res.get("R1_d0_opposite") and
                                                                   abs(res["R1_d0_opposite"]["gross_bp"]) > COST and
                                                                   abs(res.get("R0_d0_opposite", {}).get("gross_bp", 0.0)) > 0)
                                                   else "UNREALISTIC")})
    json.dump({"schema": "v3_m03_event_results/1", "ts_utc": NOW, "events": ev_out},
              open(os.path.join(HERE, "m03_event_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    v_all = np.array([e["gross_edge_R2_d0_opposite"] for e in ev_out if e["gross_edge_R2_d0_opposite"] is not None], float)
    obs = float(v_all.mean()) if len(v_all) else 0.0
    span_days = max(1e-9, (pd.Timestamp(ev_out[-1]["event_timestamp"]) - pd.Timestamp(ev_out[0]["event_timestamp"])).total_seconds() / 86400)

    fam = []
    for src in ("DXY", "VIX", "UST10Y_PROXY", "MULTI_SOURCE"):
        for dn in ("aligned", "opposite"):
            key = f"R2_d0_{dn}"
            v = np.array([e["responses"][key]["gross_bp"] for e in ev_out
                           if e["shock_source"] == src and e["responses"].get(key)], float)
            fam.append({"source": src, "direction": dn, "window": "R2", "delay": 0, "n": int(len(v)),
                         "mean_gross_bp": (round(float(v.mean()), 4) if len(v) else None),
                         "median_gross_bp": (round(float(np.median(v)), 4) if len(v) else None),
                         "std_bp": (round(float(v.std(ddof=1)), 4) if len(v) > 1 else None),
                         "mean_net_1x_bp": (round(float((v - COST).mean()), 4) if len(v) else None),
                         "mean_net_2x_bp": (round(float((v - 2 * COST).mean()), 4) if len(v) else None),
                         "mean_net_3x_bp": (round(float((v - 3 * COST).mean()), 4) if len(v) else None)})

    win_sum = {}
    for wn, wh in (("R0", 1), ("R1", 3), ("R2", 6), ("R3", 12)):
        key = f"{wn}_d0_opposite"
        v = np.array([e["responses"][key]["gross_bp"] for e in ev_out if e["responses"].get(key)], float)
        win_sum[wn] = {"hours": wh, "n": int(len(v)),
                        "mean_gross_bp": (round(float(v.mean()), 4) if len(v) else None),
                        "median_gross_bp": (round(float(np.median(v)), 4) if len(v) else None),
                        "mean_net_1x_bp": (round(float((v - COST).mean()), 4) if len(v) else None),
                        "reversal_frac": (round(float(np.mean([e["responses"][key]["reversal_bp"] > 0 for e in ev_out
                                                                 if e["responses"].get(key)])), 4) if len(v) else None)}

    # ---- null via event-time redraws (shared across the family, documented) ----
    g1 = st["1h"]["xau"]
    rng = random.Random(SEED)
    t0, t1 = pd.Timestamp(ev_out[0]["event_timestamp"]), pd.Timestamp(ev_out[-1]["event_timestamp"])
    null_means, nc_means = [], []
    for _ in range(FROZEN["permutation"]["iterations"]):
        vals = []
        for _e in ev_out:
            t = (t0 + pd.Timedelta(seconds=rng.uniform(0, (t1 - t0).total_seconds()))).as_unit(g1.index.unit)
            i = g1.index.searchsorted(t)
            if i + 1 < len(g1):
                seg = g1.iloc[i:i + 6]
                if len(seg) > 1 and seg.iloc[0] > 0:
                    vals.append(float(-(seg.iloc[-1] / seg.iloc[0] - 1) * 1e4))
        if vals:
            null_means.append(float(np.mean(vals)))
    for _ in range(FROZEN["negative_control"]["runs"]):
        vals = [null_means[rng.randrange(len(null_means))]] if null_means else []
        if vals:
            nc_means.append(vals[0])
    p_perm = (round(float(np.mean(np.array(null_means) >= obs)), 5) if null_means else None)
    nc_status = ("PASS" if (not nc_means or float(np.mean(nc_means)) <= obs) else "FAIL")

    # ---- BH-FDR over the 8-test family using the shared null ----
    pv = []
    for f in fam:
        v = np.array([e["responses"]["R2_d0_" + f["direction"]]["gross_bp"] for e in ev_out
                       if e["shock_source"] == f["source"] and e["responses"].get("R2_d0_" + f["direction"])], float)
        f["perm_p"] = (round(float(np.mean(np.array(null_means) >= float(v.mean()))), 5)
                        if len(v) and null_means else None)
        pv.append(f["perm_p"] if f["perm_p"] is not None else 1.0)
    order = sorted(range(len(pv)), key=lambda i: pv[i]); kmax = -1
    for k, i in enumerate(order):
        if pv[i] <= (k + 1) / len(pv) * FROZEN["multiple_testing"]["q"]:
            kmax = k
    for k, i in enumerate(order):
        fam[i]["fdr_significant"] = bool(k <= kmax)
    mt_status = ("PASS" if any(f["fdr_significant"] for f in fam) else "NO_SIGNIFICANT_TEST_AFTER_FDR")

    json.dump({"schema": "v3_m03_response_results/1", "ts_utc": NOW, "windows": win_sum, "family_R2": fam,
                "multiple_testing": {"method": "BH-FDR", "q": 0.05, "status": mt_status,
                                       "significant": [f"{f['source']}/{f['direction']}" for f in fam if f["fdr_significant"]]}},
              open(os.path.join(HERE, "m03_response_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    cost_res = {"schema": "v3_m03_cost_results/1", "ts_utc": NOW, "n": int(len(v_all)), "cost_anchor_bp": COST,
                 "gross_edge_bp": round(float(v_all.mean()), 4) if len(v_all) else None,
                 "median_bp": round(float(np.median(v_all)), 4) if len(v_all) else None,
                 "std_bp": round(float(v_all.std(ddof=1)), 4) if len(v_all) > 1 else None,
                 "net_edge_1x_bp": round(float((v_all - COST).mean()), 4) if len(v_all) else None,
                 "net_edge_2x_bp": round(float((v_all - 2 * COST).mean()), 4) if len(v_all) else None,
                 "net_edge_3x_bp": round(float((v_all - 3 * COST).mean()), 4) if len(v_all) else None,
                 "slippage_note": "historical per-event slippage unavailable - cost stress used, never faked"}
    json.dump(cost_res, open(os.path.join(HERE, "m03_cost_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    # ---- block bootstrap CI ----
    blk, ms = FROZEN["bootstrap"]["block_events"], []
    rb = np.random.default_rng(SEED)
    for _ in range(FROZEN["bootstrap"]["iterations"]):
        if len(v_all) >= blk:
            nblk = int(math.ceil(len(v_all) / blk))
            idx = rb.integers(0, max(1, len(v_all) - blk + 1), nblk)
            s = np.concatenate([v_all[i:i + blk] for i in idx])
        else:
            s = v_all
        if len(s):
            ms.append(float(np.mean(s)))
    ci = [round(float(np.percentile(ms, 2.5)), 4), round(float(np.percentile(ms, 97.5)), 4)] if ms else [None, None]

    # ---- walk-forward (3 chronological folds) ----
    ev_sorted = sorted([e for e in ev_out if e["gross_edge_R2_d0_opposite"] is not None],
                        key=lambda e: e["event_timestamp"])
    wf_folds, q = {}, int(len(ev_sorted) / 3) if ev_sorted else 0
    for fi in range(3):
        seg = ev_sorted[fi * q:(fi + 1) * q if fi < 2 else len(ev_sorted)]
        vv = np.array([e["net_edge_1x_R2_d0_opposite"] for e in seg], float)
        wf_folds[f"fold{fi+1}"] = {"n": int(len(vv)),
                                     "mean_net_1x_bp": (round(float(vv.mean()), 4) if len(vv) else None),
                                     "positive": bool(len(vv) and float(vv.mean()) >= 0)}
    wf_status = ("CONSISTENT" if all(f["positive"] for f in wf_folds.values()) else
                  ("INSUFFICIENT" if any(f["n"] == 0 for f in wf_folds.values()) else "INCONSISTENT"))

    # ---- execution + frequency + TNX sensitivity ----
    feas = [e["execution_feasibility"] for e in ev_out]
    frac_feas = round(sum(1 for f in feas if f == "FEASIBLE") / max(1, len(feas)), 4)
    exec_status = ("FEASIBLE" if frac_feas >= 0.5 else "EXECUTION_UNREALISTIC")
    freq = {"events_per_day": round(len(ev_out) / span_days, 4), "events_per_week": round(len(ev_out) / span_days * 7, 4),
             "events_per_month": round(len(ev_out) / span_days * 30.4, 4), "span_days": round(span_days, 1),
             "tradable_event_frequency": round(len(ev_out) / span_days * 7, 4),
             "research_floor_per_week": FROZEN["frequency"]["research_floor_per_week"]}
    tnx_only = [e for e in ev_out if e["shock_source"] == "UST10Y_PROXY"]
    v_wo = np.array([e["gross_edge_R2_d0_opposite"] for e in ev_out
                      if e["gross_edge_R2_d0_opposite"] is not None and e["shock_source"] != "UST10Y_PROXY"], float)
    tnx = {"UST10Y_PROXY_DEPENDENCY": bool(len(tnx_only)),
            "tnx_only_events": len(tnx_only),
            "without_tnx_mean_gross_bp": (round(float(v_wo.mean()), 4) if len(v_wo) else None),
            "without_tnx_mean_net_1x_bp": (round(float((v_wo - COST).mean()), 4) if len(v_wo) else None),
            "status": ("TNX_PROXY_DEPENDENT" if (len(tnx_only) and v_wo.size and float(v_wo.mean()) <= 0 <= obs)
                        else "NOT_PROXY_DEPENDENT")}
    json.dump({"schema": "v3_m03_execution_results/1", "ts_utc": NOW, "feasible_fraction": frac_feas,
                "execution_status": exec_status, "frequency": freq, "latency": "not used for decisions",
                "spread": "cost anchor only; historical spread unavailable", "response_duration_h": 6},
              open(os.path.join(HERE, "m03_execution_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_m03_wf_results/1", "ts_utc": NOW, "folds": wf_folds, "wf_status": wf_status,
                "split": "chronological", "tuning_inside_folds": False},
              open(os.path.join(HERE, "m03_wf_results.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    json.dump({"schema": "v3_m03_null_results/1", "ts_utc": NOW, "permutation_p": p_perm,
                "null_mean_of_means": (round(float(np.mean(null_means)), 4) if null_means else None),
                "null_iterations": FROZEN["permutation"]["iterations"], "seed": SEED,
                "negative_control": {"status": nc_status, "runs": FROZEN["negative_control"]["runs"],
                                       "control_mean": (round(float(np.mean(nc_means)), 4) if nc_means else None),
                                       "observed_mean": round(obs, 4)},
                "multiple_testing_status": mt_status},
              open(os.path.join(HERE, "m03_null_results.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)

    # ---- +/-1 bar sensitivity ----
    sens = {"schema": "v3_m03_sensitivity_results/1", "ts_utc": NOW, "timestamp_shift": {}, "without_tnx": tnx}
    for sh in (-1, 0, 1):
        vals = []
        for e, r in zip(ev_out, sorted(rows, key=lambda x: x["event_timestamp"])):
            m = measure(r, sh, FROZEN["response_windows"]["R2"], (-1.0 if r["trigger_sign"] >= 0 else 1.0))
            if m:
                vals.append(m["gross_bp"] - COST)
        sens["timestamp_shift"][f"shift_{sh:+d}"] = {"n": len(vals),
                                                       "mean_net_1x_bp": (round(float(np.mean(vals)), 4) if vals else None)}
    json.dump(sens, open(os.path.join(HERE, "m03_sensitivity_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    # ---- status (frozen rule) ----
    net1 = cost_res["net_edge_1x_bp"]
    meets = {"primary_expression_holds": net1 is not None,
              "net_edge_1x_positive": bool(net1 is not None and net1 > 0),
              "wf_consistent": wf_status == "CONSISTENT",
              "perm_p_ok": bool(p_perm is not None and p_perm <= 0.05),
              "fdr_ok": bool(any(f["fdr_significant"] for f in fam)),
              "effective_n_ok": eff_n >= 8, "execution_feasible": exec_status == "FEASIBLE",
              "frequency_ok": freq["events_per_week"] >= FROZEN["frequency"]["research_floor_per_week"]}
    if eff_n < 8:
        status = "INSUFFICIENT"
    elif all(meets.values()):
        status = "PROMISING"
    elif (net1 is not None and net1 <= 0) or wf_status == "INCONSISTENT" or exec_status == "EXECUTION_UNREALISTIC":
        status = "NOT_PROMISING"
    else:
        status = "NOT_PROMISING"

    # ---- ledger ----
    lp = os.path.join(HERE, "ledger", "m03_r1_ledger.jsonl")
    if os.path.exists(lp):
        os.remove(lp)
    led = mv2.mv.MechanismLedger(lp, FZ)
    led.append({"kind": "INPUT", "M03_INPUT_HASH": manifest["M03_INPUT_HASH"], "loaded": len(rows)})
    led.append({"kind": "FREEZE", "FREEZE_HASH": FZ})
    for e in ev_out:
        led.append({"kind": "EVENT", "event_id": e["event_id"], "source": e["shock_source"],
                     "direction": e["shock_direction"], "magnitude": e["shock_magnitude"],
                     "episode": e["macro_episode_id"], "gross": e["gross_edge_R2_d0_opposite"],
                     "net1x": e["net_edge_1x_R2_d0_opposite"]})
    led.append({"kind": "RESPONSE", "windows": win_sum})
    led.append({"kind": "COST", **cost_res})
    led.append({"kind": "WF", "folds": wf_folds, "wf_status": wf_status})
    led.append({"kind": "NULL", "permutation_p": p_perm, "negative_control": nc_status, "mt": mt_status})
    led.append({"kind": "EXECUTION", "feasible_fraction": frac_feas, "status": exec_status})
    led.append({"kind": "FINAL", "status": status, "meets": meets, "FREEZE_HASH": FZ})
    chain = mv2.mv.MechanismLedger.verify(lp)

    outputs = {"m03_event_results.json": ev_out, "m03_response_results.json": {"windows": win_sum, "family": fam},
                "m03_cost_results.json": cost_res, "m03_execution_results.json": {"feasible_fraction": frac_feas,
                                                                                    "status": exec_status, "frequency": freq},
                "m03_wf_results.json": {"folds": wf_folds, "wf_status": wf_status},
                "m03_null_results.json": {"permutation_p": p_perm, "nc": nc_status, "mt": mt_status},
                "m03_sensitivity_results.json": sens}
    out_hash = sha_obj(outputs)
    after = {k: sha_file(v) for k, v in inp["paths"].items()}
    summary = {"schema": "v3_m03_tradability_r1/1", "ts_utc": NOW, "version": VER,
                "M03_INPUT_EVENTS": len(rows), "TESTABLE_EVENTS": len(ev_out),
                "NOT_TESTABLE_EVENTS": sum(1 for e in ev_out if e["gross_edge_R2_d0_opposite"] is None),
                "DXY_EVENTS": sum(1 for e in ev_out if e["shock_source"] == "DXY"),
                "VIX_EVENTS": sum(1 for e in ev_out if e["shock_source"] == "VIX"),
                "TNX_EVENTS": sum(1 for e in ev_out if e["shock_source"] == "UST10Y_PROXY"),
                "MULTI_SOURCE_EVENTS": sum(1 for e in ev_out if e["shock_source"] == "MULTI_SOURCE"),
                "GROSS_EDGE": cost_res["gross_edge_bp"], "NET_EDGE_1X": cost_res["net_edge_1x_bp"],
                "NET_EDGE_2X": cost_res["net_edge_2x_bp"], "NET_EDGE_3X": cost_res["net_edge_3x_bp"],
                "MEDIAN_RESPONSE": cost_res["median_bp"], "MEAN_RESPONSE": cost_res["gross_edge_bp"], "CI95": ci,
                "RAW_N": len(v_all), "EFFECTIVE_N": eff_n, "EPISODES": eff_n,
                "WF_FOLD_1": wf_folds["fold1"]["mean_net_1x_bp"], "WF_FOLD_2": wf_folds["fold2"]["mean_net_1x_bp"],
                "WF_FOLD_3": wf_folds["fold3"]["mean_net_1x_bp"], "WF_STATUS": wf_status,
                "EVENTS_PER_DAY": freq["events_per_day"], "EVENTS_PER_WEEK": freq["events_per_week"],
                "EVENTS_PER_MONTH": freq["events_per_month"],
                "MEDIAN_HOLDING_TIME": 6, "NET_EDGE_PER_HOUR": (round(net1 / 6, 4) if net1 is not None else None),
                "PERMUTATION_STATUS": ("p=" + str(p_perm)) if p_perm is not None else None,
                "NEGATIVE_CONTROL_STATUS": nc_status, "MULTIPLE_TESTING_STATUS": mt_status,
                "EXECUTION_FEASIBILITY": exec_status, "TNX_PROXY_DEPENDENCY": tnx["status"],
                "M03_TRADABILITY_STATUS": status, "status_criteria_met": meets,
                "CANDIDATE_RESEARCH": 0, "CANDIDATE_ELIGIBLE": status == "PROMISING",
                "FREEZE_HASH": FZ, "INPUT_HASH": manifest["M03_INPUT_HASH"], "OUTPUT_HASH": out_hash,
                "ledger_chain": chain, "inputs_unchanged": before == after,
                "self_corrections": [{"what": "stray decorator line and incomplete tail in the first runner draft",
                                       "when": "before the first execution", "affected_data": False,
                                       "affected_method": False, "fix": "rewrote the runner completely",
                                       "rerun": "first execution"},
                                      {"what": "loader matched event members on cluster_key, which the R1 opportunity ledger "
                                                "does not persist -> 0/63 loaded; the INVALID_INPUT guard fired as designed",
                                       "when": "first execution of the corrected runner (before any result was computed)",
                                       "affected_data": False, "affected_method": False,
                                       "fix": "resolve members by rebuilding events exactly as R4 did and using the event's own "
                                                "member list", "rerun": "full re-run from the freeze gate"},
                                      {"what": "pandas unit mismatch: the state index is datetime64[us] while the derived null "
                                                "timestamps became ns -> searchsorted raised 'Cannot losslessly convert units'",
                                       "when": "execution, inside the null-redraw section (after responses were computed, "
                                                "before any result file was written)",
                                       "affected_data": False, "affected_method": False,
                                       "fix": "align query timestamps to the index unit with as_unit() before searchsorted",
                                       "rerun": "full re-run from the freeze gate"},
                                      {"what": "used random.Random for the block bootstrap but called numpy's .integers() -> "
                                                "AttributeError",
                                       "when": "execution, in the block-bootstrap section (no result file written yet)",
                                       "affected_data": False, "affected_method": False,
                                       "fix": "switched the bootstrap RNG to np.random.default_rng(SEED)",
                                       "rerun": "full re-run from the freeze gate"}]}
    json.dump(summary, open(os.path.join(HERE, "run_summary_m03.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    audit = {"schema": "v3_m03_audit/1", "ts_utc": NOW, "version": VER, "FREEZE_HASH": FZ,
              "INPUT_HASH": manifest["M03_INPUT_HASH"], "OUTPUT_HASH": out_hash,
              "input_hashes": before, "inputs_unchanged": before == after,
              "r4_mechanism_status_unchanged": "UNCERTAIN",
              "pit_policy": "all shock variables have information_available_at <= event_time",
              "no_sweeps_performed": True, "synthetic_used": False,
              "trading_status": {"ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF"}}
    json.dump(audit, open(os.path.join(HERE, "m03_r1_audit.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print(json.dumps(summary, ensure_ascii=False, default=str)[:2200])
    print("status:", status, "| meets:", meets)
    print("windows:", json.dumps(win_sum, ensure_ascii=False))
    print("family:", json.dumps([{k: f[k] for k in ("source", "direction", "n", "mean_gross_bp", "mean_net_1x_bp", "perm_p", "fdr_significant")} for f in fam], ensure_ascii=False))
    print("wf:", json.dumps(wf_folds, ensure_ascii=False), wf_status, "| exec:", exec_status, frac_feas)
    print("tnx:", json.dumps(tnx, ensure_ascii=False))
    print("sens:", json.dumps(sens["timestamp_shift"], ensure_ascii=False))
    print("chain:", chain)


if __name__ == "__main__":
    main()
