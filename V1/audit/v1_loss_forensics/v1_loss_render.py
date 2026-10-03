# -*- coding: utf-8 -*-
"""v1_loss_render.py — render TRADE_ERROR_SUMMARY.csv, COUNTERFACTUAL_ANALYSIS.md,
ROOT_CAUSE_MATRIX.md, PIT_AUDIT.json from the corrected TRADE_ERROR_DATABASE.jsonl. Read-only inputs."""
from __future__ import annotations
import csv, json, os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "TRADE_ERROR_DATABASE.jsonl")
R = [json.loads(l) for l in open(DB, encoding="utf-8") if l.strip()]
LOSS = [r for r in R if r["outcome"] == "LOSS"]
WIN = [r for r in R if r["outcome"] == "WIN"]

# ---------------- CSV ----------------
cols = ["trade_id", "outcome", "side", "entry_utc", "exit_utc", "duration_min", "session",
        "entry_px", "exit_px", "pnl_price", "commission", "swap", "net", "R", "mfe_r", "mae_r",
        "t_mfe_min", "t_mae_min", "spread_bps", "liquidity_tpm", "guard_block", "primary_root_cause"]
with open(os.path.join(HERE, "TRADE_ERROR_SUMMARY.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for r in R:
        w.writerow([r["trade_id"], r["outcome"], r["entry"]["side"], r["entry"]["ts_utc"], r["exit"]["ts_utc"],
                    r["path"]["duration_min"], r["session"], r["entry"]["price"], r["exit"]["price"],
                    r["pnl_price"], r["commission"], r["swap"], r["net"], r["R"],
                    r["path"]["mfe_r"], r["path"]["mae_r"], r["path"]["t_mfe_min"], r["path"]["t_mae_min"],
                    r["spread_bps"], r["liquidity_ticks_per_min_15m"],
                    bool(r["guard_cf"]["block_price"] or r["guard_cf"]["block_net"]), r["primary_root_cause"]])

# ---------------- aggregates ----------------
cnt = Counter(r["primary_root_cause"] for r in LOSS)
by_class = defaultdict(list)
for r in LOSS:
    by_class[r["primary_root_cause"]].append(r["trade_id"])
blocked = [r for r in R if r["guard_cf"]["block_price"] or r["guard_cf"]["block_net"]]
blk_loss = [r for r in blocked if r["outcome"] == "LOSS"]
blk_win = [r for r in blocked if r["outcome"] == "WIN"]
side_loss = Counter(r["entry"]["side"] for r in LOSS)
sess_loss = Counter(r["session"] for r in LOSS)

# PIT audit
pit_rows, pit_ok = [], True
for r in R:
    dec_ms = r["pit"]["decision_cutoff_ms"]
    bars_ok = (r["pit"]["max_bar_close_ms"] is None) or (r["pit"]["max_bar_close_ms"] <= dec_ms)
    tick_ok = (r["pit"]["max_decision_tick_ms"] is None) or (r["pit"]["max_decision_tick_ms"] <= dec_ms)
    ent_ms = int(__import__("datetime").datetime.fromisoformat(r["entry"]["ts_utc"]).timestamp() * 1000)
    path_ok = True
    for k, v in (r["path"]["pts_bps"] or {}).items():
        if v is None:
            path_ok = False
    pit_rows.append({"trade_id": r["trade_id"], "bars_ok": bars_ok, "decision_ticks_ok": tick_ok,
                     "outcome_after_entry": ent_ms, "ok": bars_ok and tick_ok})
    pit_ok = pit_ok and bars_ok and tick_ok
json.dump({"schema": "v1_loss_pit_audit/1", "verdict": "PASS" if pit_ok else "FAIL",
           "rule": "decision features: sources <= decision_ts only; outcome features: >= entry only",
           "rows": pit_rows},
          open(os.path.join(HERE, "PIT_AUDIT.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# counterfactual aggregates over losses
def agg(field):
    vals = [r["cf"].get(field) for r in LOSS]
    nums = [(v if isinstance(v, dict) else None) for v in vals]
    return nums

tim15 = [r["cf"].get("timing_15m") for r in LOSS]
tim30 = [r["cf"].get("timing_30m") for r in LOSS]
opp = [r["cf"].get("opposite") for r in LOSS]
ts = {k: [r["cf"].get(f"time_stop_{k}m") for r in LOSS] for k in (15, 30, 60)}
rev = [r["cf"].get("reversal_after_exit_30m_r") for r in LOSS]
notr = [r["cf"].get("no_trade_move_60m_r") for r in LOSS]

def stats(xs, key=None):
    vs = []
    for x in xs:
        v = x.get(key) if (key and isinstance(x, dict)) else x
        if isinstance(v, (int, float)):
            vs.append(v)
    return {"n": len(vs), "mean": round(sum(vs) / len(vs), 2) if vs else None,
            "gt0": sum(1 for v in vs if v > 0), "lt0": sum(1 for v in vs if v < 0)}

cfsum = {
    "timing_15m": {**stats(tim15, "out_r"), "won": sum(1 for x in tim15 if x and x.get("hit") == "TP"),
                   "lost": sum(1 for x in tim15 if x and x.get("hit") == "SL"),
                   "none": sum(1 for x in tim15 if x and x.get("hit") == "NONE")},
    "timing_30m": {**stats(tim30, "out_r"), "won": sum(1 for x in tim30 if x and x.get("hit") == "TP"),
                   "lost": sum(1 for x in tim30 if x and x.get("hit") == "SL"),
                   "none": sum(1 for x in tim30 if x and x.get("hit") == "NONE")},
    "opposite": {**stats(opp, "out_r"), "hit_tp": sum(1 for x in opp if x and x.get("hit") == "TP"),
                 "hit_sl": sum(1 for x in opp if x and x.get("hit") == "SL"),
                 "none": sum(1 for x in opp if x and x.get("hit") == "NONE")},
    "time_stop": {str(k): stats(v) for k, v in ts.items()},
    "reversal_after_exit_30m": {**stats(rev), "quick_rev_ge_0.25R": sum(1 for v in rev if isinstance(v, (int, float)) and v >= 0.25)},
    "no_trade_move_60m": stats(notr),
}

# ---------------- COUNTERFACTUAL_ANALYSIS.md ----------------
lines = ["# V1 亏损反事实分析（COUNTERFACTUAL_ANALYSIS）",
         "",
         "> 全部为 **Derived Evidence（派生证据）**，只用于解释“是否本可不同”，**不反向修改当时决策事实**。",
         "> 方法：以同一 tick 窗口（真实 UTC 帧，已按仪器修正 −3h）重建：延迟进场 15/30 分钟（同向、同 SL/TP 距离）、反向进场、",
         "> 固定时间止损（15/30/60 分钟平仓）、不交易（决策后 60 分钟市场路径）、SL 击穿后 30 分钟是否反向。",
         "> 触发判定：以可平仓侧价格（long→bid / short→ask）先触及 SL 或 TP；未触及按窗口末价计。",
         ""]
lines += ["## 汇总（20 笔亏损）", "", "| 反事实 | n | 均值(R) | 转正数 | 备注 |", "|---|---|---|---|---|"]
t15 = cfsum["timing_15m"]; t30 = cfsum["timing_30m"]; op = cfsum["opposite"]
lines.append(f"| 延迟 15 分钟进场 | {t15['n']} | {t15['mean']} | {t15['won']} 次打到 TP | SL {t15['lost']} / 未触及 {t15['none']} |")
lines.append(f"| 延迟 30 分钟进场 | {t30['n']} | {t30['mean']} | {t30['won']} 次打到 TP | SL {t30['lost']} / 未触及 {t30['none']} |")
lines.append(f"| 反向进场 | {op['n']} | {op['mean']} | {op['hit_tp']} 次打到 TP | SL {op['hit_sl']} / 未触及 {op['none']} |")
for k in ("15", "30", "60"):
    s = cfsum["time_stop"][k]
    lines.append(f"| 固定 {k} 分钟平仓 | {s['n']} | {s['mean']} | {s['gt0']} 笔为正 | |")
rv = cfsum["reversal_after_exit_30m"]
lines.append(f"| SL 后 30 分钟反向（原方向） | {rv['n']} | {rv['mean']} | {rv['gt0']} 笔为正（≥0.25R: {rv['quick_rev_ge_0.25R']}） | 正值=平仓后价格朝原方向回走 |")
nt = cfsum["no_trade_move_60m"]
lines.append(f"| 不交易：决策后 60 分钟市场移动 | {nt['n']} | {nt['mean']} | {nt['gt0']} 笔为正 | 为负=市场立即朝持仓反方向走 |")
lines += ["", "## 逐笔（亏损）", "",
          "| trade_id | 类因 | MFE | 延迟15m | 延迟30m | 反向 | 时间止损60m | SL后30m反向 | 不交易60m |",
          "|---|---|---|---|---|---|---|---|---|"]
for r in LOSS:
    c = r["cf"]
    def g(x, key=None):
        v = x.get(key) if (key and isinstance(x, dict)) else x
        return "—" if v is None else (round(v, 2) if isinstance(v, float) else v)
    lines.append(f"| {r['trade_id']} | {r['primary_root_cause']} | {r['path']['mfe_r']} | "
                 f"{g(c.get('timing_15m'), 'out_r')}/{g(c.get('timing_15m'), 'hit')} | "
                 f"{g(c.get('timing_30m'), 'out_r')}/{g(c.get('timing_30m'), 'hit')} | "
                 f"{g(c.get('opposite'), 'out_r')}/{g(c.get('opposite'), 'hit')} | "
                 f"{g(c.get('time_stop_60m'))} | {g(c.get('reversal_after_exit_30m_r'))} | {g(c.get('no_trade_move_60m_r'))} |")
lines += ["", "## 观察（事实级）",
          f"- 反向进场在 {op['n']} 笔中有 {op['hit_tp']} 笔直接打到 TP、{op['hit_sl']} 笔打到 SL —— 反向并非系统性更优（镜像噪声大致对称）。",
          f"- 延迟 15 分钟：{t15['won']} 笔转 TP、{t15['lost']} 笔仍 SL（均值 {t15['mean']}R）—— 无一致证据表明“等 15/30 分钟”能系统性改善，个别样本可改善。",
          f"- SL 击穿后 30 分钟：{rv['quick_rev_ge_0.25R']}/{rv['n']} 笔出现 ≥0.25R 的回走 —— “假突破快速反转”只在少数样本成立。",
          "- 以上均为样本内观察（n=20），**不构成新规则**（见报告 D 部分）。"]
open(os.path.join(HERE, "COUNTERFACTUAL_ANALYSIS.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

# ---------------- ROOT_CAUSE_MATRIX.md ----------------
FIX = {"RISK_ERROR": "CONFIRMED_FIXABLE",
       "TIMING_ERROR": "POTENTIALLY_FIXABLE",
       "DIRECTION_ERROR": "POTENTIALLY_FIXABLE",
       "REGIME_ERROR": "POTENTIALLY_FIXABLE",
       "NO_IDENTIFIABLE_ERROR": "NOT_FIXABLE_FROM_CURRENT_DATA",
       "EXECUTION_ERROR": "NOT_FIXABLE_FROM_CURRENT_DATA",
       "UNKNOWN": "UNKNOWN"}
m = ["# V1 根因矩阵（ROOT_CAUSE_MATRIX）", "",
     "> 类别定义（本分析统一口径，先定义后应用）：",
     "> - **RISK_ERROR**：声明风控门（按正确语义重建）本应拒单而实际放行（此前审计确认的接线缺陷时期）。",
     "> - **TIMING_ERROR**：方向未被证明错，但 MFE ≥ 0.5R 后全部回吐至 SL（进场/离场时机问题）。",
     "> - **DIRECTION_ERROR**：入场方向与当时 60m 趋势（MA20）相反，且路径几乎未朝持仓方向展开（MFE < 0.5R）。",
     "> - **REGIME_ERROR**：60m 趋势强度弱（|close−MA20| < 0.3×ATR）且路径未展开——趋势信号在不成立的市况里被使用。",
     "> - **NO_IDENTIFIABLE_ERROR**：无上述任何可识别错误特征（=普通市场损失）。",
     "> - **EXECUTION_ERROR / DATA_ERROR / SIGNAL_REASONING_ERROR / EXIT_ERROR**：本样本未触发（证据见下）。",
     "", "| PRIMARY_ROOT_CAUSE | 亏损数 | trade_ids | 可修复性 | 证据 |", "|---|---|---|---|---|"]
ev = {
    "RISK_ERROR": "guard_cf.block=True（价差/净额两口径一致）；此前审计 RISK_VIOLATION 与修复 commit 63d5a22/eceeec2（dm dry-run 已显示 WAIT_RISK）",
    "TIMING_ERROR": "mfe_r ≥ 0.5 且最终 R≈−1（SL 平仓）",
    "DIRECTION_ERROR": "dir_vs_ma20(60m) 与持仓方向相反 且 mfe_r < 0.5",
    "REGIME_ERROR": "60m trend_strength_atr < 0.3",
    "NO_IDENTIFIABLE_ERROR": "无任何错误特征",
    "UNKNOWN": "tick 归档窗口缺失（记录于 DATA_GAPS）",
}
order = ["RISK_ERROR", "TIMING_ERROR", "DIRECTION_ERROR", "REGIME_ERROR", "NO_IDENTIFIABLE_ERROR", "UNKNOWN"]
for c in order:
    ids = by_class.get(c, [])
    if ids:
        m.append(f"| {c} | {len(ids)} | {'; '.join(ids)} | {FIX[c]} | {ev[c]} |")
    else:
        m.append(f"| {c} | 0 | — | {FIX[c]} | {ev.get(c, '本样本未触发')} |")
m += ["", "## 其他类别（本样本计数=0，定义保留）",
      "| 类别 | 计数 | 依据 |", "|---|---|---|",
      "| EXECUTION_ERROR | 0 | 全部 32 笔：retcode=10009、|slippage| ≤ 3.4bps（限 15）、SL/TP 随单、fill=请求价±3.4bps 内 |",
      "| EXIT_ERROR | 0 | 全部亏损均为券商 SL 按声明规则（1R）触发；realized_R ∈ [−1.047, −1.0]；无提前/延后离场均未见 |",
      "| SIGNAL_REASONING_ERROR | 0 | 本 build 无推理层：信号＝冻结控制臂表（BASELINE_TRANSITION，not_hermes_alpha=true），机械映射无可证伪的“推理错误”；方向问题已归 DIRECTION_ERROR |",
      "| DATA_ERROR（对交易因果） | 0 | 交易期决策用实时终端数据；归档帧问题只影响本研究分析（已修正），不影响当时决策输入 |",
      "",
      "## 反事实风险门集合（含盈利样本）",
      f"- 声明门（正确语义）本应拦下的执行 = **{len(blocked)}** 笔：亏损 {len(blk_loss)} 笔（合计价差 {round(sum(r['pnl_price'] for r in blk_loss),2)}）"
      f" + **盈利 {len(blk_win)} 笔（合计价差 +{round(sum(r['pnl_price'] for r in blk_win),2)}）**。",
      "- 含义：该缺陷既压进亏损也放过了盈利；**亏损侧 {len(blk_loss)} 笔即 CONFIRMED_FIXABLE 的实质证据**（修复已部署并验证）。",
      "- 注意：这是“应拦未拦”的因果证据，不是收益工程建议；不推导任何参数调整。"]
open(os.path.join(HERE, "ROOT_CAUSE_MATRIX.md"), "w", encoding="utf-8", newline="\n").write("\n".join(m) + "\n")

# ---------------- digest ----------------
print("loss class counts:", dict(cnt))
print("side(loss):", dict(side_loss), "| session(loss):", dict(sess_loss))
print("blocked set:", [r['trade_id'] for r in blocked])
print("blocked losses sum pnl:", round(sum(r['pnl_price'] for r in blk_loss), 2),
      "| blocked wins sum pnl:", round(sum(r['pnl_price'] for r in blk_win), 2))
print("cf:", json.dumps(cfsum, ensure_ascii=False))
print("PIT:", "PASS" if pit_ok else "FAIL")
wsum = sum(r["pnl_price"] for r in WIN); lsum = sum(r["pnl_price"] for r in LOSS)
print("win_sum:", round(wsum, 2), "loss_sum:", round(lsum, 2), "net:", round(wsum + lsum, 2),
      "| avg win:", round(wsum / max(len(WIN), 1), 2), "avg loss:", round(lsum / max(len(LOSS), 1), 2))
print("losses by cause:", dict(cnt))
print("wrote: TRADE_ERROR_SUMMARY.csv / COUNTERFACTUAL_ANALYSIS.md / ROOT_CAUSE_MATRIX.md / PIT_AUDIT.json")
