# -*- coding: utf-8 -*-
"""market_understanding/autopsy.py — 市场事件尸检原型。

对每个事件输出时间线：事件前 60m → 后 60m 内各观测变量的轨迹与“领先顺序”，
并给出 Primary/Secondary/Rejected 解释（基于观测时序证据，不冒充因果）。
变量：rvol30 / activity30 / spread / |mid move| / 前状态 / 状态转移。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _onset_min(vals_pre: np.ndarray, thr_pct: float = 0.9) -> float | None:
    """事件前 60m 轨迹中首次超过自身 pct 阈值的分钟（相对事件起点，负值=领先）。"""
    base = np.percentile(vals_pre, 50)
    thr = base + (np.percentile(vals_pre, thr_pct * 100) - base)
    for i, v in enumerate(vals_pre):
        if v >= thr:
            return float(i - len(vals_pre))
    return None


def autopsy_one(d: pd.DataFrame, ev: dict, lookback: int = 60, lookahead: int = 60,
                state_labels: np.ndarray | None = None) -> dict:
    """d: 带 close/spread/volume(可选) 的 M1 df（ts_utc 升序）；ev: 事件行。"""
    d = d.sort_values("ts_utc").reset_index(drop=True)
    ts = pd.DatetimeIndex(d["ts_utc"])
    t_mid = pd.Timestamp(ev["t_mid"])
    pos = int(np.searchsorted(ts, t_mid))
    lo = max(0, pos - lookback)
    hi = min(len(d), pos + lookahead)
    seg = d.iloc[lo:hi].reset_index(drop=True)
    r = seg["close"].pct_change().fillna(0.0)
    seg["rvol"] = r.rolling(30).std(ddof=1)
    if "volume" in seg.columns:
        seg["act"] = seg["volume"].rolling(30).sum()
    if "spread" in seg.columns:
        seg["spread"] = seg["spread"]
    seg["cumret"] = seg["close"] / seg["close"].iloc[0] - 1.0
    k = int(np.searchsorted(ts, t_mid)) - lo
    pre = seg.iloc[max(0, k - lookback):k]
    post = seg.iloc[k:min(len(seg), k + lookahead)]
    timeline = {}
    for var in ("rvol", "act", "spread", "cumret"):
        if var in seg.columns:
            vals = seg[var].astype(float)
            timeline[var] = {
                "pre_last": float(vals.iloc[max(0, k - 1)]) if k > 0 else float("nan"),
                "post_max": float(vals.iloc[1:].max()) if len(post) > 1 else float("nan"),
                "post_mean": float(post[var].mean()) if len(post) else float("nan"),
                "onset_min_rel": _onset_min(vals.iloc[max(0, k - lookback):k].values) if k >= 15 else None,
            }
    record = {
        "event": {"t_mid": str(t_mid), "dir": ev["direction"], "ret_pct": float(ev["abs_ret_pct"]),
                  "session": ev.get("session"), "k_sigma": float(ev["k_sigma"])},
        "prior_state": int(state_labels[pos - 1]) if state_labels is not None and pos > 0 else None,
        "post_state": int(state_labels[min(pos + 30, len(state_labels) - 1)]) if state_labels is not None else None,
        "timeline": timeline,
    }
    return record


def autopsies_markdown(d, events: pd.DataFrame, state_labels=None, max_events: int = 8) -> str:
    lines = ["# XAUUSD Market Autopsy（原型：观测时序证据，非因果断言）", ""]
    for _, ev in events.head(max_events).iterrows():
        rec = autopsy_one(d, ev, state_labels=state_labels)
        lines.append(f"## Event {str(ev['t_mid'])}  {ev['direction']} {ev['abs_ret_pct']:.2f}% "
                     f"(session {ev.get('session')}, {ev['k_sigma']:.1f}σ)")
        lines.append(f"- prior state: {rec['prior_state']} → post(+30m) state: {rec['post_state']}")
        tl = rec["timeline"]
        lines.append("| var | pre-last | post-mean | onset(rel min) |")
        lines.append("|---|---|---|---|")
        for v, s in tl.items():
            lines.append(f"| {v} | {s['pre_last']:.4g} | {s['post_mean']:.4g} | {s['onset_min_rel']} |")
        # 领先排序（越早 onset 越“先动”）
        onsets = {v: s["onset_min_rel"] for v, s in tl.items() if s.get("onset_min_rel") is not None}
        order = sorted(onsets, key=onsets.get)
        if order:
            lines.append("")
            lines.append("观测领先顺序（事件前 60m 内变量自阈值升起的先后）：" +
                         " → ".join(f"{v}({onsets[v]:.0f}m)" for v in order))
        lines.append("")
        lines.append("*注意：领先顺序仅描述观测先后；无外生工具变量时不构成因果证明。*")
        lines.append("")
    return "\n".join(lines)
