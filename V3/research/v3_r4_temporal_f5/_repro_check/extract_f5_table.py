# -*- coding: utf-8 -*-
"""Extract the full F5_R4 per-hypothesis/horizon table from results_v3_r4.json (read-only helper)."""
import json, os
D = r"C:\AIQuant\research\hermes\trader_v3\research\v3_r4_temporal_f5"
r = json.load(open(os.path.join(D, "results_v3_r4.json"), encoding="utf-8"))
print("hyp | horizon | n | eff_n | gross | net1x | net2x | IS_net1x | OOS_net1x | perm_p | boot_ci")
for hid, v in r["W4"].items():
    if "horizons" not in v:
        print(hid, "->", v)
        continue
    for h, z in v["horizons"].items():
        if not isinstance(z, dict) or z.get("gross_bp") is None:
            continue
        hm = int(h) // 60000
        isv = (z.get("is") or {}).get("net1x_bp")
        oosv = (z.get("oos") or {}).get("net1x_bp")
        print("%-24s | %4dm | %3s | %3s | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %s | %s" % (
            hid[:24], hm, z.get("n"), z.get("effective_n"), z["gross_bp"], z["net_bp"]["x1.0"],
            z["net_bp"]["x2.0"],
            isv if isv is not None else float("nan"), oosv if oosv is not None else float("nan"),
            round(z.get("perm_p"), 4) if z.get("perm_p") is not None else None, z.get("boot_ci_bp")))
