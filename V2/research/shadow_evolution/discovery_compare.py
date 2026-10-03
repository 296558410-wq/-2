# -*- coding: utf-8 -*-
"""discovery_compare.py — 120 周期：reference discovery vs shadow discovery 逐周期对照（只读）。
输出 _discovery_shadow_stats.json
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "hermes")); sys.path.insert(0, str(V2)); sys.path.insert(0, str(HERE))
import context as CTX, discovery as DISC  # noqa: E402
import agent_orchestrator as AO, discovery_shadow as DS  # noqa: E402
from shadow_backfill import pairs  # noqa: E402
CTX.CTX_DIR = HERE / "decision_contexts"


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 120
    ps = pairs(limit)
    ref_src = collections.Counter(); sh_src = collections.Counter()
    ref_pick_src = collections.Counter(); sh_pick_src = collections.Counter()
    ref_n = collections.Counter(); sh_n = collections.Counter()
    per_cycle = []
    for cyc, a1p, a2p in ps:
        ctx, a1, a2, _ = AO.context_asof(cyc, a1p, a2p)
        ref, ranked, ref_pick, sh_pick = DS.compare(ctx, a1, a2)
        for c in ref: ref_src[c["id"]] += 1
        for c in ranked: sh_src[c["id"]] += 1
        ref_n[len(ref)] += 1; sh_n[len(ranked)] += 1
        ref_pick_src[(ref_pick or {}).get("id", "NONE")] += 1
        sh_pick_src[(sh_pick or {}).get("id", "NONE")] += 1
        per_cycle.append({"cycle": cyc, "ref_cands": [c["id"] for c in ref],
                          "ref_pick": (ref_pick or {}).get("id"), "ref_pick_source": (ref_pick or {}).get("source"),
                          "shadow_pick": (sh_pick or {}).get("id"), "shadow_pick_source": (sh_pick or {}).get("source"),
                          "shadow_pick_presence_only": (sh_pick or {}).get("presence_only")})
    n = len(ps)
    stats = {"cycles": n,
             "ref_candidate_sources": dict(ref_src), "shadow_candidate_sources": dict(sh_src),
             "ref_pick_distribution": dict(ref_pick_src), "shadow_pick_distribution": dict(sh_pick_src),
             "ref_candidates_per_cycle": dict(ref_n), "shadow_candidates_per_cycle": dict(sh_n),
             "geo_shock_share_of_picks": {
                 "reference": round(ref_pick_src.get("opp_geo_shock", 0) / max(1, n), 3),
                 "shadow": round(sh_pick_src.get("opp_geo_shock", 0) / max(1, n), 3)},
             "picks_changed": sum(1 for r in per_cycle if r["ref_pick"] != r["shadow_pick"]),
             "per_cycle": per_cycle}
    json.dump(stats, open(HERE / "_discovery_shadow_stats.json", "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in stats.items() if k != "per_cycle"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
