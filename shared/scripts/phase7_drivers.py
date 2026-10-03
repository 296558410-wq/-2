# -*- coding: utf-8 -*-
"""phase7_drivers.py — “谁在推动 / 为什么转换” 证据研究（Phase 7）。

证据 1：宏观日历重叠周（2026-08-31..09-04，faireconomy/FF）事件窗口 vs 非事件窗口
        （vol/activity/spread/状态转换发生率）→ 定时信息到达是否是转换驱动之一
证据 2：全窗口小时锚点风险剖面（FXTM 2026 & DUKA 2023-24 互证）：
        压力态进入的相对风险按 UTC 小时 → 是否聚集于宏观定时窗口(12:30-15:00)与开盘/定盘
证据 3（tick 23d）：事件前后 1 分钟粒度 tick-spread/activity/flow 的先后顺序（领先-滞后不对称）
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.core.dataquality import session_of

OUT = Path("C:/AIQuant/reports")

# ---------------- 证据 1：日历重叠周 ----------------
cal = json.load(open("C:/AIQuant/data/staging_mt5/ff_cal.json", encoding="utf-8"))
events = []
for e in cal:
    try:
        t = datetime.fromisoformat(e["date"]).astimezone(timezone.utc)
    except Exception:
        continue
    imp = str(e.get("impact", "")).lower()
    if imp in ("high", "medium") and e.get("country") in ("USD", "All", "EUR", "CNY", "GBP"):
        events.append({"ts": t, "title": e["title"], "impact": imp, "country": e["country"]})
ev = pd.DataFrame(events).sort_values("ts").reset_index(drop=True)
print(f"calendar events (>=Med, relevant): {len(ev)}")

# FXTM M1 + micro bars 对齐窗口
m1, _ = data_registry.load_dataset("XAUUSD_M1_MT5-FXTM-Live_20260904_v001")
m1 = m1.sort_values("ts_utc").reset_index(drop=True)
micro = pd.read_parquet("C:/AIQuant/data/staging_fxtm/micro_m1_bars.parquet")
micro = micro.sort_values("ts_utc").reset_index(drop=True)
wk = m1[(m1["ts_utc"] >= "2026-08-31") & (m1["ts_utc"] < "2026-09-05")].reset_index(drop=True)
mwk = micro[(micro["ts_utc"] >= "2026-08-31") & (micro["ts_utc"] < "2026-09-05")].reset_index(drop=True)

close = wk.set_index("ts_utc")["close"]
r = close.pct_change()
rvol = r.rolling(30).std(ddof=1)
ts_idx = close.index
in_win = np.zeros(len(ts_idx), dtype=bool)
for _, e in ev.iterrows():
    t0 = e["ts"] - timedelta(minutes=15)
    t1 = e["ts"] + timedelta(minutes=15)
    in_win |= ((ts_idx >= t0) & (ts_idx < t1)).astype(bool)

# 状态：rvol>p85(全窗滚动) → 压力分钟
stress = (rvol > rvol.rolling(1440).quantile(0.85)).fillna(False)
res1 = {
    "n_events": int(len(ev)),
    "event_minutes": int(in_win.sum()),
    "stress_frac_in_event_win": float(stress[in_win].mean()),
    "stress_frac_out_event_win": float(stress[~in_win].mean()) if (~in_win).sum() else float("nan"),
    "rvol_med_event_win": float(rvol[in_win].median()),
    "rvol_med_baseline": float(rvol[~in_win].median()),
}
# activity/spread 仅在 micro 窗（有 tick 覆盖周内分钟）
mc = mwk.set_index("ts_utc")
if len(mc):
    mc_idx = mc.index
    in_w2 = np.zeros(len(mc_idx), dtype=bool)
    for _, e in ev.iterrows():
        t0 = e["ts"] - timedelta(minutes=15)
        t1 = e["ts"] + timedelta(minutes=15)
        in_w2 |= ((mc_idx >= t0) & (mc_idx < t1)).astype(bool)
    res1["tick_act_med_event"] = float(mc["tick_count"][in_w2].median())
    res1["tick_act_med_base"] = float(mc["tick_count"][~in_w2].median())
    res1["spread_med_event"] = float(mc["spread_mean"][in_w2].median())
    res1["spread_med_base"] = float(mc["spread_mean"][~in_w2].median())
print("E1:", json.dumps(res1, ensure_ascii=False), flush=True)

# ---------------- 证据 2：小时锚点压力进入风险（两窗口） ----------------
def hour_risk(ds_id):
    df, _ = data_registry.load_dataset(ds_id)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    close = df["close"]
    r = close.pct_change()
    rvol = r.rolling(30).std(ddof=1)
    stress = (rvol > rvol.rolling(1440).quantile(0.85)).fillna(False)
    entry = stress & ~stress.shift(1).fillna(False)
    h = pd.DatetimeIndex(df["ts_utc"]).hour
    base_min = pd.Series(1.0, index=df.index).groupby(h.values).sum()
    entry_cnt = entry.groupby(h.values).sum()
    rr = (entry_cnt / base_min) / (entry_cnt.sum() / base_min.sum())
    return rr, entry_cnt, base_min

rr_f, ec_f, bm_f = hour_risk("XAUUSD_M1_MT5-FXTM-Live_20260904_v001")
rr_d, ec_d, bm_d = hour_risk("XAUUSD_M1_Dukascopy-HTTP_20260904_v001")
print("E2 FXTM hourly RR:", json.dumps({int(k): round(float(v), 2) for k, v in rr_f.items()}), flush=True)
print("E2 DUKA hourly RR:", json.dumps({int(k): round(float(v), 2) for k, v in rr_d.items()}), flush=True)
res2 = {
    "FXTM_rr": {int(k): round(float(v), 2) for k, v in rr_f.items()},
    "DUKA_rr": {int(k): round(float(v), 2) for k, v in rr_d.items()},
    "anchor_12_15_mean_rr": {
        "FXTM": round(float(rr_f.loc[12:15].mean()), 2),
        "DUKA": round(float(rr_d.loc[12:15].mean()), 2)},
}

# ---------------- 证据 3：tick 级领先-滞后（压力进入前 10m 轨迹） ----------------
mic = micro.set_index("ts_utc")
mics = mic.sort_index()
# 1 分钟压力态（用 micro 自带 rvol? 无 rvol 列 → 用 |mid_ret| 滚动）
mr = mics["mid_last"].pct_change()
mvol = mr.rolling(10).std(ddof=1)
st = (mvol > mvol.rolling(1440).quantile(0.85)).fillna(False)
entries = np.where((st.values) & (~np.roll(st.values, 1)))[0]
pre, post = 10, 10
seqs = {"spread": [], "act": [], "absret": []}
for e0 in entries:
    if e0 < pre or e0 + post >= len(mics):
        continue
    seg = mics.iloc[e0 - pre: e0 + post]
    seqs["spread"].append(seg["spread_mean"].values)
    seqs["act"].append(seg["tick_count"].values)
    seqs["absret"].append(seg["mid_last"].pct_change().abs().values)
res3 = {"n_entries": int(len(entries))}
if len(entries) > 20:
    for k, v in seqs.items():
        arr = np.nanmean(np.vstack(v), axis=0)
        res3[f"{k}_pre10_mean"] = round(float(arr[:pre].mean()), 6)
        res3[f"{k}_pre1"] = round(float(arr[pre - 1]), 6)
        res3[f"{k}_post1"] = round(float(arr[pre]), 6)
        res3[f"{k}_post5_mean"] = round(float(arr[pre:pre + 5].mean()), 6)
        # 领先判定：pre 段斜率 vs post 段（标准化相对自身）
        res3[f"{k}_pre_rise"] = round(float((arr[pre - 1] - arr[0]) / (arr[:pre].std() + 1e-12)), 2)
print("E3:", json.dumps(res3, ensure_ascii=False), flush=True)

rep = {"evidence1_calendar_week": res1, "evidence2_hour_anchor": res2,
       "evidence3_tick_leadlag": res3}
json.dump(rep, open(OUT / "phase7_drivers_evidence.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("phase7 evidence done")
