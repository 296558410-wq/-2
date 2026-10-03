# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION R1 — PHASE 4: TRANSITION EARLY-WARNING + DWELL HAZARD (RESEARCH ONLY).

Return-free: no returns, no PnL, no win-rate anywhere. Read-only on frozen artifacts.
Pre-registered in registry/v1_r2_r1_phase4_preregistration.json.
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
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
P2 = os.path.join(R1, "_r1_phase2_state_vs_event.py")
NOW = datetime.now(timezone.utc).isoformat()
HS = [1, 2, 4, 8]
PURGE, N_FOLDS = 480, 5
FLOOR = 0.005


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
    d = np.zeros(len(seq), int)
    cur = 1
    for i in range(len(seq)):
        if i > 0 and seq[i] == seq[i - 1]:
            cur += 1
        else:
            cur = 1
        d[i] = cur
    return d


def onehot(seq):
    levels = sorted(set(seq))
    idx = {v: i for i, v in enumerate(levels)}
    M = np.zeros((len(seq), len(levels)))
    for i, v in enumerate(seq):
        M[i, idx[v]] = 1.0
    return M, levels


def wf_binary(X, y, idx):
    n = len(y)
    start = int(n * 0.6)
    cuts = np.linspace(start, n - 1, N_FOLDS + 1).astype(int)
    rows = []
    for f in range(N_FOLDS):
        tr = idx < cuts[f] - PURGE
        te = (idx >= cuts[f]) & (idx < cuts[f + 1])
        if tr.sum() < 200 or te.sum() < 50:
            continue
        Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]
        if len(set(ytr)) < 2 or len(set(yte)) < 2:
            continue
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(C=1.0, max_iter=5000, solver="lbfgs")
        clf.fit(sc.transform(Xtr), ytr)
        p = sc.transform(Xte)
        pr = np.clip(clf.predict_proba(p)[:, 1], 1e-12, 1 - 1e-12)
        ll_m = -np.mean(yte * np.log2(pr) + (1 - yte) * np.log2(1 - pr))
        b = np.clip(ytr.mean(), 1e-12, 1 - 1e-12)
        ll_b = -np.mean(yte * np.log2(b) + (1 - yte) * np.log2(1 - b))
        auc = roc_auc_score(yte, pr) if len(set(yte)) > 1 else None
        rows.append({"dll": round(ll_b - ll_m, 5), "auc": round(float(auc), 4) if auc else None, "n": int(te.sum())})
    if not rows:
        return {"dll": 0.0, "auc": None, "folds": 0}
    return {"dll": round(statistics.mean(r["dll"] for r in rows), 5),
             "auc": round(statistics.mean(r["auc"] for r in rows if r["auc"] is not None), 4) if any(r["auc"] for r in rows) else None,
             "folds": len(rows), "rows": rows}


def main():
    pre = os.path.join(R1, "registry", "v1_r2_r1_phase4_preregistration.json")
    pre_hash = hashlib.sha256(open(pre, "rb").read()).hexdigest()
    p2 = load_mod("p2", P2)
    m15, frozen, stateful, X, geom, ev = p2.build()
    n = len(m15)
    feats = p2.FEATS
    st = np.array(stateful, dtype=object)
    dw = dwell_lengths(stateful)
    oh, levels = onehot(stateful)
    Xs = np.hstack([X, oh, dw.reshape(-1, 1)])
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_4_TRANSITION_EARLY_WARNING_AND_HAZARD",
            "preregistration_hash": pre_hash, "ts_utc": NOW, "bars": n, "return_free": True,
            "state_distinct": len(levels)}

    # ---- hazard curve: P(change at t+1 | dwell = d) ----
    haz = collections.defaultdict(lambda: [0, 0])
    for i in range(n - 1):
        d = dw[i]
        haz[d][1] += 1
        if st[i + 1] != st[i]:
            haz[d][0] += 1
    out["dwell_hazard"] = {str(d): {"n": v[1], "transitions": v[0], "hazard": round(v[0] / v[1], 4)}
                            for d, v in sorted(haz.items()) if v[1] >= 30}
    out["dwell_hazard_note"] = "h(d) = P(STATE_V2 changes at t+1 | dwell t = d). Monotone rise => dwell length alone predicts transition."

    # ---- early-warning models ----
    res = {}
    for h in HS:
        y = np.array([1 if (i + h < n and st[i + h] != st[i]) else 0 for i in range(n)], int)
        valid = np.array([i for i in range(n) if i + h < n and np.all(np.isfinite(X[i]))])
        base_only = wf_binary(X[valid], y[valid], valid)
        plus = wf_binary(Xs[valid], y[valid], valid)
        res[f"h={h}"] = {"base_rate": round(float(y[valid].mean()), 4), "features_only": base_only,
                          "plus_state_and_dwell": plus,
                          "incremental_dll": round((plus["dll"] or 0) - (base_only["dll"] or 0), 5)}
    out["early_warning"] = res

    # ---- acceptance ----
    best = None
    for k, v in res.items():
        h = int(k.split("=")[1])
        ok = (v["plus_state_and_dwell"]["dll"] >= FLOOR and (v["plus_state_and_dwell"]["auc"] or 0) >= 0.55
              and v["incremental_dll"] > 0)
        if ok and (best is None or v["plus_state_and_dwell"]["dll"] > res[f"h={best}"]["plus_state_and_dwell"]["dll"]):
            best = h
    out["BEST_LEAD_TIME"] = best
    out["VERDICT"] = "EARLY_WARNING_SURVIVES" if best is not None else "EARLY_WARNING_NOT_SUPPORTED"
    out["safety"] = {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                      "FROZEN_ARTIFACT_WRITE": 0, "ONTOLOGY_MODIFIED": 0, "PARAM_MODIFIED": 0, "FUTURE_RETURN_USED": "NO",
                      "PNL_USED": "NO", "WIN_RATE_USED": "NO"}
    outp = os.path.join(R1, "reports", "V1_R2_R1_PHASE4_TRANSITION_EARLY_WARNING.json")
    wjson(outp, out)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_4", "report": os.path.relpath(outp, REPO),
                              "verdict": out["VERDICT"], "preregistration_hash": pre_hash}, ensure_ascii=False) + "\n")
    print("WROTE", outp, "| VERDICT:", out["VERDICT"], "| BEST_LEAD:", best)
    print(json.dumps(out, ensure_ascii=False, default=str)[:3200])


if __name__ == "__main__":
    main()
