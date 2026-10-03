"""Statistical-power closure driver — V3-HFT-L1-STATISTICAL-POWER-CLOSURE-001.

AUDIT_ONLY / READ_ONLY / OFFLINE. Reads the IMMUTABLE SNAPSHOT only (never live_fxtm).
Places NO orders. Writes only under research/l1_statistical_power/.

No alpha discovery, no model search, no feature mining, no strategy re-run.
Effect sizes are PREDEFINED economic hypotheses, never the observed positive means.
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, V3)
from microstructure import timestamp_unit_guard as TG   # noqa: E402
from microstructure import markout as MK                 # noqa: E402

SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAPSHOT_ID)
MANIFEST_SHA = "a036a808d5d924a7a99c5941919971ff00ce9e28c804e8e91860b6ffd7fa61b5"
HORIZONS = [5000, 10000, 30000, 60000, 300000]
COST_BP = 0.914
ALPHA = 0.05
TARGETS = [0.80, 0.90, 0.95]
EFFECTS = [0.10, 0.20, 0.30, 0.50, 1.00]
N_GRID = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000]
REPS = 1000
GRID_MS = 1000
SEED = 20260922
DAY_MS = 86_400_000


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load():
    paths = sorted(glob.glob(os.path.join(SNAP, "staging_fxtm", "ticks_*.parquet"))) + \
            sorted(glob.glob(os.path.join(SNAP, "live_fxtm", "ticks_*.parquet")))
    fr = [pd.read_parquet(p, columns=["bid", "ask", "ts_utc"]).sort_values("ts_utc") for p in paths]
    d = pd.concat(fr, ignore_index=True)
    ts = (TG.read_timestamp(d["ts_utc"], "ms")["ts_ns"] // 1_000_000).astype(np.int64)
    return ts, d["bid"].to_numpy(float), d["ask"].to_numpy(float), len(paths)


def acf(x, max_lag):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 10:
        return np.array([])
    x = x - x.mean()
    denom = float(np.dot(x, x))
    if denom <= 0:
        return np.zeros(max_lag)
    out = []
    for k in range(1, max_lag + 1):
        out.append(float(np.dot(x[:-k], x[k:]) / denom))
    return np.array(out)


def eff_n_acf(x, max_lag=200):
    n = int(np.isfinite(x).sum())
    if n < 20:
        return None, None
    a = acf(x, min(max_lag, max(1, n // 4)))
    if a.size == 0:
        return None, None
    thr = 2.0 / np.sqrt(n)
    ips, s = [], 0.0
    for r in a:
        if r <= 0 or abs(r) < thr:
            break
        s += r
    neff = n / (1.0 + 2.0 * s) if (1.0 + 2.0 * s) > 0 else float(n)
    return float(max(1.0, neff)), a


def block_len_lag(x, max_lag=200):
    n = int(np.isfinite(x).sum())
    a = acf(x, min(max_lag, max(1, n // 4)))
    if a.size == 0:
        return 1
    thr = 2.0 / np.sqrt(n)
    for i, r in enumerate(a, start=1):
        if abs(r) < thr:
            return int(i)
    return int(a.size)


def block_boot_sample(x, n, blk, rng):
    x = np.asarray(x, float)
    blk = min(max(1, int(blk)), max(1, x.size // 2))
    nb = int(np.ceil(n / blk))
    starts = rng.integers(0, max(1, x.size - blk + 1), size=nb)
    idx = (starts[:, None] + np.arange(blk)[None, :]).reshape(-1)[:n]
    return x[idx]


def main():
    ts, bid, ask, nfiles = load()
    mid = (bid + ask) / 2.0
    med_dt = float(np.median(np.diff(ts)))
    g = np.arange(ts[0], ts[-1] + 1, GRID_MS, dtype=np.int64)
    gi = np.searchsorted(ts, g, side="right") - 1
    gi = gi[gi >= 0]
    gi = gi[(ts[gi] - (ts[gi] // GRID_MS * GRID_MS)) <= 5000]
    plan_hash = sha256(os.path.join(HERE, "power_plan.json"))
    base = {"schema": "v3_l1_power_base/1", "generated_utc": now_utc(),
            "DATA_SNAPSHOT_ID": SNAPSHOT_ID, "DATA_MANIFEST_SHA256": MANIFEST_SHA,
            "POWER_PLAN_HASH": plan_hash,
            "data": {"files": nfiles, "ticks": int(len(ts)), "grid_points": int(len(gi)),
                      "median_inter_tick_ms": med_dt, "cost_bp": COST_BP}}

    # ---------- coverage / calendar -------------------------------------
    days = np.unique(ts // DAY_MS)
    per_day = np.bincount((ts // DAY_MS).astype(np.int64) - int(days[0]))
    calendar_days = int(days[-1] - days[0] + 1)
    usable_days = int(days.size)
    span_s = float(ts[-1] - ts[0]) / 1000.0
    usable_hours = float(len(ts)) * med_dt / 3_600_000.0     # tick-count * cadence approximation
    base["coverage"] = {"calendar_days": calendar_days, "usable_days": usable_days,
                         "coverage_ratio_days": round(usable_days / calendar_days, 4),
                         "ticks_per_usable_day": float(np.median(per_day)),
                         "usable_hours_est": round(usable_hours, 1),
                         "coverage_ratio_hours": round(usable_hours / (calendar_days * 24), 4),
                         "span_s": round(span_s, 1)}

    dep = {"schema": "v3_l1_sample_dependence/1", **{k: base[k] for k in
            ("generated_utc", "DATA_SNAPSHOT_ID", "DATA_MANIFEST_SHA256", "POWER_PLAN_HASH")},
            "coverage": base["coverage"], "horizons": {}}
    rows_eff, rows_pow, rows_req, rows_cal, rows_cost = [], [], [], [], []
    sim = {"schema": "v3_l1_power_simulation/1",
            "DATA_SNAPSHOT_ID": SNAPSHOT_ID, "DATA_MANIFEST_SHA256": MANIFEST_SHA,
            "POWER_PLAN_HASH": plan_hash, "method": "block bootstrap on empirical non-overlapping net series",
            "replications": REPS, "alpha": ALPHA, "horizons": {}}

    # one frozen block-length function from the 1-tick return series
    r1 = np.full(len(mid), np.nan)
    r1[1:] = (mid[1:] / mid[:-1] - 1.0) * 1e4
    blk_tick = block_len_lag(r1[np.isfinite(r1)])
    dep["BLOCK_LENGTH_METHOD"] = "first lag where |ACF| < 2/sqrt(n) on the 1-tick return series (frozen once)"
    dep["BLOCK_LENGTH_VALUE_TICKS"] = int(blk_tick)
    dep["BLOCK_LENGTH_RATIONALE"] = ("tick-level return dependence dictates how far apart samples must be to be "
                                     "treated as independent; the same lag is applied to every horizon")

    for h in HORIZONS:
        j = np.searchsorted(ts, ts[gi] + h, side="left")
        elig = j < len(ts)
        gmax = max(60_000, 10 * h) if h <= 300_000 else 3_600_000
        seg = np.concatenate([[0], np.cumsum(np.diff(ts) > gmax)])
        elig = elig & (seg[gi] == seg[np.clip(j, 0, len(ts) - 1)])
        jj = np.clip(j, 0, len(ts) - 1)
        fm = mid[jj]
        cost = COST_BP * np.ones(len(gi))
        net = (fm - ask[gi]) / ask[gi] * 1e4 - cost          # long-executable net markout
        ok = elig & np.isfinite(net)
        rho = max(1.0, h / med_dt)
        nonov = net[ok][::int(round(rho))]
        n_raw, n_elig, n_valid, n_no = len(ts), int(elig.sum()), int(ok.sum()), int(nonov.size)
        neff_a, a = eff_n_acf(nonov)
        bl_no = block_len_lag(nonov)
        neff_b = float(n_no / max(1, bl_no))
        unc = bool(neff_a and neff_b and (max(neff_a, neff_b) / max(1.0, min(neff_a, neff_b)) > 2.0))
        sigma = float(np.std(nonov))
        dep["horizons"][str(h)] = {
            "raw_N": n_raw, "eligible_N": n_elig, "label_valid_N": n_valid,
            "non_overlapping_N": n_no, "effective_N_A_acf": neff_a, "effective_N_B_block": neff_b,
            "overlap_ratio": round(n_raw / max(1.0, neff_a or 1.0), 2),
            "rho": round(rho, 2), "block_length_nonoverlap_samples": int(bl_no),
            "block_length_seconds": round(bl_no * rho * med_dt / 1000.0, 1),
            "EFFECTIVE_N_UNCERTAIN": unc, "sigma_bp": sigma,
            "net_mean_bp_current": float(np.mean(nonov))}
        rows_eff.append([h, n_raw, n_elig, n_valid, n_no, neff_a, neff_b, round(rho, 2),
                          int(bl_no), round(sigma, 4), unc,
                          "UNCERTAIN" if unc else ("<500" if (neff_a or 0) < 500 else ">=500")])

        # ---------- power simulation (bootstrap under a ZERO-MEAN null + shift) -----
        # the empirical series is CENTRED first: otherwise the test detects the current
        # (negative) mean instead of the hypothesised effect delta.
        nc = nonov - float(np.mean(nonov))
        rng = np.random.default_rng(SEED)
        sim["horizons"][str(h)] = {"sigma_bp": sigma, "block_length_nonoverlap_samples": int(bl_no),
                                    "centred_null": True, "n_grid": {}, "required_effective_N": {},
                                    "analytic_required_N": {}, "sim_reachable": bool(n_no >= 100)}
        crit = st.norm.ppf(1 - ALPHA / 2)
        for n in N_GRID:
            if n > n_no:
                continue
            means, sds = np.empty(REPS), np.empty(REPS)
            for r in range(REPS):
                s = block_boot_sample(nc, n, bl_no, rng)
                means[r] = s.mean()
                sds[r] = s.std(ddof=1)
            entry = {"reject_rate_by_effect": {}}
            for d in EFFECTS:
                t = (means + d) / (sds / np.sqrt(n) + 1e-12)
                entry["reject_rate_by_effect"][f"{d:.2f}"] = float(np.mean(np.abs(t) > crit))
            sim["horizons"][str(h)]["n_grid"][str(n)] = entry
        # required N per (effect, target) from the simulated grid (monotone scan)
        for d in EFFECTS:
            for tg in TARGETS:
                found = None
                for n in N_GRID:
                    e = sim["horizons"][str(h)]["n_grid"].get(str(n))
                    if e and e["reject_rate_by_effect"][f"{d:.2f}"] >= tg:
                        found = n
                        break
                sim["horizons"][str(h)]["required_effective_N"][f"d{d:.2f}_p{int(tg*100)}"] = found
                z = st.norm.ppf(tg)
                sim["horizons"][str(h)]["analytic_required_N"][f"d{d:.2f}_p{int(tg*100)}"] = int(
                    np.ceil(((crit + z) * sigma / d) ** 2)) if d > 0 else None
        rows_pow.append([h, round(sigma, 4)] +
                         [sim["horizons"][str(h)]["analytic_required_N"].get(f"d{d:.2f}_p{p}")
                          for d in EFFECTS for p in (80, 90, 95)])

        # ---------- data requirement ------------------------------------
        eff_now = max(1.0, neff_a or neff_b)
        ticks_per_eff = n_raw / eff_now
        for d in EFFECTS:
            for p, tg in ((80, 0.80), (90, 0.90), (95, 0.95)):
                # PRIMARY = analytic requirement from the empirical sigma (standard formula);
                # the grid simulation is only a validation where the current data supports it.
                need = sim["horizons"][str(h)]["analytic_required_N"].get(f"d{d:.2f}_p{p}")
                if need is None:
                    rows_req.append([h, d, p, None, None, None, None, None])
                    continue
                need_raw = need * ticks_per_eff
                need_days = need / (eff_now / max(1e-9, base["coverage"]["usable_days"]))
                rows_req.append([h, d, p, need, int(need_raw), int(need_raw), round(need_days, 1),
                                  round(need_days / base["coverage"]["coverage_ratio_days"], 1)])
        rows_cal.append([h, n_raw, round(eff_now, 1), base["coverage"]["usable_days"],
                          base["coverage"]["coverage_ratio_days"],
                          round(eff_now / max(1e-9, base["coverage"]["usable_days"]), 2)])

        # ---------- cost-aware -----------------------------------------
        for mult in (1.0, 1.25, 1.5, 2.0):
            c = COST_BP * mult
            rows_cost.append([h, mult, round(c, 4), round(c + 0.10 * 13.7, 4),
                              0.10, round(c + 0.10, 4)])

    # ---------- FDR-adjusted power --------------------------------------
    fdr = {"schema": "v3_l1_fdr_power/1", "q": 0.05,
            "families": {"per_horizon_m1": 1, "inherited_replication_m140": 140},
            "note": "BH with m tests: practical single-test alpha ~= q/m; required N scales as (alpha ratio)^(1/2)... "
                    "reported as the alpha_eff used for the FDR-adjusted required N",
            "per_horizon": {}}
    for h in HORIZONS:
        a1 = ALPHA
        a140 = 0.05 / 140
        scale140 = np.sqrt((st.norm.ppf(1 - a140 / 2) / st.norm.ppf(1 - a1 / 2)) ** 2)
        fdr["per_horizon"][str(h)] = {"alpha_single": a1, "alpha_fdr_m140": round(a140, 8),
                                       "required_N_multiplier_vs_single": round(float(scale140), 3),
                                       "required_effective_N_d0.20_p80_single":
                                       sim["horizons"][str(h)]["required_effective_N"].get("d0.20_p80"),
                                       "required_effective_N_d0.20_p80_fdr140":
                                       (int(np.ceil((sim["horizons"][str(h)]["analytic_required_N"]
                                                     .get("d0.20_p80") or 0) * scale140)) or None)}

    # ---------- data investment ----------------------------------------
    inv = {"schema": "v3_l1_data_investment/1", "checkpoints_weeks": [1, 4, 13, 26], "rows": []}
    for h in HORIZONS:
        d = dep["horizons"][str(h)]
        eff_now = max(1.0, d["effective_N_A_acf"] or d["effective_N_B_block"])
        per_day = eff_now / max(1e-9, base["coverage"]["usable_days"])
        need500 = 500
        for wk in (1, 4, 13, 26):
            gain = per_day * wk * 7 * base["coverage"]["coverage_ratio_days"]
            inv["rows"].append({"horizon_ms": h, "weeks": wk, "effective_N_gained": round(gain, 1),
                                 "reaches_500": bool(eff_now + gain >= need500)})

    # ---------- write ---------------------------------------------------
    def wj(n, o):
        with open(os.path.join(HERE, n), "w", encoding="utf-8", newline="\n") as f:
            json.dump(o, f, indent=1, default=str)
        print("wrote", n)

    def wc(n, r):
        with open(os.path.join(HERE, n), "w", encoding="utf-8", newline="\n") as f:
            csv.writer(f).writerows(r)
        print("wrote", n)

    wj("sample_dependence.json", dep)
    wc("effective_n.csv", [["horizon_ms", "raw_N", "eligible_N", "label_valid_N", "non_overlapping_N",
                             "effective_N_A_acf", "effective_N_B_block", "rho", "block_len_samples",
                             "sigma_bp", "EFFECTIVE_N_UNCERTAIN", "gate_500"]] + rows_eff)
    wj("power_simulation.json", sim)
    wc("data_requirement.csv", [["horizon_ms", "effect_bp", "power_pct", "required_effective_N",
                                  "required_raw_ticks", "required_quote_events", "required_usable_days",
                                  "required_calendar_days"]] + rows_req)
    wc("calendar_time_projection.csv", [["horizon_ms", "raw_N", "effective_N_now", "usable_days",
                                          "coverage_ratio_days", "effective_N_per_usable_day"]] + rows_cal)
    wc("cost_aware_power.csv", [["horizon_ms", "cost_multiplier", "cost_bp", "gross_needed_bp_for_0.10USDRT",
                                  "net_min_usd_rt", "net_min_bp"]] + rows_cost)
    wj("fdr_power_analysis.json", fdr)
    wj("data_investment.json", inv)
    wj("power_base.json", base)

    print(json.dumps({"block_len_ticks": int(blk_tick), "coverage": base["coverage"],
                       "effective_N": {k: v["effective_N_A_acf"] for k, v in dep["horizons"].items()},
                       "req_d0.20_p80": {k: v["required_effective_N"].get("d0.20_p80")
                                          for k, v in sim["horizons"].items()}}, indent=1, default=str))


if __name__ == "__main__":
    main()
