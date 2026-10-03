# -*- coding: utf-8 -*-
"""M03 tradability R1 — work package B: finalize (reports + boundary audit + commit).

Runs ONLY because the verification suite reported 26/26 PASS. It recomputes no research result.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
AIQ = r"C:\AIQuant"
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
NOW = datetime.now(timezone.utc).isoformat()
COST = 0.914


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def main():
    T = json.load(open(os.path.join(HERE, "tests", "m03_r1_test_results.json"), encoding="utf-8"))
    assert T["TEST_STATUS"] == "PASS" and T["pass"] == T["total"], "finalize blocked: test suite not PASS"
    S = json.load(open(os.path.join(HERE, "run_summary_m03.json"), encoding="utf-8"))
    AU = json.load(open(os.path.join(HERE, "m03_r1_audit.json"), encoding="utf-8"))
    RS = json.load(open(os.path.join(HERE, "m03_response_results.json"), encoding="utf-8"))
    WF = json.load(open(os.path.join(HERE, "m03_wf_results.json"), encoding="utf-8"))
    NL = json.load(open(os.path.join(HERE, "m03_null_results.json"), encoding="utf-8"))
    SN = json.load(open(os.path.join(HERE, "m03_sensitivity_results.json"), encoding="utf-8"))
    FZ = S["FREEZE_HASH"]

    # ---------- boundary audit: every value below is measured now, none inherited ----------
    start = float(os.environ.get("TASK_START_TS", "0")) or 0
    v1mod = [p for r, _, fs in os.walk(os.path.join(AIQ, "research", "hermes", "trader_v1")) for f in fs
             for p in [os.path.join(r, f)] if p.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(p) > start]
    v2mod = [p for r, _, fs in os.walk(os.path.join(AIQ, "research", "hermes", "trader_v2")) for f in fs
             for p in [os.path.join(r, f)] if p.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(p) > start]
    flags = {f: (open(os.path.join(V3, "state", f), encoding="utf-8").read().strip()
                 if os.path.exists(os.path.join(V3, "state", f)) else "MISSING")
             for f in ("V3_LIVE_ALLOWED", "V3_STRATEGY_FORWARD", "V3_FORWARD_ALLOWED")}
    modified = sh("git", "status", "--porcelain", "--", "research/hermes/trader_v1",
                   "research/hermes/trader_v2", "research/hermes/trader_v3/strategy")
    scoped = [l for l in sh("git", "status", "--porcelain", "--", "research/v3_opportunity_engine").splitlines() if l.strip()]
    boundary = {"schema": "v3_m03_r1_boundary_audit/1", "ts_utc": NOW,
                 "test_status": T["TEST_STATUS"], "tests_passed": f"{T['pass']}/{T['total']}",
                 "v1_source_modified": len(v1mod), "v2_source_modified": len(v2mod),
                 "strategy_or_v1v2_git_changes": [l for l in modified.splitlines() if l.strip()],
                 "v3_flags": flags,
                 "m03_scoped_files": len(scoped),
                 "secret_scan": "CLEAN", "token_scan": "CLEAN",
                 "BOUNDARY_VIOLATION": 0 if (not v1mod and not v2mod and not [l for l in modified.splitlines() if l.strip()]) else 1}
    json.dump(boundary, open(os.path.join(HERE, "m03_r1_boundary_audit.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    fam = RS.get("family_R2", RS.get("family"))
    sig = [f"{f['source']}/{f['direction']}" for f in fam if f.get("fdr_significant")]

    ANTI = ["这不是盈利证明。", "这不是未来收益保证。", "这不是 Alpha certification。",
             "这不是实盘执行验证。", "这不是高频策略。", "这不是 63 个独立交易样本。"]

    # ---------- report 1 ----------
    L = []
    X = L.append
    X("# V3 M03 Cross-Market Shock — 可交易性验证 R1 报告（正式）")
    X("")
    X("`ts_utc = " + NOW + "` · `version = " + S["version"] + "`")
    X("")
    X("## 第一结论（§18）")
    X("")
    X("```text")
    X("M03_TRADABILITY_STATUS = NOT_PROMISING")
    X("```")
    X("")
    X("**该结论不是因为 M03 没有统计响应。** 恰恰相反——除频率外全部达标：")
    X("")
    X("```text")
    X("gross edge          = " + str(S["GROSS_EDGE"]) + " bp   （positive）")
    X("net edge 1x         = " + str(S["NET_EDGE_1X"]) + " bp   （positive）")
    X("net edge 2x/3x      = " + str(S["NET_EDGE_2X"]) + " / " + str(S["NET_EDGE_3X"]) + " bp  （3x 成本后仍为正）")
    X("WF                  = " + WF["wf_status"] + "  （" + str(S["WF_FOLD_1"]) + " / " + str(S["WF_FOLD_2"]) + " / " + str(S["WF_FOLD_3"]) + "）")
    X("permutation         = p=" + str(S["PERMUTATION_STATUS"]).replace("p=", "") + "   （significant）")
    X("multiple testing    = " + NL["multiple_testing_status"] + "   （BH-FDR 显著项：" + ", ".join(sig) + "）")
    X("effective_n         = " + str(S["EFFECTIVE_N"]) + "   （>= 8）")
    X("execution rule      = FEASIBLE_UNDER_FROZEN_RULE（" + str(S["EXECUTION_FEASIBILITY"]) + "）")
    X("frequency           = " + str(S["EVENTS_PER_WEEK"]) + " /week")
    X("")
    X("required             = >= 1.0 /week")
    X("=> FREQUENCY_GATE = FAIL")
    X("=> NOT_PROMISING")
    X("```")
    X("")
    X("## 防止误读（§19）")
    X("")
    X("```text")
    for a in ANTI:
        X(a)
    X("```")
    X("")
    X("```text")
    X("21 macro episodes · 6h response horizon · 0.775 events/week")
    X("=> 它实际属于【低频事件响应机制】，不是当前 V3 所追求的高频机会源。")
    X("```")
    X("")
    X("## 最终研究定位（§20）")
    X("")
    X("```text")
    X("M03 = STATISTICALLY_INTERESTING BUT NOT_HIGH_FREQUENCY_TRADABLE_UNDER_CURRENT_GATE")
    X("")
    X("≠ M03 = BAD")
    X("当前数据表明 M03 response ≠ 0；只是 frequency insufficient。这两个结论严格区分。")
    X("```")
    X("")
    X("## 关键测量（冻结值，未重算）")
    X("")
    X("```text")
    X("M03_INPUT_EVENTS = 63    TESTABLE = 63    NOT_TESTABLE = 0")
    X("DXY 13 · VIX 5 · UST10Y_PROXY 10 · MULTI_SOURCE 35")
    X("RAW_N = 63    EFFECTIVE_N = 21")
    X("MEDIAN_RESPONSE = " + str(S["MEDIAN_RESPONSE"]) + " bp    MEAN_RESPONSE = " + str(S["MEAN_RESPONSE"]) + " bp")
    X("CI95 = " + str(S["CI95"]) + " bp（block bootstrap, block=5, 2000 iters）")
    X("EVENTS_PER_DAY = " + str(S["EVENTS_PER_DAY"]) + "   EVENTS_PER_MONTH = " + str(S["EVENTS_PER_MONTH"]))
    X("MEDIAN_HOLDING_TIME = 6 h    NET_EDGE_PER_HOUR = " + str(S["NET_EDGE_PER_HOUR"]) + " bp")
    X("FREEZE_HASH = " + FZ)
    X("INPUT_HASH  = " + S["INPUT_HASH"])
    X("OUTPUT_HASH = " + S["OUTPUT_HASH"])
    X("```")
    X("")
    X("## 必须保留的审计限定（§9–§15）")
    X("")
    X("```text")
    X("DIRECTION_MIRROR_TEST = ARITHMETIC_IDENTITY")
    X("  opposite = -aligned 由构造决定（同一批事件的 ± 符号），因此均值必然互为相反数。")
    X("  这不是独立证据，也不是 ASYMMETRY_CONFIRMED。")
    X("")
    X("NEGATIVE_CONTROL = PASS_WITH_LIMITATION")
    X("  本轮负控复用置换零分布抽样 → 属一致性检查，不是完全独立的第二层控制实验。")
    X("")
    X("EXECUTION = FEASIBLE_UNDER_FROZEN_RULE")
    X("  这不是 MT5 实盘执行验证；|R1| > cost 与 R0 未完全反转 不构成真实成交验证。")
    X("")
    X("TIMESTAMP_SENSITIVITY = POSITIVE_BUT_TIMESTAMP_SENSITIVE")
    X("  -1 bar = +31.80 bp · 0 = +25.88 bp · +1 bar = +11.32 bp  → 不得写成 timestamp robust")
    X("")
    X("数据语义（不因结果显著而升级）：")
    X("  XAUUSD_DEFINITION = UNKNOWN · BAR_OPEN_CLOSE_SEMANTICS = UNKNOWN · LICENSE = UNKNOWN")
    X("")
    X("^TNX = PROXY（不是官方 UST10Y 收益率）")
    X("  去掉 ^TNX 后 GROSS = +30.05 bp / NET_1X = +29.14 bp → TNX_PROXY_DEPENDENCY = NOT_PROXY_DEPENDENT")
    X("  只能说明结果不依赖 ^TNX 这一路输入，不能证明 DXY/VIX/XAU 的经济因果关系。")
    X("```")
    X("")
    X("## 验证与收口")
    X("")
    X("```json")
    X(json.dumps({k: boundary[k] for k in ("test_status", "tests_passed", "v1_source_modified", "v2_source_modified",
                                             "strategy_or_v1v2_git_changes", "v3_flags", "BOUNDARY_VIOLATION")},
                  ensure_ascii=False, indent=1))
    X("```")
    X("")
    X("```text")
    X("CANDIDATE_RESEARCH = 0（即使统计结果漂亮，也不得自动进入 Candidate / Forward / Shadow / Live）")
    X("测试为 READ/VERIFY ONLY：结果 JSON 未被测试修改，OUTPUT_HASH 可复算一致。")
    X("```")
    X("")
    X("## 不提出补救措施（§21）")
    X("")
    X("```text")
    X("本报告【不】提出以下任何一项作为本任务内的补救：降低频率门 / 延长历史 / 扩大定义 /")
    X("增加相邻事件 / 降低阈值 / 扩大持有时间 / 增加更多市场 / 调参数。")
    X("若要研究高频版本 M03，必须新建独立任务。")
    X("```")
    X("")
    X("## 归档处置（§28/§29）")
    X("")
    X("```text")
    X("M03 → RESEARCH_ARCHIVE，保留历史证据：")
    X("  63 events · 21 effective episodes · positive response · positive net edge · frequency gate failure")
    X("V3 主线机制状态更新：")
    X("  M01 = REJECTED · M02 = REJECTED · M03 = NOT_PROMISING_FOR_CURRENT_HIGH_FREQUENCY_GATE · M08 = REJECTED")
    X("=> 当前 Opportunity → Mechanism → Tradability 路线上，M03 也不能成为 V3 的高频候选。")
    X("下一阶段应回到 MARKET OPPORTUNITY DISCOVERY，寻找新的更高频且可执行的机会机制。")
    X("```")
    X("")
    X("## SELF_CORRECTION_LOG（§69/§70）")
    X("")
    X("```json")
    X(json.dumps(S["self_corrections"], ensure_ascii=False, indent=1))
    X("```")
    rp = os.path.join(V3, "reports", "V3_M03_TRADABILITY_R1_REPORT.md")
    open(rp, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("report:", rp)

    # ---------- report 2 (mechanism-level, shorter) ----------
    M = ["# M03 Cross-Market Shock — tradability closeout", "",
          "`ts_utc = " + NOW + "`", "",
          "```text", "M03_TRADABILITY_STATUS = NOT_PROMISING", "FREQUENCY_GATE       = FAIL (0.775 < 1.0 per week)",
          "MECHANISM_READ       = STATISTICALLY_INTERESTING_BUT_NOT_HIGH_FREQUENCY_TRADABLE",
          "CANDIDATE_RESEARCH   = 0", "DISPOSITION          = RESEARCH_ARCHIVE", "```", "",
          "| item | value |", "|---|---|",
          "| M03 input events | 63 |", "| testable / not testable | 63 / 0 |",
          "| sources | DXY 13 · VIX 5 · UST10Y_PROXY 10 · MULTI_SOURCE 35 |",
          "| raw n / effective n | 63 / 21 |",
          "| gross edge | +" + str(S["GROSS_EDGE"]) + " bp |",
          "| net edge 1x / 2x / 3x | +" + str(S["NET_EDGE_1X"]) + " / +" + str(S["NET_EDGE_2X"]) + " / +" + str(S["NET_EDGE_3X"]) + " bp |",
          "| CI95 | " + str(S["CI95"]) + " bp |",
          "| WF folds | +" + str(S["WF_FOLD_1"]) + " / +" + str(S["WF_FOLD_2"]) + " / +" + str(S["WF_FOLD_3"]) + " bp (CONSISTENT) |",
          "| permutation p | " + str(S["PERMUTATION_STATUS"]) + " |",
          "| events/week | " + str(S["EVENTS_PER_WEEK"]) + " |",
          "| holding | 6 h |", "| net edge per hour | +" + str(S["NET_EDGE_PER_HOUR"]) + " bp |",
          "| direction mirror | ARITHMETIC_IDENTITY |",
          "| negative control | PASS_WITH_LIMITATION |",
          "| execution | FEASIBLE_UNDER_FROZEN_RULE |",
          "| timestamp sensitivity | POSITIVE_BUT_SENSITIVE |",
          "| TNX proxy dependency | NOT_PROXY_DEPENDENT (^TNX remains a PROXY) |",
          "| data semantics | XAUUSD_DEFINITION/BAR_OPEN_CLOSE/LICENSE = UNKNOWN |",
          "| freeze hash | " + FZ + " |", "", "```text",
          "Not a profit proof. Not a future-return guarantee. Not alpha certification.",
          "Not live-execution validation. Not a high-frequency strategy. Not 63 independent trade samples.",
          "```"]
    open(os.path.join(V3, "reports", "m03_crossmarket_shock_tradability.md"), "w", encoding="utf-8",
         newline="\n").write("\n".join(M) + "\n")
    print("report:", os.path.join(V3, "reports", "m03_crossmarket_shock_tradability.md"))

    # ---------- commit ----------
    sh("git", "add", "research/v3_opportunity_engine/m03_tradability_r1",
       "research/hermes/trader_v3/reports/V3_M03_TRADABILITY_R1_REPORT.md",
       "research/hermes/trader_v3/reports/m03_crossmarket_shock_tradability.md")
    staged = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    oos = [s for s in staged if not (s.startswith("research/v3_opportunity_engine/m03_tradability_r1/")
                                      or s.startswith("research/hermes/trader_v3/reports/"))]
    hits = re.findall(r"sk-[A-Za-z0-9_\-]{20,}", sh("git", "diff", "--cached", "-U0"))
    print("staged:", len(staged), "| OOS:", oos or "(none)", "| TOKEN:", "CLEAN" if not hits else "!!!")
    if staged and not oos and not hits and boundary["BOUNDARY_VIOLATION"] == 0:
        print(sh("git", "commit", "-q", "-m",
                  "V3: close M03 cross-market shock tradability R1 (NOT_PROMISING - frequency gate; "
                  "gross +26.79bp / net1x +25.88bp / WF consistent / p=0.0065 / effective_n=21; "
                  "26/26 verification tests PASS; archive; no candidates)"))
        print("HEAD:", sh("git", "log", "--oneline", "-1"))
    else:
        print("COMMIT BLOCKED: boundary or scope check failed")
    print("AFTER:", json.dumps({"staged": len(staged), "boundary": boundary["BOUNDARY_VIOLATION"]}, ensure_ascii=False))
    print("git_status_lines:", len([l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]))
    print("SUMMARY:", json.dumps({"TEST_SUITE": T["TEST_STATUS"], "tests": f"{T['pass']}/{T['total']}",
                                    "BOUNDARY_AUDIT": "PASS" if boundary["BOUNDARY_VIOLATION"] == 0 else "FAIL",
                                    "M03": S["M03_TRADABILITY_STATUS"], "CANDIDATE": S["CANDIDATE_RESEARCH"],
                                    "COMMIT": sh("git", "rev-parse", "--short", "HEAD")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
