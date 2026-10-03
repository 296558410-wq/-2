# -*- coding: utf-8 -*-
"""phase6_states.py — Market State 发现与分析（FXTM 2026 + DUKA 2023-24）。

输出：state 档案/转移/持续 → reports/phase6_states.json + 简要文本
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from market_understanding.state import (build_state_features_notime, fit_states_gmm,
                                        state_profiles, transition_matrix)

WINDOWS = {
    "FXTM_2026": ("XAUUSD_M1_MT5-FXTM-Live_20260904_v001", dict(act_col="tick_volume", spread_col="spread")),
    "DUKA_2023_24": ("XAUUSD_M1_Dukascopy-HTTP_20260904_v001", dict(spread_col="spread")),
}

out = {}
for name, (ds_id, kw) in WINDOWS.items():
    df, meta = data_registry.load_dataset(ds_id)
    df = df.sort_values("ts_utc").reset_index(drop=True)
    Z = build_state_features_notime(df, **kw)
    fit = fit_states_gmm(Z, k_range=range(2, 7), seed=42)
    labels = fit["labels"]
    prof = state_profiles(df.iloc[Z.index], labels)
    tr = transition_matrix(labels)
    # 状态标签描述（按 rvol 排序命名 S0..）
    prof = prof.sort_values("rvol30_med").reset_index(drop=True)
    rename = {int(r["state"]): f"S{new}" for new, r in prof.iterrows()}
    labels_named = np.array([rename[int(x)] for x in labels])
    prof["state"] = [rename[int(r["state"])] for _, r in prof.iterrows()]
    out[name] = {
        "k": fit["k"], "bic": float(fit["bic"]),
        "state_share": {s: float((labels_named == s).mean()) for s in prof["state"]},
        "profiles": prof.to_dict(orient="records"),
        "transition": {str(rename[int(a)]): {str(rename[int(b)]): round(v, 3)
                       for b, v in enumerate(row)} for a, row in enumerate(tr["matrix"])},
        "persistence": {str(rename[int(i)]): round(p, 3) for i, p in enumerate(tr["persistence"])},
        "mean_duration_min": {str(rename[int(i)]): (round(v, 1) if np.isfinite(v) else None)
                              for i, v in enumerate(tr["mean_duration_min"])},
        "labels_named": labels_named.tolist(),
    }
    print(f"[{name}] k={fit['k']}")
    print(prof.round(4).to_string(), flush=True)
    print("transition:", json.dumps(out[name]["transition"], ensure_ascii=False), flush=True)
    print("persistence:", json.dumps(out[name]["persistence"], ensure_ascii=False),
          "| mean_dur_min:", json.dumps(out[name]["mean_duration_min"], ensure_ascii=False), flush=True)

json.dump(out, open("C:/AIQuant/reports/phase6_states.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
print("states done")
