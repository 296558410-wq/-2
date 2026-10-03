# -*- coding: utf-8 -*-
"""V3 F-R1: minute-scale (1m-60m) structure search on the frozen snapshot.

Reads ONLY V3-SNAP-20260922T025312Z. Protocol frozen before evaluation.
No orders. No V1/V2 input. No parameter sweep.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_f_r1/run_f_r1.py
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
OUT = os.path.join(HERE, "results_f_r1.json")
GAP_MS = 60_000
SEED = 20261001


def load_ticks():
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    bid = df["bid"].to_numpy(np.float64); ask = df["ask"].to_numpy(np.float64)
    return ts, bid, ask


def build_bars(ts, mid, seg):
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    g = (b.groupby(["seg", "minute"], sort=True)
          .agg(close=("mid", "last"), close_ts=("ts", "last"), n=("mid", "size"))
          .reset_index().sort_values("close_ts").reset_index(drop=True))
    return g


def add_features(bars):
    g = bars.groupby("seg", sort=False)
    bars["ret1"] = g["close"].pct_change()
    bars["sig20"] = g["ret1"].transform(lambda s: s.rolling(20, min_periods=20).std().shift(1))
    bars["ret5"] = g["close"].pct_change(5)
    bars["ret20"] = g["close"].pct_change(20)
    bars["sma20"] = g["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    bars["rv5"] = g["ret1"].transform(lambda s: s.rolling(5, min_periods=5).std())
    bars["rv1000"] = g["ret1"].transform(lambda s: s.rolling(1000, min_periods=100).std())
    bars["q33"] = g["rv5"].transform(lambda s: s.expanding(min_periods=100).quantile(0.33))
    bars["q50"] = g["rv5"].transform(lambda s: s.expanding(min_periods=100).quantile(0.50))
    bars["q67"] = g["rv5"].transform(lambda s: s.expanding(min_periods=100).quantile(0.67))
    bars["z5"] = bars["ret5"] / (bars["sig20"] * np.sqrt(5))
    bars["z20"] = bars["ret20"] / (bars["sig20"] * np.sqrt(20))
    bars["zma"] = (bars["close"] - bars["sma20"]) / (bars["close"] * bars["sig20"] * np.sqrt(20))
    return bars


# ---------------- stats ----------------
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


def eff_n(ei, ts, hm):
    if not len(ei):
        return 0
    t = ts[ei]; n = 1; last = t[0]
    for x in t[1:]:
        if x - last >= hm:
            n += 1; last = x
    return n


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


def eval_dir(hid, entry_idx, d, ts, mid, bid, ask, seg, horizons_min, cost, extra=None):
    out = {"hypothesis_id": hid, "events_raw": int(len(entry_idx)), "horizons": {}}
    for hm in horizons_min:
        ms = hm * 60_000
        j = np.searchsorted(ts, ts[entry_idx] + ms, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[entry_idx])
        cens = int((~v).sum())
        ei, ji, dd = entry_idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
        if not len(ei):
            out["horizons"][str(hm)] = {"n": 0}
            continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g)); pp = perm_p(g)
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        oos1 = float(np.mean(g[oosm]) - cost) if oosm.sum() >= 2 else None
        out["horizons"][str(hm)] = {
            "n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, ms)),
            "mid_mean_bp": gm, "mid_median_bp": float(np.median(g)), "mid_std_bp": sd,
            "net_bp_by_cost": {f"x{x}": float(gm - cost * x) for x in (0.0, 1.0, 2.0, 3.0)},
            "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None,
                   "net1x_bp": float(np.mean(g[ism]) - cost) if ism.sum() >= 2 else None},
            "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                    "net1x_bp": oos1},
            "perm_p": pp, "boot_ci_mid_bp": boot_ci(g),
            "ladder": ladder(eff_n(ei, ts, ms), gm, gm - cost, gm - 2 * cost, pp, oos1, sd),
        }
        if extra is not None:
            out["horizons"][str(hm)].update(extra(entry_idx, ei, ji, ms))
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert h == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", h[:16])

    ts, bid, ask = load_ticks()
    mid = (bid + ask) / 2.0
    d = np.diff(ts, prepend=ts[0])
    seg = np.cumsum((d <= 0) | (d > GAP_MS)) - 1
    print("ticks", len(ts), "segments", int(seg[-1]) + 1, "-> building 1m bars...")
    bars = add_features(build_bars(ts, mid, seg))
    print("bars", len(bars))

    cost = proto["cost_model"]["REAL_RT_COST_BP"]
    HM = proto["frozen_thresholds"]["horizons_min"]

    def entries_for(mask):
        b = bars[mask]
        return np.searchsorted(ts, b["close_ts"].to_numpy() + 1, side="left")

    res = {"schema": "v3_f_r1_results/1", "protocol_hash": h,
           "snapshot": proto["data"]["SNAPSHOT_ID"], "ticks": int(len(ts)),
           "bars_1m": int(len(bars)), "cost_bp": cost, "hypotheses": {}}

    b = bars
    # --- F1a ---
    m = (b["z5"].abs() >= 2.0).to_numpy()
    ei = entries_for(m); dr = np.sign(b.loc[m, "ret5"]).astype(int).to_numpy()
    ei, dr = ei[ei < len(ts)], dr[:len(ei[ei < len(ts)])]
    res["hypotheses"]["F1a_IMPULSE_CONT"] = eval_dir("F1a_IMPULSE_CONT", ei, dr, ts, mid, bid, ask, seg, HM, cost)
    res["hypotheses"]["F2a_ANOMALY_REVERT"] = eval_dir("F2a_ANOMALY_REVERT", ei, -dr, ts, mid, bid, ask, seg, HM, cost)

    # --- F1b ---
    m = (b["z20"].abs() >= 2.0).to_numpy()
    ei = entries_for(m); dr = np.sign(b.loc[m, "ret20"]).astype(int).to_numpy()
    ei, dr = ei[ei < len(ts)], dr[:len(ei[ei < len(ts)])]
    res["hypotheses"]["F1b_VOLADJ_MOMENTUM_CONT"] = eval_dir("F1b_VOLADJ_MOMENTUM_CONT", ei, dr, ts, mid, bid, ask, seg, HM, cost)

    # --- F2b ---
    m = (b["zma"].abs() >= 2.0).to_numpy()
    ei = entries_for(m); dr = -np.sign(b.loc[m, "zma"]).astype(int).to_numpy()
    ei, dr = ei[ei < len(ts)], dr[:len(ei[ei < len(ts)])]
    res["hypotheses"]["F2b_MA_REVERSION"] = eval_dir("F2b_MA_REVERSION", ei, dr, ts, mid, bid, ask, seg, HM, cost)

    # --- F1c descriptive autocorrelation ---
    ac = {"hypothesis_id": "F1c_RETURN_AUTOCORR", "lags": {}}
    r1 = b["ret1"].to_numpy()
    r1 = r1[np.isfinite(r1)]
    for lag in range(1, 11):
        x, y = r1[:-lag], r1[lag:]
        if len(x) > 100:
            c = float(np.corrcoef(x, y)[0, 1])
            rng = np.random.default_rng(SEED)
            bs = []
            n = len(x); bs_sz = max(1, n // 50)
            for _ in range(1000):
                idx = rng.integers(0, max(1, n - bs_sz), n // bs_sz)
                xx = np.concatenate([x[i:i + bs_sz] for i in idx])
                yy = np.concatenate([y[i:i + bs_sz] for i in idx])
                bs.append(float(np.corrcoef(xx, yy)[0, 1]))
            ac["lags"][str(lag)] = {"autocorr": c, "ci": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}
    res["hypotheses"]["F1c_RETURN_AUTOCORR"] = ac

    # --- F3a vol expansion (non-directional) ---
    low = (b["rv5"] <= b["q33"]).to_numpy(); low_prev = np.concatenate([[False], low[:-1]])
    onset_low = low & ~low_prev
    base_grid = np.arange(0, len(b), 20)
    f3a = {"hypothesis_id": "F3a_VOL_EXPANSION", "n_onsets": int(onset_low.sum()), "baseline_n": int(len(base_grid)), "horizons": {}}
    for hm in HM:
        ms = hm * 60_000
        def fmask(mask_idx):
            bts = b["close_ts"].to_numpy()
            ent = np.searchsorted(ts, bts[mask_idx] + 1, side="left")
            j = np.searchsorted(ts, ts[ent] + ms, side="left")
            v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[ent])
            a2 = ent[v]; b2 = np.minimum(j, len(ts) - 1)[v]
            return mask_idx[v], np.abs(mid[b2] - mid[a2]) / mid[a2] * 1e4
        bi, av = fmask(np.flatnonzero(onset_low))
        _, bv = fmask(base_grid)
        if len(av) < 10 or len(bv) < 10:
            f3a["horizons"][str(hm)] = {"status": "INSUFFICIENT_SAMPLE", "n": int(len(av))}
            continue
        hit, bhit = float(np.mean(av > cost)), float(np.mean(bv > cost))
        # probability the regime switches to HIGH within h bars
        sw = 0; tot = 0
        for i in np.flatnonzero(onset_low):
            w = b["rv5"].to_numpy()[i + 1:i + 1 + hm]
            q67 = b["q67"].to_numpy()[i + 1:i + 1 + hm]
            if len(w):
                tot += 1; sw += int(np.nanmax(w) >= np.nanmax(q67))
        f3a["horizons"][str(hm)] = {"n": int(len(av)), "mean_abs_move_bp": float(np.mean(av)),
                                    "baseline_mean_abs_move_bp": float(np.mean(bv)),
                                    "p_gt_cost": hit, "baseline_p_gt_cost": bhit, "lift": hit - bhit,
                                    "p_switch_to_high": (sw / tot if tot else None),
                                    "verdict": "MORE_VOLATILE" if hit > bhit else "NOT_MORE_VOLATILE"}
    res["hypotheses"]["F3a_VOL_EXPANSION"] = f3a

    # --- F3b vol decay (descriptive) ---
    high = (b["rv5"] >= b["q67"]).to_numpy(); high_prev = np.concatenate([[False], high[:-1]])
    onset_high = high & ~high_prev
    rv = b["rv5"].to_numpy(); q50 = b["q50"].to_numpy()
    half = []
    for i in np.flatnonzero(onset_high):
        for k in range(i + 1, min(len(b), i + 240)):
            if b["seg"].to_numpy()[k] != b["seg"].to_numpy()[i]:
                break
            if rv[k] <= q50[k]:
                half.append(k - i); break
    res["hypotheses"]["F3b_VOL_DECAY"] = {"hypothesis_id": "F3b_VOL_DECAY", "n_onsets": int(onset_high.sum()),
                                          "n_measured": len(half),
                                          "half_life_bars_median": float(np.median(half)) if half else None,
                                          "half_life_bars_p90": float(np.percentile(half, 90)) if half else None,
                                          "note": "bars until rv5 falls back to/below the trailing median after a HIGH onset"}

    # --- F3c regime transition direction ---
    ei = entries_for(onset_high); dr = np.sign(b.loc[onset_high, "ret5"]).astype(int).to_numpy()
    ei, dr = ei[ei < len(ts)], dr[:len(ei[ei < len(ts)])]
    res["hypotheses"]["F3c_REGIME_TRANSITION_DIR"] = eval_dir("F3c_REGIME_TRANSITION_DIR", ei, dr, ts, mid, bid, ask, seg, HM, cost)

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    for k, v in res["hypotheses"].items():
        if k == "F1c_RETURN_AUTOCORR":
            print(f"{k}: " + " ".join(f"L{l}={z['autocorr']:+.4f}" for l, z in list(v["lags"].items())[:5]))
        elif k == "F3a_VOL_EXPANSION":
            print(f"{k}: onsets={v['n_onsets']}")
            for hm, z in v["horizons"].items():
                print(f"   h={hm:>3}m {z.get('verdict')} lift={z.get('lift')} p_switch={z.get('p_switch_to_high')}")
        elif k == "F3b_VOL_DECAY":
            print(f"{k}: onsets={v['n_onsets']} median_half_life_bars={v['half_life_bars_median']}")
        elif "horizons" in v:
            print(f"{k}: raw={v['events_raw']}  " + " ".join(
                f"{hm}:{z.get('ladder','-')}/{round(z.get('mid_mean_bp',0),3)}" for hm, z in v["horizons"].items() if z.get("n")))
        else:
            print(k, json.dumps(v, ensure_ascii=False)[:150])


if __name__ == "__main__":
    main()
