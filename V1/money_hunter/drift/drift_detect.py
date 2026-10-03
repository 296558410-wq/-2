# -*- coding: utf-8 -*-
"""drift_detect.py — 微结构记忆自动漂移探测器 (2026-09-06, 系统审计 #10 落地)
确定性脚本(无 LLM): 读 research/microstructure_memory/daily/YYYYMMDD.json 日快照序列,
对比"近期 7 天均值" vs "基线均值", 找统计显著 + 相对显著的漂移。
- 基线: 最早 (N-MIN_WIN) 天; 近期窗: 最后 MIN_WIN 天
- 漂移判定: |z| >= Z_DRIFT(3) 且 |shift/mean_base| >= REL(0.15)
- 状态: WARMUP(< MIN_N 天, 属正常) / OK / DRIFT / MINOR(1<z<3 仅记录)
输出: research/money_hunter/drift/drift_status.json (dashboard 读取)
使用说明: 每周评审 cron step-0 运行. 只读, 不写研究结论文件.
数据注意: n_ticks/by_session.n 在日内被 merge_snapshot 累加(全日在跑次数之和), 跨日不可比 → 本探测器
不追踪这两个字段; 追踪全日在跑的标量: median/p99 spread(各会话中位价差保留), burst_min_p99_count, n_minutes.
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent
DAILY = REPO / "research/microstructure_memory/daily"
OUT = REPO / "research/money_hunter/drift/drift_status.json"

MIN_N = 14          # 至少 14 个采集日才出基线
MIN_WIN = 7         # 近期窗 7 天
Z_DRIFT = 3.0       # 显著 z
REL = 0.15          # 相对基线均值变化 >= 15%
FIELDS = ["median_spr_bps", "p99_spr_bps", "spread_usd_median", "burst_min_p99_count", "n_minutes"]
SESSIONS = ["Asia", "London", "Overlap", "NY", "Quiet"]


def load_series():
    """每日期文件取最后写入状态 → {field: {date: value}}"""
    by_date = {}
    for p in sorted(DAILY.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        by_date[p.stem] = d  # 同日多次运行取最后(文件覆盖写) — glob 排序后自然最后
    series = {f: {} for f in FIELDS}
    for f in SESSIONS:
        series[f"sess_{f}_median_spr_bps"] = {}
    for date, d in by_date.items():
        for f in FIELDS:
            if f in d and isinstance(d[f], (int, float)) and math.isfinite(float(d[f])):
                series[f][date] = float(d[f])
        bs = d.get("by_session", {})
        for f in SESSIONS:
            v = bs.get(f, {}).get("median_spr_bps")
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                series[f"sess_{f}_median_spr_bps"][date] = float(v)
    return by_date, series


def test_field(name, pts):
    dates = sorted(pts)
    n = len(dates)
    if n < MIN_N:
        return None
    base = [pts[x] for x in dates[: n - MIN_WIN]]
    win = [pts[x] for x in dates[n - MIN_WIN:]]
    mb = sum(base) / len(base)
    mw = sum(win) / len(win)
    sp = math.sqrt((sum((x - mb) ** 2 for x in base) + sum((x - mw) ** 2 for x in win)) / (len(base) + len(win) - 2))
    sp = sp if sp > 1e-12 else None
    shift = mw - mb
    if sp is None:
        z = math.inf if abs(shift) > 1e-12 else 0.0
    else:
        z = shift / sp
    rel = abs(shift / mb) if abs(mb) > 1e-12 else math.inf
    return {"field": name, "n": n, "base_mean": round(mb, 5), "win_mean": round(mw, 5),
            "shift": round(shift, 5), "z": round(z, 2), "rel_shift": round(rel, 3)}


def main():
    DAILY.mkdir(parents=True, exist_ok=True)
    by_date, series = load_series()
    n_days = len(by_date)
    results = []
    for f, pts in series.items():
        if len(pts) < MIN_N:
            continue
        r = test_field(f, pts)
        if r:
            results.append(r)
    findings = [r for r in results if r["z"] >= Z_DRIFT and r["rel_shift"] >= REL]
    minors = [r for r in results if Z_DRIFT > r["z"] >= 1.0 and r["rel_shift"] >= REL]
    if n_days < MIN_N:
        status = "WARMUP"
    elif findings:
        status = "DRIFT"
    elif minors:
        status = "MINOR"
    else:
        status = "OK"
    out = {"status": status, "generated_utc": datetime.now(timezone.utc).isoformat(),
           "n_days": n_days, "min_required": MIN_N, "win_days": MIN_WIN,
           "z_drift": Z_DRIFT, "rel": REL, "fields_checked": len(results),
           "findings": findings, "minors": minors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"DRIFT status={status} days={n_days}/{MIN_N} fields={len(results)} findings={len(findings)}", flush=True)
    for f in findings:
        print(f"  FINDING {f['field']}: base={f['base_mean']} win={f['win_mean']} shift={f['shift']} z={f['z']} rel={f['rel_shift']}", flush=True)
    return 0 if status in ("WARMUP", "OK") else 0  # 探测器永不失败退出; 判定交给周评审


if __name__ == "__main__":
    sys.exit(main())
