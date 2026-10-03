# -*- coding: utf-8 -*-
"""V3 Alpha Sweep R1 runner. Protocol frozen before evaluation.

Reads only the frozen V3 snapshots. No orders. No V1/V2 input.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_alpha_sweep_r1/run_sweep_r1.py
"""
from __future__ import annotations
import glob, hashlib, json, math, os, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
SNAP2 = os.path.join(V3, "data", "snapshots", "V3-SNAP-PIT2-20261001T131500Z")
PROTO = os.path.join(HERE, "ALPHA_SWEEP_R1_FROZEN_PROTOCOL.json")
OUT = os.path.join(HERE, "results_alpha_sweep_r1.json")
GAP = 60_000
SEED = 20261002
COST = 0.914


# ---------------- stats ----------------
def reps_for(n):
    return int(min(2000, max(500, math.floor(2e7 / max(1, n)))))


def perm_p(x):
    n = len(x)
    if n < 5:
        return None
    reps = reps_for(n); base = abs(float(np.mean(x)))
    rng = np.random.default_rng(SEED); f = x.astype(np.float32)
    ge = 0; done = 0; chunk = max(1, min(250, max(1, 4_000_000 // max(1, n))))
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        ge += int(np.sum(np.abs((f[None, :] * s).mean(axis=1)) >= base)); done += c
    return float((ge + 1) / (reps + 1))


def boot_ci(x, reps=1500, nblocks=50):
    n = len(x)
    if n < 10:
        return None
    bs = max(1, n // nblocks); nb = int(np.ceil(n / bs))
    pad = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blk = np.nanmean(pad.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(SEED + 1)
    m = blk[rng.integers(0, nb, size=(reps, nb))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def eff_n(ei, ts, hm):
    if not len(ei):
        return 0
    t = ts[ei]; c = 1; last = t[0]
    for x in t[1:]:
        if x - last >= hm:
            c += 1; last = x
    return c


def ladder(eff, gross, net2, p, oos1, ci, std):
    if eff < 30:
        return "INSUFFICIENT_SAMPLE"
    if gross < COST:
        return "COST_INSUFFICIENT"
    if gross - COST <= 0:
        return "REJECT"
    if p is None or p >= 0.05:
        return "EDGE_UNCERTAIN"
    if ci is not None and ci[0] <= 0 <= ci[1]:
        return "EDGE_UNCERTAIN"
    if oos1 is None or oos1 <= 0:
        return "EDGE_UNCERTAIN"
    if net2 <= 0:
        return "EDGE_UNCERTAIN"
    if std > 5 * abs(gross):
        return "EXECUTION_UNREALISTIC"
    return "CANDIDATE"


def eval_dir(hid, idx, d, ts, mid, bid, ask, seg, H_ms, meta=None):
    out = {"hypothesis_id": hid, "corpus_events": int(len(idx)), "horizons": {}}
    for hm in H_ms:
        j = np.searchsorted(ts, ts[idx] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
        cens = int((~v).sum())
        ei, ji, dd = idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
        if len(ei) < 1:
            out["horizons"][str(hm)] = {"n": 0}
            continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g)); pp = perm_p(g); ci = boot_ci(g)
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        oos1 = float(np.mean(g[oosm]) - COST) if oosm.sum() >= 2 else None
        rec = {"n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, hm)),
               "gross_bp": gm, "std_bp": sd, "net_bp": {f"x{x}": float(gm - COST * x) for x in (0., 1., 2., 3.)},
               "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None},
               "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                       "net1x_bp": oos1},
               "perm_p": pp, "reps": reps_for(len(ei)), "boot_ci_bp": ci,
               "ladder": ladder(eff_n(ei, ts, hm), gm, gm - 2 * COST, pp, oos1, ci, sd)}
        if meta is not None:
            rec["buckets"] = meta(ei, g)
        out["horizons"][str(hm)] = rec
    return out


def eval_nondir(hid, ent, ts, mid, seg, H_ms):
    base = np.arange(0, len(ts), 50)
    out = {"hypothesis_id": hid, "corpus_events": int(len(ent)), "horizons": {}}
    for hm in H_ms:
        def mag(ix):
            j = np.searchsorted(ts, ts[ix] + hm, side="left")
            v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ix])
            a, b = ix[v], np.minimum(j, len(ts) - 1)[v]
            return np.abs(mid[b] - mid[a]) / mid[a] * 1e4
        av, bv = mag(ent), mag(base)
        if len(av) < 10 or len(bv) < 10:
            out["horizons"][str(hm)] = {"n": int(len(av)), "ladder": "INSUFFICIENT_SAMPLE"}
            continue
        hit, bhit = float(np.mean(av > COST)), float(np.mean(bv > COST))
        out["horizons"][str(hm)] = {"n": int(len(av)), "mean_abs_move_bp": float(np.mean(av)),
                                    "baseline_mean_abs_bp": float(np.mean(bv)),
                                    "p_gt_cost": hit, "baseline_p_gt_cost": bhit, "lift": hit - bhit,
                                    "effective_n": int(eff_n(ent, ts, hm)),
                                    "verdict": "MORE_VOLATILE" if hit > bhit else "NOT_MORE_VOLATILE",
                                    "ladder": "NON_DIRECTIONAL"}
    return out


# ---------------- feature helpers ----------------
def seg_roll(x, seg, W, mode):
    n = len(x); out = np.zeros(n)
    b = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0)
    end = np.append(b, n)
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    for k in range(len(b)):
        a, e = b[k], end[k + 1]
        idx = np.arange(a, e)
        if mode == "sum":
            out[a:e] = c[idx + 1] - c[np.maximum(idx + 1 - W, a)]
        else:
            out[a:e] = np.minimum(idx - a + 1, W)
    return out


def seg_start(seg):
    b = np.flatnonzero(np.diff(seg, prepend=seg[0] - 1) != 0)
    e = np.append(b, len(seg))
    return np.repeat(b, np.diff(e))


def causal_med(x, seg, W, grid=500):
    n = len(x); out = np.full(n, np.nan); ss = seg_start(seg)
    for p in range(W, n, grid):
        w = x[ss[p]:p]
        if len(w) >= 50:
            out[p:min(n, p + grid)] = float(np.median(w))
    v = np.flatnonzero(~np.isnan(out))
    if not len(v):
        return out
    out[:v[0]] = out[v[0]]
    return out[np.maximum.accumulate(np.where(~np.isnan(out), np.arange(n), 0))]


def onset(c):
    return c & ~np.concatenate([[False], c[:-1]])


def bar_meta_factory(idx_meta, cost=COST):
    def meta(ei, g):
        out = {}
        for name, arr in idx_meta.items():
            slots = arr.get("slots")
            vals = {}
            for e, v in zip(ei, g):
                k = slots.get(int(e))
                if k is None:
                    continue
                vals.setdefault(k, []).append(v)
            out[name] = {k: {"n": len(v), "mean_bp": float(np.mean(v)),
                             "net1x_bp": float(np.mean(v) - cost)} for k, v in sorted(vals.items())}
        return out
    return meta


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    hh = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert hh == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", hh[:16])
    H = {h["id"]: h for h in proto["hypotheses"]}
    res = {"schema": "v3_alpha_sweep_r1_results/1", "protocol_hash": hh,
           "hypothesis_count": proto["hypothesis_count"], "cost_bp": COST,
           "preflight": {}, "hypotheses": {}}

    # ============ PREFLIGHT (synthetic) ============
    rng = np.random.default_rng(SEED)
    pre = {}
    # tick-scale features
    m = rng.normal(0, 0.05, 2_000_000)
    sgn = np.sign(m); sgn[sgn == 0] = 1
    ti = pd.Series(sgn).rolling(100).sum().to_numpy() / math.sqrt(100)
    pre["TI"] = {"std": float(np.nanstd(ti)), "band": [0.85, 1.15]}
    pre["TI"]["result"] = "PASS" if 0.85 <= pre["TI"]["std"] <= 1.15 else "FAIL"
    mid_s = 2000 + np.cumsum(m)
    sd3 = pd.Series(m).rolling(3000).std().to_numpy()
    r100 = pd.Series(m).rolling(100).sum().to_numpy()
    r500 = pd.Series(m).rolling(500).sum().to_numpy()
    z100 = r100 / (sd3 * math.sqrt(100)); z500 = r500 / (sd3 * math.sqrt(500))
    pre["z100"] = {"std": float(np.nanstd(z100)), "band": [0.85, 1.15]}
    pre["z100"]["result"] = "PASS" if 0.85 <= pre["z100"]["std"] <= 1.15 else "FAIL"
    pre["z500"] = {"std": float(np.nanstd(z500)), "band": [0.85, 1.15]}
    pre["z500"]["result"] = "PASS" if 0.85 <= pre["z500"]["std"] <= 1.15 else "FAIL"
    # bar-scale
    br = rng.normal(0, 0.0005, 200_000)
    bs = pd.Series(br)
    sig20 = bs.rolling(20).std().shift(1)
    z5s = (bs.rolling(5).sum()) / (sig20 * math.sqrt(5))
    z1s = bs / sig20
    pre["z5"] = {"std": float(np.nanstd(z5s.to_numpy())), "band": [0.85, 1.15]}
    pre["z5"]["result"] = "PASS" if 0.85 <= pre["z5"]["std"] <= 1.15 else "FAIL"
    pre["z1"] = {"std": float(np.nanstd(z1s.to_numpy())), "band": [0.85, 1.15]}
    pre["z1"]["result"] = "PASS" if 0.85 <= pre["z1"]["std"] <= 1.15 else "FAIL"
    res["preflight"] = pre
    bad = [k for k, v in pre.items() if v["result"] == "FAIL"]
    print("preflight:", {k: round(v["std"], 4) for k, v in pre.items()}, "FAIL:", bad)

    # ============ TICK corpus ============
    print("loading TICK corpus ...")
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files], ignore_index=True)
    df = df.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    bid = df["bid"].to_numpy(np.float64); ask = df["ask"].to_numpy(np.float64)
    mid = (bid + ask) / 2.0
    d = np.diff(ts, prepend=ts[0]); seg = np.cumsum((d <= 0) | (d > GAP)) - 1
    print("  ticks", len(ts), "segments", int(seg[-1]) + 1)

    dm = np.diff(mid, prepend=np.nan)
    sn = np.sign(np.nan_to_num(dm))
    r100 = seg_roll(dm, seg, 100, "sum"); r500 = seg_roll(dm, seg, 500, "sum")
    c3000 = seg_roll(np.zeros(len(dm)), seg, 3000, "cnt")
    s3000 = seg_roll(dm ** 2, seg, 3000, "sum")
    sd3 = np.sqrt(np.maximum(s3000 / np.maximum(c3000, 1), 1e-18))
    ti100 = seg_roll(sn, seg, 100, "sum") / np.sqrt(np.maximum(seg_roll(np.zeros(len(dm)), seg, 100, "cnt"), 1))
    s200 = seg_roll(sn, seg, 200, "sum"); c200 = np.maximum(seg_roll(np.zeros(len(dm)), seg, 200, "cnt"), 1)
    press = np.abs(s200) / c200
    spread = (ask - bid) / mid * 1e4
    medsp = causal_med(spread, seg, 3000)
    z100 = r100 / (sd3 * math.sqrt(100)); z500 = r500 / (sd3 * math.sqrt(500))

    def ent(mask):
        return np.flatnonzero(mask)
    tick_tests = []
    if "TI" in bad or "z100" in bad or "z500" in bad:
        res["hypotheses"]["T1_TICK_IMBALANCE"] = {"status": "INVALID_IMPLEMENTATION"}
    else:
        e = ent(onset(np.abs(ti100) >= 2.0)); tick_tests.append(("T1_TICK_IMBALANCE", e, np.sign(ti100[e]).astype(int)))
    e2 = ent(onset(press >= 0.85)); tick_tests.append(("T2_PRESSURE_PERSIST", e2, np.sign(s200[e2]).astype(int)))
    tick_tests.append(("T3_LIQUIDITY_SHOCK", ent(onset(np.abs(z500) >= 2.0)), None))
    e4 = ent(onset((spread >= 1.5 * medsp) & (np.abs(z100) >= 1.0)))
    tick_tests.append(("T4_SPREAD_STRESS", e4, np.sign(r100[e4]).astype(int)))
    tick_tests.append(("T5_MICRO_REVERSAL", ent(onset(np.abs(z100) >= 2.0)), None))

    THm = [int(x) for x in proto["frozen_thresholds"]["abs_z_2"] > 0 and [100, 250, 500, 1000, 2000, 5000]]
    THm = [100, 250, 500, 1000, 2000, 5000]
    for hid, e, dd in tick_tests:
        if hid in res["hypotheses"]:
            continue
        base = H[hid]["direction"]
        sgn_ = np.sign(r500[e]).astype(int) if dd is None else dd
        if base == "fade":
            sgn_ = -sgn_
        res["hypotheses"][hid] = eval_dir(hid, e.astype(int), sgn_, ts, mid, bid, ask, seg, THm)
        mir = sgn_ * -1
        res["hypotheses"][hid + "__MIRROR"] = eval_dir(hid + "__MIRROR", e.astype(int), mir, ts, mid, bid, ask, seg, THm)
        print("  ", hid, "n=", len(e))

    # ============ BAR corpus ============
    print("building 1m bars ...")
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    bars = (b.groupby(["seg", "minute"], sort=True).agg(close=("mid", "last"), close_ts=("ts", "last"),
                                                        n=("mid", "size"), spread=("mid", "size"))
              .reset_index().sort_values("close_ts").reset_index(drop=True))
    bars["ret1"] = np.nan; bars["sig20"] = np.nan; bars["ret5"] = np.nan; bars["rv5"] = np.nan
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = bars["close"].to_numpy()[idx]
        srs = pd.Series(c); r1 = srs.pct_change()
        bars.iloc[idx, bars.columns.get_loc("ret1")] = r1.to_numpy()
        bars.iloc[idx, bars.columns.get_loc("sig20")] = r1.rolling(20, min_periods=20).std().shift(1).to_numpy()
        bars.iloc[idx, bars.columns.get_loc("ret5")] = srs.pct_change(5).to_numpy()
        bars.iloc[idx, bars.columns.get_loc("rv5")] = r1.rolling(5, min_periods=5).std().to_numpy()
    bars["z5"] = bars["ret5"] / (bars["sig20"] * math.sqrt(5))
    bars["z1"] = bars["ret1"] / bars["sig20"]
    bars["ch60"] = np.nan
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = bars["close"].to_numpy()[idx]
        bars.iloc[idx, bars.columns.get_loc("ch60")] = (pd.Series(c).pct_change(60)).to_numpy()
    q67 = np.full(len(bars), np.nan); q20 = np.full(len(bars), np.nan); q33 = np.full(len(bars), np.nan); q67b = np.full(len(bars), np.nan)
    rv = bars["rv5"].to_numpy()
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); ser = pd.Series(rv[idx])
        q67[idx] = ser.expanding(min_periods=100).quantile(0.67).to_numpy()
        q20[idx] = ser.expanding(min_periods=100).quantile(0.20).to_numpy()
        q33[idx] = ser.expanding(min_periods=100).quantile(0.33).to_numpy()
        q67b[idx] = q67[idx]
    bars["q67"] = q67; bars["q20"] = q20; bars["q33"] = q33
    # donchian
    hi20 = np.full(len(bars), np.nan); lo20 = np.full(len(bars), np.nan)
    cl = bars["close"].to_numpy()
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); ser = pd.Series(cl[idx])
        hi20[idx] = ser.rolling(20, min_periods=20).max().shift(1).to_numpy()
        lo20[idx] = ser.rolling(20, min_periods=20).min().shift(1).to_numpy()
    bars["hi20"] = hi20; bars["lo20"] = lo20
    bts = bars["close_ts"].to_numpy()

    def bent(mask):
        bb = bars[mask]
        return np.searchsorted(ts, bb["close_ts"].to_numpy() + 1, side="left")
    BHm = [1, 5, 15, 30, 60]
    Bms = [x * 60000 for x in BHm]

    def runbar(hid, mask, dirfn, mirror=True):
        bidx = np.flatnonzero(mask)
        e = np.searchsorted(ts, bts[bidx] + 1, "left")
        ok = e < len(ts)
        e = e[ok]; bidx = bidx[ok]
        s = dirfn(bidx)
        res["hypotheses"][hid] = eval_dir(hid, e.astype(int), s, ts, mid, bid, ask, seg, Bms)
        if mirror:
            res["hypotheses"][hid + "__MIRROR"] = eval_dir(hid + "__MIRROR", e.astype(int), -s, ts, mid, bid, ask, seg, Bms)
        print("  ", hid, "n=", len(e))
        return e, s

    z5v = bars["z5"].to_numpy(); r1v = bars["ret1"].to_numpy(); r5v = bars["ret5"].to_numpy()
    if "z5" in bad or "z1" in bad:
        for hid in ("P1_IMPULSE", "P2_ABNORMAL_REVERSAL", "X1_SCALE_AGREEMENT", "X2_SCALE_DISAGREEMENT", "X3_HTF_REGIME_COND"):
            res["hypotheses"][hid] = {"status": "INVALID_IMPLEMENTATION"}
    else:
        runbar("P1_IMPULSE", np.abs(z5v) >= 2.0, lambda e: np.sign(np.nan_to_num(r5v[e])).astype(int))
        runbar("P2_ABNORMAL_REVERSAL", np.abs(np.nan_to_num(bars["z1"].to_numpy())) >= 3.0,
               lambda e: -np.sign(np.nan_to_num(r1v[e])).astype(int))
    rv_ = bars["rv5"].to_numpy(); prev = np.concatenate([[False], (rv_ >= bars["q67"].to_numpy())[:-1]])
    runbar("P3_VOL_EXPANSION_DIR", (rv_ >= bars["q67"].to_numpy()) & ~prev,
           lambda e: np.sign(np.nan_to_num(r1v[e])).astype(int))
    runbar("P4_BREAKOUT", cl > bars["hi20"].to_numpy(), lambda e: np.ones(len(e), int))
    madehigh = np.zeros(len(bars), bool)
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = cl[idx]; hh = bars["hi20"].to_numpy()[idx]
        mk = (c > hh) & np.isfinite(hh)
        within = pd.Series(mk.astype(float)).rolling(5, min_periods=1).max().to_numpy() > 0
        madehigh[idx] = within & (c < hh) & np.isfinite(hh)
    runbar("P5_FAILED_BREAKOUT", madehigh, lambda e: -np.ones(len(e), int))
    # P6 non-directional
    lowrv = (rv_ <= bars["q20"].to_numpy()); pv = np.concatenate([[False], lowrv[:-1]])
    e6 = bent(lowrv & ~pv); e6 = e6[e6 < len(ts)]
    res["hypotheses"]["P6_RANGE_COMPRESSION"] = eval_nondir("P6_RANGE_COMPRESSION", e6.astype(int), ts, mid, seg, Bms)
    print("   P6_RANGE_COMPRESSION n=", len(e6))
    # X1/X2/X3
    agree = np.sign(np.nan_to_num(r5v)) == np.sign(np.nan_to_num(bars["ch60"].to_numpy()))
    runbar("X1_SCALE_AGREEMENT", (np.abs(z5v) >= 2.0) & agree, lambda e: np.sign(np.nan_to_num(r5v[e])).astype(int))
    runbar("X2_SCALE_DISAGREEMENT", (np.abs(z5v) >= 2.0) & ~agree, lambda e: np.sign(np.nan_to_num(r5v[e])).astype(int))
    runbar("X3_HTF_REGIME_COND", (np.abs(z5v) >= 2.0) & (bars["ch60"].to_numpy() > 0) & (r5v > 0),
           lambda e: np.ones(len(e), int))

    # ---- S1..S5 state conditioning: pooled P1 + bucket report (pre-registered: pooled gate + all-bucket same sign)
    spread_bar = np.full(len(bars), np.nan)
    bars["n_ticks"] = bars["n"].to_numpy()
    # build bucket label arrays
    buckets = {}
    t3v = np.nanquantile(rv_[np.isfinite(rv_)], [1/3, 2/3])
    buckets["S1_VOL_TERCILE"] = np.where(rv_ <= t3v[0], "LOW", np.where(rv_ >= t3v[1], "HIGH", "MID"))
    # bar spread proxy: mean absolute tick-to-tick move inside the minute is expensive; use hi-lo proxy via n/ rv
    sp_tick = (ask - bid) / mid * 1e4
    spbar = pd.DataFrame({"seg": seg, "minute": ts // 60000, "sp": sp_tick}).groupby(["seg", "minute"], sort=True)["sp"].mean().reset_index()
    spbar = spbar.rename(columns={"sp": "spread_bar"})
    bars = bars.merge(spbar, on=["seg", "minute"], how="left")
    spv = bars["spread_bar"].to_numpy(); t3s = np.nanquantile(spv[np.isfinite(spv)], [1/3, 2/3])
    buckets["S2_SPREAD_TERCILE"] = np.where(spv <= t3s[0], "TIGHT", np.where(spv >= t3s[1], "WIDE", "MID"))
    ntv = bars["n_ticks"].to_numpy(); t3a = np.nanquantile(ntv[np.isfinite(ntv)], [1/3, 2/3])
    buckets["S3_ACTIVITY_TERCILE"] = np.where(ntv <= t3a[0], "QUIET", np.where(ntv >= t3a[1], "BUSY", "NORMAL"))
    hour = ((bts // 3600000) % 24)
    buckets["S4_SESSION"] = np.where(hour < 8, "ASIA", np.where(hour < 16, "LONDON", "NY"))
    er = np.full(len(bars), np.nan)
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = cl[idx]
        net = np.abs(pd.Series(c).diff(20).to_numpy()); tot = pd.Series(np.abs(np.diff(c, prepend=c[0]))).rolling(20).sum().to_numpy()
        er[idx] = net / np.where(tot > 0, tot, np.nan)
    buckets["S5_TREND_RANGE"] = np.where(np.nan_to_num(er) >= 0.5, "TREND", "RANGE")

    idx_meta = {k: {"slots": {int(t): v for t, v in zip(bts, buckets[k])}} for k in buckets}
    mf = bar_meta_factory(idx_meta)
    eP1 = bent(np.abs(z5v) >= 2.0); eP1 = eP1[eP1 < len(ts)]
    bar_of_entry = np.searchsorted(bts, ts[eP1] - 1, side="left")
    sP1 = np.sign(np.nan_to_num(r5v[np.minimum(bar_of_entry, len(bars) - 1)])).astype(int)
    for hid in buckets:
        res["hypotheses"][hid] = eval_dir(hid, eP1.astype(int), sP1, ts, mid, bid, ask, seg, Bms, meta=mf)
        res["hypotheses"][hid + "__MIRROR"] = eval_dir(hid + "__MIRROR", eP1.astype(int), -sP1, ts, mid, bid, ask, seg, Bms, meta=mf)
        print("  ", hid, "n=", len(eP1))

    # ============ EVENT corpus ============
    print("loading EVENT corpus ...")
    ev = []
    vd = os.path.join(V3, "research", "v3_pit_supplement_r1", "vintages")
    for fn in sorted(glob.glob(os.path.join(vd, "*.json"))):
        v = json.load(open(fn, encoding="utf-8"))
        for e in v.get("events", []):
            if e.get("pub_time"):
                try:
                    t = pd.Timestamp(e["pub_time"], tz="Asia/Shanghai").tz_convert("UTC").value // 10**6
                    ev.append((int(t), fn))
                except Exception:
                    pass
    for cand in glob.glob(os.path.join(V3, "**", "V3_JIN10_EVENT_PIT.json"), recursive=True):
        v = json.load(open(cand, encoding="utf-8"))
        for e in v.get("events", []):
            if e.get("pub_time_utc"):
                try:
                    t = pd.Timestamp(e["pub_time_utc"]).value // 10**6
                    ev.append((int(t), "V3_JIN10_EVENT_PIT.json"))
                except Exception:
                    pass
    ev = sorted(set(ev))
    res["event_corpus"] = {"events_loaded": len(ev)}
    print("  events", len(ev))
    if len(ev) < 20:
        for hid in ("E1_EVENT_X_MICRO", "E2_EVENT_X_VOL", "E3_EVENT_X_SPREAD", "E4_POST_EVENT_CONT", "E5_POST_EVENT_FADE"):
            res["hypotheses"][hid] = {"status": "DATA_BLOCKED", "reason": "calendar events unavailable"}
    else:
        files2 = sorted(glob.glob(os.path.join(SNAP2, "*", "*.parquet")) or glob.glob(os.path.join(SNAP2, "raw_ticks", "*.parquet")))
        d2 = pd.concat([pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files2], ignore_index=True)
        d2 = d2.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
        ts2 = d2["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
        mid2 = (d2["bid"].to_numpy(np.float64) + d2["ask"].to_numpy(np.float64)) / 2.0
        dd2 = np.diff(ts2, prepend=ts2[0]); seg2 = np.cumsum((dd2 <= 0) | (dd2 > GAP)) - 1
        dm2 = np.diff(mid2, prepend=np.nan); sn2 = np.sign(np.nan_to_num(dm2))
        ti2 = seg_roll(sn2, seg2, 100, "sum") / np.sqrt(np.maximum(seg_roll(np.zeros(len(dm2)), seg2, 100, "cnt"), 1))
        sp2 = (d2["ask"].to_numpy() - d2["bid"].to_numpy()) / mid2 * 1e4
        med2 = causal_med(sp2, seg2, 3000)
        EVH = [60_000, 300_000, 900_000]
        evts = [t for t, _ in ev if ts2[0] <= t <= ts2[-1]]
        # E1 event-proximity x tick imbalance
        ent1 = []; dir1 = []
        ons = np.flatnonzero(onset(np.abs(ti2) >= 2.0))
        for t in evts:
            i0 = int(np.searchsorted(ts2, t, "left"))
            j = int(np.searchsorted(ts2, t + 300_000, "left"))
            k = ons[(ons >= i0) & (ons < j)]
            if len(k):
                ent1.append(k[0]); dir1.append(int(np.sign(ti2[k[0]])))
        if len(ent1) >= 10:
            res["hypotheses"]["E1_EVENT_X_MICRO"] = eval_dir("E1_EVENT_X_MICRO", np.array(ent1, int), np.array(dir1, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
            res["hypotheses"]["E1_EVENT_X_MICRO__MIRROR"] = eval_dir("E1_EVENT_X_MICRO__MIRROR", np.array(ent1, int), -np.array(dir1, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
        else:
            res["hypotheses"]["E1_EVENT_X_MICRO"] = {"status": "DATA_BLOCKED", "n": len(ent1)}
        # E2 / E3 pre-event 60s move
        ent2 = []; dir2 = []
        for t in evts:
            i = int(np.searchsorted(ts2, t, "left"))
            k = int(np.searchsorted(ts2, t - 60_000, "left"))
            if i < len(ts2) and i - k >= 2 and np.isfinite(mid2[i]) and np.isfinite(mid2[k]):
                mvv = mid2[i] - mid2[k]
                if abs(mvv) > 0:
                    ent2.append(i); dir2.append(int(np.sign(mvv)))
        if len(ent2) >= 10:
            res["hypotheses"]["E2_EVENT_X_VOL"] = eval_dir("E2_EVENT_X_VOL", np.array(ent2, int), np.array(dir2, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
            res["hypotheses"]["E2_EVENT_X_VOL__MIRROR"] = eval_dir("E2_EVENT_X_VOL__MIRROR", np.array(ent2, int), -np.array(dir2, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
            wide = [i for i, t in zip(ent2, evts) if np.isfinite(med2[i]) and sp2[i] >= 1.2 * med2[i]]
            widx = [i for i in wide]
            if len(widx) >= 10:
                res["hypotheses"]["E3_EVENT_X_SPREAD"] = eval_dir("E3_EVENT_X_SPREAD", np.array(widx, int), -np.array([dir2[ent2.index(i)] for i in widx], int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
            else:
                res["hypotheses"]["E3_EVENT_X_SPREAD"] = {"status": "DATA_BLOCKED", "n": len(widx)}
        else:
            res["hypotheses"]["E2_EVENT_X_VOL"] = {"status": "DATA_BLOCKED", "n": len(ent2)}
            res["hypotheses"]["E3_EVENT_X_SPREAD"] = {"status": "DATA_BLOCKED"}
        # E4/E5 first 1m move after the event
        ent4 = []; dir4 = []
        for t in evts:
            i = int(np.searchsorted(ts2, t, "left"))
            j = int(np.searchsorted(ts2, t + 60_000, "left"))
            if i < len(ts2) and j < len(ts2) and j - i >= 2:
                mv = mid2[j] - mid2[i]
                if abs(mv) > 0:
                    ent4.append(j); dir4.append(int(np.sign(mv)))
        if len(ent4) >= 10:
            res["hypotheses"]["E4_POST_EVENT_CONT"] = eval_dir("E4_POST_EVENT_CONT", np.array(ent4, int), np.array(dir4, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
            res["hypotheses"]["E5_POST_EVENT_FADE"] = eval_dir("E5_POST_EVENT_FADE", np.array(ent4, int), -np.array(dir4, int), ts2, mid2, d2["bid"].to_numpy(), d2["ask"].to_numpy(), seg2, EVH)
        else:
            for hid in ("E4_POST_EVENT_CONT", "E5_POST_EVENT_FADE"):
                res["hypotheses"][hid] = {"status": "DATA_BLOCKED", "n": len(ent4)}

    # ============ taxonomy + global FDR ============
    tests = []
    for hid, blk in res["hypotheses"].items():
        if "horizons" not in blk:
            continue
        for hm, z in blk["horizons"].items():
            if z.get("perm_p") is not None:
                tests.append({"id": hid, "horizon": hm, "perm_p": z["perm_p"],
                              "gross_bp": z.get("gross_bp"), "eff_n": z.get("effective_n"),
                              "ladder": z.get("ladder")})
    tests.sort(key=lambda t: t["perm_p"])
    m = len(tests)
    for r, t in enumerate(tests, start=1):
        t["bh_cutoff"] = 0.05 * r / m
        t["survives_fdr"] = t["perm_p"] <= t["bh_cutoff"]
    res["fdr"] = {"method": "BH", "alpha": 0.05, "n_tests": m,
                  "surviving": sum(1 for t in tests if t["survives_fdr"]), "table": tests}

    ORDER = ["VALIDATED_EDGE", "EDGE_UNCERTAIN", "COST_INSUFFICIENT", "DATA_BLOCKED", "INVALID_IMPLEMENTATION"]
    tax = {}
    for hid, blk in res["hypotheses"].items():
        if blk.get("status") in ("INVALID_IMPLEMENTATION", "DATA_BLOCKED"):
            tax[hid] = blk["status"]; continue
        rungs = [z.get("ladder") for z in blk.get("horizons", {}).values() if z.get("ladder")]
        effs = [z.get("effective_n", 0) for z in blk.get("horizons", {}).values()]
        if not any(e >= 30 for e in effs):
            tax[hid] = "DATA_BLOCKED"; continue
        if any(r == "CANDIDATE" for r in rungs):
            tax[hid] = "VALIDATED_EDGE"
        elif any(r in ("EDGE_UNCERTAIN", "EXECUTION_UNREALISTIC") for r in rungs):
            tax[hid] = "EDGE_UNCERTAIN"
        else:
            tax[hid] = "COST_INSUFFICIENT"
    res["taxonomy"] = tax
    base_ids = [k for k in res["hypotheses"] if not k.endswith("__MIRROR")]
    res["summary"] = {
        "hypotheses_total": proto["hypothesis_count"],
        "hypotheses_evaluated": len([k for k in base_ids if tax.get(k) not in ("DATA_BLOCKED", "INVALID_IMPLEMENTATION")]),
        "validated_edge_count": sum(1 for k in base_ids if tax.get(k) == "VALIDATED_EDGE"),
        "counts": {k: sum(1 for x in base_ids if tax.get(x) == k) for k in ORDER},
        "best_net1x_bp": None, "best_oos_net1x_bp": None, "eff_n_range": None,
    }
    allz = [(k, hm, z) for k, blk in res["hypotheses"].items() if "horizons" in blk
            for hm, z in blk["horizons"].items() if z.get("gross_bp") is not None]
    if allz:
        res["summary"]["best_net1x_bp"] = round(max(z["gross_bp"] - COST for _, _, z in allz), 4)
        res["summary"]["best_gross_bp"] = round(max(z["gross_bp"] for _, _, z in allz), 4)
        oos = [z["oos"]["net1x_bp"] for _, _, z in allz if z.get("oos", {}).get("net1x_bp") is not None]
        res["summary"]["best_oos_net1x_bp"] = round(max(oos), 4) if oos else None
        es = [z["effective_n"] for _, _, z in allz]
        res["summary"]["eff_n_range"] = [min(es), max(es)]

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    print("summary:", json.dumps(res["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
