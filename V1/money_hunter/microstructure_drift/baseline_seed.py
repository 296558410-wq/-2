# -*- coding: utf-8 -*-
"""microstructure_drift/baseline_seed.py — 用已存在的历史数据建立微结构基准 (确定性, 零预算)

数据考古原则: 只读已有 parquet, 不购买任何数据, 不用 volume 伪装 signed flow。
来源 (均为已存在资产):
  - data/staging_fxtm/ticks_*.parquet  — FXTM XAUUSD 报价 (与 live 采集同源同 feed)
  - data/staging_duka/assembled/ticks_*.parquet — DUKA assembled (bi5 报价, 跨年参考层)
输出:
  - baseline_seed/fxtm_daily.json       — 逐日指标 (同源 feed 基准主层)
  - baseline_seed/duka_daily.json       — 逐日指标 (DUKA 参考层, 不混入主基准)
  - BASELINE.yaml                       — 三窗口(短期/中期/长期)滚动基准快照
用法: .venv/Scripts/python.exe research/money_hunter/microstructure_drift/baseline_seed.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent  # C:\AIQuant
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

from metrics import load_parquet_metrics_by_day  # noqa: E402

import yaml  # noqa: E402

FXTM_DIR = REPO / "data/staging_fxtm"
DUKA_DIR = REPO / "data/staging_duka/assembled"
SEED_DIR = HERE / "baseline_seed"
SEED_DIR.mkdir(parents=True, exist_ok=True)

# 引擎追踪字段 (两边定义一致, 排除跨日不可比的累加计数)
FIELDS = ["median_spr_bps", "p90_spr_bps", "p99_spr_bps", "spread_usd_median",
          "spread_usd_p90", "arrival_per_min", "burst_min_p99_count", "n_minutes",
          "rv1m_bps", "n_jump_min", "max_min_move_bps"]
SESSIONS = ["Asia", "London", "Overlap", "NY", "Quiet"]


def collect(dirp, globpat, name):
    rows = []
    for p in sorted(dirp.glob(globpat)):
        try:
            days = load_parquet_metrics_by_day(p)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {p.name}: {e}", flush=True)
            continue
        for m in days:
            m["_feed"] = name
            m["_file"] = p.name
            rows.append(m)
        print(f"  {p.name}: {len(days)} day(s)", flush=True)
    rows.sort(key=lambda r: r["date"])
    return rows


def compact(r):
    """保留与 live 行同构的字段子集 (by_session 原样保留, 供 engine 统一消费)。"""
    out = {k: r.get(k) for k in FIELDS}
    out["date"] = r["date"]
    out["_feed"] = r.get("_feed")
    bs = {s: dict(r.get("by_session", {}).get(s, {})) for s in SESSIONS}
    out["by_session"] = {s: b for s, b in bs.items() if b}
    return out


def stat_block(vals):
    import numpy as np
    a = np.array([v for v in vals if v is not None and float(v) == float(v)], dtype=float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)),
            "mean": round(float(a.mean()), 4),
            "median": round(float(np.median(a)), 4),
            "std": round(float(a.std(ddof=1)), 4) if len(a) > 1 else None,
            "p10": round(float(np.percentile(a, 10)), 4),
            "p90": round(float(np.percentile(a, 90)), 4)}


def main():
    print("seed fxtm ...", flush=True)
    fxtm = collect(FXTM_DIR, "ticks_*.parquet", "fxtm")
    print(f"seed duka ...", flush=True)
    duka = collect(DUKA_DIR, "ticks_*.parquet", "duka")

    fx_c = [compact(r) for r in fxtm]
    dk_c = [compact(r) for r in duka]
    (SEED_DIR / "fxtm_daily.json").write_text(
        json.dumps(fx_c, indent=1, ensure_ascii=False), encoding="utf-8")
    (SEED_DIR / "duka_daily.json").write_text(
        json.dumps(dk_c, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"fxtm days={len(fx_c)} duka days={len(dk_c)}", flush=True)

    # —— BASELINE.yaml: 三窗口滚动基准 (主层 = fxtm 同源; duka 为参考层) ——
    def windows(rows):
        dates = sorted({r["date"] for r in rows})
        long_all = rows
        med = [r for r in rows if r["date"] >= sorted(dates)[max(0, len(dates) - 21)]]
        short = [r for r in rows if r["date"] >= sorted(dates)[max(0, len(dates) - 7)]]
        return {"short_7d": short, "medium_21d": med, "long_all": long_all}

    def series_block(rows, key, sub=None):
        if sub:
            vals = [r.get("by_session", {}).get(sub, {}).get(key) for r in rows]
            name = f"sess_{sub}_{key}"
        else:
            vals = [r.get(key) for r in rows]
            name = key
        return {name: stat_block(vals)}

    def build(rows):
        out = {}
        for wname, wrows in windows(rows).items():
            blk = {}
            for f in FIELDS:
                blk.update(series_block(wrows, f))
            for s in SESSIONS:
                blk.update(series_block(wrows, "median_spr_bps", sub=s))
            out[wname] = {k: v for k, v in blk.items() if v}
        return out

    baseline = {
        "meta": {
            "purpose": "微结构状态滚动基准 (DRIFT_ENGINE.md). 主层=fxtm 与 live 采集同源同定义; duka 参考层仅跨年上下文, 不混入主层阈值。",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "fields_definition": "research/money_hunter/microstructure_drift/metrics.py",
            "seed_sources": {"fxtm": str(FXTM_DIR), "duka": str(DUKA_DIR)},
            "window_note": "short=最近7个有数据日, medium=最近21日, long=全部",
        },
        "fxtm": build(fxtm),
        "duka": build(duka),
        "fxtm_n_days": len(fx_c),
        "duka_n_days": len(dk_c),
        "fxtm_date_range": [fx_c[0]["date"], fx_c[-1]["date"]] if fx_c else None,
    }
    (HERE / "BASELINE.yaml").write_text(
        yaml.safe_dump(baseline, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("wrote BASELINE.yaml", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
