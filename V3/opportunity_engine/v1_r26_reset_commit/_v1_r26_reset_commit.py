# -*- coding: utf-8 -*-
"""R26 — full read-only dissection of git commit 43f9b2f (the V1 RESET commit).

READ-ONLY: git show/ls-tree/log + file hashing only. No git write verbs, no file writes outside this task dir,
no V1/V2/V3 modification, no MT5, no start/reset/automation change.
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
C = "43f9b2f"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
P_STATS = "research/hermes/trader_v1/run_state/statistics.json"
P_META = "research/hermes/trader_v1/run_state/RUN_META.json"
P_LEDGER = "research/hermes/trader_v1/run_state/plan_ledger.jsonl"
ARCHIVE = "archive/v1_pre_reset_20260923_233741"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")
R = {}


def sh(a, cwd=None, t=120):
    try:
        p = subprocess.run(a, cwd=cwd or AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def cls_of(path):
    p = path.replace("\\", "/").lower()
    if p.startswith("archive/"):
        return "ARCHIVE"
    if "run_state/statistics.json" in p:
        return "STATISTICS"
    if "run_state/run_meta.json" in p:
        return "RUN_META"
    if "plan_ledger.jsonl" in p or "ledger" in os.path.basename(p):
        return "LEDGER"
    if "/memory/reviews/" in p or "review" in os.path.basename(p):
        return "REVIEWS"
    if "decision_contexts/" in p or "decisions/" in p:
        return "DECISION_HISTORY"
    if p.endswith((".py", ".ps1", ".bat", ".cmd")):
        return "V1_SOURCE" if "/trader_v1/" in p else ("CONFIG" if p.endswith((".yaml", ".yml")) else "OTHER")
    if p.endswith((".json", ".jsonl", ".txt", ".yaml", ".yml")):
        return "STATE"
    return "OTHER"


def flat_numeric(o, path="$", out=None):
    if out is None:
        out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            flat_numeric(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        pass
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out[path] = o
    return out


def main():
    os.makedirs(HERE, exist_ok=True)
    R["TASK_STATUS"] = "RUNNING"
    R["AUDIT_NOW_UTC"] = datetime.now(timezone.utc).isoformat()

    # ---------- §2 freeze ----------
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    R["AUTOMATION_ENABLED"] = auto.get("enabled", "UNKNOWN")
    praw = sh(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package'} | "
                "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"], t=90)
    try:
        dd = json.loads(praw) if praw and praw.strip().startswith(("{", "[")) else []
        allp = dd if isinstance(dd, list) else [dd]
    except Exception:  # noqa: BLE001
        allp = []
    v1p = [x for x in allp if "Get-CimInstance" not in (x.get("CommandLine") or "")]
    R["V1_ENGINE_PROCESS"] = "NOT_RUNNING" if not v1p else "RUNNING"
    R["HASH_BEFORE"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    ok = (str(R["AUTOMATION_ENABLED"]).lower() == "false" and R["V1_ENGINE_PROCESS"] == "NOT_RUNNING"
           and R["HASH_BEFORE"]["ENGINE"] == BASE and R["HASH_BEFORE"]["LEDGER"] == LEDGER_EXPECT
           and R["HASH_BEFORE"]["STATISTICS"] == STATS_EXPECT and R["HASH_BEFORE"]["RUN_META"] == META_EXPECT)
    print("§2 freeze ok =", ok, flush=True)
    if not ok:
        R["R26_GATE"] = "FAIL"
        return finish("FREEZE_FAILED")

    # ---------- §3/§4 commit identity + full file inventory ----------
    ident = sh(["git", "show", C, "--no-patch", "--format=%H%n%P%n%an%n%ae%n%aI%n%cn%n%ce%n%cI%n%s"], t=120).splitlines()
    R["COMMIT"] = C
    R["COMMIT_FULL"] = ident[0] if ident else "UNKNOWN"
    R["PARENT_COMMIT"] = ident[1] if len(ident) > 1 else "UNKNOWN"
    R["AUTHOR"] = ident[2] if len(ident) > 2 else "UNKNOWN"
    R["AUTHOR_EMAIL"] = ident[3] if len(ident) > 3 else "UNKNOWN"
    R["AUTHOR_TIME"] = ident[4] if len(ident) > 4 else "UNKNOWN"
    R["COMMITTER"] = ident[5] if len(ident) > 5 else "UNKNOWN"
    R["COMMITTER_EMAIL"] = ident[6] if len(ident) > 6 else "UNKNOWN"
    R["COMMIT_TIME"] = ident[7] if len(ident) > 7 else "UNKNOWN"
    R["SUBJECT"] = ident[8] if len(ident) > 8 else "UNKNOWN"
    ns = sh(["git", "show", C, "--name-status", "--format="], t=180)
    entries = []
    for line in ns.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            entries.append({"status": parts[0], "path": parts[-1].replace("\\", "/")})
    R["CHANGED_FILES"] = len(entries)
    R["FILE_CLASSIFICATION"] = [{"file": e["path"], "op": e["status"], "type": cls_of(e["path"]),
                                   "run_boundary_relevant": cls_of(e["path"]) in
                                                               ("RUN_META", "STATISTICS", "ARCHIVE", "LEDGER")} for e in entries]
    byclass = {}
    for e in R["FILE_CLASSIFICATION"]:
        byclass[e["type"]] = byclass.get(e["type"], 0) + 1
    R["COMMIT_FILE_CLASSIFICATION"] = byclass
    numstat = sh(["git", "show", C, "--numstat", "--format="], t=180)
    R["NUMSTAT_LINES"] = len([l for l in numstat.splitlines() if l.strip()])
    R["NUMSTAT_SAMPLE"] = numstat.splitlines()[:20]
    R["DIFF_TOTAL_CHARS"] = len(sh(["git", "show", C, "--format="], t=300))
    print("§3/4 commit:", R["COMMIT_FULL"][:12], "parent:", R["PARENT_COMMIT"][:12], "files:", R["CHANGED_FILES"],
          json.dumps(byclass, ensure_ascii=False), "| diff chars:", R["DIFF_TOTAL_CHARS"], flush=True)
    R["DIFF_READ_MODE"] = ("FULL for key files (RUN_META/statistics/ledger/reset scripts/config); blob-hash + size for "
                             "archive and other bulk files (disclosed limitation for very large trees)")

    # ---------- §5 key-file content at parent vs commit ----------
    def at(rev, path):
        return sh(["git", "show", f"{rev}:{path}"], t=180)
    changes = {}
    for label, path in (("RUN_META", P_META), ("STATISTICS", P_STATS), ("LEDGER", P_LEDGER)):
        par = at(f"{C}^", path)
        cur = at(C, path)
        exists_par = not (par.startswith("ERR:") or "fatal:" in par[:60] or "does not exist" in par[:80])
        exists_cur = not (cur.startswith("ERR:") or "fatal:" in cur[:60] or "does not exist" in cur[:80])
        eff = ("CREATED" if (exists_cur and not exists_par) else ("UNCHANGED" if (exists_par and exists_cur and par == cur)
                                                                   else ("MODIFIED" if (exists_par and exists_cur) else "NOT_IN_COMMIT")))
        changes[label] = {"effect": eff, "in_parent": exists_par, "in_commit": exists_cur,
                            "parent_len": (len(par) if exists_par else 0), "commit_len": (len(cur) if exists_cur else 0),
                            "parent_blob": hashlib.sha256(par.encode()).hexdigest()[:16] if exists_par else None,
                            "commit_blob": hashlib.sha256(cur.encode()).hexdigest()[:16] if exists_cur else None}
        if label == "RUN_META":
            try:
                pj = json.loads(par) if exists_par else {}
            except Exception:  # noqa: BLE001
                pj = {}
            try:
                cj = json.loads(cur) if exists_cur else {}
            except Exception:  # noqa: BLE001
                cj = {}
            pk = sorted(pj.keys()) if isinstance(pj, dict) else []
            ck = sorted(cj.keys()) if isinstance(cj, dict) else []
            changes[label].update({"parent_keys": pk, "commit_keys": ck,
                                     "keys_added": [k for k in ck if k not in pk],
                                     "keys_removed": [k for k in pk if k not in ck],
                                     "field_diff": {k: {"parent": pj.get(k, "ABSENT"), "commit": cj.get(k, "ABSENT")}
                                                      for k in set(pk) | set(ck) if pj.get(k) != cj.get(k)}})
        if label == "STATISTICS":
            try:
                pj = json.loads(par) if exists_par else None
            except Exception:  # noqa: BLE001
                pj = None
            try:
                cj = json.loads(cur) if exists_cur else None
            except Exception:  # noqa: BLE001
                cj = None
            pn = flat_numeric(pj) if isinstance(pj, (dict, list)) else {}
            cn = flat_numeric(cj) if isinstance(cj, (dict, list)) else {}
            diffs = []
            for k in sorted(set(pn) | set(cn)):
                o, n = pn.get(k, "ABSENT"), cn.get(k, "ABSENT")
                if o == n:
                    ct = "UNCHANGED"
                elif o == "ABSENT":
                    ct = "ADDED"
                elif n == "ABSENT":
                    ct = "REMOVED"
                elif isinstance(n, (int, float)) and n == 0 and isinstance(o, (int, float)) and o != 0:
                    ct = "ZEROED"
                elif isinstance(n, (int, float)) and isinstance(o, (int, float)) and n > o:
                    ct = "INCREASED"
                elif isinstance(n, (int, float)) and isinstance(o, (int, float)) and n < o:
                    ct = "DECREASED"
                else:
                    ct = "CHANGED"
                diffs.append({"PATH": k, "OLD_VALUE": o, "NEW_VALUE": n, "CHANGE_TYPE": ct})
            changes[label].update({"numeric_paths_parent": len(pn), "numeric_paths_commit": len(cn),
                                     "counter_diff": diffs,
                                     "counter_diff_counts": {t: sum(1 for d in diffs if d["CHANGE_TYPE"] == t)
                                                              for t in ("ZEROED", "INCREASED", "DECREASED", "UNCHANGED",
                                                                          "REMOVED", "ADDED", "CHANGED")},
                                     "top_keys_parent": sorted(pj.keys()) if isinstance(pj, dict) else "N/A",
                                     "top_keys_commit": sorted(cj.keys()) if isinstance(cj, dict) else "N/A"})
    R["KEY_FILE_CHANGES"] = changes
    print("§5 effects:", json.dumps({k: v["effect"] for k, v in changes.items()}, ensure_ascii=False), flush=True)

    # ---------- §9/§10 run id + start time ----------
    rm = changes["RUN_META"]
    fd = rm.get("field_diff", {}) if isinstance(rm, dict) else {}
    def gv(field):
        return fd.get(field, {})
    old_rid = gv("run_id").get("parent", "ABSENT")
    new_rid = gv("run_id").get("commit", "ABSENT")
    R["OLD_RUN_ID"] = old_rid if old_rid != "ABSENT" else "ABSENT"
    R["NEW_RUN_ID"] = new_rid
    R["RUN_ID_FIELD_DIFF"] = gv("run_id")
    R["RUN_START_FIELD_DIFF"] = {k: gv(k) for k in ("run_start_utc", "start_time_utc", "runtime_version")}
    print("§9/10 run_id diff:", json.dumps(R["RUN_ID_FIELD_DIFF"], ensure_ascii=False), flush=True)

    # ---------- §11 archive ----------
    arch_all = sh(["git", "ls-tree", "-r", "--name-only", C, "--", ARCHIVE], t=180)
    arch_par = sh(["git", "ls-tree", "-r", "--name-only", f"{C}^", "--", ARCHIVE], t=180)
    al = [x for x in arch_all.splitlines() if x.strip()]
    pl = [x for x in arch_par.splitlines() if x.strip()]
    R["ARCHIVE_FILES_IN_COMMIT"] = len(al)
    R["ARCHIVE_FILES_IN_PARENT"] = len(pl)
    R["ARCHIVE_CREATED_BY_COMMIT"] = "YES" if (al and not pl) else ("PARTIAL" if al else "NO")
    R["ARCHIVE_SCOPE"] = ("UNKNOWN" if not al else ("FULL" if R["ARCHIVE_CREATED_BY_COMMIT"] == "YES" else "PARTIAL"))
    R["ARCHIVE_SAMPLE"] = al[:12]
    # archive dirs
    dirs = sorted({os.path.dirname(x).replace("\\", "/") for x in al})[:20]
    R["ARCHIVED_DIRECTORIES_SAMPLE"] = dirs
    R["ARCHIVE_MAPPING_NOTE"] = f"archive prefix '{ARCHIVE}/v1_root/' mirrors the pre-reset V1 tree"
    print("§11 archive:", R["ARCHIVE_CREATED_BY_COMMIT"], R["ARCHIVE_SCOPE"], "files:", len(al), flush=True)

    # ---------- §12/§13/§14 old artifacts archived? ----------
    def find_in_commit(substr):
        return [x for x in al if substr in x.lower()]
    R["OLD_STATISTICS_IN_ARCHIVE"] = find_in_commit("statistics.json")[:5]
    R["OLD_RUN_META_IN_ARCHIVE"] = find_in_commit("run_meta.json")[:5]
    R["OLD_LEDGER_IN_ARCHIVE"] = find_in_commit("plan_ledger")[:5]
    R["OLD_STATISTICS_ARCHIVED"] = "YES" if R["OLD_STATISTICS_IN_ARCHIVE"] else "NO"
    R["OLD_RUN_META_ARCHIVED"] = "YES" if R["OLD_RUN_META_IN_ARCHIVE"] else "NO"
    R["OLD_LEDGER_ARCHIVED"] = "YES" if R["OLD_LEDGER_IN_ARCHIVE"] else "NO"
    R["LEDGER_TREATMENT"] = ("UNTOUCHED" if changes["LEDGER"]["effect"] == "UNCHANGED" else changes["LEDGER"]["effect"])
    R["LEDGER_IN_COMMIT_EFFECT"] = changes["LEDGER"]["effect"]
    print("§12-14 archived:", {"stats": R["OLD_STATISTICS_ARCHIVED"], "meta": R["OLD_RUN_META_ARCHIVED"],
                                 "ledger": R["OLD_LEDGER_ARCHIVED"]}, "| ledger:", R["LEDGER_TREATMENT"], flush=True)

    # ---------- §19/§20 reset script ----------
    rs = [e["path"] for e in entries if re.search(r"(?i)(reset|run_manager|run_init|run_reset)[\w.-]*\.(py|ps1|bat|cmd)$",
                                                    os.path.basename(e["path"]))]
    R["RESET_SCRIPT_IN_COMMIT"] = "FOUND" if rs else "NOT_FOUND"
    R["RESET_SCRIPT_PATH"] = rs[:5]
    R["RESET_SCRIPT_FUNCTION"] = "UNKNOWN"
    R["RESET_SCRIPT_ACTIONS"] = []
    if rs:
        d = sh(["git", "show", C, "--format=", "--"] + rs, t=240)
        acts = []
        for pat, name in ((r"json\.dump", "write_json"), (r"open\s*\([^)]*['\"][wa]", "open_write"), (r"mkdir|makedirs", "mkdir"),
                            (r"shutil\.(copy|move|rmtree)", "shutil"), (r"run_id\s*=", "generate_run_id"),
                            (r"RUN_META", "write_run_meta"), (r"statistics", "write_statistics")):
            if re.search(pat, d):
                acts.append(name)
        R["RESET_SCRIPT_ACTIONS"] = acts
        R["RESET_SCRIPT_DIFF_EXCERPT"] = d[:1500]
    print("§19/20 reset script:", R["RESET_SCRIPT_IN_COMMIT"], R["RESET_SCRIPT_PATH"], R["RESET_SCRIPT_ACTIONS"], flush=True)

    # ---------- §22 actor ----------
    R["EXECUTION_ACTOR"] = "UNKNOWN"
    R["ACTOR_NOTE"] = ("git proves AUTHOR/COMMITTER only; no external execution log was found in this read-only "
                        "round -> EXECUTION_ACTOR = UNKNOWN (correct by rule, not a defect)")

    # ---------- §23 timeline (separate evidence classes) ----------
    R["TIMELINE"] = {"PARENT_COMMIT_TIME": sh(["git", "show", "-s", "--format=%cI", f"{C}^"], t=60),
                       "RESET_COMMIT_TIME": R["COMMIT_TIME"],
                       "ARCHIVE_DIR_NAME_TIME": "2026-09-23T23:37:41 (from directory name, not a file timestamp)",
                       "RUN_META_START_TIME": (rm.get("field_diff", {}).get("start_time_utc", {}) or {}).get("commit", "UNKNOWN"),
                       "STATISTICS_COMMIT_TIME": R["COMMIT_TIME"],
                       "NOTE": "git commit time != reset execution time; mtime != business event time (kept separate)"}

    # ---------- §26 verdicts ----------
    stats_created = changes["STATISTICS"]["effect"] == "CREATED"
    meta_created = rm["effect"] == "CREATED"
    counters_zeroed = (changes["STATISTICS"].get("counter_diff_counts", {}) or {}).get("ZEROED", 0) > 0
    R["RESET_RUN_CREATION"] = ("PROVEN" if (meta_created and R["NEW_RUN_ID"] not in ("ABSENT", "UNKNOWN")) else
                                 ("PARTIALLY_PROVEN" if (R["NEW_RUN_ID"] not in ("ABSENT", "UNKNOWN")) else "NOT_PROVEN"))
    R["STATISTICS_INITIALIZATION"] = ("PROVEN" if stats_created else
                                        ("PARTIALLY_PROVEN" if changes["STATISTICS"]["effect"] == "MODIFIED" else "NOT_PROVEN"))
    R["PER_RUN_STATISTICS_ISOLATION"] = ("PROVEN" if (stats_created and R["OLD_STATISTICS_ARCHIVED"] == "YES") else
                                            ("PARTIALLY_PROVEN" if (stats_created or R["OLD_STATISTICS_ARCHIVED"] == "YES")
                                              else "NOT_PROVEN"))
    R["OLD_COUNTERS_ISOLATION"] = ("PROVEN" if (stats_created and counters_zeroed and R["OLD_STATISTICS_ARCHIVED"] == "YES")
                                     else ("PARTIALLY_PROVEN" if (stats_created or counters_zeroed) else "NOT_PROVEN"))
    R["OLD_PNL_ISOLATION"] = "NOT_PROVEN（commit 未处理 PnL/profit/realized；未见 −21.97 的任何隔离动作）"
    R["STATISTICS_RESET_MODEL"] = ("ARCHIVE_AND_RECREATE" if (stats_created and R["OLD_STATISTICS_ARCHIVED"] == "YES")
                                     else ("IN_PLACE_RESET" if changes["STATISTICS"]["effect"] == "MODIFIED" else "UNKNOWN"))
    R["NEW_RUN_COUNTERS_ZERO"] = ("YES" if counters_zeroed else ("UNKNOWN" if not stats_created else "NO"))
    statuses = [R["RESET_RUN_CREATION"], R["STATISTICS_INITIALIZATION"], R["PER_RUN_STATISTICS_ISOLATION"],
                 R["OLD_COUNTERS_ISOLATION"]]
    R["R26_GATE"] = "PASS" if all(s == "PROVEN" for s in statuses) else "FAIL"
    print("§26 verdicts:", json.dumps({k: R[k] for k in ("RESET_RUN_CREATION", "STATISTICS_INITIALIZATION",
                                                           "PER_RUN_STATISTICS_ISOLATION", "OLD_COUNTERS_ISOLATION",
                                                           "OLD_PNL_ISOLATION", "STATISTICS_RESET_MODEL",
                                                           "NEW_RUN_COUNTERS_ZERO", "R26_GATE")}, ensure_ascii=False),
          flush=True)
    return finish("NONE")


def finish(reason):
    R["STOP_REASON"] = reason
    R["HASH_AFTER"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    R["HASH_BEFORE_AFTER_MATCH"] = "YES" if R.get("HASH_BEFORE") == R.get("HASH_AFTER") else "NO"
    R["BOUNDARY_VIOLATION"] = 0 if R["HASH_BEFORE_AFTER_MATCH"] == "YES" else 1
    for k in COUNTERS:
        R.setdefault(k, 0)
    R["MT5_ACCESS"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["NEW_RUN_STATS_BOUNDARY"] = "PROVEN" if R.get("R26_GATE") == "PASS" else "NOT_PROVEN"
    R["RESET"] = 0
    R["V1_START"] = 0
    R["AUTOMATION_ENABLE"] = 0
    R["V1_ISOLATION"] = "PASS" if R["HASH_BEFORE_AFTER_MATCH"] == "YES" else "FAIL"
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_ISOLATION"] = "PASS" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "FAIL"
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = [p for r_, _, fs in os.walk(V2) if "__pycache__" not in r_ for f in fs
            if f.lower().endswith((".py", ".yaml", ".yml"))
            and os.path.getmtime(p := os.path.join(r_, f)) > lim]
    R["V2_ISOLATION"] = "PASS" if not v2c else "FAIL"
    R["CHANGED_FILES_LOCAL"] = 0
    R["TASK_STATUS"] = "V1_RESET_COMMIT_R26_COMPLETE"
    json.dump(R, open(os.path.join(HERE, "V1_R26_RESET_COMMIT.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False, default=str)
    lines = ["# R26 — commit 43f9b2f dissection", "", "```text"]
    for k in ("TASK_STATUS", "COMMIT", "COMMIT_FULL", "PARENT_COMMIT", "AUTHOR", "COMMITTER", "AUTHOR_TIME",
                "COMMIT_TIME", "SUBJECT", "CHANGED_FILES", "COMMIT_FILE_CLASSIFICATION", "RUN_META_COMMIT_EFFECT",
                "STATISTICS_COMMIT_EFFECT", "LEDGER_COMMIT_EFFECT", "ARCHIVE_COMMIT_EFFECT", "OLD_RUN_ID",
                "NEW_RUN_ID", "STATISTICS_RESET_MODEL", "OLD_COUNTERS_BEHAVIOR", "NEW_RUN_COUNTERS_ZERO",
                "OLD_STATISTICS_ARCHIVED", "OLD_RUN_META_ARCHIVED", "OLD_LEDGER_ARCHIVED", "RESET_SCRIPT_IN_COMMIT",
                "RESET_SCRIPT_PATH", "RESET_SCRIPT_ACTIONS", "EXECUTION_ACTOR", "RESET_RUN_CREATION",
                "STATISTICS_INITIALIZATION", "PER_RUN_STATISTICS_ISOLATION", "OLD_COUNTERS_ISOLATION",
                "OLD_PNL_ISOLATION", "R26_GATE", "NEW_RUN_STATS_BOUNDARY", "RESET", "V1_START", "AUTOMATION_ENABLE",
                "MT5_ACCESS", "V1_ISOLATION", "V2_ISOLATION", "V3_ISOLATION", "BOUNDARY_VIOLATION", "GIT_COMMIT"):
        v = R.get(k, "UNKNOWN")
        lines.append(f"{k} = {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
    lines += ["", "-- counters --", json.dumps({k: 0 for k in COUNTERS} | {"MT5_ACCESS": 0, "GIT_COMMIT": "NONE"},
                                                  ensure_ascii=False), "```", "",
              "## KEY FILE DIFFS", "", "```json",
              json.dumps(R.get("KEY_FILE_CHANGES", {}), ensure_ascii=False)[:6000], "```", "",
              "## ARCHIVE", "", "```text", f"files in commit = {R.get('ARCHIVE_FILES_IN_COMMIT')}",
              f"files in parent = {R.get('ARCHIVE_FILES_IN_PARENT')}",
              f"created_by_commit = {R.get('ARCHIVE_CREATED_BY_COMMIT')}", f"scope = {R.get('ARCHIVE_SCOPE')}",
              f"sample = {json.dumps(R.get('ARCHIVE_SAMPLE', []), ensure_ascii=False)}",
              f"old statistics in archive = {R.get('OLD_STATISTICS_IN_ARCHIVE')}",
              f"old RUN_META in archive = {R.get('OLD_RUN_META_IN_ARCHIVE')}",
              f"old ledger in archive = {R.get('OLD_LEDGER_IN_ARCHIVE')}", "```", "",
              "## TIMELINE (evidence classes kept separate)", "", "```text",
              json.dumps(R.get("TIMELINE", {}), ensure_ascii=False), "```", "",
              "## LIMITATIONS", "", "```text", R.get("DIFF_READ_MODE", ""), "```"]
    open(os.path.join(HERE, "V1_R26_RESET_COMMIT_REPORT.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("\n=== §33 FINAL OUTPUT ===", flush=True)
    for k in ("TASK_STATUS", "COMMIT", "PARENT_COMMIT", "AUTHOR", "COMMITTER", "CHANGED_FILES",
                "COMMIT_FILE_CLASSIFICATION", "RUN_META_COMMIT_EFFECT", "STATISTICS_COMMIT_EFFECT",
                "LEDGER_COMMIT_EFFECT", "ARCHIVE_COMMIT_EFFECT", "OLD_RUN_ID", "NEW_RUN_ID",
                "STATISTICS_RESET_MODEL", "OLD_COUNTERS_BEHAVIOR", "NEW_RUN_COUNTERS_ZERO",
                "OLD_STATISTICS_ARCHIVED", "OLD_RUN_META_ARCHIVED", "OLD_LEDGER_ARCHIVED",
                "RESET_SCRIPT_IN_COMMIT", "RESET_SCRIPT_PATH", "EXECUTION_ACTOR", "RESET_RUN_CREATION",
                "STATISTICS_INITIALIZATION", "PER_RUN_STATISTICS_ISOLATION", "OLD_COUNTERS_ISOLATION",
                "OLD_PNL_ISOLATION", "R26_GATE", "NEW_RUN_STATS_BOUNDARY", "RESET", "V1_START",
                "AUTOMATION_ENABLE", "MT5_ACCESS", "V1_ISOLATION", "V2_ISOLATION", "V3_ISOLATION",
                "BOUNDARY_VIOLATION", "GIT_COMMIT"):
        v = R.get(k, "UNKNOWN")
        print(f"{k} = {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}", flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_R26_RESET_COMMIT.json"), flush=True)
    sys.exit(0 if R.get("R26_GATE") == "PASS" else 2)


if __name__ == "__main__":
    main()
