# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION — STAGE 1 (cache-based): §10 five models, §35 ablation,
§34 nulls, §30 splits, §31 effective_n, §32/33 concentration, §37 effect floor.

Reads states/state_v2_series.parquet (Stage 0). Return-free. Writes ONLY under v1_r2_full_optimization/."""
from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization")
LEDGER = os.path.join(ROOT, "ledger", "v1_r2_full_optimization_ledger.jsonl")
CACHE = os.path.join(ROOT, "states", "state_v2_series.parquet")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
COVER = [1.0, 0.9, 0.8, 0.7, 0.6]
FLOOR = 0.01
NPERM, BLOCK, MAXIT = 8, 48, 1200
FEATS = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]
MTFC = ["mtf_0", "mtf_1", "mtf_2", "mtf_3", "mtf_4", "mtf_5"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def ledger(phase, event, payload):
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["this_hash"]; seq += 1
    e = {"seq": seq + 1, "ts_utc": NOW, "phase": phase, "event": event, "payload_hash": sha_obj(payload), "prev_hash": prev}
    e["this_hash"] = sha_obj({k: v for k, v in e.items() if k != "this_hash"})
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")


def onehot(seq):
    lv = sorted(set(seq)); idx = {v: i for i, v in enumerate(lv)}
    M = np.zeros((len(seq), len(lv)))
    for i, v in enumerate(seq):
        M[i, idx[v]] = 1.0
    return M, lv


def fit_eval(Xtr, ytr, Xte, yte, binary=False):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=1.0, max_iter=MAXIT, solver="lbfgs", tol=1e-3).fit(sc.transform(Xtr), ytr)
    pr = clf.predict_proba(sc.transform(Xte)); cls = list(clf.classes_)
    if binary:
        p1 = np.clip(pr[:, 1], 1e-12, 1 - 1e-12); yb = yte.astype(int)
        ll = -np.mean(yb * np.log2(p1) + (1 - yb) * np.log2(1 - p1))
        b = np.clip(float(np.mean(ytr)), 1e-12, 1 - 1e-12)
        llb = -np.mean(yb * np.log2(b) + (1 - yb) * np.log2(1 - b))
        return {"dll": round(float(llb - ll), 5), "auc": round(float(roc_auc_score(yb, p1)), 4) if len(set(yb)) > 1 else None,
                 "n_test": int(len(yte))}
    ci = [cls.index(v) for v in yte]
    ll = -np.mean(np.log2(np.clip(pr[np.arange(len(yte)), ci], 1e-12, 1.0)))
    pri = np.array([np.mean(ytr == c) for c in cls])
    llb = -np.mean(np.log2(np.clip(pri[ci], 1e-12, 1.0)))
    pred = np.array([cls[i] for i in pr.argmax(axis=1)])
    maj = collections.Counter(ytr).most_common(1)[0][0]
    conf = pr.max(axis=1); corr = (pred == yte).astype(float)
    bn = np.clip((conf * 10).astype(int), 0, 9); ece = 0.0
    for b_ in range(10):
        m = bn == b_
        if m.sum():
            ece += (m.sum() / len(yte)) * abs(corr[m].mean() - conf[m].mean())
    order = np.argsort(-conf); sel = {}
    for cov in COVER:
        kk = max(1, int(len(yte) * cov)); ii = order[:kk]
        sel[f"cov_{int(cov*100)}"] = round(float(np.mean(pred[ii] == yte[ii])), 4)
    return {"dll": round(float(llb - ll), 5), "n_test": int(len(yte)), "accuracy": round(float(np.mean(pred == yte)), 4),
             "majority_accuracy": round(float(np.mean(yte == maj)), 4),
             "balanced_accuracy": round(float(balanced_accuracy_score(yte, pred)), 4),
             "macro_f1": round(float(f1_score(yte, pred, average="macro")), 4), "ECE": round(float(ece), 4),
             "per_class_recall": {c: round(float(np.mean(pred[np.array(yte) == c] == c)), 4) for c in cls if (np.array(yte) == c).sum() > 0},
             "selective_accuracy": sel}


def main():
    df = pd.read_parquet(CACHE)
    n = len(df)
    state = df["state"].tolist(); events = df["event"].tolist()
    dw = df["dwell"].to_numpy(float); nod8 = df["nod8"].to_numpy(float)
    Xp = df[FEATS].to_numpy(float); MTF = df[MTFC].to_numpy(float)
    ohS, lvS = onehot(state); ohE, lvE = onehot(events)
    evidx = {v: i for i, v in enumerate(lvE)}
    evhist = np.zeros((n, len(lvE) + 2))
    for i in range(n):
        w = events[max(0, i - 3):i + 1]
        for e_ in w:
            evhist[i, evidx[e_]] += 1.0 / len(w)
        evhist[i, -2] = sum(1 for e_ in w if e_ != "NONE") / len(w)
        evhist[i, -1] = 1.0 if (i and events[i] == events[i - 1]) else 0.0
    Y_state = np.array([state[i + H] if i + H < n else None for i in range(n)], dtype=object)
    Y_event = np.array([events[i + H] if i + H < n else None for i in range(n)], dtype=object)
    Y_change = np.array([1 if (i + H < n and state[i + H] != state[i]) else 0 for i in range(n)], int)
    ok = np.array([i for i in range(n) if Y_state[i] is not None and np.all(np.isfinite(Xp[i]))])
    split = int(n * 0.6); tr, te = ok < split, ok >= split
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION", "stage": "STATE_VS_EVENT_5MODELS", "ts_utc": NOW, "bars": n,
            "H": H, "n_train": int(tr.sum()), "n_test": int(te.sum()), "state_levels": lvS, "event_levels": lvE,
            "effect_floor_bits": FLOOR, "abstention_grid": COVER, "models": {}, "safety": {
                "ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                "V2_WRITE": 0, "V3_WRITE": 0, "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO"}}
    SH = np.hstack([ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1)])
    EH = np.hstack([ohE, evhist])
    M = {"M_A_STATE_FORECAST": (np.hstack([Xp, SH]), Y_state, False),
         "M_B_EVENT_FORECAST": (np.hstack([Xp, EH]), Y_event, False),
         "M_C_STATE_PLUS_EVENT": (np.hstack([Xp, SH, EH]), Y_state, False),
         "M_D_EVENT_SEQUENCE": (np.hstack([Xp, EH, ohE]), Y_event, False),
         "M_E_STATE_TRANSITION": (np.hstack([Xp, SH]), Y_change, True)}
    for k, (MM, Y, b) in M.items():
        X = MM[ok]
        r = fit_eval(X[tr], Y[ok][tr], X[te], Y[ok][te], binary=b); r["n_train"] = int(tr.sum())
        out["models"][k] = r
        print(k, "dll=", r["dll"], "acc=", r.get("accuracy"), "maj=", r.get("majority_accuracy"), "auc=", r.get("auc"), flush=True)
    wjson("reports/V1_R2_FULL_STAGE1_STATE_VS_EVENT.json", out)
    # ---- ablation (§35) ----
    ABL = {"A0_priors_only": np.zeros((n, 1)), "A1_candle_behavior": ohS, "A2_structure": Xp[:, [1, 6, 7]],
            "A3_momentum": Xp[:, [4, 5]], "A6_state_plus_dwell": SH, "A8_mtf_only": MTF,
            "A9_counter_evidence": np.hstack([nod8.reshape(-1, 1), EH]), "A10_full": np.hstack([Xp, SH, EH, MTF])}
    abl = {}
    for k, MM in ABL.items():
        if k == "A0_priors_only":
            abl[k] = 0.0; continue
        X = MM[ok]
        abl[k] = fit_eval(X[tr], Y_state[ok][tr], X[te], Y_state[ok][te])["dll"]
        print("abl", k, abl[k], flush=True)
    out["ablation_state_target"] = abl
    wjson("ablation/ABLATION_RESULTS.json", {"target": "STATE_V2(t+8)", "ladder": abl,
                                              "best": max(abl, key=lambda k: abl[k]),
                                              "increments_vs_A1": {k: round(abl[k] - abl["A1_candle_behavior"], 5) for k in abl},
                                              "ts_utc": NOW})
    wjson("reports/V1_R2_FULL_STAGE1_STATE_VS_EVENT.json", out)
    # ---- nulls (§34) on best state model ----
    bestk = "M_C_STATE_PLUS_EVENT"; Xb = M[bestk][0][ok]; Ys = Y_state[ok]
    rng = np.random.default_rng(20260927); nulls = {"label_shuffle": [], "time_shuffle": []}
    for _ in range(NPERM):
        p_ = rng.permutation(Ys); nulls["label_shuffle"].append(fit_eval(Xb[tr], p_[tr], Xb[te], p_[te])["dll"])
    for _ in range(NPERM):
        nb = len(Xb) // BLOCK + 1; s_ = rng.integers(0, max(1, len(Xb) - BLOCK), nb)
        p_ = np.concatenate([Ys[t_:t_ + BLOCK] for t_ in s_])[:len(Ys)]
        nulls["time_shuffle"].append(fit_eval(Xb[tr], p_[tr], Xb[te], p_[te])["dll"])
    out["nulls"] = {k: {"mean": round(float(np.mean(v)), 5), "p95": round(float(np.percentile(v, 95)), 5),
                          "max": round(float(np.max(v)), 5),
                          "empirical_p": round(float(np.mean(np.array(v) >= out["models"][bestk]["dll"])), 4)}
                     for k, v in nulls.items()}
    # ---- effective_n + concentration (§31/32/33) ----
    x = Y_change[ok].astype(float); x = x - x.mean(); d = (x * x).sum(); s = 0.0
    for k in range(1, 51):
        s += (1 - k / 51) * ((x[:-k] * x[k:]).sum() / d)
    ne = round(float(len(x) / max(1.0, 1 + 2 * s)), 2)
    days = np.array([str(pd.Timestamp(t).date()) for t in df["ts"].to_numpy()[ok]])
    clus = np.array([f"{str(pd.Timestamp(t).date())}-{'A' if pd.Timestamp(t).hour < 12 else 'B'}" for t in df["ts"].to_numpy()[ok]])
    cc = collections.Counter(clus); dc = collections.Counter(days)
    out["effective_n"] = {"raw_n": int(len(x)), "effective_n": ne, "autocorr_sum": round(float(s), 4),
                           "unique_days": len(dc), "unique_clusters": len(cc)}
    out["concentration"] = {"top5_cluster_share": round(sum(v for _, v in cc.most_common(5)) / len(clus), 4),
                             "top10_cluster_share": round(sum(v for _, v in cc.most_common(10)) / len(clus), 4),
                             "max_cluster_share": round(max(cc.values()) / len(clus), 4),
                             "max_day_share": round(max(dc.values()) / len(days), 4)}
    # ---- day / cluster holdout (§30) ----
    rngd = np.random.default_rng(7); ud = sorted(set(days)); hd = set(rngd.choice(ud, max(1, int(len(ud) * 0.3)), replace=False))
    dtr = np.array([d not in hd for d in days]); uc = sorted(set(clus)); hc = set(rngd.choice(uc, max(1, int(len(uc) * 0.3)), replace=False))
    ctr = np.array([c not in hc for c in clus])
    Xs = M["M_A_STATE_FORECAST"][0][ok]
    out["splits"] = {"time": out["models"]["M_A_STATE_FORECAST"],
                      "day_holdout": fit_eval(Xs[dtr], Y_state[ok][dtr], Xs[~dtr], Y_state[ok][~dtr]),
                      "cluster_holdout": fit_eval(Xs[ctr], Y_state[ok][ctr], Xs[~ctr], Y_state[ok][~ctr])}
    bd = out["models"][bestk]["dll"]
    out["effect_floor_check"] = {"best_model": bestk, "best_dll": bd, "floor": FLOOR, "PASSES_FLOOR": bool(bd >= FLOOR),
                                  "null_separated": bool(out["nulls"]["time_shuffle"]["empirical_p"] <= 0.05),
                                  "beats_majority": bool(out["models"]["M_A_STATE_FORECAST"]["accuracy"] > out["models"]["M_A_STATE_FORECAST"]["majority_accuracy"])}
    out["STAGE1_VERDICT"] = ("STATE_FORECAST_SUPPORTED" if all(out["effect_floor_check"][k] for k in ("PASSES_FLOOR", "null_separated", "beats_majority"))
                              else "STATE_FORECAST_UNSUPPORTED")
    p = wjson("reports/V1_R2_FULL_STAGE1_STATE_VS_EVENT.json", out)
    ledger("STAGE1", "state_vs_event_5models", {"verdict": out["STAGE1_VERDICT"], "best_dll": bd})
    print("VERDICT:", out["STAGE1_VERDICT"], flush=True)
    print("nulls:", json.dumps(out["nulls"], ensure_ascii=False), flush=True)
    print("effn:", json.dumps({**out["effective_n"], **out["concentration"]}, ensure_ascii=False), flush=True)
    print("splits:", json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("dll", "accuracy", "macro_f1")} for k, v in out["splits"].items()}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
