"""Data layer for the Grand Architecture research program.

Reads ONLY the local FXTM tick archive (real observed XAUUSD bid/ask) from
C:\\AIQuant\\data\\live_fxtm\\ticks_*.parquet. Builds PIT-safe bars and a
feature matrix. Nothing here touches production state or MT5.
"""
from __future__ import annotations
import glob
import os
import numpy as np
import pandas as pd

from . import hashing

LIVE_DIR = r"C:\AIQuant\data\live_fxtm"

# Frozen research splits (UTC dates). Discovery is used to DESIGN rules;
# validation to check; OOS is untouched until the final reveal.
SPLITS = {
    "discovery": ("2026-09-07", "2026-09-16"),
    "validation": ("2026-09-17", "2026-09-23"),
    "oos": ("2026-09-24", "2026-10-01"),
}


def tick_files(live_dir: str = LIVE_DIR) -> list[str]:
    return sorted(glob.glob(os.path.join(live_dir, "ticks_*.parquet")))


def dataset_hash(live_dir: str = LIVE_DIR) -> str:
    """Hash of the sorted (filename, sha256) list of source tick files."""
    items = [(os.path.basename(p), hashing.sha256_file(p)) for p in tick_files(live_dir)]
    return hashing.sha256_json(items)


def load_ticks(live_dir: str = LIVE_DIR) -> pd.DataFrame:
    parts = []
    for p in tick_files(live_dir):
        df = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
        parts.append(df)
    allt = pd.concat(parts, ignore_index=True)
    allt["ts_utc"] = pd.to_datetime(allt["ts_utc"], utc=True)
    allt = allt.sort_values("ts_utc").reset_index(drop=True)
    allt["mid"] = (allt["bid"] + allt["ask"]) / 2.0
    allt["spread"] = allt["ask"] - allt["bid"]
    return allt


def build_bars(ticks: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """OHLC + spread bars from ticks, indexed by bar-END UTC time (PIT: a bar is
    only complete after its timestamp)."""
    t = ticks.set_index("ts_utc")
    o = t["mid"].resample(freq).first()
    h = t["mid"].resample(freq).max()
    l = t["mid"].resample(freq).min()
    c = t["mid"].resample(freq).last()
    sp = t["spread"].resample(freq).median()
    n = t["mid"].resample(freq).count()
    bars = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "spread": sp, "nticks": n})
    bars = bars.dropna(subset=["close"]).reset_index()
    bars = bars.rename(columns={"ts_utc": "bar_end_utc"})
    return bars


def feature_matrix(bars: pd.DataFrame) -> pd.DataFrame:
    """PIT-safe features. At row t, every column uses bars <= t only."""
    df = bars.copy()
    c = df["close"].to_numpy(dtype=np.float64)

    def lag(arr, k):
        out = np.full(arr.shape[0], np.nan)
        if k < arr.shape[0]:
            out[k:] = arr[:-k]
        return out

    for w in (5, 20, 60):
        ma = pd.Series(c).rolling(w).mean().to_numpy()
        df[f"ma{w}"] = ma
        df[f"dist_ma{w}"] = (c - ma) / ma
    for w in (5, 10, 20, 40, 60):
        df[f"ret{w}"] = c - lag(c, w)
    for w in (20, 60):
        df[f"vol{w}"] = pd.Series(c - lag(c, 1)).rolling(w).std().to_numpy()
    df["atr14"] = (df["high"] - df["low"]).rolling(14).mean().to_numpy()
    df["range_pos20"] = ((c - df["low"].rolling(20).min()) /
                         (df["high"].rolling(20).max() - df["low"].rolling(20).min())).to_numpy()
    for w in (20, 40):
        df[f"hh{w}"] = df["high"].rolling(w).max().to_numpy()
        df[f"ll{w}"] = df["low"].rolling(w).min().to_numpy()
    # RSI(14) on 1m closes
    delta = pd.Series(c).diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi14"] = (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()
    # volatility expansion / contraction ratio
    df["vol_ratio"] = (df["vol20"] / df["vol60"].replace(0, np.nan)).to_numpy()
    df["trend_strength"] = (df["ma5"] - df["ma20"]) / df["atr14"].replace(0, np.nan)
    df["date"] = pd.to_datetime(df["bar_end_utc"], utc=True).dt.date
    return df


def regime_labels(df: pd.DataFrame) -> np.ndarray:
    """PIT regime classification per bar: TREND/RANGE/BREAKOUT/TRANSITION.

    Rules use only current/past columns (all PIT features).
    """
    n = len(df)
    reg = np.array(["TRANSITION"] * n, dtype=object)
    ts = df["trend_strength"].to_numpy()
    vr = df["vol_ratio"].to_numpy()
    rp = df["range_pos20"].to_numpy()
    for i in range(n):
        if not np.isfinite(ts[i]) or not np.isfinite(vr[i]):
            reg[i] = "TRANSITION"
        elif abs(ts[i]) > 1.0:
            reg[i] = "TREND"
        elif vr[i] > 1.6 and (rp[i] > 0.95 or rp[i] < 0.05):
            reg[i] = "BREAKOUT"
        elif vr[i] < 0.7:
            reg[i] = "RANGE"
        else:
            reg[i] = "TRANSITION"
    return reg


def load_research_dataset(freq: str = "1min") -> tuple[pd.DataFrame, dict]:
    """Load, build bars + features, attach regimes. Returns (df, manifest)."""
    ticks = load_ticks()
    bars = build_bars(ticks, freq)
    df = feature_matrix(bars)
    df["regime"] = regime_labels(df)
    manifest = {
        "source": "local_fxtm_tick_archive",
        "source_dir": LIVE_DIR,
        "n_tick_files": len(tick_files()),
        "n_ticks": int(len(ticks)),
        "bar_freq": freq,
        "n_bars": int(len(df)),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
        "dataset_hash": dataset_hash(),
        "file_hashes": {os.path.basename(p): hashing.sha256_file(p) for p in tick_files()},
        "observed_spread_median": float(ticks["spread"].replace(0, np.nan).median()),
        "splits": SPLITS,
    }
    return df, manifest
