"""Shared evaluation: turn a PIT stance series into discrete TRADE events.

A "trade" is opened on the bar where the stance changes into (or flips to) a
non-zero direction; it is evaluated over the next `horizon` bars. This avoids
counting the same overlapping position thousands of times, giving a meaningful
effective_n (number of discrete trades).
"""
from __future__ import annotations
import numpy as np

from . import metrics, pit, cost as cost_mod


def entry_indices(stance: np.ndarray) -> np.ndarray:
    s = np.asarray(stance, dtype=np.float64)
    prev = np.concatenate([[0.0], s[:-1]])
    changed = s != prev
    opened = (s != 0) & changed
    return np.nonzero(opened)[0]


def trade_table(df, stance: np.ndarray, horizon: int, cost: float) -> dict:
    mid = df["close"].to_numpy(dtype=np.float64)
    n = mid.shape[0]
    idx = entry_indices(stance)
    gross, net, side, t0, t1, mfe, mae = [], [], [], [], [], [], []
    for i in idx:
        if i + horizon >= n:
            continue
        seg = mid[i + 1:i + 1 + horizon] - mid[i]
        sg = np.sign(stance[i])
        g = sg * (mid[i + horizon] - mid[i])
        gross.append(g); net.append(g - cost); side.append(sg)
        t0.append(str(df["bar_end_utc"].iloc[i]))
        t1.append(str(df["bar_end_utc"].iloc[i + horizon]))
        if sg > 0:
            mfe.append(seg.max()); mae.append(-seg.min())
        else:
            mfe.append(-seg.min()); mae.append(seg.max())
    return {
        "n_eff": len(gross),
        "gross": np.asarray(gross), "net": np.asarray(net), "side": np.asarray(side),
        "t0": t0, "t1": t1, "mfe": np.asarray(mfe), "mae": np.asarray(mae),
    }


def summarize(trades: dict) -> dict:
    net = trades["net"]
    if net.size == 0:
        return {"n_eff": 0, "precision": float("nan"), "expectancy": float("nan"),
                "total": float("nan"), "mfe": float("nan"), "mae": float("nan"),
                "stability": float("nan")}
    return {
        "n_eff": int(net.size),
        "precision": float((net > 0).mean()),
        "expectancy": float(net.mean()),
        "total": float(net.sum()),
        "mfe": float(np.nanmean(trades["mfe"])) if trades["mfe"].size else float("nan"),
        "mae": float(np.nanmean(trades["mae"])) if trades["mae"].size else float("nan"),
        "stability": metrics.stability(net, n_blocks=4),
    }


def eval_on_mask(df, stance: np.ndarray, horizon: int, cost: float, mask: np.ndarray) -> dict:
    s = np.where(mask, stance, 0.0)
    return summarize(trade_table(df, s, horizon, cost))


def split_masks(df):
    return pit.time_split(df["bar_end_utc"].astype(str), _splits())


def _splits():
    from . import data as data_mod
    return data_mod.SPLITS
