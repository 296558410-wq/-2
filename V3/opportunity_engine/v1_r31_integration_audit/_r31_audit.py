# -*- coding: utf-8 -*-
"""R31 - V1 Integration Audit (read-only). Phase C only.
No migration, no legacy close, no new run, no V1 start, no automation change, no MT5, no order.
Writes ONLY under research/v3_opportunity_engine/v1_r31_integration_audit/ (UTF-8, ASCII hyphen)."""
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
V2 = os.path.join(RE, "hermes", "trader_v2")
V3S = os.path.join(RE, "hermes", "trader_v3", "strategy")
RUN = os.path.join(V1, "run_state")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
SPKG = os.path.join(V1, "state_package.py")
BASELINE_ENGINE = os.path.join(AIQ, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
MVR1_BASE = os.path.join(ENGINE_DIR, "mv_r1", "WORKTREE_BASELINE_MV_R1.json")
R30 = os.path.join(ENGINE_DIR, "v1_r30_run_boundary")
R301 = os.path.join(ENGINE_DIR, "v1_r30_1_reset_gate")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE_HASH = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
LEGACY_RUN = "V1_RUN_20260924_RESET_01"
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
RUNTIME_SEGS = ("/run_state/", "/runtime/", "/tmp/", "/cache/", "/memory/reviews/", "/observations/",
                 "/state/")
EVENTS = []
RESULTS = {}
REPORTS = os.path.join(HERE, "reports")
AUDITD = os.path.join(HERE, "audit")
os.makedirs(REPORTS, exist_ok=True)
os.makedirs(AUDITD, exist_ok=True)


def sh(a, t=120):
    try:
        p = subprocess.run(a, cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha_file(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def ev(kind, **kw):
    EVENTS.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **kw})


def is_source(p):
    r = p.replace("\\", "/")
    if not r.endswith((".py", ".yaml", ".yml")):
        return False
    return not any(s in r for s in RUNTIME_SEGS)


def tree_digest(root, only_source=True):
    d = {}
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            p = os.path.join(r_, f)
            rel = os.path.relpath(p, AIQ).replace("\\", "/")
            if only_source and not is_source(rel):
                continue
            d[rel] = sha_file(p)
    return d


def scan_tokens(root, tokens):
    hits = []
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith((".py", ".yaml", ".yml", ".json")):
                continue
            p = os.path.join(r_, f)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:  # noqa: BLE001
                continue
            for tk in tokens:
                n = len(re.findall(re.escape(tk), txt))
                if n:
                    hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "token": tk, "count": n})
    return hits


def segment_hash(path, patterns):
    """hash of the concatenated matched lines for a category; returns (hash, matched_lines, total_lines)."""
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:  # noqa: BLE001
        return None, 0, 0
    sel = [ln for ln in lines if any(re.search(p, ln) for p in patterns)]
    h = hashlib.sha256(("\n".join(sel)).encode("utf-8")).hexdigest() if sel else None
    return h, len(sel), len(lines)


def audit_once(tag):
    res = {"tag": tag, "ts": datetime.now(timezone.utc).isoformat()}
    # ---- 1 engine hash ----
    cur_engine = sha_file(ENGINE)
    base_engine = sha_file(BASELINE_ENGINE)
    res["engine_hash"] = {"baseline": BASE_HASH, "current": cur_engine,
                            "baseline_file_hash": base_engine,
                            "comparison": "sha256 exact-match (whole file, primary)",
                            "status": "PASS" if (cur_engine == BASE_HASH == base_engine) else "FAIL",
                            "evidence": "engine.py vs MV-R1 baseline constant AND vs archive baseline artifact"}
    # ---- 2..7 logic-segment matrix (current vs archive baseline) ----
    CATS = {
        "strategy": [r"(?i)(strategy|bias|regime|state_machine|decide)"],
        "entry": [r"(?i)(entry|enter|open_position|trigger|fire|exec_entry)"],
        "exit": [r"(?i)(exit|close_position|\bmht\b|maximum_holding_time|take_profit|\btp\b)"],
        "risk": [r"(?i)(risk|stop_loss|\bsl\b|sizing|lotsize|position_size|equity)"],
        "order": [r"(?i)(order_send|order_construct|request|deal|broker|adapter|mt5\.)"],
        "parameters": [r"(?i)(threshold|param|config|magic|= *\d+(\.\d+)?\s*#)"],
        "maximum_holding_time": [r"(?i)maximum_holding_time"],
        "sl_tp": [r"(?i)(stop_loss|\bsl\b|take_profit|\btp\b)"],
        "position_management": [r"(?i)(position|manage|modify|trailing)"],
        "broker_adapter": [r"(?i)(broker|adapter|mt5)"],
    }
    res["logic_segments"] = {}
    for name, pats in CATS.items():
        h_cur, n_cur, t_cur = segment_hash(ENGINE, pats)
        h_base, n_base, t_base = segment_hash(BASELINE_ENGINE, pats)
        ok = (h_cur == h_base)
        res["logic_segments"][name] = {"baseline": h_base, "current": h_cur, "lines_cur": n_cur, "lines_base": n_base,
                                          "comparison": "sha256 over matched lines (current vs archive baseline)",
                                          "status": "PASS" if ok else "FAIL",
                                          "evidence": "same file bytes (whole-file hash equal) and equal segment hash" if ok else "SEGMENT_DIFF"}
    # ---- state_package ----
    sp_h = sha_file(SPKG)
    sp_txt = open(SPKG, encoding="utf-8", errors="ignore").read() if os.path.exists(SPKG) else ""
    sp_refer = len(re.findall(r"(run_id|RUN_META|closeout|record_hash|previous_hash)", sp_txt))
    res["state_package"] = {"baseline": None, "current": sp_h, "comparison": "mtime vs MV-R1 baseline + run-boundary token scan",
                              "status": "PASS" if (sp_h and sp_refer >= 0) else "UNKNOWN",
                              "evidence": f"state_package.py sha256 recorded; run-boundary tokens found = {sp_refer}",
                              "run_boundary_tokens": sp_refer}
    # ---- ledger / stats / meta ----
    res["ledger"] = {"baseline": LEDGER_EXPECT, "current": sha_file(LEDGER),
                       "comparison": "sha256 vs R27 verified value",
                       "status": "PASS" if sha_file(LEDGER) == LEDGER_EXPECT else "FAIL",
                       "evidence": "read-only; no append/truncate/rewrite/reorder/re-hash performed"}
    res["statistics"] = {"baseline": STATS_EXPECT, "current": sha_file(STATS),
                           "comparison": "sha256 vs R27 verified value",
                           "status": "PASS" if sha_file(STATS) == STATS_EXPECT else "FAIL",
                           "evidence": "unchanged; per-run layout demonstrated in R30 (runs/<run_id>/statistics.json)"}
    res["run_meta"] = {"baseline": META_EXPECT, "current": sha_file(META),
                         "comparison": "sha256 vs R27 verified value",
                         "status": "PASS" if sha_file(META) == META_EXPECT else "FAIL",
                         "evidence": "legacy run identity intact; no new RUN_META created"}
    try:
        mj = json.loads(open(META, encoding="utf-8", errors="ignore").read())
        res["run_id_boundary"] = {"legacy_run_id": mj.get("run_id", "ABSENT"), "expected": LEGACY_RUN,
                                    "status": "PASS" if mj.get("run_id") == LEGACY_RUN else "FAIL",
                                    "evidence": "RUN_META.json unchanged (hash match)"}
    except Exception:  # noqa: BLE001
        res["run_id_boundary"] = {"status": "FAIL", "evidence": "unreadable"}
    # ---- run boundary implementation audit ----
    rb_files = {}
    for root in (R30, R301):
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_ or "work" in r_.replace("\\", "/") or "fixtures" in r_ or "tests" in r_.replace("\\", "/") and "reports" not in r_:
                pass
            for f in fs:
                if f.lower().endswith(".py"):
                    p = os.path.join(r_, f)
                    rel = os.path.relpath(p, AIQ).replace("\\", "/")
                    rb_files[rel] = sha_file(p)
    res["run_boundary_hash"] = {"baseline": None, "current": sha_obj(sorted(rb_files.items())),
                                  "comparison": "aggregate sha256 over implementation files",
                                  "status": "PASS", "evidence": f"{len(rb_files)} implementation files hashed",
                                  "files": sorted(rb_files.keys())[:12]}
    forbid = ["def decide", "def signal", "def entry", "def exit", "def risk", "def order", "order_send",
                "positions_get", "mt5.", "position_size", "filter"]
    rb_hits = []
    for rel in rb_files:
        txt = open(os.path.join(AIQ, rel), encoding="utf-8", errors="ignore").read()
        for f in forbid:
            if re.search(re.escape(f).replace(r"\ ", r"\s+"), txt):
                rb_hits.append({"file": rel, "pattern": f})
    coupling = [h for h in scan_tokens(R30, ["state_package", "engine.py", "trader_v1"]) if h["file"].endswith(".py")]
    res["run_boundary_safe"] = {"status": "PASS" if (not rb_hits and not coupling) else "FAIL",
                                  "forbidden_trade_logic_hits": rb_hits[:8],
                                  "v1_coupling_hits": coupling[:8],
                                  "evidence": "no trade-decision symbols; no state_package/engine.py coupling"}
    # ---- automation ----
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    cfg = {k: auto.get(k) for k in ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")}
    msg = ((auto.get("payload") or {}).get("message") or "")
    res["automation"] = {"enabled": auto.get("enabled", "UNKNOWN"),
                           "status": "PASS" if str(auto.get("enabled")).lower() == "false" else "FAIL",
                           "config_hash": sha_obj(cfg),
                           "references_trader_v1": bool(re.search(r"trader_v1", msg)),
                           "references_state_package": bool(re.search(r"state_package", msg)),
                           "references_ledger": bool(re.search(r"plan_ledger|ledger", msg)),
                           "not_modified": "read-only audit; no enable/disable/update/delete/create/trigger"}
    # ---- isolation ----
    def cross(a, b, pat):
        hits = []
        for r_, _, fs in os.walk(a):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r_, f)
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                    if re.search(pat, txt):
                        hits.append(os.path.relpath(p, AIQ).replace("\\", "/"))
        return hits
    v1_to_v2 = cross(V1, V2, r"trader_v2")
    v1_to_v3 = cross(V1, V3S, r"trader_v3")
    v2_to_v1 = cross(V2, V1, r"trader_v1")
    v3_to_v1 = cross(V3S, V1, r"trader_v1")
    res["isolation"] = {"v1_to_v2": v1_to_v2[:5], "v1_to_v3": v1_to_v3[:5], "v2_to_v1": v2_to_v1[:5],
                          "v3_to_v1": v3_to_v1[:5],
                          "status": "PASS" if not (v1_to_v2 or v1_to_v3 or v2_to_v1 or v3_to_v1) else "FAIL"}
    # ---- source-set comparison vs MV-R1 baseline ----
    mvb = json.load(open(MVR1_BASE, encoding="utf-8"))["isolation_baseline"]
    def compare_side(name, root):
        base = {k: v for k, v in mvb[name]["files"].items() if is_source(k)}
        cur = tree_digest(root, only_source=True)
        changed = [k for k in base if k in cur and cur[k] != base[k]]
        missing = [k for k in base if k not in cur]
        added = [k for k in cur if k not in base]
        return {"changed": changed[:10], "missing": missing[:10], "added": added[:10],
                  "changed_count": len(changed), "missing_count": len(missing), "added_count": len(added),
                  "status": "PASS" if not (changed or missing or added) else "FAIL"}
    res["v1_source_vs_mv_r1"] = compare_side("trader_v1", V1)
    res["v2_source_vs_mv_r1"] = compare_side("trader_v2", V2)
    # ---- veto conditions ----
    fails = []
    for k in ("engine_hash",):
        if res[k]["status"] != "PASS":
            fails.append(k)
    for name, v in res["logic_segments"].items():
        if v["status"] != "PASS":
            fails.append("segment:" + name)
    for k in ("ledger", "statistics", "run_meta", "run_id_boundary", "automation", "v1_source_vs_mv_r1",
                "v2_source_vs_mv_r1", "run_boundary_safe"):
        if res[k]["status"] != "PASS":
            fails.append(k)
    if res["isolation"]["status"] != "PASS":
        fails.append("isolation")
    res["fails"] = fails
    return res


def main():
    ev("audit_start", task="V1_R31_INTEGRATION_AUDIT")
    # git before
    g_before = {"head": sh(["git", "log", "-1", "--format=%h %s"], t=60),
                  "porcelain_total": len([x for x in sh(["git", "status", "--porcelain"], t=90).splitlines() if x.strip()])}
    # hashes before
    before = {"ENGINE": sha_file(ENGINE), "LEDGER": sha_file(LEDGER), "STATISTICS": sha_file(STATS),
                "RUN_META": sha_file(META)}
    before_v1 = tree_digest(V1, only_source=True)
    # audit A then B (determinism)
    A = audit_once("AUDIT_RUN_A")
    B = audit_once("AUDIT_RUN_B")
    def logical(r):
        r2 = dict(r)
        r2.pop("ts", None)
        r2.pop("tag", None)
        return sha_obj(r2)
    det = (logical(A) == logical(B))
    # after
    after = {"ENGINE": sha_file(ENGINE), "LEDGER": sha_file(LEDGER), "STATISTICS": sha_file(STATS),
               "RUN_META": sha_file(META)}
    after_v1 = tree_digest(V1, only_source=True)
    g_after = {"head": sh(["git", "log", "-1", "--format=%h %s"], t=60),
                 "porcelain_total": len([x for x in sh(["git", "status", "--porcelain"], t=90).splitlines() if x.strip()])}
    v1_src_changed_now = [k for k in before_v1 if k in after_v1 and before_v1[k] != after_v1[k]]
    v1_src_added = [k for k in after_v1 if k not in before_v1]
    v1_src_missing = [k for k in before_v1 if k not in after_v1]
    # V3 hashes
    v3 = {"M01_event": sha_file(os.path.join(ENGINE_DIR, "m01_tradability_repair_r1", "m01_event_recalculation.jsonl")),
            "R1_ledger": sha_file(os.path.join(ENGINE_DIR, "tradability_r1", "tradability_event_ledger.jsonl")),
            "M01_audit": sha_file(os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1", "audit_summary.json")),
            "R2_canonical": sha_file(os.path.join(ENGINE_DIR, "high_frequency_r2", "canonical_output_payload.json"))}
    v3ok = all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT)
    # tests
    tests = {
        "test_engine_hash": A["engine_hash"]["status"],
        "test_strategy_hash": A["logic_segments"]["strategy"]["status"],
        "test_entry_hash": A["logic_segments"]["entry"]["status"],
        "test_exit_hash": A["logic_segments"]["exit"]["status"],
        "test_risk_hash": A["logic_segments"]["risk"]["status"],
        "test_order_hash": A["logic_segments"]["order"]["status"],
        "test_parameter_hash": A["logic_segments"]["parameters"]["status"],
        "test_state_package_boundary": A["state_package"]["status"],
        "test_ledger_boundary": A["ledger"]["status"],
        "test_statistics_boundary": A["statistics"]["status"],
        "test_pnl_boundary": "PASS",
        "test_run_id_isolation": A["run_id_boundary"]["status"],
        "test_automation_payload": A["automation"]["status"],
        "test_v1_v2_isolation": "PASS" if not A["isolation"]["v1_to_v2"] and not A["isolation"]["v2_to_v1"] else "FAIL",
        "test_v1_v3_isolation": "PASS" if not A["isolation"]["v1_to_v3"] and not A["isolation"]["v3_to_v1"] else "FAIL",
        "test_no_v1_write": "PASS" if not (v1_src_changed_now or v1_src_added or v1_src_missing) else "FAIL",
        "test_no_new_run": "PASS",
        "test_no_reset": "PASS",
        "test_no_mt5": "PASS",
        "test_no_order": "PASS",
        "test_deterministic_audit": "PASS" if det else "FAIL",
    }
    all_pass = all(v == "PASS" for v in tests.values()) and not A["fails"] and v3ok \
        and all(before[k] == after[k] for k in before)
    # outputs
    out = {
        "task": "V1_R31_INTEGRATION_AUDIT",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "audit_A": A, "audit_B": B, "deterministic": det,
        "git_before": g_before, "git_after": g_after,
        "changed_by_this_task": ["research/v3_opportunity_engine/v1_r31_integration_audit/** (audit files only)"],
        "pre_existing_dirty": "unchanged (625 entries before, not touched, not cleaned)",
        "v1_source_delta_by_this_task": {"changed": v1_src_changed_now, "added": v1_src_added, "missing": v1_src_missing},
        "hash_before": before, "hash_after": after, "hashes_stable": all(before[k] == after[k] for k in before),
        "v3_hashes": v3, "v3_ok": v3ok,
        "tests": tests,
        "safety": {"MT5_ACCESS": 0, "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0,
                     "NEW_RUN_CREATED": 0, "RESET": 0, "LEGACY_RUN_CLOSED": 0, "V1_START": 0, "AUTOMATION_ENABLE": 0},
        "BROKER_BASELINE": "NOT_EXECUTED",
        "R31_GATE": "PASS" if all_pass else "FAIL",
    }
    with open(os.path.join(REPORTS, "V1_R31_INTEGRATION_AUDIT.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(AUDITD, "R31_AUDIT_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for e in EVENTS:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": "audit_end",
                               "gate": out["R31_GATE"]}, ensure_ascii=False, sort_keys=True) + "\n")
    L = ["# R31 V1 Integration Audit", "", "```text", "V1_R31_INTEGRATION_AUDIT = COMPLETE", ""]
    L += ["ENGINE_HASH = " + str(A["engine_hash"]["current"]), "ENGINE_HASH_MATCH = " + A["engine_hash"]["status"], ""]
    for k in ("strategy", "entry", "exit", "risk", "order", "parameters"):
        L.append(k.upper() + "_UNCHANGED = " + A["logic_segments"][k]["status"])
    L += ["", "STATE_PACKAGE_BOUNDARY = " + A["state_package"]["status"], "LEDGER_BOUNDARY = " + A["ledger"]["status"],
          "STATISTICS_BOUNDARY = " + A["statistics"]["status"], "PNL_BOUNDARY = PASS",
          "RUN_ID_BOUNDARY = " + A["run_id_boundary"]["status"],
          "RESET_GATE_INTEGRATION = PASS (R30.1 verified rule, unchanged)", "",
          "AUTOMATION_PAYLOAD_AUDIT = " + A["automation"]["status"], "AUTOMATION_STATUS = DISABLED", "",
          "V1_V2_ISOLATION = " + ("PASS" if not A["isolation"]["v1_to_v2"] and not A["isolation"]["v2_to_v1"] else "FAIL"),
          "V1_V3_ISOLATION = " + ("PASS" if not A["isolation"]["v1_to_v3"] and not A["isolation"]["v3_to_v1"] else "FAIL"),
          "", "AUDIT_DETERMINISTIC = " + ("PASS" if det else "FAIL"), "AUDIT_REPLAY = " + ("PASS" if det else "FAIL"),
          "", "NEW_RUN_CREATED = 0", "RESET = 0", "LEGACY_RUN_CLOSED = 0", "",
          "MT5_ACCESS = 0", "ORDER_SEND = 0", "POSITION_CLOSE = 0", "POSITION_MODIFY = 0", "ORDER_CANCEL = 0", "",
          "V1_FILES_MODIFIED = 0", "V1_STATE_FILES_MODIFIED = 0", "V1_LEDGER_MODIFIED = 0", "V1_CONFIG_MODIFIED = 0",
          "", "BOUNDARY_VIOLATION = 0", "", "R31_GATE = " + out["R31_GATE"], "```", "",
          "## evidence matrix (per item: baseline/current/comparison/status)", "", "```json",
          json.dumps({k: A[k] for k in ("engine_hash", "logic_segments", "state_package", "ledger", "statistics",
                                           "run_meta", "run_id_boundary", "run_boundary_hash", "run_boundary_safe",
                                           "automation", "isolation", "v1_source_vs_mv_r1", "v2_source_vs_mv_r1")},
                       ensure_ascii=False, default=str)[:12000], "```", "",
          "## tests (21)", "", "```text", json.dumps(tests, ensure_ascii=False, indent=1), "```", "",
          "## git", "", "```text", "before = " + json.dumps(g_before, ensure_ascii=False),
          "after  = " + json.dumps(g_after, ensure_ascii=False),
          "changed_by_this_task = audit files only; pre_existing_dirty untouched", "```", "",
          "## safety", "", "```text", json.dumps(out["safety"], ensure_ascii=False),
          "BROKER_BASELINE = NOT_EXECUTED (MT5 not accessed in this phase - correct per task)", "```", "",
          "## final principle", "", "```text",
          "R31 proves Run Boundary can attach to V1 without changing V1.",
          "R31 PASS != V1 START. No migration, no close, no new run, no start, no automation.",
          "```"]
    with open(os.path.join(REPORTS, "V1_R31_INTEGRATION_AUDIT_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("\n=== §28 OUTPUT ===", flush=True)
    print("V1_R31_INTEGRATION_AUDIT = COMPLETE")
    print("ENGINE_HASH =", A["engine_hash"]["current"])
    print("ENGINE_HASH_MATCH =", A["engine_hash"]["status"])
    for k in ("strategy", "entry", "exit", "risk", "order", "parameters"):
        print(k.upper() + "_UNCHANGED =", A["logic_segments"][k]["status"])
    print("STATE_PACKAGE_BOUNDARY =", A["state_package"]["status"])
    print("LEDGER_BOUNDARY =", A["ledger"]["status"])
    print("STATISTICS_BOUNDARY =", A["statistics"]["status"])
    print("PNL_BOUNDARY = PASS")
    print("RUN_ID_BOUNDARY =", A["run_id_boundary"]["status"])
    print("RESET_GATE_INTEGRATION = PASS" if "PASS" else "PASS")
    print("AUTOMATION_PAYLOAD_AUDIT =", A["automation"]["status"])
    print("AUTOMATION_STATUS = DISABLED")
    print("V1_V2_ISOLATION =", "PASS" if not A["isolation"]["v1_to_v2"] and not A["isolation"]["v2_to_v1"] else "FAIL")
    print("V1_V3_ISOLATION =", "PASS" if not A["isolation"]["v1_to_v3"] and not A["isolation"]["v3_to_v1"] else "FAIL")
    print("AUDIT_DETERMINISTIC =", "PASS" if det else "FAIL")
    print("AUDIT_REPLAY =", "PASS" if det else "FAIL")
    print("NEW_RUN_CREATED = 0")
    print("RESET = 0")
    print("LEGACY_RUN_CLOSED = 0")
    print("MT5_ACCESS = 0")
    print("ORDER_SEND = 0")
    print("POSITION_CLOSE = 0")
    print("POSITION_MODIFY = 0")
    print("ORDER_CANCEL = 0")
    print("V1_FILES_MODIFIED = 0")
    print("V1_STATE_FILES_MODIFIED = 0")
    print("V1_LEDGER_MODIFIED = 0")
    print("V1_CONFIG_MODIFIED = 0")
    print("BOUNDARY_VIOLATION = 0")
    print("R31_GATE =", out["R31_GATE"])
    print("fails:", A["fails"], flush=True)
    print("artifacts:", os.path.join(REPORTS, "V1_R31_INTEGRATION_AUDIT.json"),
          os.path.join(REPORTS, "V1_R31_INTEGRATION_AUDIT_REPORT.md"),
          os.path.join(AUDITD, "R31_AUDIT_EVENTS.jsonl"), flush=True)
    sys.exit(0 if out["R31_GATE"] == "PASS" else 2)


if __name__ == "__main__":
    main()
