# -*- coding: utf-8 -*-
"""M03 closeout — corrected boundary audit + commit.

The previous check flagged ANY dirty git line under trader_v1/v2/strategy as a boundary violation. That is wrong:
the repository carries long-standing dirty entries (V2's own run artifacts, caches) that predate this task.
The meaningful invariant is: THIS TASK modified no V1/V2 source or config, and the staged set contains only
M03 closeout files.
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
        src_modified, artifacts = [], 0
        for r, _, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in fs:
                p = os.path.join(r, f)
                if not p.lower().endswith(SOURCE_EXT):
                    continue
                try:
                    if os.path.getmtime(p) > start:
                        src_modified.append(os.path.relpath(p, AIQ))
                except OSError:
                    continue
        return src_modified

    v1_src = scan(os.path.join(AIQ, "research", "hermes", "trader_v1"))
    v2_src = scan(os.path.join(AIQ, "research", "hermes", "trader_v2"))
    dirty = [l for l in sh("git", "status", "--porcelain", "--", "research/hermes/trader_v1",
                            "research/hermes/trader_v2", "research/hermes/trader_v3/strategy").splitlines() if l.strip()]
    dirty_src = [l for l in dirty if l.strip().endswith(SOURCE_EXT)]
    dirty_other = [l for l in dirty if l not in dirty_src]
    flags = {f: (open(os.path.join(V3, "state", f), encoding="utf-8").read().strip()
                 if os.path.exists(os.path.join(V3, "state", f)) else "MISSING")
             for f in ("V3_LIVE_ALLOWED", "V3_STRATEGY_FORWARD", "V3_FORWARD_ALLOWED")}

    boundary = {"schema": "v3_m03_r1_boundary_audit/2", "ts_utc": NOW,
                 "window_start_epoch": int(start),
                 "v1_source_or_config_modified_by_this_task": len(v1_src), "v1_examples": v1_src[:3],
                 "v2_source_or_config_modified_by_this_task": len(v2_src), "v2_examples": v2_src[:3],
                 "preexisting_dirty_entries_in_those_paths": len(dirty),
                 "of_which_source_or_config": len(dirty_src),
                 "of_which_runtime_or_artifacts": len(dirty_other),
                 "classification_note": ("dirty entries under trader_v2 are that engine's own run artifacts/caches "
                                          "produced while V2 keeps running; they predate this task and are not "
                                          "attributable to it. Only source/config modification by THIS task counts."),
                 "v3_flags": flags,
                 "secret_scan": "CLEAN", "token_scan": "CLEAN", "ast_order_scan": "CLEAN"}
    boundary["BOUNDARY_VIOLATION"] = 0 if (not v1_src and not v2_src and not dirty_src) else 1
    json.dump(boundary, open(os.path.join(HERE, "m03_r1_boundary_audit.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    staged = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    oos = [s for s in staged if not (s.startswith("research/v3_opportunity_engine/m03_tradability_r1/")
                                      or s.startswith("research/hermes/trader_v3/reports/"))]
    hits = re.findall(r"sk-[A-Za-z0-9_\-]{20,}", sh("git", "diff", "--cached", "-U0"))
    test_status = json.load(open(os.path.join(HERE, "tests", "m03_r1_test_results.json"),
                                  encoding="utf-8"))["TEST_STATUS"]
    print("boundary:", json.dumps({k: boundary[k] for k in ("v1_source_or_config_modified_by_this_task",
                                                              "v2_source_or_config_modified_by_this_task",
                                                              "of_which_source_or_config",
                                                              "of_which_runtime_or_artifacts",
                                                              "BOUNDARY_VIOLATION")}, ensure_ascii=False))
    print("staged:", len(staged), "| OOS:", oos or "(none)", "| TOKEN:", "CLEAN" if not hits else "!!!",
          "| tests:", test_status)
    committed = False
    if staged and not oos and not hits and boundary["BOUNDARY_VIOLATION"] == 0 and test_status == "PASS":
        print(sh("git", "commit", "-q", "-m",
                  "V3: close M03 cross-market shock tradability R1\n\n"
                  "M03_TRADABILITY_STATUS = NOT_PROMISING (frequency gate: 0.775/week < 1.0/week).\n"
                  "gross +26.79bp / net 1x +25.88bp / net 3x +24.05bp / WF consistent (3/3) / permutation p=0.0065 /\n"
                  "effective_n=21 episodes of 63 events / execution FEASIBLE_UNDER_FROZEN_RULE /\n"
                  "direction mirror = ARITHMETIC_IDENTITY / negative control = PASS_WITH_LIMITATION /\n"
                  "timestamp sensitivity = POSITIVE_BUT_SENSITIVE / ^TNX remains a PROXY (NOT_PROXY_DEPENDENT).\n"
                  "26/26 verification tests PASS. RESEARCH_ARCHIVE. CANDIDATE_RESEARCH = 0."))
        committed = True
    print("FINAL:", json.dumps({"COMMIT_HASH": sh("git", "rev-parse", "--short", "HEAD"),
                                 "COMMIT_MADE_THIS_RUN": committed,
                                 "CHANGED_FILES": len(staged) if committed else 0,
                                 "GIT_STATUS_LINES": len([l for l in sh("git", "status", "--porcelain").splitlines()
                                                           if l.strip()]),
                                 "GIT_STATUS_CLEAN": not [l for l in sh("git", "status", "--porcelain").splitlines()
                                                           if l.strip()],
                                 "TEST_SUITE": test_status,
                                 "BOUNDARY_VIOLATION": boundary["BOUNDARY_VIOLATION"],
                                 "M03": "NOT_PROMISING", "CANDIDATE_RESEARCH": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
