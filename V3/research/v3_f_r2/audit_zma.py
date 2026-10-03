# -*- coding: utf-8 -*-
"""V3 F2b zma DEFINITION AUDIT (math + synthetic verification + distribution-only check).

This script does NOT compute any forward return, markout, ladder verdict or edge.
It only inspects the DISTRIBUTION of the zma statistic. It does not modify any protocol.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_f_r2/audit_zma.py
"""
from __future__ import annotations
import json, os, sys, math
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
EMPTY_GAP_MS = 60_000
N = 20

# ---------- theory ----------
# D_t = close_t - SMA_n(close)_t = (1/n) * sum_{k=1..n-1} (close_t - close_{t-k})
# for iid increments with per-bar price variance s_p^2:  Cov = min(k,l) s_p^2
# => Var(D) = [ sum_{k,l=1..n-1} min(k,l) / n^2 ] s_p^2 = [(n-1)(2n-1)/(6n)] s_p^2
K_theory = math.sqrt((N - 1) * (2 * N - 1) / (6 * N))
frozen_const = math.sqrt(N)
ratio = frozen_const / K_theory


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


th = {
    "n_bars_ma": N,
    "var_factor_numerator": (N - 1) * (2 * N - 1),
    "var_factor_denominator": 6 * N,
    "var_factor": (N - 1) * (2 * N - 1) / (6 * N),
    "correct_std_constant_K": K_theory,
    "frozen_constant_sqrt_n": frozen_const,
    "scale_error_ratio": ratio,
    "frozen_is_too_wide_by_pct": (ratio - 1) * 100,
    "p_abs_z_ge_2_correct": 2 * (1 - phi(2.0)),
    "frozen_z2_equals_correct_z": 2.0 * ratio,
    "p_abs_z_ge_2_frozen": 2 * (1 - phi(2.0 * ratio)),
}


# ---------- synthetic verification (no market data) ----------
def make_series(r, price0=1000.0):
    close = price0 * np.cumprod(1.0 + r)
    return close


def zmas(close):
    s = pd.Series(close)
    ret1 = s.pct_change()
    sig = ret1.rolling(N, min_periods=N).std().shift(1)
    sma = s.rolling(N, min_periods=N).mean()
    dev = s - sma
    z_frozen = (dev / (s * sig * frozen_const)).to_numpy()
    z_correct = (dev / (s * sig * K_theory)).to_numpy()
    return z_frozen, z_correct


def rate(z, thr=2.0):
    v = z[np.isfinite(z)]
    return float(np.mean(np.abs(v) >= thr)), int(len(v)), int(np.sum(np.abs(v) >= thr))


def synth():
    rng = np.random.default_rng(12345)
    out = {}
    for label, kind in (("gaussian", "g"), ("student_t_df4", "t")):
        n = 200_000
        if kind == "g":
            r = rng.normal(0, 0.0005, n)
        else:
            r = rng.standard_t(4, n) * 0.0005 / math.sqrt(2.0)   # unit-ish scale
        close = make_series(r)
        zf, zc = zmas(close)
        rf = rate(zf); rc = rate(zc)
        out[label] = {
            "n": rf[1],
            "emp_std_frozen": float(np.nanstd(zf[np.isfinite(zf)])),
            "emp_std_correct": float(np.nanstd(zc[np.isfinite(zc)])),
            "emp_ratio_std": float(np.nanstd(zf[np.isfinite(zf)]) / np.nanstd(zc[np.isfinite(zc)])),
            "trigger_rate_frozen_at_2": rf[0], "trigger_n_frozen": rf[2],
            "trigger_rate_correct_at_2": rc[0], "trigger_n_correct": rc[2],
        }
    return out


# ---------- distribution-only check on the frozen snapshot ----------
def load_ticks():
    import glob
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    mid = (df["bid"].to_numpy(np.float64) + df["ask"].to_numpy(np.float64)) / 2.0
    return ts, mid


def real_check():
    ts, mid = load_ticks()
    d = np.diff(ts, prepend=ts[0])
    seg = np.cumsum((d <= 0) | (d > EMPTY_GAP_MS)) - 1
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    g = (b.groupby(["seg", "minute"], sort=True).agg(close=("mid", "last"), close_ts=("ts", "last"))
          .reset_index().sort_values("close_ts").reset_index(drop=True))
    close = g["close"].to_numpy()
    zf = np.full(len(close), np.nan); zc = np.full(len(close), np.nan)
    for s, idx in g.groupby("seg", sort=False).indices.items():
        c = close[idx]
        srs = pd.Series(c)
        ret1 = srs.pct_change()
        sig = ret1.rolling(N, min_periods=N).std().shift(1).to_numpy()
        sma = srs.rolling(N, min_periods=N).mean().to_numpy()
        dev = c - sma
        zf[idx] = dev / (c * sig * frozen_const)
        zc[idx] = dev / (c * sig * K_theory)
    rf = rate(zf); rc = rate(zc)
    return {
        "bars": int(len(close)),
        "segments": int(g["seg"].nunique()),
        "emp_std_frozen": float(np.nanstd(zf)),
        "emp_std_correct": float(np.nanstd(zc)),
        "emp_ratio_std": float(np.nanstd(zf) / np.nanstd(zc)),
        "trigger_rate_frozen_at_2": rf[0], "trigger_n_frozen": rf[2], "valid_frozen": rf[1],
        "trigger_rate_correct_at_2": rc[0], "trigger_n_correct": rc[2], "valid_correct": rc[1],
        "observed_vs_theory_frozen": rf[0] / th["p_abs_z_ge_2_frozen"] if th["p_abs_z_ge_2_frozen"] else None,
    }


def main():
    res = {"schema": "v3_zma_audit/1", "frozen_def": "zma = (close - sma20) / (close * sig20 * sqrt(20))",
           "n": N, "theory": th,
           "synthetic": synth(), "real_distribution_only": real_check(),
           "note": "distribution-only audit: no forward returns, no markouts, no ladder verdicts, no protocol change"}
    out = os.path.join(HERE, "zma_audit.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("=== THEORY ===")
    print(f"  correct std constant K_n = sqrt((n-1)(2n-1)/(6n)) = {K_theory:.6f}")
    print(f"  frozen constant sqrt(n)                          = {frozen_const:.6f}")
    print(f"  ratio (frozen / correct)                         = {ratio:.6f}  -> frozen denominator {th['frozen_is_too_wide_by_pct']:.1f}% too wide")
    print(f"  P(|z|>=2) with the CORRECT normalisation        = {th['p_abs_z_ge_2_correct']*100:.3f}%")
    print(f"  |zma|>=2 on the FROZEN scale == |z| >= {th['frozen_z2_equals_correct_z']:.3f}")
    print(f"  P(|z|>=2) implied by the FROZEN scale           = {th['p_abs_z_ge_2_frozen']*100:.4f}%")
    print()
    print("=== SYNTHETIC (no market data) ===")
    for k, v in res["synthetic"].items():
        print(f"  {k}: n={v['n']} std_frozen={v['emp_std_frozen']:.4f} std_correct={v['emp_std_correct']:.4f} "
              f"ratio={v['emp_ratio_std']:.4f} | rate_frozen={v['trigger_rate_frozen_at_2']*100:.3f}% ({v['trigger_n_frozen']}) "
              f"rate_correct={v['trigger_rate_correct_at_2']*100:.3f}% ({v['trigger_n_correct']})")
    print()
    print("=== REAL SNAPSHOT (distribution only) ===")
    r = res["real_distribution_only"]
    print(f"  bars={r['bars']} segments={r['segments']}")
    print(f"  std_frozen={r['emp_std_frozen']:.4f} std_correct={r['emp_std_correct']:.4f} ratio={r['emp_ratio_std']:.4f}")
    print(f"  trigger @|z|>=2  frozen  = {r['trigger_n_frozen']} / {r['valid_frozen']} = {r['trigger_rate_frozen_at_2']*100:.4f}%")
    print(f"  trigger @|z|>=2  correct = {r['trigger_n_correct']} / {r['valid_correct']} = {r['trigger_rate_correct_at_2']*100:.4f}%")
    print(f"  frozen observed/theory   = {r['observed_vs_theory_frozen']:.2f}x")
    print("wrote", out)


if __name__ == "__main__":
    main()
