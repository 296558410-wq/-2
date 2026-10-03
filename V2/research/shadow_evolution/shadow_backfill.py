# -*- coding: utf-8 -*-
"""shadow_backfill.py — 用**历史归档快照**逐周期产出 Shadow 决策（reference + agent），
并回填 outcome 链（MFE/MAE/future return/TP-SL path/时间窗口）。隔离、只读 V2、order_send=0。

输入: state/snapshots/agent1_<cycle>.json + agent2_<cycle>.json（V2 每周期归档的完整快照）
输出: SHADOW_DECISIONS.jsonl / SHADOW_OUTCOMES.jsonl / _backfill_stats.json
"""
from __future__ import annotations
import glob, hashlib, json, os, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes")); sys.path.insert(0, str(V2)); sys.path.insert(0, str(HERE))
import context as CTX, discovery as DISC, hermes as H  # noqa: E402
import agent_orchestrator as AO  # noqa: E402
CTX.CTX_DIR = HERE / "decision_contexts"

SNAP = V2 / "state" / "snapshots"


def _sha(o): return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def pairs(limit=None):
    out = []
    for f in sorted(glob.glob(str(SNAP / "agent1_*.json"))):
        cyc = re.search(r"agent1_(.+)\.json$", f).group(1)
        a2 = SNAP / f"agent2_{cyc}.json"
        if a2.exists(): out.append((cyc, f, str(a2)))
    return out[-limit:] if limit else out


def decide_row(side, cyc, ctx, a1, a2, cands, tags, d, input_hash):
    return {"shadow_side": side, "cycle": cyc, "ts_utc": d.get("ts") or ctx.get("created_utc"),
            "context_id": ctx.get("context_id"), "context_hash": ctx.get("context_hash"),
            "health_overall": (ctx.get("health") or {}).get("overall_status"),
            "a1_freshness": (ctx.get("freshness") or {}).get("agent1", {}).get("status"),
            "a2_freshness": (ctx.get("freshness") or {}).get("agent2", {}).get("status"),
            "market_primary_last": (ctx.get("market") or {}).get("primary_last"),
            "decision": d.get("decision"), "decision_source": d.get("decision_source"),
            "signal_from_agents": d.get("signal_from_agents"), "agent_llm": d.get("agent_llm"),
            "agent_source": d.get("agent_source"),
            "direction": ((d.get("plan") or {}).get("direction")) or d.get("direction"),
            "opportunity": d.get("chosen_opportunity"), "confidence": d.get("confidence") or (d.get("plan") or {}).get("confidence"),
            "reason": d.get("reason"), "regime_tags": d.get("regime_tags") or tags,
            "risk_reason": d.get("risk_reason") or d.get("no_trade_reason"),
            "plan": d.get("plan"), "candidates": [c["id"] for c in cands],
            "input_hash": input_hash,
            "decision_hash": _sha({k: d.get(k) for k in ("decision", "chosen_opportunity", "reason", "plan", "regime_tags")})}


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    ps = pairs(limit)
    dec_f = open(HERE / "SHADOW_DECISIONS.jsonl", "w", encoding="utf-8", newline="\n")
    n = 0
    for cyc, a1p, a2p in ps:
        ctx, a1, a2, _ = AO.context_asof(cyc, a1p, a2p)
        cands = DISC.discover(ctx, a1, a2); tags = DISC.regime_tags(ctx, a1, a2)
        ref, _, _ = H.decide_pure(ctx, a1, a2, source="reference_rules")
        ref["ts"] = ctx.get("created_utc")
        pack = AO.prompt_pack(ctx, cands, tags)
        ag = AO.orchestrate(ctx, a1, a2, cands, tags)
        ag.setdefault("ts", ref["ts"])
        for side, d in (("reference", ref), ("agent", ag)):
            dec_f.write(json.dumps(decide_row(side, cyc, ctx, a1, a2, cands, tags, d, pack["input_hash"]), ensure_ascii=False) + "\n")
            n += 1
    dec_f.close()
    print("cycles:", len(ps), "rows:", n, "->", HERE / "SHADOW_DECISIONS.jsonl")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
