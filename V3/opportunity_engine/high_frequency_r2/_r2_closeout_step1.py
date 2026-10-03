# -*- coding: utf-8 -*-
"""R2 FINAL CLOSEOUT — step 1: WORKTREE_BASELINE_MANIFEST + freeze/input re-verification.

Created BEFORE any code modification (task section 1). Historical dirty files are recorded in full and are
never cleaned, never staged. No research rule is touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

AIQ = r"C:\AIQuant"
HERE = os.path.join(AIQ, "research", "v3_opportunity_engine", "high_frequency_r2")
NOW = datetime.now(timezone.utc).isoformat()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}"


def main():
    # ---------- section 1: baseline manifest of the WHOLE worktree ----------
    porcelain = [l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]
    entries = []
    for line in porcelain:
        code, _, path = line[:2], line[2], line[3:].strip().strip('"')
        fp = os.path.join(AIQ, path)
        exists = os.path.exists(fp)
        entries.append({"git_status": code.strip() or code, "path": path.replace("\\", "/"),
                         "exists": exists,
                         "size": (os.path.getsize(fp) if exists and os.path.isfile(fp) else None),
                         "mtime": (datetime.fromtimestamp(os.path.getmtime(fp), timezone.utc).isoformat()
                                    if exists else None),
                         "sha256": (sha_file(fp) if exists and os.path.isfile(fp) else None)})
    # expand untracked directories so the manifest is file-level where possible
    expanded = []
    for e in entries:
        fp = os.path.join(AIQ, e["path"])
        if e["exists"] and os.path.isdir(fp):
            for r, _, fs in os.walk(fp):
                for f in fs:
                    p = os.path.join(r, f)
                    rel = os.path.relpath(p, AIQ).replace("\\", "/")
                    expanded.append({**e, "path": rel, "size": os.path.getsize(p),
                                      "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat(),
                                      "sha256": sha_file(p)})
        else:
            expanded.append(e)
    tracked_modified = [e for e in expanded if e["git_status"] and e["git_status"][0] in ("M", "A", "R")]
    tracked_deleted = [e for e in expanded if e["git_status"] and e["git_status"][0] == "D"]
    untracked = [e for e in expanded if e["git_status"] == "??" or e["git_status"].startswith("??")]
    in_r2 = [e for e in expanded if e["path"].startswith("research/v3_opportunity_engine/high_frequency_r2/")]
    out_r2 = [e for e in expanded if e not in in_r2]

    manifest = {"schema": "v3_r2_worktree_baseline_manifest/1", "ts_utc": NOW,
                 "head": sh("git", "rev-parse", "HEAD"), "head_short": sh("git", "rev-parse", "--short", "HEAD"),
                 "porcelain_lines": len(porcelain), "files_recorded": len(expanded),
                 "tracked_modified": len(tracked_modified), "tracked_deleted": len(tracked_deleted),
                 "untracked": len(untracked),
                 "historical_dirty_outside_r2": len(out_r2), "files_inside_r2_at_baseline": len(in_r2),
                 "policy": {"historical_dirty_cleaned": False, "historical_dirty_staged": False,
                             "r2_scope_only": "research/v3_opportunity_engine/high_frequency_r2/"},
                 "entries": expanded}
    json.dump(manifest, open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"), "w", encoding="utf-8",
                              newline="\n"), indent=1, ensure_ascii=False)
    print("BASELINE_MANIFEST:", json.dumps({k: manifest[k] for k in (
        "head_short", "porcelain_lines", "files_recorded", "tracked_modified", "tracked_deleted", "untracked",
        "historical_dirty_outside_r2", "files_inside_r2_at_baseline")}, ensure_ascii=False))

    # ---------- section 2: freeze + input verification ----------
    reg = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"),
                          encoding="utf-8"))
    stored = reg.pop("FREEZE_HASH")
    reg.pop("frozen_at_utc", None)
    recomputed = hashlib.sha256(json.dumps(reg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    EXPECTED_FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
    EXPECTED_INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
    old = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    chk = {"FREEZE_HASH_stored": stored, "FREEZE_HASH_recomputed": recomputed,
            "FREEZE_MATCH": stored == recomputed == EXPECTED_FREEZE,
            "INPUT_HASH_old_run": old.get("INPUT_HASH"), "INPUT_MATCH": old.get("INPUT_HASH") == EXPECTED_INPUT,
            "OLD_OUTPUT_HASH": old.get("OUTPUT_HASH"),
            "OLD_RESULT_STATUS": "INVALIDATED_FOR_FINAL_USE",
            "SUPERSEDED": {"INDEPENDENT_EVENTS": old.get("INDEPENDENT_EVENTS"),
                            "INDEPENDENT_EVENTS_PER_DAY": old.get("INDEPENDENT_EVENTS_PER_DAY"),
                            "INDEPENDENT_EVENTS_PER_WEEK": old.get("INDEPENDENT_EVENTS_PER_WEEK"),
                            "HIGH_FREQUENCY_COUNT": old.get("HIGH_FREQUENCY_COUNT"),
                            "CLUSTERS": "SUPERSEDED_BY_DEFECT_REPAIR",
                            "marker": "SUPERSEDED_BY_DEFECT_REPAIR"}}
    json.dump(chk, open(os.path.join(HERE, "r2_freeze_input_verification.json"), "w", encoding="utf-8",
                         newline="\n"), indent=1, ensure_ascii=False)
    print("FREEZE/INPUT CHECK:", json.dumps(chk, ensure_ascii=False)[:600])
    if not chk["FREEZE_MATCH"] or not chk["INPUT_MATCH"]:
        print("STOP: freeze or input hash mismatch")
        sys.exit(2)
    print("OK -> proceed to defect repair")


if __name__ == "__main__":
    main()
