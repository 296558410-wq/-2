# -*- coding: utf-8 -*-
"""shadow_three_way.py — 三侧 Shadow：reference_rules / hermes_heuristic / true_llm_agent。
与之前**完全相同的 120 周期 PIT 快照**；三侧共享 context_id/context_hash/data snapshot/as-of 时间戳。
隔离、只读 V2、order_send=0、不改历史 ledger、不改生产参数。

输出: TRUE_AGENT_DECISIONS.jsonl (3 行/周期)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes")); sys.path.insert(0, str(V2)); sys.path.insert(0, str(HERE))
import context as CTX, discovery as DISC, hermes as H  # noqa: E402
import agent_orchestrator as AO  # noqa: E402
from shadow_backfill import pairs, decide_row  # noqa: E402
CTX.CTX_DIR = HERE / "decision_contexts"

OUT = HERE / "TRUE_AGENT_DECISIONS.jsonl"


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 120
    ps = pairs(limit)
    rows = []
    for cyc, a1p, a2p in ps:
        ctx, a1, a2, _ = AO.context_asof(cyc, a1p, a2p)
        cands = DISC.discover(ctx, a1, a2)
        tags = DISC.regime_tags(ctx, a1, a2)
        pack = AO.prompt_pack(ctx, cands, tags)
        ts = ctx.get("created_utc")
        # 1) reference
        ref, _, _ = H.decide_pure(ctx, a1, a2, source="reference_rules"); ref["ts"] = ts
        # 2) hermes_heuristic (对照, 保留)
        heur = AO.heuristic_decide(ctx, a1, a2, cands, tags); heur["ts"] = ts
        # 3) true_llm_agent
        llm = AO.orchestrate_llm(ctx, a1, a2, cands, tags); llm.setdefault("ts", ts)
        for side, d in (("reference_rules", ref), ("hermes_heuristic", heur), ("true_llm_agent", llm)):
            r = decide_row(side, cyc, ctx, a1, a2, cands, tags, d, pack["input_hash"])
            r["prompt_hash"] = pack["prompt_hash"]
            r["evidence"] = (d.get("reasoning") or d.get("evidence") or d.get("reason"))
            rows.append(r)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("cycles:", len(ps), "rows:", len(rows), "->", OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
