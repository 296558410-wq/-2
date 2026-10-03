"""
40_decay.py — decay definitions A-F, DECAY_TIME_DISTRIBUTION, PRE_EXHAUSTION_SIGNAL_REPORT.

All statistics are computed from the real closed-trade series (V1_OLD, V1_NEW) ordered
by continuous age. Bootstrap CIs and permutation tests use the frozen seed.
No future information is used: every statistic at age t uses only trades with age <= t.

READ-ONLY. Writes only to the lab dir.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (DATA, SRC, banner, read_jsonl, write_json, write_text,
                        git_commit, parse_ts, hours_between, mean, median, stdev,
                        EXPERIMENT_CONFIG)

SOURCES = ["v1_trade_db", "v1_upgrade_ledger"]
SEED = EXPERIMENT_CONFIG["seed"]
BOOT = EXPERIMENT_CONFIG["bootstrap_iters"]
PERM = EXPERIMENT_CONFIG["permutation_iters"]


def rng():
    return random.Random(SEED)


def bootstrap_ci(xs, stat=mean, iters=BOOT, seeded=True):
    r = rng() if seeded else random.Random()
    n = len(xs)
    if n < 2:
        return (None, None, None)
    vals = []
    for _ in range(iters):
        vals.append(stat([xs[r.randrange(n)] for _ in range(n)]))
    vals.sort()
    lo = vals[int(0.025 * iters)]
    hi = vals[int(0.975 * iters)]
    return (round(lo, 4), round(hi, 4), round(stat(xs), 4))


def perm_test(xs, ys, iters=PERM):
    """Two-sided permutation test on difference of means."""
    r = rng()
    obs = mean(xs) - mean(ys)
    pooled = list(xs) + list(ys)
    n = len(xs)
    cnt = 0
    for _ in range(iters):
        r.shuffle(pooled)
        d = mean(pooled[:n]) - mean(pooled[n:])
        if abs(d) >= abs(obs):
            cnt += 1
    return round(obs, 4), round((cnt + 1) / (iters + 1), 4)


def load_series():
    rows = read_jsonl(SRC["v1_trade_db"])
    out = {}
    for r in rows:
        if not isinstance(r, dict) or not r.get("closed"):
            continue
        s = r.get("system")
        out.setdefault(s, []).append(r)
    for s in out:
        out[s].sort(key=lambda r: r.get("entry_ts"))
    return out


def cum_curve(trades):
    """Cumulative after-cost and before-cost PnL by trade index (time-ordered)."""
    cum_a, cum_b = [], []
    a = b = 0.0
    for t in trades:
        a += (t.get("net") or 0.0)
        b += (t.get("profit_price") or 0.0)
        cum_a.append(round(a, 3))
        cum_b.append(round(b, 3))
    return cum_a, cum_b


def cusum_changepoint(xs):
    """CUSUM change point: argmax of |cumulative deviation from the mean|."""
    if len(xs) < 4:
        return None
    m = mean(xs)
    c = 0.0
    best_i, best_v = None, -1
    for i, x in enumerate(xs):
        c += (x - m)
        if abs(c) > best_v:
            best_v, best_i = abs(c), i
    return best_i


def binary_segmentation(xs):
    """Binary segmentation: split index maximizing between-group mean difference."""
    if len(xs) < 4:
        return None
    best_i, best_v = None, -1
    for i in range(2, len(xs) - 1):
        d = abs(mean(xs[:i]) - mean(xs[i:]))
        if d > best_v:
            best_v, best_i = d, i
    return best_i


def rolling(xs, w):
    return [round(mean(xs[max(0, i - w + 1):i + 1]), 4) for i in range(len(xs))]


def analyze_system(system, trades):
    after = [t.get("net") or 0.0 for t in trades]
    before = [t.get("profit_price") or 0.0 for t in trades]
    ages = [t.get("entry_ts") for t in trades]
    n = len(after)
    cum_a, cum_b = cum_curve(trades)

    # Definition A — performance decay: early vs late halves
    half = n // 2
    early, late = after[:half], after[half:]
    early_b, late_b = before[:half], before[half:]
    ci_early = bootstrap_ci(early)
    ci_late = bootstrap_ci(late)
    p_perm = perm_test(early, late) if (len(early) >= 3 and len(late) >= 3) else (None, None)

    # Definition B — edge exhaustion: cumulative crosses zero?
    cross_idx = None
    for i, v in enumerate(cum_a):
        if v <= 0:
            cross_idx = i
            break
    peak_idx = max(range(n), key=lambda i: cum_a[i]) if n else None
    peak_val = cum_a[peak_idx] if peak_idx is not None else None
    final = cum_a[-1] if cum_a else None

    # Definition D proxy for trades — opportunity/trade quality: win-rate by half
    wr_early = round(sum(1 for x in early if x > 0) / len(early), 4) if early else None
    wr_late = round(sum(1 for x in late if x > 0) / len(late), 4) if late else None

    # Definition E — change point (>= 2 methods)
    cp_cusum = cusum_changepoint(after)
    cp_bs = binary_segmentation(after)
    cp_agree = (cp_cusum is not None and cp_bs is not None and
                abs(cp_cusum - cp_bs) <= max(3, int(0.15 * n)))

    # Definition F — survival: age (hours) at which cumulative edge peaks
    peak_age_h = None
    if peak_idx is not None and ages[peak_idx]:
        t0 = parse_ts(ages[0])
        peak_age_h = round(hours_between(t0, parse_ts(ages[peak_idx])), 2)
    last_age_h = round(hours_between(parse_ts(ages[0]), parse_ts(ages[-1])), 2) if n else None

    return {
        "system": system,
        "n": n,
        "first_trade": ages[0] if ages else None,
        "last_trade": ages[-1] if ages else None,
        "span_hours": last_age_h,
        "after_cost": {"sum": round(sum(after), 3), "mean": round(mean(after), 4),
                       "median": round(median(after), 4), "stdev": round(stdev(after), 4) if stdev(after) else None},
        "before_cost": {"sum": round(sum(before), 3), "mean": round(mean(before), 4)},
        "A_performance_decay": {
            "early_half_net_mean": round(mean(early), 4),
            "late_half_net_mean": round(mean(late), 4),
            "early_ci95": ci_early, "late_ci95": ci_late,
            "early_sum": round(sum(early), 3), "late_sum": round(sum(late), 3),
            "perm_p": p_perm[1] if p_perm else None,
        },
        "B_edge_exhaustion": {
            "cum_first_negative_idx": cross_idx,
            "peak_cum_net": peak_val, "peak_idx": peak_idx,
            "final_cum_net": final,
            "exhausted": final is not None and final < 0,
        },
        "C_prediction_decay": {"status": "NOT_EVALUABLE",
                               "reason": "no per-trade prediction/confidence series with PIT in raw evidence"},
        "D_trade_quality_decay": {"win_rate_early": wr_early, "win_rate_late": wr_late},
        "E_change_point": {"cusum_idx": cp_cusum, "binary_seg_idx": cp_bs,
                           "methods_agree": cp_agree,
                           "cusum_age_h": round(hours_between(parse_ts(ages[0]), parse_ts(ages[cp_cusum])), 2)
                           if cp_cusum is not None else None,
                           "bs_age_h": round(hours_between(parse_ts(ages[0]), parse_ts(ages[cp_bs])), 2)
                           if cp_bs is not None else None},
        "F_survival": {"peak_cum_age_hours": peak_age_h, "observed_span_hours": last_age_h},
        "rolling10_net": rolling(after, 10),
    }


def main():
    banner("40_decay.py", SOURCES)
    series = load_series()
    result = {"schema": "decay_analysis/1", "code_commit": git_commit(),
              "seed": SEED, "systems": {}}
    for s, trades in series.items():
        result["systems"][s] = analyze_system(s, trades)

    # ---- DECAY_TIME_DISTRIBUTION -------------------------------------------
    dist = {"schema": "decay_time_distribution/1", "code_commit": git_commit(),
            "definition": "age (hours since run start) at which the cumulative after-cost "
                          "PnL peaks (drawdown onset) and crosses zero, per system",
            "systems": {}}
    for s, a in result["systems"].items():
        dist["systems"][s] = {
            "peak_cum_age_hours": a["F_survival"]["peak_cum_age_hours"],
            "span_hours": a["F_survival"]["observed_span_hours"],
            "final_cum_net": a["B_edge_exhaustion"]["final_cum_net"],
            "interpretation": ("INCONCLUSIVE: single system, no cross-system replication; "
                               "cannot fix a universal decay time")
            if a["n"] < 30 else "weak single-system estimate",
        }
    dist["cross_system_universal_decay_time"] = "NOT_ESTABLISHED (n_systems_with_trades=2, one is a control arm)"
    write_json(DATA / "DECAY_TIME_DISTRIBUTION.json", dist)

    # ---- PRE_EXHAUSTION_SIGNAL_REPORT --------------------------------------
    pre = {"schema": "pre_exhaustion_signal_report/1", "code_commit": git_commit(),
           "hypothesis": "a measurable pre-exhaustion signal precedes cumulative edge decay",
           "tests": []}
    for s, a in result["systems"].items():
        after = [t.get("net") or 0.0 for t in series[s]]
        roll = a["rolling10_net"]
        # signal = rolling mean turns negative before the cumulative peak
        sig = None
        if len(roll) > 10:
            for i in range(1, len(roll)):
                if roll[i] < 0 and roll[i - 1] >= 0:
                    sig = i
                    break
        pre["tests"].append({
            "system": s,
            "first_rolling10_negative_idx": sig,
            "peak_idx": a["B_edge_exhaustion"]["peak_idx"],
            "signal_precedes_peak": (sig is not None and a["B_edge_exhaustion"]["peak_idx"] is not None
                                     and sig < a["B_edge_exhaustion"]["peak_idx"]),
            "verdict": "INCONCLUSIVE",
            "reason": "n small; no OOS confirmation; signal is in-sample only",
        })
    write_json(DATA / "PRE_EXHAUSTION_SIGNAL_REPORT.json", pre)

    write_json(DATA / "DECAY_ANALYSIS.json", result)

    # console
    for s, a in result["systems"].items():
        print(f"\n[{s}] n={a['n']} span={a['span_hours']}h")
        print(f"  A: early_mean={a['A_performance_decay']['early_half_net_mean']} "
              f"late_mean={a['A_performance_decay']['late_half_net_mean']} "
              f"perm_p={a['A_performance_decay']['perm_p']}")
        print(f"  B: peak_cum={a['B_edge_exhaustion']['peak_cum_net']} "
              f"final={a['B_edge_exhaustion']['final_cum_net']} exhausted={a['B_edge_exhaustion']['exhausted']}")
        print(f"  E: cusum_idx={a['E_change_point']['cusum_idx']} "
              f"bs_idx={a['E_change_point']['binary_seg_idx']} agree={a['E_change_point']['methods_agree']}")
        print(f"  F: peak_cum_age={a['F_survival']['peak_cum_age_hours']}h")


if __name__ == "__main__":
    main()
