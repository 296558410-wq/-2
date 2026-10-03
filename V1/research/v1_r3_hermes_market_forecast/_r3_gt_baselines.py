# -*- coding: utf-8 -*-
"""V1-R3 — GROUND TRUTH + FROZEN BASELINES + INFORMATION-CONTENT ABLATION MATRIX (§28, §30, §87, §109).

Ground truth is produced by this INDEPENDENT module and is NEVER fed to Hermes.
Baselines are evaluated BOTH on the whole blind window and on the same 20 blind sample points Hermes sees.
Cross-market variants use a window-internal time split (cross-market coverage starts 2026-07-16). Writes under R3 only.
"""
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
from sklearn.metrics import f1_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
CACHE = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization", "states", "state_v2_series.parquet")
XS = os.path.join(REPO, "research", "v3_crossmarket_sources")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
DEV_END = pd.Timestamp("2026-06-01T00:00Z")
CM_START = pd.Timestamp("2026-07-16T00:00Z")
FLOOR = 0.01
FAM = {"TREND": "DIR", "EXPANSION": "DIR", "BREAKOUT_CONFIRMATION": "DIR", "BREAKOUT_ATTEMPT": "DIR", "ACCEPTANCE": "DIR",
        "COMPRESSION": "BAL", "RANGE": "BAL", "ROTATION": "BAL", "REJECTION": "NEG", "FAILED_BREAK": "NEG",
        "DECELERATION": "BAL", "NO_DEFINED_STATE": "UNK"}
NEG = {"FAILED_BREAK", "REJECTION", "VOL_CONTRACTION", "MOM_DECELERATION"}
POS = {"BREAK", "BREAK_ATTEMPT", "ACCEPTANCE", "VOL_EXPANSION", "MOM_ACCELERATION", "RETEST"}
FEATS = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def onehot(seq):
    lv = sorted(set(seq)); ix = {v: i for i, v in enumerate(lv)}
    M = np.zeros((len(seq), len(lv)))
    for i, v in enumerate(seq):
        M[i, ix[v]] = 1.0
    return M, lv


def metrics(ytr, yte, pred, prob=None, cls=None):
    maj = collections.Counter(ytr).most_common(1)[0][0]
    out = {"n": int(len(yte)), "accuracy": round(float(np.mean(pred == yte)), 4),
            "majority_accuracy": round(float(np.mean(yte == maj)), 4),
            "balanced_accuracy": round(float(balanced_accuracy_score(yte, pred)), 4),
            "macro_f1": round(float(f1_score(yte, pred, average="macro")), 4)}
    if prob is not None and cls is not None:
        ci = [list(cls).index(v) for v in yte]
        ll = -np.mean(np.log2(np.clip(prob[np.arange(len(yte)), ci], 1e-12, 1.0)))
        pri = np.array([np.mean(ytr == c) for c in cls])
        llb = -np.mean(np.log2(np.clip(pri[ci], 1e-12, 1.0)))
        conf = prob.max(axis=1); corr = (pred == yte).astype(float)
        bn = np.clip((conf * 10).astype(int), 0, 9); ece = 0.0
        for b in range(10):
            m = bn == b
            if m.sum():
                ece += (m.sum() / len(yte)) * abs(corr[m].mean() - conf[m].mean())
        out.update({"dll": round(float(llb - ll), 5), "log_loss_bits": round(float(ll), 5), "ECE": round(float(ece), 4),
                     "coverage_at_0.5": round(float(np.mean(conf >= 0.5)), 4),
                     "accuracy_on_covered": round(float(np.mean(pred[conf >= 0.5] == yte[conf >= 0.5])), 4) if (conf >= 0.5).sum() else None})
    return out


def main():
    df = pd.read_parquet(CACHE)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    n = len(df)
    state = df["state"].tolist(); events = df["event"].tolist()
    ts = df["ts"]
    sd = lambda e_: "UP" if e_ in POS else "DOWN" if e_ in NEG else "NEUTRAL"

    def bucket(i):
        for b in (1, 2, 4, 8, 16):
            if i + b < n and state[i + b] != state[i]:
                return f"<= {b}"
        return "> 16"

    gt = []
    for i in range(n - 16):
        gt.append({"idx": i, "ts": str(ts.iloc[i]), "state_now": state[i], "ACTUAL_NEXT_STATE": state[i + H],
                    "ACTUAL_TRANSITION": int(state[i + H] != state[i]), "ACTUAL_DIRECTION": sd(events[i + H]),
                    "ACTUAL_TIMING": bucket(i),
                    "ACTUAL_INVALIDATION": int(FAM.get(state[i + H], "UNK") != FAM.get(state[i], "UNK"))})
    gtdf = pd.DataFrame(gt)
    wjson("evaluation/GROUND_TRUTH_META.json", {"rows": len(gtdf), "H": H,
                                                 "generator": "independent module (never fed to Hermes)",
                                                 "targets": ["ACTUAL_NEXT_STATE", "ACTUAL_TRANSITION", "ACTUAL_DIRECTION", "ACTUAL_TIMING", "ACTUAL_INVALIDATION"],
                                                 "hash": sha_obj(gt[:3000]), "ts_utc": NOW})
    samp = json.load(open(os.path.join(ROOT, "context", "CONTEXT_SAMPLE_INDEX.json"), encoding="utf-8"))["sample_timestamps"]
    sidx = []
    for s in samp:
        m = df.index[ts <= pd.Timestamp(s)]
        if len(m):
            sidx.append(int(m[-1]))
    gt_s = gtdf[gtdf["idx"].isin(sidx)].to_dict("records")
    wjson("evaluation/GROUND_TRUTH_BLIND_SAMPLE.json", {"points": gt_s, "n": len(gt_s), "H": H, "note": "EVALUATOR ONLY — never passed to Hermes"})

    # ---- features ----
    Xp = df[FEATS].to_numpy(float); MTF = df[[f"mtf_{i}" for i in range(6)]].to_numpy(float)
    ohS, _ = onehot(state); ohE, _ = onehot(events)
    dw = df["dwell"].to_numpy(float); nod8 = df["nod8"].to_numpy(float)
    o, h, l, c = df["o"].to_numpy(float), df["h"].to_numpy(float), df["l"].to_numpy(float), df["c"].to_numpy(float)
    rng_ = np.maximum(h - l, 1e-12); body = np.abs(c - o)
    KL = np.column_stack([body / rng_, (h - np.maximum(o, c)) / rng_, (np.minimum(o, c) - l) / rng_, (c - o) / rng_])
    MECH, _ = onehot([f"{s}|{e}" for s, e in zip(state, events)])
    xc = {}
    for name, f in (("DXY", "series_DXY_5m"), ("VIX", "series_VIX_5m"), ("TNX", "series_UST10Y_PROXY_TNX_5m")):
        try:
            s = pd.read_parquet(os.path.join(XS, f + ".parquet")); s.index = pd.to_datetime(s.index, utc=True)
            s = s["close"].astype(float).sort_index().reindex(ts, method="ffill")
            xc[name] = (s.diff(8).to_numpy(float), s.to_numpy(float))
        except Exception:  # noqa: BLE001
            xc[name] = (np.full(n, np.nan), np.full(n, np.nan))
    XCM = np.column_stack([xc[k][0] for k in xc] + [xc[k][1] for k in xc])
    Y = np.array([state[i + H] if i + H < n else None for i in range(n)], dtype=object)
    valid = np.array([i for i in range(n) if Y[i] is not None and np.all(np.isfinite(Xp[i]))])
    is_dev = np.array([ts.iloc[i] < DEV_END for i in valid])
    dev_all, bl_all = valid[is_dev], valid[~is_dev]
    out = {"task": "V1_R3_HERMES_MARKET_FORECAST_ENGINE", "stage": "GT_BASELINES_ABLATION", "ts_utc": NOW, "H": H,
            "n_dev_full": int(len(dev_all)), "n_blind_full": int(len(bl_all)), "n_blind_sample": len(sidx),
            "crossmarket_start": str(CM_START), "effect_floor_bits": FLOOR,
            "safety": {"ORDER_SEND": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "LIVE": "OFF", "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO"}}

    def fit_eval(M, devi, bli):
        fin = np.all(np.isfinite(M), axis=1)
        d, b = [i for i in devi if fin[i]], [i for i in bli if fin[i]]
        if len(d) < 150 or len(b) < 20 or len(set(Y[d])) < 2:
            return {"status": "INSUFFICIENT_COVERAGE", "n_dev": len(d), "n_blind": len(b)}
        sc = StandardScaler().fit(M[d]); clf = LogisticRegression(C=1.0, max_iter=1500, solver="lbfgs", tol=1e-3)
        clf.fit(sc.transform(M[d]), Y[d])
        pr = clf.predict_proba(sc.transform(M[b])); cls = list(clf.classes_)
        pred = np.array([cls[i] for i in pr.argmax(axis=1)])
        return metrics(Y[d], Y[b], pred, pr, cls)

    # ---- baselines (main split) ----
    b0 = {}
    b0["MAJORITY"] = metrics(Y[dev_all], Y[bl_all], np.array([collections.Counter(Y[dev_all]).most_common(1)[0][0]] * len(bl_all)))
    b0["PERSISTENCE"] = metrics(Y[dev_all], Y[bl_all], np.array([state[i] for i in bl_all]))
    b0["PREVIOUS_STATE"] = metrics(Y[dev_all], Y[bl_all], np.array([state[i - 1] for i in bl_all]))
    b0["SIMPLE_TRANSITION"] = metrics(Y[dev_all], Y[bl_all], np.array([state[i + 1] if state[i + 1] != state[i] else state[i] for i in bl_all]))
    Xbase = np.hstack([Xp, KL, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1), ohE, MTF])
    b0["FROZEN_NEXT_STATE_MODEL"] = fit_eval(Xbase, dev_all, bl_all)
    out["baselines_blind_window"] = b0
    # baselines on the SAME 20 points Hermes sees
    b20 = {"MAJORITY": metrics(Y[dev_all], Y[np.array(sidx)], np.array([collections.Counter(Y[dev_all]).most_common(1)[0][0]] * len(sidx))),
            "PERSISTENCE": metrics(Y[dev_all], Y[np.array(sidx)], np.array([state[i] for i in sidx])),
            "PREVIOUS_STATE": metrics(Y[dev_all], Y[np.array(sidx)], np.array([state[i - 1] for i in sidx])),
            "SIMPLE_TRANSITION": metrics(Y[dev_all], Y[np.array(sidx)], np.array([state[i + 1] if state[i + 1] != state[i] else state[i] for i in sidx]))}
    r20 = fit_eval(Xbase, dev_all, np.array(sidx))
    b20["FROZEN_NEXT_STATE_MODEL"] = r20
    out["baselines_blind_sample20"] = b20
    wjson("baselines/BASELINES.json", {"target": "STATE_V2(t+8)", "blind_window": b0, "blind_sample20": b20,
                                        "note": "frozen baselines; Hermes compared on the SAME 20 points (§109)", "ts_utc": NOW})
    print("baselines20:", json.dumps({k: {"acc": v.get("accuracy"), "ba": v.get("balanced_accuracy")} for k, v in b20.items()}, ensure_ascii=False), flush=True)

    # ---- §87 information-content matrix ----
    ABL = {"PRICE": Xp, "PRICE+KLINE": np.hstack([Xp, KL]), "PRICE+STRUCTURE": np.hstack([Xp, Xp[:, [1, 6, 7]]]),
            "PRICE+STATE": np.hstack([Xp, ohS, dw.reshape(-1, 1), nod8.reshape(-1, 1)]), "PRICE+EVENT": np.hstack([Xp, ohE]),
            "PRICE+MTF": np.hstack([Xp, MTF]), "PRICE+MECHANISM": np.hstack([Xp, MECH]),
            "PRICE+CROSSMARKET": np.hstack([Xp, XCM]), "FULL": np.hstack([Xp, KL, ohS, ohE, MTF, MECH, XCM])}
    mat = {}
    for k, M in ABL.items():
        if "CROSSMARKET" in k or k == "FULL":
            cm_mask = np.array([ts.iloc[i] >= CM_START for i in valid])
            vv = valid[cm_mask]
            cut = int(len(vv) * 0.6)
            mat[k] = fit_eval(M, vv[:cut], vv[cut:])
            mat[k]["split"] = "window-internal 60/40 (cross-market coverage starts 2026-07-16)"
        else:
            mat[k] = fit_eval(M, dev_all, bl_all)
            mat[k]["split"] = "main (dev < 2026-06-01, blind >= 2026-06-01)"
    out["information_content_matrix"] = mat
    wjson("ablation/INFORMATION_CONTENT.json", {"target": "STATE_V2(t+8)", "matrix": mat, "ts_utc": NOW,
                                                 "note": "frozen-model information content, NOT Hermes (§87/§88); all variants saved"})
    print("ablation:", json.dumps({k: v.get("dll") for k, v in mat.items()}, ensure_ascii=False), flush=True)
    wjson("evaluation/GT_BASELINES_ABLATION.json", out)
    print("WROTE evaluation/GT_BASELINES_ABLATION.json", flush=True)


if __name__ == "__main__":
    main()
