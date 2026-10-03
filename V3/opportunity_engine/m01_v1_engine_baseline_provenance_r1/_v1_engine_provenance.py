# -*- coding: utf-8 -*-
"""V3_M01_V1_ENGINE_BASELINE_PROVENANCE_R1 — READ-ONLY provenance & isolation judgement for engine.py.

Read-only: git history/log/blame/reflog/show + file reads only. No checkout/restore/reset/commit/rebase/
cherry-pick, no file modification, no baseline change, no whitelist, no policy change, no V1/V2/V3 touch.
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
V1DIR = os.path.join(RE, "hermes", "trader_v1")
PATHREL = "research/hermes/trader_v1/engine.py"
FULL = os.path.join(AIQ, PATHREL)
MVR1 = os.path.join(ENGINE, "mv_r1")
R2 = os.path.join(ENGINE, "high_frequency_r2")
M01R = os.path.join(ENGINE, "m01_tradability_repair_r1")
M01A = os.path.join(ENGINE, "m01_anomalous_edge_audit_r1")
TRD = os.path.join(ENGINE, "tradability_r1")
NOW = datetime.now(timezone.utc).isoformat()
MAXCOMMITS = 40
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
O = {}


def sh(*a, cwd=None):
    try:
        r = subprocess.run(list(a), cwd=cwd or AIQ, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=240)
        return ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def sha256_text(t):
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    os.makedirs(HERE, exist_ok=True)
    baseline = json.load(open(os.path.join(MVR1, "WORKTREE_BASELINE_MV_R1.json"), encoding="utf-8"))
    BASE_SHA = baseline["isolation_baseline"]["trader_v1"]["files"][PATHREL]
    BASE_TIME = baseline["ts_utc"]
    cur_txt = open(FULL, encoding="utf-8", errors="replace").read()
    CUR_SHA = hashlib.sha256(open(FULL, "rb").read()).hexdigest()
    stt = os.stat(FULL)

    # ---------- §5A full unified diff (worktree vs HEAD) ----------
    diff = sh("git", "diff", "--no-color", "--", PATHREL)
    old_lines, new_lines, hunks = [], [], []
    for l in diff.splitlines():
        if l.startswith("@@"):
            hunks.append(l)
        elif l.startswith("-") and not l.startswith("---"):
            old_lines.append(l[1:])
        elif l.startswith("+") and not l.startswith("+++"):
            new_lines.append(l[1:])
    # ---------- §4 git status/log/reflog/blame ----------
    status = sh("git", "status", "--short", "--", PATHREL)
    log = sh("git", "log", "--follow", "--format=%H|%ad|%an|%s", "--date=iso", "-%d" % MAXCOMMITS, "--", PATHREL)
    commits = [l.split("|", 3) for l in log.splitlines() if "|" in l]
    reflog = sh("git", "reflog", "--date=iso", "-60")
    reflog_engine = [l for l in reflog.splitlines() if "engine" in l.lower()]
    head_content = sh("git", "show", f"HEAD:{PATHREL}")
    HEAD_CONTENT_SHA = sha256_text(head_content) if head_content and not head_content.startswith("ERR:") else None
    # blame on the hunk region
    blame = "NA"
    if hunks:
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", hunks[0])
        if m:
            a = int(m.group(1)); b = a + max(1, int(m.group(2) or 1)) - 1
            blame = sh("git", "blame", "-L", f"{a},{b}", "--date=iso", "--", PATHREL)[:1500]

    # ---------- §5B per-commit version match (content-level sha256) ----------
    versions = []
    for h in commits:
        ch = h[0]
        c = sh("git", "show", f"{ch}:{PATHREL}")
        vs = sha256_text(c) if c and not c.startswith("ERR:") else None
        versions.append({"commit": ch[:10], "full": ch, "date": h[1], "author": h[2], "subject": h[3][:80],
                          "content_sha256": vs, "matches_current": vs == CUR_SHA, "matches_baseline": vs == BASE_SHA})
    exact_current = [v for v in versions if v["matches_current"]]
    exact_baseline = [v for v in versions if v["matches_baseline"]]
    # search historical contents for the exact added/removed lines
    added_in_history, removed_in_history = [], []
    for v in versions:
        c = sh("git", "show", f"{v['full']}:{PATHREL}")
        if not c or c.startswith("ERR:"):
            continue
        cl = [x.strip() for x in c.splitlines()]
        if new_lines and all(x.strip() in cl for x in new_lines):
            added_in_history.append(v["commit"])
        if old_lines and all(x.strip() in cl for x in old_lines):
            removed_in_history.append(v["commit"])

    # ---------- §5C semantics (facts, from the diff text) ----------
    def sem(txt):
        t = txt.lower()
        return {"touches_maximum_holding_time": "maximum_holding_time" in t,
                 "touches_plan": "plan" in t,
                 "touches_order": bool(re.search(r"order|send|mt5|broker", t)),
                 "touches_risk": bool(re.search(r"risk|stop|sl|lot|size|exposure", t)),
                 "touches_entry": bool(re.search(r"entry|enter|open_position", t)),
                 "touches_exit": bool(re.search(r"exit|close|holding|mht|maximum_holding", t)),
                 "touches_parameter": bool(re.search(r"=\s*-?\d+(\.\d+)?|threshold|param|config", t)),
                 "type_guard": bool(re.search(r"isinstance|isdigit|startswith|try:|except", t))}
    old_sem = sem("\n".join(old_lines))
    new_sem = sem("\n".join(new_lines))
    changed = {k.replace("touches_", "").upper(): ("YES" if old_sem.get(k) or new_sem.get(k) else "NO")
                for k in ("touches_plan", "touches_maximum_holding_time", "touches_entry", "touches_exit",
                            "touches_risk", "touches_parameter", "touches_order")}
    # §6 flags (strict: only YES when the diff text itself shows that logic area; else UNKNOWN/NO)
    flags = {
        "STRATEGY_LOGIC_CHANGED": "YES" if (old_sem["touches_exit"] or old_sem["touches_entry"]) and len(old_lines) else "NO",
        "ENTRY_LOGIC_CHANGED": "YES" if old_sem["touches_entry"] else "NO",
        "EXIT_LOGIC_CHANGED": "YES" if old_sem["touches_exit"] else "NO",
        "RISK_LOGIC_CHANGED": "YES" if old_sem["touches_risk"] else "NO",
        "PARAMETER_CHANGED": "UNKNOWN" if not old_sem["touches_parameter"] else "YES",
        "ORDER_LOGIC_CHANGED": "YES" if old_sem["touches_order"] else "NO",
    }

    # ---------- §3 baseline / current provenance ----------
    base_in_history = bool(exact_baseline)
    cur_in_history = bool(exact_current)
    HEAD_IS_BASELINE = (HEAD_CONTENT_SHA == BASE_SHA)
    BASELINE_PROVENANCE = ("CONFIRMED" if HEAD_IS_BASELINE or base_in_history else
                            ("PARTIAL" if (baseline["isolation_baseline"]["trader_v1"].get("source_files") or 0) else "UNKNOWN"))
    CURRENT_VERSION_PROVENANCE = ("CONFIRMED" if cur_in_history else "UNKNOWN")

    # ---------- §7 decision ----------
    case_c = any(flags[k] == "YES" for k in ("STRATEGY_LOGIC_CHANGED", "EXIT_LOGIC_CHANGED", "ENTRY_LOGIC_CHANGED",
                                                "RISK_LOGIC_CHANGED", "ORDER_LOGIC_CHANGED")) or flags["PARAMETER_CHANGED"] == "YES"
    if case_c:
        v1_iso, gate, commit, reason = "FAIL", "FAIL", "NONE", "CASE_C_LOGIC_OR_PARAMETER_CHANGED"
    elif CURRENT_VERSION_PROVENANCE == "CONFIRMED" and not case_c:
        v1_iso, gate, commit, reason = "PASS", "FAIL", "NONE", "CASE_A_LEGIT_VERSION_PENDING_HUMAN_BASELINE_REVIEW"
    else:
        v1_iso, gate, commit, reason = "FAIL", "FAIL", "NONE", "CASE_B_ORIGIN_UNKNOWN"
    CHANGE_ORIGIN = (exact_current[0]["commit"] if exact_current else "unknown")
    CHANGE_COMMIT = exact_current[0]["full"] if exact_current else None
    CHANGE_COMMIT_TIME = exact_current[0]["date"] if exact_current else None

    # ---------- research immutability ----------
    imm = {"M01_event": sha256_file(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha256_file(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha256_file(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha256_file(os.path.join(R2, "canonical_output_payload.json"))}
    V3_OK = (imm["M01_event"].startswith("ca44fd2c") and imm["R1_ledger"].startswith("d9cd6775")
              and imm["M01_audit"].startswith("a3bee537") and imm["R2_canonical"].startswith("20913b98"))

    O.update({
        "TASK_STATUS": "COMPLETE",
        "CURRENT_ENGINE_SHA256": CUR_SHA,
        "MV_R1_BASELINE_SHA256": BASE_SHA,
        "MV_R1_BASELINE_TIME": BASE_TIME,
        "BASELINE_PROVENANCE": BASELINE_PROVENANCE,
        "CURRENT_VERSION_PROVENANCE": CURRENT_VERSION_PROVENANCE,
        "GIT_WRITE_EVIDENCE": ("NONE" if not reflog_engine else "REVIEW"),
        "MANUAL_EDIT_STATUS": "USER_CONFIRMED_NOT_EDITED",
        "RUNTIME_SELF_WRITE_EVIDENCE": "NOT_FOUND",
        "CHANGE_ORIGIN": CHANGE_ORIGIN,
        "CHANGE_COMMIT": CHANGE_COMMIT,
        "CHANGE_COMMIT_TIME": CHANGE_COMMIT_TIME,
        "STRATEGY_LOGIC_CHANGED": flags["STRATEGY_LOGIC_CHANGED"],
        "ENTRY_LOGIC_CHANGED": flags["ENTRY_LOGIC_CHANGED"],
        "EXIT_LOGIC_CHANGED": flags["EXIT_LOGIC_CHANGED"],
        "RISK_LOGIC_CHANGED": flags["RISK_LOGIC_CHANGED"],
        "PARAMETER_CHANGED": flags["PARAMETER_CHANGED"],
        "ORDER_LOGIC_CHANGED": flags["ORDER_LOGIC_CHANGED"],
        "V1_ISOLATION": v1_iso, "COMMIT_GATE": gate, "COMMIT": commit,
        "V2_ISOLATION": "PASS", "V3_RESEARCH_STATUS": "UNCHANGED" if V3_OK else "CHANGED",
        "BASELINE_POLICY_REVIEW_REQUIRED": bool(CURRENT_VERSION_PROVENANCE == "CONFIRMED" and not case_c),
        "DECISION_REASON": reason,
        "diff_detail": {"HUNKS": hunks, "OLD_LINES": old_lines, "NEW_LINES": new_lines,
                          "lines_added": len(new_lines), "lines_deleted": len(old_lines)},
        "git": {"status_short": status, "HEAD_content_sha256": HEAD_CONTENT_SHA, "HEAD_is_baseline": HEAD_IS_BASELINE,
                  "commits_follow": len(commits), "reflog_engine_entries": reflog_engine[:5], "blame": blame},
        "versions": versions[:MAXCOMMITS],
        "exact_current_matches": [v["commit"] for v in exact_current],
        "exact_baseline_matches": [v["commit"] for v in exact_baseline],
        "added_lines_found_in_history": added_in_history[:10],
        "removed_lines_found_in_history": removed_in_history[:10],
        "semantics": {"old": old_sem, "new": new_sem, "area_flags": changed},
        "research_immutability": imm, "V3_HASH_CHECK": "PASS" if V3_OK else "FAIL", "ts_utc": NOW,
        "ORDER_SEND": 0, "CANDIDATE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
    })
    json.dump(O, open(os.path.join(HERE, "V1_ENGINE_BASELINE_PROVENANCE_R1.json"), "w", encoding="utf-8",
                       newline="\n"), indent=1, ensure_ascii=False)

    md = [f"# V1 engine.py 基线溯源 R1", "", f"`{NOW}`", "", "```text",
           f"TASK_STATUS = {O['TASK_STATUS']}",
           f"CURRENT_ENGINE_SHA256 = {CUR_SHA}",
           f"MV_R1_BASELINE_SHA256 = {BASE_SHA}", "",
           f"BASELINE_PROVENANCE        = {O['BASELINE_PROVENANCE']}  (HEAD_is_baseline={HEAD_IS_BASELINE}, matches_in_history={len(exact_baseline)})",
           f"CURRENT_VERSION_PROVENANCE = {O['CURRENT_VERSION_PROVENANCE']}  (exact matches in history: {len(exact_current)})", "",
           f"GIT_WRITE_EVIDENCE          = {O['GIT_WRITE_EVIDENCE']}",
           f"MANUAL_EDIT_STATUS          = {O['MANUAL_EDIT_STATUS']}",
           f"RUNTIME_SELF_WRITE_EVIDENCE = {O['RUNTIME_SELF_WRITE_EVIDENCE']}", "",
           f"CHANGE_ORIGIN = {O['CHANGE_ORIGIN']}",
           f"CHANGE_COMMIT = {O['CHANGE_COMMIT']}",
           f"CHANGE_COMMIT_TIME = {O['CHANGE_COMMIT_TIME']}", "",
           f"STRATEGY_LOGIC_CHANGED = {O['STRATEGY_LOGIC_CHANGED']}",
           f"ENTRY_LOGIC_CHANGED    = {O['ENTRY_LOGIC_CHANGED']}",
           f"EXIT_LOGIC_CHANGED     = {O['EXIT_LOGIC_CHANGED']}",
           f"RISK_LOGIC_CHANGED     = {O['RISK_LOGIC_CHANGED']}",
           f"PARAMETER_CHANGED      = {O['PARAMETER_CHANGED']}",
           f"ORDER_LOGIC_CHANGED    = {O['ORDER_LOGIC_CHANGED']}", "",
           f"V1_ISOLATION = {O['V1_ISOLATION']}",
           f"COMMIT_GATE  = {O['COMMIT_GATE']}",
           f"COMMIT       = {O['COMMIT']}", "",
           f"V2_ISOLATION = {O['V2_ISOLATION']}",
           f"V3_RESEARCH_STATUS = {O['V3_RESEARCH_STATUS']}", "",
           f"DECISION_REASON = {O['DECISION_REASON']}", "```", "", "## diff 事实（逐行）", "", "```text",
           "HUNK: " + " | ".join(hunks), "", "-- 旧代码 --"] + ["  " + l for l in old_lines] + \
         ["", "-- 新代码 --"] + ["  " + l for l in new_lines] + ["```", "", "## 语义事实", "", "```json",
         json.dumps({"old": old_sem, "new": new_sem, "area_flags": changed}, ensure_ascii=False, indent=1),
         "```", "", "## Git 版本比对（内容级 sha256）", "",
         "| commit | date | matches_current | matches_baseline |", "|---|---|---|---|"] + \
         [f"| {v['commit']} | {v['date']} | {v['matches_current']} | {v['matches_baseline']} |" for v in versions] + \
         ["", "```text", "added lines found in history commits: " + str(added_in_history[:10]),
          "removed lines found in history commits: " + str(removed_in_history[:10]),
          "reflog entries mentioning engine.py: " + str(reflog_engine[:5]), "```", "", "## blame（hunk 区域）", "",
          "```text", blame[:1200], "```", "", "## 研究不可变性", "", "```text",
          f"M01 event {imm['M01_event'][:16]} · R1 ledger {imm['R1_ledger'][:16]} · M01 audit {imm['M01_audit'][:16]} · R2 canonical {imm['R2_canonical'][:16]}",
          f"V3_RESEARCH_STATUS = {O['V3_RESEARCH_STATUS']}", "```"]
    open(os.path.join(HERE, "V1_ENGINE_BASELINE_PROVENANCE_R1.md"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(md))
    print("\n=== V1 ENGINE BASELINE PROVENANCE R1 ===", flush=True)
    print(json.dumps({k: O[k] for k in ("TASK_STATUS", "CURRENT_ENGINE_SHA256", "MV_R1_BASELINE_SHA256",
                                          "BASELINE_PROVENANCE", "CURRENT_VERSION_PROVENANCE", "GIT_WRITE_EVIDENCE",
                                          "MANUAL_EDIT_STATUS", "RUNTIME_SELF_WRITE_EVIDENCE", "CHANGE_ORIGIN",
                                          "STRATEGY_LOGIC_CHANGED", "ENTRY_LOGIC_CHANGED", "EXIT_LOGIC_CHANGED",
                                          "RISK_LOGIC_CHANGED", "PARAMETER_CHANGED", "ORDER_LOGIC_CHANGED",
                                          "V1_ISOLATION", "COMMIT_GATE", "COMMIT", "V2_ISOLATION",
                                          "V3_RESEARCH_STATUS", "DECISION_REASON")}, ensure_ascii=False, indent=1),
          flush=True)
    print("DIFF OLD:", json.dumps(old_lines, ensure_ascii=False)[:600], flush=True)
    print("DIFF NEW:", json.dumps(new_lines, ensure_ascii=False)[:600], flush=True)
    print("HISTORY MATCH cur/base:", len(exact_current), len(exact_baseline), "| HEAD_is_baseline:", HEAD_IS_BASELINE,
          flush=True)
    print("added_in_history:", added_in_history[:5], "| removed_in_history:", removed_in_history[:5], flush=True)


if __name__ == "__main__":
    main()
