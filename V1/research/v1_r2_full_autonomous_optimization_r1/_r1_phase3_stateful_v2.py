# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION R1 — PHASE 3: STATEFUL STATE v2 + STRICT BLIND + ABLATION + STABILITY
+ MTF INCREMENT (RESEARCH ONLY).

Pre-registered in registry/v1_r2_r1_phase3_preregistration.json.
Reuses the Phase 2 builder (frozen labeler + PIT-safe features). No orders / no broker / no live.
No future return, PnL or win-rate anywhere. Writes ONLY under v1_r2_full_autonomous_optimization_r1/.
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
P2 = os.path.join(R1, "_r1_phase2_state_vs_event.py")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
BLIND_SPLIT = 0.6
FLOOR = 0.01
ABLATIONS = {
    "A0_VOL_ONLY": ["atr_pctl", "rng_exp"],
    "A1_VOL_MOM": ["atr_pctl", "rng_exp", "vel4", "acc"],
    "A2_VOL_MOM_STRUCT": ["atr_pctl", "rng_exp", "vel4", "acc", "er10", "eff3", "act3"],
    "A3_ALL_PLUS_SLOPE": ["atr_pctl", "er10", "slope5", "rng_exp", "vel4", "acc", "eff3", "act3"],
}


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wjson(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def fit_eval(Xtr, ytr, Xte, yte):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=1.0, max_iter=5000, solver="lbfgs")
    clf.fit(sc.transform(Xtr), ytr)
    prob = np.clip(clf.predict_proba(sc.transform(Xte)), 1e-12, 1.0)
    cls = list(clf.classes_)
    ll_model = -np.mean(np.log2(prob[np.arange(len(yte)), [cls.index(v) for v in yte]]))
    pri = np.array([np.mean(ytr == cc) for cc in cls])
    ll_base = -np.mean(np.log2(np.clip(pri[[cls.index(v) for v in yte]], 1e-12, 1.0)))
    maj = collections.Counter(ytr).most_common(1)[0][0]
    return {"dll": round(ll_base - ll_model, 5), "ll_model": round(ll_model, 5), "ll_base": round(ll_base, 5),
             "acc_model": round(float(np.mean(clf.predict(sc.transform(Xte)) == yte)), 4),
             "acc_majority": round(float(np.mean(yte == maj)), 4), "n_test": int(len(yte)), "n_train": int(len(ytr))}


def main():
    pre = os.path.join(R1, "registry", "v1_r2_r1_phase3_preregistration.json")
    pre_hash = hashlib.sha256(open(pre, "rb").read()).hexdigest()
    p2 = load_mod("p2", P2)
    m15, frozen, stateful, X, geom, ev = p2.build()
    feats = p2.FEATS
    n = len(m15)
    y = np.array([stateful[i + H] if i + H < n else None for i in range(n)], dtype=object)
    ok = np.array([i for i in range(n) if y[i] is not None and np.all(np.isfinite(X[i]))])
    lab = np.array([y[i] for i in ok], dtype=object)
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_3_STATEFUL_V2_BLIND_ABLATION",
            "preregistration_hash": pre_hash, "ts_utc": NOW, "bars": n, "H": H,
            "state_definition": "STATE_V2 = frozen MARKET_BEHAVIOR with min-dwell k=2 (pre-registered from Phase 1)",
            "persistence": {"frozen_H8": round(sum(1 for i in range(n - H) if frozen[i] == frozen[i + H]) / (n - H), 4),
                             "stateful_k2_H8": round(sum(1 for i in range(n - H) if stateful[i] == stateful[i + H]) / (n - H), 4)}}
    # ---- STRICT BLIND: single split, one fit, no refit ----
    split = int(n * BLIND_SPLIT)
    tr = ok[ok < split]; te = ok[ok >= split]
    Xi = X[ok]
    blind = {}
    for name, cols in ABLATIONS.items():
        ci = [feats.index(c) for c in cols]
        blind[name] = fit_eval(Xi[np.isin(ok, tr)][:, ci], lab[np.isin(ok, tr)], Xi[np.isin(ok, te)][:, ci], lab[np.isin(ok, te)])
    out["strict_blind_ablation"] = blind
    # ---- STABILITY: 4 sub-blocks of the blind test region ----
    sub = np.array_split(te, 4)
    ci = [feats.index(c) for c in ABLATIONS["A3_ALL_PLUS_SLOPE"]]
    stab = []
    trm = np.isin(ok, tr)
    for b in sub:
        m = np.isin(ok, b)
        r = fit_eval(Xi[trm][:, ci], lab[trm], Xi[m][:, ci], lab[m])
        r["block_start"] = str(m15.index[b[0]]); r["block_end"] = str(m15.index[b[-1]])
        stab.append(r)
    out["stability_4blocks"] = {"blocks": stab, "dll_mean": round(statistics.mean(s["dll"] for s in stab), 5),
                                 "dll_min": round(min(s["dll"] for s in stab), 5), "all_positive": all(s["dll"] > 0 for s in stab)}
    # ---- MTF INCREMENT: add H1 context features ----
    h1 = m15.resample("60min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    h1 = h1.reindex(m15.index, method="ffill")
    comp = pd.DataFrame({"c": h1["c"], "h": h1["h"], "l": h1["l"]})
    pc = comp["c"].shift(1)
    tr_ = pd.concat([(comp["h"] - comp["l"]), (comp["h"] - pc).abs(), (comp["l"] - pc).abs()], axis=1).max(axis=1)
    h1atr = tr_.rolling(20).mean()
    h1ctx = pd.DataFrame({"h1_ret": (comp["c"] / comp["c"].shift(4) - 1) * 1e4,
                           "h1_rng": tr_ / h1atr,
                           "h1_slope": (comp["c"].rolling(20).mean() - comp["c"].rolling(20).mean().shift(2)) / h1atr}).to_numpy(float)
    Xm = np.hstack([X, h1ctx])
    okm = np.array([i for i in range(n) if y[i] is not None and np.all(np.isfinite(Xm[i]))])
    labm = np.array([y[i] for i in okm], dtype=object)
    cim = [feats.index(c) for c in ABLATIONS["A3_ALL_PLUS_SLOPE"]] + [len(feats), len(feats) + 1, len(feats) + 2]
    trm2 = np.isin(okm, okm[okm < split]); tem2 = np.isin(okm, okm[okm >= split])
    base_m = fit_eval(Xm[okm][trm2][:, [feats.index(c) for c in ABLATIONS["A3_ALL_PLUS_SLOPE"]]], labm[trm2],
                       Xm[okm][tem2][:, [feats.index(c) for c in ABLATIONS["A3_ALL_PLUS_SLOPE"]]], labm[tem2])
    mtf_m = fit_eval(Xm[okm][trm2][:, cim], labm[trm2], Xm[okm][tem2][:, cim], labm[tem2])
    out["MTF_increment"] = {"base_A3": base_m, "plus_H1_context": mtf_m,
                             "delta_dll": round(mtf_m["dll"] - base_m["dll"], 5),
                             "MTF_ADDS_VALUE": bool(mtf_m["dll"] - base_m["dll"] >= FLOOR)}
    # ---- verdict ----
    best = max(blind.items(), key=lambda kv: kv[1]["dll"])
    out["BLIND_BEST"] = {"model": best[0], "dll": best[1]["dll"], "acc_model": best[1]["acc_model"], "acc_majority": best[1]["acc_majority"]}
    out["ACCEPTANCE"] = {
        "effect_floor_bits": FLOOR,
        "blind_dll_ge_floor": bool(best[1]["dll"] >= FLOOR),
        "beats_majority": bool(best[1]["acc_model"] > best[1]["acc_majority"]),
        "stability_all_positive": out["stability_4blocks"]["all_positive"]}
    out["VERDICT"] = ("STATEFUL_STATE_V2_ACCEPTED" if all(out["ACCEPTANCE"][k] for k in
                       ("blind_dll_ge_floor", "beats_majority", "stability_all_positive")) else "STATEFUL_STATE_V2_NOT_ACCEPTED")
    out["safety"] = {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                      "FROZEN_ARTIFACT_WRITE": 0, "ONTOLOGY_MODIFIED": 0, "PARAM_MODIFIED": 0, "FUTURE_RETURN_USED": "NO",
                      "PNL_USED": "NO", "WIN_RATE_USED": "NO"}
    outp = os.path.join(R1, "reports", "V1_R2_R1_PHASE3_STATEFUL_V2.json")
    wjson(outp, out)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_3", "report": os.path.relpath(outp, REPO),
                              "verdict": out["VERDICT"], "preregistration_hash": pre_hash}, ensure_ascii=False) + "\n")
    print("WROTE", outp, "| VERDICT:", out["VERDICT"])
    print(json.dumps(out, ensure_ascii=False, default=str)[:3000])


if __name__ == "__main__":
    main()
