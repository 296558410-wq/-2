# -*- coding: utf-8 -*-
"""horizon_summary.py — per side/decision medians across horizons (read-only)."""
import json, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
O = [json.loads(l) for l in open(HERE / "TRUE_AGENT_OUTCOMES.jsonl", encoding="utf-8") if l.strip()]
g = collections.defaultdict(list)
for o in O:
    g[(o["shadow_side"], o["decision"])].append(o)


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


print("side/decision | n | +15m | +30m | +60m | +240m | MFE_med | MAE_med")
for k, v in sorted(g.items()):
    def fr(h):
        return med([(x.get("future_return") or {}).get("+%dm_bps" % h) for x in v])
    print("%s/%s | %d | %s | %s | %s | %s | %s | %s" % (
        k[0], k[1], len(v), fr(15), fr(30), fr(60), fr(240),
        med([x.get("mfe_bps") for x in v]), med([x.get("mae_bps") for x in v])))
