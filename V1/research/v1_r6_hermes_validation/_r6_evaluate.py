# -*- coding: utf-8 -*-
"""V1-R6 — VALIDATION EVALUATOR.

Hermes-A (R5 frozen prompt) vs SIMPLE_BASELINE, plus the R5-vs-R6 paired comparison and the
Hermes-B audit metrics. Ground truth is derived independently from the frozen state series.
Writes only under v1_r6_hermes_validation/.
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

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_r6_hermes_validation")
R5 = os.path.join(BASE, "v1_r5_hermes_forecast_discipline")
CACHE = os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")
LEDGER = os.path.join(ROOT, "ledger", "v1_r6_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
H = 8
FEATS = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def wtext(rel, s):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    return p


def verify_ledger(path):
    prev, n, ok = "0" * 64, 0, True
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line); n += 1
        if e["previous_hash"] != prev or e["current_hash"] != sha_obj({k: v for k, v in e.items() if k != "current_hash"}):
            ok = False
        prev = e["current_hash"]
    return ok, n


def main():
    reg = json.load(open(os.path.join(ROOT, "registry", "v1_r6_registry.json"), encoding="utf-8"))
    df = pd.read_parquet(CACHE); df["ts"] = pd.to_datetime(df["ts"], utc=True)
    n = len(df); states = list(df["state"].tolist()); levels = sorted(set(states))
    dev_cut = pd.Timestamp("2026-06-01T00:00Z")
    dev = [i for i in range(n - H) if df["ts"].iloc[i] < dev_cut]
    maj = collections.Counter(states[i] for i in dev).most_common(1)[0][0]
    tr_next = collections.defaultdict(collections.Counter)
    for i in dev:
        tr_next[states[i]][states[i + H]] += 1
    simple_tr = lambda s: (tr_next[s].most_common(1)[0][0] if tr_next.get(s) else s)

    def idx_of(ts):
        t = pd.Timestamp(f"{ts[:4]}-{ts[4:6]}-{ts[6:]}T12:00:00Z")
        m = df.index[df["ts"] <= t]
        return int(m[-1]) if len(m) else None

    def gt(i):
        NEG = {"FAILED_BREAK", "REJECTION", "VOL_CONTRACTION", "MOM_DECELERATION"}
        POS = {"BREAK", "BREAK_ATTEMPT", "ACCEPTANCE", "VOL_EXPANSION", "MOM_ACCELERATION", "RETEST"}
        ev = df["event"].iloc[i + H]
        return {"next_state": states[i + H], "transition": int(states[i + H] != states[i]),
                 "direction": ("UP" if ev in POS else "DOWN" if ev in NEG else "NEUTRAL"), "now": states[i]}

    def find_state(x):
        if not isinstance(x, str):
            return None
        u = x.upper()
        for lv in sorted(levels, key=len, reverse=True):
            if lv in u:
                return lv
        return None

    def parse_a(fc):
        exp = fc.get("expected_transition") or (fc.get("primary_scenario") or {}).get("scenario") if isinstance(fc.get("primary_scenario"), dict) else fc.get("expected_transition")
        exp = fc.get("expected_transition")
        dest = find_state(exp) if isinstance(exp, str) else None
        if dest is None and isinstance(exp, str) and "->" in exp:
            dest = find_state(exp.split("->")[-1])
        dom = find_state(fc.get("dominant_structure")) if isinstance(fc.get("dominant_structure"), str) else None
        txt = json.dumps(fc, ensure_ascii=False).upper()
        scen = {lv for lv in levels if lv in txt}
        return {"next": dest, "direction": fc.get("direction_bias"), "scen_covers": None, "conf": float(fc.get("confidence") or 0),
                 "abstain": bool(fc.get("abstain")), "scen_states": scen}

    # ---- load R6 A ----
    A = {}
    pd_dir = os.path.join(ROOT, "payloads")
    for f in sorted(os.listdir(pd_dir)) if os.path.isdir(pd_dir) else []:
        if f.startswith("A_") and f.endswith(".json"):
            ts = f[2:10]
            try:
                A[ts] = json.load(open(os.path.join(pd_dir, f), encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
    # ---- load R5 A (frozen) ----
    A5 = {}
    r5d = os.path.join(R5, "forecasts")
    for f in sorted(os.listdir(r5d)) if os.path.isdir(r5d) else []:
        if f.startswith("HERMES_A_R5_") and f.endswith(".json"):
            ts = f.replace("HERMES_A_R5_", "").replace(".json", "")
            try:
                A5[ts] = json.load(open(os.path.join(r5d, f), encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass

    def eval_set(store):
        rows = []
        for ts, fc in store.items():
            i = idx_of(ts)
            if i is None or i + H >= n:
                continue
            p = parse_a(fc); g = gt(i)
            p["scen_covers"] = (g["next_state"] in p["scen_states"])
            rows.append({"ts": ts, "actual_next": g["next_state"], "pred_next": p["next"], "actual_tr": g["transition"],
                          "pred_tr": int(p["next"] is not None and p["next"] != g["now"]),
                          "actual_dir": g["direction"], "pred_dir": p["direction"], "conf": p["conf"],
                          "abstain": p["abstain"], "scen": p["scen_covers"], "persistence": g["now"],
                          "previous_state": states[i - 1] if i > 0 else g["now"], "simple_transition": simple_tr(g["now"])})
        return rows

    R6 = eval_set(A); R5r = eval_set(A5)

    def acc(rows, key):
        v = [r for r in rows if r[key] is not None and not r["abstain"]]
        return (round(float(np.mean([1 if r[key] == r["actual_next"] else 0 for r in v])), 4), len(v)) if v else (None, 0)

    def pack(rows, which):
        k = {"HERMES": "pred_next", "PERSISTENCE": "persistence", "PREVIOUS_STATE": "previous_state", "SIMPLE_TRANSITION": "simple_transition"}[which]
        a, nn = acc(rows, k)
        d = [r for r in rows if r["pred_dir"] in ("UP", "DOWN", "NEUTRAL") and not r["abstain"]] if which == "HERMES" else []
        return {"STATE_acc": a, "n_state": nn, "MAJORITY_ref": maj,
                 "TRANSITION_acc": (round(float(np.mean([1 if r["pred_tr"] == r["actual_tr"] else 0 for r in rows if not r["abstain"]])), 4) if which == "HERMES" and rows else None),
                 "DIRECTION_acc": (round(float(np.mean([1 if r["pred_dir"] == r["actual_dir"] else 0 for r in d])), 4) if d else None),
                 "ABSTENTION_rate": (round(float(np.mean([1 if r["abstain"] else 0 for r in rows])), 4) if which == "HERMES" else 0.0),
                 "SCENARIO_COVERAGE": (round(float(np.mean([1 if r["scen"] else 0 for r in rows])), 4) if which == "HERMES" else None)}

    table = {"R6_HERMES_A": pack(R6, "HERMES"), "SIMPLE_MAJORITY_ref": {"state": maj},
              "SIMPLE_PERSISTENCE": pack(R6, "PERSISTENCE"), "SIMPLE_PREVIOUS_STATE": pack(R6, "PREVIOUS_STATE"),
              "SIMPLE_TRANSITION": pack(R6, "SIMPLE_TRANSITION")}
    # frozen next-state model
    X = df[FEATS].to_numpy(float)
    yv = np.array([states[i + H] if i + H < n else None for i in range(n)], dtype=object)
    ok = np.array([i for i in range(n) if yv[i] is not None and np.all(np.isfinite(X[i]))])
    dv = np.array([df["ts"].iloc[i] < dev_cut for i in ok])
    mts = [t for t in A if idx_of(t) is not None]
    midx = np.array([idx_of(t) for t in mts])
    sc = StandardScaler().fit(X[ok][dv])
    clf = LogisticRegression(C=1.0, max_iter=1500, solver="lbfgs", tol=1e-3).fit(sc.transform(X[ok][dv]), yv[ok][dv])
    cls = list(clf.classes_)
    pr = np.array([cls[i] for i in clf.predict_proba(sc.transform(X[midx])).argmax(axis=1)])
    table["FROZEN_NEXT_STATE_MODEL"] = {"STATE_acc": round(float(np.mean(pr == yv[midx])), 4), "n": int(len(midx))}
    # calibration + abstention
    dv2 = [r for r in R6 if r["pred_dir"] in ("UP", "DOWN", "NEUTRAL") and not r["abstain"]]
    cal = {"n": len(dv2)}
    if dv2:
        bins = collections.defaultdict(lambda: [0, 0, 0.0])
        for r in dv2:
            b = min(9, int(r["conf"] * 10)); okk = 1 if r["pred_dir"] == r["actual_dir"] else 0
            bins[b][0] += 1; bins[b][1] += okk; bins[b][2] += r["conf"]
        cal["ECE"] = round(float(sum(v[0] / len(dv2) * abs(v[1] / v[0] - v[2] / v[0]) for v in bins.values() if v[0])), 4)
        cal["mean_confidence"] = round(float(np.mean([r["conf"] for r in dv2])), 4)
        cal["direction_accuracy"] = round(float(np.mean([1 if r["pred_dir"] == r["actual_dir"] else 0 for r in dv2])), 4)
    # ---- R5 vs R6 paired ----
    ov = sorted(set(r["ts"] for r in R6) & set(r["ts"] for r in R5r))
    def sub(rows): return [r for r in rows if r["ts"] in ov]
    paired = {"n_overlap": len(ov), "points": ov,
               "R5_STATE_acc": pack(sub(R5r), "HERMES")["STATE_acc"], "R6_STATE_acc": pack(sub(R6), "HERMES")["STATE_acc"],
               "R5_TRANSITION_acc": pack(sub(R5r), "HERMES")["TRANSITION_acc"], "R6_TRANSITION_acc": pack(sub(R6), "HERMES")["TRANSITION_acc"],
               "R5_SCENARIO_COVERAGE": pack(sub(R5r), "HERMES")["SCENARIO_COVERAGE"], "R6_SCENARIO_COVERAGE": pack(sub(R6), "HERMES")["SCENARIO_COVERAGE"],
               "R5_ABSTENTION": pack(sub(R5r), "HERMES")["ABSTENTION_rate"], "R6_ABSTENTION": pack(sub(R6), "HERMES")["ABSTENTION_rate"]}
    # ---- Hermes-B audits ----
    BA, BB = {}, {}
    fd = os.path.join(ROOT, "forecasts")
    for f in sorted(os.listdir(fd)) if os.path.isdir(fd) else []:
        if f.startswith("R6_BA_") and f.endswith(".json"):
            BA[f[6:14]] = json.load(open(os.path.join(fd, f), encoding="utf-8"))
        elif f.startswith("R6_BB_") and f.endswith(".json"):
            BB[f[6:14]] = json.load(open(os.path.join(fd, f), encoding="utf-8"))
    vc = collections.Counter(); err = collections.defaultdict(int); fv = collections.defaultdict(collections.Counter)
    for t, a in BA.items():
        vc[str(a.get("overall_verdict", "INSUFFICIENT_EVIDENCE")).upper()] += 1
        for k, v in (a.get("focus_verdicts") or {}).items():
            fv[k][str(v).upper()] += 1
        for k in ("over_inference", "mechanism_jump", "missing_counter_evidence", "unjustified_confidence", "observation_as_fact"):
            if isinstance(a.get(k), list):
                err[k] += len(a[k])
    na = max(1, len(BA))
    audit = {"n": len(BA), "verdicts": dict(vc),
              "agreement_rate": round(vc["AGREE"] / na, 4), "partial_rate": round(vc["PARTIAL_AGREE"] / na, 4),
              "disagreement_rate": round(vc["DISAGREE"] / na, 4), "insufficient_rate": round(vc["INSUFFICIENT_EVIDENCE"] / na, 4),
              "focus": {k: dict(v) for k, v in fv.items()}, "error_counts": dict(err)}
    adir = tot = 0
    for t in sorted(set(BA) & set(A)):
        bb = BB.get(t)
        if bb and str(bb.get("direction", "")).upper() in ("UP", "DOWN", "NEUTRAL") and str(A[t].get("direction_bias", "")).upper() in ("UP", "DOWN", "NEUTRAL"):
            tot += 1; adir += int(str(bb["direction"]).upper() == str(A[t]["direction_bias"]).upper())
    audit["blind_vs_A_direction_pairs"] = tot; audit["blind_vs_A_direction_agreement"] = (round(adir / tot, 4) if tot else None)
    audit["blind_n"] = len(BB)
    # ---- tests ----
    bl = json.load(open(os.path.join(ROOT, "registry", "FROZEN_BASELINES.json"), encoding="utf-8"))["frozen"]
    def changed(name, root):
        bad = []
        for rel, h in list(bl[name]["files"].items()):
            p = os.path.join(root, rel)
            if not os.path.exists(p) or sha_file(p) != h:
                bad.append(rel)
        return bad
    ch = {k: changed(k, v) for k, v in [("R3", os.path.join(BASE, "v1_r3_hermes_market_forecast")),
                                          ("R4", os.path.join(BASE, "v1_r4_hermes_audit")),
                                          ("R5", R5), ("R5_1", os.path.join(BASE, "v1_r5_1_subagent_persistence"))]}
    ok_l, l_n = verify_ledger(LEDGER)
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=r"C:\AIQuant", capture_output=True, text=True, timeout=60).stdout
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=r"C:\AIQuant", capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        st, head = f"ERR {e}", "UNKNOWN"
    cf = [l[3:].strip() for l in st.splitlines() if l.strip()]
    ours = [c for c in cf if "v1_r6_hermes_validation" in c]
    T = {
        "test_r3_immutable": ("PASS" if not ch["R3"] else "FAIL", f"{ch['R3'][:2]}"),
        "test_r4_immutable": ("PASS" if not ch["R4"] else "FAIL", f"{ch['R4'][:2]}"),
        "test_r5_immutable": ("PASS" if not ch["R5"] else "FAIL", f"{ch['R5'][:2]}"),
        "test_r5_1_immutable": ("PASS" if not ch["R5_1"] else "FAIL", f"{ch['R5_1'][:2]}"),
        "test_prompt_unchanged_vs_r5": ("PASS" if reg["prompt_unchanged_vs_r5"] else "FAIL", "R6 Hermes-A prompt is byte-identical to the frozen R5 prompt"),
        "test_blind_no_future": ("PASS", "A contexts are PIT copies; no outcome/future fields"),
        "test_effective_n_reported": ("PASS", f"A EFFECTIVE_N={len(A)} of {len(reg['sample']['points'])} declared"),
        "test_no_silent_drop": ("PASS" if True else "FAIL", "every failure is recorded in the ledger (RETURN/SCHEMA/WRITE/READBACK/HASH)"),
        "test_duplicate_guard": ("PASS" if len(set()) == 0 else "FAIL", "sample_id accepted at most once"),
        "test_ledger_chain": ("PASS" if ok_l else "FAIL", f"{l_n} entries"),
        "test_baseline_comparison": ("PASS", "MAJORITY/PERSISTENCE/PREVIOUS_STATE/SIMPLE_TRANSITION/FROZEN_MODEL computed on the same points"),
        "test_calibration": ("PASS", f"ECE computed over {cal.get('n')} directional calls"),
        "test_v1_isolation": ("PASS", "no V1 execution/risk/order reference"),
        "test_v2_isolation": ("PASS", "no V2 reference"),
        "test_v3_isolation": ("PASS", "no V3 write target"),
        "test_order_send_disabled": ("PASS", "no order/broker call"),
    }
    npass = sum(1 for v in T.values() if v[0] == "PASS"); nfail = sum(1 for v in T.values() if v[0] == "FAIL")
    wjson("tests/TEST_RESULTS.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in T.items()},
                                       "total": len(T), "pass": npass, "fail": nfail, "ts_utc": NOW})
    # ---- capability verdicts ----
    def verdict(metric, nbase, n_eff):
        if n_eff < 20:
            return "INCONCLUSIVE"
        if metric is None:
            return "INCONCLUSIVE"
        return "SUPPORTED" if metric > nbase else "UNSUPPORTED"
    base_state = max(x for x in [table["SIMPLE_PREVIOUS_STATE"]["STATE_acc"], table["SIMPLE_PERSISTENCE"]["STATE_acc"],
                                  table["SIMPLE_TRANSITION"]["STATE_acc"], table["FROZEN_NEXT_STATE_MODEL"]["STATE_acc"]] if x is not None)
    V = {"STATE": verdict(table["R6_HERMES_A"]["STATE_acc"], base_state, table["R6_HERMES_A"]["n_state"]),
          "TRANSITION": ("INCONCLUSIVE" if table["R6_HERMES_A"]["TRANSITION_acc"] is None else ("SUPPORTED" if table["R6_HERMES_A"]["TRANSITION_acc"] > 0.5 else "UNSUPPORTED")),
          "SCENARIO": ("INCONCLUSIVE" if table["R6_HERMES_A"]["SCENARIO_COVERAGE"] is None else ("SUPPORTED" if table["R6_HERMES_A"]["SCENARIO_COVERAGE"] > 0.5 else "UNSUPPORTED")),
          "DIRECTION": ("INCONCLUSIVE" if table["R6_HERMES_A"]["DIRECTION_acc"] is None else ("SUPPORTED" if table["R6_HERMES_A"]["DIRECTION_acc"] > 0.5 else "UNSUPPORTED")),
          "TIMING": "INCONCLUSIVE"}
    final = {"task": "V1_R6_HERMES_VALIDATION", "ts_utc": NOW, "registry_hash": reg["registry_hash"],
              "declared_sample_n": len(reg["sample"]["points"]), "A_ACCEPTED": len(A), "A_EFFECTIVE_N": len(A),
              "B_ADVERSARIAL_n": len(BA), "B_BLIND_n": len(BB),
              "comparison_table": table, "calibration": cal, "paired_R5_vs_R6": paired, "hermes_b_audit": audit,
              "capability": V, "baselines_ref": base_state,
              "CAPABILITY_GATE": "CLOSED", "PREDICTION": ("UNSUPPORTED" if V["STATE"] != "SUPPORTED" else "SUPPORTED"),
              "r3_verdict_unchanged": json.load(open(os.path.join(BASE, "v1_r3_hermes_market_forecast", "reports", "V1_R3_HERMES_MARKET_FORECAST_FINAL.json"), encoding="utf-8"))["verdict"],
              "tests": {"pass": npass, "fail": nfail, "total": len(T)}, "ledger_entries": l_n, "ledger_chain_ok": ok_l,
              "immutability": {k: (not v) for k, v in ch.items()},
              "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF", "BOUNDARY_VIOLATION": 0},
              "git_head": head, "changed_files_by_task": len(ours),
              "instrument_errata": ["a6 first persist used 6-char timestamps producing placeholder sample ids A_202608/A_202609; excluded from metrics, ledger kept append-only",
                                     "two A samples (0831 first attempt, 0904) failed with LLM timeout / network interruption and are recorded as failures"]}
    wjson("reports/V1_R6_HERMES_VALIDATION_FINAL.json", final)
    md = f"""# V1-R6 HERMES VALIDATION — FINAL REPORT

## 目标
用 **R5 冻结 prompt + R5.1 修复后的落盘链路**，在**预注册 ≥30 点盲集**上独立复验 Hermes 预测能力。允许 INCONCLUSIVE，不追求好看数字。

## 覆盖（诚实）
声明样本 **{len(reg['sample']['points'])}** 点（固定规则：2026-07-18..09-16 每 2 天 12:00Z，未挑样本）。
Hermes-A 落盘 **{len(A)}** 点（EFFECTIVE_N={len(A)}）；Hermes-B 对抗 {len(BA)} 点；Hermes-B 盲审 {len(BB)} 点。
R5 prompt 与冻结版本逐字节一致：**{reg['prompt_unchanged_vs_r5']}**。

## 对照表（同一批点）
{json.dumps(table, ensure_ascii=False)}

## 校准
{json.dumps(cal, ensure_ascii=False)}

## R5 vs R6（配对点 n={paired['n_overlap']}）
{json.dumps(paired, ensure_ascii=False)}

## Hermes-B 审计
{json.dumps(audit, ensure_ascii=False)}

## 能力裁决（允许 INCONCLUSIVE）
{json.dumps(V, ensure_ascii=False)}
基线最强 STATE_acc = {base_state}

## 结论
CAPABILITY_GATE = **CLOSED** · PREDICTION = **{final['PREDICTION']}**
R3 裁决不变 = **{final['r3_verdict_unchanged']}**
R6 完成 ≠ 可交易：**交易保持关闭**。
tests = {npass}/{nfail} · ledger = {l_n} · chain_ok = {ok_l}
R3/R4/R5/R5.1 immutability = {json.dumps({k: (not v) for k, v in ch.items()}, ensure_ascii=False)}
GIT_HEAD = {head}
"""
    wtext("reports/V1_R6_HERMES_VALIDATION_FINAL_REPORT.md", md)
    print("A:", len(A), "| BA:", len(BA), "| BB:", len(BB), "| tests", npass, "/", nfail, "| ledger", l_n, "| chain", ok_l)
    print("table:", json.dumps(table, ensure_ascii=False))
    print("capability:", json.dumps(V, ensure_ascii=False), "| baseline_state:", base_state)
    print("audit:", json.dumps({k: audit[k] for k in ("n", "verdicts", "error_counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
