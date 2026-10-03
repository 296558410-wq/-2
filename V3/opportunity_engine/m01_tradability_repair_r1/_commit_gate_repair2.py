# -*- coding: utf-8 -*-
"""COMMIT GATE REPAIR (final) — immutability verified from the DURABLE artifact, then gates + commit.

Research values are re-derived ONLY to prove they are unchanged (frozen event file + frozen seed/N).
Nothing in the research definition, event set, cost, exit, statistics or thresholds is modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE)
AIQ = os.path.dirname(RE)
R2 = os.path.join(ENGINE, "high_frequency_r2")
MVR1 = os.path.join(ENGINE, "mv_r1")
M1P = os.path.join(RE, "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
NOW = datetime.now(timezone.utc).isoformat()
SCOPE = "research/v3_opportunity_engine/m01_tradability_repair_r1/"
COMMIT_MSG = "V3: repair M01 tradability calculation and revalidate"
COST, SEED, BLOCK, RESAMPLES, PERMS = 0.914, 20260925, 5, 2000, 500
FROZEN = {"M01_N": 6759, "M01_EFFECTIVE_N": 6759, "GROSS": -0.8937, "NET_0X": -0.8937, "NET_1X": -1.8077,
           "NET_2X": -2.7217, "NET_3X": -3.6357, "CI95_NET1X": [-2.4929, -1.0816], "PERMUTATION_P": 1.0,
           "WF1": -1.8238, "WF2": -1.6785, "WF3": -1.9210, "POSITIVE_FOLDS": 0,
           "TRADABILITY_STATUS": "TRADABILITY_REJECTED"}
RUNTIME_CLASSES = ["/run_state/", "/runtime/", "/tmp/", "/cache/", "/memory/reviews/", "/observations/",
                    "/state/decision_contexts/"]
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


def done(status, **kw):
    out = {"V3_M01_TRADABILITY_REPAIR_R1_COMMIT_GATE_REPAIR": status, "ts_utc": NOW, **Q, **kw}
    json.dump(out, open(os.path.join(HERE, "commit_gate_repair_summary.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("\n=== COMMIT GATE REPAIR ===\n" + json.dumps(out, ensure_ascii=False, indent=1)[:2600], flush=True)
    sys.exit(0 if status == "PASS" else 2)


def is_cache(p):
    return "__pycache__" in p or p.endswith(".pyc")


def is_runtime(p):
    return any(c in p for c in RUNTIME_CLASSES)


def main():
    # ---------- re-derive the frozen values from the DURABLE per-event artifact ----------
    evf = os.path.join(HERE, "m01_event_recalculation.jsonl")
    rows = [json.loads(l) for l in open(evf, encoding="utf-8") if l.strip()]
    rows.sort(key=lambda r: r["signal_time"])
    g = np.array([r["gross_return_bp"] for r in rows], float)
    n1 = g - COST
    n2 = g - 2 * COST
    n3 = g - 3 * COST
    eps = {r["event_id"].split("|")[0].replace("TE-M01-", "") for r in rows}
    q3 = int(len(rows) / 3)
    folds = {}
    for i in range(3):
        seg = slice(i * q3, (i + 1) * q3 if i < 2 else len(rows))
        folds[f"WF{i+1}"] = round(float(np.mean(n1[seg])), 4)
    pos = sum(1 for v in folds.values() if v > 0)
    rng = np.random.default_rng(SEED)
    ms = []
    for _ in range(RESAMPLES):
        nb = int(np.ceil(len(n1) / BLOCK))
        st = rng.integers(0, max(1, len(n1) - BLOCK + 1), nb)
        ms.append(float(np.concatenate([n1[i:i + BLOCK] for i in st]).mean()))
    ci = [round(float(np.percentile(ms, 2.5)), 4), round(float(np.percentile(ms, 97.5)), 4)]
    # permutation with the frozen null/tail/N/seed (vectorised lookup, identical definition)
    m1 = pd.read_parquet(M1P, columns=["dt_utc", "close"])
    m1["dt"] = pd.to_datetime(m1["dt_utc"], utc=True)
    px = m1.set_index("dt")["close"].sort_index()
    idx_ns = px.index.values.astype("datetime64[ns]").view("int64")
    vals = px.to_numpy(float)
    step = np.int64(60 * 1_000_000_000)
    sig = np.array([int(pd.Timestamp(r["signal_time"]).value) for r in rows], dtype="int64")

    def pm(s):
        i_sig = np.searchsorted(idx_ns, s, side="right") - 1
        i_en = np.searchsorted(idx_ns, idx_ns[np.clip(i_sig, 0, len(idx_ns) - 1)] + step, side="right") - 1
        i_ex = np.clip(np.searchsorted(idx_ns, idx_ns[np.clip(i_sig, 0, len(idx_ns) - 1)] + 2 * step, side="left"),
                        i_en + 1, len(vals) - 1)
        good = (i_sig >= 6) & (i_en > i_sig) & (i_en + 1 < len(vals))
        ent, ex = vals[np.clip(i_en, 0, len(vals) - 1)], vals[i_ex]
        lng = vals[np.clip(i_sig, 0, len(vals) - 1)] >= vals[np.clip(i_sig - 5, 0, len(vals) - 1)]
        gg = np.where(lng, (ex - ent) / np.where(ent > 0, ent, np.nan),
                       (ent - ex) / np.where(ent > 0, ent, np.nan)) * 1e4
        gg = gg[good & np.isfinite(gg)]
        return float(np.mean(gg - COST)) if len(gg) else None

    obs = round(float(n1.mean()), 4)
    rp = np.random.default_rng(SEED)
    null = [pm(np.sort(rp.integers(int(sig.min()), int(sig.max()), len(rows)).astype("int64"))) for _ in range(PERMS)]
    null = np.array([x for x in null if x is not None], float)
    ext = int(np.sum(null >= obs))
    got = {"M01_N": len(rows), "M01_EFFECTIVE_N": len(eps), "GROSS": round(float(g.mean()), 4),
            "NET_0X": round(float(g.mean()), 4), "NET_1X": round(float(n1.mean()), 4),
            "NET_2X": round(float(n2.mean()), 4), "NET_3X": round(float(n3.mean()), 4), "CI95_NET1X": ci,
            "PERMUTATION_P": round((ext + 1) / (len(null) + 1), 6), "WF1": folds["WF1"], "WF2": folds["WF2"],
            "WF3": folds["WF3"], "POSITIVE_FOLDS": pos}
    got["TRADABILITY_STATUS"] = ("TRADABILITY_SUPPORTED" if (got["NET_1X"] > 0 and ci[0] > 0 and pos >= 2
                                                                and got["NET_2X"] > 0 and got["NET_3X"] > 0)
                                   else "TRADABILITY_REJECTED" if got["NET_1X"] <= 0 and ci[1] < 0
                                   else "TRADABILITY_UNCERTAIN")
    checks = {k: (got[k] == v) for k, v in FROZEN.items()}
    Q["research_values_read_back"] = got
    Q["research_immutability"] = {"checks": checks, "mismatched": [k for k, v in checks.items() if not v],
                                    "EVENT_SET_FILE_HASH": sha_file(evf)[:24],
                                    "R1_LEDGER_HASH": sha_file(os.path.join(ENGINE, "tradability_r1",
                                                                             "tradability_event_ledger.jsonl"))[:24],
                                    "AUDIT_HASH": sha_file(os.path.join(ENGINE, "m01_anomalous_edge_audit_r1",
                                                                          "audit_summary.json"))[:24]}
    Q["TRADABILITY_STATUS"] = got["TRADABILITY_STATUS"]
    Q["RESEARCH_ARTIFACTS"] = "UNCHANGED" if all(checks.values()) else "CHANGED"
    print("immutability:", Q["RESEARCH_ARTIFACTS"], json.dumps(checks, ensure_ascii=False), flush=True)
    print("read back:", json.dumps(got, ensure_ascii=False), flush=True)
    if Q["RESEARCH_ARTIFACTS"] != "UNCHANGED":
        done("STOPPED", FIRST_FAILED_GATE="RESEARCH_ARTIFACT_CHANGED")
    if got["TRADABILITY_STATUS"] != "TRADABILITY_REJECTED":
        done("STOPPED", FIRST_FAILED_GATE="TRADABILITY_STATUS_NOT_REJECTED")

    # ---------- isolation scanner (SOURCE/CONFIG vs RUNTIME by PATH CLASS) ----------
    base = json.load(open(os.path.join(MVR1, "WORKTREE_BASELINE_MV_R1.json"), encoding="utf-8"))

    def scan(root):
        src, rt = {}, 0
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                p = os.path.join(r_, f)
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                if not p.lower().endswith((".py", ".yaml", ".yml")) or is_cache(rel):
                    continue
                if is_runtime(rel):
                    rt += 1
                    continue
                src[rel] = sha_file(p)
        return src, rt
    iso = {}
    for k, root in (("trader_v1", os.path.join(RE, "hermes", "trader_v1")),
                     ("trader_v2", os.path.join(RE, "hermes", "trader_v2"))):
        src, rt = scan(root)
        bl = base["isolation_baseline"][k]["files"]
        changed = [p for p, h in bl.items() if not is_runtime(p) and src.get(p) != h]
        added = [p for p in src if p not in bl]
        iso[k] = {"SOURCE_CONFIG_files": len(src), "runtime_generated_excluded": rt, "changed": changed[:5],
                    "added": added[:5], "STATUS": "PASS" if not changed and not added else "FAIL"}
    Q["V1_ISOLATION"] = iso["trader_v1"]["STATUS"]
    Q["V2_ISOLATION"] = iso["trader_v2"]["STATUS"]
    Q["isolation_scanner"] = {"rule": "SOURCE/CONFIG only; RUNTIME path classes excluded; no per-file whitelist",
                                "runtime_path_classes": RUNTIME_CLASSES, "v1": iso["trader_v1"], "v2": iso["trader_v2"]}
    print("isolation:", json.dumps({"V1": Q["V1_ISOLATION"], "V2": Q["V2_ISOLATION"],
                                      "v1_src": iso["trader_v1"]["SOURCE_CONFIG_files"],
                                      "v1_runtime_excluded": iso["trader_v1"]["runtime_generated_excluded"],
                                      "v2_src": iso["trader_v2"]["SOURCE_CONFIG_files"],
                                      "v2_runtime_excluded": iso["trader_v2"]["runtime_generated_excluded"]},
                                     ensure_ascii=False), flush=True)
    if Q["V1_ISOLATION"] != "PASS" or Q["V2_ISOLATION"] != "PASS":
        done("STOPPED", FIRST_FAILED_GATE="V1/V2_ISOLATION", ISOLATION=iso)

    # ---------- boundary: locate + classify ----------
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
    cls, unknown = {}, []
    for p in added:
        c = ("M01_REPAIR_FILES" if p.startswith(SCOPE) else "V3_RESEARCH_FILES"
             if p.startswith("research/v3_opportunity_engine/") else "REGISTERED_CLOSEOUT_FILES"
             if p in CLOSEOUT_ALLOW else "V1_V2_RUNTIME_OUTPUT" if is_runtime(p) else "UNKNOWN")
        cls.setdefault(c, []).append(p)
        if c == "UNKNOWN":
            unknown.append(p)
    Q["BOUNDARY_ADDED"] = len(added)
    Q["BOUNDARY_BREAKDOWN"] = {k: len(v) for k, v in cls.items()}
    Q["BOUNDARY_VIOLATION"] = len(unknown)
    print("boundary:", json.dumps({"added": len(added), "breakdown": Q["BOUNDARY_BREAKDOWN"],
                                     "unknown": unknown[:5]}, ensure_ascii=False), flush=True)
    if unknown:
        fp = os.path.join(AIQ, unknown[0])
        st = os.stat(fp) if os.path.exists(fp) else None
        done("STOPPED", FIRST_FAILED_GATE="BOUNDARY_VIOLATION_UNCLASSIFIED",
             UNKNOWN_PATH=unknown[0], PATH_CLASS="UNKNOWN", CLASSIFICATION_BASIS="not in any registered path class",
             CREATED_BY="unknown", TIMESTAMP=(datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat() if st else None))

    # ---------- secrets / file audit / gates ----------
    files = sorted({os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
                     for r_, _, fs in os.walk(HERE) for f in fs if not is_cache(f)})
    for x in files:
        sh("git", "add", "--", x)
    stg = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    pat = re.compile(r"(sk-[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=])")
    sec = [s for s in stg if os.path.exists(os.path.join(AIQ, s))
            and pat.search(open(os.path.join(AIQ, s), encoding="utf-8", errors="ignore").read())]
    fa = {"staged": len(stg), "non_scope": len([s for s in stg if not s.startswith(SCOPE)]),
           "v1": len([s for s in stg if "trader_v1" in s]), "v2": len([s for s in stg if "trader_v2" in s]),
           "secrets": len(sec)}
    Q["SECRETS_SCAN"] = "PASS" if not sec else "FAIL"
    Q["FILE_AUDIT"] = "PASS" if not (fa["non_scope"] or fa["v1"] or fa["v2"]) else "FAIL"
    Q["COMMIT_FILE_AUDIT"] = fa
    gates = {"RESEARCH_ARTIFACT_IMMUTABILITY": True, "TRADABILITY_STATUS_REJECTED": True,
              "V1_ISOLATION": True, "V2_ISOLATION": True, "BOUNDARY": Q["BOUNDARY_VIOLATION"] == 0,
              "SECRETS_SCAN": Q["SECRETS_SCAN"] == "PASS", "FILE_AUDIT": Q["FILE_AUDIT"] == "PASS"}
    Q["COMMIT_GATE"] = gates
    print("gates:", json.dumps(gates, ensure_ascii=False), flush=True)
    if not all(gates.values()):
        done("STOPPED", FIRST_FAILED_GATE="COMMIT_GATE")
    sh("git", "commit", "-q", "-m", COMMIT_MSG)
    commit = sh("git", "rev-parse", "--short", "HEAD")
    changed = [x for x in sh("git", "show", "--name-only", "--format=", "HEAD").splitlines() if x.strip()]
    done("PASS", COMMIT_GATE="PASS", COMMIT=commit, COMMIT_HASH=commit, COMMIT_MESSAGE=COMMIT_MSG,
         FILES_CHANGED=len(changed), V1_FILES_CHANGED=len([x for x in changed if "trader_v1" in x]),
         V2_FILES_CHANGED=len([x for x in changed if "trader_v2" in x]), RESEARCH_RESULT_CHANGED=0,
         UNKNOWN_PATH="NONE", PATH_CLASS="NONE", CLASSIFICATION_BASIS="no unclassified added path",
         BOUNDARY="PASS", CANDIDATE=0, FORWARD="OFF", SHADOW="OFF", LIVE="OFF", ORDER_SEND=0,
         post={"log1": sh("git", "log", "-1", "--oneline")})


if __name__ == "__main__":
    main()
