# -*- coding: utf-8 -*-
"""normalize_register.py — 服务器时间 → UTC（-3h）→ 质检 → data_registry 注册。"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "C:/AIQuant")
from research_engine.core import data_registry
from research_engine.core.dataquality import run_quality_gate

STAGING = Path("C:/AIQuant/data/staging_mt5")
SERVER_OFFSET_H = 3  # FXTM Live UTC+3（2026-09 验证）


def load_norm(tf_name: str) -> pd.DataFrame:
    raw = pd.read_parquet(STAGING / f"XAUUSD_{tf_name}_server.parquet")
    df = raw.rename(columns={"time": "ts_server"}).copy()
    df["ts_utc"] = df["ts_server"] - pd.Timedelta(hours=SERVER_OFFSET_H)
    df["symbol"] = "XAUUSD"
    df["source"] = "MT5-FXTM-Live"
    df["spread_points"] = df["spread"].astype(int)
    df["spread"] = df["spread_points"] * 0.01  # point=0.01 USD
    out = df[["ts_utc", "symbol", "open", "high", "low", "close",
              "tick_volume", "spread", "spread_points"]].sort_values("ts_utc").reset_index(drop=True)
    return out


for tf_name, freq in (("M1", "1min"), ("M5", "5min"), ("H1", "1h")):
    df = load_norm(tf_name)
    qc = run_quality_gate(df, symbol="XAUUSD", timeframe=tf_name,
                          expected_freq=freq, has_spread=True)
    print(f"== {tf_name}: rows={qc['n']:,} range={qc['range']['start']} -> {qc['range']['end']}")
    print(f"   gate_passed={qc['gate_passed']} dup={qc['duplicates']} missing={qc['missing_bars']} "
          f"abnormal_gaps={qc['abnormal_gaps']} ohlc_ok={qc['ohlc_ok']}")
    print(f"   spread: n_nonpos={qc['spread']['n_nonpos']} mean={qc['spread']['mean']:.4f} "
          f"p99={qc['spread']['p99']:.4f} spikes={qc['spread'].get('spike_count', 0)}")
    print(f"   sessions: {qc['sessions']}")
    if qc["gate_passed"]:
        meta = data_registry.register_dataset(
            df, source="MT5-FXTM-Live", symbol="XAUUSD", timeframe=tf_name,
            extra={"server_offset_hours": SERVER_OFFSET_H,
                   "staging": str(STAGING / f"XAUUSD_{tf_name}_server.parquet"),
                   "note": "FXTM Live server history retention; spread=points*0.01 USD",
                   "qc": {k: qc[k] for k in ("duplicates", "missing_bars", "abnormal_gaps",
                                             "ohlc_ok", "gate_passed")}})
        print(f"   REGISTERED: {meta['dataset_id']} sha256={meta['sha256'][:16]}…")
    else:
        print(f"   !! QC FAILED — 未注册；人工检查 {tf_name}")
