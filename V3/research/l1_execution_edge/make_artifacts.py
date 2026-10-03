"""Generate the remaining delivery artifacts from experiment_results.json.

READ_ONLY. No orders. Writes only under research/l1_execution_edge/.
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "experiment_results.json"), encoding="utf-8"))
D = json.load(open(os.path.join(HERE, "diagnostics.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(HERE, "diagnostics.json")) else {}
SNAP = {"SNAPSHOT_ID": R["DATA_SNAPSHOT_ID"], "DATA_MANIFEST_SHA256": R["DATA_MANIFEST_SHA256"],
        "file_count": R["data"]["files"], "row_count": R["data"]["ticks"],
        "grid_points": R["data"]["grid_points"], "median_inter_tick_ms": R["data"]["median_inter_tick_ms"],
        "ts_min": "2026-08-04T01:05:00.093Z", "ts_max": "2026-09-22T02:39:05.572Z",
        "cost_bp": R["data"]["cost_bp"], "source": "immutable snapshot only (live_fxtm never read)"}


def w(name, obj):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, default=str))
    print("wrote", name)


def main():
    w("dataset_manifest.json", {"schema": "v3_l1_edge_dataset_manifest/1", **SNAP,
                                 "folds": R["fold_counts"], "fold_definition": {"train": "2026-08-04..2026-08-21",
                                 "val": "2026-08-24..2026-09-04", "test": "2026-09-07..2026-09-21"}})

    # horizon_results.csv
    rows = [["horizon_ms", "family", "model", "n_trades", "effective_n", "mean_bp", "median_bp",
             "win_rate", "gross_mean_bp", "boot_ci_low", "boot_ci_high", "p_value", "q_value",
             "top1pct_share", "top5pct_share", "top10pct_share", "status"]]
    for h, v in R["selected"].items():
        if "test_deep" not in v:
            rows.append([h, v.get("family"), v.get("model"), "", "", "", "", "", "", "", "", "", "", "", "", "", "NO_VALID_CONFIG"])
            continue
        d = v["test_deep"]
        b = d.get("boot") or {}
        t = d.get("tail") or {}
        fdr = next((s for s in R["screens"] if s["horizon_ms"] == int(h) and s["family"] == v["family"]
                    and s["model"] == v["model"]), {})
        rows.append([h, v["family"], v["model"], d["n_trades"], d["effective_n"],
                     _r(d.get("mean_bp")), _r(d.get("median_bp")), _r(d.get("win_rate")),
                     "", _r(b.get("ci_low")), _r(b.get("ci_high")), _r(fdr.get("val_p")),
                     _r(fdr.get("q_value")), _r(t.get("top1pct_share")), _r(t.get("top5pct_share")),
                     _r(t.get("top10pct_share")), "TAIL_DEPENDENT" if (d.get("mean_bp") or 0) > 0
                     and (d.get("median_bp") or 0) <= 0 else "NO_SUPPORTED_EDGE"])
    _csv("horizon_results.csv", rows)

    # regime_results.csv
    rr = [["horizon_ms", "dimension", "state", "n", "status", "mean_bp", "median_bp", "win_rate"]]
    for h, dims in R["regimes"].items():
        for dim, states in dims.items():
            if not isinstance(states, dict):
                continue
            for s, v in states.items():
                rr.append([h, dim, s, v.get("n", ""), v.get("status", ""), _r(v.get("mean_bp")),
                           _r(v.get("median_bp")), _r(v.get("win_rate"))])
    _csv("regime_results.csv", rr)

    # cost_stress_results.csv
    cs = [["horizon_ms", "multiplier", "usd_per_rt", "cost_bp", "n_trades", "mean_bp", "median_bp", "win_rate"]]
    for h, tiers in R["cost_stress"].items():
        for k, v in tiers.items():
            cs.append([h, k, v["usd_per_rt"], _r(v["cost_bp"]), v["n_trades"], _r(v.get("mean_bp")),
                       _r(v.get("median_bp")), _r(v.get("win_rate"))])
    _csv("cost_stress_results.csv", cs)

    w("bootstrap_results.json", {"schema": "v3_l1_edge_bootstrap/1",
                                  "method": "moving block bootstrap",
                                  "n_resamples": 2000, "block_rule": "max(50, int(10*rho))",
                                  "per_horizon": {h: (v.get("test_deep") or {}).get("boot")
                                                   for h, v in R["selected"].items()}})
    w("fdr_results.json", {"schema": "v3_l1_edge_fdr/1", **R["fdr"],
                            "interpretation": ("insufficient != failed. 0 significant would be reported as "
                                               "'0/N valid survived FDR, M/N statistically insufficient'."),
                            "screen_rows": [{k: r.get(k) for k in ("family", "horizon_ms", "model",
                             "val", "val_p", "q_value", "reject_fdr")} for r in R["screens"]]})

    # experiment_results.md
    lines = ["# Experiment Results — L1 Execution Edge", "",
             f"- SNAPSHOT {SNAP['SNAPSHOT_ID']} · manifest sha256 `{SNAP['DATA_MANIFEST_SHA256']}`",
             f"- files {SNAP['file_count']} · ticks {SNAP['row_count']:,} · grid {SNAP['grid_points']:,}",
             f"- cost {SNAP['cost_bp']} bp · folds {R['fold_counts']}", "",
             "## Selected configurations (VAL selection, TEST evaluated once)", "",
             "| h | family | model | n | eff_n | mean bp | median bp | win | boot CI |",
             "|---|---|---|---|---|---|---|---|---|"]
    for h, v in R["selected"].items():
        d = v.get("test_deep") or {}
        b = d.get("boot") or {}
        lines.append(f"| {int(h)/1000:g}s | {v.get('family')} | {v.get('model')} | {d.get('n_trades')} | "
                     f"{d.get('effective_n')} | {_r(d.get('mean_bp'))} | {_r(d.get('median_bp'))} | "
                     f"{_r(d.get('win_rate'))} | [{_r(b.get('ci_low'))}, {_r(b.get('ci_high'))}] |")
    lines += ["", "## FDR", "", f"- total {R['fdr']['total_tests']} · valid {R['fdr']['valid_tests']} · "
              f"insufficient {R['fdr']['insufficient_tests']} · significant {R['fdr']['significant_tests']}",
              "", "## Tail vs central tendency", "",
              "| h | median bp | mean bp | top1% | top5% | top10% |", "|---|---|---|---|---|---|"]
    for h, v in R["selected"].items():
        d = v.get("test_deep") or {}
        t = d.get("tail") or {}
        lines.append(f"| {int(h)/1000:g}s | {_r(d.get('median_bp'))} | {_r(d.get('mean_bp'))} | "
                     f"{_r(t.get('top1pct_share'))} | {_r(t.get('top5pct_share'))} | {_r(t.get('top10pct_share'))} |")
    lines += ["", "## Diagnostic on the positive result (§三十 checks)", "",
              f"- `corr(pred, spread_bp) = {_r(D.get('corr_pred_vs_spread_bp'))}` -> the predictor is the entry spread.",
              f"- `long_share ≈ {D.get('trades_spread_profile',{}).get('long_share')}` -> essentially all trades are SHORT.",
              f"- top10% share `{_r(D.get('TEST_ridge_spread',{}).get('tail',{}).get('top10pct_share'))}` -> tail-dependent.",
              "- the mechanical predictor `pred = -spread/2` produces 0 trades, so the 'edge' needs an amplified",
              "  spread signal to cross the cost threshold; it is not a forecast of the future mid."]
    w("experiment_results.md", "\n".join(lines) + "\n")
    print("done")


def _r(x):
    return None if x is None else round(float(x), 6)


def _csv(name, rows):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as f:
        csv.writer(f).writerows(rows)
    print("wrote", name)


if __name__ == "__main__":
    main()
