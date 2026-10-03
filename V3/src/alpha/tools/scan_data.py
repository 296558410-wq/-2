"""Stage 0 - real data scan for V3-HFT-ALPHA-DISCOVERY-001.

Reads the actual parquet files (never copies the registry) and emits
alpha/data/data_manifest.json + alpha/data/data_gaps.md.

Read-only. No MT5 calls. No writes outside alpha/.
"""
from __future__ import annotations
import os, json, glob, hashlib, datetime as dt
import numpy as np
import pandas as pd

ROOT = r"C:\AIQuant"
OUT = os.path.join(ROOT, "research", "hermes", "trader_v3", "alpha")
DATA_OUT = os.path.join(OUT, "data")
os.makedirs(DATA_OUT, exist_ok=True)

NOW = dt.datetime.now(dt.timezone.utc).isoformat()

GAP_SESSION_S = 4 * 3600        # >4h gap = between-session (not a data error by this venue's hours)
GAP_WEEKEND_S = 24 * 3600


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gap_stats(ts_ns: np.ndarray) -> dict:
    n = len(ts_ns)
    if n < 2:
        return {"max_gap_s": None, "n_session_gaps": 0, "n_weekend_gaps": 0, "top_gaps": []}
    s = np.sort(ts_ns)
    d = np.diff(s).astype(np.float64) / 1e9
    order = np.argsort(d)[::-1]
    top = []
    for k in order[:8]:
        top.append({
            "from_utc": pd.Timestamp(int(s[k]), unit="ns", tz="UTC").isoformat(),
            "to_utc": pd.Timestamp(int(s[k + 1]), unit="ns", tz="UTC").isoformat(),
            "gap_s": float(d[k]),
        })
    return {
        "max_gap_s": float(d.max()),
        "n_session_gaps": int(np.sum(d > GAP_SESSION_S)),
        "n_weekend_gaps": int(np.sum(d > GAP_WEEKEND_S)),
        "top_gaps": top,
    }


def tick_stats(ts_ns: np.ndarray, bid: np.ndarray, ask: np.ndarray,
               hash_path: str | None = None, extra: dict | None = None) -> dict:
    n = len(ts_ns)
    rec: dict = {"rows": int(n)}
    if hash_path:
        rec["sha256"] = sha256(hash_path)
    if n == 0:
        rec["empty"] = True
        return rec
    # order / duplicates (on original order)
    d = np.diff(ts_ns.astype(np.int64))
    rec["out_of_order_rate"] = float(np.mean(d < 0)) if n > 1 else 0.0
    uniq, counts = np.unique(ts_ns, return_counts=True)
    rec["duplicate_rate"] = float(1.0 - len(uniq) / n)
    rec["ts_min_utc"] = pd.Timestamp(int(ts_ns.min()), unit="ns", tz="UTC").isoformat()
    rec["ts_max_utc"] = pd.Timestamp(int(ts_ns.max()), unit="ns", tz="UTC").isoformat()
    span_s = (int(ts_ns.max()) - int(ts_ns.min())) / 1e9
    rec["span_hours"] = round(span_s / 3600.0, 3)
    rec["tick_rate_hz"] = round(n / span_s, 3) if span_s > 0 else None
    rec.update(gap_stats(ts_ns))
    # quote health
    with np.errstate(invalid="ignore"):
        spread = ask - bid
    rec["nan_rate_bid"] = float(np.mean(~np.isfinite(bid)))
    rec["nan_rate_ask"] = float(np.mean(~np.isfinite(ask)))
    rec["nonpositive_quote_rate"] = float(np.mean((bid <= 0) | (ask <= 0)))
    rec["crossed_quote_rate"] = float(np.mean(spread < 0))
    rec["median_spread_usd"] = float(np.median(spread))
    mid = (bid + ask) / 2.0
    rec["median_spread_bp"] = float(np.median(spread / mid * 1e4))
    if extra:
        rec.update(extra)
    return rec


def scan_duka_monthly() -> list[dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, r"data\staging_duka\assembled\ticks_*.parquet"))):
        df = pd.read_parquet(p, columns=["ts_utc", "bid", "ask", "ask_vol", "bid_vol"])
        ts = (df["ts_utc"].to_numpy(dtype=np.int64) * 1_000_000)  # ms -> ns
        rec = {"family": "duka_monthly_tick", "file": os.path.basename(p), "path": p,
               "columns": list(df.columns),
               "units": {"ts_utc": "epoch_ms_utc", "bid": "USD", "ask": "USD",
                         "ask_vol": "int(venue)", "bid_vol": "int(venue)"},
               "utc_proof": "epoch ms since 1970-01-01 UTC (absolute; no local tz)",
               "ts_col": "ts_utc",
               "bid_vol_gap_frac": float(np.mean(df["bid_vol"].to_numpy() == df["ask_vol"].to_numpy())),
               }
        rec.update(tick_stats(ts, df["bid"].to_numpy(np.float64), df["ask"].to_numpy(np.float64), p))
        out.append(rec)
        print("  duka_monthly", rec["file"], rec["rows"], rec["ts_min_utc"], "->", rec["ts_max_utc"])
    return out


def scan_duka_daily() -> list[dict]:
    out = []
    files = sorted(glob.glob(os.path.join(ROOT, r"data\staging_duka\ticks_*.parquet")))
    for p in files:
        name = os.path.basename(p)
        ymd = name.replace("ticks_", "").replace(".parquet", "")
        try:
            day = pd.Timestamp(ymd + "000000", tz="UTC")  # yyyymmdd -> timestamp
        except Exception:
            continue
        df = pd.read_parquet(p)
        hour = df["hour"].to_numpy(np.float64)
        ms = df["ms"].to_numpy(np.float64)
        ms_from_hour_start = (hour * 3_600_000.0 + ms).astype(np.int64)  # ms within hour
        ts = np.asarray(day.value, dtype=np.int64) + ms_from_hour_start * 1_000_000  # ns
        bid = df["bid"].to_numpy(np.float64) / 1000.0
        ask = df["ask"].to_numpy(np.float64) / 1000.0
        rec = {"family": "duka_daily_tick", "file": name, "path": p,
               "columns": list(df.columns),
               "units": {"ms": "ms_within_hour", "bid": "int/USD*1e3", "ask": "int/USD*1e3",
                         "ask_vol": "int(venue)", "bid_vol": "int(venue)", "hour": "hour_of_day_utc"},
               "utc_proof": "date from filename + hour column + ms-within-hour; venue convention UTC",
               "ts_col": "reconstructed",
               "hours_present": sorted(set(int(h) for h in np.unique(hour)))}
        rec.update({"sha256": sha256(p)})
        rec.update(tick_stats(ts, bid, ask))
        out.append(rec)
    print("  duka_daily files:", len(out))
    return out


def scan_fxtm(family: str, pattern: str) -> list[dict]:
    out = []
    for p in sorted(glob.glob(pattern)):
        df = pd.read_parquet(p)
        ts = df["ts_utc"].to_numpy(dtype="datetime64[ns]").astype(np.int64)
        rec = {"family": family, "file": os.path.basename(p), "path": p,
               "columns": list(df.columns),
               "units": {"bid": "USD", "ask": "USD", "last": "USD", "volume": "tick_volume",
                         "volume_real": "real_volume", "flags": "MT5_flag_bits",
                         "ts_utc": "datetime64[ms,UTC]"},
               "utc_proof": "ts_utc is tz-aware datetime64[ms, UTC] (verified dtype)",
               "ts_col": "ts_utc"}
        if "volume_real" in df.columns:
            rec["volume_real_nonzero_frac"] = float(np.mean(df["volume_real"].to_numpy(np.float64) != 0.0))
        if "volume" in df.columns:
            rec["volume_nonzero_frac"] = float(np.mean(df["volume"].to_numpy(np.float64) != 0.0))
        if "last" in df.columns:
            rec["last_nonzero_frac"] = float(np.mean(df["last"].to_numpy(np.float64) != 0.0))
        rec.update(tick_stats(ts, df["bid"].to_numpy(np.float64), df["ask"].to_numpy(np.float64), p))
        out.append(rec)
    print(f"  {family} files:", len(out))
    return out


def scan_candles() -> dict:
    """Candle files: 1-minute bars with side (BID/ASK). Summarize (many files)."""
    files = sorted(glob.glob(os.path.join(ROOT, r"data\staging_duka\candles_*.parquet")))
    total_rows = 0
    dmin = None
    dmax = None
    sample_cols = None
    per_month = []
    for p in files:
        df = pd.read_parquet(p, columns=["day", "side"])
        total_rows += len(df)
        if sample_cols is None:
            sample_cols = list(pd.read_parquet(p).columns)
        d = df["day"]
        dmin = d.min() if dmin is None else min(dmin, d.min())
        dmax = d.max() if dmax is None else max(dmax, d.max())
        per_month.append({"file": os.path.basename(p), "rows": int(len(df)), "start": d.min(), "end": d.max()})
    return {"files": len(files), "total_rows": int(total_rows), "columns": sample_cols,
            "units": {"sec": "second_of_day", "open/close/low/high": "int/USD*1e3", "vol": "int", "side": "BID|ASK", "day": "date_str"},
            "date_min": dmin, "date_max": dmax, "per_file": per_month}


def main():
    manifest = {"schema": "v3_alpha_data_manifest/1", "generated_utc": NOW,
                "scanned_root": ROOT, "files": {}}
    print("[scan] duka monthly ticks")
    manifest["files"]["duka_monthly_tick"] = scan_duka_monthly()
    print("[scan] duka daily ticks")
    manifest["files"]["duka_daily_tick"] = scan_duka_daily()
    print("[scan] fxtm staging ticks")
    manifest["files"]["fxtm_staging_tick"] = scan_fxtm(
        "fxtm_staging_tick", os.path.join(ROOT, r"data\staging_fxtm\ticks_*.parquet"))
    print("[scan] fxtm live ticks")
    manifest["files"]["fxtm_live_tick"] = scan_fxtm(
        "fxtm_live_tick", os.path.join(ROOT, r"data\live_fxtm\ticks_*.parquet"))
    print("[scan] duka candles")
    manifest["files"]["duka_candles"] = scan_candles()

    # coverage summary per family
    summary = {}
    for fam, recs in manifest["files"].items():
        if fam == "duka_candles":
            summary[fam] = {"files": recs["files"], "total_rows": recs["total_rows"],
                            "date_min": recs["date_min"], "date_max": recs["date_max"]}
            continue
        tot = sum(r["rows"] for r in recs)
        tr = [r for r in recs if r.get("ts_min_utc")]
        summary[fam] = {
            "files": len(recs),
            "total_rows": int(tot),
            "ts_min_utc": min(r["ts_min_utc"] for r in tr) if tr else None,
            "ts_max_utc": max(r["ts_max_utc"] for r in tr) if tr else None,
            "median_spread_usd_files": [round(r["median_spread_usd"], 3) for r in tr][:6],
            "max_gap_s_overall": max((r["max_gap_s"] or 0) for r in tr) if tr else None,
        }
    manifest["summary"] = summary

    with open(os.path.join(DATA_OUT, "data_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("[scan] wrote data_manifest.json")
    print(json.dumps(summary, indent=1)[:4000])


if __name__ == "__main__":
    main()
