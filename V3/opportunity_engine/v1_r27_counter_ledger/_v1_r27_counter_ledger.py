# -*- coding: utf-8 -*-
"""R27 - evidence completion: statistics.json counter diff + plan_ledger.jsonl diff for commit 43f9b2f.
READ-ONLY (git show/ls-tree only). Writes ONLY the two deliverables under
research/v3_opportunity_engine/v1_r27_counter_ledger/. ASCII hyphens only (no U+2212)."""
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
PARENT = C + "^"
P_STATS = "research/hermes/trader_v1/run_state/statistics.json"
P_LEDGER = "research/hermes/trader_v1/run_state/plan_ledger.jsonl"
P_META = "research/hermes/trader_v1/run_state/RUN_META.json"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
IDS = {"broker_ticket": "2377449557", "position_id": "POS-20260925T140419", "plan_id": "TP-20260925T140419"}
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
COUNTERS = ("ORDER_SEND", "POSITION_CLOSE", "POSITION_MODIFY", "ORDER_CANCEL", "V1_START", "V1_STOP", "V1_RESTART",
             "AUTOMATION_RUN", "AUTOMATION_ENABLE", "AUTOMATION_UPDATE", "AUTOMATION_DELETE", "LEDGER_WRITE",
             "STATE_WRITE", "SOURCE_WRITE", "CONFIG_WRITE", "HISTORY_MOVE", "HISTORY_DELETE", "HISTORY_RENAME")
R = {}


def sh(a, t=180):
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


def at(rev, path):
    return sh(["git", "show", rev + ":" + path], t=240)


def numerics(o, path="$", out=None):
    if out is None:
        out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            numerics(v, path + "." + str(k), out)
    elif isinstance(o, list):
        return out
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out[path] = o
    return out


def main():
    os.makedirs(HERE, exist_ok=True)
    R["task_status"] = "RUNNING"
    R["audit_now_utc"] = datetime.now(timezone.utc).isoformat()
    R["commit"] = C
    R["parent_commit"] = "ebce041797ec"

    # ---------- freeze ----------
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
    R["hash_before"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    ok = (str(R["AUTOMATION_ENABLED"]).lower() == "false" and R["V1_ENGINE_PROCESS"] == "NOT_RUNNING"
           and R["hash_before"]["ENGINE"] == BASE and R["hash_before"]["LEDGER"] == LEDGER_EXPECT
           and R["hash_before"]["STATISTICS"] == STATS_EXPECT and R["hash_before"]["RUN_META"] == META_EXPECT)
    print("freeze ok =", ok, flush=True)
    if not ok:
        R["gate"] = "FAIL"
        R["stop_reason"] = "FREEZE_FAILED"
        return finish()

    # ---------- part 1: statistics diff ----------
    par_txt = at(PARENT, P_STATS)
    cur_txt = at(C, P_STATS)
    par_ok = not (par_txt.startswith("ERR:") or "fatal" in par_txt[:40])
    cur_ok = not (cur_txt.startswith("ERR:") or "fatal" in cur_txt[:40])
    try:
        pj = json.loads(par_txt) if par_ok else {}
    except Exception:  # noqa: BLE001
        pj = {}
    try:
        cj = json.loads(cur_txt) if cur_ok else {}
    except Exception:  # noqa: BLE001
        cj = {}
    pn = numerics(pj) if isinstance(pj, (dict, list)) else {}
    cn = numerics(cj) if isinstance(cj, (dict, list)) else {}
    diff = []
    for k in sorted(set(pn) | set(cn)):
        o = pn.get(k, "ABSENT")
        n = cn.get(k, "ABSENT")
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
            ct = "NON_NUMERIC_CHANGED"
        diff.append({"path": k, "OLD": o, "NEW": n, "classification": ct})
    # non-numeric top-level changes
    nonnum = []
    if isinstance(pj, dict) and isinstance(cj, dict):
        for k in sorted(set(pj) | set(cj)):
            a, b = pj.get(k, "ABSENT"), cj.get(k, "ABSENT")
            if a != b and not isinstance(a, (int, float)) and not isinstance(b, (int, float)):
                nonnum.append({"path": "$." + str(k), "OLD": (a if not isinstance(a, (dict, list)) else "<obj>"),
                                 "NEW": (b if not isinstance(b, (dict, list)) else "<obj>"),
                                 "classification": "NON_NUMERIC_CHANGED"})
    counts = {}
    for d in diff:
        counts[d["classification"]] = counts.get(d["classification"], 0) + 1
    R["statistics"] = {
        "parent_present": par_ok, "commit_present": cur_ok,
        "numeric_paths_parent": len(pn), "numeric_paths_commit": len(cn),
        "counter_diff": diff, "counter_diff_counts": counts, "non_numeric_changes": nonnum,
        "old_run_id": (pj.get("run_id", "ABSENT") if isinstance(pj, dict) else "ABSENT"),
        "new_run_id": (cj.get("run_id", "ABSENT") if isinstance(cj, dict) else "ABSENT"),
        "parent_top_keys": sorted(pj.keys()) if isinstance(pj, dict) else "N/A",
        "commit_top_keys": sorted(cj.keys()) if isinstance(cj, dict) else "N/A",
        "parent_run_start_utc": (pj.get("run_start_utc", "ABSENT") if isinstance(pj, dict) else "ABSENT"),
        "commit_run_start_utc": (cj.get("run_start_utc", "ABSENT") if isinstance(cj, dict) else "ABSENT"),
    }
    orig_paths = [k for k in pn]
    all_zero = all((isinstance(cn.get(k), (int, float)) and cn.get(k) == 0) for k in orig_paths) if orig_paths else False
    R["statistics"]["new_run_counters_zero"] = ("YES" if all_zero else ("NO" if orig_paths else "UNKNOWN"))
    zeroed = counts.get("ZEROED", 0)
    kept_pos = sum(1 for k in orig_paths if isinstance(cn.get(k), (int, float)) and isinstance(pn.get(k), (int, float))
                    and cn.get(k) == pn.get(k) and cn.get(k) > 0)
    if not orig_paths:
        behav = "UNKNOWN"
    elif zeroed == len(orig_paths):
        behav = "CLEARED"
    elif zeroed > 0 and kept_pos > 0:
        behav = "PARTIALLY_CLEARED"
    elif kept_pos >= (len(orig_paths) * 0.5):
        behav = "RETAINED"
    elif zeroed > 0:
        behav = "PARTIALLY_CLEARED"
    else:
        behav = "UNKNOWN"
    R["statistics"]["old_counters_behavior"] = behav
    R["statistics"]["logical_counter_reset"] = ("PROVEN" if (zeroed > 0 and all_zero) else
                                                  ("NOT_PROVEN" if not all_zero else "NOT_PROVEN"))
    R["statistics"]["reset_model"] = ("IN_PLACE_COUNTER_RESET" if (par_ok and cur_ok) else "UNKNOWN")
    R["old_run_id"] = R["statistics"]["old_run_id"]
    R["new_run_id"] = R["statistics"]["new_run_id"]
    print("stats diff:", json.dumps({"paths": len(orig_paths), "counts": counts, "zero": R["statistics"]["new_run_counters_zero"],
                                      "behav": behav, "logical": R["statistics"]["logical_counter_reset"]},
                                     ensure_ascii=False), flush=True)

    # ---------- part 2: ledger diff ----------
    pl_txt = at(PARENT, P_LEDGER)
    cl_txt = at(C, P_LEDGER)
    pl = [x for x in pl_txt.splitlines() if x.strip()] if not pl_txt.startswith("ERR:") else []
    cl = [x for x in cl_txt.splitlines() if x.strip()] if not cl_txt.startswith("ERR:") else []
    R["ledger"] = {"parent_lines": len(pl), "commit_lines": len(cl),
                     "lines_added": max(0, len(cl) - len(pl)), "lines_removed": max(0, len(pl) - len(cl))}

    def canon(s):
        try:
            return json.dumps(json.loads(s), sort_keys=True, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return s
    pc = [canon(x) for x in pl]
    cc = [canon(x) for x in cl]
    set_p = {}
    for i, x in enumerate(pc):
        set_p.setdefault(x, []).append(i + 1)
    set_c = {}
    for i, x in enumerate(cc):
        set_c.setdefault(x, []).append(i + 1)
    added = [x for x in set_c if x not in set_p]
    removed = [x for x in set_p if x not in set_c]
    def typ(s):
        try:
            return str(json.loads(s).get("type", "UNKNOWN"))
        except Exception:  # noqa: BLE001
            return "UNPARSEABLE"
    R["ledger"]["added_records"] = [{"commit_line": set_c[x][0], "type": typ(x)} for x in added[:40]]
    R["ledger"]["removed_records"] = [{"parent_line": set_p[x][0], "type": typ(x)} for x in removed[:40]]
    R["ledger"]["added_types"] = {}
    for x in added:
        t = typ(x)
        R["ledger"]["added_types"][t] = R["ledger"]["added_types"].get(t, 0) + 1
    R["ledger"]["removed_types"] = {}
    for x in removed:
        t = typ(x)
        R["ledger"]["removed_types"][t] = R["ledger"]["removed_types"].get(t, 0) + 1
    # history preservation model
    prefix_ok = len(pl) > 0 and len(cl) >= len(pl) and pc == cc[:len(pl)]
    all_present = all(x in set_c for x in set_p)
    if prefix_ok and len(cl) >= len(pl):
        model = "UNCHANGED_HISTORY_PLUS_NEW_RECORDS"
    elif all_present and len(cl) > len(pl):
        model = "PARTIAL_REWRITE"
    elif not any(x in set_c for x in set_p) and len(cl) < len(pl):
        model = "TRUNCATED"
    elif not any(x in set_c for x in set_p):
        model = "REWRITTEN"
    else:
        model = "PARTIAL_REWRITE"
    R["ledger"]["reset_model"] = model
    # legacy position field-level change
    def legacy(txt_lines):
        found = {}
        for i, raw in enumerate(txt_lines):
            try:
                j = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(j, dict):
                continue
            hit = {k: j.get(k) for k in IDS if k in j and str(j.get(k)) in IDS.values()}
            if hit:
                found[i + 1] = {"type": j.get("type"), "utc_ts": j.get("utc_ts"), "ids": hit,
                                  "canon": canon(raw)}
        return found
    lp = legacy(pl)
    lc = legacy(cl)
    def same_line(a, b):
        if a is None or b is None:
            return None
        return "UNCHANGED" if a["canon"] == b["canon"] else "CHANGED"
    pt = sorted({v["type"] for v in lp.values()})
    ct = sorted({v["type"] for v in lc.values()})
    def find_by_type(d, t):
        for ln, v in d.items():
            if v["type"] == t:
                return ln, v
        return None, None
    ch = {}
    for label, t in (("LEGACY_ENTRY_CHANGED", "registered"), ("LEGACY_TRIGGER_CHANGED", "triggered"),
                       ("LEGACY_FILL_CHANGED", "filled"), ("LEGACY_EXIT_CHANGED", "closed"),
                       ("LEGACY_PNL_CHANGED", "pnl")):
        pa, va = find_by_type(lp, t)
        pb, vb = find_by_type(lc, t)
        if pa is None and pb is None:
            ch[label] = "NOT_FOUND"
        elif va is None or vb is None:
            ch[label] = "CHANGED(present in only one side)"
        else:
            ch[label] = "UNCHANGED" if va["canon"] == vb["canon"] else "CHANGED"
    R["ledger"]["legacy_position_changes"] = ch
    R["ledger"]["legacy_parent_lines"] = {str(k): v["type"] for k, v in lp.items()}
    R["ledger"]["legacy_commit_lines"] = {str(k): v["type"] for k, v in lc.items()}
    # pnl handling in the added records
    pnl_pat = re.compile(r"(?i)(profit|pnl|realized|closed|close)")
    pnl_added = [d for d in R["ledger"]["added_records"] if pnl_pat.search(json.dumps(d))]
    added_with_pnl_fields = 0
    for x in added:
        try:
            j = json.loads(x)
        except Exception:  # noqa: BLE001
            continue
        if any(re.search(r"(?i)(profit|pnl|realized|closed|close)", str(k)) for k in j.keys()):
            added_with_pnl_fields += 1
    R["ledger"]["pnl_handling"] = ("PRESENT" if (pnl_added or added_with_pnl_fields) else "ABSENT")
    R["ledger"]["pnl_evidence"] = {"added_records_matching_pnl_keywords": len(pnl_added),
                                     "added_records_with_pnl_like_fields": added_with_pnl_fields}
    # ledger run binding
    def binding(txt_lines):
        keys = set()
        for raw in txt_lines:
            try:
                j = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(j, dict):
                for k in ("run_id", "run_start_utc", "run_scope"):
                    if k in j:
                        keys.add(k)
        return sorted(keys)
    R["ledger"]["run_binding_parent"] = binding(pl) or "ABSENT"
    R["ledger"]["run_binding_commit"] = binding(cl) or "ABSENT"
    print("ledger diff:", json.dumps({"parent": len(pl), "commit": len(cl), "added": len(added), "removed": len(removed),
                                       "model": model, "legacy": ch, "pnl": R["ledger"]["pnl_handling"]},
                                      ensure_ascii=False)[:600], flush=True)

    # ---------- isolation + behavior model ----------
    R["isolation"] = {"file_namespace": "ABSENT",
                        "logical_statistics_isolation": ("PROVEN" if R["statistics"]["logical_counter_reset"] == "PROVEN"
                                                           else "NOT_PROVEN"),
                        "old_counters_isolation": ("PROVEN" if (R["statistics"]["old_counters_behavior"] == "CLEARED"
                                                                  and all_zero and R["statistics"]["new_run_counters_zero"] == "YES")
                                                     else "NOT_PROVEN"),
                        "old_pnl_isolation": "NOT_PROVEN"}
    resets = []
    if R["statistics"]["reset_model"] == "IN_PLACE_COUNTER_RESET":
        resets.append("IN_PLACE_COUNTER_RESET")
    if model in ("REWRITTEN", "TRUNCATED", "PARTIAL_REWRITE"):
        resets.append("LEDGER_" + model)
    R["reset_behavior_model"] = ("IN_PLACE_COUNTER_RESET_PLUS_LEDGER_REWRITE" if model in ("REWRITTEN", "TRUNCATED", "PARTIAL_REWRITE")
                                   else ("IN_PLACE_COUNTER_RESET" if resets else "UNKNOWN"))
    R["reset_run_creation"] = "PARTIALLY_PROVEN"
    R["statistics_initialization"] = ("PROVEN" if (par_ok and cur_ok and R["new_run_id"] != "ABSENT") else "PARTIALLY_PROVEN")
    R["logical_counter_reset"] = R["statistics"]["logical_counter_reset"]
    R["per_run_file_namespace"] = "ABSENT"
    R["per_run_statistics_isolation"] = "NOT_PROVEN"
    R["old_counters_isolation"] = R["isolation"]["old_counters_isolation"]
    R["old_pnl_isolation"] = "NOT_PROVEN"
    R["ledger_reset_model"] = model
    for k in COUNTERS:
        R[k] = 0
    R["MT5_ACCESS"] = 0
    R["GIT_COMMIT"] = "NONE"
    R["RESET"] = 0
    R["NEW_RUN"] = 0
    R["V1_START"] = 0
    R["AUTOMATION_ENABLE"] = 0
    # ---------- gate ----------
    g5 = {"RESET_RUN_CREATION": R["reset_run_creation"] == "PROVEN",
            "STATISTICS_INITIALIZATION": R["statistics_initialization"] == "PROVEN",
            "LOGICAL_COUNTER_RESET": R["logical_counter_reset"] == "PROVEN",
            "OLD_COUNTERS_ISOLATION": R["old_counters_isolation"] == "PROVEN",
            "OLD_PNL_ISOLATION": R["old_pnl_isolation"] == "PROVEN"}
    R["gate_conditions"] = g5
    R["gate"] = "PASS" if all(g5.values()) else "FAIL"
    R["new_run_stats_boundary"] = "PROVEN" if R["gate"] == "PASS" else "NOT_PROVEN"
    R["task_status"] = "V1_COUNTER_LEDGER_R27_COMPLETE"
    return finish()


def finish():
    R.setdefault("gate", "FAIL")
    R["hash_after"] = {"ENGINE": sha(ENGINE), "LEDGER": sha(LEDGER), "STATISTICS": sha(STATS), "RUN_META": sha(META)}
    R["hash_before_after_match"] = "YES" if R.get("hash_before") == R.get("hash_after") else "NO"
    R["BOUNDARY_VIOLATION"] = 0 if R["hash_before_after_match"] == "YES" else 1
    R["V1_ISOLATION"] = "PASS" if R["hash_before_after_match"] == "YES" else "FAIL"
    v3 = {"M01_event": sha(os.path.join(M01R, "m01_event_recalculation.jsonl")),
            "R1_ledger": sha(os.path.join(TRD, "tradability_event_ledger.jsonl")),
            "M01_audit": sha(os.path.join(M01A, "audit_summary.json")),
            "R2_canonical": sha(os.path.join(R2, "canonical_output_payload.json"))}
    R["V3_ISOLATION"] = "PASS" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "FAIL"
    lim = datetime.now(timezone.utc).timestamp() - 1800
    v2c = []
    for r_, _, fs in os.walk(V2):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if f.lower().endswith((".py", ".yaml", ".yml")) and os.path.getmtime(os.path.join(r_, f)) > lim:
                v2c.append(os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/"))
    R["V2_ISOLATION"] = "PASS" if not v2c else "FAIL"
    R["changed_files"] = 0
    for k in COUNTERS:
        R.setdefault(k, 0)
    R.setdefault("MT5_ACCESS", 0)
    R.setdefault("GIT_COMMIT", "NONE")
    R.setdefault("RESET", 0)
    R.setdefault("NEW_RUN", 0)
    R.setdefault("V1_START", 0)
    R.setdefault("AUTOMATION_ENABLE", 0)
    R["safety"] = {"AUTOMATION_ENABLED": R.get("AUTOMATION_ENABLED"), "V1_ENGINE_PROCESS": R.get("V1_ENGINE_PROCESS"),
                     "RESET": 0, "NEW_RUN": 0, "V1_START": 0, "AUTOMATION_ENABLE": 0, "MT5_ACCESS": 0,
                     "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0,
                     "LEDGER_WRITE": 0, "STATE_WRITE": 0, "SOURCE_WRITE": 0, "CONFIG_WRITE": 0,
                     "GIT_COMMIT": "NONE", "BOUNDARY_VIOLATION": R["BOUNDARY_VIOLATION"]}
    jp = os.path.join(HERE, "V1_R27_COUNTER_LEDGER.json")
    with open(jp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(R, fh, indent=1, ensure_ascii=False, default=str)
    # markdown
    L = ["# R27 SUMMARY", "", "```text",
          "TASK_STATUS = " + str(R.get("task_status")),
          "COMMIT = " + C, "PARENT_COMMIT = " + R.get("parent_commit", ""),
          "OLD_RUN_ID = " + str(R.get("old_run_id")), "NEW_RUN_ID = " + str(R.get("new_run_id")),
          "NEW_RUN_COUNTERS_ZERO = " + str(R["statistics"]["new_run_counters_zero"]),
          "OLD_COUNTERS_BEHAVIOR = " + str(R["statistics"]["old_counters_behavior"]),
          "LOGICAL_COUNTER_RESET = " + str(R.get("logical_counter_reset")),
          "LEDGER_PARENT_LINES = " + str(R["ledger"]["parent_lines"]),
          "LEDGER_COMMIT_LINES = " + str(R["ledger"]["commit_lines"]),
          "LEDGER_LINES_ADDED = " + str(len(R["ledger"]["added_records"])),
          "LEDGER_LINES_REMOVED = " + str(len(R["ledger"]["removed_records"])),
          "LEDGER_RESET_MODEL = " + str(R.get("ledger_reset_model")),
          "PER_RUN_FILE_NAMESPACE = " + str(R.get("per_run_file_namespace")),
          "LOGICAL_STATISTICS_ISOLATION = " + str(R["isolation"]["logical_statistics_isolation"]),
          "OLD_COUNTERS_ISOLATION = " + str(R.get("old_counters_isolation")),
          "OLD_PNL_ISOLATION = " + str(R.get("old_pnl_isolation")),
          "COMMIT_PNL_HANDLING = " + str(R["ledger"]["pnl_handling"]),
          "RESET_BEHAVIOR_MODEL = " + str(R.get("reset_behavior_model")),
          "R27_GATE = " + str(R.get("gate")),
          "NEW_RUN_STATS_BOUNDARY = " + str(R.get("new_run_stats_boundary")), "```", "",
          "## 1. statistics counter diff", "", "| JSON Path | OLD | NEW | Classification |", "|---|---:|---:|---|"]
    for d in R["statistics"]["counter_diff"]:
        L.append("| `" + d["path"] + "` | " + str(d["OLD"]) + " | " + str(d["NEW"]) + " | " + d["classification"] + " |")
    L += ["", "non-numeric changes: " + json.dumps(R["statistics"]["non_numeric_changes"], ensure_ascii=False), "",
          "counts: " + json.dumps(R["statistics"]["counter_diff_counts"], ensure_ascii=False), "",
          "## 2. logical counter reset conclusion", "", "```text",
          "NEW_RUN_COUNTERS_ZERO = " + str(R["statistics"]["new_run_counters_zero"]),
          "OLD_COUNTERS_BEHAVIOR = " + str(R["statistics"]["old_counters_behavior"]),
          "LOGICAL_COUNTER_RESET = " + str(R.get("logical_counter_reset")),
          "note: counter reset alone does NOT prove per-run namespace isolation", "```", "",
          "## 3. ledger diff", "", "```text",
          "parent_lines = " + str(R["ledger"]["parent_lines"]), "commit_lines = " + str(R["ledger"]["commit_lines"]),
          "added = " + json.dumps(R["ledger"]["added_types"], ensure_ascii=False),
          "removed = " + json.dumps(R["ledger"]["removed_types"], ensure_ascii=False),
          "LEDGER_RESET_MODEL = " + str(R.get("ledger_reset_model")),
          "run binding: parent=" + str(R["ledger"]["run_binding_parent"]) + " commit=" + str(R["ledger"]["run_binding_commit"]),
          "```", "", "## 4. legacy lifecycle impact", "", "```text",
          json.dumps(R["ledger"]["legacy_position_changes"], ensure_ascii=False),
          "parent legacy lines = " + json.dumps(R["ledger"]["legacy_parent_lines"], ensure_ascii=False),
          "commit legacy lines = " + json.dumps(R["ledger"]["legacy_commit_lines"], ensure_ascii=False), "```", "",
          "## 5. PnL handling", "", "```text", "COMMIT_PNL_HANDLING = " + str(R["ledger"]["pnl_handling"]),
          json.dumps(R["ledger"]["pnl_evidence"], ensure_ascii=False), "```", "",
          "## 6. logical vs file isolation", "", "```text",
          "PER_RUN_FILE_NAMESPACE = " + str(R.get("per_run_file_namespace")),
          "LOGICAL_STATISTICS_ISOLATION = " + str(R["isolation"]["logical_statistics_isolation"]),
          "OLD_COUNTERS_ISOLATION = " + str(R.get("old_counters_isolation")),
          "OLD_PNL_ISOLATION = " + str(R.get("old_pnl_isolation")), "```", "",
          "## 7. R26 corrections retained", "", "```text",
          "archive NOT created by this commit; statistics was MODIFIED in place (not archived+recreated);",
          "no reset script in the commit; RUN_META.json CREATED.", "```", "",
          "## 8. R27 gate", "", "```text", "gate = " + str(R.get("gate")),
          json.dumps(R.get("gate_conditions", {}), ensure_ascii=False),
          "NEW_RUN_STATS_BOUNDARY = " + str(R.get("new_run_stats_boundary")), "```", "",
          "## 9. safety", "", "```text", json.dumps(R["safety"], ensure_ascii=False), "```", "",
          "## 10. hashes", "", "```text", "before = " + json.dumps(R.get("hash_before", {}), ensure_ascii=False),
          "after  = " + json.dumps(R.get("hash_after", {}), ensure_ascii=False),
          "match = " + str(R.get("hash_before_after_match")), "```"]
    mp = os.path.join(HERE, "V1_R27_COUNTER_LEDGER_REPORT.md")
    with open(mp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    bad = [c for c in json.dumps(R, ensure_ascii=False) if ord(c) > 0xFFFF]
    print("\n=== FINAL (ASCII-safe print) ===", flush=True)
    safe = {k: R.get(k) for k in ("task_status", "old_run_id", "new_run_id", "logical_counter_reset",
                                    "per_run_file_namespace", "old_counters_isolation", "old_pnl_isolation",
                                    "ledger_reset_model", "gate", "new_run_stats_boundary", "V1_ISOLATION",
                                    "V2_ISOLATION", "V3_ISOLATION", "BOUNDARY_VIOLATION", "GIT_COMMIT",
                                    "changed_files", "reset_behavior_model")}
    try:
        print(json.dumps(safe, ensure_ascii=True), flush=True)
    except Exception:  # noqa: BLE001
        print("print-error", flush=True)
    print("\nartifacts:", jp, "|", mp, flush=True)
    print("utf8_ok:", "YES" if not bad else "NO", flush=True)
    sys.exit(0 if R.get("gate") == "PASS" else 2)


if __name__ == "__main__":
    main()
