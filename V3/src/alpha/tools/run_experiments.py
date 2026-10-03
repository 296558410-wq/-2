"""V3-HFT-ALPHA-DISCOVERY-001 experiment driver.

Implements the frozen plan in alpha/freeze/V3_ALPHA_RESEARCH_FREEZE_001.md
(sha256 557bcc3c96338c1261f8a5b70371a6a679ff61ec433fbd24234aabf782b8a4d0).

Read-only on market data. No order placement of any kind (order_send calls = 0).
"""
from __future__ import annotations
import os, sys, json, glob, math, time
import numpy as np
import pandas as pd
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ALPHA, "features"))
import feature_builder as fb  # noqa: E402

ROOT = r"C:\AIQuant"
SEED = 20260921
RT_ANCHOR_USD = 0.40
RT_TIERS = [0.40, 0.50, 0.60, 0.80, 1.00]
LATENCY_MS = [0, 50, 100, 250, 500, 1000]
HORIZONS_ALL = [50, 200, 1000, 5000, 30000, 300000, 3600000, 86400000]
HORIZONS_SEARCH = [1000, 30000, 300000]
GRID_MS = 1000
COMMISSION_RT_USD = 0.22
MIN_NET_EDGE_USD = 0.10
MIN_VAL_TRADES = 200
ALPHA_LEVEL = 0.05
FDR_Q = 0.05
ITERATION_CAP = 30
DAY_NS = 86_400_000_000_000


def daynum(s: str) -> int:
    return int(pd.Timestamp(s).value) // DAY_NS


FOLDS = {
    "train": (daynum("2026-08-04"), daynum("2026-08-22")),
    "val": (daynum("2026-08-24"), daynum("2026-09-05")),
    "test": (daynum("2026-09-07"), daynum("2026-09-22")),
}


def log(*a):
    print(*a, flush=True)


def now_utc():
    return pd.Timestamp.now("UTC").isoformat()


# ---------------------------------------------------------------- data load
def load_fxtm():
    paths = sorted(glob.glob(os.path.join(ROOT, r"data\staging_fxtm\ticks_*.parquet"))) + \
            sorted(glob.glob(os.path.join(ROOT, r"data\live_fxtm\ticks_*.parquet")))
    ts_l, b_l, a_l = [], [], []
    for p in paths:
        df = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
        ts_l.append(df["ts_utc"].to_numpy(dtype="datetime64[ns]").astype(np.int64))
        b_l.append(df["bid"].to_numpy(np.float64))
        a_l.append(df["ask"].to_numpy(np.float64))
    ts = np.concatenate(ts_l); bid = np.concatenate(b_l); ask = np.concatenate(a_l)
    o = np.argsort(ts, kind="stable")
    ts, bid, ask = ts[o], bid[o], ask[o]
    keep = np.concatenate([[True], np.diff(ts) != 0])
    dropped = int((~keep).sum())
    ts, bid, ask = ts[keep], bid[keep], ask[keep]
    log(f"[load] files={len(paths)} ticks={len(ts)} dropped_exact_dup_ts={dropped}")
    return ts, bid, ask


# ---------------------------------------------------------------- stats utils
def block_bootstrap_mean(series, block, n_boot=2000, rng=None):
    n = len(series)
    if n == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n_blocks": 0, "degenerate": True}
    if block >= n:
        block = max(1, n // 20)
    nb = int(np.ceil(n / block))
    pad = nb * block - n
    s = np.concatenate([series, np.zeros(pad)]) if pad else series
    bsum = s.reshape(nb, block).sum(axis=1)
    bcnt = np.full(nb, block, np.float64)
    if pad:
        bcnt[-1] = block - pad
    rng = rng or np.random.default_rng(SEED)
    pick = rng.integers(0, nb, size=(n_boot, nb))
    means = bsum[pick].sum(axis=1) / bcnt[pick].sum(axis=1)
    return {"mean": float(series.mean()), "ci_low": float(np.percentile(means, 2.5)),
            "ci_high": float(np.percentile(means, 97.5)), "n_blocks": nb,
            "block_samples": int(block), "degenerate": False}


def spearman(a, b):
    if len(a) < 10:
        return None
    ra = pd.Series(a).rank().to_numpy(); rb = pd.Series(b).rank().to_numpy()
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def block_len_for(h_ms):
    return max(50, 10 * max(1, int(round(h_ms / GRID_MS))))


def _max_dd(cum):
    return 0.0 if len(cum) == 0 else float(np.max(np.maximum.accumulate(cum) - cum))


def core_metrics(pos, y_gross_bp, c_bp, mid_t, pred=None):
    tr = pos != 0
    n = int(tr.sum())
    out = {"n_samples": int(len(pos)), "n_trades": n,
           "trade_rate": float(n / len(pos)) if len(pos) else 0.0}
    if n == 0:
        out.update({"gross_edge_bp": None, "gross_edge_usd": None, "cost_bp_mean": None,
                    "net_edge_bp": None, "net_edge_usd": None, "hit_rate": None,
                    "sharpe_trade": None, "max_dd_usd": None, "turnover": 0.0,
                    "ic": None, "rank_ic": None})
        return out
    gp = pos[tr] * y_gross_bp[tr]; cost = c_bp[tr]
    net_bp = gp - cost; net_usd = net_bp / 1e4 * mid_t[tr]
    out.update({
        "gross_edge_bp": float(gp.mean()), "gross_edge_usd": float((gp / 1e4 * mid_t[tr]).mean()),
        "cost_bp_mean": float(cost.mean()),
        "net_edge_bp": float(net_bp.mean()), "net_edge_usd": float(net_usd.mean()),
        "hit_rate": float(np.mean(gp > 0)),
        "sharpe_trade": float(net_bp.mean() / net_bp.std() * math.sqrt(n)) if net_bp.std() > 0 else None,
        "max_dd_usd": _max_dd(np.cumsum(net_usd)), "turnover": float(n / len(pos)),
    })
    if pred is not None:
        m2 = np.isfinite(pred) & np.isfinite(y_gross_bp)
        if m2.sum() > 10 and np.std(pred[m2]) > 0:
            out["ic"] = float(np.corrcoef(pred[m2], y_gross_bp[m2])[0, 1])
            out["rank_ic"] = spearman(pred[m2], y_gross_bp[m2])
        else:
            out["ic"] = None; out["rank_ic"] = None
    return out


def ttest_nonoverlap(pos, y_gross_bp, c_bp, rho):
    tr = pos != 0
    if tr.sum() < 10:
        return {"net_t": None, "net_p": None, "gross_t": None, "gross_p": None, "n_indep": 0}
    net = pos[tr] * y_gross_bp[tr] - c_bp[tr]
    gross = pos[tr] * y_gross_bp[tr]
    ind = net[::rho]; gnd = gross[::rho]
    nt = st.ttest_1samp(ind, 0.0) if len(ind) > 5 else (float("nan"), float("nan"))
    gt = st.ttest_1samp(gnd, 0.0) if len(gnd) > 5 else (float("nan"), float("nan"))
    return {"net_t": float(nt[0]), "net_p": float(nt[1]),
            "gross_t": float(gt[0]), "gross_p": float(gt[1]), "n_indep": int(len(ind))}


# ---------------------------------------------------------------- models
def _model_factories():
    from sklearn.linear_model import Ridge, LogisticRegression
    from sklearn.ensemble import HistGradientBoostingRegressor
    return {
        "Ridge": lambda: Ridge(alpha=1.0),
        "Logistic": lambda: LogisticRegression(max_iter=200, C=1.0),
        "GBT": lambda: HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05,
                                                     max_depth=3, l2_regularization=1.0,
                                                     random_state=SEED),
    }


def fit_predict(name, Xtr, ytr, Xte):
    if name == "MLP":
        return _mlp(Xtr, ytr, Xte)
    m = _model_factories()[name]()
    if name == "Logistic":
        yb = (ytr > 0).astype(int)
        if yb.min() == yb.max():
            return np.zeros(len(Xte))
        m.fit(Xtr, yb)
        p = m.predict_proba(Xte)[:, 1]
        return (2 * p - 1) * (float(np.std(ytr)) or 1.0)
    m.fit(Xtr, ytr)
    return m.predict(Xte)


def _mlp(Xtr, ytr, Xte, epochs=60, hidden=32, lr=1e-3):
    import torch
    torch.manual_seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    ym, ys = ytr.mean(), ytr.std() + 1e-12
    Xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32, device=dev)
    yt = torch.tensor((ytr - ym) / ys, dtype=torch.float32, device=dev).unsqueeze(1)
    Xe = torch.tensor((Xte - mu) / sd, dtype=torch.float32, device=dev)
    net = torch.nn.Sequential(torch.nn.Linear(Xtr.shape[1], hidden), torch.nn.ReLU(),
                              torch.nn.Linear(hidden, hidden), torch.nn.ReLU(),
                              torch.nn.Linear(hidden, 1)).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    lossf = torch.nn.MSELoss()
    n = len(Xt); bs = 8192
    for _ in range(epochs):
        perm = torch.randperm(n, device=dev)
        for i in range(0, n, bs):
            j = perm[i:i + bs]
            opt.zero_grad(); lossf(net(Xt[j]), yt[j]).backward(); opt.step()
    with torch.no_grad():
        return net(Xe).squeeze(1).cpu().numpy() * ys + ym


def _positions(pred_bp, c_bp):
    pos = np.zeros(len(pred_bp), np.float64)
    pos[pred_bp > c_bp] = 1.0
    pos[pred_bp < -c_bp] = -1.0
    return pos


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    for d in ["data", os.path.join("data", "cache"), "freeze", "features", "labels",
              "models", "backtest", "statistics", "oos", "reports", "tools"]:
        os.makedirs(os.path.join(ALPHA, d), exist_ok=True)
    ts, bid, ask = load_fxtm()
    mid = (bid + ask) / 2.0
    n_ticks = len(ts)
    log("[feat] computing causal tick features")
    feats = fb.compute_tick_features(ts, bid, ask)
    med_dt_ms = float(np.median(np.diff(ts) / 1e6))
    log(f"[feat] median inter-tick interval = {med_dt_ms:.1f} ms ({1000/med_dt_ms:.2f} Hz)")

    grid = np.arange(ts[0], ts[-1] + 1, GRID_MS * 1_000_000, dtype=np.int64)
    idx_all = np.searchsorted(ts, grid, side="right") - 1
    ok = idx_all >= 0
    grid, idx_all = grid[ok], idx_all[ok]
    idx_s = idx_all[(grid - ts[idx_all]) / 1e6 <= 5000.0]
    log(f"[grid] grid_points={len(idx_all)} used(fresh<=5s)={len(idx_s)} "
        f"({100*len(idx_s)/len(idx_all):.1f}%)")
    day_s = ts[idx_s] // DAY_NS
    fold = np.full(len(idx_s), "none", dtype=object)
    for f, (a, b) in FOLDS.items():
        fold[(day_s >= a) & (day_s < b)] = f
    log("[grid] fold counts:", {f: int((fold == f).sum()) for f in ["train", "val", "test"]})

    def g_max_ns(h):
        return (max(60_000, 10 * h) if h <= 300_000 else 3_600_000) * 1_000_000

    # ---- diagnostics on all 8 horizons -----------------------------------
    diag = {"schema": "v3_alpha_effective_sample/1", "generated_utc": now_utc(),
            "median_inter_tick_ms": med_dt_ms, "tick_rate_hz": 1000 / med_dt_ms,
            "grid_ms": GRID_MS, "folds": {k: list(v) for k, v in FOLDS.items()},
            "n_ticks": n_ticks, "horizons": {}}
    cache = {}          # h -> (keep_idx, y, fold)
    for h in HORIZONS_ALL:
        lab = fb.forward_labels(ts, mid, idx_s, h, g_max_ns(h))
        fwd_day = ts[lab["fwd_idx"]] // DAY_NS
        purge = ((fold == "train") & (fwd_day >= FOLDS["val"][0])) | \
                ((fold == "val") & (fwd_day >= FOLDS["test"][0]))
        keep = lab["defined"] & lab["clean"] & (~purge) & (fold != "none")
        rho = max(1.0, h / med_dt_ms)
        n_keep = int(keep.sum())
        diag["horizons"][str(h)] = {
            "horizon_ms": h,
            "label_defined_frac": float(lab["defined"].mean()),
            "clean_frac": float((lab["defined"] & lab["clean"]).mean()),
            "n_defined": int(lab["defined"].sum()),
            "n_clean": int((lab["defined"] & lab["clean"]).sum()), "n_used": n_keep,
            "median_slack": float(np.median(lab["slack"][lab["defined"]])) if lab["defined"].any() else None,
            "overlap_ratio_rho": rho, "effective_n": int(n_keep // max(rho, 1.0)),
            "feed_resolvable": bool(med_dt_ms <= 2 * h), "g_max_ms": g_max_ns(h) // 1_000_000,
            "verdict": ("MEASURABLE" if (med_dt_ms <= 2 * h and n_keep // max(rho, 1.0) >= 30 and
                                         ((lab["defined"] & lab["clean"]).mean() >= 0.5))
                        else "DATA_INSUFFICIENT"),
        }
        if h in HORIZONS_SEARCH:
            cache[h] = (idx_s[keep], lab["y_gross_bp"][keep], fold[keep])
        okm = lab["defined"] & lab["clean"] & (fold != "none")
        y = lab["y_gross_bp"][okm]
        best = None
        for fam in ["B0", "B2", "B3", "B4", "B5", "B6"]:
            X, names = fb.family_matrix(feats, fam)
            Xi = X[idx_s[okm]]
            for c, nm in enumerate(names):
                v = Xi[:, c]; m2 = np.isfinite(v)
                if m2.sum() > 100:
                    ric = spearman(v[m2], y[m2])
                    if ric is not None and (best is None or abs(ric) > abs(best[1])):
                        best = (f"{fam}:{nm}", ric)
        diag["horizons"][str(h)]["best_univariate_rank_ic"] = (
            {"feature": best[0], "rank_ic": best[1]} if best else None)
        log(f"[diag] h={h:>9}ms def={lab['defined'].mean():.3f} clean="
            f"{(lab['defined']&lab['clean']).mean():.3f} used={n_keep} eff_n="
            f"{diag['horizons'][str(h)]['effective_n']} verdict={diag['horizons'][str(h)]['verdict']} "
            f"best_uni={best}")
        del lab, keep, purge, fwd_day, okm, y

    # ---- model search ----------------------------------------------------
    iterations = []
    by_fh = {}

    def build(fam, h):
        keep_idx, y, f = cache[h]
        X, names = fb.family_matrix(feats, fam)
        Xi = X[keep_idx]
        good = np.isfinite(Xi).all(1) & np.isfinite(y)
        return Xi, y, f, good, names, keep_idx

    def naive_pred(h, ks):
        j0 = np.searchsorted(ts, ts[ks] - h * 1_000_000, side="left")
        return (mid[ks] / mid[np.clip(j0, 0, n_ticks - 1)] - 1.0) * 1e4

    def run_config(fam, h, model):
        Xi, y, f, good, names, ks = build(fam, h)
        tr = good & (f == "train"); va = good & (f == "val"); te = good & (f == "test")
        mu, sd = Xi[tr].mean(0), Xi[tr].std(0) + 1e-12
        Z = (Xi - mu) / sd
        out = {"family": fam, "family_name": fb.FAMILY_NAMES[fam], "horizon_ms": h, "model": model,
               "features": names, "n_train": int(tr.sum()), "n_val": int(va.sum()),
               "n_test": int(te.sum())}
        for tag, msk in (("val", va), ("test", te)):
            if model == "Naive":
                pred = naive_pred(h, ks[msk])
            else:
                pred = fit_predict(model, Z[tr], y[tr], Z[msk])
            c = RT_ANCHOR_USD / mid[ks[msk]] * 1e4
            pos = _positions(pred, c)
            m = core_metrics(pos, y[msk], c, mid[ks[msk]], pred=pred)
            m.update(ttest_nonoverlap(pos, y[msk], c, max(1, int(round(h / med_dt_ms)))))
            out[tag] = m
        out["val_net_edge_usd"] = out["val"].get("net_edge_usd")
        out["val_net_edge_bp"] = out["val"].get("net_edge_bp")
        out["val_p"] = out["val"].get("net_p")
        return out

    for h in HORIZONS_SEARCH:
        for fam in fb.FAMILIES:
            r = run_config(fam, h, "Ridge")
            iterations.append(r); by_fh[(fam, h)] = {"Ridge": r}
            log(f"   iter{len(iterations):02d} {fam} h={h:>6} Ridge val_net_usd="
                f"{r['val_net_edge_usd']} trades={r['val']['n_trades']} p={r['val_p']}")

    best_fam = {}
    for h in HORIZONS_SEARCH:
        cands = [(fam, by_fh[(fam, h)]["Ridge"]["val_net_edge_usd"]
                  if by_fh[(fam, h)]["Ridge"]["val_net_edge_usd"] is not None else -9)
                 for fam in fb.FAMILIES]
        pick = max(cands, key=lambda x: x[1])
        best_fam[h] = pick[0]
        log(f"[sel] best family @h={h}ms -> {pick[0]} (val_net_usd={pick[1]:.6f})")

    for h in HORIZONS_SEARCH:
        for model in ["Logistic", "GBT", "MLP"]:
            r = run_config(best_fam[h], h, model)
            iterations.append(r); by_fh.setdefault((best_fam[h], h), {})[model] = r
            log(f"   iter{len(iterations):02d} {best_fam[h]} h={h:>6} {model} val_net_usd="
                f"{r['val_net_edge_usd']} p={r['val_p']}")

    naive_ref = {}
    for h in HORIZONS_SEARCH:
        r = run_config(best_fam[h], h, "Naive")
        naive_ref[str(h)] = r
        log(f"   [ref] Naive h={h} val_net_usd={r['val_net_edge_usd']} "
            f"test_net_usd={r['test'].get('net_edge_usd')}")

    if len(iterations) > ITERATION_CAP:
        raise RuntimeError(f"iteration cap exceeded: {len(iterations)}")

    json.dump({"schema": "v3_alpha_model_manifest/1", "iteration_count": len(iterations),
               "cap": ITERATION_CAP,
               "iteration_log": [{"i": i + 1, "family": r["family"], "model": r["model"],
                                  "horizon_ms": r["horizon_ms"], "features": r["features"],
                                  "n_train": r["n_train"], "n_val": r["n_val"], "n_test": r["n_test"],
                                  "val_net_edge_usd": r["val_net_edge_usd"],
                                  "val_net_edge_bp": r["val_net_edge_bp"],
                                  "test_net_edge_usd": r["test"].get("net_edge_usd"),
                                  "test_net_edge_bp": r["test"].get("net_edge_bp")}
                                 for i, r in enumerate(iterations)],
               "naive_reference": naive_ref,
               "best_family_per_horizon": {str(k): v for k, v in best_fam.items()},
               "models": ["Naive", "Ridge", "Logistic", "GBT", "MLP"],
               "cost_anchor_usd": RT_ANCHOR_USD, "commission_rt_usd": COMMISSION_RT_USD,
               "note": "Naive is a reference evaluation (no fitting) and is not counted against "
                       "the 30-iteration cap"},
              open(os.path.join(ALPHA, "models", "model_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)

    # ---- latency metrics -------------------------------------------------
    def latency_metrics(pos, ks, h, L_ms):
        e = np.searchsorted(ts, ts[ks] + L_ms * 1_000_000, side="left")
        x = np.searchsorted(ts, ts[ks] + (h + L_ms) * 1_000_000, side="left")
        valid = (e < n_ticks) & (x < n_ticks)
        posv = pos.copy(); posv[~valid] = 0.0
        e = np.clip(e, 0, n_ticks - 1); x = np.clip(x, 0, n_ticks - 1)
        lng = posv > 0
        entry = np.where(lng, ask[e], bid[e]); exitp = np.where(lng, bid[x], ask[x])
        tr = posv != 0; n = int(tr.sum())
        if n == 0:
            return {"n_trades": 0, "net_edge_usd": None, "net_edge_bp": None, "hit_rate": None}
        nu = posv[tr] * (exitp[tr] - entry[tr]) - COMMISSION_RT_USD
        return {"n_trades": n, "net_edge_usd": float(nu.mean()),
                "net_edge_bp": float(np.mean(nu / mid[ks][tr] * 1e4)),
                "hit_rate": float(np.mean(nu > 0)),
                "median_abs_entry_drift_usd": float(np.median(np.abs(mid[e][tr] - mid[ks][tr])))}

    # ---- OOS + cost + latency -------------------------------------------
    oos = {"schema": "v3_alpha_oos/1", "horizons": {}}
    selected = {}
    cost_out = {"schema": "v3_alpha_cost_sensitivity/1", "anchor_usd_per_rt": RT_ANCHOR_USD,
                "tiers_usd_per_rt": RT_TIERS, "horizons": {}}
    lat_out = {"schema": "v3_alpha_latency_sensitivity/1", "latency_ms": LATENCY_MS, "horizons": {}}
    stat_out = {"schema": "v3_alpha_statistical_tests/1", "alpha": ALPHA_LEVEL,
                "bootstrap": {"n_resamples": 2000, "block_rule": "max(50, 10*rho)", "level": 0.95},
                "horizons": {}}
    for h in HORIZONS_SEARCH:
        allc = [r for (fam, hh), ms in by_fh.items() if hh == h for r in ms.values()]
        elig = [r for r in allc if r["val"]["n_trades"] and r["val"]["n_trades"] >= MIN_VAL_TRADES]
        _k = lambda r: r["val_net_edge_usd"] if r["val_net_edge_usd"] is not None else -9
        best = max(elig, key=_k) if elig else max(allc, key=_k)
        status = ("EVALUATED" if elig else
                  f"NO_VAL_ELIGIBLE_CONFIG(min_val_trades={MIN_VAL_TRADES}; "
                  f"reporting the VAL-best config as reference)")
        selected[h] = best
        Xi, y, f, good, names, ks = build(best["family"], h)
        tr = good & (f == "train"); te = good & (f == "test")
        mu, sd = Xi[tr].mean(0), Xi[tr].std(0) + 1e-12
        Z = (Xi - mu) / sd
        pred_te = naive_pred(h, ks[te]) if best["model"] == "Naive" else \
            fit_predict(best["model"], Z[tr], y[tr], Z[te])
        ct = {}
        for tier in RT_TIERS:
            c = tier / mid[ks[te]] * 1e4
            ct[f"{tier:.2f}"] = core_metrics(_positions(pred_te, c), y[te], c, mid[ks[te]],
                                             pred=pred_te)
        cost_out["horizons"][str(h)] = {
            "selected": f"{best['family']}/{best['model']}",
            "cost_tiers_usd_per_rt": {k: {"net_edge_bp": v["net_edge_bp"],
                                          "net_edge_usd": v["net_edge_usd"],
                                          "gross_edge_bp": v["gross_edge_bp"],
                                          "n_trades": v["n_trades"]} for k, v in ct.items()}}
        pos0 = _positions(pred_te, RT_ANCHOR_USD / mid[ks[te]] * 1e4)
        lt = {str(L): latency_metrics(pos0, ks[te], h, L) for L in LATENCY_MS}
        lat_out["horizons"][str(h)] = {"selected": f"{best['family']}/{best['model']}", "latency_ms": lt}
        c_te = RT_ANCHOR_USD / mid[ks[te]] * 1e4
        pos = _positions(pred_te, c_te)
        trd = pos != 0
        net_bp = pos[trd] * y[te][trd] - c_te[trd]
        gross_bp = pos[trd] * y[te][trd]
        boot = block_bootstrap_mean(net_bp, block_len_for(h), 2000, np.random.default_rng(SEED))
        rho = max(1, int(round(h / med_dt_ms)))
        ind = net_bp[::rho]; gind = gross_bp[::rho]
        tt = st.ttest_1samp(ind, 0.0) if len(ind) > 5 else (float("nan"), float("nan"))
        gt = st.ttest_1samp(gind, 0.0) if len(gind) > 5 else (float("nan"), float("nan"))
        stat_out["horizons"][str(h)] = {
            "selected": f"{best['family']}/{best['model']}",
            "test": {"n_trades": int(trd.sum()), "net_edge_bp": float(net_bp.mean()),
                     "net_edge_usd": float(np.mean(net_bp / 1e4 * mid[ks[te]][trd])),
                     "gross_edge_bp": float(gross_bp.mean()), "bootstrap_net_bp": boot,
                     "nonoverlap_rho": rho, "n_independent": int(len(ind)),
                     "t_noverlap_net": float(tt[0]), "p_noverlap_net": float(tt[1]),
                     "t_noverlap_gross": float(gt[0]), "p_noverlap_gross": float(gt[1]),
                     "ci_excludes_zero_positive": bool(boot["ci_low"] is not None and boot["ci_low"] > 0)},
            "val": {"net_edge_bp": best["val"].get("net_edge_bp"),
                    "net_edge_usd": best["val"].get("net_edge_usd"),
                    "n_trades": best["val"].get("n_trades")}}
        oos["horizons"][str(h)] = {"status": status, "selected_family": best["family"],
                                   "selected_model": best["model"], "features": names,
                                   "val_metrics": best["val"], "test_metrics": best["test"],
                                   "cost_tiers_usd_per_rt": {k: {"net_edge_bp": v["net_edge_bp"],
                                                                 "net_edge_usd": v["net_edge_usd"]}
                                                             for k, v in ct.items()},
                                   "latency_ms": lt}
        log(f"[oos] h={h} {best['family']}/{best['model']} test_net_usd={best['test'].get('net_edge_usd')} "
            f"test_net_bp={best['test'].get('net_edge_bp')} p={best['test'].get('net_p')}")

    json.dump(cost_out, open(os.path.join(ALPHA, "backtest", "cost_sensitivity.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(lat_out, open(os.path.join(ALPHA, "backtest", "latency_sensitivity.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(stat_out, open(os.path.join(ALPHA, "statistics", "statistical_tests.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(oos, open(os.path.join(ALPHA, "oos", "oos_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)

    # ---- multiple testing -------------------------------------------------
    tests = [{"i": i + 1, "family": r["family"], "horizon_ms": r["horizon_ms"], "model": r["model"],
              "n_trades": r["val"]["n_trades"], "net_edge_usd": r["val"].get("net_edge_usd"),
              "net_edge_bp": r["val"].get("net_edge_bp"),
              "gross_edge_bp": r["val"].get("gross_edge_bp"), "p_value": r["val_p"]}
             for i, r in enumerate(iterations)]
    valid = [t for t in tests if t["p_value"] is not None and np.isfinite(t["p_value"])]
    n_rej = 0
    if valid:
        from statsmodels.stats.multitest import multipletests
        rej, padj, _, _ = multipletests([t["p_value"] for t in valid], alpha=FDR_Q, method="fdr_bh")
        for t, okk, pa in zip(valid, rej, padj):
            t["reject_fdr"] = bool(okk); t["p_adj_bh"] = float(pa)
        n_rej = int(sum(1 for t in valid if t["reject_fdr"]))
    json.dump({"schema": "v3_alpha_multiple_testing/1", "alpha": ALPHA_LEVEL, "fdr_q": FDR_Q,
               "method": "Benjamini-Hochberg (fdr_bh)",
               "family_definition": "all 30 feature/model/horizon screen tests, VAL fold, two-sided "
                                    "t on non-overlapping net returns",
               "n_tests": len(tests), "n_valid_p": len(valid), "n_reject": n_rej, "tests": tests},
              open(os.path.join(ALPHA, "statistics", "multiple_testing.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)

    diag["generated_utc_end"] = now_utc()
    diag["runtime_s"] = round(time.time() - t0, 1)
    json.dump(diag, open(os.path.join(ALPHA, "statistics", "effective_sample.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

    # ---- per-family backtest files ---------------------------------------
    for fam in fb.FAMILIES:
        rec = {"schema": "v3_alpha_backtest/1", "family": fam, "family_name": fb.FAMILY_NAMES[fam],
               "features": fb.FAMILIES[fam], "cost_anchor_usd_per_rt": RT_ANCHOR_USD,
               "note": "screen model = Ridge; extra models only for the best family per horizon",
               "horizons": {}}
        for h in HORIZONS_SEARCH:
            rec["horizons"][str(h)] = {
                m: {"val": {"n_trades": r["val"]["n_trades"],
                            "gross_edge_bp": r["val"].get("gross_edge_bp"),
                            "net_edge_bp": r["val"].get("net_edge_bp"),
                            "net_edge_usd": r["val"].get("net_edge_usd"),
                            "hit_rate": r["val"].get("hit_rate"),
                            "rank_ic": r["val"].get("rank_ic"), "p_value": r["val"].get("net_p")},
                    "test": {"n_trades": r["test"]["n_trades"],
                             "gross_edge_bp": r["test"].get("gross_edge_bp"),
                             "net_edge_bp": r["test"].get("net_edge_bp"),
                             "net_edge_usd": r["test"].get("net_edge_usd"),
                             "hit_rate": r["test"].get("hit_rate"),
                             "rank_ic": r["test"].get("rank_ic"), "p_value": r["test"].get("net_p")}}
                for m, r in by_fh.get((fam, h), {}).items()}
        name = "B0_baseline.json" if fam == "B0" else f"{fam}_backtest.json"
        json.dump(rec, open(os.path.join(ALPHA, "backtest", name), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)

    json.dump({"schema": "v3_alpha_model_results/1",
               "models_tested": ["Naive", "Ridge", "Logistic", "GBT", "MLP"],
               "search_horizons_ms": HORIZONS_SEARCH, "iteration_count": len(iterations),
               "best_family_per_horizon": {str(k): v for k, v in best_fam.items()},
               "selected_per_horizon": {str(h): (f"{selected[h]['family']}/{selected[h]['model']}"
                                                 if selected[h] else None) for h in HORIZONS_SEARCH},
               "iteration_results": [{k: r[k] for k in ["family", "horizon_ms", "model", "features",
                                                        "n_train", "n_val", "n_test", "val", "test"]}
                                     for r in iterations],
               "naive_reference": naive_ref},
              open(os.path.join(ALPHA, "models", "model_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)

    json.dump({"generated_utc": now_utc(), "runtime_s": round(time.time() - t0, 1),
               "iterations": len(iterations), "n_reject_fdr": n_rej},
              open(os.path.join(ALPHA, "tools", "_run_state.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    log(f"[done] iterations={len(iterations)} fdr_rejects={n_rej} runtime={time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
