"""L1 execution-edge discovery driver — V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001.

READ_ONLY / OFFLINE. Reads the IMMUTABLE SNAPSHOT ONLY (never live_fxtm).
No orders. No MT5 trading calls. Writes only under research/l1_execution_edge/.

Implements experiment_plan.json + feature_registry.json + label_definition.md +
cost_definition.md + statistical_plan.md + trading_rule.md.

Three phases (so the expensive statistics run only where they are needed):
  PHASE 1  screen   : every family x horizon x model, TRAIN fit, VAL metrics + cheap
                      non-overlapping t-test p-value (this is the FDR family)
  PHASE 2  select   : best config per horizon on VAL only (never TEST)
  PHASE 3  deep     : for the selected configs -> TEST once, block bootstrap CI,
                      tail shares, cost stress, regime analysis
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as st
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.tree import DecisionTreeRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, V3)
from microstructure import timestamp_unit_guard as TG   # noqa: E402
from execution import cost_model_v2 as CM2               # noqa: E402

SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAPSHOT_ID)
MANIFEST_SHA = "a036a808d5d924a7a99c5941919971ff00ce9e28c804e8e91860b6ffd7fa61b5"
COST_BP = CM2.REAL_RT_COST_BP
HORIZONS = [5000, 10000, 30000, 60000, 300000]
REF_HORIZONS = [1000, 2000]
DAY_MS = 86_400_000
MIN_EFF_N = 500
MIN_TRADES = 100
GRID_MS = 1000
BOOT = 2000
COST_TIERS = [0.40, 0.50, 0.60, 0.80]


def daynum(s):
    return int(pd.Timestamp(s).value // (DAY_MS * 1_000_000))


FOLDS = {"train": (daynum("2026-08-04"), daynum("2026-08-22")),
         "val": (daynum("2026-08-24"), daynum("2026-09-05")),
         "test": (daynum("2026-09-07"), daynum("2026-09-22"))}


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def cumsum0(x):
    return np.concatenate([[0.0], np.cumsum(x)])


def roll_mean(x, w):
    c = cumsum0(np.nan_to_num(x))
    out = np.full(len(x), np.nan)
    out[w - 1:] = (c[w:] - c[:-w]) / w
    return out


def roll_std(x, w):
    x = np.nan_to_num(x)
    m = roll_mean(x, w)
    m2 = roll_mean(x * x, w)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def load_snapshot():
    paths = sorted(glob.glob(os.path.join(SNAP, "staging_fxtm", "ticks_*.parquet"))) + \
            sorted(glob.glob(os.path.join(SNAP, "live_fxtm", "ticks_*.parquet")))
    fr = [pd.read_parquet(p, columns=["bid", "ask", "ts_utc"]).sort_values("ts_utc") for p in paths]
    d = pd.concat(fr, ignore_index=True)
    ts = (TG.read_timestamp(d["ts_utc"], "ms")["ts_ns"] // 1_000_000).astype(np.int64)
    return ts, d["bid"].to_numpy(float), d["ask"].to_numpy(float), len(paths)


def make_grid(ts):
    g = np.arange(ts[0], ts[-1] + 1, GRID_MS, dtype=np.int64)
    gi = np.searchsorted(ts, g, side="right") - 1
    gi = gi[gi >= 0]
    return gi[(ts[gi] - (ts[gi] // GRID_MS * GRID_MS)) <= 5000]


def folds_of(ts, gi):
    day = ts[gi] // DAY_MS
    fo = np.full(len(gi), "none", dtype=object)
    for k, (a, b) in FOLDS.items():
        fo[(day >= a) & (day < b)] = k
    return fo


def build_features(ts, bid, ask, gi):
    mid = (bid + ask) / 2.0
    spread = ask - bid
    bp = 1e4
    n = len(mid)
    r1 = np.full(n, np.nan)
    r1[1:] = (mid[1:] / mid[:-1] - 1.0) * bp
    f = {}
    j1 = np.searchsorted(ts, ts[gi] - 1000, side="right") - 1
    j5 = np.searchsorted(ts, ts[gi] - 5000, side="right") - 1
    f["mid_return_1s"] = np.where(j1 >= 0, (mid[gi] / mid[np.clip(j1, 0, n - 1)] - 1.0) * bp, np.nan)
    f["displacement_5s"] = np.where(j5 >= 0, (mid[gi] / mid[np.clip(j5, 0, n - 1)] - 1.0) * bp, np.nan)

    def lag(k):
        out = np.full(len(gi), np.nan)
        ok = gi >= k
        out[ok] = (mid[gi[ok]] / mid[gi[ok] - k] - 1.0) * bp
        return out
    f["mom_3t"] = lag(3)
    f["mom_10t"] = lag(10)
    f["rev_5t"] = -lag(5)
    dt5 = np.searchsorted(ts, ts - 5000, side="left")
    disp_full = (mid / mid[np.clip(dt5, 0, n - 1)] - 1.0) * bp
    dm, ds = roll_mean(disp_full, 50), roll_std(disp_full, 50)
    dsi = ds[gi]
    f["overshoot_z"] = np.where(dsi > 0, (disp_full[gi] - dm[gi]) / dsi, np.nan)

    f["spread_bp"] = spread[gi] / mid[gi] * bp

    q = np.round(spread / 0.0001).astype(np.int64)
    uniq = np.unique(q)
    left = np.maximum(gi - 200 + 1, 0)
    total = (gi - left + 1).astype(float)
    running = np.zeros(len(gi), float)
    qg = q[gi]
    cums = {v: np.concatenate([[0], np.cumsum(q == v)]) for v in uniq}
    for v in uniq:
        m = qg >= v
        if m.any():
            c = cums[v]
            running[m] += (c[gi[m] + 1] - c[left[m]])
    f["spread_pctile_200t"] = running / total

    f["rv_50t"] = roll_std(r1, 50)[gi]
    f["absret_10t"] = roll_mean(np.abs(r1), 10)[gi]
    l1 = np.searchsorted(ts, ts[gi] - 1000, side="left")
    f["quote_update_rate_1s"] = (gi - l1).astype(float)
    dtp = np.full(len(gi), np.nan)
    okp = gi >= 1
    dtp[okp] = (ts[gi[okp]] - ts[gi[okp] - 1]) / 1000.0
    f["time_since_last_quote_s"] = dtp
    d = np.zeros(n)
    d[1:] = np.sign(mid[1:] - mid[:-1])
    c = cumsum0(d)
    for w in (20, 50):
        out = np.full(n, np.nan)
        out[w - 1:] = (c[w:] - c[:-w]) / w
        f[f"tick_rule_proxy_{w}t"] = out[gi]
    return f


def segment_ids(ts, g_max_ms):
    """Maximal runs where every consecutive gap <= g_max_ms (frozen censoring rule)."""
    d = np.diff(ts)
    return np.concatenate([[0], np.cumsum(d > g_max_ms)])


def labels_for(ts, mid, bid, ask, gi, h, seg=None):
    j = np.searchsorted(ts, ts[gi] + h, side="left")
    elig = j < len(ts)
    jj = np.clip(j, 0, len(ts) - 1)
    if seg is not None:
        elig = elig & (seg[gi] == seg[jj])          # forward tick must be in the SAME segment
    fm = mid[jj]
    return {"long": np.where(elig, (fm - ask[gi]) / ask[gi] * 1e4, np.nan),
            "short": np.where(elig, (bid[gi] - fm) / bid[gi] * 1e4, np.nan),
            "elig": elig, "fwd_day": ts[jj] // DAY_MS,
            "cost_bp": CM2.REAL_RT_COST_USD / mid[gi] * 1e4}


def nonoverlap(v, rho):
    return np.asarray(v, float)[::max(1, int(round(rho)))]


def block_boot(v, rho, n_boot=BOOT, seed=20260922, chunk=25):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size < 50:
        return None
    rng = np.random.default_rng(seed)
    blk = min(max(50, int(10 * rho)), max(1, v.size // 2))
    nb = int(np.ceil(v.size / blk))
    offs = np.arange(blk)
    means = []
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        starts = rng.integers(0, max(1, v.size - blk + 1), size=(k, nb))
        idx = (starts[:, :, None] + offs[None, None, :]).reshape(k, -1)[:, :v.size]
        means.append(v[idx].mean(axis=1))
        done += k
    m = np.concatenate(means)
    return {"mean": float(v.mean()), "ci_low": float(np.percentile(m, 2.5)),
            "ci_high": float(np.percentile(m, 97.5)), "n_boot": int(m.size),
            "block": int(blk), "n_eff": int(v.size)}


def tail_shares(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size < 20:
        return {}
    tot = float(v.sum())
    pos = np.sort(v)[::-1]
    out = {}
    for p in (1, 5, 10):
        k = max(1, int(v.size * p / 100))
        out[f"top{p}pct_share"] = float(pos[:k].sum() / tot) if tot != 0 else None
    return out


def ttest(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size < 10:
        return {"n": int(v.size), "t": None, "p": None}
    t, p = st.ttest_1samp(v, 0.0)
    return {"n": int(v.size), "t": float(t), "p": float(p)}


def main():
    ts, bid, ask, nfiles = load_snapshot()
    mid = (bid + ask) / 2.0
    gi = make_grid(ts)
    fo = folds_of(ts, gi)
    med_dt = float(np.median(np.diff(ts)))
    feats = build_features(ts, bid, ask, gi)
    reg = json.load(open(os.path.join(HERE, "feature_registry.json"), encoding="utf-8"))
    FAM = {x["family"]: [y["name"] for y in x["features"]] for x in reg["families"]}
    MODELS = ["naive_momentum", "ridge", "logistic", "tree_depth3"]

    res = {"schema": "v3_l1_edge_results/1", "generated_utc": now_utc(),
           "DATA_SNAPSHOT_ID": SNAPSHOT_ID, "DATA_MANIFEST_SHA256": MANIFEST_SHA,
           "data": {"files": nfiles, "ticks": int(len(ts)), "grid_points": int(len(gi)),
                     "median_inter_tick_ms": med_dt, "cost_bp": COST_BP},
           "fold_counts": {k: int((fo == k).sum()) for k in ["train", "val", "test"]},
           "screens": [], "selected": {}, "reference": {}, "cost_stress": {}, "regimes": {}}

    cache = {}   # (fam,h) -> (X, mu, sd, tr, va, te, good, labs)
    for h in HORIZONS + REF_HORIZONS:
        g_max = max(60_000, 10 * h) if h <= 300_000 else 3_600_000
        seg = segment_ids(ts, g_max)
        lab = labels_for(ts, mid, bid, ask, gi, h, seg=seg)
        rho = max(1.0, h / med_dt)
        purge = ((fo == "train") & (lab["fwd_day"] >= FOLDS["val"][0])) | \
                ((fo == "val") & (lab["fwd_day"] >= FOLDS["test"][0]))
        base = lab["elig"] & (~purge) & (fo != "none")
        for fam, cols in FAM.items():
            X = np.column_stack([feats[c] for c in cols])
            good = base & np.isfinite(X).all(1) & np.isfinite(lab["long"])
            tr, va, te = good & (fo == "train"), good & (fo == "val"), good & (fo == "test")
            if tr.sum() < 1000 or va.sum() < 100:
                continue
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-12
            cache[(fam, h)] = (X, mu, sd, tr, va, te, good, lab, rho)

            def predict(model, X, mu, sd, tr, lab, msk):
                Z = (X - mu) / sd
                if model == "naive_momentum":
                    return feats["mom_3t"][msk]
                if model == "ridge":
                    return Ridge(alpha=1.0).fit(Z[tr], lab["long"][tr]).predict(Z[msk])
                if model == "logistic":
                    yb = (lab["long"][tr] > 0).astype(int)
                    if len(np.unique(yb)) < 2:
                        return np.zeros(int(msk.sum()))
                    m = LogisticRegression(max_iter=200).fit(Z[tr], yb)
                    return (2 * m.predict_proba(Z[msk])[:, 1] - 1) * (np.std(lab["long"][tr]) or 1.0)
                return DecisionTreeRegressor(max_depth=3, random_state=20260922) \
                    .fit(Z[tr], lab["long"][tr]).predict(Z[msk])

            for model in MODELS:
                row = {"family": fam, "horizon_ms": h, "model": model, "features": cols,
                        "rho": rho, "reference_only": h in REF_HORIZONS}
                for tag, msk in (("val", va), ("test", te)):
                    pred = predict(model, X, mu, sd, tr, lab, msk)
                    cb = lab["cost_bp"][msk]
                    pos = np.where(pred > cb, 1.0, np.where(pred < -cb, -1.0, 0.0))
                    nz = pos != 0
                    net = np.where(pos > 0, lab["long"][msk] - cb, lab["short"][msk] - cb)[nz]
                    grs = np.where(pos > 0, lab["long"][msk], lab["short"][msk])[nz]
                    row[tag] = {"n_trades": int(net.size),
                                 "effective_n": int(net.size // max(1.0, rho)),
                                 "mean_bp": float(net.mean()) if net.size else None,
                                 "median_bp": float(np.median(net)) if net.size else None,
                                 "gross_mean_bp": float(grs.mean()) if grs.size else None,
                                 "win_rate": float((net > 0).mean()) if net.size else None}
                    if tag == "val":
                        tt = ttest(nonoverlap(net, rho))
                        row["val_p"] = tt["p"]
                        row["val_t"] = tt["t"]
                        row["val_tail"] = tail_shares(net)
                res["screens"].append(row)

    # ---------------- PHASE 2: select on VAL ----------------
    def best_of(h, pool):
        c = [r for r in pool if r["horizon_ms"] == h and r["val"].get("n_trades", 0) >= MIN_TRADES]
        return max(c, key=lambda r: (r["val"]["mean_bp"] if r["val"]["mean_bp"] is not None else -9)) if c else None

    sel_rows = {}
    for h in HORIZONS:
        b = best_of(h, res["screens"])
        sel_rows[h] = b
        res["selected"][str(h)] = ({"status": "NO_VALID_CONFIG"} if b is None else
                                    {"family": b["family"], "model": b["model"], "val": b["val"],
                                     "test": b["test"], "val_p": b.get("val_p")})
    for h in REF_HORIZONS:
        b = best_of(h, res["screens"])
        if b:
            res["reference"][str(h)] = {"family": b["family"], "model": b["model"],
                                         "val": b["val"], "test": b["test"]}

    # ---------------- PHASE 3: deep evaluation on selected ----------------
    for h in HORIZONS:
        b = sel_rows[h]
        if b is None:
            continue
        fam, model = b["family"], b["model"]
        X, mu, sd, tr, va, te, good, lab, rho = cache[(fam, h)]
        Z = (X - mu) / sd

        def pred_for(msk):
            if model == "naive_momentum":
                return feats["mom_3t"][msk]
            if model == "ridge":
                return Ridge(alpha=1.0).fit(Z[tr], lab["long"][tr]).predict(Z[msk])
            if model == "logistic":
                yb = (lab["long"][tr] > 0).astype(int)
                if len(np.unique(yb)) < 2:
                    return np.zeros(int(msk.sum()))
                m = LogisticRegression(max_iter=200).fit(Z[tr], yb)
                return (2 * m.predict_proba(Z[msk])[:, 1] - 1) * (np.std(lab["long"][tr]) or 1.0)
            return DecisionTreeRegressor(max_depth=3, random_state=20260922) \
                .fit(Z[tr], lab["long"][tr]).predict(Z[msk])

        for tag, msk in (("val", va), ("test", te)):
            pred = pred_for(msk)
            cb = lab["cost_bp"][msk]
            pos = np.where(pred > cb, 1.0, np.where(pred < -cb, -1.0, 0.0))
            nz = pos != 0
            net = np.where(pos > 0, lab["long"][msk] - cb, lab["short"][msk] - cb)[nz]
            nol = nonoverlap(net, rho)
            rec = {"n_trades": int(net.size), "effective_n": int(net.size // max(1.0, rho)),
                    "mean_bp": float(net.mean()) if net.size else None,
                    "median_bp": float(np.median(net)) if net.size else None,
                    "win_rate": float((net > 0).mean()) if net.size else None,
                    "tail": tail_shares(net), "boot": block_boot(nol, rho), "ttest": ttest(nol)}
            res["selected"][str(h)][tag + "_deep"] = rec

        # cost stress on TEST with the SAME positions (robustness only)
        pred = pred_for(te)
        cb_ref = lab["cost_bp"][te]
        tiers = {}
        for t in COST_TIERS:
            cb = CM2.REAL_RT_COST_USD * (t / 0.40) / mid[gi[te]] * 1e4
            pos = np.where(pred > cb, 1.0, np.where(pred < -cb, -1.0, 0.0))
            nz = pos != 0
            net = np.where(pos > 0, lab["long"][te] - cb, lab["short"][te] - cb)[nz]
            tiers[f"{t:.2f}"] = {"usd_per_rt": t, "cost_bp": float(np.mean(cb)),
                                  "n_trades": int(net.size),
                                  "mean_bp": float(net.mean()) if net.size else None,
                                  "median_bp": float(np.median(net)) if net.size else None,
                                  "win_rate": float((net > 0).mean()) if net.size else None}
        res["cost_stress"][str(h)] = tiers

        # regime analysis on TEST (3 dims x 3 states, N >= 500)
        regs = {}
        for dim, arr in (("spread_regime", feats["spread_bp"]), ("volatility_regime", feats["rv_50t"]),
                          ("quote_arrival_regime", feats["quote_update_rate_1s"])):
            v = arr[te]
            if not np.isfinite(v).any():
                regs[dim] = {"status": "DATA_GAP"}
                continue
            qs = np.nanquantile(v, [1 / 3, 2 / 3])
            lab3 = np.where(v <= qs[0], "low", np.where(v <= qs[1], "mid", "high"))
            cb = cb_ref
            pos = np.where(pred > cb, 1.0, np.where(pred < -cb, -1.0, 0.0))
            nz = pos != 0
            out = {}
            for s in ("low", "mid", "high"):
                m = nz & (lab3 == s)
                if m.sum() < 500:
                    out[s] = {"n": int(m.sum()), "status": "INSUFFICIENT_SAMPLE"}
                    continue
                net = np.where(pos[m] > 0, lab["long"][te][m] - cb[m], lab["short"][te][m] - cb[m])
                out[s] = {"n": int(net.size), "status": "OK",
                           "mean_bp": float(net.mean()), "median_bp": float(np.median(net)),
                           "win_rate": float((net > 0).mean())}
            regs[dim] = out
        res["regimes"][str(h)] = regs

    # ---------------- FDR over the screen family ----------------
    tests = res["screens"]
    valid = [r for r in tests if r.get("val_p") is not None and np.isfinite(r["val_p"])
             and r["val"].get("effective_n", 0) >= MIN_EFF_N and r["val"].get("n_trades", 0) >= MIN_TRADES]
    insuff = [r for r in tests if r not in valid]
    sig = 0
    if valid:
        from statsmodels.stats.multitest import multipletests
        rej, padj, _, _ = multipletests([r["val_p"] for r in valid], alpha=0.05, method="fdr_bh")
        for r, ok, pa in zip(valid, rej, padj):
            r["q_value"] = float(pa)
            r["reject_fdr"] = bool(ok)
        sig = int(sum(1 for r in valid if r["reject_fdr"]))
    res["fdr"] = {"method": "Benjamini-Hochberg", "q": 0.05, "family": "all family x horizon x model VAL screen tests",
                   "total_tests": len(tests), "valid_tests": len(valid),
                   "insufficient_tests": len(insuff), "significant_tests": sig,
                   "insufficient_definition": f"effective_n < {MIN_EFF_N} or n_trades < {MIN_TRADES}"}

    with open(os.path.join(HERE, "experiment_results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps({"folds": res["fold_counts"], "grid": int(len(gi)), "fdr": res["fdr"],
                       "selected": {k: {"f": v.get("family"), "m": v.get("model"),
                                         "test_mean_bp": (v.get("test") or {}).get("mean_bp")}
                                    for k, v in res["selected"].items()}}, indent=1, default=str))


if __name__ == "__main__":
    main()
