# -*- coding: utf-8 -*-
"""V3 R2 confirmation: P3 independent re-check (MAIN + EXTENDED) and X3 Beta Null Test.

Protocol frozen before computation. Read-only. No orders.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_r2_confirmation/run_r2_conf.py
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
PROTO = os.path.join(HERE, "V3_R2_FROZEN_PROTOCOL.json")
OUT = os.path.join(HERE, "results_v3_r2.json")
GAP = 60_000
SEED = 20261003
COST = 0.914
N = 20


def load_one(snap, cols=("ts_utc", "bid", "ask")):
    files = sorted(glob.glob(os.path.join(snap, "*", "*.parquet")))
    d = pd.concat([pd.read_parquet(f, columns=list(cols)) for f in files], ignore_index=True)
    return d


def to_arrays(d):
    d = d.sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = d["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    bid = d["bid"].to_numpy(np.float64); ask = d["ask"].to_numpy(np.float64)
    return ts, bid, ask


def segments(ts):
    dd = np.diff(ts, prepend=ts[0])
    return np.cumsum((dd <= 0) | (dd > GAP)) - 1


def build_bars(ts, mid, seg):
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    g = (b.groupby(["seg", "minute"], sort=True).agg(close=("mid", "last"), close_ts=("ts", "last"), n=("mid", "size"))
          .reset_index().sort_values("close_ts").reset_index(drop=True))
    g["ret1"] = np.nan; g["sig20"] = np.nan; g["rv5"] = np.nan
    for s, idx in g.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = g["close"].to_numpy()[idx]
        srs = pd.Series(c); r1 = srs.pct_change()
        g.iloc[idx, g.columns.get_loc("ret1")] = r1.to_numpy()
        g.iloc[idx, g.columns.get_loc("sig20")] = r1.rolling(N, min_periods=N).std().shift(1).to_numpy()
        g.iloc[idx, g.columns.get_loc("rv5")] = r1.rolling(5, min_periods=5).std().to_numpy()
    g["z5"] = (g["close"].pct_change(5)) / (g["sig20"] * math.sqrt(5))
    g["ch60"] = np.nan
    for s, idx in g.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx); c = g["close"].to_numpy()[idx]
        g.iloc[idx, g.columns.get_loc("ch60")] = pd.Series(c).pct_change(60).to_numpy()
    q67 = np.full(len(g), np.nan)
    rv = g["rv5"].to_numpy()
    for s, idx in g.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx)
        q67[idx] = pd.Series(rv[idx]).expanding(min_periods=100).quantile(0.67).to_numpy()
    g["q67"] = q67
    return g


def onset(c):
    return c & ~np.concatenate([[False], c[:-1]])


def perm_p(x, reps=2000):
    n = len(x)
    if n < 5:
        return None
    base = abs(float(np.mean(x))); rng = np.random.default_rng(SEED); f = x.astype(np.float32)
    ge = 0; done = 0; chunk = max(1, min(250, max(1, 4_000_000 // max(1, n))))
    while done < reps:
        c = min(chunk, reps - done)
        s = rng.integers(0, 2, size=(c, n)).astype(np.int8) * 2 - 1
        ge += int(np.sum(np.abs((f[None, :] * s).mean(axis=1)) >= base)); done += c
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


def eff_n(ei, ts, hm):
    if not len(ei):
        return 0
    t = ts[ei]; c = 1; last = t[0]
    for x in t[1:]:
        if x - last >= hm:
            c += 1; last = x
    return c


def max_dd(x):
    if not len(x):
        return None
    c = np.cumsum(x); peak = np.maximum.accumulate(c)
    return float(np.min(c - peak))


def evaluate(idx, d, ts, mid, seg, Bms, buckets=None):
    out = {}
    for hm in Bms:
        j = np.searchsorted(ts, ts[idx] + hm, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
        cens = int((~v).sum())
        ei, ji, dd = idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
        if len(ei) < 2:
            out[str(hm)] = {"n": int(len(ei)), "ladder": "INSUFFICIENT_SAMPLE"}
            continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g))
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        rec = {"n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, hm)),
               "overlap_ratio": float(hm / max(1.0, float(np.median(np.diff(ts[ei]))))) if len(ei) > 1 else None,
               "gross_bp": gm, "std_bp": sd,
               "net_bp": {f"x{x}": float(gm - COST * x) for x in (0., 1., 2., 3.)},
               "max_drawdown_bp": max_dd(g),
               "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None},
               "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                       "net1x_bp": (float(np.mean(g[oosm]) - COST) if oosm.sum() >= 2 else None)},
               "perm_p": perm_p(g), "boot_ci_bp": boot_ci(g)}
        if buckets is not None:
            subs = {}
            for name, labels in buckets.items():
                pos = np.searchsorted(ts, ts[ei], side="left")
                acc = {}
                for p_, val in zip(pos, g):
                    k = labels.get(int(p_))
                    if k is None:
                        continue
                    acc.setdefault(k, []).append(val)
                subs[name] = {k: {"n": len(v2), "mean_bp": float(np.mean(v2)),
                                  "net1x_bp": float(np.mean(v2) - COST)} for k, v2 in sorted(acc.items())}
            rec["subsamples"] = subs
        out[str(hm)] = rec
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    hh = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert hh == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", hh[:16])
    Bms = [h * 60_000 for h in proto["P3"]["horizons_min"]]

    print("loading snapshots ...")
    dmain = load_one(SNAP); dpit2 = load_one(SNAP2)
    dext = pd.concat([dmain, dpit2], ignore_index=True).drop_duplicates(subset=["ts_utc"]).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    corpora = {}
    for tag, dd in (("MAIN", dmain), ("EXTENDED", dext)):
        ts, bid, ask = to_arrays(dd)
        mid = (bid + ask) / 2.0; seg = segments(ts)
        bars = build_bars(ts, mid, seg)
        corpora[tag] = {"ts": ts, "mid": mid, "bid": bid, "ask": ask, "seg": seg, "bars": bars}
        print(f"  {tag}: ticks={len(ts)} segments={int(seg[-1])+1} bars={len(bars)} "
              f"span={pd.to_datetime(ts[0],unit='ms',utc=True)} .. {pd.to_datetime(ts[-1],unit='ms',utc=True)}")

    res = {"schema": "v3_r2_confirmation_results/1", "protocol_hash": hh, "cost_bp": COST}

    # ---------------- P3 ----------------
    res["P3"] = {}
    for tag, C in corpora.items():
        ts, mid, seg, bars = C["ts"], C["mid"], C["seg"], C["bars"]
        rv = bars["rv5"].to_numpy(); q = bars["q67"].to_numpy()
        prev = np.concatenate([[False], (rv >= q)[:-1]])
        mask = (rv >= q) & ~prev & np.isfinite(rv) & np.isfinite(q)
        bidx = np.flatnonzero(mask)
        bts = bars["close_ts"].to_numpy()
        e = np.searchsorted(ts, bts[bidx] + 1, "left")
        ok = e < len(ts); e = e[ok]; bidx = bidx[ok]
        s = np.sign(np.nan_to_num(bars["ret1"].to_numpy()[bidx])).astype(int)
        # buckets keyed by ENTRY TICK index (fixed vs R1)
        hour = ((ts[e] // 3600000) % 24)
        rv_ev = np.nan_to_num(rv[bidx])
        t3 = np.quantile(rv_ev, [1/3, 2/3]) if len(rv_ev) else [0, 0]
        sp_tick = (C["ask"] - C["bid"]) / C["mid"] * 1e4
        spbar = pd.DataFrame({"seg": seg, "minute": ts // 60000, "sp": sp_tick}).groupby(["seg", "minute"], sort=True)["sp"].mean().reset_index()
        bb = bars.merge(spbar, on=["seg", "minute"], how="left")
        spv = np.nan_to_num(bb["spread_bar_line"].to_numpy()) if "spread_bar_line" in bb.columns else np.nan_to_num(bb["sp"].to_numpy())
        spv_ev = spv[bidx] if len(spv) >= len(bars) else np.zeros(len(bidx))
        t3s = np.quantile(spv_ev, [1/3, 2/3]) if len(spv_ev) else [0, 0]
        buckets = {
            "session": {int(t_): ("ASIA" if (t_ // 3600000) % 24 < 8 else ("LONDON" if (t_ // 3600000) % 24 < 16 else "NY")) for t_ in ts[e]},
            "vol_tercile": {int(t_): ("LOW" if r_ <= t3[0] else ("HIGH" if r_ >= t3[1] else "MID")) for t_, r_ in zip(ts[e], rv_ev)},
            "spread_tercile": {int(t_): ("TIGHT" if s_ <= t3s[0] else ("WIDE" if s_ >= t3s[1] else "MID")) for t_, s_ in zip(ts[e], spv_ev)},
        }
        res["P3"][tag] = evaluate(e.astype(int), s, ts, mid, seg, Bms, buckets)
        print(f"  P3 {tag}: triggers={len(e)}")

    # ------------- X3 + nulls (MAIN sample, identical entries) -------------
    C = corpora["MAIN"]; ts, mid, bid, ask, seg, bars = C["ts"], C["mid"], C["bid"], C["ask"], C["seg"], C["bars"]
    bts = bars["close_ts"].to_numpy()
    z5 = np.nan_to_num(bars["z5"].to_numpy()); ch60 = np.nan_to_num(bars["ch60"].to_numpy())
    ret5 = np.nan_to_num(bars["close"].pct_change(5).to_numpy())
    x3mask = (np.abs(z5) >= 2.0) & (ch60 > 0) & (ret5 > 0)
    bidx = np.flatnonzero(x3mask)
    e = np.searchsorted(ts, bts[bidx] + 1, "left")
    ok = e < len(ts); e = e[ok]
    ones = np.ones(len(e), int)
    res["X3"] = {"n_entries": int(len(e)),
                 "X3_signal_long": evaluate(e.astype(int), ones, ts, mid, seg, Bms),
                 "NULL_UNCOND_LONG_SAME_TIMES": evaluate(e.astype(int), ones, ts, mid, seg, Bms)}
    # note: X3 direction is always +1, so "X3 signal" and "unconditional long at the same times"
    # produce IDENTICAL trades; the meaningful null is a DIFFERENT entry set. Add it:
    allb = np.arange(len(bars))
    ea = np.searchsorted(ts, bts[allb] + 1, "left"); ea = ea[ea < len(ts)]
    res["X3"]["NULL_UNCOND_LONG_ALL_BARS"] = evaluate(ea.astype(int), np.ones(len(ea), int), ts, mid, seg, Bms)
    # random-entry control with the SAME count as X3 (deterministic seed)
    rng = np.random.default_rng(SEED)
    if len(e) > 0:
        ridx = np.sort(rng.choice(len(bars), size=min(len(e), len(bars)), replace=False))
        er = np.searchsorted(ts, bts[ridx] + 1, "left"); er = er[er < len(ts)]
        res["X3"]["NULL_RANDOM_ENTRIES_SAME_COUNT"] = evaluate(er.astype(int), np.ones(len(er), int), ts, mid, seg, Bms)
    # buy and hold per segment
    bh = []
    for s_, idx in pd.Series(seg).groupby(seg).indices.items():
        idx = np.asarray(idx)
        a, b_ = idx[0], idx[-1]
        if mid[a] > 0:
            bh.append(float((mid[b_] - mid[a]) / mid[a] * 1e4))
    res["X3"]["NULL_BUY_AND_HOLD_per_segment_bp"] = {"n_segments": len(bh),
                                                     "mean_bp": float(np.mean(bh)) if bh else None,
                                                     "median_bp": float(np.median(bh)) if bh else None}
    print("  X3 entries:", len(e), " buy&hold segments:", len(bh), " mean bp:", round(float(np.mean(bh)), 3) if bh else None)

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    for tag in res["P3"]:
        print(f"--- P3 {tag} ---")
        for hm, z in res["P3"][tag].items():
            if z.get("gross_bp") is None:
                print("   ", hm, z.get("ladder")); continue
            print(f"   h={int(hm)//60000:>3}m n={z['n']:>5} eff={z['effective_n']:>5} gross={z['gross_bp']:+.4f} "
                  f"net1x={z['gross_bp']-COST:+.4f} net2x={z['gross_bp']-2*COST:+.4f} net3x={z['gross_bp']-3*COST:+.4f} "
                  f"IS={z['is']['mean_bp']} OOS={z['oos']['mean_bp']} p={z['perm_p']} CI={[round(x,2) for x in (z['boot_ci_bp'] or [])]}")
    print("--- X3 vs nulls ---")
    for k in ("X3_signal_long", "NULL_UNCOND_LONG_ALL_BARS", "NULL_RANDOM_ENTRIES_SAME_COUNT"):
        blk = res["X3"].get(k)
        if not blk:
            continue
        vals = [(int(h)//60000, z.get("gross_bp")) for h, z in blk.items() if z.get("gross_bp") is not None]
        print(f"  {k}: " + " ".join(f"{h}m={v:+.3f}" for h, v in vals))
    print("  buy&hold per segment:", res["X3"]["NULL_BUY_AND_HOLD_per_segment_bp"])


if __name__ == "__main__":
    main()
