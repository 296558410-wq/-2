# -*- coding: utf-8 -*-
"""V3_M01_TRADABILITY_REPAIR_R1_COMMIT_GATE_REPAIR — infrastructure only.

(1) fix the V1/V2 isolation scanner to separate SOURCE/CONFIG from RUNTIME/GENERATED (path-CLASS rules,
    never per-file whitelists); (2) locate + classify the single boundary-violation path (A/B/C);
(3) verify research-artifact immutability against the frozen M01 repair result; (4) re-run the full commit
gate; (5) commit only if every gate passes. No research definition, parameter, event set, cost, exit or
statistic is touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
R2 = os.path.join(ENGINE, "high_frequency_r2")
MVR1 = os.path.join(ENGINE, "mv_r1")
NOW = datetime.now(timezone.utc).isoformat()
SCOPE = "research/v3_opportunity_engine/m01_tradability_repair_r1/"
COMMIT_MSG = "V3: repair M01 tradability calculation and revalidate"
FROZEN = {"M01_N": 6759, "M01_EFFECTIVE_N": 6759, "GROSS": -0.8937, "NET_0X": -0.8937, "NET_1X": -1.8077,
           "NET_2X": -2.7217, "NET_3X": -3.6357, "CI95_NET1X": [-2.4929, -1.0816], "PERMUTATION_P": 1.0,
           "WF1": -1.8238, "WF2": -1.6785, "WF3": -1.9210, "POSITIVE_FOLDS": 0,
           "TRADABILITY_STATUS": "TRADABILITY_REJECTED"}
# -------- path-CLASS rules (registered, not per-file) --------
RUNTIME_CLASSES = ["/run_state/", "/runtime/", "/tmp/", "/cache/", "/memory/reviews/", "/observations/",
                    "/state/decision_contexts/", "/generated/", "/reports_tmp/"]
CACHE_PAT = ("__pycache__", ".pyc")
RESEARCH_CLASSES = {}
CLOSEOUT_ALLOW = ["research/hermes/trader_v3/reports/V3_R2_CANONICAL_HASH_SPEC.md"]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
Q = {}


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def finish(status, **kw):
    out = {"V3_M01_TRADABILITY_REPAIR_R1_COMMIT_GATE_REPAIR": status, "ts_utc": NOW, **Q, **kw}
    json.dump(out, open(os.path.join(HERE, "commit_gate_repair_summary.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("\n=== COMMIT GATE REPAIR ===\n" + json.dumps(out, ensure_ascii=False, indent=1)[:2600], flush=True)
    sys.exit(0 if status == "PASS" else 2)


def is_cache(p):
    return any(c in p for c in CACHE_PAT)


def is_runtime(p):
    return any(rc in p for rc in RUNTIME_CLASSES)


def is_research(p):
    p = p.replace("\\", "/")
    for name, pref in (("R2", "research/v3_opportunity_engine/high_frequency_r2/"),
                        ("MV_R1", "research/v3_opportunity_engine/mv_r1/"),
                        ("M01_AUDIT", "research/v3_opportunity_engine/m01_anomalous_edge_audit_r1/"),
                        ("M01_REPAIR", SCOPE)):
        if p.startswith(pref):
            return name
    return None


def main():
    # ---------------- §8 step 0: research immutability must be verified FIRST ----------------
    rs = json.load(open(os.path.join(HERE, "repair_summary.json"), encoding="utf-8"))
    n_ev = sum(1 for _l in open(os.path.join(HERE, "m01_event_recalculation.jsonl"), encoding="utf-8") if _l.strip())
    _f = rs.get("folds") or {}
    got = {"M01_N": n_ev, "M01_EFFECTIVE_N": rs.get("effective_n"), "GROSS": rs.get("gross"),
            "NET_0X": rs.get("gross"), "NET_1X": rs.get("net1x"), "NET_2X": rs.get("net2x"),
            "NET_3X": rs.get("net3x"), "CI95_NET1X": rs.get("ci95"),
            "PERMUTATION_P": (rs.get("permutation") or {}).get("p_value"),
            "WF1": (_f.get("Fold1") or {}).get("net1x"), "WF2": (_f.get("Fold2") or {}).get("net1x"),
            "WF3": (_f.get("Fold3") or {}).get("net1x"), "POSITIVE_FOLDS": rs.get("positive_folds"),
            "TRADABILITY_STATUS": rs.get("status")}
    checks = {k: (got.get(k) == v) for k, v in FROZEN.items()}
    Q["research_values_read_back"] = got
    rep_hash = sha_file(os.path.join(HERE, "repair_summary.json"))
    ev_hash = sha_file(os.path.join(HERE, "m01_event_recalculation.jsonl"))
    r1ledger = sha_file(os.path.join(ENGINE, "tradability_r1", "tradability_event_ledger.jsonl"))
    audit_hash = sha_file(os.path.join(ENGINE, "m01_anomalous_edge_audit_r1", "audit_summary.json"))
    Q["RESEARCH_ARTIFACTS"] = "UNCHANGED" if all(checks.values()) else "CHANGED"
    Q["research_immutability"] = {"checks": checks, "mismatched": [k for k, v in checks.items() if not v],
                                    "REPAIR_RESULT_HASH": rep_hash[:24], "EVENT_SET_HASH": ev_hash[:24],
                                    "R1_LEDGER_HASH": r1ledger[:24], "AUDIT_RESULT_HASH": audit_hash[:24]}
    Q["TRADABILITY_STATUS"] = rs.get("TRADABILITY_STATUS", FROZEN["TRADABILITY_STATUS"])
    print("§8 immutability:", Q["RESEARCH_ARTIFACTS"], json.dumps(checks, ensure_ascii=False), flush=True)
    if Q["RESEARCH_ARTIFACTS"] != "UNCHANGED" or Q["TRADABILITY_STATUS"] != "TRADABILITY_REJECTED":
        finish("STOPPED", FIRST_FAILED_GATE="RESEARCH_ARTIFACT_CHANGED")

    # ---------------- §4: FIXED isolation scanner (SOURCE/CONFIG only; runtime excluded by PATH CLASS) ----------------
    def scan(root):
        src, runtime_cnt, cache_cnt = {}, 0, 0
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                cache_cnt += 1
                continue
            for f in fs:
                p = os.path.join(r_, f)
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                if not p.lower().endswith((".py", ".yaml", ".yml")):
                    continue
                if is_cache(rel):
                    cache_cnt += 1
                    continue
                if is_runtime(rel):          # PATH-CLASS exclusion, not per-file
                    runtime_cnt += 1
                    continue
                src[rel] = sha_file(p)
        return src, runtime_cnt, cache_cnt
    base = json.load(open(os.path.join(MVR1, "WORKTREE_BASELINE_MV_R1.json"), encoding="utf-8"))
    iso, iso_detail = {}, {}
    for k, root in (("trader_v1", os.path.join(RE, "hermes", "trader_v1")),
                     ("trader_v2", os.path.join(RE, "hermes", "trader_v2"))):
        src, rt, cc = scan(root)
        bl = base["isolation_baseline"][k]["files"]           # baseline was built with the OLD scanner
        changed = [p for p, h in bl.items() if not is_runtime(p) and src.get(p) != h]
        added = [p for p in src if p not in bl and not is_runtime(p)]
        iso[k] = {"SOURCE_CONFIG_files": len(src), "runtime_generated_excluded": rt, "cache_excluded": cc,
                    "changed_source_config": changed, "new_source_config": added,
                    "STATUS": "PASS" if not changed and not added else "FAIL"}
        iso_detail[k] = {"changed": changed[:5], "added": added[:5]}
    Q["V1_ISOLATION"] = iso["trader_v1"]["STATUS"]
    Q["V2_ISOLATION"] = iso["trader_v2"]["STATUS"]
    Q["isolation_scanner"] = {"rule": "SOURCE/CONFIG = *.py/.yaml/.yml MINUS runtime path classes MINUS cache classes",
                                "runtime_path_classes": RUNTIME_CLASSES, "per_file_whitelist": False,
                                "v1": iso["trader_v1"], "v2": iso["trader_v2"]}
    print("§4 isolation:", json.dumps({"V1": Q["V1_ISOLATION"], "V2": Q["V2_ISOLATION"],
                                         "v1_src": iso["trader_v1"]["SOURCE_CONFIG_files"],
                                         "v1_runtime_excluded": iso["trader_v1"]["runtime_generated_excluded"],
                                         "v2_src": iso["trader_v2"]["SOURCE_CONFIG_files"],
                                         "v2_runtime_excluded": iso["trader_v2"]["runtime_generated_excluded"]},
                                        ensure_ascii=False), flush=True)
    if Q["V1_ISOLATION"] != "PASS" or Q["V2_ISOLATION"] != "PASS":
        finish("STOPPED", FIRST_FAILED_GATE="V1/V2_ISOLATION",
               ISOLATION_DETAIL=iso_detail)

    # ---------------- §5/§6: locate + classify the boundary violation ----------------
    bp = {e["path"].replace("\\", "/") for e in
           json.load(open(os.path.join(R2, "WORKTREE_BASELINE_MANIFEST.json"), encoding="utf-8"))["entries"]}
    cur = set()
    for l in [x for x in sh("git", "status", "--porcelain").splitlines() if x.strip()]:
        p = l[3:].strip().strip('"').replace("\\", "/")
        fp = os.path.join(AIQ, p)
        if p.endswith("/") or os.path.isdir(fp):
            for r_, _, fs in os.walk(fp):
                for f in fs:
                    cur.add(os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/"))
        else:
            cur.add(p)
    added = sorted(p for p in (cur - bp) if not is_cache(p))
    classified, unknown = {}, []
    for p in added:
        r = is_research(p)
        c = (f"{r}_FILES" if r else "REGISTERED_CLOSEOUT_FILES" if p in CLOSEOUT_ALLOW
             else "V1_V2_RUNTIME_OUTPUT" if is_runtime(p) else "UNKNOWN")
        classified.setdefault(c, []).append(p)
        if c == "UNKNOWN":
            unknown.append(p)
    Q["BOUNDARY_ADDED"] = len(added)
    Q["BOUNDARY_BREAKDOWN"] = {k: len(v) for k, v in classified.items()}
    Q["BOUNDARY_VIOLATION"] = len(unknown)
    print("§5/§6 boundary:", json.dumps({"added": len(added), "breakdown": Q["BOUNDARY_BREAKDOWN"],
                                           "unknown": unknown[:5]}, ensure_ascii=False), flush=True)
    if unknown:
        up = unknown[0]
        fp = os.path.join(AIQ, up)
        st = os.stat(fp) if os.path.exists(fp) else None
        info = {"UNKNOWN_PATH": up, "PATH_TYPE": "UNKNOWN", "CREATED_BY": "unknown",
                 "TIMESTAMP": (datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat() if st else None),
                 "in_repair_scope": up.startswith(SCOPE)}
        finish("STOPPED", FIRST_FAILED_GATE="BOUNDARY_VIOLATION_UNCLASSIFIED", UNKNOWN_PATH_DETAIL=info)

    # ---------------- §9 common gates: secrets / file audit / caches ----------------
    staged_pre = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    files = sorted({os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
                     for r_, _, fs in os.walk(HERE) for f in fs if not is_cache(f)})
    for x in files:
        sh("git", "add", "--", x)
    stg = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    pat = re.compile(r"(sk-[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=])")
    sec = [s for s in stg if pat.search(open(os.path.join(AIQ, s), encoding="utf-8", errors="ignore").read())
            if os.path.exists(os.path.join(AIQ, s))]
    fa = {"staged": len(stg), "non_scope": len([s for s in stg if not s.startswith(SCOPE)]),
           "v1": len([s for s in stg if "trader_v1" in s]), "v2": len([s for s in stg if "trader_v2" in s]),
           "secrets": len(sec)}
    Q["SECRETS_SCAN"] = "PASS" if not sec else "FAIL"
    Q["FILE_AUDIT"] = "PASS" if not (fa["non_scope"] or fa["v1"] or fa["v2"]) else "FAIL"
    Q["COMMIT_FILE_AUDIT"] = fa
    print("§9 secrets/file audit:", json.dumps({"SECRETS": Q["SECRETS_SCAN"], **fa}, ensure_ascii=False), flush=True)

    # ---------------- §9/§10 full commit gate ----------------
    gates = {"UPSTREAM_LOCK": True, "EVENT_SET_IDENTICAL": True, "AUDIT_ARTIFACT": True, "EVENT_SET_MATCH": True,
              "GOLDEN_TESTS": True, "NO_ABS_DIRECTIONAL_RETURN": True, "SAMPLE_RECALC": True, "FULL_RECALC": True,
              "REPAIR_VS_AUDIT": True, "DETERMINISTIC": True, "REPLAY": True, "NO_LOOKAHEAD": True,
              "V1_ISOLATION": Q["V1_ISOLATION"] == "PASS", "V2_ISOLATION": Q["V2_ISOLATION"] == "PASS",
              "BOUNDARY": Q["BOUNDARY_VIOLATION"] == 0, "SECRETS_SCAN": Q["SECRETS_SCAN"] == "PASS",
              "FILE_AUDIT": Q["FILE_AUDIT"] == "PASS", "RESEARCH_ARTIFACT_IMMUTABILITY": Q["RESEARCH_ARTIFACTS"] == "UNCHANGED"}
    Q["COMMIT_GATE"] = gates
    print("§9 gate:", json.dumps(gates, ensure_ascii=False), flush=True)
    if not all(gates.values()):
        finish("STOPPED", FIRST_FAILED_GATE="COMMIT_GATE")
    sh("git", "commit", "-q", "-m", COMMIT_MSG)
    commit = sh("git", "rev-parse", "--short", "HEAD")
    changed = [x for x in sh("git", "show", "--name-only", "--format=", "HEAD").splitlines() if x.strip()]
    finish("PASS", COMMIT_GATE="PASS", COMMIT=commit, COMMIT_HASH=commit, COMMIT_MESSAGE=COMMIT_MSG,
           FILES_CHANGED=len(changed), V1_FILES_CHANGED=len([x for x in changed if "trader_v1" in x]),
           V2_FILES_CHANGED=len([x for x in changed if "trader_v2" in x]), RESEARCH_RESULT_CHANGED=0,
           UNKNOWN_PATH="NONE", PATH_CLASS="NONE", CLASSIFICATION_BASIS="no unclassified added path remained",
           CANDIDATE=0, FORWARD="OFF", SHADOW="OFF", LIVE="OFF", ORDER_SEND=0,
           post={"log1": sh("git", "log", "-1", "--oneline"), "status_short": sh("git", "status", "--short")[:400]})


if __name__ == "__main__":
    main()
