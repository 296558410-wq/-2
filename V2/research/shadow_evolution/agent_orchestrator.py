# -*- coding: utf-8 -*-
"""agent_orchestrator.py — Hermes 真编排(agent/LLM) + 明确的启发式回退，用于 V2 Evolution Shadow。

三条路径（**按可用性**，绝不伪造 LLM 结论）:
  1) llm      : 若配置 V2_SHADOW_LLM_URL/V2_SHADOW_LLM_KEY → 真调用（生产环境用）。
  2) external : 由外部编排器(审计/人工/LLM)产出后经 --from-file 注入（记 prompt_hash/output_hash）。
  3) heuristic: 无 LLM 时的**独立证据式**决策函数（非 reference_rules 优先级），显式标注来源，
               用于让 shadow 在无 LLM 环境也能逐周期产出对照行。

铁律: 不写 V2 状态；不投票；WAIT 正常；不下单；不使用未来信息。
"""
from __future__ import annotations
import hashlib, json, os, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes")); sys.path.insert(0, str(V2))
import context as CTX  # noqa: E402
import discovery as DISC  # noqa: E402
import hermes as H  # noqa: E402

CTX.CTX_DIR = HERE / "decision_contexts"
PROMPT = V2 / "hermes" / "PROMPT.md"
MODEL_ID = "deepseek/deepseek-v4-flash"
SYSTEM = ("你是 Hermes（V2）。基于冻结的 decision_context 与候选机会，做 TRADE/WAIT/REJECT 决策。"
          "铁律：不投票；WAIT 是正常结果；只产决策，不下单；不得使用未来信息；输出必须是 JSON。")

_HEUR_AGENT = "hermes_heuristic(evidence-based, no-llm)"

def _sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

# ---- as-of PIT freshness (faithful replay: age measured at the cycle time, not 'now') ----
def asof_freshness(a1, a2, ref_epoch):
    _te = CTX._to_epoch
    def data_ts(a):
        es = []
        for v in ((a.get("data_quality") or {}).get("by_tf") or {}).values():
            x = _te((v or {}).get("last_bar_ts"))
            if x is not None: es.append(x)
        return max(es) if es else None
    def macro_ts(a):
        es = []
        for k in ("usd", "rates"):
            x = _te(((a.get("macro") or {}).get(k) or {}).get("data_ts"))
            if x is not None: es.append(x)
        return max(es) if es else None
    def label(age, kind):
        if age is None: return "unknown", None
        thr = (1200, "fresh"), (3600, "stale")
        if kind == "agent2": thr = (4500, "fresh"), (10800, "stale")
        for t, l in thr:
            if age < t: return l, int(age)
        return "expired", int(age)
    a1d, a2d = data_ts(a1), macro_ts(a2)
    f1 = label(None if a1d is None else ref_epoch - a1d, "agent1")
    f2 = label(None if a2d is None else ref_epoch - a2d, "agent2")
    return {"agent1": {"data_ts": a1d, "status": f1[0], "age_seconds": f1[1]},
            "agent2": {"data_ts": a2d, "status": f2[0], "age_seconds": f2[1]}}

def context_asof(cycle, a1path, a2path):
    """构建 as-of 冻结 context：freshness/health 以 cycle 时刻计（PIT 忠实回放）。"""
    ctx, p = CTX.build_context(cycle, a1path, a2path)
    a1 = json.loads(Path(a1path).read_text(encoding="utf-8"))
    a2 = json.loads(Path(a2path).read_text(encoding="utf-8"))
    try: ref_epoch = float(a1.get("generated_utc") and __import__("datetime").datetime.fromisoformat(a1["generated_utc"]).timestamp())
    except Exception: ref_epoch = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp()
    fr = asof_freshness(a1, a2, ref_epoch)
    router = False
    try: router = (V2 / "config" / "data_router.enabled").read_text(encoding="utf-8").strip().lower() in ("1","true","yes","on")
    except Exception: pass
    health = CTX.build_health(a1, a2, fr["agent1"]["status"], fr["agent2"]["status"], router)
    # 关键: gate() 读的是顶层 ctx["agent1"]["freshness"]，必须一并按 as-of 覆写
    ctx["freshness"] = fr
    ctx["agent1"]["freshness"] = fr["agent1"]["status"]
    ctx["agent1"]["age_seconds"] = fr["agent1"]["age_seconds"]
    ctx["agent2"]["freshness"] = fr["agent2"]["status"]
    ctx["agent2"]["age_seconds"] = fr["agent2"]["age_seconds"]
    ctx["health"] = health
    return ctx, a1, a2, p

def prompt_pack(ctx, cands, tags):
    prompt_md = PROMPT.read_text(encoding="utf-8") if PROMPT.exists() else ""
    user = json.dumps({"decision_context": ctx, "candidates": cands, "hermes_regime_tags": tags,
                       "prompt_md": prompt_md}, ensure_ascii=False, sort_keys=True)
    return {"system": SYSTEM, "user": user, "model": MODEL_ID,
            "prompt_hash": _sha({"system": SYSTEM, "user": user, "model": MODEL_ID}),
            "input_hash": _sha({"context_hash": ctx.get("context_hash"), "candidates": [c["id"] for c in cands]})}

# ---- 3) heuristic agent path (independent evidence-based decision) ----
def heuristic_decide(ctx, a1, a2, cands, tags):
    d = {"decision_source": "llm", "signal_from_agents": True, "agent_llm": "AGENT_LLM_UNAVAILABLE",
         "agent_source": _HEUR_AGENT, "model": None, "reason": "", "chosen_opportunity": None,
         "confidence": None, "regime_tags": tags, "plan": None, "risk_reason": None,
         "context_id": ctx.get("context_id"), "context_hash": ctx.get("context_hash"),
         "instrument": "XAUUSD", "reference_market": "GC_F", "live_trading": False}
    ov = (ctx.get("health") or {}).get("overall_status")
    if ov == "FAIL":
        d.update({"decision": "REJECT", "reason": "data health FAIL"}); return d
    if ov == "DEGRADED":
        d.update({"decision": "WAIT", "reason": f"data health DEGRADED (freshness a1={ctx['freshness']['agent1']['status']})"}); return d
    if not cands:
        d.update({"decision": "WAIT", "reason": "no candidate"}); return d
    gt = (a2 or {}).get("gold_macro_state", "UNCERTAIN")
    elig = []
    for c in cands:
        dirn = c.get("dir_hint")
        if dirn is None: continue
        if (dirn == "LONG" and gt == "BEARISH") or (dirn == "SHORT" and gt == "BULLISH"): continue
        if c.get("priced_in") == "HIGH": continue
        if c.get("requires_confirmation"): continue
        if (c.get("expected_R_est") or 0) < 1.0: continue
        if not c.get("counter_thesis"): continue
        elig.append(c)
    if not elig:
        d.update({"decision": "WAIT", "confidence": 0.3,
                  "reason": "no candidate survives evidence screen (macro-align / priced_in / confirmation / R / counter-thesis)"})
        return d
    # 选 evidence 最强: 期望 R × 已定价折扣
    elig.sort(key=lambda c: (c.get("expected_R_est") or 0) * (1.0 if c.get("priced_in") == "LOW" else 0.7), reverse=True)
    c = elig[0]; dirn = c["dir_hint"]
    price = (ctx.get("market") or {}).get("primary_last")
    plan = H.build_plan(c, price)
    d.update({"decision": "TRADE", "chosen_opportunity": c["id"], "confidence": 0.6,
              "reason": "evidence screen pass (macro-align, not priced-in, confirmed, R ok, counter-thesis present)",
              "plan": plan, "direction": dirn})
    return d

def orchestrate_llm(ctx, a1, a2, cands, tags, llm_decision=None):
    """**真 LLM Agent** 路径。无端点/密钥 ⇒ 显式 LLM_UNAVAILABLE（绝不静默退化冒充）。"""
    if llm_decision is not None:
        d = dict(llm_decision); d.setdefault("agent_source", "true_llm_agent(external)"); d.setdefault("agent_llm", "OK"); return d
    url = os.environ.get("V2_SHADOW_LLM_URL"); key = os.environ.get("V2_SHADOW_LLM_KEY")
    pack = prompt_pack(ctx, cands, tags)
    if not (url and key):
        return {"decision": "LLM_UNAVAILABLE", "agent_llm": "LLM_UNAVAILABLE",
                "agent_source": "true_llm_agent", "reason": "no LLM endpoint/key (V2_SHADOW_LLM_URL/KEY unset); NOT degraded to heuristic",
                "context_id": ctx.get("context_id"), "context_hash": ctx.get("context_hash"),
                "regime_tags": tags, "prompt_hash": pack["prompt_hash"], "input_hash": pack["input_hash"],
                "live_trading": False, "signal_from_agents": True}
    req = urllib.request.Request(url, data=json.dumps({"model": MODEL_ID,
        "messages": [{"role": "system", "content": pack["system"]}, {"role": "user", "content": pack["user"]}],
        "temperature": 0, "response_format": {"type": "json_object"}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"])
    out.update({"agent_source": "true_llm_agent", "agent_llm": "OK", "model": MODEL_ID,
                "prompt_hash": pack["prompt_hash"], "input_hash": pack["input_hash"]})
    out.setdefault("regime_tags", tags); out.setdefault("context_id", ctx.get("context_id"))
    out.setdefault("context_hash", ctx.get("context_hash")); out.setdefault("decision_source", "llm")
    out.setdefault("signal_from_agents", True)
    return out


def orchestrate(ctx, a1, a2, cands, tags, llm_decision=None):
    if llm_decision is not None:
        d = dict(llm_decision); d.setdefault("agent_source", "hermes_orchestrator(external)"); return d
    url = os.environ.get("V2_SHADOW_LLM_URL"); key = os.environ.get("V2_SHADOW_LLM_KEY")
    if url and key:
        pack = prompt_pack(ctx, cands, tags)
        req = urllib.request.Request(url, data=json.dumps({"model": MODEL_ID,
            "messages": [{"role": "system", "content": pack["system"]}, {"role": "user", "content": pack["user"]}],
            "temperature": 0, "response_format": {"type": "json_object"}}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"])
        out.setdefault("agent_source", "hermes_orchestrator(agent-llm)"); out["agent_llm"] = "OK"; out["model"] = MODEL_ID
        out.setdefault("regime_tags", tags); out.setdefault("context_id", ctx.get("context_id"))
        out.setdefault("context_hash", ctx.get("context_hash"))
        return out
    return heuristic_decide(ctx, a1, a2, cands, tags)
