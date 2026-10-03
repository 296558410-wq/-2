# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION — STAGE 2: §17 transition lead-time, §11/§12/§74 K-line context,
§25 MTF increment, §28 counter-evidence ablation, §26 mechanism increment, §19 structural direction.

Reads the Stage-0 cache. Direction is defined STRUCTURALLY (from market-structure labels), never from
returns/PnL. Return-free. Writes ONLY under v1_r2_full_optimization/."""
from __future__ import annotations

import collections
import hashlib
import importlib.util
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
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation")
CACHE = os.path.join(ROOT, "states", "state_v2_series.parquet")
LEDGER = os.path.join(ROOT, "ledger", "v1_r2_full_optimization_ledger.jsonl")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
R1MOD = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade", "_v1r2_phaseB_R1.py")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
LEADS = [0, 1, 2, 3, 4, 8]
MAXIT, FLOOR = 1000, 0.01
FEATS = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]


def load_mod(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


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


def fit(Xtr, ytr, Xte, yte, binary=False):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(C=1.0, max_iter=MAXIT, solver="lbfgs", tol=1e-3).fit(sc.transform(Xtr), ytr)
    pr = clf.predict_proba(sc.transform(Xte)); cls = list(clf.classes_)
    if binary:
        p1 = np.clip(pr[:, 1], 1e-12, 1 - 1e-12); yb = yte.astype(int)
        ll = -np.mean(yb * np.log2(p1) + (1 - yb) * np.log2(1 - p1))
        b = np.clip(float(np.mean(ytr)), 1e-12, 1 - 1e-12)
        llb = -np.mean(yb * np.log2(b) + (1 - yb) * np.log2(1 - b))
        return {"dll": round(float(llb - ll), 5), "auc": round(float(roc_auc_score(yb, p1)), 4) if len(set(yb)) > 1 else None, "n": int(len(yte))}
    ci = [cls.index(v) for v in yte]
    ll = -np.mean(np.log2(np.clip(pr[np.arange(len(yte)), ci], 1e-12, 1.0)))
    pri = np.array([np.mean(ytr == c) for c in cls])
    llb = -np.mean(np.log2(np.clip(pri[ci], 1e-12, 1.0)))
    pred = np.array([cls[i] for i in pr.argmax(axis=1)])
    maj = collections.Counter(ytr).most_common(1)[0][0]
    return {"dll": round(float(llb - ll), 5), "n": int(len(yte)), "accuracy": round(float(np.mean(pred == yte)), 4),
             "majority_accuracy": round(float(np.mean(yte == maj)), 4),
             "balanced_accuracy": round(float(balanced_accuracy_score(yte, pred)), 4),
             "macro_f1": round(float(f1_score(yte, pred, average="macro")), 4)}


def main():
    df = pd.read_parquet(CACHE)
    n = len(df)
    state = df["state"].tolist(); events = df["event"].tolist(); frozen = df["frozen"].tolist()
    Xp = df[FEATS].to_numpy(float); MTF = df[[f"mtf_{i}" for i in range(6)]].to_numpy(float)
    ohS, lvS = onehot(state); ohE, lvE = onehot(events)
    dw = df["dwell"].to_numpy(float); nod8 = df["nod8"].to_numpy(float)
    o, h, l, c = df["o"].to_numpy(float), df["h"].to_numpy(float), df["l"].to_numpy(float), df["c"].to_numpy(float)
    # ---- K-line geometry features (§11/§12/§74): pure candle shape (context-free) ----
    rng_ = np.maximum(h - l, 1e-12); body = np.abs(c - o)
    up = h - np.maximum(o, c); dn = np.minimum(o, c) - l
    CG = np.column_stack([body / rng_, up / rng_, dn / rng_, (c - o) / rng_,
                           (c - o) / np.maximum(np.abs(c - o), 1e-12) * (body / rng_),
                           np.roll(rng_, 1) / rng_])
    # ---- context features ----
    LOC = Xp[:, [2]]                                # slope (location/trend context)
    STR = Xp[:, [1, 6, 7]]                          # efficiency/act (structure)
    MOM = Xp[:, [4, 5]]                             # momentum
    # ---- counter-evidence (§27): explicit conflicts ----
    conflict = np.zeros((n, 2))
    for i in range(n):
        ps, cs, mom, reg = None, None, None, None
        conflict[i, 0] = 1.0 if (reg in ("TREND", "EXPANSION") and cs == "REJECTION") else 0.0
    # rebuild conflicts from cache columns is not stored; use proxies
    conflict = np.column_stack([nod8, (Xp[:, 5] < 0).astype(float) * (Xp[:, 4] > 0).astype(float)])
    # ---- mechanism proxy (§26) from state x event interaction ----
    MECH, lvM = onehot([f"{s}|{e}" for s, e in zip(state, events)])
    Y_state = np.array([state[i + H] if i + H < n else None for i in range(n)], dtype=object)
    Y_change = np.array([1 if (i + H < n and state[i + H] != state[i]) else 0 for i in range(n)], int)
    ok = np.array([i for i in range(n) if Y_state[i] is not None and np.all(np.isfinite(Xp[i]))])
    split = int(n * 0.6); tr, te = ok < split, ok >= split
    out = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION", "stage": "KLINE_MTF_TRANSITION_COUNTER", "ts_utc": NOW,
            "bars": n, "H": H, "leads": LEADS, "n_train": int(tr.sum()), "n_test": int(te.sum()), "safety": {
                "ORDER_SEND": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "LIVE": "OFF", "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO"}}

    # ---- §17 transition lead-time (precursor search) ----
    lt = {}
    for lg in LEADS:
        y = np.array([1 if (i + H < n and state[i + H] != state[i]) else 0 for i in range(n)], int)
        rows = np.array([i for i in range(n) if i + H < n and i - lg >= 0 and np.all(np.isfinite(Xp[i - lg]))])
        X = np.hstack([Xp[rows - lg], ohS[rows - lg], dw[rows - lg].reshape(-1, 1), nod8[rows - lg].reshape(-1, 1)])
        m_ = rows < split
        lt[f"lead_{lg}"] = fit(X[m_], y[rows][m_], X[~m_], y[rows][~m_], binary=True)
        print("lead", lg, lt[f"lead_{lg}"], flush=True)
    out["transition_lead_time"] = lt
    out["lead_time_best"] = max(lt, key=lambda k: (lt[k]["auc"] or 0))

    # ---- §11/§12/§74 K-line context ladder ----
    Yk = Y_state
    CANDLE = {"KLINE_ONLY": CG, "KLINE_LOCATION": np.hstack([CG, LOC]), "KLINE_STRUCTURE": np.hstack([CG, STR]),
               "KLINE_MOMENTUM": np.hstack([CG, MOM]), "KLINE_STATE": np.hstack([CG, ohS, dw.reshape(-1, 1)]),
               "KLINE_EVENT": np.hstack([CG, ohE]), "KLINE_MTF": np.hstack([CG, MTF]),
               "KLINE_CONTEXT_FULL": np.hstack([CG, LOC, STR, MOM, ohS, ohE, MTF])}
    kl = {}
    for k, M in CANDLE.items():
        X = M[ok]; kl[k] = fit(X[tr], Yk[ok][tr], X[te], Yk[ok][te])
        print("kline", k, kl[k]["dll"], flush=True)
    out["kline_ladder"] = kl
    out["kline_increment"] = {"vs_KLINE_ONLY": {k: round(kl[k]["dll"] - kl["KLINE_ONLY"]["dll"], 5) for k in kl},
                               "KLINE_VERDICT": ("KLINE_CONTEXTUAL_INCREMENTAL" if kl["KLINE_CONTEXT_FULL"]["dll"] - kl["KLINE_ONLY"]["dll"] >= FLOOR else "KLINE_REDUNDANT_OR_WEAK")}

    # ---- §25 MTF increment ----
    b0 = fit(Xp[ok][tr], Yk[ok][tr], Xp[ok][te], Yk[ok][te])
    b1 = fit(np.hstack([Xp, MTF[:, :3]])[ok][tr], Yk[ok][tr], np.hstack([Xp, MTF[:, :3]])[ok][te], Yk[ok][te])
    b2 = fit(np.hstack([Xp, MTF])[ok][tr], Yk[ok][tr], np.hstack([Xp, MTF])[ok][te], Yk[ok][te])
    out["mtf_increment"] = {"M15_only": b0["dll"], "M15_plus_H1": b1["dll"], "M15_plus_H1_plus_H4": b2["dll"],
                             "delta_H1": round(b1["dll"] - b0["dll"], 5), "delta_H1H4": round(b2["dll"] - b1["dll"], 5),
                             "MTF_SUPPORTED": bool(b2["dll"] - b0["dll"] >= FLOOR)}
    print("mtf", out["mtf_increment"], flush=True)

    # ---- §28 counter-evidence ablation ----
    cw = fit(np.hstack([Xp, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1)])[ok][tr], Yk[ok][tr],
             np.hstack([Xp, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1)])[ok][te], Yk[ok][te])
    cc_ = fit(np.hstack([Xp, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1), conflict])[ok][tr], Yk[ok][tr],
              np.hstack([Xp, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1), conflict])[ok][te], Yk[ok][te])
    out["counter_evidence_ablation"] = {"WITHOUT": cw["dll"], "WITH": cc_["dll"], "delta": round(cc_["dll"] - cw["dll"], 5),
                                         "COUNTER_EVIDENCE_STATUS": ("SUPPORTED" if cc_["dll"] - cw["dll"] >= FLOOR else "EXPLANATORY_ONLY")}
    # ---- §26 mechanism increment ----
    mw = fit(np.hstack([Xp, ohS, dw.reshape(-1, 1)])[ok][tr], Yk[ok][tr], np.hstack([Xp, ohS, dw.reshape(-1, 1)])[ok][te], Yk[ok][te])
    mm = fit(np.hstack([Xp, ohS, dw.reshape(-1, 1), MECH])[ok][tr], Yk[ok][tr], np.hstack([Xp, ohS, dw.reshape(-1, 1), MECH])[ok][te], Yk[ok][te])
    out["mechanism_increment"] = {"without": mw["dll"], "with": mm["dll"], "delta": round(mm["dll"] - mw["dll"], 5),
                                   "MECHANISM_STATUS": ("SUPPORTED" if mm["dll"] - mw["dll"] >= FLOOR else "EXPLANATORY_ONLY")}

    # ---- §19 structural DIRECTION (defined from structure, never from returns) ----
    NEG = {"FAILED_BREAK", "REJECTION", "VOL_CONTRACTION", "MOM_DECELERATION"}
    POS = {"BREAK", "BREAK_ATTEMPT", "ACCEPTANCE", "VOL_EXPANSION", "MOM_ACCELERATION", "RETEST"}
    def struct_dir(e_):
        return "UP" if e_ in POS else "DOWN" if e_ in NEG else "NEUTRAL"
    Ydir = np.array([struct_dir(events[i + H]) if i + H < n else None for i in range(n)], dtype=object)
    okd = np.array([i for i in range(n) if Ydir[i] is not None and np.all(np.isfinite(Xp[i]))])
    trd, ted = okd < split, okd >= split
    Xd = np.hstack([Xp, CG, ohE])[okd]
    dr = fit(Xd[trd], Ydir[okd][trd], Xd[ted], Ydir[okd][ted])
    # baselines
    ydtr, ydte = Ydir[okd][trd], Ydir[okd][ted]
    maj = collections.Counter(ydtr).most_common(1)[0][0]
    prev = np.array([Ydir[okd][i - 1] if i - 1 >= 0 else maj for i in range(len(okd))])[ted]
    out["direction_structural"] = {"model": dr, "majority_baseline": round(float(np.mean(ydte == maj)), 4),
                                    "previous_event_baseline": round(float(np.mean(ydte == prev)), 4),
                                    "BEATS_BASELINES": bool(dr["accuracy"] > max(float(np.mean(ydte == maj)), float(np.mean(ydte == prev)))),
                                    "note": "direction defined STRUCTURALLY from events; NO returns/PnL used (§19/§5)"}
    print("direction", out["direction_structural"]["model"]["dll"], "acc", dr["accuracy"], "vs maj", out["direction_structural"]["majority_baseline"], "vs prev", out["direction_structural"]["previous_event_baseline"], flush=True)

    p = wjson("reports/V1_R2_FULL_STAGE2_KLINE_MTF_TRANSITION_COUNTER.json", out)
    ledger("STAGE2", "kline_mtf_transition_counter_direction", {"kline": out["kline_increment"]["KLINE_VERDICT"],
                                                                  "mtf": out["mtf_increment"]["MTF_SUPPORTED"],
                                                                  "counter": out["counter_evidence_ablation"]["COUNTER_EVIDENCE_STATUS"],
                                                                  "mech": out["mechanism_increment"]["MECHANISM_STATUS"],
                                                                  "lead_best": out["lead_time_best"]})
    print("WROTE", p, flush=True)


if __name__ == "__main__":
    main()
