# -*- coding: utf-8 -*-
"""V3 E-R1: tick-microstructure search on the frozen snapshot.

Reads ONLY the immutable snapshot V3-SNAP-20260922T025312Z.
Protocol frozen before evaluation (FROZEN_PROTOCOL.json). No orders. No V1/V2 input.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_e_r1/run_e_r1.py
"""
from __future__ import annotations
import glob, hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
PROTO = os.path.join(HERE, "FROZEN_PROTOCOL.json")
OUT = os.path.join(HERE, "results_e_r1.json")
GAP_MS = 60_000
SEED = 20261001


def load_ticks():
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    return ts, df["bid"].to_numpy(np.float64), df["ask"].to_numpy(np.float64)


def segments(ts):
    d = np.diff(ts, prepend=ts[0])
    return np.cumsum((d <= 0) | (d > GAP_MS)) - 1


def _bounds(seg):
    s = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0)
    return s, np.append(s, len(seg))


def seg_roll_sum(x, seg, W):
    n = len(x); out = np.zeros(n)
    s, b = _bounds(seg)
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    for k in range(len(s)):
        a, e = s[k], b[k + 1]
        idx = np.arange(a, e)
        out[a:e] = c[idx + 1] - c[np.maximum(idx + 1 - W, a)]
    return out


def seg_roll_cnt(seg, W):
    n = len(seg); out = np.zeros(n)
    s, b = _bounds(seg)
    for k in range(len(s)):
        a, e = s[k], b[k + 1]
        out[a:e] = np.minimum(np.arange(e - a) + 1, W)
    return out


def seg_start(seg):
    s, b = _bounds(seg)
    return np.repeat(s, np.diff(b))


def causal_q(values, seg, q, grid=500, win=3000):
    n = len(values); thr = np.full(n, np.nan); ss = seg_start(seg)
    for p in range(grid, n, grid):
        w = values[ss[p]:p]
        if len(w) >= 50:
            thr[p:min(n, p + grid)] = float(np.quantile(w, q))
    v = np.flatnonzero(~np.isnan(thr))
    if not len(v):
        return np.full(n, np.nan)
    thr[:v[0]] = thr[v[0]]
    return thr[np.maximum.accumulate(np.where(~np.isnan(thr), np.arange(n), 0))]


def onset(c):
    return c & ~np.concatenate([[False], c[:-1]])


def eff_n(ei, ts, hm):
    if not len(ei):
        return 0
    t = ts[ei]; n = 1; last = t[0]
    for x in t[1:]:
        if x - last >= hm:
            n += 1; last = x
    return n


def overlap_ratio(ei, ts, hm):
    if len(ei) < 2:
        return None
    return float(hm / max(1.0, float(np.median(np.diff(ts[ei])))))


def perm_p(x, reps=2000, chunk=250):
    n = len(x)
    if n < 5:
        return None
    base = abs(float(np.mean(x))); rng = np.random.default_rng(SEED)
    ge = 0; done = 0; xf = x.astype(np.float32)
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        ge += int(np.sum(np.abs((xf[None, :] * s).mean(axis=1)) >= base)); done += c
    return float((ge + 1) / (reps + 1))


def boot_ci(x, reps=2000, nblocks=50):
    n = len(x)
    if n < 10:
        return None
    bs = max(1, n // nblocks); nb = int(np.ceil(n / bs))
    pad = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blk = np.nanmean(pad.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(SEED + 1)
    m = blk[rng.integers(0, nb, size=(reps, nb))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def ladder(eff, gross, net1, net2, p, oos1, std):
    if eff < 30:
        return "INSUFFICIENT_SAMPLE"
    if gross < 0.914:
        return "COST_INSUFFICIENT"
    if net1 <= 0:
        return "REJECT"
    if p is None or p >= 0.05 or (oos1 is not None and oos1 <= 0):
        return "EDGE_UNCERTAIN"
    if net2 <= 0:
        return "EDGE_UNCERTAIN"
    if std > 5 * abs(gross):
        return "EXECUTION_UNREALISTIC"
    return "CANDIDATE"


def eval_dir(hid, idx, d, ts, mid, bid, ask, seg, horizons_ms, cost):
    out = {"hypothesis_id": hid, "events_raw": int(len(idx)), "horizons": {}}
    for hm in horizons_ms:
        j = np.searchsorted(ts, ts[idx] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
        cens = int((~v).sum())
        ei, ji, dd = idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
        if len(ei) < 1:
            out["horizons"][str(hm)] = {"n": 0}
            continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g)); pp = perm_p(g)
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        oos1 = (float(np.mean(g[oosm]) - cost) if oosm.sum() >= 2 else None)
        out["horizons"][str(hm)] = {
            "n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, hm)),
            "overlap_ratio": overlap_ratio(ei, ts, hm),
            "mid_mean_bp": gm, "mid_median_bp": float(np.median(g)), "mid_std_bp": sd,
            "net_bp_by_cost": {f"x{x}": float(gm - cost * x) for x in (0.0, 1.0, 2.0, 3.0)},
            "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None,
                   "net1x_bp": float(np.mean(g[ism]) - cost) if ism.sum() >= 2 else None},
            "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                    "net1x_bp": oos1},
            "perm_p": pp, "boot_ci_mid_bp": boot_ci(g),
            "ladder": ladder(eff_n(ei, ts, hm), gm, gm - cost, gm - 2 * cost, pp, oos1, sd),
        }
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert h == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", h[:16])

    ts, bid, ask = load_ticks()
    mid = (bid + ask) / 2.0
    seg = segments(ts)
    print("ticks", len(ts), "segments", int(seg[-1]) + 1)

    dmid = np.diff(mid, prepend=np.nan)
    sgn = np.sign(np.nan_to_num(dmid))
    spread_bp = (ask - bid) / mid * 1e4
    cnt100 = np.maximum(seg_roll_cnt(seg, 100), 1)
    ti100 = seg_roll_sum(sgn, seg, 100) / np.sqrt(cnt100)
    ret100 = seg_roll_sum(dmid, seg, 100)
    ret500 = seg_roll_sum(dmid, seg, 500)
    sd3000 = np.sqrt(np.maximum(seg_roll_sum(dmid ** 2, seg, 3000) / np.maximum(seg_roll_cnt(seg, 3000), 1), 1e-18))
    z500 = ret500 / (sd3000 * np.sqrt(500) + 1e-18)
    z100 = ret100 / (sd3000 * np.sqrt(100) + 1e-18)
    rv500 = np.sqrt(seg_roll_sum(dmid ** 2, seg, 500) / np.maximum(seg_roll_cnt(seg, 500), 1))

    cost = proto["cost_model"]["REAL_RT_COST_BP"]
    H = proto["frozen_thresholds"]["horizons_ms"]

    res = {"schema": "v3_e_r1_results/1", "protocol_hash": h,
           "snapshot": proto["data"]["SNAPSHOT_ID"], "ticks": int(len(ts)),
           "segments": int(seg[-1]) + 1, "cost_bp": cost, "hypotheses": {},
           "reproducibility_note": "E1/E4 are re-runs of Phase-2 R1 A1/A2 under this frozen protocol"}

    # ---- E1 tick imbalance ----
    ev = np.flatnonzero(onset(np.abs(ti100) >= 2.0))
    sd_ = np.where(ti100[ev] >= 0, 1, -1).astype(int)
    res["hypotheses"]["E1_TICKIMB_CONT"] = eval_dir("E1_TICKIMB_CONT", ev, sd_, ts, mid, bid, ask, seg, H, cost)
    res["hypotheses"]["E1_TICKIMB_FADE"] = eval_dir("E1_TICKIMB_FADE", ev, -sd_, ts, mid, bid, ask, seg, H, cost)

    # ---- E2 impact recovery ----
    ev2 = np.flatnonzero(onset(np.abs(z500) >= 2.0))
    d2 = -np.sign(np.nan_to_num(ret500[ev2])).astype(int)   # FADE the shock
    r = eval_dir("E2_IMPACT_RECOVERY_FADE", ev2, d2, ts, mid, bid, ask, seg, H, cost)
    # recovered fraction: how much of the shock is given back
    for hm in H:
        j = np.searchsorted(ts, ts[ev2] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ev2])
        ei, ji = ev2[v], np.minimum(j, len(ts) - 1)[v]
        if len(ei):
            shock = ret500[ei]
            back = (mid[ji] - mid[ei])
            sh = np.where(np.abs(shock) > 0, shock, np.nan)
            r["horizons"][str(hm)]["recovered_fraction_mean"] = float(np.nanmean(-back / sh))
            r["horizons"][str(hm)]["recovered_fraction_median"] = float(np.nanmedian(-back / sh))
    res["hypotheses"]["E2_IMPACT_RECOVERY_FADE"] = r

    # E2 recovery time (descriptive)
    ss = seg_start(seg)
    med_sp = np.full(len(ts), np.nan)
    for p in range(3000, len(ts), 500):
        w = spread_bp[int(ss[p]):p]
        if len(w) >= 50:
            med_sp[p:min(len(ts), p + 500)] = float(np.median(w))
    vv = np.flatnonzero(~np.isnan(med_sp))
    med_sp = med_sp[np.maximum.accumulate(np.where(~np.isnan(med_sp), np.arange(len(ts)), 0))] if len(vv) else med_sp
    rec_times = []
    for i in ev2[:4000]:
        base = med_sp[i]
        if not np.isfinite(base) or base <= 0:
            continue
        lim = base * 1.10
        j = i
        end = min(len(ts), i + 60000)
        cur_seg = seg[i]
        for j in range(i, end):
            if seg[j] != cur_seg:
                break
            if spread_bp[j] <= lim:
                rec_times.append(ts[j] - ts[i]); break
    res["hypotheses"]["E2_RECOVERY_TIME"] = {
        "n_shocks": int(len(ev2)), "n_measured": len(rec_times),
        "recovery_ms_median": float(np.median(rec_times)) if rec_times else None,
        "recovery_ms_p90": float(np.percentile(rec_times, 90)) if rec_times else None,
        "note": "time for spread_bp to fall back within 10% of the trailing 3000-tick median"}

    # ---- E3 joint state drift ----
    q_s = causal_q(spread_bp, seg, 0.33), causal_q(spread_bp, seg, 0.67)
    q_r = causal_q(rv500, seg, 0.33), causal_q(rv500, seg, 0.67)
    grid = np.arange(500, len(ts) - 1, 500)
    sp_terc = np.where(spread_bp[grid] <= np.nan_to_num(q_s[0][grid], nan=np.inf), "TIGHT",
              np.where(spread_bp[grid] >= np.nan_to_num(q_s[1][grid], nan=np.inf), "WIDE", "MID"))
    rv_terc = np.where(rv500[grid] <= np.nan_to_num(q_r[0][grid], nan=np.inf), "LOW",
              np.where(rv500[grid] >= np.nan_to_num(q_r[1][grid], nan=np.inf), "HIGH", "MID"))
    press = np.sign(ti100[grid])
    cells = {}
    for a in ("TIGHT", "MID", "WIDE"):
        for b in ("LOW", "MID", "HIGH"):
            m = (sp_terc == a) & (rv_terc == b) & (press != 0)
            if m.sum() >= 50:
                cells[f"{a}|{b}"] = (grid[m], press[m].astype(int))
    e3 = {"hypothesis_id": "E3_JOINT_STATE_DRIFT", "cells": {}, "fdr": {},
          "grid_stride_ticks": 500, "n_cells": len(cells)}
    for name, (gi, gd) in cells.items():
        e3["cells"][name] = eval_dir(f"E3::{name}", gi, gd, ts, mid, bid, ask, seg, H, cost)
    # BH-FDR across all cell x horizon p-values
    tests = []
    for name, blk in e3["cells"].items():
        for hm, z in blk["horizons"].items():
            if z.get("perm_p") is not None:
                tests.append((name, hm, z["perm_p"], z["mid_mean_bp"], z["ladder"]))
    tests.sort(key=lambda t: t[2])
    m = len(tests)
    fdr = []
    for rank, (name, hm, p, gm, ld) in enumerate(tests, start=1):
        fdr.append({"cell": name, "horizon_ms": int(hm), "perm_p": p, "mid_mean_bp": gm,
                    "ladder": ld, "bh_cutoff": 0.05 * rank / m, "survives_fdr": p <= 0.05 * rank / m})
    e3["fdr"] = {"n_tests": m, "surviving": sum(1 for f in fdr if f["survives_fdr"]), "table": fdr[:20]}
    res["hypotheses"]["E3_JOINT_STATE_DRIFT"] = e3

    # ---- E4 micro continuation / reversal ----
    ev4 = np.flatnonzero(onset(np.abs(z100) >= 2.0))
    d4 = np.sign(np.nan_to_num(ret100[ev4])).astype(int)
    res["hypotheses"]["E4_MICRO_CONT"] = eval_dir("E4_MICRO_CONT", ev4, d4, ts, mid, bid, ask, seg, H, cost)
    res["hypotheses"]["E4_MICRO_FADE"] = eval_dir("E4_MICRO_FADE", ev4, -d4, ts, mid, bid, ask, seg, H, cost)

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    for k, v in res["hypotheses"].items():
        if k.startswith("E3"):
            print(f"{k}: cells={v['n_cells']} fdr_tests={v['fdr']['n_tests']} surviving={v['fdr']['surviving']}")
            best = sorted(v["fdr"]["table"], key=lambda x: -abs(x["mid_mean_bp"]))[:3]
            for b in best:
                print("   ", b)
        elif "horizons" in v:
            line = " ".join(f"{hm}:{z.get('ladder','-')}/{round(z.get('mid_mean_bp',0),3)}"
                            for hm, z in v["horizons"].items() if z.get("n"))
            print(f"{k}: raw={v['events_raw']}  {line}")
        else:
            print(k, json.dumps(v, ensure_ascii=False)[:160])


if __name__ == "__main__":
    main()
