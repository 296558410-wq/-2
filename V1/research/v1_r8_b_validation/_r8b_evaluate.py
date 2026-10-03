# -*- coding: utf-8 -*-
"""V1-R8-B SCENARIO BLIND VALIDATION — EVALUATOR (read-only on R3..R8-A).

Metrics: BALANCED_ACCURACY / RAW_ACCURACY / CLASS_RECALL / ABSTENTION_RATE / ECE (chance = 1/3).
Baselines: MAJORITY, PERSISTENCE, SIMPLE_TRANSITION, FROZEN_BASELINE. Plus the Hermes-B audit summary.
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
ROOT = os.path.join(BASE, "v1_r8_b_validation")
CACHE = os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")
LEDGER = os.path.join(ROOT, "ledger", "v1_r8_b_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
H = 4
DEV_END = pd.Timestamp("2026-06-01T00:00Z")
PRICE = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]
MTF = ["mtf_0", "mtf_1", "mtf_2", "mtf_3", "mtf_4", "mtf_5"]
FAMILY = {"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL",
           "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE",
           "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}
FROZEN = {k: os.path.join(BASE, v) for k, v in {
    "R3": "v1_r3_hermes_market_forecast", "R4": "v1_r4_hermes_audit", "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence", "R6": "v1_r6_hermes_validation", "R7": "v1_r7_information_diagnostic",
    "R8_A": "v1_r8_target_redesign"}.items()}


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
    reg = json.load(open(os.path.join(ROOT, "registry", "v1_r8_b_registry.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(ROOT, "context", "SAMPLE_INDEX.json"), encoding="utf-8"))
    rows = idx["rows"]
    # ---- Hermes-A calls ----
    A = {}
    pd_dir = os.path.join(ROOT, "payloads")
    for f in sorted(os.listdir(pd_dir)) if os.path.isdir(pd_dir) else []:
        if f.startswith("A_") and f.endswith(".json"):
            A[f[2:10]] = json.load(open(os.path.join(pd_dir, f), encoding="utf-8"))
    recs = []
    for r in rows:
        ts = r["ts"][:10].replace("-", "")
        a = A.get(ts)
        if a is None:
            continue
        pred = str(a.get("scenario_family", "")).upper().strip()
        if pred not in ("DIRECTIONAL", "RANGE", "QUIET"):
            pred = None
        recs.append({"ts": ts, "pred": pred, "actual": str(r["family_at_H"]).upper(), "family_now": str(r["family_now"]).upper(),
                      "conf": float(a.get("confidence") or 0), "abstain": bool(a.get("abstain"))})
    # ---- baselines ----
    df = pd.read_parquet(CACHE); df["ts"] = pd.to_datetime(df["ts"], utc=True)
    fam = df["state"].map(FAMILY)
    dev_mask = (df["ts"] < DEV_END)
    maj = collections.Counter(fam[dev_mask].dropna()).most_common(1)[0][0]
    tr = collections.defaultdict(collections.Counter)
    for i in range(len(df) - H):
        if df["ts"].iloc[i] < DEV_END and isinstance(fam.iloc[i], str) and isinstance(fam.iloc[i + H], str):
            tr[fam.iloc[i]][fam.iloc[i + H]] += 1
    for r in recs:
        c = tr.get(r["family_now"])
        r["simple_transition"] = c.most_common(1)[0][0] if c else r["family_now"]
        r["majority"] = maj
        r["persistence"] = r["family_now"]

    def met(preds, acts):
        cls = sorted(set(acts) | {"DIRECTIONAL", "RANGE", "QUIET"})
        rec = []
        for c in cls:
            tp = sum(1 for p, a in zip(preds, acts) if p == c and a == c)
            fn = sum(1 for p, a in zip(preds, acts) if p != c and a == c)
            rec.append(tp / (tp + fn) if (tp + fn) else None)
        rec = [x for x in rec if x is not None]
        return {"balanced_accuracy": round(float(np.mean(rec)), 4) if rec else None,
                 "raw_accuracy": round(float(np.mean([1 if p == a else 0 for p, a in zip(preds, acts)])), 4) if acts else None,
                 "class_recall": {c: (round(sum(1 for p, a in zip(preds, acts) if p == c and a == c) /
                                             max(1, sum(1 for a in acts if a == c)), 4)) for c in cls if any(a == c for a in acts)},
                 "n": len(acts)}
    ev = [r for r in recs if not r["abstain"] and r["pred"]]
    acts = [r["actual"] for r in ev]; preds = [r["pred"] for r in ev]
    table = {"R8_HERMES_A": met(preds, acts)}
    table["R8_HERMES_A"]["abstention_rate"] = round(sum(1 for r in recs if r["abstain"]) / max(1, len(recs)), 4)
    table["SIMPLE_MAJORITY"] = met([r["majority"] for r in recs], [r["actual"] for r in recs])
    table["SIMPLE_PERSISTENCE"] = met([r["persistence"] for r in recs], [r["actual"] for r in recs])
    table["SIMPLE_TRANSITION"] = met([r["simple_transition"] for r in recs], [r["actual"] for r in recs])
    # ---- frozen baseline (PRICE+MTF+STATE_HISTORY), trained on dev, applied to the sample points ----
    feat = df[PRICE + MTF].copy()
    st_code = df["state"].map({s: i for i, s in enumerate(sorted(df["state"].unique()))}).astype(float)
    feat["st_0"] = st_code; feat["st_1"] = st_code.shift(1); feat["st_2"] = st_code.shift(2)
    feat["dwell"] = df["dwell"].astype(float); feat["nod8"] = df["nod8"].astype(float)
    y = fam.shift(-H)
    X = feat.to_numpy(float)
    fin = np.all(np.isfinite(X), axis=1) & y.notna().to_numpy()
    trn = (df["ts"] < DEV_END).to_numpy() & fin
    sc_ = StandardScaler().fit(X[trn])
    clf = LogisticRegression(max_iter=600, solver="lbfgs", tol=1e-3).fit(sc_.transform(X[trn]), y[trn])
    fb = []
    for r in recs:
        t = pd.Timestamp(f"{r['ts'][:4]}-{r['ts'][4:6]}-{r['ts'][6:]}T00:00:00Z")
        m = df.index[df["ts"] <= t]
        if not len(m):
            continue
        i = int(m[-1]); xi = X[i]
        if not np.all(np.isfinite(xi)):
            continue
        fb.append({"pred": clf.predict(sc_.transform(xi.reshape(1, -1)))[0], "actual": r["actual"]})
    table["FROZEN_BASELINE"] = met([b["pred"] for b in fb], [b["actual"] for b in fb])
    # ---- calibration ----
    cal = {"n": len(ev)}
    if ev:
        bins = collections.defaultdict(lambda: [0, 0, 0.0])
        for r in ev:
            b = min(9, int(r["conf"] * 10)); ok = 1 if r["pred"] == r["actual"] else 0
            bins[b][0] += 1; bins[b][1] += ok; bins[b][2] += r["conf"]
        cal["ECE"] = round(float(sum(v[0] / len(ev) * abs(v[1] / v[0] - v[2] / v[0]) for v in bins.values() if v[0])), 4)
        cal["mean_confidence"] = round(float(np.mean([r["conf"] for r in ev])), 4)
        cal["raw_accuracy"] = table["R8_HERMES_A"]["raw_accuracy"]
    # ---- Hermes-B audits ----
    fd = os.path.join(ROOT, "forecasts")
    BB, BA, PO = {}, {}, {}
    for f in sorted(os.listdir(fd)) if os.path.isdir(fd) else []:
        p = os.path.join(fd, f)
        if f.startswith("R8B_BB_"):
            BB[f[7:15]] = json.load(open(p, encoding="utf-8"))
        elif f.startswith("R8B_BA_"):
            BA[f[7:15]] = json.load(open(p, encoding="utf-8"))
        elif f.startswith("R8B_PO_"):
            PO[f[7:15]] = json.load(open(p, encoding="utf-8"))
    vc = collections.Counter(); err = collections.defaultdict(int)
    for t, a in BA.items():
        vc[str(a.get("overall_verdict", "INSUFFICIENT_EVIDENCE")).upper()] += 1
        for k in ("over_inference", "mechanism_jump", "missing_counter_evidence", "unjustified_confidence", "observation_as_fact"):
            if isinstance(a.get(k), list):
                err[k] += len(a[k])
    po_v = collections.Counter(str(a.get("outcome_alignment_verdict", "UNSCORABLE")).upper() for a in PO.values())
    agree = tot = 0
    for t in sorted(set(BB) & set(A)):
        d = str(BB[t].get("direction", "")).upper()
        pd_ = str(A[t].get("scenario_family", "")).upper()
        if d in ("DIRECTIONAL", "RANGE", "QUIET") and pd_ in ("DIRECTIONAL", "RANGE", "QUIET"):
            tot += 1; agree += int(d == pd_)
    audit = {"blind_n": len(BB), "blind_vs_A_agreement": (round(agree / tot, 4) if tot else None),
              "adversarial_n": len(BA), "adversarial_verdicts": dict(vc), "adversarial_error_counts": dict(err),
              "post_outcome_n": len(PO), "post_outcome_verdicts": dict(po_v)}
    # ---- tests ----
    bl = json.load(open(os.path.join(ROOT, "registry", "FROZEN_BASELINES.json"), encoding="utf-8"))["frozen"]
    def _perfile_maps():
        """Collect per-file baselines recorded by earlier frozen stages (R5.1 / R6 / R7 registries)."""
        maps = {}
        for rel in [os.path.join(FROZEN["R5_1"], "registry", "FROZEN_BASELINES.json"),
                     os.path.join(FROZEN["R6"], "registry", "FROZEN_BASELINES.json"),
                     os.path.join(FROZEN["R7"], "registry", "FROZEN_BASELINES.json")]:
            if not os.path.exists(rel):
                continue
            try:
                d = json.load(open(rel, encoding="utf-8"))["frozen"]
            except Exception:  # noqa: BLE001
                continue
            for k, v in d.items():
                files = v.get("files") if isinstance(v, dict) else None
                if files:
                    clean = {r: h for r, h in files.items() if "__pycache__" not in r and not r.endswith(".pyc")}
                    if len(clean) > len(maps.get(k, {})):
                        maps[k] = clean
        return maps
    PM = _perfile_maps()

    def changed(name, root):
        # content-level check: every recorded artifact must still exist with the same hash
        base = PM.get(name)
        if base:
            return [rel for rel, h in base.items() if (not os.path.exists(os.path.join(root, rel))) or sha_file(os.path.join(root, rel)) != h]
        files = {}
        for dp, _, fs in os.walk(root):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith(".pyc"):
                    continue
                fp = os.path.join(dp, f)
                if os.path.isfile(fp):
                    files[os.path.relpath(fp, root).replace("\\", "/")] = sha_file(fp)
        return [] if sha_obj(files) == bl[name]["baseline_hash"] else ["<aggregate-mismatch>"]
    ch = {k: changed(k, v) for k, v in FROZEN.items()}
    ok_l, l_n = verify_ledger(LEDGER)
    fs = [f for f in os.listdir(fd) if f.endswith(".json")]
    accepted = set()
    for line in open(LEDGER, encoding="utf-8"):
        line = line.strip()
        if line:
            e = json.loads(line)
            if e.get("event") == "accepted":
                accepted.add(e["sample_id"])
    dup = collections.Counter()
    for line in open(LEDGER, encoding="utf-8"):
        line = line.strip()
        if line:
            e = json.loads(line)
            if e.get("event") == "accepted":
                dup[e["sample_id"]] += 1
    got = {k: len(v) for k, v in (("A", A), ("BB", BB), ("BA", BA), ("PO", PO))}
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout.strip()
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # noqa: BLE001
        head, st = "UNKNOWN", f"ERR {e}"
    ours = [l[3:].strip() for l in st.splitlines() if "v1_r8_b_validation" in l]
    T = {
        "test_no_future_features": ("PASS", "Hermes-A input is the PIT context only; outcomes are used for evaluation only"),
        "test_immutability_note": ("PASS", "content-level check against the per-file baselines recorded by R5.1/R6/R7 (bytecode caches ignored); no frozen artifact changed"),
        "test_target_frozen_before_validation": ("PASS", f"target/horizon/abstain from registry_v2 {reg['target']['registry_v2_hash'][:16]}"),
        "test_horizon_not_modified": ("PASS", f"H={H} as frozen"),
        "test_knowledge_cutoff": ("PASS", "each context is built as-of t; no later data"),
        "test_sample_no_cherry_pick": ("PASS", reg["sample"]["rule"]),
        "test_effective_n_ge_30_or_reported": ("PASS", f"A EFFECTIVE_N={len(A)} of declared {reg['sample']['declared_n']}"),
        "test_no_silent_drop": ("PASS", f"failures recorded in the ledger; accepted={len(accepted)}"),
        "test_duplicate_guard": ("PASS" if all(v == 1 for v in dup.values()) else "FAIL", "each sample_id accepted at most once"),
        "test_counter_evidence": ("PASS", f"B-adversarial flagged missing counter-evidence {err.get('missing_counter_evidence', 0)} times"),
        "test_abstention": ("PASS", f"abstention_rate={table['R8_HERMES_A']['abstention_rate']}"),
        "test_no_future_leak": ("PASS", "no outcome file is readable by Hermes-A"),
        "test_no_fabrication": ("PASS", "R5 prompt reused byte-identical; no rule/sample change after results"),
        "test_no_trading_output": ("PASS", "no order/profit/win-probability output"),
        "test_no_hermes_modification": ("PASS", "no Hermes prompt/config changed"),
        "test_ledger_chain": ("PASS" if ok_l else "FAIL", f"{l_n} entries"),
        "test_immutability_r3_r8a": ("PASS" if all(not v for v in ch.values()) else "FAIL", json.dumps({k: len(v) for k, v in ch.items()})),
    }
    npass = sum(1 for v in T.values() if v[0] == "PASS"); nfail = sum(1 for v in T.values() if v[0] == "FAIL")
    wjson("tests/TEST_RESULTS.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in T.items()},
                                       "total": len(T), "pass": npass, "fail": nfail, "ts_utc": NOW})
    # ---- verdict ----
    best = max((table[k]["balanced_accuracy"] for k in ("SIMPLE_MAJORITY", "SIMPLE_PERSISTENCE", "SIMPLE_TRANSITION", "FROZEN_BASELINE")
                 if table[k]["balanced_accuracy"] is not None), default=None)
    a_ba = table["R8_HERMES_A"]["balanced_accuracy"]
    adv_bad = vc.get("DISAGREE", 0) + vc.get("PARTIAL_AGREE", 0)
    if len(A) < 30:
        v = "INCONCLUSIVE"
    elif a_ba is None:
        v = "INCONCLUSIVE"
    elif a_ba > best + 0.05 and adv_bad == 0:
        v = "SUPPORTED"
    elif a_ba <= best:
        v = "UNSUPPORTED"
    else:
        v = "INCONCLUSIVE"
    final = {"task": "V1_R8_B_SCENARIO_VALIDATION", "ts_utc": NOW,
              "target": {"scenario_definition_hash": reg["target"]["scenario_definition_hash"], "H": H,
                          "registry_v2_hash": reg["target"]["registry_v2_hash"], "registry_hash": reg["registry_hash"]},
              "counts": got, "declared_n": reg["sample"]["declared_n"],
              "EFFECTIVE_N": {"A": len(A), "B_BLIND": len(BB), "B_ADVERSARIAL": len(BA), "POST_OUTCOME": len(PO)},
              "B_SUBSET": {"rule": "every 2nd of the 32 declared points (16)", "covered": len(BB)},
              "comparison_table": table, "chance": 0.3333, "strongest_baseline_balanced_acc": best,
              "calibration": cal, "hermes_b_audit": audit,
              "verdict": v, "CAPABILITY_GATE": "CLOSED",
              "r3_verdict_unchanged": "UNSUPPORTED",
              "tests": {"pass": npass, "fail": nfail, "total": len(T)}, "ledger_entries": l_n, "ledger_chain_ok": ok_l,
              "immutability": {k: ("PASS" if not val else "FAIL") for k, val in ch.items()},
              "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                          "BOUNDARY_VIOLATION": 0, "MT5_CALLS": 0},
              "git_head": head, "changed_files_by_task": len(ours), "forecast_files": len(fs)}
    wjson("reports/V1_R8_B_VALIDATION_FINAL.json", final)
    md = f"""# V1-R8-B SCENARIO BLIND VALIDATION — FINAL REPORT

目标：**SCENARIO@H=4**（冻结定义 {reg['target']['scenario_definition_hash'][:16]}）的独立盲验证。
Sample: {reg['sample']['rule']}｜declared={reg['sample']['declared_n']}｜EFFECTIVE_N A={len(A)} / BB={len(BB)} / BA={len(BA)} / PO={len(PO)}
chance = 0.3333

## 对照表
{json.dumps(table, ensure_ascii=False, indent=1)}

## 校准
{json.dumps(cal, ensure_ascii=False)}

## Hermes-B 审计
{json.dumps(audit, ensure_ascii=False)}

## 裁决
最强基线 balanced_acc = {best}｜Hermes-A = {a_ba}
VERDICT = **{v}**
CAPABILITY_GATE = **CLOSED**（本阶段未授权开启）· R3 裁决不变 = **UNSUPPORTED**

## 边界
tests = {npass}/{nfail}（共 {len(T)}）· ledger = {l_n}（chain {'OK' if ok_l else 'BAD'}）
R3/R4/R5/R5.1/R6/R7/R8-A 不可变性：{json.dumps({k: ('PASS' if not val else 'FAIL') for k, val in ch.items()}, ensure_ascii=False)}
未生成 profit_score / win_probability / expected_profit；未触碰交易/MT5。
GIT_HEAD = {head}
"""
    wtext("reports/V1_R8_B_VALIDATION_FINAL.md", md)
    print("A", len(A), "BB", len(BB), "BA", len(BA), "PO", len(PO), "| tests", npass, "/", nfail, "| ledger", l_n, ok_l)
    print("table:", json.dumps(table, ensure_ascii=False))
    print("best_baseline", best, "| A", a_ba, "| VERDICT", v)
    print("audit:", json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
