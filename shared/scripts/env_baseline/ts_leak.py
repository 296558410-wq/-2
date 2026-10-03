# -*- coding: utf-8 -*-
"""ts_leak.py - time-series research capability + point-in-time / leakage tests.
rolling, expanding, resample, asof, merge_asof, groupby, timezone/DST/UTC.
Leak checks: (1) point-in-time recompute, (2) multi-timeframe M1-vs-H1 asof must
not use an incomplete higher-TF bar (bar_end/complete_at <= decision_time rule)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_ts_leak.json"


def detect_future_use(df: pd.DataFrame, col: str, decision_times: pd.DatetimeIndex, formula) -> list[str]:
    """Formula-based detector: recompute the feature FORMULA on rows <= t and compare
    with the stored feature value at t. A precomputed column that depends on future
    rows cannot be reproduced from the past-only window -> flagged."""
    problems = []
    for t in decision_times:
        pos = df.index.get_indexer([t], method="pad")[0]
        if pos < 0:
            continue
        past = df.iloc[: pos + 1]
        try:
            recomputed = float(formula(past))
        except Exception:
            recomputed = float("nan")
        stored = float(df[col].iloc[pos])
        if not np.isclose(recomputed, stored, equal_nan=True, rtol=1e-9, atol=1e-12):
            problems.append(str(t))
    return problems


def main() -> None:
    checks: list[dict] = []
    info: dict = {}
    rng = np.random.default_rng(11)

    def add(name, ok, detail=""):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # ---- tz / DST / UTC ----
    naive = pd.date_range("2026-03-08 00:00", "2026-03-08 06:00", freq="30min", tz=None)
    utc = naive.tz_localize("UTC")
    ny = utc.tz_convert("America/New_York")
    add("tz_convert_dst", ny.is_monotonic_increasing and len(ny) == len(utc) and utc[0].tzname() == "UTC",
        f"NY span {ny[0]}..{ny[-1]} crosses 2026-03-08 DST jump")
    norm = utc.normalize()
    add("utc_normalize", str(norm.tz) == "UTC" and bool((norm.hour == 0).all()), "UTC normalize -> all midnights, tz preserved")
    add("tz_roundtrip", ny.tz_convert("UTC").equals(utc), "NY->UTC roundtrip identical")

    # ---- rolling / expanding / resample / groupby / asof / merge_asof ----
    idx = pd.date_range("2026-01-01", periods=4000, freq="1min", tz="UTC")
    close = 100 + np.cumsum(rng.standard_normal(4000) * 0.05)
    df = pd.DataFrame({"close": close}, index=idx)
    df["rmean5"] = df["close"].rolling(5).mean()
    df["emax"] = df["close"].expanding().max()
    h = df["close"].resample("1h").agg(["last", "count"])
    gb = df.assign(g=(df.index.hour // 4).astype(int)).groupby("g")["close"].mean()
    q = df.asof(pd.Timestamp("2026-01-02 00:00:30", tz="UTC"))
    right = df.rename_axis("time").reset_index()
    m = pd.merge_asof(pd.DataFrame({"time": [pd.Timestamp("2026-01-01 00:00:01", tz="UTC")]}),
                      right, on="time", direction="backward")
    add("rolling_expanding", float(df["rmean5"].iloc[-1]) > 0 and float(df["emax"].iloc[-1]) > 99,
        "rolling(5).mean + expanding().max computed")
    add("resample_hourly", len(h) == 67 and int(h["count"].max()) == 60 and int(h["count"].min()) == 40,
        f"{len(h)} hourly buckets (66 full x60 + trailing {int(h['count'].min())})")
    add("groupby", len(gb) == 6, f"{len(gb)} 4h groups")
    add("asof_merge_asof", (not q.empty) and len(m) == 1 and not m["close"].isna().any(), "asof + merge_asof backward ok")

    # ---- point-in-time: clean rolling feature (formula recompute on past-only) ----
    df["f_clean"] = df["close"].rolling(3, min_periods=1).mean()
    dec_times = df.index[1000:1100]
    formula_clean = lambda past: past["close"].rolling(3, min_periods=1).mean().iloc[-1]
    problems = detect_future_use(df, "f_clean", dec_times, formula_clean)
    add("point_in_time_clean", len(problems) == 0, "rolling feature reproduces from past-only formula at every decision time")

    # ---- injected future leak must be DETECTED (formula needs a row that does not exist yet) ----
    df["f_leak"] = df["close"].shift(-1)  # uses next bar close -> leak
    formula_leak = lambda past: past["close"].shift(-1).iloc[-1]  # -> NaN at the last past row
    problems2 = detect_future_use(df, "f_leak", dec_times, formula_leak)
    add("lookahead_detector", len(problems2) > 0, f"detector flagged {len(problems2)} contaminated decision rows (past-only formula cannot reproduce)")

    # ---- multi-timeframe: M1 decisions vs H1 bar completion ----
    m1_idx = pd.date_range("2026-02-02 09:00", periods=600, freq="1min", tz="UTC")
    m1 = pd.DataFrame({"close": 100 + np.cumsum(rng.standard_normal(600)) * 0.05}, index=m1_idx)
    h1_rows = []
    for start in m1_idx[::60]:
        window = m1["close"].loc[start:start + pd.Timedelta(minutes=59)]
        h1_rows.append({"h1_start": start, "h1_end": start + pd.Timedelta(minutes=59),
                        "h1_close": float(window.iloc[-1]), "h1_first": float(window.iloc[0]),
                        "complete_at": start + pd.Timedelta(minutes=60)})
    h1 = pd.DataFrame(h1_rows)  # bars 09:00,10:00,11:00,12:00,...
    # make bar 12:00 close dramatically different so the leak is visible
    h1.loc[h1["h1_start"] == pd.Timestamp("2026-02-02 12:00", tz="UTC"), "h1_close"] += 50.0

    decision = m1_idx[180]  # 12:00:00
    buggy = h1[h1["h1_start"] <= decision].iloc[-1]      # includes bar started 12:00 -> FUTURE content
    clean = h1[h1["complete_at"] <= decision].iloc[-1]   # only bars fully done by 12:00 -> 11:00 bar
    leak_flag = buggy["complete_at"] > decision          # true => buggy bar contains post-decision data
    add("multi_tf_no_incomplete_h1", leak_flag and clean["h1_start"] < buggy["h1_start"] and not np.isclose(clean["h1_close"], buggy["h1_close"]),
        f"decision 12:00: clean=H1 {clean['h1_start'].time()} close={clean['h1_close']:.3f} | buggy=H1 {buggy['h1_start'].time()} close={buggy['h1_close']:.3f} (leak={leak_flag})")

    # ---- duplicate samples ----
    dup_df = pd.concat([df.iloc[:100], df.iloc[:100]])
    add("dup_detection", dup_df.index.duplicated().sum() == 100, "duplicated timestamps detected")

    # ---- multi-timeframe rolling feature must not leak (M1 features from H1 via completed bars) ----
    # feature = last completed H1 close asof <= t-1s (decision after bar t close)
    comp = h1.set_index("complete_at")["h1_close"]
    m1["h1feat_clean"] = comp.asof(m1_idx - pd.Timedelta(seconds=1)).to_numpy()
    feats = m1["h1feat_clean"].dropna()
    add("multi_tf_feature_clean", len(feats) > 100 and bool(np.isfinite(feats).all()),
        f"{len(feats)} M1 rows got completed-H1 feature (asof complete_at)")

    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ts_leak: {status} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
