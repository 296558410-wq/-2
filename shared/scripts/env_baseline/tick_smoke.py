# -*- coding: utf-8 -*-
"""tick_smoke.py - tick research toolchain smoke (synthetic XAUUSD-like ticks).
Builds tick df (ts,bid,ask,side-vols), computes mid/spread/direction/signed flow,
arrival intensity, aggregates tick->1s/5s/10s/1m with strict bucketing
(bucket b contains ONLY ticks with ts in [b, b+delta); no future ticks)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_tick.json"


def synth_ticks(n: int = 60_000, seed: int = 9, base: float = 2000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # 2h window, random arrival
    start = pd.Timestamp("2026-02-03 08:00:00", tz="UTC")
    end = start + pd.Timedelta(hours=2)
    ts = start + pd.to_timedelta(np.sort(rng.uniform(0, (end - start).total_seconds(), n)), unit="s")
    # returns with mild momentum feedback so aggressor side predicts next move (proxy sanity)
    noise = rng.standard_normal(n)
    e = np.empty(n)
    side = np.empty(n)
    prev = 0.0
    for i in range(n):
        e[i] = 0.5 * prev + noise[i]
        prev = 1.0 if e[i] > 0 else -1.0
        side[i] = prev
    mid = base + np.cumsum(e) * 0.02
    spread = np.maximum(0.05, rng.exponential(0.05, n))
    bid = mid - spread / 2
    ask = mid + spread / 2
    bvol = rng.integers(0, 3, n)
    avol = rng.integers(0, 3, n)
    return pd.DataFrame({"ts": ts, "bid": bid, "ask": ask, "bvol": bvol, "avol": avol, "side": side.astype(int)})


def bucket(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate ticks into aligned buckets. Each bucket's values derive only from
    ticks with ts in [bucket_start, bucket_start+delta)."""
    g = df.set_index("ts").groupby(pd.Grouper(freq=rule))
    out = g.agg(mid_first=("mid", "first"), mid_last=("mid", "last"),
                mid_high=("mid", "max"), mid_low=("mid", "min"),
                n_ticks=("mid", "size"), n_buy=("side", lambda s: int((s > 0).sum())),
                n_sell=("side", lambda s: int((s < 0).sum())),
                sum_bvol=("bvol", "sum"), sum_avol=("avol", "sum"),
                spread_mean=("spread", "mean")).dropna()
    out["signed_flow"] = out["sum_bvol"] - out["sum_avol"]
    out["imbalance"] = (out["n_buy"] - out["n_sell"]) / out["n_ticks"].replace(0, np.nan)
    return out


def main() -> None:
    checks: list[dict] = []
    info: dict = {}

    def add(name, ok, detail=""):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    tk = synth_ticks()
    tk["mid"] = (tk["bid"] + tk["ask"]) / 2
    tk["spread"] = tk["ask"] - tk["bid"]
    info["ticks"] = len(tk)
    info["span"] = str(tk["ts"].iloc[-1] - tk["ts"].iloc[0])

    add("tick_fields", {"ts", "bid", "ask", "mid", "spread", "side"}.issubset(tk.columns), f"{len(tk)} ticks")
    add("tick_monotonic", tk["ts"].is_monotonic_increasing and tk["ts"].is_unique, "timestamps sorted & unique")

    # arrival intensity (ticks per second)
    tsec = tk.set_index("ts").resample("1s").size()
    add("arrival_intensity", float(tsec.mean()) > 1.0, f"mean {tsec.mean():.1f} ticks/s, max {tsec.max()}")

    # signed flow & price impact proxy
    imp = tk.assign(ret=tk["mid"].diff().shift(-1)).dropna()
    corr = imp["side"].corr(imp["ret"])
    add("price_impact_proxy", corr > 0.05, f"corr(side, next-mid-ret)={corr:.3f} (buy aggression precedes up-move)")

    # aggregations
    for rule, expect in (("1s", None), ("5s", None), ("10s", None), ("1min", None)):
        b = bucket(tk, rule)
        # strict alignment: every tick inside bucket k must lie in [start, start+delta)
        delta = pd.Timedelta(rule)
        starts = b.index.to_series()
        # verify no future leak: recompute bucket content from ticks only within window
        bad = 0
        for st in starts[:: max(1, len(starts) // 40)]:
            win = tk[(tk["ts"] >= st) & (tk["ts"] < st + delta)]
            if len(win) == 0:
                continue
            if not np.isclose(win["mid"].iloc[-1], b.loc[st, "mid_last"], rtol=1e-9):
                bad += 1
        ok = bad == 0 and len(b) > 0
        add(f"agg_{rule}", ok, f"{len(b)} buckets, sampled window checks bad={bad} (no future-tick contamination)")

    # 1m OHLC sanity
    m1 = bucket(tk, "1min")
    okhl = (m1["mid_high"] >= m1[["mid_first", "mid_last"]].max(axis=1) - 1e-12).all() and (m1["mid_low"] <= m1[["mid_first", "mid_last"]].min(axis=1) + 1e-12).all()
    add("agg_ohlc_sane", bool(okhl), f"high>=max(first,last) & low<=min(first,last) across {len(m1)} 1m buckets")

    # duplicate/boundary: no tick outside bucket span (first/last buckets)
    add("bucket_coverage", float((m1["n_ticks"].sum()) / len(tk)) > 0.99, "all ticks assigned to a bucket")

    # parquet roundtrip (tick toolchain writes parquet)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ticks.parquet"
        tk.set_index("ts").to_parquet(p)
        back = pd.read_parquet(p)
        add("tick_parquet_roundtrip", len(back) == len(tk), f"{len(back)} rows roundtrip")

    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"tick_smoke: {status} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
