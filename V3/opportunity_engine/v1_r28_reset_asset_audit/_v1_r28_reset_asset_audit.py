# -*- coding: utf-8 -*-
"""R28 - read-only audit: external snapshots of the truncated old ledger, old statistics, and PnL boundaries.
No writes to V1/V2/V3 or their runtime. Writes ONLY under
research/v3_opportunity_engine/v1_r28_reset_asset_audit/ (UTF-8, ASCII hyphens only)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
RUN = os.path.join(V1, "run_state")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
V2 = os.path.join(RE, "hermes", "trader_v2")
R2 = os.path.join(ENGINE_DIR, "high_frequency_r2")
M01R = os.path.join(ENGINE_DIR, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE_DIR, "tradability_r1")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
C = "43f9b2f8e221"
P = "ebce041797ec"
RUNID = "V1_RUN_20260924_RESET_01"
P_LEDGER = "research/hermes/trader_v1/run_state/plan_ledger.jsonl"
P_STATS = "research/hermes/trader_v1/run_state/statistics.json"
P_META = "research/hermes/trader_v1/run_state/RUN_META.json"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
SKIP_DIRS = (".git", "node_modules", "__pycache__", "mt5_instances", ".venv", "site-packages", "media",
              "dist", ".mypy_cache", ".pytest_cache")
TEXT_EXT = (".jsonl", ".json", ".md", ".txt", ".log", ".yaml", ".yml")
ARCH_EXT = (".zip", ".gz", ".tar", ".7z", ".bak", ".orig")
PNL_TOKENS = ["-21.97", "2364265913", "2377465821", "4299.03", "2377449557"]
COUNTER_MODEL = {}

R = {}


def sh(a, t=240):
    try:
        p = subprocess.run(a, cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def canon_line(s):
    try:
        return json.dumps(json.loads(s), sort_keys=True, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return None


def main():
    os.makedirs(HERE, exist_ok=True)
    R["task_status"] = "RUNNING"
    R["audit_now_utc"] = datetime.now(timezone.utc).isoformat()
    R["reset_commit"] = C
    R["parent_commit"] = P

    # ---------- freeze ----------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    R["automation_enabled"] = auto.get("enabled", "UNKNOWN")
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], t=90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["v1_engine_process"] = "NOT_RUNNING" if not v1p else "RUNNING"
    R["hash_before"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    ok = (str(R["automation_enabled"]).lower() == "false" and R["v1_engine_process"] == "NOT_RUNNING"
           and R["hash_before"]["ENGINE"] == BASE and R["hash_before"]["LEDGER"] == LEDGER_EXPECT
           and R["hash_before"]["STATISTICS"] == STATS_EXPECT and R["hash_before"]["RUN_META"] == META_EXPECT)
    print("freeze ok =", ok, flush=True)
    if not ok:
        R["r28_gate"] = "FAIL"
        R["stop_reason"] = "FREEZE_FAILED"
        return finish()

    # ---------- parent versions from git ----------
    par_ledger = sh(["git", "show", P + ":" + P_LEDGER], t=240)
    par_stats = sh(["git", "show", P + ":" + P_STATS], t=240)
    cur_ledger = sh(["git", "show", C + ":" + P_LEDGER], t=240)
    cur_stats = sh(["git", "show", C + ":" + P_STATS], t=240)
    pl_lines = [x for x in par_ledger.splitlines() if x.strip()]
    cl_lines = [x for x in cur_ledger.splitlines() if x.strip()]
    R["old_ledger_records_total"] = len(pl_lines)
    R["parent_ledger_file_sha256"] = hashlib.sha256(par_ledger.encode("utf-8")).hexdigest()
    R["commit_ledger_file_sha256"] = hashlib.sha256(cur_ledger.encode("utf-8")).hexdigest()
    R["parent_statistics_file_sha256"] = hashlib.sha256(par_stats.encode("utf-8")).hexdigest()
    par_records = {}
    for i, ln in enumerate(pl_lines):
        c = canon_line(ln)
        if c:
            par_records[hashlib.sha256(c.encode("utf-8")).hexdigest()] = i + 1
    R["parent_record_hashes"] = len(par_records)
    print("anchor:", "parent_lines=", len(pl_lines), "parent_records=", len(par_records), flush=True)

    # ---------- walk worktree for snapshots ----------
    found_records = {}          # rec_hash -> list of {file,line}
    candidates_ledger = []      # files that look like ledger snapshots
    candidates_stats = []       # files that look like statistics snapshots
    pnl_hits = []
    keyword_files = []
    arch_files = []
    scanned = 0
    for root in (RE, AIQ):
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            rl = r_.replace("\\", "/").lower()
            if any(s in rl for s in SKIP_DIRS):
                continue
            if "v3_opportunity_engine/v1_r28" in rl:
                continue
            ds[:] = [d for d in ds if d not in SKIP_DIRS]
            for f in fs:
                ext = os.path.splitext(f)[1].lower()
                p = os.path.join(r_, f)
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                if ext in ARCH_EXT:
                    arch_files.append({"path": rel, "ext": ext, "size": os.path.getsize(p) if os.path.exists(p) else None})
                    continue
                if ext not in TEXT_EXT:
                    continue
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if sz > 5_000_000:
                    continue
                scanned += 1
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                low = f.lower()
                # ledger snapshot candidates
                if "plan_ledger" in low or "ledger" in low:
                    ls = [x for x in txt.splitlines() if x.strip()]
                    hit = 0
                    for ln in ls:
                        c = canon_line(ln)
                        if c:
                            h = hashlib.sha256(c.encode("utf-8")).hexdigest()
                            if h in par_records:
                                hit += 1
                                found_records.setdefault(h, []).append({"file": rel, "line": len(found_records.get(h, [])) + 1})
                    if ls:
                        candidates_ledger.append({"path": rel, "size": sz, "lines": len(ls), "matched_records": hit,
                                                    "sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest(),
                                                    "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat()})
                # statistics snapshot candidates
                if re.search(r"(?i)(statistics|stats|run_meta)", low):
                    h2 = hashlib.sha256(txt.encode("utf-8")).hexdigest()
                    candidates_stats.append({"path": rel, "size": sz, "sha256": h2,
                                               "matches_parent_statistics": h2 == R["parent_statistics_file_sha256"],
                                               "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat()})
                # keyword files
                for kw in ("V1_RUN_20260924_RESET_01", "43f9b2f", "ebce041797ec", "v1_pre_reset"):
                    if kw in txt:
                        keyword_files.append({"path": rel, "keyword": kw})
                        break
                # pnl tokens
                for tok in PNL_TOKENS:
                    if tok in txt:
                        bound = ("EXPLICIT" if re.search(r"(V1_RUN_20260924_RESET_01|run_id|plan_id|TP-20260925T140419|POS-20260925T140419)", txt) else "IMPLICIT_ONLY")
                        pnl_hits.append({"path": rel, "token": tok, "binding": bound})
                        break
                if scanned > 9000:
                    break
            if scanned > 9000:
                break
        if scanned > 9000:
            break
    R["scanned_text_files"] = scanned
    R["old_ledger_records_found"] = len(found_records)
    R["old_ledger_records_missing"] = R["old_ledger_records_total"] - len(found_records)
    best = max(candidates_ledger, key=lambda x: x["matched_records"], default=None)
    if best and best["matched_records"] == R["old_ledger_records_total"] and best["lines"] >= R["old_ledger_records_total"]:
        R["old_ledger_snapshot"] = "PROVEN"
    elif best and best["matched_records"] > 0:
        R["old_ledger_snapshot"] = "PARTIAL"
    else:
        R["old_ledger_snapshot"] = "NOT_FOUND"
    R["old_ledger_snapshot_candidates"] = sorted(candidates_ledger, key=lambda x: -x["matched_records"])[:10]
    R["old_ledger_snapshot_detail"] = {"best_candidate": best, "found_record_files": len({v[0] for lst in found_records.values() for v in lst})}
    R["old_ledger_records_found_detail_sample"] = [{"record_hash": k[:16], "occurrences": len(v), "files": [x["file"] for x in v][:3]}
                                                     for k, v in list(found_records.items())[:10]]
    print("ledger snapshots:", R["old_ledger_snapshot"], "found_records=", len(found_records), "/", len(par_records),
          "cands=", len(candidates_ledger), flush=True)

    # ---------- statistics snapshot verdict ----------
    exact_stats = [c for c in candidates_stats if c["matches_parent_statistics"]]
    R["old_statistics_snapshot_candidates"] = sorted(candidates_stats, key=lambda x: (not x["matches_parent_statistics"], x["size"]))[:10]
    if exact_stats:
        R["old_statistics_snapshot"] = "PROVEN"
    elif any(c["path"].endswith("statistics.json") for c in candidates_stats):
        R["old_statistics_snapshot"] = "PARTIAL"
    else:
        R["old_statistics_snapshot"] = "NOT_FOUND"
    R["exact_parent_statistics_matches"] = [c["path"] for c in exact_stats]
    print("statistics snapshot:", R["old_statistics_snapshot"], "exact_matches=", len(exact_stats),
          "cands=", len(candidates_stats), flush=True)

    # ---------- PnL binding ----------
    explicit = [h for h in pnl_hits if h["binding"] == "EXPLICIT"]
    R["pnl_token_hits"] = pnl_hits[:20]
    R["pnl_explicit_binding_files"] = sorted({h["path"] for h in explicit})[:10]
    R["old_pnl_isolation"] = ("PROVEN" if explicit else "NOT_PROVEN")
    R["old_pnl_note"] = "field/token presence alone does not prove an accounting boundary"
    print("pnl:", R["old_pnl_isolation"], "hits=", len(pnl_hits), "explicit=", len(explicit), flush=True)

    # ---------- new-run boundaries ----------
    meta = {}
    stats = {}
    try:
        meta = json.loads(open(META, encoding="utf-8", errors="ignore").read())
    except Exception:  # noqa: BLE001
        meta = {}
    try:
        stats = json.loads(open(STATS, encoding="utf-8", errors="ignore").read())
    except Exception:  # noqa: BLE001
        stats = {}
    def has(o, *keys):
        return any(k in o for k in keys) if isinstance(o, dict) else False
    counter_fields = has(meta, "opening_counters", "starting_counters", "counters") or has(stats, "counters")
    pnl_fields = has(meta, "realized_pnl", "opening_pnl") or has(stats, "realized_pnl")
    bal_fields = has(meta, "opening_balance", "opening_equity", "starting_equity") or has(stats, "opening_balance", "opening_equity")
    R["new_run_state_fields"] = {"RUN_META_keys": sorted(meta.keys()) if isinstance(meta, dict) else "N/A",
                                   "STATISTICS_keys": sorted(stats.keys()) if isinstance(stats, dict) else "N/A",
                                   "counter_fields_present": counter_fields, "pnl_fields_present": pnl_fields,
                                   "balance_fields_present": bal_fields}
    R["new_run_counter_boundary"] = "PARTIAL" if counter_fields else "NOT_PROVEN"
    R["new_run_pnl_boundary"] = "PARTIAL" if pnl_fields else "NOT_PROVEN"
    R["new_run_balance_boundary"] = "PARTIAL" if bal_fields else "NOT_PROVEN"
    print("new-run boundaries:", R["new_run_counter_boundary"], R["new_run_pnl_boundary"], R["new_run_balance_boundary"],
          flush=True)

    # ---------- boundaries ----------
    R["ledger_boundary"] = ("PROVEN" if R["old_ledger_snapshot"] == "PROVEN" else
                              ("PARTIAL" if R["old_ledger_snapshot"] == "PARTIAL" else "NOT_PROVEN"))
    R["statistics_boundary"] = ("PROVEN" if R["old_statistics_snapshot"] == "PROVEN" else
                                  ("PARTIAL" if R["old_statistics_snapshot"] == "PARTIAL" else "NOT_PROVEN"))
    R["pnl_boundary"] = R["old_pnl_isolation"]
    six = [R["old_ledger_snapshot"] == "PROVEN", R["old_statistics_snapshot"] == "PROVEN",
            R["old_pnl_isolation"] == "PROVEN", R["new_run_counter_boundary"] == "PROVEN",
            R["new_run_pnl_boundary"] == "PROVEN", R["new_run_balance_boundary"] == "PROVEN"]
    R["run_accounting_boundary"] = "PROVEN" if all(six) else "NOT_PROVEN"
    R["six_requirements"] = {"OLD_LEDGER_SNAPSHOT": R["old_ledger_snapshot"],
                               "OLD_STATISTICS_SNAPSHOT": R["old_statistics_snapshot"],
                               "OLD_PNL_ISOLATION": R["old_pnl_isolation"],
                               "NEW_RUN_COUNTER_BOUNDARY": R["new_run_counter_boundary"],
                               "NEW_RUN_PNL_BOUNDARY": R["new_run_pnl_boundary"],
                               "NEW_RUN_BALANCE_BOUNDARY": R["new_run_balance_boundary"]}

    # ---------- actor / archive separation ----------
    R["execution_actor"] = "UNKNOWN"
    R["archive_classification"] = {"GIT_HISTORY": "43f9b2f has 0 files under archive/ (R26); parent also 0",
                                     "WORKTREE_ARCHIVE": "archive/v1_pre_reset_20260923_233741 exists in the worktree",
                                     "EXTERNAL_SNAPSHOT": ("FOUND" if (R["old_ledger_snapshot"] != "NOT_FOUND"
                                                                          or R["old_statistics_snapshot"] != "NOT_FOUND") else "NOT_FOUND"),
                                     "UNKNOWN": "actor/origin of the archive remains unknown"}
    R["keyword_files"] = keyword_files[:20]
    R["archives_seen"] = arch_files[:10]

    # ---------- timeline ----------
    R["timeline"] = {"T1_git_parent": sh(["git", "show", "-s", "--format=%cI", P], t=60) + " [source=git metadata]",
                       "T2_git_commit": sh(["git", "show", "-s", "--format=%cI", C], t=60) + " [source=git metadata]",
                       "T3_run_meta_start_time_utc": str(meta.get("start_time_utc", "ABSENT")) + " [source=JSON field]",
                       "T4_archive_timestamp": "2026-09-23T23:37:41 (from directory name) [source=filesystem name]",
                       "T5_current_state": "V1 stopped; automation disabled [source=R28 freeze]"}

    # ---------- Q1-Q8 ----------
    R["Q1_old_ledger_external_copy"] = ("YES" if R["old_ledger_snapshot"] == "PROVEN" else
                                          ("PARTIAL" if R["old_ledger_snapshot"] == "PARTIAL" else "NO"))
    R["Q2_old_statistics_snapshot"] = ("YES" if R["old_statistics_snapshot"] == "PROVEN" else
                                         ("PARTIAL" if R["old_statistics_snapshot"] == "PARTIAL" else "NO"))
    R["Q3_old_pnl_run_binding"] = ("PROVEN" if R["old_pnl_isolation"] == "PROVEN" else "NOT_PROVEN")
    R["Q4_new_run_opening_boundary"] = ("PROVEN" if all([R["new_run_counter_boundary"] == "PROVEN",
                                                            R["new_run_pnl_boundary"] == "PROVEN",
                                                            R["new_run_balance_boundary"] == "PROVEN"]) else
                                          ("PARTIAL" if any([R["new_run_counter_boundary"] != "NOT_PROVEN",
                                                              R["new_run_pnl_boundary"] != "NOT_PROVEN",
                                                              R["new_run_balance_boundary"] != "NOT_PROVEN"]) else "NOT_PROVEN"))
    R["Q5_new_run_may_inherit_counters"] = "UNKNOWN"
    R["Q6_new_run_may_inherit_pnl"] = "UNKNOWN"
    R["Q7_old_ledger_recoverable"] = ("YES" if R["old_ledger_snapshot"] == "PROVEN" else
                                        ("PARTIAL" if R["old_ledger_snapshot"] == "PARTIAL" else "NO"))
    R["Q8_safe_to_reset"] = "NO"

    # ---------- gate ----------
    R["r28_gate"] = "PASS" if R["run_accounting_boundary"] == "PROVEN" else "FAIL"
    for k in ("reset", "new_run", "v1_start", "automation_enable", "mt5_access", "order_send", "position_close",
                "position_modify", "order_cancel", "ledger_write", "state_write", "source_write", "config_write"):
        R[k] = 0
    R["git_commit"] = "NONE"
    R["task_status"] = "V1_R28_RESET_ASSET_AUDIT_COMPLETE"
    return finish()


def finish():
    R.setdefault("task_status", "V1_R28_RESET_ASSET_AUDIT_COMPLETE")
    R["hash_after"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    R["hash_before_after_match"] = "YES" if R.get("hash_before") == R.get("hash_after") else "NO"
    R["engine_hash_stable"] = "YES" if R["hash_before_after_match"] == "YES" else "NO"
    R["ledger_hash_stable"] = R["engine_hash_stable"]
    R["statistics_hash_stable"] = R["engine_hash_stable"]
    R["run_meta_hash_stable"] = R["engine_hash_stable"]
    R["v1_isolation"] = "PASS" if R["hash_before_after_match"] == "YES" else "FAIL"
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["v3_isolation"] = "PASS" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "FAIL"
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = []
    for r_, _, fs in os.walk(V2):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim:
                v2c.append(os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/"))
    R["v2_isolation"] = "PASS" if not v2c else "FAIL"
    R["boundary_violation"] = 0 if R["hash_before_after_match"] == "YES" else 1
    R.setdefault("execution_actor", "UNKNOWN")
    jp = os.path.join(HERE, "V1_R28_RESET_ASSET_AUDIT.json")
    with open(jp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(R, fh, indent=1, ensure_ascii=False, default=str)
    minf = {"task_status": R.get("task_status"), "reset_commit": C, "parent_commit": P,
              "old_ledger_snapshot": R.get("old_ledger_snapshot"),
              "old_ledger_records_total": R.get("old_ledger_records_total", 30),
              "old_ledger_records_found": R.get("old_ledger_records_found", 0),
              "old_ledger_records_missing": R.get("old_ledger_records_missing", 0),
              "old_statistics_snapshot": R.get("old_statistics_snapshot"),
              "old_pnl_isolation": R.get("old_pnl_isolation"),
              "new_run_counter_boundary": R.get("new_run_counter_boundary"),
              "new_run_pnl_boundary": R.get("new_run_pnl_boundary"),
              "new_run_balance_boundary": R.get("new_run_balance_boundary"),
              "run_accounting_boundary": R.get("run_accounting_boundary"),
              "execution_actor": R.get("execution_actor"),
              "automation_enabled": R.get("automation_enabled"), "v1_engine_process": R.get("v1_engine_process"),
              "reset": 0, "new_run": 0, "v1_start": 0, "automation_enable": 0, "mt5_access": 0,
              "order_send": 0, "position_close": 0, "position_modify": 0, "order_cancel": 0,
              "ledger_write": 0, "state_write": 0, "source_write": 0, "config_write": 0, "git_commit": "NONE",
              "boundary_violation": R.get("boundary_violation", 0)}
    with open(os.path.join(HERE, "V1_R28_RESET_ASSET_AUDIT_MIN.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(minf, fh, indent=1, ensure_ascii=False, default=str)
    lines = ["# R28 - Reset asset and PnL boundary audit", "", "```text",
             "V1_R28_RESET_ASSET_AUDIT = " + str(R.get("task_status")), "",
             "OLD_LEDGER_SNAPSHOT = " + str(R.get("old_ledger_snapshot")),
             "OLD_LEDGER_RECORDS_FOUND = " + str(R.get("old_ledger_records_found")),
             "OLD_LEDGER_RECORDS_MISSING = " + str(R.get("old_ledger_records_missing")), "",
             "OLD_STATISTICS_SNAPSHOT = " + str(R.get("old_statistics_snapshot")), "",
             "OLD_PNL_ISOLATION = " + str(R.get("old_pnl_isolation")), "",
             "NEW_RUN_COUNTER_BOUNDARY = " + str(R.get("new_run_counter_boundary")),
             "NEW_RUN_PNL_BOUNDARY = " + str(R.get("new_run_pnl_boundary")),
             "NEW_RUN_BALANCE_BOUNDARY = " + str(R.get("new_run_balance_boundary")), "",
             "RUN_ACCOUNTING_BOUNDARY = " + str(R.get("run_accounting_boundary")), "",
             "EXECUTION_ACTOR = " + str(R.get("execution_actor")), "",
             "RESET = 0", "NEW_RUN = 0", "V1_START = 0", "AUTOMATION_ENABLE = 0", "MT5_ACCESS = 0", "",
             "ORDER_SEND = 0", "POSITION_CLOSE = 0", "POSITION_MODIFY = 0", "ORDER_CANCEL = 0", "",
             "LEDGER_WRITE = 0", "STATE_WRITE = 0", "SOURCE_WRITE = 0", "CONFIG_WRITE = 0", "GIT_COMMIT = NONE", "",
             "V1_ISOLATION = " + str(R.get("v1_isolation")), "V2_ISOLATION = " + str(R.get("v2_isolation")),
             "V3_ISOLATION = " + str(R.get("v3_isolation")),
             "BOUNDARY_VIOLATION = " + str(R.get("boundary_violation")), "",
             "ENGINE_HASH_STABLE = " + str(R.get("engine_hash_stable")),
             "LEDGER_HASH_STABLE = " + str(R.get("ledger_hash_stable")),
             "STATISTICS_HASH_STABLE = " + str(R.get("statistics_hash_stable")),
             "RUN_META_HASH_STABLE = " + str(R.get("run_meta_hash_stable")), "",
             "R28_GATE = " + str(R.get("r28_gate")), "```", "",
             "## anchors", "", "```text", "parent ledger lines = " + str(R.get("old_ledger_records_total")),
             "parent ledger file sha256 = " + str(R.get("parent_ledger_file_sha256")),
             "commit ledger file sha256 = " + str(R.get("commit_ledger_file_sha256")),
             "parent statistics file sha256 = " + str(R.get("parent_statistics_file_sha256")), "```", "",
             "## search scope", "", "```text", "scanned_text_files = " + str(R.get("scanned_text_files")),
             "ledger snapshot candidates = " + str(len(R.get("old_ledger_snapshot_candidates", []))),
             "statistics snapshot candidates = " + str(len(R.get("old_statistics_snapshot_candidates", []))),
             "archive-extension files seen = " + str(len(R.get("archives_seen", []))),
             "keyword files = " + str(len(R.get("keyword_files", []))), "```", "",
             "## ledger snapshot candidates (top)", "", "| path | size | lines | matched_records | mtime |",
             "|---|---:|---:|---:|---|"]
    for c in R.get("old_ledger_snapshot_candidates", [])[:10]:
        lines.append("| `" + c["path"] + "` | " + str(c["size"]) + " | " + str(c["lines"]) + " | " +
                       str(c["matched_records"]) + " | " + str(c["mtime"]) + " |")
    lines += ["", "## statistics snapshot candidates (top)", "", "| path | size | exact_parent_match | mtime |", "|---|---:|---|---|"]
    for c in R.get("old_statistics_snapshot_candidates", [])[:10]:
        lines.append("| `" + c["path"] + "` | " + str(c["size"]) + " | " + str(c["matches_parent_statistics"]) + " | " + str(c["mtime"]) + " |")
    lines += ["", "## PnL token hits", "", "```text",
              json.dumps(R.get("pnl_token_hits", []), ensure_ascii=False)[:1200], "```", "",
              "## six requirements", "", "```text",
              json.dumps(R.get("six_requirements", {}), ensure_ascii=False), "```", "",
              "## Q1-Q8", "", "```text"]
    for q in ("Q1_old_ledger_external_copy", "Q2_old_statistics_snapshot", "Q3_old_pnl_run_binding",
                "Q4_new_run_opening_boundary", "Q5_new_run_may_inherit_counters", "Q6_new_run_may_inherit_pnl",
                "Q7_old_ledger_recoverable", "Q8_safe_to_reset"):
        lines.append(q + " = " + str(R.get(q)))
    lines += ["```", "", "## timeline", "", "```text", json.dumps(R.get("timeline", {}), ensure_ascii=False), "```", "",
              "## archive vs git separation", "", "```text",
              json.dumps(R.get("archive_classification", {}), ensure_ascii=False), "```", "",
              "## core principle", "", "```text",
              "finding one archive is not proof of reset safety; the old ledger, old statistics and old PnL must",
              "each have a complete, explicit, replayable accounting boundary to the new run.", "```"]
    with open(os.path.join(HERE, "V1_R28_RESET_ASSET_AUDIT_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print("\n=== FINAL ===", flush=True)
    print(json.dumps(minf, ensure_ascii=True), flush=True)
    print("artifacts:", jp, "|", os.path.join(HERE, "V1_R28_RESET_ASSET_AUDIT_REPORT.md"), flush=True)
    sys.exit(0 if R.get("r28_gate") == "PASS" else 2)


if __name__ == "__main__":
    main()
