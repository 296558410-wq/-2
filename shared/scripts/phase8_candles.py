# -*- coding: utf-8 -*-
"""phase8_candles.py — Candlestick 行为研究（框架先行，Phase 8）。

E1 描述：蜡烛特征刻画已实现趋势状态（描述性）
E2 变化识别：蜡烛特征 vs 基线 → 未来 k 根结构破坏的 OOS AUC（非重叠块）
E3 增量预测：动量基线上加蜡烛特征 → ΔIC（block bootstrap，OOS 非重叠入场）
E4 形态×阶段条件表（FXTM M5，描述性+有限检验）
E5 尺度对照：M1/M5/H1 的 E3 ΔIC
源：FXTM 2026 M1/M5/H1 与 DUKA 2023-24 M1（M5/H1 由 M1 派生）
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.features.candles import shape_frame, swing_structure
from research_engine.statistics.overlap import block_permutation_p

OUT = Path("C:/AIQuant/reports")
H = 15  # 主 horizon（bars）


def load(tf="M1", source="MT5-FXTM-Live"):
    ds = data_registry.find_dataset("XAUUSD", tf, source=source)[-1]
    df, _ = data_registry.load_dataset(ds["dataset_id"])
    return df.sort_values("ts_utc").reset_index(drop=True)


def prep(df, L=10, h=H):
    sh = shape_frame(df)
    sw = swing_structure(df, L)
    X = pd.concat([sh, sw], axis=1)
    close = df["close"]
    r = close.pct_change()
    fwd = close.shift(-h) / close - 1.0
    # 动量基线特征
    X["mom5"] = close / close.shift(5) - 1
    X["mom10"] = close / close.shift(10) - 1
    X["mom30"] = close / close.shift(30) - 1
    X["rvol30"] = r.rolling(30).std(ddof=1)
    # 描述性标签：过去 30 根 drift 方向（已实现）
    X["past_drift30"] = close / close.shift(30) - 1.0
    return X, fwd


def nonoverlap_oos(df_in, frac=0.6, block=H):
    n = len(df_in)
    cut = int(n * frac)
    idx = np.arange(cut, n - block, block)
    return idx


# ---------------- 主循环 ----------------
report = {}
for source, tag in (("MT5-FXTM-Live", "FXTM2026"), ("Dukascopy-HTTP", "DUKA2023")):
    df = load("M1", source)
    X, fwd = prep(df)
    m = pd.concat([X, fwd.rename("fwd")], axis=1).dropna()
    n = len(m)
    cut = int(n * 0.6)
    ei = nonoverlap_oos(m, 0.6, H)
    m_oos = m.iloc[ei]
    # ---- E1 描述：蜡烛特征 vs 已实现过去趋势 ----
    e1 = {}
    for f in ("body_frac", "close_pos", "marubozu", "upper_wick", "lower_wick"):
        e1[f] = round(float(spearmanr(m[f].values, m["past_drift30"].values).statistic), 4)
    # ---- E2 变化识别：未来 H*2 根内结构破坏（方向相关） ----
    lab_break = ((m["trend_dir"].shift(-H).fillna(0) > 0) & (m["breakout_dn"].rolling(2 * H).max().shift(-2 * H) > 0)) | \
                ((m["trend_dir"].shift(-H).fillna(0) < 0) & (m["breakout_up"].rolling(2 * H).max().shift(-2 * H) > 0))
    # 简化：任何与当前方向相反的结构突破（未来 2H 内）
    lab = pd.Series(0.0, index=m.index)
    m2 = m.copy()
    for i in range(len(m) - 2 * H):
        d = m2["trend_dir"].iloc[i]
        if d > 0 and m2["breakout_dn"].iloc[i + 1:i + 2 * H + 1].max() > 0:
            lab.iloc[i] = 1.0
        elif d < 0 and m2["breakout_up"].iloc[i + 1:i + 2 * H + 1].max() > 0:
            lab.iloc[i] = 1.0
    m2["lab_break"] = lab
    feat_change = ["body_eff_z", "wick_z", "range_z", "close_pos", "doji"]
    e2 = {}
    for f in feat_change:
        mm = m2[[f, "lab_break"]].dropna()
        if mm["lab_break"].sum() < 20:
            continue
        cut2 = int(len(mm) * 0.6)
        tr, te = mm.iloc[:cut2], mm.iloc[cut2:]
        clf = LogisticRegression(max_iter=300)
        clf.fit(tr[[f]].values, tr["lab_break"].values)
        auc = roc_auc_score(te["lab_break"].values, clf.predict_proba(te[[f]].values)[:, 1])
        # 非重叠块置换 p（块=H）
        idxb = nonoverlap_oos(te, 0.0, H) if len(te) > 3 * H else np.arange(0, len(te) - H, H)
        yb = te["lab_break"].values
        xb = te[f].values
        rng = np.random.default_rng(3)
        dist = np.empty(200)
        for i in range(200):
            yp = rng.permutation(yb[idxb])
            if yp.sum() in (0, len(yp)):
                dist[i] = 0.5
            else:
                dist[i] = roc_auc_score(yp, xb[idxb])
        pv = float((dist >= auc).mean())
        e2[f] = {"auc": round(auc, 3), "p_block": round(pv, 3), "n": int(len(te))}
    # ---- E3 增量预测（非重叠 OOS 入场，IC of features） ----
    e3 = {}
    momf = ["mom5", "mom10", "mom30"]
    canf = ["body_frac", "close_pos", "upper_wick", "lower_wick", "body_eff_z",
            "range_z", "marubozu", "doji", "engulf_up", "engulf_dn"]
    for f in momf + canf:
        e3[f] = round(float(spearmanr(m_oos[f].values, m_oos["fwd"].values).statistic), 5)
    # 基线（mom 组合 IC）vs +蜡烛（等权标准化组合）——用简单 OLS 在 train 拟合权重，OOS 算 IC
    from sklearn.linear_model import LinearRegression
    mtr = m.iloc[:cut]
    mte = m.iloc[ei]
    rng = np.random.default_rng(1)
    # baseline model: mom features
    def combo_ic(feats):
        lr = LinearRegression()
        lr.fit(mtr[feats].values, mtr["fwd"].values)
        pred = lr.predict(mte[feats].values)
        return float(spearmanr(pred, mte["fwd"].values).statistic), pred
    ic_base, pred_base = combo_ic(momf)
    ic_full, pred_full = combo_ic(momf + canf)
    # paired block bootstrap of ΔIC
    n_te = len(mte)
    blocks = np.arange(0, n_te - H, H)
    nb = len(blocks)
    obs_delta = ic_full - ic_base
    dist = np.empty(300)
    for i in range(300):
        sel = rng.integers(0, nb, nb)
        sel_idx = np.concatenate([np.arange(blocks[b], blocks[b] + H) for b in sel])
        sel_idx = sel_idx[sel_idx < n_te]
        d_base = float(spearmanr(pred_base[sel_idx], mte["fwd"].values[sel_idx]).statistic)
        d_full = float(spearmanr(pred_full[sel_idx], mte["fwd"].values[sel_idx]).statistic)
        dist[i] = d_full - d_base
    e3["ic_mom_base"] = round(ic_base, 5)
    e3["ic_mom_candle"] = round(ic_full, 5)
    e3["delta_ic"] = round(obs_delta, 5)
    e3["delta_ic_ci95"] = [round(float(np.percentile(dist, 2.5)), 5),
                           round(float(np.percentile(dist, 97.5)), 5)]
    e3["n_oos_entries"] = int(n_te)
    report[tag] = {"n_bars": n, "E1_descriptive": e1, "E2_change_detection": e2,
                   "E3_incremental_IC": e3}
    print(f"[{tag}] E3 delta_ic={e3['delta_ic']} ci={e3['delta_ic_ci95']} "
          f"(base {e3['ic_mom_base']} → full {e3['ic_mom_candle']})", flush=True)
    print(f"[{tag}] E2:", json.dumps(e2, ensure_ascii=False), flush=True)

# ---- E4 形态×阶段（FXTM M5） ----
df5 = load("M5", "MT5-FXTM-Live")
X5, fwd5 = prep(df5, L=8, h=15)
m5 = pd.concat([X5, fwd5.rename("fwd")], axis=1).dropna()
e4 = {}
for pat in ("doji", "hammer", "shooting_star", "marubozu", "engulf_up", "engulf_dn", "inside_bar"):
    cell = {}
    for dname, dval in (("up", 1.0), ("dn", -1.0), ("flat", 0.0)):
        mask = (m5["trend_dir"] == dval) & (m5[pat] == 1)
        if mask.sum() > 100:
            cell[dname] = {"n": int(mask.sum()),
                           "fwd_mean_bp": round(float(m5["fwd"][mask].mean() * 1e4), 2),
                           "uncond_bp": round(float(m5["fwd"][m5["trend_dir"] == dval].mean() * 1e4), 2)}
    e4[pat] = cell
report["E4_pattern_x_trend_M5_FXTM"] = e4
print("E4 done")

json.dump(report, open(OUT / "phase8_candles_evidence.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("phase8 done")
