# -*- coding: utf-8 -*-
"""Derive the G3 (time-block stability) table with BOTH gross and NET sign flags — read-only."""
import json, os
import numpy as np
D = r"C:\AIQuant\research\hermes\trader_v3\research\v3_r4_temporal_f5"
r = json.load(open(os.path.join(D, "results_v3_r4_splits.json"), encoding="utf-8"))
print("id | best_h(gross) | blocks net1x (B1,B2,B3) | gross_signs | net_signs | net_stable")
for hid, blk in r["W4"].items():
    if "horizons" not in blk:
        continue
    zs = {h: z for h, z in blk["horizons"].items() if z.get("gross_bp") is not None}
    if not zs:
        continue
    best = max(zs.items(), key=lambda kv: kv[1]["gross_bp"])
    sp = (best[1].get("splits") or {}).get("temporal_blocks")
    if not sp:
        continue
    nb = [round(sp[f"B{i}"]["net1x_bp"], 3) for i in (1, 2, 3)]
    mb = [sp[f"B{i}"]["mean_bp"] for i in (1, 2, 3)]
    gs = len({np.sign(round(x, 9)) for x in mb})
    ns = len({np.sign(round(x, 9)) for x in nb})
    print(f"{hid[:26]:26s} | {int(best[0])//60000:>4}m | {nb} | {gs}sign | {ns}sign | {'STABLE' if ns==1 else 'UNSTABLE'}")
# also a compact summary of session/vol/spread availability
have = sum(1 for blk in r["W4"].values() if isinstance(blk, dict) and "horizons" in blk
           for z in blk["horizons"].values() if isinstance(z, dict) and isinstance(z.get("splits"), dict) and z["splits"].get("session"))
print("hypothesis-horizons with session splits:", have)
