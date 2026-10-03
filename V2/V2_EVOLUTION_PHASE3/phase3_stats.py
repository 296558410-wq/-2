# -*- coding: utf-8 -*-
"""phase3_stats.py — 汇总 Phase-3 各任务的最终数字（只读）。"""
import collections, json, statistics as st
from pathlib import Path
SH = Path(r"C:\AIQuant\research\hermes\trader_v2\shadow_evolution")
OUT = Path(r"C:\AIQuant\research\hermes\trader_v2\V2_EVOLUTION_PHASE3")


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


res = {}
# A
ds = json.loads((SH / "_discovery_shadow_stats.json").read_text(encoding="utf-8"))
res["A_discovery"] = {k: ds[k] for k in ("cycles", "ref_pick_distribution", "shadow_pick_distribution",
                                         "geo_shock_share_of_picks", "picks_changed",
                                         "ref_candidates_per_cycle", "shadow_candidates_per_cycle",
                                         "ref_candidate_sources")}
# C
oe = [json.loads(l) for l in open(SH / "OUTCOME_ENGINE.jsonl", encoding="utf-8") if l.strip()]
g = collections.defaultdict(list)
for o in oe:
    g[(o["shadow_side"], o["decision"])].append(o)
tab = {}
for k, v in sorted(g.items()):
    fr = lambda h: med([(x.get("future_return") or {}).get("+%dm_bps" % h) for x in v])
    tab["/".join(k)] = {"n": len(v), "+15m": fr(15), "+30m": fr(30), "+60m": fr(60), "+240m": fr(240),
                        "mfe_med": med([x.get("mfe_bps") for x in v]), "mae_med": med([x.get("mae_bps") for x in v]),
                        "tp_sl": dict(collections.Counter(((x.get("tp_sl_path") or {}).get("first_touch")) for x in v))}
res["C_outcome"] = {"rows": len(oe), "table": tab, "stats": json.loads((SH / "_outcome_engine_stats.json").read_text(encoding="utf-8"))}
# D + verify
res["D_version"] = json.loads((OUT / "_phase3_verify.json").read_text(encoding="utf-8"))
print(json.dumps(res, ensure_ascii=False, indent=1))
(OUT / "_phase3_stats.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
