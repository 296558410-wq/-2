# -*- coding: utf-8 -*-
"""discovery_shadow.py — 新 Opportunity Discovery（Shadow；与 reference 逐周期对照）。

结构改动（**不动任何阈值/触发条件**）：
  1) 候选生成 = 复用 reference `discovery.discover()` 的**完全相同条件**（零阈值变更）；
  2) **生成与排序分离**：`rank()` 独立打分（不再用 first-hit 类别优先级）；
  3) **presence vs trigger 区分**：常驻型来源（geo/macro/narrative 等 requires_confirmation 类）
     在缺乏可观察 follow-through 时标 `presence_only=True`（仍计入供给统计，但**不作为首选**）；
  4) 一个来源不能因为"存在"就垄断**选择**：`select()` 先取有 trigger 的最强候选，presence-only 仅在无其它候选时兜底。
  ⇒ 不降低门槛、不制造交易；只改变"选谁"的结构。

`reference` = 原 `discovery.discover()`（保持不变）。
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes"))
import discovery as DISC  # noqa: E402

SOURCE_OF = {"opp_trend_long": "trend", "opp_trend_short": "trend",
             "opp_bo_long": "breakout", "opp_bo_short": "breakout",
             "opp_fbo_short": "false_breakout", "opp_fbo_long": "false_breakout",
             "opp_macro_repricing_long": "macro_repricing", "opp_macro_repricing_short": "macro_repricing",
             "opp_geo_shock": "geopolitical", "opp_narrative_flow_divergence": "narrative_flow"}
# 常驻型（"存在即生成"）来源；无 follow-through 证据时仅作 presence_only
PRESENCE_SOURCES = {"geopolitical", "macro_repricing", "narrative_flow"}


def discover_shadow(ctx, a1, a2):
    """与 reference 完全相同的生成条件；仅补 source 标签与 presence_only 标记。"""
    cands = DISC.discover(ctx, a1, a2)          # ← 零阈值变更
    for c in cands:
        c = dict(c)
        c["source"] = SOURCE_OF.get(c["id"], "other")
        # trigger 可观察性：requires_confirmation=True 且无明确跟随确认 ⇒ presence_only
        c["presence_only"] = bool(c.get("requires_confirmation") and c["source"] in PRESENCE_SOURCES)
    return [dict(c, source=SOURCE_OF.get(c["id"], "other"),
                 presence_only=bool(c.get("requires_confirmation") and SOURCE_OF.get(c["id"], "other") in PRESENCE_SOURCES))
            for c in cands]


def rank(cands, ctx, a1, a2):
    """独立排序（确定性；**不用 outcome**）。score 高者优先。"""
    def score(c):
        s = 0.0
        s += 2.0 * float(c.get("expected_R_est") or 0.0)          # 期望 R
        s += 1.0 if not c.get("presence_only") else -1.0          # 有触发 > 仅存在
        s += 0.5 if c.get("dir_hint") in ("LONG", "SHORT") else -0.5  # 方向明确
        s += 0.5 if c.get("priced_in") == "LOW" else (0.0 if c.get("priced_in") == "MED" else -0.5)  # 未被定价
        s += 0.4 * len(c.get("evidence_ids") or []) / 5.0          # 证据量（归一）
        s += 0.5 if (c.get("macro_align") in ("NEUTRAL", "BULLISH", "BEARISH")) else 0.0
        return round(s, 4)
    out = sorted(cands, key=lambda c: (-score(c), c["id"]))
    for c in out:
        c["rank_score"] = score(c)
    return out


def select(cands, ctx, a1, a2):
    """选取原则：先取有触发的最高分候选；无则取最高分（含 presence_only）作为**观察**候选。"""
    r = rank(cands, ctx, a1, a2)
    trig = [c for c in r if not c.get("presence_only")]
    return (trig or r or [None])[0], r


def compare(ctx, a1, a2):
    """返回 (reference_cands, shadow_ranked, ref_first_hit, shadow_pick)。"""
    ref = DISC.discover(ctx, a1, a2)
    sh = discover_shadow(ctx, a1, a2)
    # reference 选择 = 原 first-hit 类别优先级
    ref_pick = None
    for cat in DISC.__dict__.get("CATEGORY_PRIORITY", []) or ["false_breakout", "breakout", "trend", "macro_repricing", "geopolitical", "narrative_flow"]:
        hit = [c for c in ref if c.get("category") == cat]
        if hit:
            ref_pick = hit[0]; break
    sh_pick, ranked = select(sh, ctx, a1, a2)
    return ref, ranked, ref_pick, sh_pick
