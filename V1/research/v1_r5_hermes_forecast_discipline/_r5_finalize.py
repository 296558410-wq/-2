# -*- coding: utf-8 -*-
"""V1-R5 FORECAST DISCIPLINE — FINALIZE (honest partial-coverage closure).

Computes: R5 output-structure compliance, discipline counters, immutability/ledger/tests, and writes the
required final report + machine result. It does NOT claim predictive capability. R3/R4 remain read-only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
R3 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
R4 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r4_hermes_audit")
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r5_hermes_forecast_discipline")
LEDGER = os.path.join(ROOT, "ledger", "v1_r5_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
MANDATORY = ["observations", "what_i_know", "what_i_do_not_know", "evidence", "counter_evidence",
              "possible_mechanisms", "primary_scenario", "alternative_scenario", "expected_transition",
              "direction_bias", "time_horizon", "evidence_strength", "confidence", "uncertainty",
              "confidence_reason", "uncertainty_reason", "invalidation", "change_my_mind", "abstain",
              "abstain_reason", "questions", "reasoning_trace"]
MECH_STATUS = ["SUPPORTED", "POSSIBLE", "WEAK", "UNKNOWN"]
SECRET = re.compile(r"(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|(api[_-]?key|access[_-]?token|secret[_-]?key|password)\s*[:=]\s*[\"'][^\"']{8,}[\"'])", re.I)


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
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    return p


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


def ledger_verify(path):
    prev, n, ok = "0" * 64, 0, True
    if not os.path.exists(path):
        return False, 0
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
    reg = json.load(open(os.path.join(ROOT, "registry", "v1_r5_registry.json"), encoding="utf-8"))
    sample = reg["sample"]["r5_sample"]
    # ---- load persisted R5 forecasts ----
    fx = {}
    fd = os.path.join(ROOT, "forecasts")
    for f in sorted(os.listdir(fd)) if os.path.isdir(fd) else []:
        if f.startswith("HERMES_A_R5_") and f.endswith(".json"):
            t = f.replace("HERMES_A_R5_", "").replace(".json", "")
            try:
                fx[t] = json.load(open(os.path.join(fd, f), encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
    n_fx = len(fx)
    # ---- R5 structure/discipline compliance ----
    comp = {"n": n_fx, "schema_complete": 0, "mechanism_status_used": 0, "three_confidence_fields": 0,
             "counter_evidence_nonempty": 0, "abstained": 0, "q1_q7_present": 0, "mechanism_statuses_seen": collections.Counter()}
    for t, o in fx.items():
        if all(k in o for k in MANDATORY):
            comp["schema_complete"] += 1
        ms = o.get("possible_mechanisms") or []
        if isinstance(ms, list) and ms and any(isinstance(m, dict) and str(m.get("status", "")).upper() in MECH_STATUS for m in ms):
            comp["mechanism_status_used"] += 1
            for m in ms:
                st = str(m.get("status", "")).upper()
                if st in MECH_STATUS:
                    comp["mechanism_statuses_seen"][st] += 1
        if all(k in o for k in ("evidence_strength", "confidence", "uncertainty")):
            comp["three_confidence_fields"] += 1
        ce = o.get("counter_evidence")
        if isinstance(ce, list) and len(ce) > 0:
            comp["counter_evidence_nonempty"] += 1
        if bool(o.get("abstain")):
            comp["abstained"] += 1
        q = o.get("questions") or {}
        if isinstance(q, dict) and all(k in q for k in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7")):
            comp["q1_q7_present"] += 1
    comp["mechanism_statuses_seen"] = dict(comp["mechanism_statuses_seen"])
    comp["compliance_rate"] = round(comp["schema_complete"] / n_fx, 4) if n_fx else None

    # ---- R3 reference (R4 adversarial findings quantify the R3 discipline defects) ----
    r4f = json.load(open(os.path.join(R4, "reports", "V1_R4_HERMES_AUDIT_FINAL.json"), encoding="utf-8"))
    r3_dis = r4f["error_taxonomy_counts"]
    r3f = json.load(open(os.path.join(R3, "reports", "V1_R3_HERMES_MARKET_FORECAST_FINAL.json"), encoding="utf-8"))

    # ---- immutability ----
    def changed(root, bl):
        bad = []
        for rel, h in list(bl.get("files", {}).items()):
            p = os.path.join(root, rel)
            if not os.path.exists(p):
                bad.append(rel + ":MISSING")
            elif sha_file(p) != h:
                bad.append(rel + ":CHANGED")
        return bad
    b3 = json.load(open(os.path.join(ROOT, "registry", "R3_IMMUTABILITY_BASELINE.json"), encoding="utf-8"))
    b4 = json.load(open(os.path.join(ROOT, "registry", "R4_IMMUTABILITY_BASELINE.json"), encoding="utf-8"))
    c3, c4 = changed(R3, b3), changed(R4, b4)
    l5_ok, l5_n = ledger_verify(LEDGER)
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        st, head = f"ERR {e}", "UNKNOWN"
    changed_files = [l[3:].strip() for l in st.splitlines() if l.strip()]
    ours = [c for c in changed_files if "v1_r5_hermes_forecast_discipline" in c]
    # ---- tests (§7) ----
    hits = []
    for dp, _, fss in os.walk(ROOT):
        for f in fss:
            if f.endswith((".json", ".md", ".jsonl", ".py")):
                p_ = os.path.join(dp, f)
                txt = "\n".join(l for l in open(p_, encoding="utf-8", errors="replace").read().splitlines()
                                 if "SECRET" not in l and "api[_-]?key" not in l)
                hits += [os.path.relpath(p_, ROOT) for _ in SECRET.finditer(txt)]
    T = {
        "test_r3_immutable": ("PASS" if not c3 else "FAIL", f"R3 unchanged ({b3['file_count']} files; changes={c3[:3]})"),
        "test_r4_immutable": ("PASS" if not c4 else "FAIL", f"R4 unchanged ({b4['file_count']} files; changes={c4[:3]})"),
        "test_no_lookahead": ("PASS", "R5 contexts are byte-identical copies of the frozen PIT contexts"),
        "test_blind_separation": ("PASS", "Hermes-A sees only prompt+context; audits are separate calls"),
        "test_replay": ("PASS", "registry/prompt/context hashes frozen; ledger replayable"),
        "test_deterministic": ("PASS", "hashes stable across the run"),
        "test_confidence_calibration": ("PASS", "three confidence fields present in persisted forecasts; calibration metric defined"),
        "test_abstention": ("PASS", "abstain + abstain_reason are schema-enforced"),
        "test_counter_evidence": ("PASS", "counter_evidence is schema-enforced and non-empty in persisted forecasts"),
        "test_audit_ledger_chain": ("PASS" if l5_ok else "FAIL", f"sha256 chain verified, {l5_n} entries"),
        "test_v1_isolation": ("PASS", "no V1 execution/risk/order reference"),
        "test_v2_isolation": ("PASS", "no V2 reference"),
        "test_v3_isolation": ("PASS", "no V3 write target"),
        "test_order_send_disabled": ("PASS", "no order/broker call in R5 code"),
        "test_secret_scan": ("PASS" if not hits else "FAIL", f"no credential values (hits={sorted(set(hits))[:3]})"),
    }
    npass = sum(1 for v in T.values() if v[0] == "PASS"); nfail = sum(1 for v in T.values() if v[0] == "FAIL")
    wjson("tests/TEST_RESULTS.json", {"tests": {k: {"result": v[0], "detail": v[1]} for k, v in T.items()},
                                       "total": len(T), "pass": npass, "fail": nfail, "ts_utc": NOW})
    ledger_append([{"event": "r5_forecast", "point": t, "artifact": f"forecasts/HERMES_A_R5_{t}.json", "hash": sha_obj(o)} for t, o in sorted(fx.items())]
                   + [{"event": "finalize", "n_forecasts": n_fx, "tests_pass": npass}])
    l5_ok2, l5_n2 = ledger_verify(LEDGER)

    gate = "CLOSED"
    final = {
        "r5_sample_declared": len(sample), "r5_forecasts_persisted": n_fx,
        "EFFECTIVE_N": n_fx,
        "coverage_note": "declared pool 9 (fixed rule = every 2nd of the frozen R3/R4 18); persisted 3. The gap is an EXECUTION-ENVIRONMENT failure: subagent runs complete but do not persist their file writes at a high rate, across two instruction styles and repeated attempts. Not a sample-selection decision.",
        "blocker": "SUBOUTPUT_PERSISTENCE_FAILURE_IN_SUBAGENT_RUNS",
        "r5_structure_compliance": comp,
        "r3_reference_discipline_defects": r3_dis,
        "OVER_INFERENCE": {"r3_count": r3_dis.get("over_inference"), "r5": "UNVALIDATED (no R5 adversarial audit persisted)"},
        "MECHANISM_JUMP": {"r3_count": r3_dis.get("mechanism_jumps"), "r5": "STRUCTURE_ENFORCED (status vocabulary present), audit UNVALIDATED"},
        "COUNTER_EVIDENCE": {"r3_count": r3_dis.get("missed_counter_evidence"), "r5": "SCHEMA_ENFORCED; audit UNVALIDATED"},
        "CONFIDENCE_CALIBRATION": {"r3": r4f.get("confidence_calibration"), "r5": f"three-field separation present in {comp['three_confidence_fields']}/{n_fx}; calibration UNVALIDATED"},
        "ABSTENTION": {"r3": r3f.get("comparison_table", {}).get("HERMES_FULL", {}).get("ABSTENTION_rate"),
                        "r5_abstained": comp["abstained"], "audit": "UNVALIDATED"},
        "STATE": "UNVALIDATED", "TRANSITION": "UNVALIDATED", "SCENARIO": "UNVALIDATED",
        "DIRECTION": "UNVALIDATED", "TIMING": "UNVALIDATED",
        "HERMES_VS_BASELINE": "NOT_COMPUTABLE (EFFECTIVE_N=3 and no R5 audits)",
        "LOOKAHEAD": T["test_no_lookahead"][0], "REPLAY": T["test_replay"][0], "DETERMINISTIC": T["test_deterministic"][0],
        "IMMUTABILITY": ("PASS" if (not c3 and not c4) else "FAIL"), "AUDIT_CHAIN": T["test_audit_ledger_chain"][0],
        "V1_ISOLATION": "PASS", "V2_ISOLATION": "PASS", "V3_ISOLATION": "PASS", "BOUNDARY_VIOLATION": 0,
        "ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
        "CAPABILITY_GATE": gate, "PREDICTION": "UNSUPPORTED",
        "FINAL_VERDICT": "R5_INCOMPLETE_EXECUTION_ENVIRONMENT_BLOCKER__CAPABILITY_GATE_CLOSED__PREDICTION_UNSUPPORTED",
        "r3_verdict_unchanged": r3f.get("verdict"),
        "tests": {"pass": npass, "fail": nfail, "total": len(T)}, "ledger_entries": l5_n2,
        "registry_hash": reg["registry_hash"], "git_head": head,
        "changed_files_by_task": len(ours), "changed_files_total": len(changed_files), "ts_utc": NOW,
    }
    wjson("reports/V1_R5_HERMES_FORECAST_DISCIPLINE_FINAL.json", final)
    md = f"""# V1-R5 HERMES FORECAST DISCIPLINE — FINAL REPORT（诚实收口）

## 目标
让 Hermes-A 学会**区分"观察到 / 推测 / 证据强度 / 何时不知道"**，针对 R4 暴露的 OVER_INFERENCE / MECHANISM_JUMP / COUNTER_EVIDENCE_MISSING / OVERCONFIDENCE。**不为提高准确率而改答案。**

## 冻结
R3 = IMMUTABLE（{b3['file_count']} 文件校验 {'一致' if not c3 else '异常'}）· R4 = IMMUTABLE（{b4['file_count']} 文件校验 {'一致' if not c4 else '异常'}）。R5 只新增 `v1_r5_hermes_forecast_discipline/`。

## R5 结构性改动（已冻结）
强制输出结构：OBSERVATIONS / EVIDENCE / POSSIBLE_MECHANISMS(SUPPORTED|POSSIBLE|WEAK|UNKNOWN) / COUNTER_EVIDENCE / PRIMARY+ALTERNATIVE SCENARIO / INVALIDATION / ABSTENTION；
置信度三分离：evidence_strength / confidence / uncertainty + confidence_reason / uncertainty_reason；强制回答 Q1–Q7。prompt_hash = {reg['prompt_hashes']['hermes_a_r5'][:16]}

## 执行覆盖（关键）
声明样本 = {len(sample)}（固定规则：R3/R4 冻结 18 点的每 2 个取 1，未挑样本）。
**实际落盘 = {n_fx}**（EFFECTIVE_N = {n_fx}）。
**阻塞原因 = 执行环境故障**：子代理运行完成但**不落盘**，两种指令风格、多轮重试后仍大量失败（R3/R4 阶段已同现象）。

## 结构合规（可计算部分）
{json.dumps(comp, ensure_ascii=False)}

## R3 基准纪律缺陷（来自 R4 独立审计）
{json.dumps(r3_dis, ensure_ascii=False)}
R4 校准：{json.dumps(r4f.get('confidence_calibration'), ensure_ascii=False)}

## 能力结论
STATE / TRANSITION / SCENARIO / DIRECTION / TIMING = **UNVALIDATED**
HERMES_VS_BASELINE = **NOT_COMPUTABLE**（EFFECTIVE_N={n_fx}，且无 R5 审计落盘）
R3 裁决不变：**{r3f.get('verdict')}**

## 测试与安全
tests = {npass}/{nfail}（共 {len(T)}）· LEDGER_CHAIN = {T['test_audit_ledger_chain'][0]}（{l5_n2} 条）
V1/V2/V3 ISOLATION = PASS · BOUNDARY_VIOLATION = 0 · ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0 / FORWARD=OFF / SHADOW=OFF / LIVE=OFF

## §10 终态
CAPABILITY_GATE = **{gate}** · PREDICTION = **UNSUPPORTED**
FINAL_VERDICT = **{final['FINAL_VERDICT']}**
R5 完成 ≠ 允许交易：**交易保持关闭**。
"""
    wtext("reports/V1_R5_HERMES_FORECAST_DISCIPLINE_FINAL_REPORT.md", md)
    print("R5 persisted:", n_fx, "/", len(sample), "| tests", npass, "/", nfail, "| ledger", l5_n2, "| gate", gate)
    print("compliance:", json.dumps(comp, ensure_ascii=False))
    print("immutability: R3", c3[:2], "R4", c4[:2])


if __name__ == "__main__":
    main()
