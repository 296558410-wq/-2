# -*- coding: utf-8 -*-
"""V1-R8-A AMENDMENT 1 — pre-validation correction of the horizon selection rule.

NOT post-hoc tuning: R8-B (blind validation) has not started and no validation result exists.
The original rule ranked by stability_score, but the three stability scores are within 0.0003
(a numerical tie), so it selected the LOWEST-information horizon. Amendment 1 declares a tie
tolerance and then maximises information. Both rules and both outcomes are recorded.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r8_target_redesign"
LEDGER = os.path.join(ROOT, "ledger", "v1_r8_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
TOL = 0.005


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def ledger_append(entries):
    prev, seq = "0" * 64, 0
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


def main():
    reg1 = json.load(open(os.path.join(ROOT, "registry", "v1_r8_target_registry.json"), encoding="utf-8"))
    aud = json.load(open(os.path.join(ROOT, "audit", "v1_r8_target_audit.json"), encoding="utf-8"))
    fin = json.load(open(os.path.join(ROOT, "reports", "V1_R8_TARGET_REDESIGN_FINAL.json"), encoding="utf-8"))
    ha = aud["horizon_analysis"]
    hs = sorted(ha, key=lambda s: s)
    orig_sel = reg1["selected_horizon"]
    best_stab = max(ha[h]["stability_score"] for h in hs)
    tied = [h for h in hs if best_stab - ha[h]["stability_score"] <= TOL]
    # amended: among stability ties, maximise information_score, then stability
    amended_sel = max(tied, key=lambda h: (ha[h]["information_score"], ha[h]["stability_score"]))
    amend = {"task": "V1_R8_TARGET_REDESIGN_A", "amendment": 1, "ts_utc": NOW,
              "made_before_validation": True, "validation_started": False,
              "reason": ("the original rule ranked ONLY by stability_score, but the three stability scores are within "
                          f"{round(best_stab - min(ha[h]['stability_score'] for h in hs), 4)} (a numerical tie), so it selected the "
                          "lowest-information horizon. The pre-registration text says to compare stability AND information."),
              "original_rule": reg1["selection_rule"], "original_selected_horizon": orig_sel,
              "original_registry_hash": reg1["registry_hash"],
              "stability_tie_tolerance": TOL, "stability_tied_horizons": tied,
              "amended_rule": ("SELECTED_HORIZON = among horizons whose stability_score is within "
                                f"{TOL} of the maximum, argmax information_score, tie-broken by stability_score."),
              "amended_selected_horizon": amended_sel,
              "selection_trace": {h: {"stability_score": ha[h]["stability_score"], "information_score": ha[h]["information_score"],
                                       "balanced_acc": (ha[h]["information"] or {}).get("balanced_acc"),
                                       "chance": (ha[h]["information"] or {}).get("chance"),
                                       "min_class_share_blind": ha[h]["min_class_share_blind"], "stable": ha[h]["stable"]} for h in hs},
              "no_validation_peek": "R8-B blind validation has not been run; no outcome information was consulted"}
    amend["amendment_hash"] = sha_obj({k: v for k, v in amend.items() if k != "amendment_hash"})
    json.dump(amend, open(os.path.join(ROOT, "registry", "v1_r8_target_registry_AMENDMENT_1.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    # v2 registry = v1 + amendment (v1 kept untouched as evidence)
    reg2 = dict(reg1)
    reg2["registry_id"] = "v1r8-target-registry-r2"
    reg2["selected_horizon"] = amended_sel
    reg2["amendments"] = [amend]
    reg2["scenario_definition"]["horizon"] = amended_sel
    reg2.pop("registry_hash", None)
    reg2["registry_hash"] = sha_obj({k: v for k, v in reg2.items() if k != "registry_hash"})
    json.dump(reg2, open(os.path.join(ROOT, "registry", "v1_r8_target_registry_v2.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    # update final report + json
    fin["SELECTED_HORIZON"] = amended_sel
    fin["SELECTED_HORIZON_ORIGINAL_RULE"] = orig_sel
    fin["AMENDMENT_1"] = {"applied_before_validation": True, "reason": amend["reason"],
                           "original_selected_horizon": orig_sel, "amended_selected_horizon": amended_sel,
                           "amendment_hash": amend["amendment_hash"]}
    fin["REGISTRY_HASH_V1"] = reg1["registry_hash"]
    fin["REGISTRY_HASH"] = reg2["registry_hash"]
    fin["SCENARIO_DEFINITION_HASH"] = reg2["scenario_definition_hash"]
    json.dump(fin, open(os.path.join(ROOT, "reports", "V1_R8_TARGET_REDESIGN_FINAL.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    md = open(os.path.join(ROOT, "reports", "V1_R8_TARGET_REDESIGN_FINAL.md"), encoding="utf-8").read()
    md += f"""

---

## AMENDMENT 1（验证前修订，全程留痕）

**原规则缺陷**：只按 `stability_score` 取最大，而三个 horizon 的稳定性分**几乎并列**
（{json.dumps({h: ha[h]['stability_score'] for h in hs}, ensure_ascii=False)}，全距 {round(best_stab - min(ha[h]['stability_score'] for h in hs), 4)}），
于是选到了**信息量最低**的 H={orig_sel}（balanced_acc {(ha[str(orig_sel)]['information'] or {}).get('balanced_acc')}）。
预注册文本明确要求"比较**稳定性与信息量**"，故该规则未能实现其自身意图。

**修订规则**：稳定性分在最大值 {TOL} 邻域内视为并列 → 其间取 `information_score` 最大者。

**修订结果**：SELECTED_HORIZON = **{amended_sel}**（原 {orig_sel}）。
选择轨迹：{json.dumps({h: {"stab": ha[h]["stability_score"], "info": ha[h]["information_score"],
                            "ba": (ha[h]["information"] or {}).get("balanced_acc"), "stable": ha[h]["stable"]} for h in hs}, ensure_ascii=False)}

**合规声明**：R8-B **盲验证尚未开始**，未查看任何验证结果；原注册表 `v1_r8_target_registry.json` **原样保留**（哈希 {reg1['registry_hash'][:16]}），
修订另立 `v1_r8_target_registry_AMENDMENT_1.json` 与 `v1_r8_target_registry_v2.json`（哈希 {reg2['registry_hash'][:16]}）。
"""
    open(os.path.join(ROOT, "reports", "V1_R8_TARGET_REDESIGN_FINAL.md"), "w", encoding="utf-8", newline="\n").write(md)
    ledger_append([{"event": "amendment_1_applied", "amendment_hash": amend["amendment_hash"],
                     "original_horizon": orig_sel, "amended_horizon": amended_sel,
                     "registry_hash_v1": reg1["registry_hash"], "registry_hash_v2": reg2["registry_hash"],
                     "before_validation": True}])
    print("orig:", orig_sel, "-> amended:", amended_sel, "| tied:", tied)
    print("trace:", json.dumps(amend["selection_trace"], ensure_ascii=False))
    print("registry v1", reg1["registry_hash"][:16], "| v2", reg2["registry_hash"][:16], "| scen-def", reg2["scenario_definition_hash"][:16])


if __name__ == "__main__":
    main()
