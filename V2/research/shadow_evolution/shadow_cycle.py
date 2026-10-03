# -*- coding: utf-8 -*-
"""shadow_cycle.py — V2 Evolution Shadow 周期入口（隔离、只读 V2、order_send=0）。

对**同一个冻结 PIT 快照**同时产出两条决策:
  A. reference_rules  (与当前 V2 生产完全相同的确定性参照器)  ← hermes.decide_pure(source=reference_rules)
  B. agent 真编排      (Agent1+Agent2+Hermes LLM 编排)          ← agent_orchestrator / 外部注入
两者共享 同一 context_id / context_hash / 数据快照 / 采集时刻；各自记录 input_hash + decision_hash。

绝不写入 V2 state/ledger；只写本目录 (shadow_evolution/)。
用法:
  python shadow_cycle.py                      # 跑当前窗口，agent 路径按可用性自动处理
  python shadow_cycle.py --cycle 2026-10-02T14:00Z
  python shadow_cycle.py --agent-decision <file.json>   # 注入外部编排(LLM)决策
  python shadow_cycle.py --emit-input <out.json>        # 输出冻结输入(供外部编排)
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes")); sys.path.insert(0, str(V2)); sys.path.insert(0, str(HERE))
import context as CTX  # noqa: E402
import hermes as H     # noqa: E402
import discovery as DISC  # noqa: E402
import agent_orchestrator as AO  # noqa: E402

CTX.CTX_DIR = HERE / "decision_contexts"
DEC = HERE / "SHADOW_DECISIONS.jsonl"


def _sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _inputs():
    a1 = json.loads((V2 / "state" / "agent1_latest.json").read_text(encoding="utf-8"))
    a2 = json.loads((V2 / "state" / "agent2_latest.json").read_text(encoding="utf-8"))
    return a1, a2


def _row(side, ctx, a1, a2, cands, tags, d, input_hash):
    return {
        "shadow_side": side,                       # "reference" | "agent"
        "cycle": ctx.get("cycle"), "ts_utc": d.get("ts"),
        "context_id": ctx["context_id"], "context_hash": ctx["context_hash"],
        "data_snapshot": {"a1_cycle": a1.get("cycle"), "a1_generated_utc": a1.get("generated_utc"),
                          "a2_cycle": a2.get("cycle"), "a2_snapshot_ts": a2.get("snapshot_ts"),
                          "market_primary_last": (ctx.get("market") or {}).get("primary_last")},
        "decision": d.get("decision"), "decision_source": d.get("decision_source"),
        "signal_from_agents": d.get("signal_from_agents"),
        "direction": ((d.get("plan") or {}).get("direction")) or d.get("direction"),
        "opportunity": d.get("chosen_opportunity"), "confidence": d.get("confidence") or (d.get("plan") or {}).get("confidence"),
        "reason": d.get("reason"), "regime_tags": d.get("regime_tags") or tags,
        "risk_reason": d.get("risk_reason") or d.get("no_trade_reason"),
        "candidates": [c["id"] for c in cands],
        "input_hash": input_hash,
        "decision_hash": _sha({k: d.get(k) for k in ("decision", "chosen_opportunity", "reason", "plan", "regime_tags")}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", default=None)
    ap.add_argument("--agent-decision", default=None)
    ap.add_argument("--emit-input", default=None)
    a = ap.parse_args()
    a1, a2 = _inputs()
    ctx, _ = CTX.build_context(a.cycle or a1.get("cycle"))
    ref_d, cands, tags = H.decide_pure(ctx, a1, a2, source="reference_rules")
    ref_d["ts"] = datetime.now(timezone.utc).isoformat()
    inp = AO.build_input(a.cycle or a1.get("cycle"))
    if a.emit_input:
        Path(a.emit_input).write_text(json.dumps({"context": ctx, "candidates": cands, "regime_tags": tags,
                                                  "prompt_hash": inp["prompt_hash"], "input_hash": inp["input_hash"],
                                                  "system": inp["system"], "model": inp["model"]},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
        print("emitted:", a.emit_input); return
    if a.agent_decision:
        llm_out = json.loads(Path(a.agent_decision).read_text(encoding="utf-8"))
        llm_out.setdefault("agent_source", "hermes_orchestrator(external)")
        agent_d = AO.normalize(llm_out, ctx, cands)
    else:
        agent_d, _ = AO.orchestrate(a.cycle or a1.get("cycle"))
    agent_d["ts"] = ref_d["ts"]                    # 同时间戳
    rows = [_row("reference", ctx, a1, a2, cands, tags, ref_d, inp["input_hash"]),
            _row("agent", ctx, a1, a2, cands, tags, agent_d, inp["input_hash"])]
    with open(DEC, "a", encoding="utf-8", newline="\n") as fh:
        for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (HERE / "latest.json").write_text(json.dumps({"context_id": ctx["context_id"], "cycle": ctx.get("cycle"),
        "candidates": [c["id"] for c in cands], "reference": rows[0]["decision"], "agent": rows[1]["decision"]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("CYCLE:", ctx.get("cycle"), "| ctx:", ctx["context_id"])
    print("  candidates:", [c["id"] for c in cands])
    print("  reference:", rows[0]["decision"], "|", rows[0]["reason"])
    print("  agent     :", rows[1]["decision"], "|", rows[1]["reason"])
    print("  wrote", DEC)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
