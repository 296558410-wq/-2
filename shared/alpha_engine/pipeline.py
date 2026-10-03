# -*- coding: utf-8 -*-
"""alpha_engine/pipeline.py — 一轮研究的完整流水线（§10/§12/§13/§15）。

run_round(dataset_id, ...)：
  1. 载入冻结 hypothesis_registry（规格不可改）
  2. 载入注册数据集（data_registry）→ QC 已在注册时通过
  3. 生成特征/标签 → 无前视截断抽查
  4. info 评估（全部 N）
  5. OOS permutation（全部 N，GPU 优先）→ 收集 p
  6. 全局 BH-FDR（整个 round 的 N 一起校正）
  7. FDR 存活者 → bootstrap CI → WF 折叠 IC → 转规则信号做成本压力 & 子段
  8. 汇总：N tested / raw sig / FDR sig / OOS pos / WF stable / cost robust / final
  9. 写入 alpha_registry + reports/round_<ts>.md
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from research_engine.core import data_registry
from research_engine.statistics.multiple_testing import benjamini_hochberg
from .evaluator import evaluate_information
from .filters import bootstrap_ci_ic, oos_permutation_p
from .generator import add_h1_state, add_labels, build_matrix
from .hypothesis import load_frozen
from .registry import register_candidate, summary as alpha_summary

# 成本校准自实测基线：spread mean $0.159 (≈0.37bp)，median 0.35bp；p99 0.53bp；滑点假设 0.3bp
XAUUSD_COST = {"spread_bps": 0.6, "commission_bps": 0.0, "slippage_bps": 0.3}
ALPHA_LEVEL = 0.05
M1_DATASET = "XAUUSD_M1_MT5-FXTM-Live_20260904_v001"


def run_round(dataset_id: str, *, n_perm: int = 1000, n_boot: int = 1500,
              train_frac: float = 0.6, backend: str = "auto",
              max_hypotheses: int | None = None) -> dict:
    t_all = time.perf_counter()
    frozen = load_frozen()
    hyps = frozen["hypotheses"]
    if max_hypotheses:
        hyps = hyps[:max_hypotheses]
    m1, meta = data_registry.load_dataset(dataset_id)
    m1 = m1.sort_values("ts_utc").reset_index(drop=True)
    report = {"dataset_id": dataset_id, "dataset_meta": meta,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "n_hypotheses_registered": len(hyps),
              "cost": XAUUSD_COST, "alpha_level": ALPHA_LEVEL}
    # H10 需要 H1
    h1 = None
    if any(h["feature"].startswith("h1_") for h in hyps):
        cands = data_registry.find_dataset(meta["symbol"], "H1", source=meta["source"])
        if cands:
            h1_df, _ = data_registry.load_dataset(cands[-1]["dataset_id"])
            h1 = h1_df.sort_values("ts_utc").reset_index(drop=True)

    X, lookbacks = build_matrix(m1, h1)
    lb_max = max(lookbacks.values()) if lookbacks else 1
    y = add_labels(m1, horizons=(5, 15, 30, 60, 240))
    # 对齐：特征矩阵已丢弃 warmup 头部 → 同步截断 m1 与 labels
    drop = len(m1) - len(X)
    m1t = m1.iloc[drop:].reset_index(drop=True)
    y = y.iloc[drop:].reset_index(drop=True)
    X = X.reset_index(drop=True)
    assert len(X) == len(m1t) == len(y)

    h1m = None
    if h1 is not None:
        h1m = add_h1_state(m1t, h1).reset_index(drop=True)  # bugfix: 与 X/y 同为 RangeIndex

    results = []
    t0 = time.perf_counter()
    for i, h in enumerate(hyps):
        feat_name = h["feature"]
        if feat_name.startswith("h1_"):
            if h1m is None or feat_name not in h1m.columns:
                results.append(_skipped(h, "no H1 state"))
                continue
            f = h1m[feat_name]
        else:
            if feat_name not in X.columns:
                results.append(_skipped(h, f"feature missing: {feat_name}"))
                continue
            f = X[feat_name]
        lab = h["label"]
        if lab not in y.columns:
            results.append(_skipped(h, f"label missing: {lab}"))
            continue
        l = y[lab]
        info = evaluate_information(f, l, h["expected_direction"])
        perm = oos_permutation_p(f, l, train_frac=train_frac, n_iter=n_perm,
                                 seed=42 + i, backend=backend)
        results.append({"hypothesis": h, "info": info, "perm": perm, "stage": "RAW"})
    report["info_stage_s"] = round(time.perf_counter() - t0, 1)

    # 缺失假设记录
    report["skipped"] = [{"hypothesis_id": r["hypothesis"]["hypothesis_id"],
                          "reason": r.get("skip_reason")}
                         for r in results if r["stage"] == "SKIP"]
    # ---- 全局 BH-FDR（只对有效检验） ----
    valid = [r for r in results if r["stage"] != "SKIP" and r["perm"].get("n_iter", 0) > 0]
    p_all = np.array([r["perm"]["p_value"] for r in valid])
    bh = benjamini_hochberg(p_all, alpha=ALPHA_LEVEL)
    for r, q, rej in zip(valid, bh["q_values"], bh["reject"]):
        r["q_value"] = float(q)
        r["fdr_reject"] = bool(rej)
        r["stage"] = "OOS_SIG"
    n_raw = int((p_all < ALPHA_LEVEL).sum())
    n_fdr = int(bh["n_reject"])
    report["funnel"] = {"n_tested": len(valid), "n_raw_sig": n_raw, "n_fdr_sig": n_fdr}

    # ---- FDR 存活者深挖：bootstrap CI + WF 折叠 ----
    survivors = [r for r in valid if r["fdr_reject"]]
    deep = []
    for r in survivors:
        h = r["hypothesis"]
        feat_name = h["feature"]
        f = h1m[feat_name] if feat_name.startswith("h1_") else X[feat_name]
        l = y[h["label"]]
        # bootstrap CI 与 perm 同段（OOS 尾部）
        pair = pd.concat([f, l], axis=1).dropna()
        cut = int(len(pair) * train_frac)
        oos_pair = pair.iloc[cut:]
        boot = bootstrap_ci_ic(oos_pair.iloc[:, 0], oos_pair.iloc[:, 1], n_iter=n_boot, seed=7)
        wf = _fold_ics(f, l, train_frac=train_frac)
        r["bootstrap"] = boot
        r["wf"] = wf
        r["stage"] = "FDR_SIG"
        deep.append(r)
    report["n_survivors"] = len(deep)
    report["survivors"] = [_survivor_summary(r) for r in deep]

    # ---- 成本压力 & 子段（对 FDR 存活者转规则信号） ----
    cost_rows = []
    for r in deep:
        h = r["hypothesis"]
        if h["expected_direction"] in ("+", "-") and "forward_return" in h["label"]:
            feat_name = h["feature"]
            f = h1m[feat_name] if feat_name.startswith("h1_") else X[feat_name]
            cs = _cost_stress(f, m1t, h, XAUUSD_COST)
            r["cost_stress"] = cs
            r["stage"] = "COST_DONE"
            cost_rows.append({"hypothesis_id": h["hypothesis_id"], **cs})
        else:
            r["cost_stress"] = None
            r["stage"] = "COST_NA"
    report["cost_rows"] = cost_rows

    # ---- Alpha Registry 写入 ----
    alpha_records = []
    for r in deep:
        h = r["hypothesis"]
        decision = _decide(r)
        alpha_id = f"{h['hypothesis_id']}_{dataset_id[-4:]}"
        rec = {
            "hypothesis": h["description"], "features": h["feature"],
            "parameters": {"holding": h["holding"], "feature_params": h["feature_params"]},
            "dataset": dataset_id,
            "train_period": str(m1t["ts_utc"].iloc[0]) + "→" + str(m1t["ts_utc"].iloc[int(len(m1t) * train_frac)]),
            "test_period": str(m1t["ts_utc"].iloc[int(len(m1t) * train_frac)]) + "→" + str(m1t["ts_utc"].iloc[-1]),
            "OOS": {"ic": r["perm"]["ic_oos"], "p": r["perm"]["p_value"]},
            "FDR": {"q": r["q_value"], "reject": r["fdr_reject"]},
            "WF": r.get("wf"),
            "cost_stress": r.get("cost_stress"),
            "subperiod": r.get("subperiod"),
            "status": decision,
            "git_commit": _git(),
        }
        register_candidate(alpha_id, rec)
        alpha_records.append({"alpha_id": alpha_id, "status": decision,
                              "ic_oos": round(r["perm"]["ic_oos"], 4),
                              "q": round(r["q_value"], 4)})
    report["alpha_registry"] = alpha_summary()
    report["alpha_records"] = alpha_records
    report["elapsed_s"] = round(time.perf_counter() - t_all, 1)
    return report


def _skipped(h: dict, reason: str) -> dict:
    return {"hypothesis": h, "stage": "SKIP", "skip_reason": reason}


def _survivor_summary(r: dict) -> dict:
    h = r["hypothesis"]
    return {"hypothesis_id": h["hypothesis_id"], "feature": h["feature"],
            "label": h["label"], "ic_oos": round(r["perm"]["ic_oos"], 5),
            "p": round(r["perm"]["p_value"], 5), "q": round(r["q_value"], 5),
            "ci95": r.get("bootstrap", {}).get("ci95"),
            "wf_positive_frac": r.get("wf", {}).get("positive_frac")}


def _fold_ics(f: pd.Series, l: pd.Series, train_frac: float = 0.6, n_folds: int = 5) -> dict:
    from scipy.stats import spearmanr
    m = pd.concat([f, l], axis=1).dropna()
    n = len(m)
    cut = int(n * train_frac)
    seg = m.iloc[cut:]
    edges = np.linspace(0, len(seg), n_folds + 1, dtype=int)
    ics = []
    for k in range(n_folds):
        s = seg.iloc[edges[k]:edges[k + 1]]
        if len(s) < 100:
            continue
        ics.append(float(spearmanr(s.iloc[:, 0], s.iloc[:, 1]).statistic))
    return {"folds_ic": [round(x, 4) for x in ics],
            "positive_frac": round(float(np.mean([x > 0 for x in ics])), 3),
            "n_folds": len(ics)}


def _cost_stress(f: pd.Series, m1t: pd.DataFrame, h: dict, cost_cfg: dict) -> dict:
    """转规则信号（方向 = expected_direction；连续特征按符号）→ 成本压力 1x/2x/3x。
    bugfix 2026-09-04：f 与 close 必须同索引（统一以 m1t ts_utc 为基准）。"""
    from research_engine.core.backtest import BacktestEngine
    from research_engine.core.cost import CostModel
    from research_engine.validation.cost_stress import run_cost_stress
    base = m1t.set_index("ts_utc")
    # f 若为 RangeIndex 则按位置映射到 ts_utc
    f2 = f.copy()
    if not isinstance(f2.index, pd.DatetimeIndex):
        f2.index = base.index[: len(f2)]
    m = pd.concat([f2, base["close"]], axis=1).dropna()
    sig = m.iloc[:, 0]
    close = m.iloc[:, 1]
    # 持仓与 hypothesis 登记的 holding period 一致：每 holding 根 bar 才允许更新一次
    # （决策在当期收盘 → 下一根生效；由 BacktestEngine 的滞后约定保证）
    hold = int(h.get("holding", 60))
    raw = np.sign(sig).clip(-1, 1).values
    pos_arr = np.zeros(len(sig))
    pos_arr[::hold] = raw[::hold]
    # 前向填充：两次更新之间保持持仓
    last = 0.0
    for i in range(len(pos_arr)):
        if pos_arr[i] != 0.0 or i % hold == 0:
            last = pos_arr[i]
        pos_arr[i] = last
    pos = pd.Series(pos_arr, index=sig.index)
    cm = CostModel(**cost_cfg)
    bt = BacktestEngine(cost_model=cm)
    res = bt.run(close, pos, name=h["hypothesis_id"])
    net = res.df["net_r"].values
    gross = res.df["gross_r"].values
    posv = res.df["position"].values
    stress = run_cost_stress(gross, posv, cm.one_way_cost, multipliers=(1.0, 2.0, 3.0))
    from research_engine.statistics.robustness import subperiod_stability
    sub = subperiod_stability(net, n_parts=4)
    return {"1x": stress["1x"]["sharpe_annualized"], "2x": stress["2x"]["sharpe_annualized"],
            "3x": stress["3x"]["sharpe_annualized"], "net_total": res.metrics["net_total_return"],
            "n_trades": res.metrics["n_trades"], "subperiod": sub}


def _decide(r: dict) -> str:
    """垃圾 Alpha 淘汰器（§16）：OOS + FDR + WF + cost + subperiod 全过 → SUPPORTED。"""
    ic = r["perm"]["ic_oos"]
    exp = r["hypothesis"]["expected_direction"]
    if exp in ("+", "-"):
        want = 1 if exp == "+" else -1
        dir_ok = bool(np.sign(ic) == want) and abs(ic) > 0.005
    else:
        dir_ok = abs(ic) > 0.01
    wf_ok = (r.get("wf") or {}).get("positive_frac", 0) >= 0.8
    cs = r.get("cost_stress")
    cs_ok = cs is not None and cs["3x"] > 0 and cs["1x"] > 1.0
    sub_ok = cs is not None and cs["subperiod"]["sharpe_positive_frac"] >= 0.75
    if dir_ok and wf_ok and cs_ok and sub_ok:
        return "SUPPORTED"
    if (dir_ok or abs(ic) > 0.01) and (wf_ok or cs_ok):
        return "EDGE_UNCERTAIN"
    return "REJECTED"


def _git() -> str:
    import subprocess
    from pathlib import Path
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(Path(__file__).resolve().parents[1]),
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "no-git"
    except Exception:
        return "no-git"
