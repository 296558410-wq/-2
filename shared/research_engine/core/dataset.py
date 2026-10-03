# -*- coding: utf-8 -*-
"""core/dataset.py — 数据集协议 + Synthetic XAUUSD 生成器（§4）。

价格模型（1s tick，UTC）：
  * 状态：trend_up / trend_down / range / high_vol（马尔可夫切换，分钟级）
  * range 带均值回复（锚定进入时价格）；trend 带漂移
  * 波动率：基准 σ + 日内 U 型 + regime 乘子 + **volatility shock**（随机发生、
    指数衰减 2–6h，×2.5–4）
  * spread 随波动放大；买卖量不对称 ∝ 当秒收益
输出：
  data/synthetic/XAUUSD_tick1s.parquet
  data/synthetic/XAUUSD_M{1,5}.parquet / XAUUSD_H1.parquet
  data/synthetic/ground_truth.parquet   ← 逐 M1 bar 的 regime/shock 真值（仅验证用，
    严禁进入 feature/label 管道）
  data/synthetic/MANIFEST.json（含 sha256 数据版本）
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "synthetic"

VERSION = "synthetic-xauusd-v1"
SYMBOL = "XAUUSD"

# 模型参数（每 1s；价格单位 = 美元/盎司）
S0 = 2400.0
SIGMA_SEC_BASE = 1.0e-4          # ~2.9% 日波动
KAPPA_RANGE = 0.02               # range 均值回复强度（/s）
TREND_MU_MIN = {"trend_up": 1.2e-4, "trend_down": -1.2e-4, "range": 0.0, "high_vol": 0.0}  # 漂移（/分钟），已知答案可检但量级合理
REGIME_VOL_MULT = {"trend_up": 1.0, "trend_down": 1.0, "range": 0.65, "high_vol": 2.2}
REGIME_HOURS = {"trend_up": (1, 6), "trend_down": (1, 6), "range": (0.5, 3.0), "high_vol": (0.5, 2.0)}
SPREAD_BPS_BASE = 0.9
SHOCK_LAMBDA_PER_DAY = 0.18      # 平均每 ~5.5 天一次 vol shock
SHOCK_MULT = (2.5, 4.0)
SHOCK_HOURS = (2.0, 6.0)
JUMPS_PER_DAY = 0.5              # 大跳跃（信息事件）
START_UTC = pd.Timestamp("2026-01-05", tz="UTC")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class SyntheticDataset:
    days: int
    seed: int
    start_utc: pd.Timestamp
    ticks: pd.DataFrame = field(default_factory=pd.DataFrame)
    bars: dict = field(default_factory=dict)          # {"M1": df, "M5": df, "H1": df}
    ground_truth_m1: pd.DataFrame = field(default_factory=pd.DataFrame)
    files: dict = field(default_factory=dict)         # name -> sha256
    generated_at_utc: str = ""

    @property
    def version(self) -> str:
        return VERSION


class SyntheticXAUUSDGenerator:
    """1s tick 生成（分钟级 regime 循环 + 秒级向量化）。"""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def _regime_sequence(self, n_minutes: int, rng: np.random.Generator) -> list[tuple[int, str, float]]:
        """返回 [(minute_start, regime, shock_mult)]，逐分钟。"""
        seq = []
        minute = 0
        shock_until = -1
        shock_mult = 1.0
        while minute < n_minutes:
            # 选择 regime
            p = rng.random()
            if p < 0.40:
                regime = "trend_up"
            elif p < 0.65:
                regime = "range"
            elif p < 0.85:
                regime = "trend_down"
            else:
                regime = "high_vol"
            lo, hi = REGIME_HOURS[regime]
            dur_min = int(rng.uniform(lo, hi) * 60)
            # 周期性冲击检查
            for _ in range(dur_min):
                if minute >= n_minutes:
                    break
                if minute >= shock_until and rng.random() < SHOCK_LAMBDA_PER_DAY / 1440.0:
                    shock_until = minute + int(rng.uniform(*SHOCK_HOURS) * 60)
                    shock_mult = float(rng.uniform(*SHOCK_MULT))
                    regime = "high_vol"
                seq.append((minute, regime, shock_mult))
                if minute >= shock_until:
                    shock_mult = 1.0
                minute += 1
        return seq

    def generate(self, days: int, start_utc: pd.Timestamp = START_UTC,
                 pure_rw: bool = False) -> SyntheticDataset:
        """pure_rw=True：纯几何布朗运动（无 regime/无 shock/无跳跃/无均值回复）——
        供已知答案实验 A 使用。"""
        rng = np.random.default_rng(self.seed)
        n_minutes = days * 1440
        if pure_rw:
            seq = [(m, "range", 1.0) for m in range(n_minutes)]
        else:
            seq = self._regime_sequence(n_minutes, rng)

        sec_of_day_all = np.arange(n_minutes * 60) % 86400
        intraday = 1.0 + 0.8 * np.exp(-((sec_of_day_all - 3600 * 8) ** 2) / (2 * (3600 * 2.5) ** 2)) \
                        + 0.8 * np.exp(-((sec_of_day_all - 3600 * 14.5) ** 2) / (2 * (3600 * 2.5) ** 2))

        # 逐分钟循环（路径依赖：range 均值回复 / shock 衰减）
        rets = np.empty(n_minutes * 60)
        sigmas = np.empty(n_minutes * 60)
        regimes_min = np.empty(n_minutes, dtype=object)
        shocks_min = np.zeros(n_minutes, dtype=bool)
        mus_min = np.zeros(n_minutes)
        anchor = np.log(S0)
        logp = np.log(S0)
        j = 0
        for m0, regime, shock_mult in seq:
            mu_min = 0.0 if pure_rw else TREND_MU_MIN[regime]
            vol_mult = (1.0 if pure_rw else REGIME_VOL_MULT[regime] * shock_mult)
            sigma_m = SIGMA_SEC_BASE * vol_mult
            mus_min[m0] = mu_min
            regimes_min[m0] = "rw" if pure_rw else regime
            shocks_min[m0] = (not pure_rw) and shock_mult > 1.0
            n_sec = 60
            idx = slice(m0 * 60, m0 * 60 + n_sec)
            sigma_arr = sigma_m * intraday[idx]
            z = rng.standard_normal(n_sec)
            mu_sec = mu_min / 60.0   # 每分钟漂移 → 每秒漂移（bugfix 2026-09-04）
            if regime == "range" and not pure_rw:
                # 均值回复到锚点（锚点 = 进入 range 时的价格；进入时更新）
                if m0 == 0 or regimes_min[m0 - 1] != "range":
                    anchor = logp
                r = KAPPA_RANGE * (anchor - logp) + sigma_arr * z
            else:
                r = mu_sec + sigma_arr * z
            # 随机跳跃（信息事件；纯 RW 关闭）
            jump = (not pure_rw) and (rng.random(n_sec) < JUMPS_PER_DAY / 86400.0)
            r = r + rng.standard_normal(n_sec) * (6 * SIGMA_SEC_BASE) * jump
            rets[idx] = r
            sigmas[idx] = sigma_arr
            logp += r.sum()
            j += 1

        # ---- 组装 tick ----
        mid = S0 * np.exp(np.cumsum(rets))
        ts = pd.to_datetime(start_utc, utc=True) + pd.to_timedelta(np.arange(len(rets)), unit="s")
        # 跳跃位置清理（漂移用真实实现）
        spread_bp = np.maximum(SPREAD_BPS_BASE * 0.4,
                               SPREAD_BPS_BASE * (0.6 + 2.5 * sigmas / SIGMA_SEC_BASE))
        spread_bp = np.minimum(spread_bp, SPREAD_BPS_BASE * 8)
        spread = mid * spread_bp / 10000.0
        # 买卖量：总量 ~ 泊松，买量比例 ∝ 当秒收益方向
        volume = rng.poisson(6.0, size=len(rets)) + 1
        buy_frac = 1.0 / (1.0 + np.exp(-30.0 * np.clip(rets / np.maximum(sigmas, 1e-9), -3, 3)))
        buy_volume = np.round(volume * buy_frac).astype(np.int64)
        ticks = pd.DataFrame({
            "ts_utc": ts,
            "symbol": SYMBOL,
            "bid": mid - spread / 2.0,
            "ask": mid + spread / 2.0,
            "spread": spread,
            "volume": volume.astype(np.int64),
            "buy_volume": buy_volume,
            "source": "synthetic",
        })
        # mid 保留便于验证
        ticks.insert(3, "mid", mid)

        # ---- bars ----
        def to_bars(rule: str) -> pd.DataFrame:
            g = ticks.set_index("ts_utc")
            ohlc = g["mid"].resample(rule).agg(["first", "max", "min", "last"])
            vol = g["volume"].resample(rule).sum()
            bvol = g["buy_volume"].resample(rule).sum()
            sp = g["spread"].resample(rule).mean()
            cnt = g["mid"].resample(rule).count()
            bars = pd.DataFrame({
                "open": ohlc["first"], "high": ohlc["max"], "low": ohlc["min"],
                "close": ohlc["last"], "volume": vol.astype(np.int64),
                "buy_volume": bvol.astype(np.int64),
                "spread_mean": sp, "tick_count": cnt.astype(np.int64),
            }).dropna()
            bars.index.name = "ts_utc"
            bars.insert(0, "symbol", SYMBOL)
            return bars.reset_index()

        bars = {r: to_bars(r) for r in ("1min", "5min", "1h")}

        # ---- ground truth（M1 粒度）----
        m1 = bars["1min"]
        gt = pd.DataFrame({
            "ts_utc": m1["ts_utc"],
            "regime": regimes_min[: len(m1)],
            "in_shock": shocks_min[: len(m1)],
            "true_mu_min": mus_min[: len(m1)],
            "true_sigma_sec": sigmas[::60][: len(m1)],
        })
        return SyntheticDataset(
            days=days, seed=self.seed, start_utc=pd.Timestamp(start_utc),
            ticks=ticks, bars=bars, ground_truth_m1=gt,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def save(self, ds: SyntheticDataset, out: Path = OUT) -> dict:
        out.mkdir(parents=True, exist_ok=True)
        files = {}
        p = out / "XAUUSD_tick1s.parquet"
        ds.ticks.to_parquet(p, index=False)
        files["XAUUSD_tick1s.parquet"] = {"rows": int(len(ds.ticks)), "sha256": sha256_file(p)}
        for rule, name in (("1min", "XAUUSD_M1.parquet"), ("5min", "XAUUSD_M5.parquet"), ("1h", "XAUUSD_H1.parquet")):
            p = out / name
            ds.bars[rule].to_parquet(p, index=False)
            files[name] = {"rows": int(len(ds.bars[rule])), "sha256": sha256_file(p)}
        p = out / "ground_truth.parquet"
        ds.ground_truth_m1.to_parquet(p, index=False)
        files["ground_truth.parquet"] = {"rows": int(len(ds.ground_truth_m1)), "sha256": sha256_file(p)}
        manifest = {
            "dataset_version": ds.version,
            "generator": "research_engine.core.dataset.SyntheticXAUUSDGenerator",
            "seed": ds.seed, "days": ds.days,
            "start_utc": str(ds.start_utc),
            "generated_at_utc": ds.generated_at_utc,
            "model": {
                "regimes": list(REGIME_HOURS.keys()),
                "sigma_sec_base": SIGMA_SEC_BASE,
                "shock_lambda_per_day": SHOCK_LAMBDA_PER_DAY,
                "jumps_per_day": JUMPS_PER_DAY,
            },
            "files": files,
        }
        (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest


def ensure_synthetic(days: int = 40, seed: int = 42, force: bool = False) -> SyntheticDataset:
    """加载已生成数据；不存在或天数不足时生成。"""
    manifest_path = OUT / "MANIFEST.json"
    if not force and manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        if m.get("days", 0) >= days and m.get("dataset_version") == VERSION:
            ds = SyntheticDataset(days=days, seed=seed, start_utc=START_UTC,
                                  generated_at_utc=m.get("generated_at_utc", ""))
            ds.ticks = pd.read_parquet(OUT / "XAUUSD_tick1s.parquet")
            ds.bars = {"1min": pd.read_parquet(OUT / "XAUUSD_M1.parquet"),
                       "5min": pd.read_parquet(OUT / "XAUUSD_M5.parquet"),
                       "1h": pd.read_parquet(OUT / "XAUUSD_H1.parquet")}
            ds.ground_truth_m1 = pd.read_parquet(OUT / "ground_truth.parquet")
            ds.files = m.get("files", {})
            return ds
    gen = SyntheticXAUUSDGenerator(seed=seed)
    ds = gen.generate(days=days)
    gen.save(ds)
    return ds
