# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION R1 — PHASE 2: STATE vs EVENT LIFE-OR-DEATH TEST (RESEARCH ONLY).

Does a STATE survive as a predictive object once given a lifecycle? Does an EVENT target beat it?
Pre-registered in registry/v1_r2_r1_phase2_preregistration.json (frozen before analysis).
Read-only on frozen artifacts. Writes ONLY under v1_r2_full_autonomous_optimization_r1/.
No orders / no broker / no live. No future return, PnL or win-rate.
"""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
import statistics
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
R1MOD = os.path.join(UP, "_v1r2_phaseB_R1.py")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
HYST_K = 2
PURGE, N_FOLDS, NPERM, BLOCK = 480, 5, 30, 48
FLOOR = 0.01
SEED = 20260927
FEATS = ["atr_pctl", "er10", "slope5", "rng_exp", "vel4", "acc", "eff3", "act3"]
RANGE_W = 96


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def hysteresis(labels, k):
    if not labels:
        return []
    out = [labels[0]]; cur = labels[0]; pend = None; plen = 0
    for x in labels[1:]:
        if x == cur:
            out.append(cur); pend = None; plen = 0
        else:
            if pend == x:
                plen += 1
            else:
                pend = x; plen = 1
            if plen >= k:
                cur = x; out.append(cur); pend = None; plen = 0
            else:
                out.append(cur)
    return out


def build():
    mod = load_mod("c15", os.path.join(C15, "_c1_5_run.py"))
    r1 = load_mod("r1mod", R1MOD)
    m = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m["dt"] = pd.to_datetime(m["dt_utc"], utc=True)
    m = m.set_index("dt").sort_index()
    m15 = pd.DataFrame({"o": m["open"].resample("15min").first(), "h": m["high"].resample("15min").max(),
                         "l": m["low"].resample("15min").min(), "c": m["close"].resample("15min").last()}).dropna()
    rows = mod.label_series(m15, "M15")
    frozen = [r["MARKET_BEHAVIOR"] for r in rows]
    stateful = hysteresis(frozen, HYST_K)
    ind = r1.indicators(m15.copy())
    X = ind[FEATS].to_numpy(float)
    n = len(m15)
    c = m15["c"].to_numpy(float); hh = m15["h"].to_numpy(float); ll = m15["l"].to_numpy(float)
    # T3 next-bar geometry
    geom = []
    for i in range(n):
        if i + 1 >= n:
            geom.append(None); continue
        a = c[i]; b = c[i + 1]
        thr = 0.15 * (np.nanmean(np.abs(np.diff(c[max(0, i - 20):i + 1]))) or 1e-9)
        geom.append("UP_BREAK" if b > a + thr else "DOWN_BREAK" if b < a - thr else "INSIDE")
    # T4 causal breakout event within next H bars
    ev = []
    for i in range(n):
        if i < RANGE_W + 1 or i + H >= n:
            ev.append(None); continue
        hi = hh[i - RANGE_W:i].max(); lo = ll[i - RANGE_W:i].min()
        seg = c[i + 1:i + 1 + H]
        up = bool((seg > hi).any()); dn = bool((seg < lo).any())
        ev.append("UP_BREAK" if (up and not dn) else "DOWN_BREAK" if (dn and not up) else "BOTH" if (up and dn) else "NONE")
    return m15, frozen, stateful, X, geom, ev


def build_target(frozen, stateful, geom, ev, which):
    if which == "T1_FROZEN_STATE":
        y = [frozen[i + H] if i + H < len(frozen) else None for i in range(len(frozen))]
    elif which == "T2_STATEFUL_STATE":
        y = [stateful[i + H] if i + H < len(stateful) else None for i in range(len(stateful))]
    elif which == "T3_GEOMETRY":
        y = geom
    else:
        y = ev
    return y


def walk_forward(X, y):
    n = len(y)
    ok = [(i, y[i]) for i in range(n) if y[i] is not None and np.all(np.isfinite(X[i]))]
    idx = np.array([o[0] for o in ok]); lab = np.array([o[1] for o in ok])
    start = int(n * 0.6)
    cuts = np.linspace(start, n - 1, N_FOLDS + 1).astype(int)
    mrows = []
    for f in range(N_FOLDS):
        tr = (idx < cuts[f] - PURGE); te = (idx >= cuts[f]) & (idx < cuts[f + 1])
        if tr.sum() < 200 or te.sum() < 50:
            continue
        Xtr, ytr = X[idx[tr]], lab[tr]
        Xte, yte = X[idx[te]], lab[te]
        classes = sorted(set(ytr))
        if len(classes) < 2:
            continue
        # INSTRUMENT REPAIR (v2): standardize features using TRAIN-only statistics (PIT-safe).
        # v1 used raw features and lbfgs failed to converge -> measurement unreliable. No result tuning.
        sc = StandardScaler().fit(Xtr)
        Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
        clf = LogisticRegression(C=1.0, max_iter=5000, solver="lbfgs")
        clf.fit(Xtr_s, ytr)
        prob = np.clip(clf.predict_proba(Xte_s), 1e-12, 1.0)
        ll_model = -np.mean(np.log2(prob[np.arange(len(yte)), [list(clf.classes_).index(v) for v in yte]]))
        pri = np.array([np.mean(ytr == cc) for cc in clf.classes_])
        pm = np.clip(pri[[list(clf.classes_).index(v) for v in yte]], 1e-12, 1.0)
        ll_base = -np.mean(np.log2(pm))
        maj = collections.Counter(ytr).most_common(1)[0][0]
        mrows.append({"fold": f, "n_test": int(te.sum()), "ll_model": round(ll_model, 5), "ll_base": round(ll_base, 5),
                       "dll": round(ll_base - ll_model, 5), "acc_model": round(float(np.mean(clf.predict(Xte_s) == yte)), 4),
                       "acc_majority": round(float(np.mean(yte == maj)), 4)})
    dll = round(statistics.mean(r["dll"] for r in mrows), 5) if mrows else 0.0
    return {"folds": mrows, "DeltaLL": dll,
             "acc_model": round(statistics.mean(r["acc_model"] for r in mrows), 4) if mrows else None,
             "acc_majority": round(statistics.mean(r["acc_majority"] for r in mrows), 4) if mrows else None,
             "worst_fold_dll": round(min((r["dll"] for r in mrows), default=0.0), 5), "n_folds_used": len(mrows)}


def null_test(X, y, obs_dll):
    rng = np.random.default_rng(SEED)
    n = len(y)
    arr = np.array([v if v is not None else "__NONE__" for v in y], dtype=object)
    nulls = []
    for _ in range(NPERM):
        nb = n // BLOCK + 1
        st = rng.integers(0, max(1, n - BLOCK), nb)
        perm = np.concatenate([arr[s:s + BLOCK] for s in st])[:n]
        yp = [None if v == "__NONE__" else v for v in perm]
        nulls.append(walk_forward(X, yp)["DeltaLL"])
    nulls = np.array(nulls)
    p = float(np.mean(nulls >= obs_dll))
    return {"NPERM": NPERM, "null_mean": round(float(nulls.mean()), 5), "null_p95": round(float(np.percentile(nulls, 95)), 5),
             "empirical_p": round(p, 4), "null_max": round(float(nulls.max()), 5)}


def main():
    pre = os.path.join(R1, "registry", "v1_r2_r1_phase2_preregistration.json")
    pre_hash = hashlib.sha256(open(pre, "rb").read()).hexdigest()
    print("phase2 preregistration_hash:", pre_hash[:16])
    m15, frozen, stateful, X, geom, ev = build()
    print("bars:", len(m15), "| frozen distinct:", len(set(frozen)), "| stateful distinct:", len(set(stateful)))
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_2_STATE_VS_EVENT_LIFE_DEATH",
            "preregistration_hash": pre_hash, "ts_utc": NOW, "bars": len(m15), "H": H, "k": HYST_K,
            "features": FEATS, "targets": {}}
    # persistence of stateful vs frozen at horizon H
    def pers(seq):
        return round(sum(1 for i in range(len(seq) - H) if seq[i] == seq[i + H]) / (len(seq) - H), 4)
    out["persistence_baseline"] = {"frozen": pers(frozen), "stateful_k2": pers(stateful)}
    for which in ("T1_FROZEN_STATE", "T2_STATEFUL_STATE", "T3_GEOMETRY", "T4_EVENT_BREAKOUT"):
        y = build_target(frozen, stateful, geom, ev, which)
        wf = walk_forward(X, y)
        nt = null_test(X, y, wf["DeltaLL"])
        survived = wf["DeltaLL"] >= FLOOR and nt["empirical_p"] <= 0.05 and (wf["acc_model"] or 0) > (wf["acc_majority"] or 1)
        out["targets"][which] = {"walk_forward": wf, "null": nt, "SURVIVES": bool(survived)}
        print(which, "DeltaLL=", wf["DeltaLL"], "p=", nt["empirical_p"], "survives=", survived)
    t = out["targets"]
    if t["T1_FROZEN_STATE"]["SURVIVES"] or t["T2_STATEFUL_STATE"]["SURVIVES"]:
        verdict = "STATE_SURVIVES"
    elif t["T4_EVENT_BREAKOUT"]["SURVIVES"]:
        verdict = "EVENT_DOMINATES"
    else:
        verdict = "NEITHER"
    out["VERDICT"] = verdict
    out["safety"] = {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                      "FROZEN_ARTIFACT_WRITE": 0, "ONTOLOGY_MODIFIED": 0, "PARAM_MODIFIED": 0, "FUTURE_RETURN_USED": "NO",
                      "PNL_USED": "NO", "WIN_RATE_USED": "NO"}
    outp = os.path.join(R1, "reports", "V1_R2_R1_PHASE2_STATE_VS_EVENT.json")
    wjson(outp, out)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_2", "report": os.path.relpath(outp, REPO),
                              "verdict": verdict, "preregistration_hash": pre_hash}, ensure_ascii=False) + "\n")
    print("WROTE", outp)
    print("VERDICT:", verdict)
    print(json.dumps(out, ensure_ascii=False, default=str)[:2500])


if __name__ == "__main__":
    main()
