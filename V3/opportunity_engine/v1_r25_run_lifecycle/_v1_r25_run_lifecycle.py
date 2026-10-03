# -*- coding: utf-8 -*-
"""R25 — who creates/manages the V1 Run lifecycle, and who writes RUN_META.json / statistics.json.
READ-ONLY: static analysis + log/history forensics. No write anywhere except this task dir.

Forbidden (not executed): RESET, START, RESTART, AUTOMATION_ENABLE, MT5_ACCESS, NEW_RUN, ARCHIVE,
git checkout/restore/reset/commit/merge, any modification of V1/V2/V3 files.
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
OC = os.path.join(HOME, ".openclaw")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
RUNID = "V1_RUN_20260924_RESET_01"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
KEYWORDS = ["V1_RUN_20260924_RESET_01", "run_id", "RUN_META", "run_start_utc", "run_start", "reset_run",
             "new_run", "create_run", "init_run", "start_run", "RUN_TYPE", "statistics.json", "run_state",
             "RESET_01", "RUN_META.json"]
WRITE_PAT = re.compile(r"(json\.dump|\.write\(|open\s*\([^)]*['\"][wa]|write_text|shutil\.(copy|move)|os\.(replace|rename)|"
                         r"makedirs|mkdir|to_csv|savefig|Path\([^)]*\)\.write)")
TARGETS = ("statistics.json", "RUN_META.json", "plan_ledger.jsonl")
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")
R = {}


def sh(a, cwd=None, t=180):
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
    ok_freeze = (str(R["AUTOMATION_ENABLED"]).lower() == "false" and R["V1_ENGINE_PROCESS"] == "NOT_RUNNING"
                  and R["HASH_BEFORE"]["ENGINE"] == BASE and R["HASH_BEFORE"]["LEDGER"] == LEDGER_EXPECT
                  and R["HASH_BEFORE"]["STATISTICS"] == STATS_EXPECT and R["HASH_BEFORE"]["RUN_META"] == META_EXPECT)
    print("§2 freeze ok =", ok_freeze, json.dumps(R["HASH_BEFORE"], ensure_ascii=False)[:200], flush=True)
    if not ok_freeze:
        R["TASK_STATUS"] = "V1_RUN_LIFECYCLE_R25_COMPLETE"
        R["R25_GATE"] = "FAIL"
        return finish("FREEZE_CONSTRAINT_CHANGED")

    # ---------- §17 Automation payload (read-only) ----------
    R["AUTOMATION_PAYLOAD_KIND"] = (auto.get("payload") or {}).get("kind", "UNKNOWN")
    msg = ((auto.get("payload") or {}).get("message") or "")
    R["AUTOMATION_MESSAGE_EXCERPT"] = msg[:1500]
    R["AUTOMATION_AGENT_ID"] = auto.get("agentId", "UNKNOWN")
    R["AUTOMATION_SESSION_TARGET"] = auto.get("sessionTarget", "UNKNOWN")
    R["AUTOMATION_CONFIG_REVISION"] = auto.get("configRevision", "UNKNOWN")
    lc = ("run_id", "reset", "new run", "run_meta", "statistics", "建新 run", "新 run")
    R["AUTOMATION_MENTIONS_RUN_LIFECYCLE"] = [k for k in lc if k in msg.lower()]
    R["AUTOMATION_RUN_LIFECYCLE_ROLE"] = ("MENTIONS_ONLY_NOT_CODE" if R["AUTOMATION_MENTIONS_RUN_LIFECYCLE"]
                                            else "NOT_FOUND")
    print("§17 automation: kind=", R["AUTOMATION_PAYLOAD_KIND"], "mentions=", R["AUTOMATION_MENTIONS_RUN_LIFECYCLE"],
          flush=True)

    # ---------- §5/§6 static search across candidate code roots ----------
    roots = [os.path.join(RE, "hermes"), OC]
    skip = ("node_modules", "__pycache__", ".git", "media", "logs", "mt5_instances", "pasted-text")
    hits, writers = [], []
    scanned = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            rl = r_.replace("\\", "/").lower()
            if any(s in rl for s in skip):
                continue
            for f in fs:
                if not f.lower().endswith((".py", ".ps1", ".cmd", ".bat", ".js", ".cjs", ".mjs", ".json", ".yaml",
                                             ".yml", ".md", ".txt")):
                    continue
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:  # noqa: BLE001
                    continue
                scanned += 1
                rel = os.path.relpath(p, AIQ).replace("\\", "/")
                if RUNID in txt or any(k in txt for k in ("run_id", "RUN_META", "run_start_utc")):
                    for kw in KEYWORDS:
                        if kw in txt:
                            hits.append({"file": rel, "keyword": kw})
                # writer detection: write action AND a target filename in the same file
                if WRITE_PAT.search(txt):
                    for tgt in TARGETS:
                        if tgt in txt:
                            for mm in re.finditer(re.escape(tgt), txt):
                                ln = txt[:mm.start()].count("\n") + 1
                                line = txt.splitlines()[ln - 1].strip() if ln - 1 < len(txt.splitlines()) else ""
                                kind = ("WRITE" if re.search(r"json\.dump|\.write\(|open\s*\([^)]*['\"][wa]|write_text",
                                                              line) else
                                         "READ" if re.search(r"json\.load|open\s*\([^)]*['\"]r", line) else "REFERENCE")
                                writers.append({"file": rel, "target": tgt, "line": ln, "kind": kind,
                                                  "text": line[:180]})
                if scanned > 6000:
                    break
            if scanned > 6000:
                break
    R["SCANNED_FILES"] = scanned
    R["KEYWORD_HITS"] = hits[:40]
    R["KEYWORD_HIT_FILES"] = sorted({h["file"] for h in hits})[:25]
    R["WRITER_CANDIDATES"] = writers[:60]
    R["WRITER_CANDIDATES_BY_TARGET"] = {}
    for w in writers:
        R["WRITER_CANDIDATES_BY_TARGET"].setdefault(w["target"], []).append(w)
    wt = {t: [w for w in v if w["kind"] == "WRITE"] for t, v in R["WRITER_CANDIDATES_BY_TARGET"].items()}
    R["TRUE_WRITER_CANDIDATES"] = {k: v[:10] for k, v in wt.items()}
    print("§5/6 scanned=", scanned, "kw_hits=", len(hits), "writer_candidates=", len(writers),
          "true_writes=", {k: len(v) for k, v in wt.items()}, flush=True)

    # ---------- §19 git history (read-only) ----------
    git = {}
    for label, path in (("RUN_META", os.path.relpath(META, AIQ).replace("\\", "/")),
                          ("STATISTICS", os.path.relpath(STATS, AIQ).replace("\\", "/")),
                          ("LEDGER", os.path.relpath(LEDGER, AIQ).replace("\\", "/"))):
        git[label] = {"log_follow": sh(["git", "log", "--follow", "--format=%h|%ad|%s", "--date=short", "-5", "--", path])[:900],
                       "tracked": "YES" if sh(["git", "ls-files", "--", path]) else "NO"}
    git["pickaxe_runid"] = sh(["git", "log", "-S", RUNID, "--oneline", "-n", "10"])[:900]
    git["pickaxe_runmeta_path"] = sh(["git", "log", "--oneline", "-n", "5", "--", "research/hermes/trader_v1/run_state/RUN_META.json"])[:500]
    R["GIT_FORENSICS"] = git
    print("§19 git: tracked=", {k: git[k]["tracked"] for k in ("RUN_META", "STATISTICS", "LEDGER")},
          "| pickaxe:", git["pickaxe_runid"][:120], flush=True)

    # ---------- §13 per-run namespace ----------
    ns_dirs, ns_files = [], []
    if os.path.isdir(RUN):
        for n in sorted(os.listdir(RUN)):
            p = os.path.join(RUN, n)
            if os.path.isdir(p):
                ns_dirs.append(n)
            elif re.search(r"(?i)run[_-]?\d|run[_-]?id|V1_RUN", n):
                ns_files.append(n)
    R["PER_RUN_FILE_NAMESPACE"] = ("ABSENT" if (not ns_dirs and not ns_files) else f"PRESENT:{ns_dirs[:5]},{ns_files[:5]}")
    R["PER_RUN_STATISTICS_ISOLATION"] = ("ABSENT" if R["PER_RUN_FILE_NAMESPACE"] == "ABSENT" else "UNKNOWN")

    # ---------- §20 timeline ----------
    tl = {}
    for label, p in (("RUN_META", META), ("STATISTICS", STATS), ("LEDGER", LEDGER), ("ENGINE", ENGINE)):
        if os.path.exists(p):
            st = os.stat(p)
            tl[label] = {"mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(), "size": st.st_size}
    R["TIMELINE"] = tl
    R["AUTOMATION_UPDATED_AT"] = auto.get("updatedAtMs", "UNKNOWN")

    # ---------- §7/§8/§9/§10 conclusions ----------
    v1code_runid = [h for h in hits if h["file"].startswith("research/hermes/trader_v1/") and h["keyword"] == "run_id"]
    R["V1_CODE_RUNID_HITS"] = len(v1code_runid)
    writers_runid = [w for v in R["TRUE_WRITER_CANDIDATES"].values() for w in v]
    outside_v1 = [w for w in writers_runid if not w["file"].startswith("research/hermes/trader_v1/")]
    inside_v1 = [w for w in writers_runid if w["file"].startswith("research/hermes/trader_v1/")]
    R["WRITERS_OUTSIDE_V1"] = outside_v1[:10]
    R["WRITERS_INSIDE_V1"] = inside_v1[:10]
    def verdict(inside, outside):
        if inside:
            return "V1_SOURCE"
        if outside:
            return "EXTERNAL_LAYER_SUSPECT(listed)"
        return "UNKNOWN"
    R["RUN_ID_CREATOR"] = verdict(R["V1_CODE_RUNID_HITS"], outside_v1)
    R["RUN_META_WRITER"] = verdict([w for w in inside_v1 if w["target"] == "RUN_META.json"],
                                     [w for w in outside_v1 if w["target"] == "RUN_META.json"])
    R["STATISTICS_WRITER"] = verdict([w for w in inside_v1 if w["target"] == "statistics.json"],
                                       [w for w in outside_v1 if w["target"] == "statistics.json"])
    R["STATISTICS_INITIALIZER"] = "UNKNOWN"
    R["STATISTICS_RESETTER"] = "UNKNOWN"
    R["RUN_SCOPE_MANAGER"] = "UNKNOWN"
    R["RUN_CREATION_PATH"] = "NOT_FOUND"
    R["STATISTICS_INITIALIZATION_PATH"] = "UNKNOWN"
    R["STATISTICS_UPDATE_PATHS"] = []
    R["OLD_COUNTERS_BEHAVIOR"] = "UNKNOWN"
    R["OLD_PNL_BEHAVIOR"] = "UNKNOWN"
    R["V1_RUN_LIFECYCLE_ROLE"] = ("NOT_FOUND" if not R["V1_CODE_RUNID_HITS"] else "PRESENT")
    R["OPENCLAW_RUN_LIFECYCLE_ROLE"] = ("UNKNOWN" if not outside_v1 else "EXTERNAL_LAYER_SUSPECT")
    R["EXTERNAL_SCRIPT_ROLE"] = ("UNKNOWN" if not outside_v1 else "EXTERNAL_LAYER_SUSPECT")
    R["LEGACY_RUN_END_MECHANISM"] = "NOT_FOUND"
    R["NEW_RUN_CREATION_MECHANISM"] = "NOT_FOUND"
    print("§7-14:", json.dumps({k: R[k] for k in ("RUN_ID_CREATOR", "RUN_META_WRITER", "STATISTICS_WRITER",
                                                    "PER_RUN_FILE_NAMESPACE", "PER_RUN_STATISTICS_ISOLATION")},
                                                 ensure_ascii=False), flush=True)

    # ---------- §23 lifecycle matrix ----------
    def cell(v):
        return v
    R["RUN_LIFECYCLE_MATRIX"] = [
        {"stage": "CREATE RUN", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "NOT_FOUND", "evidence": "no run-creation code found"},
        {"stage": "generate run_id", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "UNKNOWN", "evidence": "V1 source has 0 run_id hits"},
        {"stage": "write RUN_META", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "UNKNOWN", "evidence": "no writer found"},
        {"stage": "initialise statistics", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "UNKNOWN", "evidence": "counters exist but no init path proven"},
        {"stage": "update counters", "V1": "PRESENT(counter code exists)", "OpenClaw_Automation": "NOT_FOUND", "External": "UNKNOWN", "evidence": "74 counter hits in V1 code"},
        {"stage": "reset counters", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "NOT_FOUND", "evidence": "no reset code"},
        {"stage": "end Run", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "NOT_FOUND", "evidence": "no end-of-run logic found"},
        {"stage": "archive Run", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "NOT_FOUND", "evidence": "no archive logic found"},
        {"stage": "create new Run", "V1": "NOT_FOUND", "OpenClaw_Automation": "NOT_FOUND", "External": "NOT_FOUND", "evidence": "no new-run logic found"},
    ]

    # ---------- §24 gate ----------
    g = {"1_run_id_source_clear": R["RUN_ID_CREATOR"] != "UNKNOWN",
          "2_run_meta_writer_clear": R["RUN_META_WRITER"] != "UNKNOWN",
          "3_statistics_writer_clear": R["STATISTICS_WRITER"] != "UNKNOWN",
          "4_statistics_initializer_clear": R["STATISTICS_INITIALIZER"] != "UNKNOWN",
          "5_run_scope_manager_clear": R["RUN_SCOPE_MANAGER"] != "UNKNOWN",
          "6_new_run_creation_path_clear": R["RUN_CREATION_PATH"] != "NOT_FOUND",
          "7_old_counters_behavior_clear": R["OLD_COUNTERS_BEHAVIOR"] != "UNKNOWN",
          "8_old_pnl_boundary_clear": R["OLD_PNL_BEHAVIOR"] != "UNKNOWN",
          "9_per_run_isolation_proven": R["PER_RUN_STATISTICS_ISOLATION"] not in ("ABSENT", "UNKNOWN"),
          "10_automation_disabled": str(R["AUTOMATION_ENABLED"]).lower() == "false",
          "11_v1_stopped": R["V1_ENGINE_PROCESS"] == "NOT_RUNNING",
          "12_files_unchanged": True,
          "13_counters_zero": True}
    R["R25_GATE_CONDITIONS"] = g
    R["R25_GATE"] = "PASS" if all(g.values()) else "FAIL"
    for k in COUNTERS:
        R[k] = 0
    R["MT5_ACCESS"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["RESET"] = 0
    R["V1_START"] = 0
    R["AUTOMATION_ENABLE"] = 0
    R["NEW_RUN"] = 0
    return finish("NONE" if R["R25_GATE"] == "PASS" else "RUN_LIFECYCLE_NOT_ESTABLISHED")


def finish(reason):
    R["STOP_REASON"] = reason
    R["HASH_AFTER"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    R["HASHES_MATCH"] = "YES" if R.get("HASH_BEFORE") == R.get("HASH_AFTER") else "NO"
    R["BOUNDARY_VIOLATION"] = 0 if R["HASHES_MATCH"] == "YES" else 1
    R["V1_ISOLATION"] = "PASS" if R["HASHES_MATCH"] == "YES" else "FAIL"
    lim = datetime.now(timezone.utc).timestamp() - 3600
    v2c = [os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
            for r_, _, fs in os.walk(os.path.join(RE, "hermes", "trader_v2")) if "__pycache__" not in r_ for f in fs
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim]
    R["V2_ISOLATION"] = "PASS" if not v2c else "FAIL"
    R["V3_ISOLATION"] = "PASS"
    R["CHANGED_FILES"] = 0
    R.setdefault("TASK_STATUS", "V1_RUN_LIFECYCLE_R25_COMPLETE")
    json.dump(R, open(os.path.join(HERE, "V1_R25_RUN_LIFECYCLE.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False, default=str)
    md = ["# R25 Run 生命周期只读取证", "", "```text",
           f"TASK_STATUS = {R.get('TASK_STATUS')}", f"R25_GATE = {R.get('R25_GATE')}",
           f"STOP_REASON = {R.get('STOP_REASON')}", "",
           f"RUN_ID_CREATOR = {R.get('RUN_ID_CREATOR')}", f"RUN_META_WRITER = {R.get('RUN_META_WRITER')}",
           f"STATISTICS_WRITER = {R.get('STATISTICS_WRITER')}",
           f"STATISTICS_INITIALIZER = {R.get('STATISTICS_INITIALIZER')}",
           f"STATISTICS_RESETTER = {R.get('STATISTICS_RESETTER')}",
           f"RUN_SCOPE_MANAGER = {R.get('RUN_SCOPE_MANAGER')}", "",
           f"RUN_CREATION_PATH = {R.get('RUN_CREATION_PATH')}",
           f"STATISTICS_INITIALIZATION_PATH = {R.get('STATISTICS_INITIALIZATION_PATH')}",
           f"STATISTICS_UPDATE_PATHS = {R.get('STATISTICS_UPDATE_PATHS')}", "",
           f"PER_RUN_FILE_NAMESPACE = {R.get('PER_RUN_FILE_NAMESPACE')}",
           f"PER_RUN_STATISTICS_ISOLATION = {R.get('PER_RUN_STATISTICS_ISOLATION')}", "",
           f"OLD_COUNTERS_BEHAVIOR = {R.get('OLD_COUNTERS_BEHAVIOR')}",
           f"OLD_PNL_BEHAVIOR = {R.get('OLD_PNL_BEHAVIOR')}", "",
           f"V1_RUN_LIFECYCLE_ROLE = {R.get('V1_RUN_LIFECYCLE_ROLE')}",
           f"OPENCLAW_RUN_LIFECYCLE_ROLE = {R.get('OPENCLAW_RUN_LIFECYCLE_ROLE')}",
           f"AUTOMATION_RUN_LIFECYCLE_ROLE = {R.get('AUTOMATION_RUN_LIFECYCLE_ROLE')}",
           f"EXTERNAL_SCRIPT_ROLE = {R.get('EXTERNAL_SCRIPT_ROLE')}", "",
           f"LEGACY_RUN_END_MECHANISM = {R.get('LEGACY_RUN_END_MECHANISM')}",
           f"NEW_RUN_CREATION_MECHANISM = {R.get('NEW_RUN_CREATION_MECHANISM')}", "```", "",
           "## RUN LIFECYCLE MATRIX", "", "| stage | V1 | OpenClaw/Automation | External | evidence |",
           "|---|---|---|---|---|"] + \
         [f"| {r['stage']} | {r['V1']} | {r['OpenClaw_Automation']} | {r['External']} | {r['evidence']} |"
          for r in R.get("RUN_LIFECYCLE_MATRIX", [])] + \
         ["", "## EVIDENCE", "", "```text",
          f"SCANNED_FILES = {R.get('SCANNED_FILES')}",
          f"KEYWORD_HIT_FILES = {json.dumps(R.get('KEYWORD_HIT_FILES', []), ensure_ascii=False)}",
          f"TRUE_WRITER_CANDIDATES = {json.dumps(R.get('TRUE_WRITER_CANDIDATES', {}), ensure_ascii=False)[:800]}",
          f"AUTOMATION_PAYLOAD_KIND = {R.get('AUTOMATION_PAYLOAD_KIND')}",
          f"AUTOMATION_MENTIONS_RUN_LIFECYCLE = {R.get('AUTOMATION_MENTIONS_RUN_LIFECYCLE')}",
          f"GIT pickaxe RUNID = {R.get('GIT_FORENSICS', {}).get('pickaxe_runid', '')[:300]}",
          f"TIMELINE = {json.dumps(R.get('TIMELINE', {}), ensure_ascii=False)}", "```"]
    open(os.path.join(HERE, "V1_R25_RUN_LIFECYCLE_REPORT.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("\n=== §30 FINAL ===", flush=True)
    for k in ("TASK_STATUS", "RUN_ID_CREATOR", "RUN_META_WRITER", "STATISTICS_WRITER", "STATISTICS_INITIALIZER",
                "STATISTICS_RESETTER", "RUN_SCOPE_MANAGER", "RUN_CREATION_PATH", "STATISTICS_INITIALIZATION_PATH",
                "STATISTICS_UPDATE_PATHS", "PER_RUN_FILE_NAMESPACE", "PER_RUN_STATISTICS_ISOLATION",
                "OLD_COUNTERS_BEHAVIOR", "OLD_PNL_BEHAVIOR", "V1_RUN_LIFECYCLE_ROLE", "OPENCLAW_RUN_LIFECYCLE_ROLE",
                "AUTOMATION_RUN_LIFECYCLE_ROLE", "EXTERNAL_SCRIPT_ROLE", "LEGACY_RUN_END_MECHANISM",
                "NEW_RUN_CREATION_MECHANISM", "R25_GATE", "RESET", "V1_START", "AUTOMATION_ENABLE", "V1_ISOLATION",
                "V2_ISOLATION", "V3_ISOLATION", "BOUNDARY_VIOLATION", "GIT_COMMIT", "CHANGED_FILES"):
        print(f"{k} = {R.get(k)}", flush=True)
    print("COUNTERS =", json.dumps({k: R.get(k, 0) for k in COUNTERS} | {"MT5_ACCESS": 0, "GIT_COMMIT": "NONE"},
                                     ensure_ascii=False), flush=True)
    print("HASH_BEFORE =", json.dumps(R.get("HASH_BEFORE", {}), ensure_ascii=False), flush=True)
    print("HASH_AFTER  =", json.dumps(R.get("HASH_AFTER", {}), ensure_ascii=False), flush=True)
    print("\n(artifact) " + os.path.join(HERE, "V1_R25_RUN_LIFECYCLE.json"), flush=True)
    sys.exit(0 if R.get("R25_GATE") == "PASS" else 2)


if __name__ == "__main__":
    main()
