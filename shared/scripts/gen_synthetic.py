"""gen_synthetic.py — 生成模拟 XAUUSD 数据（tick/M1/M5/H1），验证数据管线。

生成模型（仅用于管线联调，不代表真实市场）：
  1 秒粒度 mid 价格：GBM + 跳跃 + 日内波动率 U 型
  bid/ask = mid ± spread/2（spread 随波动放大）
  输出: data/synthetic/XAUUSD_*.parquet + MANIFEST
用法: python scripts/gen_synthetic.py --days 2 --seed 42
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"


def gen_1s_quotes(days: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * 86400
    # 日内波动 U 型因子（以 UTC 秒计）
    sec_of_day = np.arange(n) % 86400
    intraday = 1.0 + 0.8 * np.exp(-((sec_of_day - 3600 * 8) ** 2) / (2 * (3600 * 2.5) ** 2)) \
                      + 0.8 * np.exp(-((sec_of_day - 3600 * 14.5) ** 2) / (2 * (3600 * 2.5) ** 2))
    dt = 1.0  # 秒
    mu = 0.0
    base_sigma = 0.00010  # 每秒波动 ~1bp
    sigma_t = base_sigma * intraday
    # GBM
    z = rng.standard_normal(n)
    rets = (mu - 0.5 * sigma_t ** 2) * dt + sigma_t * np.sqrt(dt) * z
    # 随机跳跃（每 ~6 小时一次 ±3-6 sigma 事件）
    jump_prob = dt / (6 * 3600)
    jumps = rng.standard_normal(n) * (6 * base_sigma) * (rng.random(n) < jump_prob)
    rets = rets + jumps
    mid = 2400.0 * np.exp(np.cumsum(rets))
    # spread（bp 计，随波动放大）
    spread_bp = np.maximum(0.2, 0.5 + 8 * sigma_t / base_sigma)
    spread = mid * spread_bp / 10000.0
    ts = pd.to_datetime("2026-01-05", utc=True) + pd.to_timedelta(np.arange(n), unit="s")
    df = pd.DataFrame({
        "ts_utc": ts,
        "symbol": "XAUUSD",
        "mid": mid,
        "bid": mid - spread / 2,
        "ask": mid + spread / 2,
        "spread": spread,
        "volume": rng.integers(1, 20, size=n).astype(float),
        "source": "synthetic",
    })
    return df


def to_bars(quotes: pd.DataFrame, rule: str) -> pd.DataFrame:
    g = quotes.set_index("ts_utc")
    ohlc = g["mid"].resample(rule).agg(["first", "max", "min", "last"])
    vol = g["volume"].resample(rule).sum()
    sp = g["spread"].resample(rule).mean()
    cnt = g["mid"].resample(rule).count()
    bars = pd.DataFrame({
        "open": ohlc["first"], "high": ohlc["max"], "low": ohlc["min"],
        "close": ohlc["last"], "volume": vol, "spread_mean": sp, "tick_count": cnt,
    }).dropna()
    bars.index.name = "ts_utc"
    bars.insert(0, "symbol", "XAUUSD")
    return bars.reset_index()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"[gen] 生成 {args.days} 天 1 秒级报价 (seed={args.seed}) ...")
    quotes = gen_1s_quotes(args.days, args.seed)
    qpath = OUT / "XAUUSD_tick1s.parquet"
    quotes.to_parquet(qpath, index=False)
    print(f"[gen] tick1s: {len(quotes):,} 行 -> {qpath}")

    manifest = {"generator": "scripts/gen_synthetic.py", "seed": args.seed,
                "days": args.days, "symbol": "XAUUSD", "files": {}}
    for rule, name in [("1min", "XAUUSD_M1.parquet"), ("5min", "XAUUSD_M5.parquet"), ("1h", "XAUUSD_H1.parquet")]:
        bars = to_bars(quotes, rule)
        p = OUT / name
        bars.to_parquet(p, index=False)
        print(f"[gen] {rule}: {len(bars):,} bars -> {p}")
        manifest["files"][name] = {"rows": int(len(bars)), "sha256": sha256_file(p)}
    manifest["files"]["XAUUSD_tick1s.parquet"] = {"rows": int(len(quotes)), "sha256": sha256_file(qpath)}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("[gen] MANIFEST.json 已写入")


if __name__ == "__main__":
    main()
