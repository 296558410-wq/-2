# -*- coding: utf-8 -*-
"""experiments/base.py — 实验公共设施（数据装载/特征/验证流水线）。

约定：
  * prepare_bars(days, seed, pure_rw) → M1 bars（ts_utc 升序）+ 收盘序列
  * run_strategy_validation：对给定 position 序列跑完整验证电池：
    时间切分 IS/OOS + walk-forward(5折) + 成本压力 + 置换 + shuffle + 子段
  * 结论只允许 SUPPORTED / REJECTED / EDGE_UNCERTAIN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..core.backtest import BacktestEngine, compute_metrics
from ..core.cost import CostModel
from ..core.dataset import ensure_synthetic
from ..core.feature import FeatureSpec, assert_no_lookahead, build as build_features
from ..core.signal import make_signal
from ..features import momentum, sma, ema, realised_vol, volatility_ratio, atr
from ..features.labels import add_forward_labels
from ..statistics.multiple_testing import summarize_fdr
from ..statistics.permutation import time_permutation
from ..statistics.robustness import subperiod_stability
from ..validation.cost_stress import run_cost_stress
from ..validation.placebo import label_shuffle_test
from ..validation.split import time_split
from ..validation.walk_forward import walk_forward_evaluate, walk_forward_folds

COST = CostModel(spread_bps=0.9, commission_bps=0.35, slippage_bps=0.2)
PPY = 365 * 1440.0


def prepare_bars(days: int = 30, seed: int = 42, pure_rw: bool = False,
                 force_rw_gen: bool = False) -> tuple[pd.DataFrame, pd.Series]:
    """返回 (m1 bars, close Series)。pure_rw 时临时生成纯 RW 数据（不入主缓存）。"""
    if pure_rw:
        from ..core.dataset import SyntheticXAUUSDGenerator
        ds = SyntheticXAUUSDGenerator(seed=seed).generate(days=days, pure_rw=True)
        m1 = ds.bars["1min"]
    else:
        m1 = ensure_synthetic(days=days, seed=seed).bars["1min"]
    m1 = m1.sort_values("ts_utc").reset_index(drop=True)
    return m1, m1.set_index("ts_utc")["close"]


def trend_specs(windows=(15, 30, 60)) -> list[FeatureSpec]:
    out = []
    for w in windows:
        out.append(FeatureSpec(f"mom{w}", momentum, {"window": w}))
    out.append(FeatureSpec("ema_ratio_15_60", _ema_ratio, {"fast": 15, "slow": 60}))
    return out


def vol_specs(windows=(15, 60, 120)) -> list[FeatureSpec]:
    out = []
    for w in windows:
        out.append(FeatureSpec(f"rv{w}", realised_vol, {"window": w, "annualize": True}))
    out.append(FeatureSpec("vol_ratio_15_120", volatility_ratio, {"short": 15, "long": 120}))
    return out


def _ema_ratio(bars, fast=15, slow=60):
    return ema(bars, fast) / ema(bars, slow) - 1.0


def build_X(m1: pd.DataFrame, specs: list[FeatureSpec]) -> pd.DataFrame:
    fm = build_features(m1, specs).drop_warmup()
    return fm.X


def add_labels(m1: pd.DataFrame) -> pd.DataFrame:
    return add_forward_labels(m1)


def no_lookahead_check(m1: pd.DataFrame, specs: list[FeatureSpec]) -> bool:
    res = assert_no_lookahead(m1, specs, probes=5, seed=1)
    return res["passed"]


def run_backtest(close: pd.Series, positions: pd.Series,
                 cost_multiplier: float = 1.0, name: str = "bt") -> dict:
    bt = BacktestEngine(cost_model=COST, periods_per_year=PPY)
    res = bt.run(close, positions.fillna(0.0), cost_multiplier=cost_multiplier, name=name)
    return {"metrics": res.metrics, "df": res.df}


def full_validation(close: pd.Series, positions: pd.Series, label_name: str,
                    n_folds: int = 5, min_train: int = 1000,
                    n_perm: int = 1500, seed: int = 7) -> dict:
    """对固定信号做完整验证电池。

    统计口径（2026-09-04 修订）：
      * 显著性（permutation / label shuffle / time perm）一律基于**毛收益**
        ——成本拖累不是 skill；避免把 cost drag 误判为负 alpha
      * walk-forward / cost-stress / 指标 用**净收益**（实际可行性视角）
    """
    rng = np.random.default_rng(seed)
    bt = BacktestEngine(cost_model=COST, periods_per_year=PPY)
    res = bt.run(close, positions.fillna(0.0), name="full")
    df = res.df
    net = df["net_r"].values
    gross = df["gross_r"].values
    pos = df["position"].values
    # OOS 结构：Train 60% / Val 20% / Test 20%（时间顺序）
    n = len(df)
    sp = time_split(n, 0.6, 0.2, 0.2)
    oos_gross = gross[sp["test"]]
    # Walk-forward（净收益逐折）
    folds = walk_forward_folds(n, n_folds=n_folds, min_train=min_train,
                               val_frac=0.2, mode="expanding", embargo=0)
    wf = walk_forward_evaluate(net, pos, folds, one_way_cost=COST.one_way_cost, periods_per_year=PPY)
    # 显著性检验（毛收益；skill 证据）
    perm = _perm(gross[1:], n_perm, seed)
    shuf = label_shuffle_test(pos[:-1], gross[1:], n_iter=800, seed=seed)
    # 成本压力（净收益）
    stress = run_cost_stress(gross, pos, COST.one_way_cost, multipliers=(1.0, 2.0, 3.0),
                             periods_per_year=PPY)
    # 子段稳定（净收益）
    sub = subperiod_stability(net, n_parts=4, periods_per_year=PPY)
    return {
        "n_bars": int(n),
        "metrics_1x": {k: res.metrics[k] for k in
                       ("net_total_return", "gross_total_return", "cost_total",
                        "sharpe_annualized", "max_drawdown", "win_rate",
                        "profit_factor", "turnover_total", "n_trades")},
        "oos": {"sharpe_net": float(_sharpe(net[sp["test"]])),
                "sharpe_gross": float(_sharpe(oos_gross)),
                "mean_gross": float(oos_gross.mean()), "n": int(len(oos_gross))},
        "walk_forward": wf,
        "permutation_gross": {k: perm[k] for k in ("stat_obs", "p_value_two_sided", "n_iter")},
        "label_shuffle_gross": {k: shuf[k] for k in ("stat_obs", "p_value", "n_iter")},
        "cost_stress": {k: v["sharpe_annualized"] for k, v in stress.items() if k != "_one_way_cost"},
        "subperiod": sub,
        "seed": seed,
    }


def _sharpe(x: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(PPY)) if sd > 0 else 0.0


def _perm(net, n_perm, seed):
    from ..statistics.permutation import run_permutation
    return run_permutation(net, n_iter=n_perm, seed=seed, backend="auto")


def fdr_across(keys: list[tuple], p_values: list[float], alpha: float = 0.05) -> dict:
    """对一组 (key, p) 做 BH 校正，返回 {keys, p, q, reject} 供报告。"""
    s = summarize_fdr(np.asarray(p_values, dtype=float), alpha=alpha)
    return {"keys": [str(k) for k in keys], "p_values": [float(p) for p in p_values],
            "bh_reject": s["bh_reject"], "raw_sig": s["raw_sig_at_alpha"],
            "n_hypotheses": s["n_hypotheses"], "max_q": s["max_q"]}
