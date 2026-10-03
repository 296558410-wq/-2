# -*- coding: utf-8 -*-
"""phase6_autopsy_demo.py — Market Autopsy 原型演示（FXTM 2026 M1 窗口）。

事件：30m |return| > 3×σ30；输出前 8 个事件的尸检 markdown。
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from market_understanding.events import detect_events
from market_understanding.autopsy import autopsies_markdown

df, _ = data_registry.load_dataset("XAUUSD_M1_MT5-FXTM-Live_20260904_v001")
df = df.sort_values("ts_utc").reset_index(drop=True)

states = json.load(open("C:/AIQuant/reports/phase6_states.json", encoding="utf-8"))
labels_named = states["FXTM_2026"]["labels_named"]
state_map = {s: i for i, s in enumerate(sorted(set(labels_named)))}
labels_int = [state_map[s] for s in labels_named]

ev = detect_events(df, window=30, k_sigma=3.0, min_gap=60)
print(f"events detected: {len(ev)}")
md = autopsies_markdown(df, ev, state_labels=np.array(labels_int) if labels_int else None, max_events=8)
open("C:/AIQuant/reports/phase6_autopsy_sample.md", "w", encoding="utf-8").write(md)
print(md[:2500])
