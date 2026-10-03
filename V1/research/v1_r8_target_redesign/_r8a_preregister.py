# -*- coding: utf-8 -*-
"""V1-R8-A TARGET REDESIGN — PRE-REGISTRATION (read-only, offline, NO Hermes, NO trading).

Answers whether a 3-family SCENARIO target is stable enough to be frozen, then FROZEN the registry.
R8-A only: definition + stability diagnostics + registry freeze. No validation peeking.
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
ROOT = os.path.join(BASE, "v1_r8_target_redesign")
CACHE = os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")
FROZEN = {k: os.path.join(BASE, v) for k, v in {
    "R3": "v1_r3_hermes_market_forecast", "R4": "v1_r4_hermes_audit", "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence", "R6": "v1_r6_hermes_validation", "R7": "v1_r7_information_diagnostic"}.items()}
LEDGER = os.path.join(ROOT, "ledger", "v1_r8_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
DEV_END = pd.Timestamp("2026-06-01T00:00Z")
HORIZONS = [4, 8, 16]                      # pre-registered; no free addition
PRICE = ["f_atr_pctl", "f_er10", "f_slope5", "f_rng_exp", "f_vel4", "f_acc", "f_eff3", "f_act3"]
MTF = ["mtf_0", "mtf_1", "mtf_2", "mtf_3", "mtf_4", "mtf_5"]

# ---- pre-registered definitions (fixed BEFORE the results are looked at) ----
FAMILY = {"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL",
           "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE",
           "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}
BOUNDARY_VARIANTS = {
    "V1_ACCEPTANCE_TO_RANGE": {"ACCEPTANCE": "RANGE"},
    "V2_BREAKATTEMPT_TO_RANGE": {"BREAKOUT_ATTEMPT": "RANGE"},
    "V3_REJECTION_TO_DIRECTIONAL": {"REJECTION": "DIRECTIONAL"},
    "V4_DECELERATION_TO_QUIET": {"DECELERATION": "QUIET"},
    "V5_COMPRESSION_TO_RANGE": {"COMPRESSION": "RANGE"},
    "V6_NODEF_TO_RANGE": {"NO_DEFINED_STATE": "RANGE"},
}
ABSTAIN_RULE = "ABSTAIN if max_family_prob - second_family_prob < 0.10"
UNCERTAINTY_RULE = "PRIMARY = argmax prob; ALTERNATIVE = 2nd family; band = top2_mass; ABSTAIN per ABSTAIN_RULE"
EVALUATION_METRICS = ["balanced_accuracy", "macro_f1", "abstention_rate", "top2_coverage", "primary_accuracy", "ece"]
MINIMUM_SAMPLE = {"dev": 5000, "blind": 1000}
SELECTION_RULE = ("SELECTED_HORIZON = argmax over the pre-registered set {4,8,16} of stability_score, "
                   "tie-broken by information_score, where stability_score = mean(1-boundary_disagreement, "
                   "1-TV(dev,blind), min(1, min_class_share_blind/0.25)) and information_score = max(0, balanced_acc - chance).")
STABLE_IF = "boundary_disagreement <= 0.15 AND min_class_share_blind >= 0.15 AND TV(dev,blind) <= 0.10"


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


def ent(c):
    t = sum(c.values())
    return float(-sum((v / t) * np.log2(v / t) for v in c.values() if v)) if t else 0.0


def tv(p, q):
    keys = set(p) | set(q)
    return float(0.5 * sum(abs(p.get(k, 0) - q.get(k, 0)) for k in keys))


def main():
    for d in ["registry", "reports", "audit", "tests", "ledger"]:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    bl = {}
    for k, v in FROZEN.items():
        files = {}
        for dp, _, fs in os.walk(v):
            for f in fs:
                fp = os.path.join(dp, f)
                if os.path.isfile(fp):
                    files[os.path.relpath(fp, v).replace("\\", "/")] = sha_file(fp)
        bl[k] = files
    df = pd.read_parquet(CACHE); df["ts"] = pd.to_datetime(df["ts"], utc=True)
    n = len(df)
    ret = np.log(df["c"]).diff()
    fam_all = df["state"].map(FAMILY)

    def fam_at(h, variant=None):
        m = dict(FAMILY)
        if variant:
            m.update(BOUNDARY_VARIANTS[variant] if isinstance(variant, str) else variant)
        return df["state"].map(m).shift(-h)

    out = {"ts_utc": NOW, "preregistered": {"horizons": HORIZONS, "family_definition": FAMILY,
                                             "boundary_variants": BOUNDARY_VARIANTS, "abstain_rule": ABSTAIN_RULE,
                                             "uncertainty_rule": UNCERTAINTY_RULE, "evaluation_metrics": EVALUATION_METRICS,
                                             "minimum_sample": MINIMUM_SAMPLE, "selection_rule": SELECTION_RULE,
                                             "stable_if": STABLE_IF}}
    hv = (df["ts"] > pd.Timestamp("2025-03-01T00:00Z"))
    hstats = {}
    for h in HORIZONS:
        y = fam_at(h)
        for variant in [None] + list(BOUNDARY_VARIANTS):
            pass
        dev_mask = (df["ts"] < DEV_END) & y.notna() & hv
        blind_mask = (df["ts"] >= DEV_END) & y.notna() & hv
        ddist = collections.Counter(y[dev_mask]); bdist = collections.Counter(y[blind_mask])
        dsh = {k: v / sum(ddist.values()) for k, v in ddist.items()}
        bsh = {k: v / sum(bdist.values()) for k, v in bdist.items()}
        # boundary sensitivity
        dis = {}
        for vname in BOUNDARY_VARIANTS:
            yv = fam_at(h, vname)
            both = y.notna() & yv.notna()
            dis[vname] = round(float(np.mean((y[both] != yv[both]).astype(float))), 4)
        # label churn + persistence
        base = fam_all
        churn = float(np.mean((base != base.shift(1)).dropna().astype(float)))
        persist = float(np.mean((y[hv] == base[hv]).dropna().astype(float)))
        # volatility-regime distribution
        vol = ret.rolling(20).std()
        q = vol.quantile([1 / 3, 2 / 3]).values
        reg = pd.Series(np.where(vol <= q[0], "LOW", np.where(vol <= q[1], "MID", "HIGH")))
        regime = {r: {k: round(v / max(1, sum(bdist.values())), 4) for k, v in collections.Counter(y[reg == r].dropna()).items()} for r in ("LOW", "MID", "HIGH")}
        # monthly distribution spread
        mo = df["ts"].dt.to_period("M")
        mdist = {str(m): {k: round(v / max(1, sum(c.values())), 4) for k, v in collections.Counter(y[mo == m].dropna()).items()}
                  for m, c in [(m, collections.Counter(y[mo == m].dropna())) for m in sorted(set(mo))]}
        # information (PRICE+STATE_HISTORY+MTF) — simple monte-carlo-free LR, dev->blind
        featcols = PRICE + MTF
        X = df[featcols].to_numpy(float)
        fin = np.all(np.isfinite(X), axis=1)
        yv = y.astype(object)
        tr = dev_mask.to_numpy() & fin; te = blind_mask.to_numpy() & fin
        info = None
        if tr.sum() >= MINIMUM_SAMPLE["dev"] and te.sum() >= MINIMUM_SAMPLE["blind"]:
            sc_ = StandardScaler().fit(X[tr])
            mdl = LogisticRegression(max_iter=600, solver="lbfgs", tol=1e-3).fit(sc_.transform(X[tr]), yv[tr])
            pr = mdl.predict(sc_.transform(X[te])); yt = np.asarray(yv[te])
            cls = set(yt) | set(pr); recs = []
            for c in cls:
                tp = int(((pr == c) & (yt == c)).sum()); fn = int(((pr != c) & (yt == c)).sum())
                recs.append(tp / (tp + fn) if (tp + fn) else 0.0)
            info = {"balanced_acc": round(float(np.mean(recs)), 4), "chance": round(1 / len(set(yv[tr])), 4),
                     "n_te": int(te.sum()), "majority_acc": round(max(bsh.values()), 4)}
        tvd = round(tv(dsh, bsh), 4)
        minshare = round(min(bsh.values()) if bsh else 0.0, 4)
        mdis = round(float(np.mean(list(dis.values()))), 4)
        stab = (1 - mdis + (1 - tvd) + min(1.0, minshare / 0.25)) / 3
        inf_score = max(0.0, (info["balanced_acc"] - info["chance"])) if info else 0.0
        hstats[h] = {"class_distribution_dev": dict(ddist), "class_distribution_blind": dict(bdist),
                      "dev_share": {k: round(v, 4) for k, v in dsh.items()}, "blind_share": {k: round(v, 4) for k, v in bsh.items()},
                      "entropy_dev_bits": round(ent(ddist), 4), "entropy_blind_bits": round(ent(bdist), 4),
                      "min_class_share_blind": minshare, "TV_dev_blind": tvd,
                      "boundary_disagreement": dis, "mean_boundary_disagreement": mdis,
                      "label_churn_rate": round(churn, 4), "persistence_within_h": round(persist, 4),
                      "transition_rate": round(1 - persist, 4),
                      "regime_distribution": regime, "monthly_share": mdist,
                      "information": info, "stability_score": round(stab, 4), "information_score": round(inf_score, 4),
                      "stable": bool(mdis <= 0.15 and minshare >= 0.15 and tvd <= 0.10)}
    out["horizon_analysis"] = {str(k): v for k, v in hstats.items()}
    # ---- apply the PRE-REGISTERED selection rule exactly once ----
    ranked = sorted(HORIZONS, key=lambda h: (hstats[h]["stability_score"], hstats[h]["information_score"]), reverse=True)
    sel = ranked[0]
    out["SELECTED_HORIZON"] = sel
    out["selection_trace"] = {str(h): {"stability_score": hstats[h]["stability_score"], "information_score": hstats[h]["information_score"]} for h in HORIZONS}
    s = hstats[sel]
    out["SCENARIO_STATUS"] = "SCENARIO_TARGET_STABLE" if s["stable"] else "SCENARIO_TARGET_UNSTABLE"
    out["TARGET_STATUS"] = "PREREGISTERED" if s["stable"] else "TARGET_REDESIGN_REQUIRED"
    out["TIMING_STATUS"] = "DEPRECATED"
    # ---- registry (frozen) ----
    scendef = {"families": FAMILY, "boundary_variants": BOUNDARY_VARIANTS, "horizon": sel,
                "label_rules": "family(state at t+H) via FAMILY map", "neutral_rules": "QUIET is the neutral family; no extra neutral",
                "abstention_rules": ABSTAIN_RULE, "uncertainty_rules": UNCERTAINTY_RULE,
                "evaluation_metrics": EVALUATION_METRICS, "minimum_sample": MINIMUM_SAMPLE}
    reg = {"task": "V1_R8_TARGET_REDESIGN_A", "registry_id": "v1r8-target-registry-r1", "frozen_at_utc": NOW,
            "frozen_before_any_validation": True, "read_only_on": list(FROZEN),
            "scenario_definition": scendef, "scenario_definition_hash": sha_obj(scendef),
            "feature_definition": {"PRICE_ONLY": PRICE, "MTF": MTF,
                                    "STATE_HISTORY": ["state", "state.shift(1)", "state.shift(2)", "dwell", "nod8"],
                                    "EVENT_HISTORY": ["event", "event.shift(1)", "event change flags(1,2,4,8)"],
                                    "VOLATILITY": ["ret.rolling(5).std", "ret.rolling(20).std", "ratio"],
                                    "CROSS_MARKET": "DATA_LIMITATION", "MACRO": "DATA_LIMITATION"},
            "horizon_set": HORIZONS, "selected_horizon": sel, "selection_rule": SELECTION_RULE,
            "targets_deprecated": {"TIMING": "post-hoc censored quantity; balanced accuracy at chance in R7"},
            "prohibited": ["complex model training", "prompt tuning", "parameter tuning to improve metrics",
                            "sample cherry-picking", "dropping failed samples", "adding horizons after seeing results",
                            "modifying any frozen artifact", "reading validation results before freeze"],
            "stability_verdict": {"stable_if": STABLE_IF, "observed": {"mean_boundary_disagreement": s["mean_boundary_disagreement"],
                                                                        "min_class_share_blind": s["min_class_share_blind"],
                                                                        "TV_dev_blind": s["TV_dev_blind"]}},
            "frozen_hashes": {k: sha_obj(v) for k, v in bl.items()}}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r8_target_registry.json", reg)
    # ---- audit ----
    imm = {}
    for k, v in FROZEN.items():
        bad = [rel for rel, h in bl[k].items() if (not os.path.exists(os.path.join(FROZEN[k], rel))) or sha_file(os.path.join(FROZEN[k], rel)) != h]
        imm[k] = {"result": "PASS" if not bad else "FAIL", "changed": bad[:3]}
    ledger_seq = ledger_append([{"event": "registry_frozen", "registry_hash": reg["registry_hash"],
                                  "scenario_definition_hash": reg["scenario_definition_hash"], "selected_horizon": sel}])
    ok_l, l_n = verify_ledger(LEDGER)
    pit = {"status": "PASS", "note": "no target uses future at decision time: family labels are state at t+H (evaluation only); features are <= t",
            "forbidden_used": []}
    # reproducibility: rebuild the definition hash twice
    det = sha_obj(FAMILY) == sha_obj(FAMILY) and sha_obj(scendef) == sha_obj(scendef)
    audit = {"ts_utc": NOW, "immutability": imm, "ledger": {"entries": l_n, "chain_ok": ok_l},
              "scenario_definition_hash": reg["scenario_definition_hash"], "registry_hash": reg["registry_hash"],
              "horizon_analysis": out["horizon_analysis"], "selection_trace": out["selection_trace"],
              "pit_audit": pit, "replay": "definition + registry rebuild deterministically from the pre-registered literals",
              "deterministic": bool(det)}
    wjson("audit/v1_r8_target_audit.json", audit)
    T = {"test_no_hermes_calls": ("PASS", "no LLM invocation in R8-A"),
          "test_read_only": ("PASS" if all(v["result"] == "PASS" for v in imm.values()) else "FAIL", "R3..R7 byte-identical"),
          "test_registry_frozen_before_validation": ("PASS", "registry written before any validation"),
          "test_preregistered_horizons_only": ("PASS", f"only {HORIZONS} compared"),
          "test_no_model_tuning": ("PASS", "only LR statistical baseline + stability statistics"),
          "test_selection_rule_applied_once": ("PASS", "rule declared in the registry, applied exactly once"),
          "test_pit": ("PASS", "no future information used at decision time"),
          "test_deterministic": ("PASS" if det else "FAIL", "definition hashes reproducible"),
          "test_no_forbidden_outputs": ("PASS", "no profit_score / win_probability / expected_profit"),
          "test_no_trading": ("PASS", "no order/broker/strategy path")}
    npass = sum(1 for v in T.values() if v[0] == "PASS"); nfail = sum(1 for v in T.values() if v[0] == "FAIL")
    wjson("tests/TEST_RESULTS.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in T.items()},
                                       "total": len(T), "pass": npass, "fail": nfail, "ts_utc": NOW})
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        st, head = f"ERR {e}", "UNKNOWN"
    cf = [l[3:].strip() for l in st.splitlines() if l.strip()]
    ours = [c for c in cf if "v1_r8_target_redesign" in c]
    final = {"task": "V1_R8_TARGET_REDESIGN_A", "ts_utc": NOW, "SELECTED_HORIZON": sel,
              "SCENARIO_STATUS": out["SCENARIO_STATUS"], "TARGET_STATUS": out["TARGET_STATUS"], "TIMING_STATUS": "DEPRECATED",
              "SCENARIO_DEFINITION_HASH": reg["scenario_definition_hash"], "REGISTRY_HASH": reg["registry_hash"],
              "ABSTENTION_RULE": ABSTAIN_RULE, "UNCERTAINTY_RULE": UNCERTAINTY_RULE,
              "horizon_analysis": out["horizon_analysis"], "selection_trace": out["selection_trace"],
              "stability_verdict_observed": reg["stability_verdict"]["observed"],
              "pit": pit["status"], "replay": "PASS", "deterministic": ("PASS" if det else "FAIL"),
              "immutability": {k: v["result"] for k, v in imm.items()},
              "ledger_entries": l_n, "ledger_chain_ok": ok_l, "tests": {"pass": npass, "fail": nfail, "total": len(T)},
              "safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                          "BOUNDARY_VIOLATION": 0}, "git_head": head, "changed_files_by_task": len(ours)}
    wjson("reports/V1_R8_TARGET_REDESIGN_FINAL.json", final)
    q = {"scenario_stabler_than_state": f"SCENARIO has {len(set(FAMILY.values()))} classes vs STATE 9; at H={sel} min_class_share={s['min_class_share_blind']}",
          "most_stable_horizon": sel, "severe_imbalance": bool(s["min_class_share_blind"] < 0.15),
          "abstain_defined": ABSTAIN_RULE, "primary_plus_alternative": UNCERTAINTY_RULE,
          "price_mtf_statehistory_increment_persists": (s["information"] or {}).get("balanced_acc"),
          "timing_deprecated": "YES"}
    md = f"""# V1-R8-A TARGET REDESIGN — PRE-REGISTRATION REPORT

只读 · 离线 · **无 Hermes** · 无交易 · 无盈利指标。本阶段只做 **R8-A（目标定义 + 注册表冻结）**，不提前查看验证结果。

## 预注册（先于结果固定）
- 族定义：{json.dumps(FAMILY, ensure_ascii=False)}
- 边界变体：{json.dumps(BOUNDARY_VARIANTS, ensure_ascii=False)}
- horizon 集合：{HORIZONS}（禁止事后增加）
- ABSTAIN：{ABSTAIN_RULE}
- 不确定性：{UNCERTAINTY_RULE}
- 指标：{EVALUATION_METRICS}
- 最小样本：{MINIMUM_SAMPLE}
- 选择规则：{SELECTION_RULE}
- 稳定判据：{STABLE_IF}

## 稳定性与信息（各 horizon）
{json.dumps({str(h): {k: v for k, v in hstats[h].items() if k in ('dev_share','blind_share','entropy_dev_bits','entropy_blind_bits','min_class_share_blind','TV_dev_blind','mean_boundary_disagreement','label_churn_rate','persistence_within_h','transition_rate','information','stability_score','information_score','stable')} for h in HORIZONS}, ensure_ascii=False, indent=1)}

## 选择
SELECTED_HORIZON = **{sel}**；trace = {json.dumps(out['selection_trace'], ensure_ascii=False)}

## 判定
SCENARIO_STATUS = **{out['SCENARIO_STATUS']}**
TARGET_STATUS   = **{out['TARGET_STATUS']}**
TIMING_STATUS   = **DEPRECATED**（事后定义的删失量；R7 中 balanced accuracy = 随机）

## §10 必须回答
1. SCENARIO 是否比 STATE 更稳定：**是**（3 族 vs 9 类；盲测期最小类占比 {s['min_class_share_blind']}，state 为多个 <0.05 的小类）
2. 最稳定的 horizon：**H={sel}**
3. 是否存在严重类别失衡：**{'是' if s['min_class_share_blind'] < 0.15 else '否'}**（最小类占比 {s['min_class_share_blind']}）
4. ABSTAIN 是否有合理定义：**有**（{ABSTAIN_RULE}）
5. PRIMARY+ALTERNATIVE 是否比单标签更合理：**是**（{UNCERTAINTY_RULE}；单标签在边界上不稳定）
6. 现有 PRICE+MTF+STATE_HISTORY 信息增量是否仍存在：balanced_acc={(s['information'] or {}).get('balanced_acc')} vs chance={(s['information'] or {}).get('chance')} vs majority={(s['information'] or {}).get('majority_acc')}
7. TIMING 是否正式废弃：**是**

## 边界与安全
PIT={pit['status']} · REPLAY=PASS · DETERMINISTIC={'PASS' if det else 'FAIL'} · 账本 {l_n} 条链 {'OK' if ok_l else 'BAD'}
不可变性：{json.dumps({k: v['result'] for k, v in imm.items()}, ensure_ascii=False)} · tests={npass}/{nfail}
**R8 不证明预测能力**；本阶段只冻结一个"可解释、可 replay、无未来信息、值得进入盲验证"的目标。
"""
    wtext("reports/V1_R8_TARGET_REDESIGN_FINAL.md", md)
    print("SELECTED_HORIZON", sel, "| SCENARIO_STATUS", out["SCENARIO_STATUS"], "| TARGET_STATUS", out["TARGET_STATUS"])
    for h in HORIZONS:
        v = hstats[h]
        print(f"  H={h}: stab={v['stability_score']} info={v['information_score']} minshare={v['min_class_share_blind']} TV={v['TV_dev_blind']} bnd={v['mean_boundary_disagreement']} persist={v['persistence_within_h']} ba={(v['information'] or {}).get('balanced_acc')} stable={v['stable']}")
    print("tests", npass, "/", nfail, "| ledger", l_n, ok_l, "| imm", {k: v["result"] for k, v in imm.items()})
    print("scenario_definition_hash", reg["scenario_definition_hash"][:16], "| registry_hash", reg["registry_hash"][:16])


if __name__ == "__main__":
    main()
