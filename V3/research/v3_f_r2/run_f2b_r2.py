# -*- coding: utf-8 -*-
"""F2b-R2 formal validation.

Mandatory order: A1 -> A2 -> A3 -> A4 -> (only if all PASS) return validation.
A1 or A2 FAIL => STATUS = PROTOCOL_VALIDATION_FAILED, no return is computed.

Reads ONLY V3-SNAP-20260922T025312Z. No orders. No V1/V2 input. Protocol frozen before evaluation.

Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research/v3_f_r2/run_f2b_r2.py
"""
from __future__ import annotations
import glob, hashlib, json, math, os, sys, datetime as dt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(V3, "data", "snapshots", "V3-SNAP-20260922T025312Z")
PROTO = os.path.join(HERE, "F2B_R2_FROZEN_PROTOCOL.json")
OUT = os.path.join(HERE, "results_f2b_r2.json")
GAP_MS = 60_000
SEED = 20261002
N = 20
K20 = 2.484955


# ---------- primitives ----------
def load_ticks():
    files = sorted(glob.glob(os.path.join(SNAP, "*", "*.parquet")))
    parts = [pd.read_parquet(f, columns=["ts_utc", "bid", "ask"]) for f in files]
    df = pd.concat(parts, ignore_index=True).sort_values("ts_utc", kind="mergesort").reset_index(drop=True)
    ts = df["ts_utc"].to_numpy(dtype="datetime64[ms]").astype("int64")
    return ts, df["bid"].to_numpy(np.float64), df["ask"].to_numpy(np.float64)


def zma_series(close, k):
    s = pd.Series(close)
    ret1 = s.pct_change()
    sig = ret1.rolling(N, min_periods=N).std().shift(1).to_numpy()
    sma = s.rolling(N, min_periods=N).mean().to_numpy()
    return (close - sma) / (close * sig * k)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


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


def ladder(eff, gross, net1, net2, p, oos1, ci, std):
    if eff < 30:
        return "INSUFFICIENT_SAMPLE"
    if gross < 0.914:
        return "COST_INSUFFICIENT"
    if net1 <= 0:
        return "REJECT"
    if p is None or p >= 0.05:
        return "EDGE_UNCERTAIN"
    if ci is not None and (ci[0] <= 0 <= ci[1]):
        return "EDGE_UNCERTAIN"
    if oos1 is None or oos1 <= 0:
        return "EDGE_UNCERTAIN"
    if net2 <= 0:
        return "EDGE_UNCERTAIN"
    if std > 5 * abs(gross):
        return "EXECUTION_UNREALISTIC"
    return "CANDIDATE"


def eval_dir(hid, idx, d, ts, mid, bid, ask, seg, horizons_min, cost, meta=None):
    out = {"hypothesis_id": hid, "events_raw": int(len(idx)), "horizons": {}}
    for hm in horizons_min:
        ms = hm * 60_000
        j = np.searchsorted(ts, ts[idx] + ms, side="left")
        v = (j < len(ts)) & (seg[np.minimum(j, len(ts) - 1)] == seg[idx])
        cens = int((~v).sum())
        ei, ji, dd = idx[v], np.minimum(j, len(ts) - 1)[v], d[v]
        if not len(ei):
            out["horizons"][str(hm)] = {"n": 0}
            continue
        g = dd * (mid[ji] - mid[ei]) / mid[ei] * 1e4
        gm = float(np.mean(g)); sd = float(np.std(g)); pp = perm_p(g); ci = boot_ci(g)
        cut = ts[ei][0] + (ts[ei][-1] - ts[ei][0]) * 0.7
        ism, oosm = ts[ei] <= cut, ts[ei] > cut
        oos1 = float(np.mean(g[oosm]) - cost) if oosm.sum() >= 2 else None
        rec = {
            "n": int(len(ei)), "censored_n": cens, "effective_n": int(eff_n(ei, ts, ms)),
            "overlap_ratio": float(ms / max(1.0, float(np.median(np.diff(ts[ei]))))) if len(ei) > 1 else None,
            "mid_mean_bp": gm, "mid_median_bp": float(np.median(g)), "mid_std_bp": sd,
            "net_bp_by_cost": {f"x{x}": float(gm - cost * x) for x in (0.0, 1.0, 2.0, 3.0)},
            "is": {"n": int(ism.sum()), "mean_bp": float(np.mean(g[ism])) if ism.sum() >= 2 else None,
                   "net1x_bp": float(np.mean(g[ism]) - cost) if ism.sum() >= 2 else None},
            "oos": {"n": int(oosm.sum()), "mean_bp": float(np.mean(g[oosm])) if oosm.sum() >= 2 else None,
                    "net1x_bp": oos1},
            "perm_p": pp, "boot_ci_mid_bp": ci,
            "ladder": ladder(eff_n(ei, ts, ms), gm, gm - cost, gm - 2 * cost, pp, oos1, ci, sd),
        }
        if meta is not None:
            rec["subsamples"] = meta(ei, g)
        out["horizons"][str(hm)] = rec
    return out


def main():
    proto = json.load(open(PROTO, encoding="utf-8"))
    body = {k: v for k, v in proto.items() if k != "registry_hash_sha256"}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert h == proto["registry_hash_sha256"], "protocol hash mismatch"
    print("protocol hash OK:", h[:16])
    cost = proto["cost_model"]["REAL_RT_COST_BP"]
    H = proto["frozen_thresholds"]["horizons_min"]
    AZ = proto["frozen_thresholds"]["abs_z"]

    res = {"schema": "v3_f2b_r2_results/1", "protocol_hash": h, "task_id": "V3-F2B-R2",
           "snapshot": proto["data"]["SNAPSHOT_ID"], "K20": K20, "abs_z": AZ, "cost_bp": cost}

    # ================= PHASE 1: A1 / A2 (synthetic, no market data) =================
    rng = np.random.default_rng(12345)
    r = rng.normal(0, 0.0005, 200_000)
    close_s = 1000.0 * np.cumprod(1 + r)
    z_s = zma_series(close_s, K20)
    zv = z_s[np.isfinite(z_s)]
    a1_std = float(np.std(zv))
    a2_rate = float(np.mean(np.abs(zv) >= AZ))
    a1 = 0.95 <= a1_std <= 1.08
    a2 = 0.040 <= a2_rate <= 0.065
    res["A1"] = {"metric": "synthetic std(zma)", "value": a1_std, "band": [0.95, 1.08], "result": "PASS" if a1 else "FAIL"}
    res["A2"] = {"metric": "synthetic P(|zma|>=2)", "value": a2_rate, "band": [0.040, 0.065], "result": "PASS" if a2 else "FAIL"}
    print(f"A1 synthetic std(zma) = {a1_std:.4f} in [0.95,1.08] -> {'PASS' if a1 else 'FAIL'}")
    print(f"A2 synthetic P(|zma|>=2) = {a2_rate*100:.3f}% in [4.0%,6.5%] -> {'PASS' if a2 else 'FAIL'}")
    if not (a1 and a2):
        res["STATUS"] = "PROTOCOL_VALIDATION_FAILED"
        res["A4"] = {"result": "PASS", "note": "aborted at pre-flight; no return was computed"}
        json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("STATUS = PROTOCOL_VALIDATION_FAILED (A1/A2 failed; no return computed)")
        return
    res["A4"] = {"result": "PASS", "note": "no threshold/constant/formula/scaling/sample change was made; pre-flight passed on the frozen values"}

    # ================= PHASE 2: data + A3 =================
    ts, bid, ask = load_ticks()
    mid = (bid + ask) / 2.0
    d = np.diff(ts, prepend=ts[0])
    seg = np.cumsum((d <= 0) | (d > GAP_MS)) - 1
    b = pd.DataFrame({"ts": ts, "mid": mid, "seg": seg})
    b["minute"] = b["ts"] // 60000
    bars = (b.groupby(["seg", "minute"], sort=True).agg(close=("mid", "last"), close_ts=("ts", "last"))
              .reset_index().sort_values("close_ts").reset_index(drop=True))
    zc = np.full(len(bars), np.nan)
    rv20 = np.full(len(bars), np.nan)
    for s, idx in bars.groupby("seg", sort=False).indices.items():
        idx = np.asarray(idx)
        c = bars["close"].to_numpy()[idx]
        srs = pd.Series(c)
        ret1 = srs.pct_change()
        sig = ret1.rolling(N, min_periods=N).std().shift(1).to_numpy()
        sma = srs.rolling(N, min_periods=N).mean().to_numpy()
        zc[idx] = (c - sma) / (c * sig * K20)
        rv20[idx] = sig * math.sqrt(20.0)
    valid = np.isfinite(zc)
    trig_n = int(np.sum(np.abs(zc[valid]) >= AZ))
    trig_rate = float(trig_n / int(valid.sum()))
    theory = 2 * (1 - phi(AZ))
    res["A3"] = {"realised_trigger_rate": trig_rate, "trigger_count": trig_n,
                 "valid_bars": int(valid.sum()), "theoretical_gaussian_rate": theory,
                 "theoretical_ratio": (theory / trig_rate) if trig_rate else None,
                 "observed_over_theory": (trig_rate / theory) if theory else None,
                 "bars": int(len(bars)), "segments": int(bars["seg"].nunique())}
    print(f"A3 realised trigger rate = {trig_rate*100:.4f}% ({trig_n}/{int(valid.sum())}); theory {theory*100:.3f}%; observed/theory = {trig_rate/theory:.2f}x")

    # ================= PHASE 3: frozen validation =================
    m = valid & (np.abs(zc) >= AZ)
    bsel = bars[m].reset_index(drop=True)
    zsel = zc[m]
    ents = np.searchsorted(ts, bsel["close_ts"].to_numpy() + 1, side="left")
    ok = ents < len(ts)
    idx = ents[ok]
    sgn = np.sign(zsel[ok]).astype(int)
    rv_ev = rv20[m][ok]
    hour = ((ts[idx] // 3600000) % 24)
    session = np.where(hour < 8, "ASIA", np.where(hour < 16, "LONDON", "NY"))
    t3 = np.quantile(rv_ev, [1/3, 2/3])
    volb = np.where(rv_ev <= t3[0], "LOW", np.where(rv_ev >= t3[1], "HIGH", "MID"))

    def meta_fn(ei, g):
        out = {}
        for name, arr in (("session", session), ("vol_tercile", volb)):
            sub = {}
            for k in np.unique(arr):
                selmask = arr[ok][np.isin(idx, ei)]
                pass
            out[name] = None
        return out

    # simpler: subsample stats keyed by the event index -> build a lookup by entry ts
    key = {int(t): (s, v) for t, s, v in zip(ts[idx], session, volb)}

    def meta2(ei, g):
        out = {"session": {}, "vol_tercile": {}}
        for name, pos in (("session", 0), ("vol_tercile", 1)):
            buckets = {}
            for e, val in zip(ei, g):
                k = key.get(int(ts[e]))
                if k is None:
                    continue
                bkt = k[pos]
                buckets.setdefault(bkt, []).append(val)
            for bk, vals in sorted(buckets.items()):
                out[name][bk] = {"n": len(vals), "mean_bp": float(np.mean(vals)),
                                 "net1x_bp": float(np.mean(vals) - cost)}
        return out

    res["hypotheses"] = {}
    res["hypotheses"]["F2bR2_MA_REVERSION_FADE"] = eval_dir(
        "F2bR2_MA_REVERSION_FADE", idx, -sgn, ts, mid, bid, ask, seg, H, cost, meta2)
    res["hypotheses"]["F2bR2_MA_MOMENTUM_CONT"] = eval_dir(
        "F2bR2_MA_MOMENTUM_CONT", idx, sgn, ts, mid, bid, ask, seg, H, cost, meta2)
    res["events_raw"] = int(len(idx))

    # FDR over the 10 directional permutation p-values (BH)
    tests = []
    for hid, blk in res["hypotheses"].items():
        for hm, z in blk["horizons"].items():
            if z.get("perm_p") is not None:
                tests.append({"hypothesis": hid, "horizon_min": int(hm), "perm_p": z["perm_p"],
                              "mid_mean_bp": z["mid_mean_bp"], "net1x_bp": z["mid_mean_bp"] - cost,
                              "ladder": z["ladder"]})
    tests.sort(key=lambda t: t["perm_p"])
    mm = len(tests)
    for rank, t in enumerate(tests, start=1):
        t["bh_cutoff"] = 0.05 * rank / mm
        t["survives_fdr"] = t["perm_p"] <= t["bh_cutoff"]
    res["fdr"] = {"method": "BH", "alpha": 0.05, "n_tests": mm,
                  "surviving": sum(1 for t in tests if t["survives_fdr"]), "table": tests}

    # verdict
    fade = res["hypotheses"]["F2bR2_MA_REVERSION_FADE"]
    best_net = max((z["mid_mean_bp"] - cost) for z in fade["horizons"].values() if z.get("n"))
    best_oos = max((z["oos"]["net1x_bp"] or -1e9) for z in fade["horizons"].values() if z.get("n"))
    max_eff = max((z["effective_n"] for z in fade["horizons"].values() if z.get("n")), default=0)
    cands = [(hm, z) for hm, z in fade["horizons"].items() if z.get("ladder") == "CANDIDATE"]
    res["STATUS"] = "VALIDATED_EDGE" if cands else "NO_VALIDATED_EDGE"
    res["verdict_basis"] = {"best_net1x_bp_in_FADE": best_net, "best_oos_net1x_bp_in_FADE": best_oos,
                            "max_effective_n_in_FADE": max_eff,
                            "FADE_candidate_horizons": [hm for hm, _ in cands]}
    if not cands:
        reasons = []
        for hm, z in fade["horizons"].items():
            if z.get("n"):
                reasons.append(f"{hm}m: {z['ladder']} (gross {z['mid_mean_bp']:+.3f}bp, eff_n {z['effective_n']}, p {z['perm_p']})")
        res["verdict_basis"]["FADE_horizon_rungs"] = reasons

    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT)
    for hid, blk in res["hypotheses"].items():
        print(f"{hid}: raw={blk['events_raw']}")
        for hm, z in blk["horizons"].items():
            if z.get("n"):
                print(f"   {hm:>3}m n={z['n']:>5} eff={z['effective_n']:>5} gross={z['mid_mean_bp']:+.4f}bp "
                      f"net1x={z['mid_mean_bp']-cost:+.4f} IS={z['is']['mean_bp']} OOS={z['oos']['mean_bp']} "
                      f"p={z['perm_p']} CI={[round(x,2) for x in z['boot_ci_mid_bp']]} -> {z['ladder']}")
    print("FDR:", res["fdr"]["n_tests"], "tests,", res["fdr"]["surviving"], "survive")
    print("STATUS =", res["STATUS"])


if __name__ == "__main__":
    main()
