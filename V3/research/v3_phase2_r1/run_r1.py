# -*- coding: utf-8 -*-
"""V3 Phase-2 R1 discovery harness (final).

Reads ONLY the immutable snapshot V3-SNAP-20260922T025312Z.
Frozen protocol: research/v3_phase2_r1/FROZEN_PROTOCOL.json (never mutated).
No orders. No live feed. V1/V2 untouched.

Markouts (data contract v2 §6/§7):
  MID_MARKOUT        = dir * (future_mid - entry_mid)          [predictive edge]
  EXECUTION_MARKOUT  = dir>0 ? future_mid-entry_ask : entry_bid-future_mid
  COST_ADJUSTED      = MID_MARKOUT - REAL_RT_COST_BP * stress_mult
Ladder is applied to COST_ADJUSTED_MID_MARKOUT.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_phase2_r1/run_r1.py
"""
from __future__ import annotations
import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
PROTO_PATH = os.path.join(HERE, "FROZEN_PROTOCOL.json")
OUT_JSON = os.path.join(HERE, "results_r1.json")

GAP_MS = 60_000
GRID = 500
WIN = 3000
SEED = 20261001


# ------------------------------------------------------------ primitives
def load_ticks():
    man = json.load(open(os.path.join(SNAP, "MANIFEST.json"), encoding="utf-8"))
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    df["ts_ms"] = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    return df, man


def segment_ids(ts_ms):
    d = np.diff(ts_ms, prepend=ts_ms[0])
    return np.cumsum((d <= 0) | (d > GAP_MS)) - 1


def _seg_bounds(seg):
    starts = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0)
    return starts, np.append(starts, len(seg))


def seg_rolling_sum(x, seg, W):
    n = len(x)
    out = np.zeros(n)
    starts, bounds = _seg_bounds(seg)
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    for k in range(len(starts)):
        a, b = starts[k], bounds[k + 1]
        idx = np.arange(a, b)
        lo = np.maximum(idx + 1 - W, a)
        out[a:b] = c[idx + 1] - c[lo]
    return out


def seg_rolling_cnt(seg, W):
    n = len(seg)
    out = np.zeros(n)
    starts, bounds = _seg_bounds(seg)
    for k in range(len(starts)):
        a, b = starts[k], bounds[k + 1]
        out[a:b] = np.minimum(np.arange(b - a) + 1, W)
    return out


def seg_start_index(seg):
    starts, bounds = _seg_bounds(seg)
    return np.repeat(starts, np.diff(bounds))


def causal_quantile_grid(values, seg, q, grid=GRID):
    n = len(values)
    thr = np.full(n, np.nan)
    ss = seg_start_index(seg)
    for p in range(grid, n, grid):
        w = values[ss[p]:p]
        if len(w) >= 50:
            thr[p:min(n, p + grid)] = float(np.quantile(w, q))
    valid = np.flatnonzero(~np.isnan(thr))
    if len(valid) == 0:
        return np.full(n, np.nan)
    thr[:valid[0]] = thr[valid[0]]
    idx = np.arange(n)
    return thr[np.maximum.accumulate(np.where(~np.isnan(thr), idx, 0))]


def onset(cond):
    return cond & ~np.concatenate([[False], cond[:-1]])


def effective_n(ei, ts, horizon):
    if len(ei) == 0:
        return 0
    t = ts[ei]
    cnt, last = 1, t[0]
    for x in t[1:]:
        if x - last >= horizon:
            cnt += 1
            last = x
    return cnt


def signflip_perm_p(x, reps=2000, seed=SEED, chunk=250):
    """two-sided p for mean(x)!=0 under random sign flips."""
    n = len(x)
    if n < 5:
        return None
    base = abs(float(np.mean(x)))
    rng = np.random.default_rng(seed)
    ge = 0
    done = 0
    xf = x.astype(np.float32)
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        m = np.abs((xf[None, :] * s).mean(axis=1)).astype(np.float64)
        ge += int(np.sum(m >= base))
        done += c
    return float((ge + 1) / (reps + 1))


def block_bootstrap_ci(x, reps=2000, seed=SEED, nblocks=50):
    n = len(x)
    if n < 10:
        return None
    bs = max(1, n // nblocks)
    nb = int(np.ceil(n / bs))
    padded = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blocks = np.nanmean(padded.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(seed + 1)
    picks = rng.integers(0, nb, size=(reps, nb))
    means = blocks[picks].mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def ladder(eff, gross_mean_bp, net1x, net2x, p_perm, oos_net1x, gross_std):
    if eff < 30:
        return "INSUFFICIENT_SAMPLE"
    if gross_mean_bp < 0.914:
        return "COST_INSUFFICIENT"
    if net1x <= 0:
        return "REJECT"
    if p_perm is None or p_perm >= 0.05 or (oos_net1x is not None and oos_net1x <= 0):
        return "EDGE_UNCERTAIN"
    if net2x <= 0:
        return "EDGE_UNCERTAIN"
    if gross_std > 5 * abs(gross_mean_bp):
        return "EXECUTION_UNREALISTIC"
    return "CANDIDATE"


def evaluate(name, family, ev_idx, dirs, mid, bid, ask, ts, seg, horizons, cost_bp):
    out = {"hypothesis_id": name, "family": family, "events_raw": int(len(ev_idx)), "horizons": {}}
    if len(ev_idx) == 0:
        out["status"] = "NOT_TESTABLE"
        out["reason"] = "zero events under frozen trigger"
        return out
    e = ev_idx + 1
    ok = e < len(ts)
    e = e[ok]
    di = dirs[ok]
    out["events_after_entry_shift"] = int(len(e))
    for h in horizons:
        j = np.searchsorted(ts, ts[e] + h, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[e])
        censored = int((~v).sum())
        ei, ji, d = e[v], np.minimum(j, len(ts) - 1)[v], di[v]
        if len(ei) < 1:
            out["horizons"][str(h)] = {"n": 0}
            continue
        m_d = d * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        m_x = np.where(d > 0, mid[ji] - ask[ei], bid[ei] - mid[ji]) / mid[ei] * 1e4
        eff = effective_n(ei, ts, h)
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        is_m, oos_m = ts[ei] <= cut, ts[ei] > cut
        g_mean = float(np.mean(m_d))
        perm = signflip_perm_p(m_d)
        boot = block_bootstrap_ci(m_d)
        nets = {f"x{mu}": float(g_mean - cost_bp * mu) for mu in (0.0, 1.0, 2.0, 3.0)}
        seg_stats = {}
        for tag, mask in (("is", is_m), ("oos", oos_m)):
            g = m_d[mask]
            seg_stats[tag] = ({"n": int(len(g)), "mid_mean_bp": float(np.mean(g)),
                               "net1x_bp": float(np.mean(g) - cost_bp),
                               "median_bp": float(np.median(g))} if len(g) >= 2 else {"n": int(len(g))})
        verdict = ladder(eff, g_mean, nets["x1.0"], nets["x2.0"], perm,
                         seg_stats["oos"].get("net1x_bp"), float(np.std(m_d)))
        out["horizons"][str(h)] = {
            "n": int(len(ei)), "censored_n": censored, "effective_n": int(eff),
            "mid_mean_bp": g_mean, "mid_median_bp": float(np.median(m_d)), "mid_std_bp": float(np.std(m_d)),
            "mid_p10": float(np.percentile(m_d, 10)), "mid_p90": float(np.percentile(m_d, 90)),
            "exec_mean_bp": float(np.mean(m_x)), "exec_median_bp": float(np.median(m_x)),
            "net_mean_bp_by_cost": nets, "is": seg_stats["is"], "oos": seg_stats["oos"],
            "perm_p": perm, "boot_ci_mid_bp": boot, "ladder": verdict,
        }
    return out


# ------------------------------------------------------------ main
def main():
    proto = json.load(open(PROTO_PATH, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert h == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", h[:16])

    df, man = load_ticks()
    ts = df["ts_ms"].to_numpy(np.int64)
    bid = df["bid"].to_numpy(np.float64)
    ask = df["ask"].to_numpy(np.float64)
    mid = (bid + ask) / 2.0
    seg = segment_ids(ts)
    print("ticks", len(ts), "segments", int(seg[-1]) + 1)

    dmid = np.diff(mid, prepend=np.nan)
    sgn = np.sign(np.nan_to_num(dmid))
    spread_bp = (ask - bid) / mid * 1e4
    ti100 = seg_rolling_sum(sgn, seg, 100) / np.sqrt(np.maximum(seg_rolling_cnt(seg, 100), 1))
    ret100 = seg_rolling_sum(dmid, seg, 100)
    ret500 = seg_rolling_sum(dmid, seg, 500)
    sd3000 = np.sqrt(np.maximum(seg_rolling_sum(dmid ** 2, seg, 3000) / np.maximum(seg_rolling_cnt(seg, 3000), 1), 1e-18))
    z500 = ret500 / (sd3000 * np.sqrt(500) + 1e-18)
    mp_pos = np.where((ask - bid) > 0, (mid - bid) / (ask - bid), 0.5)
    rv500 = np.sqrt(seg_rolling_sum(dmid ** 2, seg, 500) / np.maximum(seg_rolling_cnt(seg, 500), 1))
    thr_spread67 = causal_quantile_grid(spread_bp, seg, 0.67)
    thr_rv67 = causal_quantile_grid(rv500, seg, 0.67)
    idx = np.arange(len(ts))
    j0 = np.searchsorted(ts, ts - 5000, side="left")
    rate = (idx - j0 + 1) / 5.0
    thr_rate90 = causal_quantile_grid(rate, seg, 0.90)

    cost_bp = proto["cost_model"]["REAL_RT_COST_BP"]
    H = proto["frozen_thresholds"]["horizons_ms"]

    res = {"schema": "v3_phase2_r1_results/1", "protocol_hash": h, "snapshot": man["SNAPSHOT_ID"],
           "rows": int(len(ts)), "segments": int(seg[-1]) + 1, "cost_bp": cost_bp,
           "markout_definitions": {
               "MID_MARKOUT": "dir*(future_mid-entry_mid)",
               "EXECUTION_MARKOUT": "dir>0? future_mid-entry_ask : entry_bid-future_mid",
               "COST_ADJUSTED_MID": "MID_MARKOUT - 0.914bp*stress"},
           "feature_notes": {"volume_field": "DATA_GAP (identically 0)", "flow_features": "quote-based _PROXY only"},
           "hypotheses": {}, "event_counts": {}}

    evA1 = np.flatnonzero(onset(np.abs(ti100) >= 2.0))
    res["hypotheses"]["A1_TICKIMB_CONT"] = evaluate("A1_TICKIMB_CONT", "A_microstructure", evA1, +np.ones(len(evA1), int), mid, bid, ask, ts, seg, H, cost_bp)
    res["hypotheses"]["A1_TICKIMB_REV"] = evaluate("A1_TICKIMB_REV", "A_microstructure", evA1, -np.ones(len(evA1), int), mid, bid, ask, ts, seg, H, cost_bp)

    evA2 = np.flatnonzero(onset(np.abs(z500) >= 2.0))
    dA2 = np.sign(np.nan_to_num(ret500[evA2]))
    res["hypotheses"]["A2_PXSHOCK_CONT"] = evaluate("A2_PXSHOCK_CONT", "A_microstructure", evA2, dA2.astype(int), mid, bid, ask, ts, seg, H, cost_bp)
    res["hypotheses"]["A2_PXSHOCK_REV"] = evaluate("A2_PXSHOCK_REV", "A_microstructure", evA2, (-dA2).astype(int), mid, bid, ask, ts, seg, H, cost_bp)

    wide = spread_bp >= np.nan_to_num(thr_spread67, nan=np.inf)
    evC1 = np.flatnonzero(onset(wide) & (np.abs(ret100) > 0))
    dC1 = -np.sign(np.nan_to_num(ret100[evC1]))
    res["hypotheses"]["C1_WIDESPREAD_MR"] = evaluate("C1_WIDESPREAD_MR", "C_liquidity_spread_regime", evC1, dC1.astype(int), mid, bid, ask, ts, seg, H, cost_bp)

    burst = rate >= np.nan_to_num(thr_rate90, nan=np.inf)
    evC2 = np.flatnonzero(onset(burst) & (np.abs(ret100) > 0))
    dC2 = np.sign(np.nan_to_num(ret100[evC2]))
    res["hypotheses"]["C2_ARRIVAL_BURST_CONT"] = evaluate("C2_ARRIVAL_BURST_CONT", "C_liquidity_spread_regime", evC2, dC2.astype(int), mid, bid, ask, ts, seg, H, cost_bp)

    ext = (mp_pos >= 0.70) | (mp_pos <= 0.30)
    evB1 = np.flatnonzero(onset(ext))
    if len(evB1) == 0:
        res["hypotheses"]["B1_MICROPRICE_EDGE"] = {
            "hypothesis_id": "B1_MICROPRICE_EDGE", "family": "B_execution_alpha",
            "events_raw": 0, "status": "NOT_TESTABLE",
            "reason": "microprice position (mid-bid)/(ask-bid) is identically 0.5 by construction (mid == midpoint of bid/ask); size-weighted microprice requires bid_vol/ask_vol which are DATA_GAP (identically 0). Family B (execution alpha via size-weighted microprice) is NOT TESTABLE with this snapshot."}
    else:
        res["hypotheses"]["B1_MICROPRICE_EDGE"] = evaluate("B1_MICROPRICE_EDGE", "B_execution_alpha", evB1, np.where(mp_pos[evB1] >= 0.7, 1, -1), mid, bid, ask, ts, seg, H, cost_bp)

    evF1 = np.flatnonzero(onset(rv500 >= np.nan_to_num(thr_rv67, nan=np.inf)))
    res["hypotheses"]["F1_VOL_PERSIST"] = evaluate("F1_VOL_PERSIST", "F_nondirectional", evF1, np.zeros(len(evF1), int), mid, bid, ask, ts, seg, H, cost_bp)

    res["event_counts"] = {"A1": len(evA1), "A2": len(evA2), "C1": len(evC1), "C2": len(evC2), "B1": 0, "F1": len(evF1)}
    res["families_not_tested"] = {
        "D_event_microstructure": "NOT_TESTABLE — no PIT event calendar overlapping 2026-08-04..2026-09-22",
        "E_crossmarket_leadlag": "LIMITED — Yahoo 5m DXY/VIX/^TNX overlap ~2026-08-25..09-18 only; DXY shock already tested in prior round",
        "B_execution_alpha": "NOT_TESTABLE — size fields identically 0 (DATA_GAP); mid-based microprice degenerate",
    }
    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT_JSON)
    for k, v in res["hypotheses"].items():
        if "horizons" in v and v["horizons"]:
            hs = v["horizons"]
            best = min(hs.values(), key=lambda z: 0)  # placeholder
            line = " ".join(f"{h}:{hs[h].get('ladder','?')}/{round(hs[h].get('mid_mean_bp',0),3)}" for h in hs)
            print(f"{k:24s} {line}")
        else:
            print(f"{k:24s} {v.get('status')}")


if __name__ == "__main__":
    main()
