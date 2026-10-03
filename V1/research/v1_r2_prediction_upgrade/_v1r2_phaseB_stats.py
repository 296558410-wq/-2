# -*- coding: utf-8 -*-
"""Phase B stats summary (read-only over the produced run artifacts)."""
from __future__ import annotations

import collections
import json
import os

UP = r"C:\AIQuant\research\hermes\trader_v1\v1_r2_prediction_upgrade"
RD = os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_20260926T120857")
st = [json.loads(l) for l in open(os.path.join(RD, "v1_r2_states.jsonl"), encoding="utf-8") if l.strip()]
rp = [json.loads(l) for l in open(os.path.join(RD, "parallel_replay.jsonl"), encoding="utf-8") if l.strip()]


def dist(recs, key):
    def g(s):
        v = s.get(key)
        return (v or {}).get("state") if isinstance(v, dict) else str(v)
    return dict(collections.Counter(g(s) for s in recs).most_common())


out = {
    "bars": len(st), "replay_records": len(rp),
    "regime": dist(st, "regime"), "momentum": dist(st, "momentum"),
    "next_state": dist(st, "next_state"), "absorption": dist(st, "absorption"),
    "break_risk": dist(st, "break_risk"), "transition": dist(st, "transition"),
    "touch_states": dict(collections.Counter(((s.get("level") or {}).get("state") or "NA") for s in st).most_common()),
    "level_coverage": sum(1 for s in st if s.get("level")),
    "v1_decisions": dict(collections.Counter(r["v1_decision"] for r in rp)),
    "v2_directions": dict(collections.Counter((r["v2_next_state"] or {}).get("direction") for r in rp)),
    "v2_states_in_replay": dict(collections.Counter((r["v2_next_state"] or {}).get("state") for r in rp)),
    "v1_directional": sum(1 for r in rp if r["v1_decision"] in ("LONG", "SHORT")),
    "v2_directional": sum(1 for r in rp if (r["v2_next_state"] or {}).get("direction") in ("LONG", "SHORT")),
    "dir_agree": sum(1 for r in rp if r["v1_decision"] in ("LONG", "SHORT")
                       and r["v1_decision"] == (r["v2_next_state"] or {}).get("direction")),
    "v2_reversion_or_hold": sum(1 for r in rp if (r["v2_next_state"] or {}).get("state") in ("REVERSION", "HOLD")),
}
print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
with open(os.path.join(UP, "reports", "V1_R2_PHASE_B_STATS.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
