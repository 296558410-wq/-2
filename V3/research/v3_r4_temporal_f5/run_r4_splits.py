# -*- coding: utf-8 -*-
"""R4 supplementary: materialize the protocol's must_report splits (session / vol / spread / temporal
blocks) on the SAME frozen samples — additive only.

- Reuses run_r4.py machinery (frozen protocol asserted inside main()).
- Redirects main()'s writes to a TEMP dir (frozen results_v3_r4.json / DATA_REGISTRY / EVENT_REGISTRY
  are NOT touched).
- Asserts every core number is identical to the frozen results; then saves the split-enriched results
  as results_v3_r4_splits.json (reporting artifact for G3 + required splits).
"""
from __future__ import annotations
import json, os, shutil, sys, tempfile
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import run_r4 as R  # noqa: E402

ORIG_EVAL = R.eval_dir
FROZEN = json.load(open(os.path.join(D, "results_v3_r4.json"), encoding="utf-8"))


def patched_eval_dir(hid, ent, dirs, ts, mid, bid, ask, seg, Hms, meta=None):
    spread = (ask - bid) / mid * 1e4
    medsp = R.causal_med(spread, seg, 3000)
    r1 = np.abs(np.diff(mid, prepend=np.nan) / mid)
    vol = R.seg_roll(np.nan_to_num(r1), seg, 300, "sum") / np.maximum(R.seg_roll(np.zeros(len(r1)), seg, 300, "cnt"), 1)
    hour = ((ts // 3600000) % 24)

    def splitter(ei, g):
        out = {}
        if len(ei) < 10:
            return {"note": "n<10, splits not reported"}
        sess = np.where(hour[ei] < 7, "ASIA",
                        np.where(hour[ei] < 13, "LONDON", np.where(hour[ei] < 21, "NY", "LATE")))
        for name in ("ASIA", "LONDON", "NY", "LATE"):
            mk = sess == name
            if mk.sum() >= 5:
                out.setdefault("session", {})[name] = {"n": int(mk.sum()), "mean_bp": float(np.mean(g[mk])),
                                                        "net1x_bp": float(np.mean(g[mk]) - R.COST)}
        for label, key in (("vol", vol), ("spread", spread)):
            v = key[ei]
            fin = np.isfinite(v)
            if fin.sum() >= 10:
                med = float(np.median(v[fin]))
                lo, hi = fin & (v <= med), fin & (v > med)
                if lo.sum() >= 5:
                    out.setdefault(label, {})["LOW"] = {"n": int(lo.sum()), "mean_bp": float(np.mean(g[lo])),
                                                         "net1x_bp": float(np.mean(g[lo]) - R.COST), "median": med}
                if hi.sum() >= 5:
                    out.setdefault(label, {})["HIGH"] = {"n": int(hi.sum()), "mean_bp": float(np.mean(g[hi])),
                                                          "net1x_bp": float(np.mean(g[hi]) - R.COST), "median": med}
        order = np.argsort(ts[ei])
        blocks = np.array_split(order, 3)
        for bi, blk in enumerate(blocks, start=1):
            if len(blk) >= 5:
                out.setdefault("temporal_blocks", {})[f"B{bi}"] = {
                    "n": int(len(blk)), "mean_bp": float(np.mean(g[blk])),
                    "net1x_bp": float(np.mean(g[blk]) - R.COST),
                    "t0_utc": str(np.datetime64(int(ts[ei][blk].min()), "ms")),
                    "t1_utc": str(np.datetime64(int(ts[ei][blk].max()), "ms"))}
        if "temporal_blocks" in out and len(out["temporal_blocks"]) == 3:
            signs = {np.sign(round(v["mean_bp"], 9)) for v in out["temporal_blocks"].values()}
            out["temporal_block_stability"] = "STABLE" if len(signs) == 1 else "UNSTABLE"
        return out

    return ORIG_EVAL(hid, ent, dirs, ts, mid, bid, ask, seg, Hms, meta=splitter)


R.eval_dir = patched_eval_dir
TMP = tempfile.mkdtemp(prefix="r4_splits_")
R.HERE = TMP
R.main()

new = json.load(open(os.path.join(TMP, "results_v3_r4.json"), encoding="utf-8"))
# assert core numbers identical to the frozen run (splits are purely additive)
bad = []
for hid, blk in FROZEN["W4"].items():
    if "horizons" not in blk:
        continue
    for hm, z in blk["horizons"].items():
        nz = new["W4"][hid]["horizons"][hm]
        for k in ("n", "effective_n", "gross_bp", "perm_p"):
            if z.get(k) != nz.get(k):
                bad.append((hid, hm, k, z.get(k), nz.get(k)))
        if z.get("net_bp") != nz.get("net_bp"):
            bad.append((hid, hm, "net_bp"))
print("core-number check:", "IDENTICAL" if not bad else f"MISMATCH {bad[:5]}")
shutil.copy2(os.path.join(TMP, "results_v3_r4.json"), os.path.join(D, "results_v3_r4_splits.json"))
shutil.rmtree(TMP, ignore_errors=True)
print("saved: results_v3_r4_splits.json")
# quick G3 summary print
for hid, blk in new["W4"].items():
    for hm, z in blk.get("horizons", {}).items():
        sp = z.get("splits") or {}
        if "temporal_block_stability" in sp:
            print(hid, int(hm)//60000, "m:", sp["temporal_block_stability"],
                  {k: round(v["net1x_bp"], 2) for k, v in sp["temporal_blocks"].items()})
