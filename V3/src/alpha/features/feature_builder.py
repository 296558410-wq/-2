"""Frozen feature + label builder for V3-HFT-ALPHA-DISCOVERY-001.

Implements exactly the definitions in
alpha/freeze/V3_ALPHA_RESEARCH_FREEZE_001.md (sha256 557bcc3c...).

Causality: every feature at tick i uses only ticks <= i (PIT).
No interpolation, no fabricated fields. L2-only concepts are marked DATA_GAP.
"""
from __future__ import annotations
import numpy as np

REV_CLIP_BP = 1.0          # frozen clip for the limited-reversal family
OFI_WINDOW = 20            # frozen tick window for the OFI proxy
MOM_WINDOWS = (10, 50)     # frozen momentum windows (ticks)
STATE_WINDOW = 50          # frozen spread/vol window (ticks)

FAMILIES = {
    "B0": ["r1_bp", "r2_bp"],
    "B1": ["micro_dev_bp", "micro_dev_norm"],      # DATA_GAP unless sizes exist
    "B2": ["ofi_proxy", "ofi_signed_sum"],
    "B3": ["mom10_bp", "mom50_bp"],
    "B4": ["spread_z50", "vol50_bp"],
    "B5": ["rev10_clip_bp", "rev50_clip_bp"],
    "B6": ["mom10_x_spreadz", "mom10_x_vol"],
}
FAMILY_NAMES = {
    "B0": "lagged_returns_baseline",
    "B1": "microprice_deviation",
    "B2": "order_flow_imbalance",
    "B3": "short_term_momentum",
    "B4": "spread_volatility_state",
    "B5": "limited_reversal",
    "B6": "interaction_minimal",
}


def _roll_mean(x, w):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    out = np.full(len(x), np.nan)
    out[w - 1:] = (cs[w:] - cs[:-w]) / w
    return out


def _roll_std(x, w):
    x = np.nan_to_num(x, nan=0.0)
    m = _roll_mean(x, w)
    m2 = _roll_mean(x * x, w)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def _lag_ret(mid, k):
    r = np.full(len(mid), np.nan)
    r[k:] = mid[k:] / mid[:-k] - 1.0
    return r


def compute_tick_features(ts_ns: np.ndarray, bid: np.ndarray, ask: np.ndarray,
                          bid_vol=None, ask_vol=None) -> dict:
    """All families, causal, vectorized. Returns dict of float64 arrays (+ status flags)."""
    bid = np.asarray(bid, np.float64)
    ask = np.asarray(ask, np.float64)
    ts_ns = np.asarray(ts_ns, np.int64)
    mid = (bid + ask) / 2.0
    spread = ask - bid
    n = len(mid)
    bp = 1e4
    f: dict = {}

    # --- B0 lagged returns
    f["r1_bp"] = _lag_ret(mid, 1) * bp
    f["r2_bp"] = _lag_ret(mid, 2) * bp

    # --- B1 microprice deviation (needs sizes; on this feed they are identically 0)
    if bid_vol is not None and ask_vol is not None:
        bv = np.asarray(bid_vol, np.float64)
        av = np.asarray(ask_vol, np.float64)
        den = bv + av
        micro = np.where(den > 0, (bid * av + ask * bv) / np.where(den > 0, den, 1.0), mid)
        usable = np.any(den > 0) and np.any(bv != av)
        f["_micro_usable"] = bool(usable)
    else:
        micro = mid.copy()
        f["_micro_usable"] = False
    f["micro_dev_bp"] = (micro - mid) * bp          # =0 when sizes absent (documented DATA_GAP)
    f["micro_dev_norm"] = (micro - mid) / np.where(spread > 0, spread, np.nan)

    # --- B2 order-flow imbalance proxy (tick rule on mid changes; no sizes/prints)
    d = np.zeros(n)
    d[1:] = np.sign(mid[1:] - mid[:-1])
    cs = np.concatenate([[0.0], np.cumsum(d)])
    w = OFI_WINDOW
    up = np.full(n, np.nan)
    up[w - 1:] = cs[w:] - cs[:-w]
    f["ofi_signed_sum"] = up
    f["ofi_proxy"] = f["ofi_signed_sum"] / w

    # --- B3 momentum
    for k in MOM_WINDOWS:
        f[f"mom{k}_bp"] = _lag_ret(mid, k) * bp

    # --- B4 spread / volatility state
    mu = _roll_mean(spread, STATE_WINDOW)
    sd = _roll_std(spread, STATE_WINDOW)
    f["spread_z50"] = np.where(sd > 0, (spread - mu) / sd, np.nan)
    f["vol50_bp"] = _roll_std(f["r1_bp"], STATE_WINDOW)

    # --- B5 limited reversal (clipped negative momentum)
    for k in MOM_WINDOWS:
        f[f"rev{k}_clip_bp"] = -np.clip(f[f"mom{k}_bp"], -REV_CLIP_BP, REV_CLIP_BP)

    # --- B6 minimal interaction
    f["mom10_x_spreadz"] = f["mom10_bp"] * f["spread_z50"]
    f["mom10_x_vol"] = f["mom10_bp"] * f["vol50_bp"]
    return f


def make_grid(ts_ns: np.ndarray, step_ms: int) -> np.ndarray:
    """Last-tick-as-of sample indices on a fixed time grid (step_ms)."""
    ts_ns = np.asarray(ts_ns, np.int64)
    g0 = ts_ns[0]
    step = step_ms * 1_000_000
    grid = np.arange(g0, ts_ns[-1] + 1, step, dtype=np.int64)
    idx = np.searchsorted(ts_ns, grid, side="right") - 1
    ok = idx >= 0
    return idx[ok]


def segment_ids(ts_ns: np.ndarray, g_max_ns: int) -> np.ndarray:
    """seg[i]: index of the maximal run containing i with all inter-tick gaps <= g_max_ns."""
    ts_ns = np.asarray(ts_ns, np.int64)
    d = np.diff(ts_ns)
    brk = np.concatenate([[0], np.cumsum(d > g_max_ns)])
    return brk


def forward_labels(ts_ns: np.ndarray, mid: np.ndarray, idx: np.ndarray,
                   h_ms: int, g_max_ns: int):
    """Returns dict with label arrays for the sampled indices."""
    ts_ns = np.asarray(ts_ns, np.int64)
    t0 = ts_ns[idx]
    h_ns = int(h_ms) * 1_000_000
    j = np.searchsorted(ts_ns, t0 + h_ns, side="left")
    defined = j < len(ts_ns)
    jj = np.clip(j, 0, len(ts_ns) - 1)
    seg = segment_ids(ts_ns, g_max_ns)
    same_seg = seg[idx] == seg[jj]
    slack = (ts_ns[jj] - t0 - h_ns) / h_ns
    clean = defined & same_seg & (slack <= 0.5)
    y_gross_bp = np.where(defined, (mid[jj] / mid[idx] - 1.0) * 1e4, np.nan)
    return {
        "fwd_idx": jj, "defined": defined, "same_segment": same_seg,
        "slack": slack, "clean": clean, "y_gross_bp": y_gross_bp,
        "fwd_ts_ns": ts_ns[jj],
    }


def family_matrix(feats: dict, family: str) -> tuple[np.ndarray, list[str]]:
    names = FAMILIES[family]
    X = np.column_stack([np.asarray(feats[c], np.float64) for c in names])
    return X, names
