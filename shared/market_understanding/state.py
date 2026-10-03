# -*- coding: utf-8 -*-
"""market_understanding/state.py — 数据驱动市场状态发现与分析。

状态向量（每根 M1 收盘时已知，无前视）：
  rvol30(log) / activity30(log, 若有 volume) / spread_z(480) /
  |mom30| 标准化 / 日内时刻(sin/cos)
方法：GMM（sklearn）在 train 段按 BIC 选 k，全样本贴标签（固定 seed 可复现）。
输出：状态档案（条件分布）、持续性、转移矩阵、状态条件前瞻分布。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


def build_state_features(df: pd.DataFrame, vol_col: str = "close",
                         vol_window: int = 30, act_col: str | None = None,
                         spread_col: str | None = None,
                         spread_win: int = 480) -> pd.DataFrame:
    """df 需 ts_utc 升序 + close（+可选 volume/spread）。返回标准化状态特征。"""
    out = pd.DataFrame(index=df.index)
    r = df[vol_col].pct_change()
    rvol = r.rolling(vol_window).std(ddof=1)
    out["log_rvol"] = np.log(rvol + 1e-12)
    mom = (df[vol_col] / df[vol_col].shift(30) - 1.0)
    out["abs_mom"] = np.abs(mom)
    if act_col and act_col in df.columns:
        act = df[act_col].rolling(vol_window).sum()
        out["log_act"] = np.log(act + 1.0)
    if spread_col and spread_col in df.columns:
        sp = df[spread_col]
        mu = sp.rolling(spread_win).mean()
        sd = sp.rolling(spread_win).std(ddof=1)
        out["spread_z"] = (sp - mu) / sd
    # 标准化（逐列）
    out = (out - out.mean()) / (out.std(ddof=1) + 1e-12)
    return out.dropna()


def build_state_features_notime(df, vol_col="close", vol_window=30,
                                act_col=None, spread_col=None, spread_win=480):
    """不含日内时刻的状态特征（避免时间特征主导状态分离）。"""
    out = pd.DataFrame(index=df.index)
    r = df[vol_col].pct_change()
    rvol = r.rolling(vol_window).std(ddof=1)
    out["log_rvol"] = np.log(rvol + 1e-12)
    mom = (df[vol_col] / df[vol_col].shift(30) - 1.0)
    out["abs_mom"] = np.abs(mom)
    out["log_range"] = np.log((df["high"] - df["low"]) / df[vol_col] + 1e-12)
    if act_col and act_col in df.columns:
        out["log_act"] = np.log(df[act_col].rolling(vol_window).sum() + 1.0)
    if spread_col and spread_col in df.columns:
        sp = df[spread_col]
        mu = sp.rolling(spread_win).mean()
        sd = sp.rolling(spread_win).std(ddof=1)
        out["spread_z"] = (sp - mu) / sd
    out = (out - out.mean()) / (out.std(ddof=1) + 1e-12)
    return out.dropna()


def fit_states_gmm(Z: pd.DataFrame, k_range=range(2, 8), seed: int = 0,
                   train_frac: float = 0.6) -> dict:
    """BIC 选 k；返回 {k, bic, labels(全样本), model, train_frac}。"""
    n = len(Z)
    cut = int(n * train_frac)
    Ztr = Z.iloc[:cut].values
    best = None
    for k in k_range:
        m = GaussianMixture(n_components=k, covariance_type="full",
                            random_state=seed, n_init=3, max_iter=300)
        m.fit(Ztr)
        bic = m.bic(Ztr)
        if best is None or bic < best["bic"]:
            best = {"k": k, "bic": bic, "model": m}
    labels = best["model"].predict(Z.values)
    return {"k": best["k"], "bic": best["bic"], "model": best["model"],
            "labels": labels, "train_frac": train_frac, "n": n}


def state_profiles(df: pd.DataFrame, labels: np.ndarray,
                   horizons=(30, 60)) -> pd.DataFrame:
    """每个状态的档案：条件均值（关键变量 + 前瞻 vol/|ret|/spread）+ 占比/持续。"""
    d = df.reset_index(drop=True) if "ts_utc" not in df.columns else df.reset_index(drop=True)
    close = d["close"]
    r = close.pct_change()
    rows = []
    k = int(labels.max()) + 1
    for s in range(k):
        mask = labels == s
        seg = d[mask]
        act_col = "tick_volume" if "tick_volume" in d.columns else ("volume" if "volume" in d.columns else None)
        row = {"state": s, "n_min": int(mask.sum()),
               "share": round(float(mask.mean()), 3),
               "rvol30_med": float(r.rolling(30).std(ddof=1)[mask].median()),
               "spread_med": float(d["spread"][mask].median()) if "spread" in d else float("nan"),
               "act_med": float(d[act_col].rolling(30).sum()[mask].median()) if act_col else float("nan")}
        for h in horizons:
            fv = r.rolling(h).std(ddof=1).shift(-h)
            fr = close.shift(-h) / close - 1.0
            row[f"fwd_vol{h}_med"] = float(fv[mask].median())
            row[f"fwd_absret{h}_med"] = float(fr[mask].abs().median())
            row[f"fwd_ret{h}_mean"] = float(fr[mask].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def transition_matrix(labels: np.ndarray) -> dict:
    """经验转移矩阵（行=当前状态，列=下一状态）+ 持续性统计。"""
    k = int(labels.max()) + 1
    T = np.zeros((k, k))
    for a, b in zip(labels[:-1], labels[1:]):
        T[a, b] += 1
    rowsum = T.sum(axis=1, keepdims=True)
    T = T / np.where(rowsum > 0, rowsum, 1.0)
    persist = [float(T[i, i]) for i in range(k)]
    mean_dur = [float(1.0 / (1.0 - T[i, i])) if T[i, i] < 1 else np.inf for i in range(k)]
    return {"matrix": T.tolist(), "persistence": persist, "mean_duration_min": mean_dur}
