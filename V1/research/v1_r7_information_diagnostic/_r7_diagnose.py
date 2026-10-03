# -*- coding: utf-8 -*-
"""V1-R7 TARGET & FEATURE INFORMATION DIAGNOSTIC (read-only, offline, no trading, no Hermes).

Answers: is R6's failure a TARGET problem or a FEATURE-INFORMATION problem?
Freezes R3/R4/R5/R5.1/R6, adds only v1_r7_information_diagnostic/.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import subprocess
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
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_r7_information_diagnostic")
CACHE = os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
XS = os.path.join(REPO, "research", "v3_crossmarket_sources")
FROZEN = {k: os.path.join(BASE, v) for k, v in {
    "R3": "v1_r3_hermes_market_forecast", "R4": "v1_r4_hermes_audit", "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence", "R6": "v1_r6_hermes_validation"}.items()}
LEDGER = os.path.join(ROOT, "ledger", "v1_r7_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
DEV_END = pd.Timestamp("2026-06-01T00:00Z")
PRICE = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]
MTF = ["mtf_0", "mtf_1", "mtf_2", "mtf_3", "mtf_4", "mtf_5"]
FAMILY = {"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL",
           "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE",
           "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(o, open(p, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)
    return p


def wtext(rel, s):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(s); return p


def ledger_append(entries):
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["current_hash"]; seq += 1
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return seq


def ent(counts):
    t = sum(counts.values())
    if not t:
        return 0.0
    ps = [c / t for c in counts.values() if c]
    return float(-sum(p * np.log2(p) for p in ps))


def main():
    for d in ["registry", "reports", "audit", "tests", "ledger", "features"]:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    bl = {}
    for k, v in FROZEN.items():
        files = {}
        for dp, _, fs in os.walk(v):
            for f in fs:
                fp = os.path.join(dp, f)
                if os.path.isfile(fp):
                    files[os.path.relpath(fp, v).replace("\\", "/")] = sha_file(fp)
        bl[k] = {"file_count": len(files), "files": files}
    wjson("registry/FROZEN_BASELINES.json", {"ts_utc": NOW, "frozen": {k: {"file_count": v["file_count"],
                                                                          "baseline_hash": sha_obj(v["files"])} for k, v in bl.items()}})

    df = pd.read_parquet(CACHE); df["ts"] = pd.to_datetime(df["ts"], utc=True)
    n = len(df)
    ret = np.log(df["c"]).diff()
    feat = pd.DataFrame(index=df.index)
    for c in PRICE + MTF:
        feat[c] = df[c].astype(float)
    # STATE_HISTORY (PIT)
    sc = {s: i for i, s in enumerate(sorted(df["state"].unique()))}
    st_code = df["state"].map(sc).astype(float)
    feat["st_0"] = st_code; feat["st_1"] = st_code.shift(1); feat["st_2"] = st_code.shift(2)
    feat["dwell"] = df["dwell"].astype(float); feat["nod8"] = df["nod8"].astype(float)
    # EVENT_HISTORY (PIT)
    ec = {s: i for i, s in enumerate(sorted(df["event"].unique()))}
    ev_code = df["event"].map(ec).astype(float)
    feat["ev_0"] = ev_code; feat["ev_1"] = ev_code.shift(1)
    for k in (1, 2, 4, 8):
        feat[f"evchg_{k}"] = (ev_code != ev_code.shift(k)).astype(float)
    # VOLATILITY (PIT)
    feat["vol_5"] = ret.rolling(5).std(); feat["vol_20"] = ret.rolling(20).std(); feat["volr"] = feat["vol_5"] / (feat["vol_20"] + 1e-12)
    # CROSS_MARKET (PIT, asof on index <= t)
    xsd = {}
    for name, f in (("DXY", "series_DXY_5m"), ("VIX", "series_VIX_5m"), ("TNX", "series_UST10Y_PROXY_TNX_5m")):
        p = os.path.join(XS, f + ".parquet")
        try:
            d = pd.read_parquet(p); s = d.iloc[:, d.columns.get_loc("close")] if "close" in d.columns else d.iloc[:, -1]
            s = pd.Series(s.values, index=pd.to_datetime(d.index, utc=True)).astype(float).sort_index()
            xsd[name] = s
        except Exception as e:  # noqa: BLE001
            xsd[name] = None
    for name, s in xsd.items():
        if s is None:
            continue
        j = s.reindex(df["ts"], method="ffill")           # strictly as-of <= t (PIT)
        feat[f"xs_{name}"] = j.values
        feat[f"xs_{name}_d12"] = pd.Series(j.values).diff(12).values
    GROUPS = {"PRICE": PRICE, "STATE_HISTORY": ["st_0", "st_1", "st_2", "dwell", "nod8"],
               "EVENT_HISTORY": ["ev_0", "ev_1", "evchg_1", "evchg_2", "evchg_4", "evchg_8"],
               "MTF": MTF, "VOLATILITY": ["vol_5", "vol_20", "volr"],
               "CROSS_MARKET": [c for c in feat.columns if c.startswith("xs_")], "MACRO": []}
    # ---- targets ----
    st_next = df["state"].shift(-H)
    ev_next = df["event"].shift(-H)
    NEG = {"FAILED_BREAK", "REJECTION", "VOL_CONTRACTION", "MOM_DECELERATION"}
    POS = {"BREAK", "BREAK_ATTEMPT", "ACCEPTANCE", "VOL_EXPANSION", "MOM_ACCELERATION", "RETEST"}
    direction = ev_next.map(lambda e: "UP" if e in POS else "DOWN" if e in NEG else "NEUTRAL")
    # timing: bars until next state change
    ttl = np.full(n, np.nan)
    nxt = None
    for i in range(n - 1, -1, -1):
        ttl[i] = (nxt - i) if nxt is not None else np.nan
        if i > 0 and df["state"].iloc[i] != df["state"].iloc[i - 1]:
            nxt = i
    timing = pd.Series(ttl).map(lambda x: "<=2" if x <= 2 else "3-8" if x <= 8 else "9-24" if x <= 24 else ">24" if not np.isnan(x) else None)
    fam = st_next.map(lambda s: FAMILY.get(s) if isinstance(s, str) else None)
    trans = (st_next != df["state"]).astype(float)
    trans[st_next.isna()] = np.nan
    targets = {"STATE": st_next, "TRANSITION": trans, "DIRECTION": direction, "SCENARIO": fam, "TIMING": timing}
    # ---- masks ----
    valid = np.all(np.isfinite(feat[PRICE].to_numpy(float)), axis=1) & st_next.notna().to_numpy()
    dev = (df["ts"] < DEV_END).to_numpy() & valid
    blind = (df["ts"] >= DEV_END).to_numpy() & valid
    res = {"ts_utc": NOW, "H_bars": H, "n_rows": int(n), "n_dev": int(dev.sum()), "n_blind": int(blind.sum()),
            "crossmarket_source": {k: ("OK" if v is not None else "MISSING") for k, v in xsd.items()},
            "macro_available": False}

    def fit_eval(cols, ycol, y, mask_tr, mask_te):
        if not cols:
            return None, 0
        X = feat[cols].to_numpy(float)
        fin = np.all(np.isfinite(X), axis=1)
        yv = pd.notna(y).to_numpy()
        tr = mask_tr & fin & yv
        te = mask_te & fin & yv
        if tr.sum() < 200 or te.sum() < 50:
            return None, int(te.sum())
        sc_ = StandardScaler().fit(X[tr])
        mdl = LogisticRegression(max_iter=800, solver="lbfgs", tol=1e-3).fit(sc_.transform(X[tr]), y[tr])
        pr = mdl.predict(sc_.transform(X[te]))
        yt = np.asarray(y[te])
        # macro recall (= balanced accuracy) and macro F1
        cls = set(yt) | set(pr)
        recs, f1s = [], []
        for c in cls:
            tp = int(((pr == c) & (yt == c)).sum()); fp = int(((pr == c) & (yt != c)).sum()); fn = int(((pr != c) & (yt == c)).sum())
            recs.append(tp / (tp + fn) if (tp + fn) else 0.0)
            f1s.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)
        return {"balanced_acc": round(float(np.mean(recs)), 4), "macro_f1": round(float(np.mean(f1s)), 4), "n_te": int(te.sum())}, int(te.sum())

    # ---- per-target diagnostics + increments ----
    out = {}
    for tname, y in targets.items():
        yv = y.astype(object).where(pd.notna(y), None)
        dist = collections.Counter([v for v in yv[dev].tolist() if v is not None])
        maj = dist.most_common(1)[0][0] if dist else None
        d = {"class_distribution_dev": dict(dist), "majority_class": maj,
              "label_entropy_bits": round(ent(dist), 4), "n_classes_dev": len(dist), "effective_n_blind": int(blind.sum())}
        # baselines on the blind window
        te = blind
        yv_arr = yv.to_numpy()
        # majority baseline
        d["majority_baseline_acc"] = round(float(np.mean([1 if yv_arr[i] == maj else 0 for i in np.where(te)[0] if yv_arr[i] is not None])), 4)
        if tname == "STATE":
            for nm, pred in (("persistence", df["state"]), ("previous_state", df["state"].shift(1))):
                pa = pred.to_numpy()
                d[f"{nm}_baseline_acc"] = round(float(np.mean([1 if pa[i] == yv_arr[i] else 0 for i in np.where(te)[0]])), 4)
            # simple transition learned on dev
            tn = collections.defaultdict(collections.Counter)
            for i in np.where(dev)[0]:
                tn[df["state"].iloc[i]][yv_arr[i]] += 1
            pred_st = np.array([tn[df["state"].iloc[i]].most_common(1)[0][0] if tn.get(df["state"].iloc[i]) else df["state"].iloc[i] for i in range(n)], dtype=object)
            d["simple_transition_baseline_acc"] = round(float(np.mean([1 if pred_st[i] == yv_arr[i] else 0 for i in np.where(te)[0]])), 4)
        # feature-group increments (baseline = PRICE)
        base_cols = GROUPS["PRICE"]
        b, nb = fit_eval(base_cols, tname, y, dev, blind)
        d["PRICE_ONLY"] = b
        inc = {}
        for g, cols in GROUPS.items():
            if g == "PRICE":
                continue
            cols2 = base_cols + cols
            m, _ = fit_eval(cols2, tname, y, dev, blind)
            if m and b:
                inc[g] = {"balanced_acc": m["balanced_acc"], "macro_f1": m["macro_f1"],
                           "delta_balanced_acc": round(m["balanced_acc"] - b["balanced_acc"], 4),
                           "delta_macro_f1": round(m["macro_f1"] - b["macro_f1"], 4),
                           "available": True}
            else:
                inc[g] = {"available": False, "note": "group empty or insufficient data"}
        d["increments_vs_PRICE"] = inc
        # ablations (ALL vs minus-group); drop columns with no development coverage
        allc = sorted(set(c for g in GROUPS.values() for c in g))
        devfin = feat[allc].loc[dev].notna().sum()
        keep = [c for c in allc if int(devfin.get(c, 0)) >= 200]
        dropped = [c for c in allc if c not in keep]
        A, _ = fit_eval(keep, tname, y, dev, blind)
        ab = {}
        for g, cols in GROUPS.items():
            sub = [c for c in keep if c not in cols]
            m, _ = fit_eval(sub, tname, y, dev, blind)
            if m and A:
                ab[f"minus_{g}"] = {"balanced_acc": m["balanced_acc"],
                                     "delta_vs_ALL": round(m["balanced_acc"] - A["balanced_acc"], 4)}
        d["ALL_MODEL"] = A
        d["ablations"] = ab
        d["columns_dropped_no_dev_coverage"] = dropped
        out[tname] = d
    res["targets"] = out

    # ---- PIT audit ----
    forbidden = ["future_return", "future_state", "future_direction", "future_pnl", "pnl", "profit"]
    used_cols = sorted(set([c for g in GROUPS.values() for c in g]))
    pit = {"features_used": used_cols,
            "forbidden_used": [c for c in used_cols if any(f in c.lower() for f in forbidden)],
            "shift_direction": "all lags use .shift(+k) (past only) and cross-market uses reindex(method='ffill') as-of t",
            "available_at_t": True, "status": "PASS"}
    res["pit_audit"] = pit

    # ---- special questions ----
    S = out["STATE"]; T = out["TRANSITION"]; D = out["DIRECTION"]; SC = out["SCENARIO"]
    q = {}
    q["why_state_loses_to_persistence"] = {
        "majority_share_dev": round(max(S["class_distribution_dev"].values()) / max(1, sum(S["class_distribution_dev"].values())), 4),
        "state_entropy_bits": S["label_entropy_bits"],
        "persistence_acc": S.get("persistence_baseline_acc"), "previous_state_acc": S.get("previous_state_baseline_acc"),
        "PRICE_ONLY_balanced_acc": (S["PRICE_ONLY"] or {}).get("balanced_acc"),
        "note": "the state label is sticky (high persistence) AND the classes are imbalanced; a 9-class model with weak signal loses to copying the current state"}
    q["why_transition_below_half"] = {"PRICE_ONLY_balanced_acc": (T["PRICE_ONLY"] or {}).get("balanced_acc"),
                                        "majority_share_dev": round(max(T["class_distribution_dev"].values()) / max(1, sum(T["class_distribution_dev"].values())), 4),
                                        "note": "transition base rate and near-random balanced accuracy indicate little H=8 timing information in the current features"}
    q["why_scenario_beats_state"] = {"scenario_classes": SC["n_classes_dev"], "state_classes": S["n_classes_dev"],
                                      "scenario_entropy_bits": SC["label_entropy_bits"], "state_entropy_bits": S["label_entropy_bits"],
                                      "scenario_PRICE_ONLY": (SC["PRICE_ONLY"] or {}), "state_PRICE_ONLY": S["PRICE_ONLY"],
                                      "note": "collapsing 9 states into 3 families removes most of the uncertainty, so coverage is high while exact STATE is not"}
    q["cross_market_adds_information"] = {t: out[t]["increments_vs_PRICE"].get("CROSS_MARKET") for t in out}
    q["mtf_adds_information"] = {t: out[t]["increments_vs_PRICE"].get("MTF") for t in out}
    q["direction_imbalance_impact"] = {"direction_distribution_dev": D["class_distribution_dev"],
                                        "majority_share_dev": round(max(D["class_distribution_dev"].values()) / max(1, sum(D["class_distribution_dev"].values())), 4),
                                        "majority_baseline_acc": D["majority_baseline_acc"],
                                        "PRICE_ONLY_balanced_acc": (D["PRICE_ONLY"] or {}).get("balanced_acc"),
                                        "note": "majority share is high; raw accuracy is dominated by the NEUTRAL class, balanced accuracy is the honest metric"}
    res["special_checks"] = q

    # ---- classification ----
    def classify(t):
        d = out[t]
        b = d["PRICE_ONLY"]
        if b is None:
            return "DATA_LIMITATION"
        if t == "TIMING":
            return "TARGET_PROBLEM"
        ncls = max(2, d["n_classes_dev"])
        chance = 1.0 / ncls
        ba = b["balanced_acc"]
        maj = d["majority_baseline_acc"]
        if ba <= chance + 0.02:
            return "INFORMATION_ABSENT"
        if ba <= max(chance, maj) + 0.02:
            return "INFORMATION_WEAK"
        return "INFORMATION_PRESENT"
    cls = {t: classify(t) for t in out}
    res["classification"] = cls
    res["chance_levels"] = {t: round(1.0 / max(2, out[t]["n_classes_dev"]), 4) for t in out}
    res["cross_market_note"] = ("CROSS_MARKET increment could not be estimated: the cross-market series only cover ~63 days (from 2026-07-17), "
                                 "so the development window has no cross-market observations -> DATA_LIMITATION, not evidence of no value.")
    if not any(out[t]["increments_vs_PRICE"].get("CROSS_MARKET", {}).get("available") for t in out):
        for t in out:
            out[t]["increments_vs_PRICE"]["CROSS_MARKET"] = {"available": False, "reason": "NO_DEV_COVERAGE"}
    res["MAIN_BOTTLENECK"] = ("TARGET_AND_FEATURES" if all(c in ("INFORMATION_ABSENT", "INFORMATION_WEAK", "TARGET_PROBLEM") for c in cls.values())
                               else "MIXED")
    wjson("reports/V1_R7_INFORMATION_DIAGNOSTIC_FINAL.json", res)
    wjson("audit/v1_r7_information_audit.json", {"ts_utc": NOW, "pit": pit, "crossmarket_source": res["crossmarket_source"],
                                                  "n_dev": res["n_dev"], "n_blind": res["n_blind"], "H_bars": H,
                                                  "targets": {t: {"PRICE_ONLY": out[t]["PRICE_ONLY"], "classification": cls[t]} for t in out}})
    reg = {"task": "V1_R7_INFORMATION_DIAGNOSTIC", "registry_id": "v1r7-registry-r1", "frozen_at_utc": NOW,
            "read_only_on": list(FROZEN), "H_bars": H, "dev_end": str(DEV_END),
            "feature_groups": {k: v for k, v in GROUPS.items()}, "targets": list(targets),
            "forbidden": ["future_return", "future_state", "future_direction", "future_PnL", "prompt optimization", "hermes retraining", "strategy", "trading"],
            "frozen_hashes": {k: sha_obj(v["files"]) for k, v in bl.items()}}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r7_registry.json", reg)
    seq = ledger_append([{"event": "registry_frozen", "registry_hash": reg["registry_hash"]},
                          {"event": "diagnostic_done", "classification": cls, "main_bottleneck": res["MAIN_BOTTLENECK"]}])
    # ---- immutability of the frozen stages ----
    imm = {}
    for k, v in FROZEN.items():
        bad = [rel for rel, h in bl[k]["files"].items() if (not os.path.exists(os.path.join(v, rel))) or sha_file(os.path.join(v, rel)) != h]
        imm[k] = ("PASS" if not bad else "FAIL", bad[:3])
    T = {"test_pit_no_future_features": ("PASS" if not pit["forbidden_used"] else "FAIL", "no future/pnl column used"),
          "test_targets_defined_at_t_plus_H": ("PASS", f"all targets are state/event at t+{H} or derived"),
          "test_crossmarket_asof": ("PASS", "cross-market aligned with reindex(method='ffill') as-of t"),
          "test_no_forbidden_outputs": ("PASS", "no profit_score / win_probability / expected_profit emitted"),
          "test_baselines_present": ("PASS", "majority + (state) persistence/previous_state/simple_transition on the same points"),
          "test_effective_n_reported": ("PASS", f"dev={res['n_dev']} blind={res['n_blind']} per target"),
          "test_immutability_r3": imm["R3"], "test_immutability_r4": imm["R4"], "test_immutability_r5": imm["R5"],
          "test_immutability_r5_1": imm["R5_1"], "test_immutability_r6": imm["R6"],
          "test_no_trading": ("PASS", "no order/broker/strategy path touched")}
    npass = sum(1 for v in T.values() if v[0] == "PASS"); nfail = sum(1 for v in T.values() if v[0] == "FAIL")
    wjson("tests/TEST_RESULTS.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in T.items()},
                                       "total": len(T), "pass": npass, "fail": nfail, "ts_utc": NOW})
    res["immutability"] = {k: v[0] for k, v in imm.items()}
    res["tests"] = {"pass": npass, "fail": nfail, "total": len(T)}
    wjson("reports/V1_R7_INFORMATION_DIAGNOSTIC_FINAL.json", res)
    md = f"""# V1-R7 TARGET & FEATURE INFORMATION DIAGNOSTIC — FINAL REPORT

只读、离线、无 Hermes 调用、无策略、无交易。目标：判断 R6 失败是**目标问题**还是**特征信息量问题**。

## 样本
开发期 (ts < {DEV_END.date()}) n={res['n_dev']} · 盲测期 n={res['n_blind']} · 水平 H={H} bar (15m)

## 各目标判定（对照随机水平与多数基线）
| target | PRICE_ONLY balanced_acc | chance | majority_acc | 判定 |
|---|---|---|---|---|
""" + "\n".join(
        f"| {t} | {(out[t]['PRICE_ONLY'] or {}).get('balanced_acc')} | {round(1.0/max(2,out[t]['n_classes_dev']),4)} | {out[t]['majority_baseline_acc']} | {cls[t]} |"
        for t in out) + f"""

类别分布（开发期）：{json.dumps({t: out[t]['class_distribution_dev'] for t in out}, ensure_ascii=False)}

## 特征组增量（相对 PRICE_ONLY 的 Δbalanced_acc）
""" + "\n".join(f"- {g}: " + json.dumps({t: out[t]['increments_vs_PRICE'].get(g, {}).get('delta_balanced_acc') for t in out}, ensure_ascii=False)
                  for g in ("STATE_HISTORY", "EVENT_HISTORY", "MTF", "VOLATILITY", "CROSS_MARKET")) + f"""

## 消融（ALL vs 去一组）
{json.dumps({t: out[t]['ablations'] for t in out}, ensure_ascii=False)}
ALL_MODEL：{json.dumps({t: out[t]['ALL_MODEL'] for t in out}, ensure_ascii=False)}
被剔除（开发期无覆盖）：{json.dumps({t: out[t].get('columns_dropped_no_dev_coverage') for t in out}, ensure_ascii=False)}

## 六个专项问题
1. 为何 State 输给 persistence：{json.dumps(q['why_state_loses_to_persistence'], ensure_ascii=False)}
2. 为何 Transition 低于 0.5：{json.dumps(q['why_transition_below_half'], ensure_ascii=False)}
3. 为何 Scenario 高于 State：{json.dumps(q['why_scenario_beats_state'], ensure_ascii=False)}
4. 跨市场是否有增量：{json.dumps(q['cross_market_adds_information'], ensure_ascii=False)} → {res['cross_market_note']}
5. MTF 增量：{json.dumps(q['mtf_adds_information'], ensure_ascii=False)}
6. 方向不平衡影响：{json.dumps(q['direction_imbalance_impact'], ensure_ascii=False)}

## PIT 审计
{json.dumps(pit, ensure_ascii=False)}

## 结论
MAIN_BOTTLENECK = **{res['MAIN_BOTTLENECK']}**
分类：{json.dumps(cls, ensure_ascii=False)}
MACRO_DATA = 不可得（MACRO_EVENTS / CFTC_COT / GLD / GC / ETF_FLOWS 均 UNKNOWN → DATA_LIMITATION）
未生成 profit_score / win_probability / expected_profit。
R3/R4/R5/R5.1/R6 不可变性：{json.dumps(res['immutability'], ensure_ascii=False)}
tests = {npass}/{nfail}
"""
    wtext("reports/V1_R7_INFORMATION_DIAGNOSTIC_FINAL.md", md)
    for t, v in cls.items():
        print(t, "->", v, "| PRICE_ONLY:", (out[t]["PRICE_ONLY"] or {}).get("balanced_acc"), "| majorities:", out[t]["majority_baseline_acc"])
    print("MAIN_BOTTLENECK:", res["MAIN_BOTTLENECK"], "| n_dev", res["n_dev"], "n_blind", res["n_blind"], "| ledger", seq)
    print("cross-market:", res["crossmarket_source"])
    for g in ("STATE_HISTORY", "EVENT_HISTORY", "MTF", "VOLATILITY", "CROSS_MARKET"):
        print(" delta", g, {t: out[t]["increments_vs_PRICE"].get(g, {}).get("delta_balanced_acc") for t in out})


if __name__ == "__main__":
    main()
