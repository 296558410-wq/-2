# -*- coding: utf-8 -*-
"""V1-R2 PHASE A: immutable baseline manifest + rollback manifest + data capability inventory + frozen feature registry.
Read-only w.r.t. data; writes ONLY under research/hermes/trader_v1/v1_r2_prediction_upgrade/ .
No order APIs. No V2/V3 writes. No Run Boundary writes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = r"C:\AIQuant"
V1 = os.path.join(REPO, "research", "hermes", "trader_v1")
UP = os.path.join(V1, "v1_r2_prediction_upgrade")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
ARCHIVE_ENGINE = os.path.join(REPO, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
ENGINE = os.path.join(V1, "engine.py")
BASE_ENGINE_SHA = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
CV3 = os.path.join(REPO, "research", "v3_opportunity_engine", "v1_r31_3_controlled_migration")
V2 = os.path.join(REPO, "research", "hermes", "trader_v2")
for d in ("reports", "registry", "manifests", "ledger", "tests", "v1_r2_research_runs", "engines"):
    os.makedirs(os.path.join(UP, d), exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()
OUT = {}


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sh(a, cwd=None, t=180):
    try:
        p = subprocess.run(list(a), cwd=cwd or REPO, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def wj(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=str)
    return path


def tree_hash(root, excl_dirs=(), exts=(".py", ".yaml", ".yml")):
    items = []
    for r_, ds, fs in os.walk(root):
        rel = os.path.relpath(r_, root).replace("\\", "/")
        if any(x in rel.split("/") for x in excl_dirs):
            continue
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith(exts):
                p = os.path.join(r_, f)
                items.append([os.path.relpath(p, root).replace("\\", "/"), sha(p)])
    items.sort()
    return sha_obj(items), len(items), items


# ============ §2 BASELINE ============
def phase_baseline():
    eng_now = sha(ENGINE)
    src_hash, nsrc, src_items = tree_hash(V1, excl_dirs=("run_state", "v1_r2_prediction_upgrade"))
    cfg_hash, ncfg, cfg_items = tree_hash(V1, excl_dirs=("run_state", "v1_r2_prediction_upgrade"),
                                            exts=(".yaml", ".yml", ".ini", ".cfg", ".conf"))
    rs = os.path.join(V1, "run_state")
    rt = []
    if os.path.isdir(rs):
        for f in sorted(os.listdir(rs)):
            p = os.path.join(rs, f)
            if os.path.isfile(p):
                rt.append([f, sha(p)])
    runtime_hash = sha_obj(rt)
    git_head = sh(["git", "log", "-1", "--format=%H|%ad|%s", "--date=iso"])
    porcelain = [x for x in sh(["git", "status", "--porcelain"]).splitlines() if x.strip()]
    v1_porcelain = [x for x in porcelain if "hermes/trader_v1" in x.replace("\\", "/")]
    man = {"baseline_version": "V1-MV-R1", "engine_hash": eng_now,
             "engine_hash_matches_expected": eng_now == BASE_ENGINE_SHA,
             "expected_engine_hash": BASE_ENGINE_SHA,
             "archive_baseline_engine_hash": sha(ARCHIVE_ENGINE),
             "source_tree_hash": src_hash, "source_files": nsrc,
             "config_hash": cfg_hash, "config_files": ncfg, "runtime_hash": runtime_hash,
             "timestamp_utc": NOW, "git_head": git_head, "git_clean": len(porcelain) == 0,
             "git_porcelain_total": len(porcelain), "git_porcelain_trader_v1": v1_porcelain[:20],
             "note": "git 状态按真实记录，未伪造 commit；source_tree_hash 排除 run_state/ 与本次升级目录"}
    wj(os.path.join(UP, "manifests", "V1_R2_BASELINE_MANIFEST.json"), man)
    return man


# ============ §4 ROLLBACK ============
def phase_rollback(base):
    rb = {"baseline_version": base["baseline_version"], "rollback_target_engine_hash": BASE_ENGINE_SHA,
            "rollback_source_engine_file": os.path.relpath(ARCHIVE_ENGINE, REPO).replace("\\", "/"),
            "rollback_source_engine_hash": sha(ARCHIVE_ENGINE),
            "method": "hash-verified restore",
            "steps": [
                "1) 校验 archive 基线 engine.py 的 sha256 == 7d956456…（不等则 STOP）",
                "2) 用 os.replace 同卷原子替换 trader_v1/engine.py（不使用 git checkout）",
                "3) 替换后校验 engine.py sha256 == 7d956456…",
                "4) 删除/忽略 v1_r2_prediction_upgrade/（本任务全部改动仅在该目录 + engine.py 若被改）",
                "5) 重跑 source_tree_hash 对比 baseline 值",
            ],
            "verification": {"engine_hash_expected": BASE_ENGINE_SHA, "baseline_source_tree_hash": base["source_tree_hash"],
                               "baseline_config_hash": base["config_hash"], "baseline_runtime_hash": base["runtime_hash"]},
            "timestamp_utc": NOW}
    wj(os.path.join(UP, "manifests", "V1_R2_ROLLBACK_MANIFEST.json"), rb)
    return rb


# ============ §5 DATA INVENTORY ============
SCAN_CODE = r'''
import json, os, glob
import pandas as pd
REPO = r"C:\AIQuant"
out = {"parquet": [], "json_files": [], "dirs": []}
roots = [os.path.join(REPO,"data"), os.path.join(REPO,"research","v3_alpha_discovery_r1"),
         os.path.join(REPO,"research","microstructure_memory"), os.path.join(REPO,"research","self_collect"),
         os.path.join(REPO,"data","live_fxtm")]
seen=set()
for root in roots:
    if not os.path.isdir(root): continue
    for r_,ds,fs in os.walk(root):
        if "__pycache__" in r_: continue
        for f in fs:
            p=os.path.join(r_,f)
            if p in seen: continue
            seen.add(p)
            rel=os.path.relpath(p,REPO).replace("\\","/")
            if f.endswith(".parquet"):
                try:
                    df=pd.read_parquet(p)
                    cols=[str(c) for c in df.columns]
                    rng=None
                    tcol=next((c for c in cols if c.lower() in ("ts_utc","dt_utc","time","timestamp","date","datetime")),None)
                    if tcol:
                        try:
                            s=pd.to_datetime(df[tcol],utc=True,errors="coerce")
                            rng=[str(s.min()),str(s.max())]
                        except Exception: rng="unparsed"
                    out["parquet"].append({"path":rel,"rows":int(len(df)),"columns":cols,"time_range":rng,
                        "has_bid":"bid" in [c.lower() for c in cols],"has_ask":"ask" in [c.lower() for c in cols],
                        "has_spread":any("spread" in c.lower() for c in cols),
                        "has_tick_volume":any("tick" in c.lower() for c in cols),
                        "has_volume":any(c.lower()=="volume" for c in cols),
                        "has_ohlc":all(x in [c.lower() for c in cols] for x in ("open","high","low","close"))
                                   or all(x in [c.lower() for c in cols] for x in ("o","h","l","c"))})
                except Exception as e:
                    out["parquet"].append({"path":rel,"error":type(e).__name__+":"+str(e)[:80]})
            elif f.endswith((".json","_latest.json")):
                st=os.stat(p)
                out["json_files"].append({"path":rel,"size":st.st_size})
for root in roots:
    if os.path.isdir(root):
        out["dirs"].append({"root":os.path.relpath(root,REPO).replace("\\","/"),
                            "files":sum(len(fs) for _,_,fs in os.walk(root))})
print(json.dumps(out,ensure_ascii=False)[:200000])
'''

DOM_CODE = r'''
import json
try:
    import MetaTrader5 as mt5
    ok=mt5.initialize()
    res={"connected":bool(ok),"has_api":True,
         "has_market_book_add":hasattr(mt5,"market_book_add"),
         "has_market_book_get":hasattr(mt5,"market_book_get"),
         "book_get_without_sub":None,"book_after_add":None,"add_ret":None}
    try:
        b=mt5.market_book_get("XAUUSD"); res["book_get_without_sub"]=None if b is None else len(b)
    except Exception as e: res["book_get_without_sub"]="ERR:"+type(e).__name__
    try:
        r=mt5.market_book_add("XAUUSD"); res["add_ret"]=bool(r)
        if r:
            b2=mt5.market_book_get("XAUUSD"); res["book_after_add"]=None if b2 is None else len(b2)
            try: mt5.market_book_release("XAUUSD")
            except Exception: pass
    except Exception as e: res["add_ret"]="ERR:"+type(e).__name__
    ti=mt5.terminal_info()
    res["terminal_connected"]=bool(getattr(ti,"connected",False)) if ti else False
    try: mt5.shutdown()
    except Exception: pass
    print(json.dumps(res,ensure_ascii=False))
except Exception as e:
    print(json.dumps({"connected":False,"has_api":False,"err":type(e).__name__+":"+str(e)[:120]}))
'''


def phase_data():
    inv = {}
    try:
        pr = subprocess.run([PY, "-c", SCAN_CODE], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=600)
        inv = json.loads((pr.stdout or "{}").strip().splitlines()[-1]) if (pr.stdout or "").strip() else {"err": "no output"}
    except Exception as e:  # noqa: BLE001
        inv = {"err": type(e).__name__ + ":" + str(e)[:120]}
    dom = {}
    try:
        pr2 = subprocess.run([PY, "-c", DOM_CODE], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=300)
        dom = json.loads((pr2.stdout or "{}").strip().splitlines()[-1]) if (pr2.stdout or "").strip() else {"err": "no output"}
    except Exception as e:  # noqa: BLE001
        dom = {"err": type(e).__name__ + ":" + str(e)[:120]}
    dom_direct = bool(dom.get("book_after_add")) and (dom.get("book_after_add") or 0) > 0
    pq = inv.get("parquet", [])
    has_bidask = any(p.get("has_bid") and p.get("has_ask") for p in pq)
    has_spread = any(p.get("has_spread") for p in pq)
    has_tickvol = any(p.get("has_tick_volume") for p in pq)
    has_ohlc = any(p.get("has_ohlc") for p in pq)
    inv_out = {"timestamp_utc": NOW, "inventory": inv, "dom_probe": dom,
                 "verdicts": {
                     "TICK_BIDASK": "DIRECT" if has_bidask else "UNAVAILABLE",
                     "SPREAD": "DIRECT" if has_spread else ("PROXY_POSSIBLE(ask-bid)" if has_bidask else "UNAVAILABLE"),
                     "TICK_VOLUME": "DIRECT" if has_tickvol else "UNAVAILABLE",
                     "OHLC_BARS": "DIRECT" if has_ohlc else "PROXY_REBUILD_FROM_TICK",
                     "ORDER_BOOK_DOM": "DIRECT" if dom_direct else "UNAVAILABLE",
                     "DEPTH": "DIRECT" if dom_direct else "UNAVAILABLE",
                     "TRADE_DIRECTION_IDENTIFIABILITY": "UNAVAILABLE(无逐笔成交方向/无 DOM)",
                     "ABSORPTION_SOURCE": "DIRECT" if dom_direct else "PROXY",
                     "LIQUIDITY_WITHDRAWAL_SOURCE": "DIRECT" if dom_direct else "PROXY",
                 },
                 "notes": ["按 §5/§10/§30：若无 DOM，则 absorption / liquidity-withdrawal 只能标记 PROXY，不得伪装成真实盘口吸收。",
                             "DOM 探测为只读（market_book_add/get/release），未做任何交易动作。"]}
    wj(os.path.join(UP, "manifests", "V1_R2_DATA_CAPABILITY.json"), inv_out)
    return inv_out


# ============ §6 FEATURE REGISTRY (FROZEN) ============
def feature(fid, name, definition, src, lookback, tf, pit, norm, missing):
    d = {"feature_id": fid, "name": name, "definition": definition, "data_source": src, "lookback": lookback,
           "timeframe": tf, "PIT_rule": pit, "normalization": norm, "missing_data_behavior": missing,
           "version": "v1r2-r1", "status": "FROZEN"}
    d["hash"] = sha_obj(d)
    return d


def phase_registry(dat):
    v = dat["verdicts"]
    feats = [
        feature("F-REGIME", "market_regime",
                "由当时可见的多周期状态(趋势/区间/ER/ATR 分位/波动)映射到 TREND|RANGE|COMPRESSION|EXPANSION|REVERSAL|LIQUIDITY_STRESS|EVENT_DRIVEN|UNKNOWN",
                "本地 M15/H1/H4/D1 已收盘 bar + ATR/ER", "96 根 M15 + 60 根 H1/H4", "M15主/H1/H4/D1上下文",
                "仅使用 signal 时刻已收盘 bar", "无(类别)", "缺周期→该周期弃权并降级为 UNKNOWN"),
        feature("F-KEYLEVEL", "key_levels",
                "5-bar 分形摆动点(左2右2)、区间边界(96根高低)、session 极值、波动极值；confirmed_at = pivot_time + 2 bar",
                "本地 bar", "240 根 M15", "M15/多周期", "确认时间=pivot+2bar（无未来函数）", "价格/ATR 归一",
                "不足 240 bar → 不输出新 level"),
        feature("F-TOUCH", "touch_exhaustion",
                "接触计数/穿透深度/近位时间/回收距离与速度/触碰后反应/反应衰减/触碰间隔 → FIRST_TEST|RETEST|REPEATED_TEST|EXHAUSTION_BUILDING|EXHAUSTION_CONFIRMED",
                "本地 bar + ATR", "240 根 M15", "M15", "只用 ≤t 的 bar", "ATR 归一", "无 level → NOT_APPLICABLE"),
        feature("F-ABSORB", "absorption",
                f"冲击(活动量或tick数)上升后价格推进是否下降；**数据源={v['ABSORPTION_SOURCE']}** → ABSORPTION_NONE|POSSIBLE|STRONG|FAILED",
                f"tick/bars（{v['ABSORPTION_SOURCE']}）", "3 根 bar / 60s 窗口", "M15+intra", "只用 ≤t 数据",
                "效率比率(tick 归一)", "无 tick → INSUFFICIENT(不得输出 STRONG)"),
        feature("F-LIQ", "liquidity_state",
                f"spread 分位 + tick 活动 + 价格响应 → STABLE|REPLENISHING|DEPLETING|WITHDRAWING|UNKNOWN（**{v['LIQUIDITY_WITHDRAWAL_SOURCE']}**）",
                "tick/spread（PROXY）", "60 根 M15", "M15", "只用 ≤t 数据", "z-score", "无 spread → UNKNOWN"),
        feature("F-BREAK", "break_risk",
                "证据集合(repeated_test/response_decay/absorption_weakening/liquidity_withdrawal/penetration/recovery_failure/momentum_accel) → LOW|NORMAL|ELEVATED|CRITICAL；必须输出 break_risk_evidence[]",
                "F-TOUCH/F-ABSORB/F-LIQ/F-MOM", "同上", "M15", "只用 ≤t 状态", "证据计数(0/1/2-3/4+)", "缺证据→证据列表标注缺失"),
        feature("F-MOM", "momentum_state",
                "速度(Δclose/ATR,4bar)/加速度/区间扩张收缩 → SLOW|NORMAL|ACCELERATING|DECELERATING|EXHAUSTING",
                "本地 bar + ATR20", "20 根 M15", "M15", "只用 ≤t bar", "ATR 归一", "缺 ATR → UNKNOWN"),
        feature("F-FAILED", "failed_event",
                "突破尝试/确认/失败/收复的时间序列 → FAILED_BREAKOUT|FAILED_BREAKDOWN|FAILED_SUPPORT_BREAK|FAILED_RESISTANCE_BREAK|FAILED_RECLAIM（禁止单根 candle 判定）",
                "本地 bar + level", "96 根 M15", "M15", "attempt/confirm/failure/reclaim 均须 ≤t", "ATR 归一",
                "无 level → NONE"),
        feature("F-TRANS", "state_transition",
                "状态向量(regime,level关系,touch,absorption,liquidity,break_risk,momentum) 的相邻周期变化 → 下一可能状态集合",
                "上述各引擎 + 上一周期状态", "2 个周期", "M15", "上一周期状态必须来自 ≤t-1", "无(离散)",
                "上周期缺失 → 只输出当前状态"),
        feature("F-COUNTER", "counter_evidence",
                "对给定方向同时产出 SUPPORTING_EVIDENCE[] 与 COUNTER_EVIDENCE[]（禁止只收集支持证据）",
                "F-TOUCH/F-ABSORB/F-LIQ/F-BREAK/F-MOM/F-TRANS", "同上", "M15", "只用 ≤t 状态", "无(列表)",
                "证据缺失 → 记 UNKNOWN 而非省略"),
        feature("F-NEXT", "next_state_prediction",
                "CURRENT_STATE → TRANSITION_EVIDENCE → NEXT_STATE(CONTINUATION|REVERSAL|BREAKOUT|BREAKDOWN|REVERSION|HOLD|UNKNOWN) → DIRECTION",
                "F-TRANS/F-COUNTER 等", "同上", "M15", "严禁未来收益入 feature", "概率/类别(冻结)", "不足→UNKNOWN"),
        feature("F-DQ", "data_quality",
                "DOM/深度/逐笔方向缺失标记、spread 异常、bar 构造伪影、重复 tick、时间戳伪影 → 向上游传递",
                "数据层", "60 根", "M15", "只用 ≤t", "标志位", "任何 UNKNOWN 必须显式传播"),
    ]
    reg = {"registry_name": "v1_r2_feature_registry", "version": "v1r2-r1", "status": "FROZEN",
             "frozen_at_utc": NOW, "note": "按 §6/§24：定义/回看/阈值/规则在 Validation 开始前冻结；registry_hash 之后不得改变",
             "params_frozen": {
                 "M15_GRID": 15, "ATR_N": 20, "ER_N": 10, "PIVOT_LEFT": 2, "PIVOT_RIGHT": 2,
                 "LEVEL_CONFIRM_LAG_BARS": 2, "LEVEL_MAX_PER_TYPE": 40, "RANGE_WINDOW_BARS": 96,
                 "TOUCH_TOL_ATR": 0.25, "TOUCH_WINDOW_BARS": 240, "RECOVERY_WINDOW_BARS": 8,
                 "ABSORB_BREAK_PEN": 0.15, "ABSORB_EFF_DECLINE": 0.40, "ABSORB_ACT_RISE": 0.30,
                 "LIQ_SPREAD_Z": 1.5, "LIQ_ACT_Z": 1.5, "BREAK_EV_CRITICAL": 4, "BREAK_EV_ELEVATED": 2,
                 "MOM_VEL_FAST_ATR": 0.8, "MOM_ACC_ATR": 0.35, "FAILED_CONFIRM_BARS": 2,
                 "FAILED_RECLAIM_BARS": 6, "REGIME_ATR_PCTL_HI": 80, "REGIME_ATR_PCTL_LO": 20},
             "features": feats,
             "data_verdicts": dat["verdicts"]}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    reg["feature_registry_hash"] = sha_obj([f["hash"] for f in feats])
    wj(os.path.join(UP, "registry", "v1_r2_feature_registry.json"), reg)
    return reg


# ============ isolation / safety evidence ============
def phase_isolation():
    v2h, v2n, _ = tree_hash(V2, excl_dirs=("run_state",), exts=(".py", ".yaml", ".yml", ".json", ".cmd", ".ps1"))
    v3dirs = {}
    for name in ("high_frequency_r2", "mv_r1", "tradability_r1", "m01_tradability_repair_r1"):
        p = os.path.join(REPO, "research", "v3_opportunity_engine", name)
        if os.path.isdir(p):
            v3dirs[name] = sha_obj(sorted([os.path.relpath(os.path.join(r_, f), p).replace("\\", "/")
                                              for r_, _, fs in os.walk(p) for f in fs]))
    rb_files = sorted([os.path.relpath(os.path.join(r_, f), CV3).replace("\\", "/")
                         for r_, _, fs in os.walk(CV3) for f in fs if not f.endswith(".tmp")])
    return {"timestamp_utc": NOW, "V2_tree_hash": v2h, "V2_files": v2n, "V3_dir_hashes": v3dirs,
              "RUN_BOUNDARY_files": len(rb_files), "RUN_BOUNDARY_sample": rb_files[:8],
              "note": "本阶段对 V2/V3/RunBoundary 仅做只读哈希，无写入"}


def main():
    base = phase_baseline()
    rb = phase_rollback(base)
    dat = phase_data()
    reg = phase_registry(dat)
    iso = phase_isolation()
    # ledger (§44)
    led_path = os.path.join(UP, "ledger", "v1_r2_prediction_ledger.jsonl")
    prev = "GENESIS"
    seq = 0
    if os.path.exists(led_path):
        for line in open(led_path, encoding="utf-8"):
            if line.strip():
                o = json.loads(line)
                prev = o["record_hash"]
                seq = o["seq"] + 1
    recs = [("BASELINE", base), ("ROLLBACK_MANIFEST", rb), ("DATA_INVENTORY", dat), ("FEATURE_REGISTRY_FROZEN", reg),
             ("ISOLATION_EVIDENCE", iso)]
    with open(led_path, "a", encoding="utf-8", newline="\n") as fh:
        for kind, payload in recs:
            body = json.dumps({"seq": seq, "ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "payload": payload},
                                sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
            fh.write(json.dumps({"seq": seq, "ts": datetime.now(timezone.utc).isoformat(), "kind": kind,
                                   "payload": payload, "prev_hash": prev, "record_hash": h},
                                  sort_keys=True, ensure_ascii=False) + "\n")
            prev = h
            seq += 1
    # audit (§43) partial
    audit = {"version": "v1r2-r1", "timestamp_utc": NOW,
               "baseline_hash": base["engine_hash"], "final_source_hash": None,
               "registry_hash": reg["registry_hash"], "feature_registry_hash": reg["feature_registry_hash"],
               "dataset_hashes": {x["path"]: sha(os.path.join(REPO, x["path"])) for x in dat["inventory"].get("parquet", [])
                                    if not x.get("error")} ,
               "input_hash": sha_obj(base), "output_hash": sha_obj(reg), "context_hash": None, "replay_hash": None,
               "test_hash": None, "lookahead_status": "PENDING", "determinism_status": "PENDING",
               "isolation_status": "PASS(snapshot recorded)", "order_send": 0, "order_check": 0,
               "boundary_violation": 0}
    wj(os.path.join(UP, "reports", "V1_R2_AUDIT.json"), audit)
    # change manifest (§37)
    porcelain = [x for x in sh(["git", "status", "--porcelain"]).splitlines() if x.strip()]
    add = [x for x in porcelain if "v1_r2_prediction_upgrade" in x.replace("\\", "/")]
    ch = {"timestamp_utc": NOW, "git_head": base["git_head"], "git_clean": base["git_clean"],
            "changed_files": [], "added_files": [x[3:].strip() for x in add], "deleted_files": [],
            "modified_files": [], "baseline_hash": base["engine_hash"], "final_hash": sha(ENGINE),
            "note": "本阶段仅在 v1_r2_prediction_upgrade/ 下新增文件；engine.py 未改"}
    wj(os.path.join(UP, "manifests", "V1_R2_CHANGE_MANIFEST.json"), ch)
    with open(os.path.join(UP, "tests", "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# tests (planned, §38)\n\n本目录将承载 26 项 blocking 测试（key_level/touch/absorption/liquidity/"
                   "break_risk/momentum/failed_event/regime/transition/counter/next_state + no_lookahead/truncated/"
                   "full/deterministic/registry_hash/feature_hash/context_hash/parallel/ablation/redundancy/cost_stress/"
                   "baseline_restore/v2_isolation/v3_isolation/run_boundary_isolation/order_send_disabled）。\n\n"
                   "**当前状态：尚未实现（Phase A 仅完成基线与注册表冻结）。**\n")
    summary = {"phase": "A", "done": ["BASELINE_MANIFEST", "ROLLBACK_MANIFEST", "DATA_CAPABILITY", "FEATURE_REGISTRY_FROZEN",
                                        "ISOLATION_EVIDENCE", "LEDGER", "AUDIT(partial)", "CHANGE_MANIFEST"],
                 "engine_hash": base["engine_hash"], "engine_matches": base["engine_hash_matches_expected"],
                 "registry_hash": reg["registry_hash"], "verdicts": dat["verdicts"],
                 "dom_probe": dat["dom_probe"], "pending": ["engines A-J", "old/new parallel replay", "time-split validation",
                                                              "walk-forward", "ablation", "redundancy", "lookahead tests",
                                                              "determinism×2", "replay", "26 tests", "final report", "final verdict"],
                 "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0,
                              "V2_WRITE": 0, "V3_WRITE": 0, "RUN_BOUNDARY_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF"},
                 "ts_utc": NOW}
    wj(os.path.join(UP, "reports", "V1_R2_PHASE_A_SUMMARY.json"), summary)
    print(json.dumps(summary, ensure_ascii=True, indent=1)[:2600], flush=True)
    print("files:", os.path.join(UP, "manifests"), "|", os.path.join(UP, "registry"), "|", os.path.join(UP, "reports"), flush=True)


if __name__ == "__main__":
    main()
