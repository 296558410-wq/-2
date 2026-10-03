# -*- coding: utf-8 -*-
"""stats_smoke.py - statistics framework smoke tests.
Bootstrap, block bootstrap, permutation, block permutation, non-overlap sampling,
effective sample size, BH-FDR, placebo/shuffle, walk-forward, seed reproducibility."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_stats.json"


def bootstrap_mean_ci(x: np.ndarray, n_iter: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    idx = rng.integers(0, n, size=(n_iter, n))
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def block_bootstrap_mean(x: np.ndarray, block: int, n_iter: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(x)
    n_blocks = int(np.ceil(n / block))
    out = np.empty(n_iter)
    for i in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        parts = [x[s:s + block] for s in starts]
        sample = np.concatenate(parts)[:n]
        out[i] = sample.mean()
    return out


def block_permutation_stat(x: np.ndarray, y: np.ndarray, block: int, n_iter: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    z = np.concatenate([x, y])
    n = len(z)
    n_blocks = int(np.ceil(n / block))
    obs = abs(x.mean() - y.mean())
    cnt = 0
    for _ in range(n_iter):
        # permute whole series by shuffling block starts (block permutation)
        starts = rng.permutation(np.arange(0, n - block + 1, block)) if n - block + 1 >= block else rng.permutation(np.arange(n))
        perm = np.concatenate([z[s:s + block] for s in starts[:n_blocks]])[:n]
        a, b = perm[: len(x)], perm[len(x):]
        cnt += abs(a.mean() - b.mean()) >= obs
    return cnt / n_iter


def bh_fdr(pvals: np.ndarray, q: float) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    thresholds = np.arange(1, n + 1) / n * q
    below = ranked <= thresholds
    if not below.any():
        return np.zeros(n, dtype=bool)
    k = int(np.max(np.where(below)[0])) + 1
    mask = np.zeros(n, dtype=bool)
    mask[order[:k]] = True
    return mask


def ess_ar1(rho: float, n: int) -> float:
    # effective sample size for AR(1): n*(1-rho)/(1+rho)
    return n * (1 - rho) / (1 + rho)


def main() -> None:
    checks: list[dict] = []
    info: dict = {}
    rng = np.random.default_rng(7)

    def add(name, ok, detail=""):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    import scipy, statsmodels, sklearn, pandas  # noqa
    info["versions"] = {"numpy": np.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__,
                        "statsmodels": statsmodels.__version__, "sklearn": sklearn.__version__}
    add("imports", True, json.dumps(info["versions"]))

    # bootstrap CI
    x = rng.standard_normal(5000)
    lo, hi = bootstrap_mean_ci(x, 2000, seed=1)
    add("bootstrap_ci", lo < 0 < hi, f"ci=[{lo:.4f},{hi:.4f}] contains true 0")

    # block bootstrap reproducibility + finite
    y = rng.standard_normal(2000)
    bb1 = block_bootstrap_mean(y, block=100, n_iter=200, seed=5)
    bb2 = block_bootstrap_mean(y, block=100, n_iter=200, seed=5)
    add("block_bootstrap_repro", np.array_equal(bb1, bb2), f"std={bb1.std():.4f}")

    # permutation test H0
    pv = block_permutation_stat(rng.standard_normal(1000), rng.standard_normal(1000), block=50, n_iter=200, seed=3)
    add("permutation_h0", pv > 0.01, f"p={pv:.3f} under null")

    # block permutation alternative (detect shift)
    pv2 = block_permutation_stat(rng.standard_normal(1000), rng.standard_normal(1000) + 0.5, block=50, n_iter=200, seed=4)
    add("block_perm_alt", pv2 < 0.05, f"p={pv2:.4f} under shift 0.5")

    # non-overlapping sampling
    n_obs = 1000
    blocks = [slice(i, min(i + 100, n_obs)) for i in range(0, n_obs, 100)]
    all_idx = set()
    disjoint = True
    for b in blocks:
        s = set(range(b.start, b.stop))
        if all_idx & s:
            disjoint = False
        all_idx |= s
    add("nonoverlap_sampling", disjoint and len(all_idx) == n_obs, f"{len(blocks)} blocks, coverage {len(all_idx)}/{n_obs}")

    # effective sample size
    e_hi = ess_ar1(0.9, 1000)
    e_lo = ess_ar1(0.0, 1000)
    add("effective_sample_size", e_hi < 200 and e_lo > 950, f"AR(0.9): {e_hi:.0f}, AR(0): {e_lo:.0f}")

    # BH-FDR: all-null control
    pnull = rng.random(1000)
    rej_null = bh_fdr(pnull, 0.05).sum()
    # mixed: 50 real effects
    p = np.concatenate([rng.random(950), rng.random(50) * 1e-4])
    rej_mix = bh_fdr(p, 0.05).sum()
    add("bh_fdr_control", rej_null <= 60, f"null rejections {rej_null}/1000 (<=5% expected)")
    add("bh_fdr_power", rej_mix >= 30, f"mixed rejections {rej_mix}/1000")

    # placebo / shuffle
    labels = np.concatenate([np.zeros(500), np.ones(500)]).astype(int)
    vals = np.concatenate([rng.standard_normal(500), rng.standard_normal(500) + 0.8])
    obs = vals[labels == 1].mean() - vals[labels == 0].mean()
    shuff = []
    for _ in range(200):
        lab2 = rng.permutation(labels)
        shuff.append(vals[lab2 == 1].mean() - vals[lab2 == 0].mean())
    add("placebo_shuffle", obs > np.percentile(shuff, 95), f"obs={obs:.2f} > p95(placebo)={np.percentile(shuff, 95):.2f}")

    # walk-forward: expanding windows no overlap/leak
    n = 2000
    folds = []
    for k in range(5):
        tr_end = 400 + k * 320
        te = slice(tr_end, tr_end + 320)
        folds.append((tr_end, te))
    ok_wf = all(folds[i][1].start >= folds[i][0] for i in range(5)) and all(folds[i][1].stop <= n for i in range(5))
    no_leak = all(folds[i][1].start >= folds[i][0] for i in range(5))
    add("walk_forward", ok_wf and no_leak, "5 expanding folds: train [:1680] before/at test starts (no overlap)")

    # seed reproducibility
    r_a = np.random.default_rng(7); r_b = np.random.default_rng(7)
    a1 = r_a.standard_normal(10); a2 = r_b.standard_normal(10)
    add("seed_repro", np.array_equal(a1, a2), "two default_rng(7) streams identical")

    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"stats_smoke: {status} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
