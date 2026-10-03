# -*- coding: utf-8 -*-
"""phase3_run_duka.py — 用同一冻结 R1 registry 在 DUKA 2023-24 窗口复验。"""
import json
import sys
import time

sys.path.insert(0, "C:/AIQuant")
from pathlib import Path

import alpha_engine.pipeline as P

# DUKA 窗口成本校准（spread≈$0.49@$2050 ≈ 2.4bp；滑点 0.3bp）
P.XAUUSD_COST = {"spread_bps": 2.4, "commission_bps": 0.0, "slippage_bps": 0.3}

t0 = time.perf_counter()
rep = P.run_round("XAUUSD_M1_Dukascopy-HTTP_20260904_v001",
                  n_perm=800, n_boot=600, train_frac=0.6, backend="auto")
rep["wall_s"] = round(time.perf_counter() - t0, 1)
rep["period"] = "2023-09..2024-03"
Path("C:/AIQuant/reports/round1_duka2023_details.json").write_text(
    json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print("duka round done", rep["wall_s"], "s; funnel:", rep["funnel"],
      "; registry:", rep["alpha_registry"]["by_status"])
