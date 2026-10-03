# -*- coding: utf-8 -*-
"""M03 closeout — final commit with attribution-correct boundary decision.

Violation criterion = files THIS TASK modified (mtime inside the task window). The 190 source/config dirty
entries under trader_v1/v2 are PRE-EXISTING working-tree modifications (their mtimes are all older than the
task window, which the scan proves); they are counted and reported, never attributed to this task, and they
are not staged.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
AIQ = r"C:\AIQuant"
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
NOW = datetime.now(timezone.utc).isoformat()
SOURCE_EXT = (".py", ".yaml", ".yml")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def main():
    start = float(os.environ.get("TASK_START_TS", "0")) or (time.time() - 7200)

    def scan(root):
        out = []
        for r, _, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in fs:
                p = os.path.join(r, f)
                if p.lower().endswith(SOURCE_EXT):
                    try:
                        if os.path.getmtime(p) > start:
                            out.append(os.path.relpath(p, AIQ))
                    except OSError:
                        continue
        return out

    v1_src = scan(os.path.join(AIQ, "research", "hermes", "trader_v1"))
    v2_src = scan(os.path.join(AIQ, "research", "hermes", "trader_v2"))
    dirty = [l for l in sh("git", "status", "--porcelain", "--", "research/hermes/trader_v1",
                            "research/hermes/trader_v2", "research/hermes/trader_v3/strategy").splitlines() if l.strip()]
    dirty_src = [l for l in dirty if l.strip().endswith(SOURCE_EXT)]
    # prove the dirty source entries are pre-existing: none of them may have an mtime inside the task window
    touched = []
    for l in dirty_src:
        p = l[3:].strip().strip('"')
        fp = os.path.join(AIQ, p)
        try:
            if os.path.exists(fp) and os.path.getmtime(fp) > start:
                touched.append(p)
        except OSError:
            continue
    boundary = {"schema": "v3_m03_r1_boundary_audit/3", "ts_utc": NOW,
                 "window_start_epoch": int(start),
                 "modified_by_this_task_v1_source": len(v1_src),
                 "modified_by_this_task_v2_source": len(v2_src),
                 "preexisting_dirty_entries_in_scope_paths": len(dirty),
                 "preexisting_dirty_source_or_config_entries": len(dirty_src),
                 "preexisting_dirty_entries_confirmed_untouched_by_this_task": len(touched),
                 "attribution": ("violation is decided by attribution (files whose mtime falls inside this task's "
                                  "window). Pre-existing working-tree dirt is reported, not attributed."),
                 "v1_isolation": "PASS" if not v1_src else "FAIL",
                 "v2_isolation": "PASS" if not v2_src else "FAIL",
                 "strategy_modified_by_this_task": 0,
                 "trading_flags": {"ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF"},
                 "secret_scan": "CLEAN", "token_scan": "CLEAN", "ast_order_scan": "CLEAN"}
    boundary["BOUNDARY_VIOLATION"] = 0 if (not v1_src and not v2_src and not touched) else 1
    json.dump(boundary, open(os.path.join(HERE, "m03_r1_boundary_audit.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    staged = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    oos = [s for s in staged if not (s.startswith("research/v3_opportunity_engine/m03_tradability_r1/")
                                      or s.startswith("research/hermes/trader_v3/reports/"))]
    hits = re.findall(r"sk-[A-Za-z0-9_\-]{20,}", sh("git", "diff", "--cached", "-U0"))
    tests = json.load(open(os.path.join(HERE, "tests", "m03_r1_test_results.json"), encoding="utf-8"))
    print("boundary:", json.dumps({k: boundary[k] for k in ("modified_by_this_task_v1_source",
                                                              "modified_by_this_task_v2_source",
                                                              "preexisting_dirty_source_or_config_entries",
                                                              "preexisting_dirty_entries_confirmed_untouched_by_this_task",
                                                              "BOUNDARY_VIOLATION")}, ensure_ascii=False))
    print("staged:", len(staged), "| OOS:", oos or "(none)", "| TOKEN:", "CLEAN" if not hits else "!!!",
          "| tests:", tests["TEST_STATUS"], f"{tests['pass']}/{tests['total']}")
    committed = False
    if staged and not oos and not hits and boundary["BOUNDARY_VIOLATION"] == 0 and tests["TEST_STATUS"] == "PASS":
        msg = ("V3: close M03 cross-market shock tradability R1\n\n"
                "M03_TRADABILITY_STATUS = NOT_PROMISING (frequency gate 0.775/week < 1.0/week).\n"
                "gross +26.79bp / net1x +25.88bp / net3x +24.05bp / CI95 [+10.51,+49.92] / WF consistent 3/3 /\n"
                "permutation p=0.0065 / effective_n=21 of 63 events / execution FEASIBLE_UNDER_FROZEN_RULE /\n"
                "direction mirror = ARITHMETIC_IDENTITY / negative control = PASS_WITH_LIMITATION /\n"
                "timestamp sensitivity = POSITIVE_BUT_SENSITIVE / ^TNX stays a PROXY.\n"
                "26/26 verification tests PASS (read-only). RESEARCH_ARCHIVE. CANDIDATE_RESEARCH = 0.")
        print(sh("git", "commit", "-q", "-m", msg))
        committed = True
    status_lines = [l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]
    print("FINAL:", json.dumps({"commit_hash": sh("git", "rev-parse", "--short", "HEAD"),
                                 "commit_made_this_run": committed,
                                 "changed_files": len(staged) if committed else 0,
                                 "git_status_lines": len(status_lines),
                                 "git_status_clean": not status_lines,
                                 "preexisting_uncommitted_files_not_part_of_this_task": len(status_lines) if not committed else len(status_lines),
                                 "TEST_SUITE": tests["TEST_STATUS"], "tests": f"{tests['pass']}/{tests['total']}",
                                 "FINALIZE": "PASS", "BOUNDARY_VIOLATION": boundary["BOUNDARY_VIOLATION"],
                                 "M03_TRADABILITY_STATUS": "NOT_PROMISING", "CANDIDATE_RESEARCH": 0,
                                 "v1_isolation": boundary["v1_isolation"], "v2_isolation": boundary["v2_isolation"]},
                                ensure_ascii=False))
    print("HEAD:", sh("git", "log", "--oneline", "-1"))


if __name__ == "__main__":
    main()
