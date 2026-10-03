# -*- coding: utf-8 -*-
"""microstructure_drift/drift_engine.py — 微结构漂移观察环 (确定性, 无 LLM, 只读+自写日志)

MICROSTRUCTURE DRIFT → ECONOMIC RELEVANCE → CANDIDATE TRIGGER  观察环 (v0, 观察阶段)

原则 (任务书 §1-§6, §10):
  - 只消费已存在数据: data/staging_fxtm (基准 seed) + data/live_fxtm (前瞻 live), 同一 feed 同一定义。
  - 统计漂移 ≠ 赚钱候选: 任何漂移先过 ECONOMIC_RELEVANCE_RULES.md 门 (P/Payoff/Cost/Exec/OppFreq)。
  - 第一阶段只观察: 不自动变成交易策略; 不写入任何新 alpha 实验。
  - 升级 (UNPROVEN MECHANISM → 预注册队列) 需满足 §六 六条 + 人工/周评审裁决, 本引擎只打标。

窗口: short=7d, medium=21d, long=全部可用(seed+live 同 feed)。
判定: 当前 = 最近 MIN(3, n) 个 live 日均值; 与各窗口比较 z 与相对位移。
输出 (每轮):
  - BASELINE.yaml   滚动基准 (短期/中期/长期, 各字段 mean/std/median/p90/p99)
  - DRIFT_LOG.yaml  观察日志 (append, 保留最近 N=500 条; 首行为 schema 说明)
  - drift_state.json 本引擎状态 (dashboard 用, 与 drift/drift_detect.py 并存不冲突)
  - CANDIDATE_TRIGGER.yaml 仅在触发经济门 + §六 判据时追加候选(观察级)
用法: .venv/Scripts/python.exe research/money_hunter/microstructure_drift/drift_engine.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent  # C:\AIQuant
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import yaml  # noqa: E402

from metrics import load_parquet_metrics_by_day  # noqa: E402

LIVE_DIR = REPO / "data/live_fxtm"
SEED_FXTM = HERE / "baseline_seed/fxtm_daily.json"
SEED_DUKA = HERE / "baseline_seed/duka_daily.json"
BASELINE_P = HERE / "BASELINE.yaml"
LOG_P = HERE / "DRIFT_LOG.yaml"
STATE_P = HERE / "drift_state.json"
CAND_P = HERE / "CANDIDATE_TRIGGER.yaml"

Z_DRIFT = 3.0
REL = 0.15
MIN_LIVE_DAYS = 3       # 至少 3 个 live 日才做"当前 vs 基准"比较 (否则 WARMUP)
CUR_WIN = 3             # 当前状态窗: 最近 3 个 live 日均值
MIN_MINUTES = 500       # live 日完整性: 活跃分钟数下限 (排除周日短段/未收市日)
MAX_LOG = 500

FIELDS = ["median_spr_bps", "p90_spr_bps", "p99_spr_bps", "spread_usd_median",
          "spread_usd_p90", "arrival_per_min", "burst_min_p99_count", "n_minutes",
          "rv1m_bps", "n_jump_min", "max_min_move_bps"]
SESSIONS = ["Asia", "London", "Overlap", "NY", "Quiet"]

# 经济相关性通道映射 (与 ECONOMIC_RELEVANCE_RULES.md 同步; 判定在周评审, 此处只给通道标签)
ECON_CHANNELS = {
    "median_spr_bps": ["COST", "EXECUTION"],
    "p90_spr_bps": ["COST", "EXECUTION"],
    "p99_spr_bps": ["COST", "EXECUTION", "TAIL"],
    "spread_usd_median": ["COST"],
    "spread_usd_p90": ["COST"],
    "arrival_per_min": ["OPP_FREQ", "INFORMATION"],
    "burst_min_p99_count": ["OPP_FREQ", "INFORMATION"],
    "n_minutes": ["OPP_FREQ"],
    "rv1m_bps": ["PROBABILITY", "PAYOFF"],
    "n_jump_min": ["PAYOFF", "TAIL"],
    "max_min_move_bps": ["PAYOFF", "TAIL"],
}


def load_json(p):
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def live_days():
    """前瞻 live: data/live_fxtm/ticks_*.parquet → 逐日指标 (与 seed 同函数同定义)。
    完整性守卫: 只保留"已收市"的 UTC 日 (date < today) 且活跃分钟数 >= MIN_MINUTES(500),
    避免把仍在写入的当日文件 / 周日~3h 短段 (结构性偏短) 当完整日混入窗口。
    """
    rows = []
    if not LIVE_DIR.exists():
        return rows
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for p in sorted(LIVE_DIR.glob("ticks_*.parquet")):
        for m in load_parquet_metrics_by_day(p):
            m["_feed"] = "fxtm_live"
            m["_file"] = p.name
            if not m.get("date") or m["date"] >= today:
                m["_partial"] = True  # 当日文件仍在写入 / 未收市
            elif (m.get("n_minutes") or 0) < MIN_MINUTES:
                m["_partial"] = True  # 覆盖不足 (如周日开盘短段)
            else:
                m["_partial"] = False
            rows.append(m)
    return rows


def field_series(rows, field, sub=None):
    out = {}
    for r in rows:
        v = None
        if sub:
            v = r.get("by_session", {}).get(sub, {}).get(field)
        else:
            v = r.get(field)
        if isinstance(v, (int, float)) and v == v:  # not NaN
            out[r["date"]] = float(v)
    return out


def stats(vals):
    import math
    n = len(vals)
    if n == 0:
        return None
    mn = sum(vals) / n
    var = sum((x - mn) ** 2 for x in vals) / n
    sd = math.sqrt(var)
    s = sorted(vals)
    def q(p):
        i = (n - 1) * p
        lo = int(i)
        return s[lo] if lo >= n - 1 else s[lo] + (i - lo) * (s[lo + 1] - s[lo])
    return {"n": n, "mean": round(mn, 4), "std": round(sd, 4),
            "median": round(q(0.5), 4), "p90": round(q(0.9), 4), "p99": round(q(0.99), 4)}


def compare(cur_vals, base_vals):
    import math
    mb = sum(base_vals) / len(base_vals)
    mc = sum(cur_vals) / len(cur_vals)
    sp = math.sqrt((sum((x - mb) ** 2 for x in base_vals) +
                    sum((x - mc) ** 2 for x in cur_vals)) / (len(base_vals) + len(cur_vals) - 2))
    z = (mc - mb) / sp if sp > 1e-12 else (math.inf if abs(mc - mb) > 1e-12 else 0.0)
    rel = (mc - mb) / mb if abs(mb) > 1e-12 else math.inf
    return {"cur": round(mc, 4), "base": round(mb, 4), "shift": round(mc - mb, 4),
            "z": round(z, 2), "rel": round(rel, 4)}


def main():
    seed = load_json(SEED_FXTM)
    _live_all = live_days()
    live = [r for r in _live_all if not r.get("_partial")]
    partial = [r for r in _live_all if r.get("_partial")]
    seed_duka = load_json(SEED_DUKA)
    all_days = seed + live  # 同一 feed, 时间连续
    all_days.sort(key=lambda r: r["date"])
    live_dates = sorted({r["date"] for r in live})
    n_live = len(live_dates)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    # —— 滚动基准 (同 feed 全部已观测日; 排除当前窗, 保证 "当前 vs 历史正常" 无循环) ——
    cur_set = set(live_dates[-CUR_WIN:] if n_live else [])

    def window(rows, k):
        ds = sorted({r["date"] for r in rows if r["date"] not in cur_set})
        cut = ds[-k] if len(ds) >= k else (ds[0] if ds else None)
        if cut is None:
            return []
        return [r for r in rows if r["date"] >= cut and r["date"] not in cur_set]

    series_all = {}
    for f in FIELDS:
        series_all[f] = field_series(all_days, f)
    for s in SESSIONS:
        series_all[f"sess_{s}_median_spr_bps"] = field_series(all_days, "median_spr_bps", sub=s)

    base = {"meta": {
        "purpose": "滚动基准 (drift_engine 每轮重写): 同 feed(fxtm) 全部观测日, 短期7d/中期21d/长期全部; 已排除当前观察窗",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_live_days": n_live, "n_seed_days": len(seed),
        "live_date_range": [live_dates[0], live_dates[-1]] if live_dates else None,
        "duka_reference_n_days": len(seed_duka),
        "warning": "duka 为跨年参考层(不同采样), 不进主基准阈值", "today_utc": today,
    }, "windows": {}, "fields": {}}
    for wname, k in (("short_7d", 7), ("medium_21d", 21), ("long_all", 10 ** 9)):
        wrows = window(all_days, k)
        base["windows"][wname] = {"n_days": len({r["date"] for r in wrows})}
        for name, pts in series_all.items():
            w = {d: v for d, v in pts.items() if d in {r["date"] for r in wrows}}
            st = stats(list(w.values()))
            if st:
                base["fields"].setdefault(name, {})[wname] = st
    (HERE / "BASELINE.yaml").write_text(
        yaml.safe_dump(base, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # —— 观察判定 ——
    entries = []
    cur_dates = live_dates[-CUR_WIN:] if n_live else []
    cur_days = [r for r in live if r["date"] in cur_dates]
    status = "WARMUP"
    if n_live == 0:
        status = "WARMUP_NO_LIVE_DAYS"
    elif n_live < MIN_LIVE_DAYS:
        status = "WARMUP_LOW_N"
    else:
        findings = []
        for name, pts in series_all.items():
            cvals = [pts[d] for d in cur_dates if d in pts]
            if len(cvals) < 2:
                continue
            for wname, k in (("short_7d", 7), ("medium_21d", 21), ("long_all", 10 ** 9)):
                bv = base["fields"].get(name, {}).get(wname)
                if not bv or bv["n"] < 5:
                    continue
                wrows = window(all_days, k)
                wset = {r["date"] for r in wrows}
                bvals = [pts[d] for d in pts if d in wset and d not in cur_set]
                if len(bvals) < 5:
                    continue
                c = compare(cvals, bvals)
                if abs(c["z"]) >= Z_DRIFT and abs(c["rel"]) >= REL:
                    findings.append({"field": name, "window": wname, **c,
                                     "channels": ECON_CHANNELS.get(name, [])})
        status = "DRIFT" if findings else "OK"
        entries = findings

    # 会话稳定性 (跨 session 同向性, 只对 spread 会话字段)
    sess_stability = None
    if n_live >= MIN_LIVE_DAYS:
        dirs = {}
        for s in SESSIONS:
            name = f"sess_{s}_median_spr_bps"
            pts = series_all[name]
            cvals = [pts[d] for d in cur_dates if d in pts]
            bv = base["fields"].get(name, {}).get("medium_21d")
            if len(cvals) >= 2 and bv and bv["n"] >= 5:
                dirs[s] = 1 if (sum(cvals) / len(cvals)) > bv["mean"] else -1
        if dirs:
            pos = sum(1 for v in dirs.values() if v > 0)
            sess_stability = {"agree_pos": pos, "n": len(dirs),
                              "stable": pos == len(dirs) or pos == 0}

    state = {"engine": "microstructure_drift/drift_engine.py", "status": status,
             "generated_utc": datetime.now(timezone.utc).isoformat(),
             "n_live_days": n_live, "min_live_days": MIN_LIVE_DAYS,
             "cur_window_days": cur_dates, "findings": entries,
             "sess_stability": sess_stability}
    # DoD 产出断言 (CONSTITUTION §完成定义): 每轮必须报告"本周期实际消费了哪些真实文件", 空产出=故障可见
    live_files = sorted(LIVE_DIR.glob("ticks_*.parquet"))
    state["health"] = {
        "live_files": [p.name for p in live_files],
        "live_file_count": len(live_files),
        "assertion": "COLLECTED" if len(live_files) > 0 else "NO_LIVE_FILES_ALERT",
    }
    STATE_P.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")

    # —— DRIFT_LOG append ——
    log = []
    if LOG_P.exists():
        try:
            log = yaml.safe_load(LOG_P.read_text(encoding="utf-8")) or []
        except Exception:  # noqa: BLE001
            log = []
        if isinstance(log, dict):
            log = log.get("entries", [])
    rec = {"ts": state["generated_utc"], "status": status,
           "n_live_days": n_live, "cur_days": cur_dates,
           "sess_stability": sess_stability,
           "n_findings": len(entries),
           "findings": entries[:20],
           "note": "观察环 v0: 统计漂移需过经济门才可升级; 本引擎不启动实验"}
    log.append(rec)
    log = log[-MAX_LOG:]
    LOG_P.write_text(yaml.safe_dump({"schema": "entries: [{ts,status,n_live_days,cur_days,sess_stability,findings}]",
                                     "entries": log}, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"DRIFT status={status} live_days={n_live} seed_days={len(seed)} "
          f"duka_days={len(seed_duka)} findings={len(entries)}", flush=True)
    for f in entries[:10]:
        print(f"  {f['field']} [{f['window']}] z={f['z']} rel={f['rel']} ch={f['channels']}", flush=True)
    if status.startswith("WARMUP"):
        print("  WARMUP: 尚无足够前瞻日, 观察环持续积累中(不打扰)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
