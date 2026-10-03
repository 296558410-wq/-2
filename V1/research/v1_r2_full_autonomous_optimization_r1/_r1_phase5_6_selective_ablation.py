# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION R1 — PHASE 5+6: SELECTIVE PREDICTION / ABSTENTION / CALIBRATION
+ COUNTER-EVIDENCE & AMBIGUITY ABLATION + PERMUTATION NULL (RESEARCH ONLY).

Return-free. Read-only on frozen artifacts. Pre-registered in registry/v1_r2_r1_phase5_6_preregistration.json.
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
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
P2 = os.path.join(R1, "_r1_phase2_state_vs_event.py")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
BLIND_SPLIT = 0.6
NPERM, BLOCK = 30, 48
A2 = ["atr_pctl", "rng_exp", "vel4", "acc", "er10", "eff3", "act3"]
COVERAGES = [1.0, 0.8, 0.6, 0.4, 0.2]


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wjson(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def dwell_lengths(seq):
    d = np.zeros(len(seq), int); cur = 1
    for i in range(len(seq)):
        cur = cur + 1 if (i > 0 and seq[i] == seq[i - 1]) else 1
        d[i] = cur
    return d


def fit_predict(Xtr, ytr, Xte):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=1.0, max_iter=5000, solver="lbfgs")
    clf.fit(sc.transform(Xtr), ytr)
    prob = clf.predict_proba(sc.transform(Xte))
    return clf.classes_, prob, clf


def eval_block(cls, prob, yte, ytr):
    ci = [list(cls).index(v) for v in yte]
    ll_m = -np.mean(np.log2(np.clip(prob[np.arange(len(yte)), ci], 1e-12, 1.0)))
    pri = np.array([np.mean(ytr == c) for c in cls])
    ll_b = -np.mean(np.log2(np.clip(pri[ci], 1e-12, 1.0)))
    pred = cls[np.argmax(prob, axis=1)]
    acc = float(np.mean(pred == yte))
    # selective / risk-coverage
    conf = prob.max(axis=1)
    order = np.argsort(-conf)
    sel = {}
    for cov in COVERAGES:
        k = max(1, int(len(yte) * cov))
        idx = order[:k]
        sel[f"cov_{int(cov*100)}"] = {"coverage": round(k / len(yte), 3), "accuracy": round(float(np.mean(pred[idx] == yte[idx])), 4),
                                        "mean_confidence": round(float(conf[idx].mean()), 4)}
    # ECE (10 bins)
    correct = (pred == yte).astype(float)
    bins = np.clip((conf * 10).astype(int), 0, 9)
    ece = 0.0
    for b in range(10):
        m = bins == b
        if m.sum() > 0:
            ece += (m.sum() / len(yte)) * abs(correct[m].mean() - conf[m].mean())
    return {"dll": round(float(ll_b - ll_m), 5), "acc": round(acc, 4), "n_test": int(len(yte)),
             "selective": sel, "ECE": round(float(ece), 4), "mean_conf": round(float(conf.mean()), 4)}


def main():
    pre = os.path.join(R1, "registry", "v1_r2_r1_phase5_6_preregistration.json")
    pre_hash = hashlib.sha256(open(pre, "rb").read()).hexdigest()
    p2 = load_mod("p2", P2)
    m15, frozen, stateful, X, geom, ev = p2.build()
    n = len(m15)
    y = np.array([stateful[i + H] if i + H < n else None for i in range(n)], dtype=object)
    st = np.array(stateful, dtype=object)
    dw = dwell_lengths(stateful)
    nod = np.array([1.0 if st[i] == "NO_DEFINED_STATE" else 0.0 for i in range(n)])
    nod8 = pd.Series(nod).rolling(8, min_periods=1).mean().to_numpy()
    # one-hot current state
    levels = sorted(set(stateful)); ohm = np.zeros((n, len(levels)))
    for i, v in enumerate(stateful):
        ohm[i, levels.index(v)] = 1.0
    h1 = m15.resample("60min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna().reindex(m15.index, method="ffill")
    pc = h1["c"].shift(1); tr_ = pd.concat([(h1["h"] - h1["l"]), (h1["h"] - pc).abs(), (h1["l"] - pc).abs()], axis=1).max(axis=1)
    h1atr = tr_.rolling(20).mean()
    H1c = np.column_stack([(h1["c"] / h1["c"].shift(4) - 1) * 1e4, tr_ / h1atr,
                            (h1["c"].rolling(20).mean() - h1["c"].rolling(20).mean().shift(2)) / h1atr])
    iA2 = [p2.FEATS.index(c) for c in A2]
    Xv = {
        "A2_STRUCT": X[:, iA2],
        "A2_PLUS_STATE_HISTORY": np.hstack([X[:, iA2], ohm, dw.reshape(-1, 1), nod8.reshape(-1, 1)]),
        "A2_PLUS_H1_CONTEXT": np.hstack([X[:, iA2], H1c]),
        "A2_PLUS_ALL": np.hstack([X[:, iA2], ohm, dw.reshape(-1, 1), nod8.reshape(-1, 1), H1c]),
    }
    ok = np.array([i for i in range(n) if y[i] is not None and np.all(np.isfinite(Xv["A2_PLUS_ALL"][i]))])
    lab = np.array([y[i] for i in ok], dtype=object)
    split = int(n * BLIND_SPLIT)
    trm = ok < split; tem = ok >= split
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_5_6_SELECTIVE_ABSTENTION_AND_ABLATION",
            "preregistration_hash": pre_hash, "ts_utc": NOW, "bars": n, "H": H, "return_free": True,
            "n_train": int(trm.sum()), "n_test": int(tem.sum()), "n_classes": len(levels)}
    blind = {}
    for name, M in Xv.items():
        Xtr = M[ok][trm]; Xte = M[ok][tem]
        cls, prob, clf = fit_predict(Xtr, lab[trm], Xte)
        blind[name] = eval_block(cls, prob, lab[tem], lab[trm])
    out["blind_ablation"] = blind
    best = max(blind.items(), key=lambda kv: kv[1]["dll"])
    out["BLIND_BEST"] = {"model": best[0], "dll": best[1]["dll"], "acc": best[1]["acc"]}
    inc = {k: round(blind[k]["dll"] - blind["A2_STRUCT"]["dll"], 5) for k in blind}
    out["incremental_vs_A2"] = inc

    # ---- permutation null on the best variant ----
    M = Xv[best[0]]
    Xtr = M[ok][trm]; Xte = M[ok][tem]; ytr0 = lab[trm]; yte = lab[tem]
    rng = np.random.default_rng(20260927)
    nulls = []
    for _ in range(NPERM):
        nb = len(ytr0) // BLOCK + 1
        stt = rng.integers(0, max(1, len(ytr0) - BLOCK), nb)
        perm = np.concatenate([ytr0[s:s + BLOCK] for s in stt])[:len(ytr0)]
        cls, prob, _ = fit_predict(Xtr, perm, Xte)
        nulls.append(eval_block(cls, prob, yte, perm)["dll"])
    nulls = np.array(nulls)
    out["null"] = {"NPERM": NPERM, "null_mean": round(float(nulls.mean()), 5), "null_p95": round(float(np.percentile(nulls, 95)), 5),
                    "null_max": round(float(nulls.max()), 5), "empirical_p": round(float(np.mean(nulls >= best[1]["dll"])), 4)}
    sel = blind[best[0]]["selective"]
    out["SELECTIVE_VALUE"] = bool(sel["cov_40"]["accuracy"] - blind[best[0]]["acc"] >= 0.10)
    out["VERDICT"] = ("SELECTIVE_AND_ABLATION_DECIDED" if out["null"]["empirical_p"] <= 0.05 else "RESULT_NOT_SEPARABLE_FROM_NULL")
    out["safety"] = {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                      "FROZEN_ARTIFACT_WRITE": 0, "ONTOLOGY_MODIFIED": 0, "PARAM_MODIFIED": 0, "FUTURE_RETURN_USED": "NO",
                      "PNL_USED": "NO", "WIN_RATE_USED": "NO"}
    outp = os.path.join(R1, "reports", "V1_R2_R1_PHASE5_6_SELECTIVE_ABLATION.json")
    wjson(outp, out)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_5_6", "report": os.path.relpath(outp, REPO),
                              "verdict": out["VERDICT"], "preregistration_hash": pre_hash}, ensure_ascii=False) + "\n")
    print("WROTE", outp, "| VERDICT:", out["VERDICT"])
    print(json.dumps({"blind_best": out["BLIND_BEST"], "incremental": inc, "null": out["null"],
                        "selective": blind[best[0]]["selective"], "ece": blind[best[0]]["ECE"],
                        "SELECTIVE_VALUE": out["SELECTIVE_VALUE"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
