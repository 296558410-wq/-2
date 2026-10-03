# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION — STAGE 3: §18 forecast decomposition (STATE / TRANSITION / EVENT /
DIRECTION / HORIZON / INVALIDATION), §22/§23 abstention, §63/§64 final blind, §49 forecast record,
§51/§53/§85 strategy mapping. Reads the Stage-0 cache. Return-free. Writes ONLY under the canonical tree."""
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
CACHE = os.path.join(ROOT, "states", "state_v2_series.parquet")
LEDGER = os.path.join(ROOT, "ledger", "v1_r2_full_optimization_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
MAXIT, FLOOR = 1000, 0.01
COVER = [1.0, 0.9, 0.8, 0.7, 0.6]
FEATS = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]
FAM = {"TREND": "DIR", "EXPANSION": "DIR", "BREAKOUT_CONFIRMATION": "DIR", "BREAKOUT_ATTEMPT": "DIR", "ACCEPTANCE": "DIR",
        "COMPRESSION": "BAL", "RANGE": "BAL", "ROTATION": "BAL",
        "REJECTION": "NEG", "FAILED_BREAK": "NEG", "DECELERATION": "BAL", "NO_DEFINED_STATE": "UNK"}


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


def fitpred(Xtr, ytr, Xte, binary=False):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=1.0, max_iter=MAXIT, solver="lbfgs", tol=1e-3).fit(sc.transform(Xtr), ytr)
    pr = clf.predict_proba(sc.transform(Xte))
    return clf, pr


def metrics_multiclass(clf, pr, ytr, yte):
    cls = list(clf.classes_); ci = [cls.index(v) for v in yte]
    ll = -np.mean(np.log2(np.clip(pr[np.arange(len(yte)), ci], 1e-12, 1.0)))
    pri = np.array([np.mean(ytr == c) for c in cls])
    llb = -np.mean(np.log2(np.clip(pri[ci], 1e-12, 1.0)))
    pred = np.array([cls[i] for i in pr.argmax(axis=1)])
    maj = collections.Counter(ytr).most_common(1)[0][0]
    conf = pr.max(axis=1)
    sel = {}
    order = np.argsort(-conf)
    for cov in COVER:
        kk = max(1, int(len(yte) * cov)); ii = order[:kk]
        sel[f"cov_{int(cov*100)}"] = {"coverage": round(kk / len(yte), 3), "accuracy": round(float(np.mean(pred[ii] == yte[ii])), 4)}
    return {"dll": round(float(llb - ll), 5), "accuracy": round(float(np.mean(pred == yte)), 4),
             "majority_accuracy": round(float(np.mean(yte == maj)), 4),
             "balanced_accuracy": round(float(balanced_accuracy_score(yte, pred)), 4),
             "macro_f1": round(float(f1_score(yte, pred, average="macro")), 4),
             "selective": sel, "abstention_rate_at_0.5": round(float(np.mean(conf < 0.5)), 4),
             "accuracy_on_emitted": round(float(np.mean(pred[conf >= 0.5] == yte[conf >= 0.5])), 4) if (conf >= 0.5).sum() else None,
             "coverage_at_0.5": round(float(np.mean(conf >= 0.5)), 4)}


def main():
    reg = json.load(open(os.path.join(ROOT, "registry", "registry.json"), encoding="utf-8"))
    RH, CH = reg["registry_hash"], reg["context_hash"]
    df = pd.read_parquet(CACHE)
    n = len(df)
    state = df["state"].tolist(); events = df["event"].tolist()
    Xp = df[FEATS].to_numpy(float)
    ohS, lvS = onehot(state); ohE, lvE = onehot(events)
    dw = df["dwell"].to_numpy(float); nod8 = df["nod8"].to_numpy(float)
    SH = np.hstack([ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1)])
    # families
    fam = [FAM.get(s, "UNK") for s in state]
    # horizon bucket: first change within 1/2/4/8/16 bars
    def bucket(i):
        for b in (1, 2, 4, 8, 16):
            if i + b < n and state[i + b] != state[i]:
                return f"<= {b}"
        return "> 16"
    Y_state = np.array([state[i + H] if i + H < n else None for i in range(n)], dtype=object)
    Y_event = np.array([events[i + H] if i + H < n else None for i in range(n)], dtype=object)
    Y_chg = np.array([1 if (i + H < n and state[i + H] != state[i]) else 0 for i in range(n)], int)
    Y_hz = np.array([bucket(i) if i + 16 < n else None for i in range(n)], dtype=object)
    Y_inv = np.array([1 if (i + H < n and FAM.get(state[i + H], "UNK") != FAM.get(state[i], "UNK")) else 0 for i in range(n)], int)
    NEG = {"FAILED_BREAK", "REJECTION", "VOL_CONTRACTION", "MOM_DECELERATION"}
    POS = {"BREAK", "BREAK_ATTEMPT", "ACCEPTANCE", "VOL_EXPANSION", "MOM_ACCELERATION", "RETEST"}
    sd = lambda e_: "UP" if e_ in POS else "DOWN" if e_ in NEG else "NEUTRAL"
    Y_dir = np.array([sd(events[i + H]) if i + H < n else None for i in range(n)], dtype=object)
    # feature sets
    o, h, l, c = df["o"].to_numpy(float), df["h"].to_numpy(float), df["l"].to_numpy(float), df["c"].to_numpy(float)
    rng_ = np.maximum(h - l, 1e-12); body = np.abs(c - o); up = h - np.maximum(o, c); dn = np.minimum(o, c) - l
    CG = np.column_stack([body / rng_, up / rng_, dn / rng_, (c - o) / rng_])
    MTF = df[[f"mtf_{i}" for i in range(6)]].to_numpy(float)
    XF = np.hstack([Xp, CG, SH, ohE, MTF])
    split = int(n * 0.6)
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION", "stage": "FORECAST_DECOMPOSITION_BLIND_STRATEGY",
            "ts_utc": NOW, "bars": n, "H": H, "blind_split": "single 60/40 freeze", "registry_hash": RH, "context_hash": CH,
            "targets": {}, "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF",
                                       "LIVE": "OFF", "V2_WRITE": 0, "V3_WRITE": 0, "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO", "WIN_RATE_USED": "NO"}}

    def run(name, Y, M=None, binary=False):
        MM = XF if M is None else M
        ok = np.array([i for i in range(n) if Y[i] is not None and np.all(np.isfinite(MM[i]))])
        tr, te = ok < split, ok >= split
        X = MM[ok]
        if binary:
            clf, pr = fitpred(X[tr], Y[ok][tr], X[te], binary=True)
            p1 = np.clip(pr[:, 1], 1e-12, 1 - 1e-12); yb = Y[ok][te].astype(int)
            ll = -np.mean(yb * np.log2(p1) + (1 - yb) * np.log2(1 - p1))
            b = np.clip(float(np.mean(Y[ok][tr])), 1e-12, 1 - 1e-12)
            llb = -np.mean(yb * np.log2(b) + (1 - yb) * np.log2(1 - b))
            r = {"dll": round(float(llb - ll), 5), "auc": round(float(roc_auc_score(yb, p1)), 4),
                  "abstention_rate_at_0.5": round(float(np.mean(np.maximum(p1, 1 - p1) < 0.5)), 4), "n_test": int(te.sum())}
        else:
            clf, pr = fitpred(X[tr], Y[ok][tr], X[te])
            r = metrics_multiclass(clf, pr, Y[ok][tr], Y[ok][te]); r["n_test"] = int(te.sum())
            if name == "DIRECTION":
                maj = collections.Counter(Y[ok][tr]).most_common(1)[0][0]
                prev = np.array([Y[ok][i - 1] if i - 1 >= 0 else maj for i in range(len(ok))])[te]
                r["majority_baseline"] = round(float(np.mean(Y[ok][te] == maj)), 4)
                r["previous_baseline"] = round(float(np.mean(Y[ok][te] == prev)), 4)
                r["BEATS_BASELINES"] = bool(r["accuracy"] > max(r["majority_baseline"], r["previous_baseline"]))
        out["targets"][name] = r
        print(name, json.dumps(r, ensure_ascii=False)[:260], flush=True)
        return ok, tr, te

    run("STATE_FORECAST", Y_state)
    run("TRANSITION_FORECAST", Y_chg, binary=True)
    run("EVENT_FORECAST", Y_event)
    run("DIRECTION_FORECAST", Y_dir)
    run("HORIZON_FORECAST", Y_hz)
    run("INVALIDATION_FORECAST", Y_inv, binary=True)

    # ---- §63/§64 final blind verdict per target ----
    dec = {}
    for k, v in out["targets"].items():
        if "auc" in v:
            dec[k] = "SUPPORTED" if (v["dll"] >= FLOOR and (v["auc"] or 0) >= 0.55) else ("INCONCLUSIVE" if v["dll"] > 0 else "UNSUPPORTED")
        else:
            dec[k] = "SUPPORTED" if (v["dll"] >= FLOOR and v["accuracy"] > v["majority_accuracy"]) else ("INCONCLUSIVE" if v["dll"] > 0 else "UNSUPPORTED")
    out["blind_decisions"] = dec
    out["MARKET_READING"] = "SUPPORTED" if dec["STATE_FORECAST"] == "SUPPORTED" else "UNSUPPORTED"
    out["TRANSITION_PREDICTION"] = dec["TRANSITION_FORECAST"]
    out["NEXT_STATE_FORECAST"] = dec["STATE_FORECAST"]
    out["DIRECTION_PREDICTION"] = dec["DIRECTION_FORECAST"]
    out["TIMING_PREDICTION"] = dec["HORIZON_FORECAST"]
    out["INVALIDATION"] = dec["INVALIDATION_FORECAST"]
    wjson("blind_validation/BLIND_RESULTS.json", out)

    # ---- §49 forecast record (blind test bars) ----
    okS = np.array([i for i in range(n) if Y_state[i] is not None and np.all(np.isfinite(XF[i]))])
    trS, teS = okS < split, okS >= split
    clfS, prS = fitpred(XF[okS][trS], Y_state[okS][trS], XF[okS][teS])
    clfC, prC = fitpred(XF[okS][trS], Y_chg[okS][trS], XF[okS][teS], binary=True)
    clfI, prI = fitpred(XF[okS][trS], Y_inv[okS][trS], XF[okS][teS], binary=True)
    clsS = list(clfS.classes_)
    fp = os.path.join(ROOT, "forecast", "V1_R2_FULL_FORECAST_RECORD.jsonl")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    idxs = okS[teS]
    with open(fp, "w", encoding="utf-8", newline="\n") as fh:
        for j, i in enumerate(idxs):
            pS = prS[j]; top = np.argsort(-pS)[:3]
            conf = float(pS.max()); pch = float(np.clip(prC[j, 1], 0, 1)); pinv = float(np.clip(prI[j, 1], 0, 1))
            abst = conf < 0.5
            fh.write(json.dumps({
                "timestamp": df["ts"].iloc[i], "market_context": state[i], "current_state": state[i],
                "active_events": [events[i]], "transition_status": ("TRANSITION_BUILDING" if pch >= 0.6 else "STATE_STABLE"),
                "forecast_horizon": H, "forecast_target": "STATE_V2",
                "forecast_distribution": {clsS[int(t)]: round(float(pS[int(t)]), 4) for t in top},
                "confidence": round(conf, 4), "counter_evidence": (["AMBIGUITY_RATE_HIGH"] if nod8[i] >= 0.5 else []),
                "invalidation": round(pinv, 4), "abstain_reason": ("LOW_CONFIDENCE" if abst else None),
                "data_quality": "DERIVED", "semantic_dependencies": ["C1_MARKET_BEHAVIOR_ONTOLOGY", "STATE_V2_K2"],
                "registry_hash": RH, "context_hash": CH}, ensure_ascii=False) + "\n")
    rec = {"artifact": os.path.relpath(fp, REPO), "rows": int(len(idxs)), "coverage_at_0.5": out["targets"]["STATE_FORECAST"]["coverage_at_0.5"],
            "accuracy_on_emitted": out["targets"]["STATE_FORECAST"]["accuracy_on_emitted"], "schema": ["timestamp", "market_context",
            "current_state", "active_events", "transition_status", "forecast_horizon", "forecast_target", "forecast_distribution",
            "confidence", "counter_evidence", "invalidation", "abstain_reason", "data_quality", "semantic_dependencies", "registry_hash", "context_hash"],
            "no_trading_fields": True}
    wjson("forecast/FORECAST_RECORD_META.json", rec)

    # ---- §51/§53/§85 strategy mapping (gated) ----
    POST = collections.Counter()
    for j, i in enumerate(idxs):
        s = state[i]; conf = float(prS[j].max()); pch = float(np.clip(prC[j, 1], 0, 1))
        if conf < 0.5:
            p = "WAIT_ABSTAIN"
        elif pch >= 0.6:
            p = "WAIT_TRANSITION"
        elif FAM.get(s) == "DIR":
            p = "TREND_FAMILY"
        elif FAM.get(s) == "BAL":
            p = "GRID_MEAN_REVERSION"
        else:
            p = "NO_TRADE_AMBIGUOUS"
        POST[p] += 1
    tot = sum(POST.values())
    gate = out["MARKET_READING"] == "SUPPORTED"
    sm = {"gate": "OPEN" if gate else "BLOCKED", "rule": "§85: mapping only if forecast SUPPORTED",
           "postures": {k: {"n": v, "share": round(v / tot, 4)} for k, v in POST.most_common()},
           "candidate_families": sorted(set(POST)), "note": "RESEARCH ONLY; no PnL/win-rate used; no trading fields; not executed"}
    wjson("strategy_mapping/STRATEGY_MAPPING.json", sm)
    out["strategy_mapping"] = {"gate": sm["gate"], "postures": sm["postures"]}
    out["forecast_record"] = rec
    p = wjson("reports/V1_R2_FULL_STAGE3_FORECAST_BLIND_STRATEGY.json", out)
    ledger("STAGE3", "forecast_decomposition_blind_strategy", {"blind_decisions": dec, "market_reading": out["MARKET_READING"],
                                                                "strategy_gate": sm["gate"]})
    print("BLIND:", json.dumps(dec, ensure_ascii=False), flush=True)
    print("STRATEGY GATE:", sm["gate"], flush=True)
    print("WROTE", p, flush=True)


if __name__ == "__main__":
    main()
