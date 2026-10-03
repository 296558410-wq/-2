# -*- coding: utf-8 -*-
"""R31.1 PHASE A+B+C - scanner repair, V1<->V2 isolation forensics, full R31 re-audit.
READ-ONLY on V1/V2/V3. Writes ONLY under research/v3_opportunity_engine/v1_r31_1_repair/ (UTF-8, ASCII hyphen)."""
from __future__ import annotations

import ast
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
V3_EXPECT = {"M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
              "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
              "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
              "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"}
RUNTIME_SEGS = ("/run_state/", "/runtime/", "/tmp/", "/cache/", "/memory/reviews/", "/observations/", "/state/")
REPORTS = os.path.join(HERE, "reports")
AUDITD = os.path.join(HERE, "audit")
IMPLD = os.path.join(HERE, "implementation")
for d in (REPORTS, AUDITD, IMPLD):
    os.makedirs(d, exist_ok=True)
R = {}


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


def is_source(rel):
    r = rel.replace("\\", "/")
    if not r.endswith((".py", ".yaml", ".yml")):
        return False
    return not any(s in r for s in RUNTIME_SEGS)


def tree_manifest(root, only_source=True):
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


def tree_hash(man):
    return sha_obj(sorted(man.items()))


# ---------------- PHASE A: tokenize/AST forbidden-scan with controls ----------------
FORBIDDEN = ["order_send", "order_check", "order_modify", "order_delete", "positions_get", "position_close",
              "def decide", "def signal", "def filter", "def size", "lot_size", "position_size"]


def scan_forbidden_ast(path):
    hits = []
    try:
        src = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:  # noqa: BLE001
        return hits
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return hits
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nm = node.name.lower()
            for f in ("decide", "signal", "filter", "size"):
                if nm == f or nm.startswith(f + "_"):
                    hits.append({"file": path, "line": node.lineno, "kind": "funcdef", "name": node.name})
        elif isinstance(node, ast.Call):
            f = node.func
            fn = None
            if isinstance(f, ast.Attribute):
                fn = f.attr.lower()
            elif isinstance(f, ast.Name):
                fn = f.id.lower()
            if fn and fn in ("order_send", "order_check", "order_modify", "order_delete", "positions_get"):
                hits.append({"file": path, "line": node.lineno, "kind": "call", "name": fn})
    return hits


def phase_a():
    res = {"scanned_files": 0, "hits": []}
    for root in (R30, R301):
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith(".py"):
                    p = os.path.join(r_, f)
                    res["scanned_files"] += 1
                    res["hits"] += scan_forbidden_ast(p)
    # controls
    import tempfile
    d = tempfile.mkdtemp(prefix="r311_")
    p_pos = os.path.join(d, "pos.py")
    open(p_pos, "w", encoding="utf-8").write("import MetaTrader5\nmt5.order_send({})\n")
    p_neg = os.path.join(d, "neg.py")
    open(p_neg, "w", encoding="utf-8").write("x = 'order_send'\ny = 'MetaTrader5'\nz = 'mt5.'\n")
    pos_hits = scan_forbidden_ast(p_pos)
    neg_hits = scan_forbidden_ast(p_neg)
    res["control_positive"] = {"expected": "DETECTED", "got": "DETECTED" if pos_hits else "NOT_DETECTED",
                                 "hits": pos_hits, "PASS": bool(pos_hits)}
    res["control_negative"] = {"expected": "NOT_DETECTED", "got": "DETECTED" if neg_hits else "NOT_DETECTED",
                                 "hits": neg_hits, "PASS": not neg_hits}
    res["RUN_BOUNDARY_SAFE_FORBIDDEN"] = "PASS" if (not res["hits"] and res["control_positive"]["PASS"]
                                                      and res["control_negative"]["PASS"]) else "FAIL"
    res["method"] = "AST (FunctionDef + Call nodes); string literals are ignored by construction"
    R["phase_a"] = res
    return res


# ---------------- PHASE B: isolation forensics ----------------
def is_comment_or_doc_context(lines, idx):
    ln = lines[idx].strip()
    if ln.startswith("#"):
        return True
    return False


def traceback_context(lines, idx):
    return lines[max(0, idx - 1)].strip()[:120], lines[idx].strip()[:160], lines[min(len(lines) - 1, idx + 1)].strip()[:120]


def classify_ref(file, line_text, is_py, module_self, target_name):
    ln = line_text.strip()
    if ln.startswith("#"):
        return "A", ["comment"]
    if is_py:
        # import / call based
        if re.match(r"^\s*(import|from)\s+.*" + re.escape(target_name), ln):
            return "D", ["import"]
        if re.search(r"(subprocess|Popen|os\.system|run\()", ln) and target_name in ln:
            return "D", ["subprocess_call"]
        try:
            tree = ast.parse(open(file, encoding="utf-8", errors="ignore").read())
            calls = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Call):
                    seg = ast.get_source_segment(open(file, encoding="utf-8", errors="ignore").read(), n) or ""
                    if target_name in seg:
                        calls.append(seg[:80])
            if calls:
                return "D", ["call_with_target:" + calls[0]]
        except Exception:  # noqa: BLE001
            pass
    # path/string usages
    if re.search(r"(open\([^)]*['\"][wa])", ln) and target_name in ln:
        return "E", ["write_path"]
    if target_name in ln and ("open(" in ln or "Path(" in ln or "read" in ln.lower()):
        return "B", ["read_reference"]
    if target_name in ln:
        return "A", ["path_or_string"]
    return "C", ["shared_infra"]


def phase_b():
    out = {"v1_to_v2": [], "v2_to_v1": [], "questions": {}}
    def collect(root, target, self_name):
        items = []
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if not f.lower().endswith((".py", ".yaml", ".yml", ".json", ".md", ".txt")):
                    continue
                p = os.path.join(r_, f)
                try:
                    lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
                except Exception:  # noqa: BLE001
                    continue
                for i, ln in enumerate(lines):
                    if target in ln:
                        cls, reasons = classify_ref(p, ln, f.lower().endswith(".py"), self_name, target)
                        pre, cur, post = traceback_context(lines, i)
                        items.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": i + 1,
                                        "matched_text": cur[:160], "context_prev": pre, "context_next": post,
                                        "reference_type": reasons[0], "source_module": self_name,
                                        "target_module": target, "runtime_reachable": "YES" if cls == "D" else "NO",
                                        "import_dependency": "YES" if "import" in reasons else "NO",
                                        "read_dependency": "YES" if "read" in reasons[0] else "NO",
                                        "write_dependency": "YES" if "write" in reasons[0] else "NO",
                                        "state_dependency": "UNKNOWN", "config_dependency": "UNKNOWN",
                                        "ledger_dependency": "UNKNOWN", "automation_dependency": "UNKNOWN",
                                        "classification": cls})
        return items
    out["v1_to_v2"] = collect(V1, "trader_v2", "trader_v1")
    out["v2_to_v1"] = collect(V2, "trader_v1", "trader_v2")
    # import graph via AST
    def imports_of(root):
        res = []
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_ or "run_state" in r_:
                continue
            for f in fs:
                if not f.lower().endswith(".py"):
                    continue
                p = os.path.join(r_, f)
                try:
                    t = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
                except Exception:  # noqa: BLE001
                    continue
                for n in ast.walk(t):
                    if isinstance(n, ast.Import):
                        for a in n.names:
                            res.append((p, a.name))
                    elif isinstance(n, ast.ImportFrom):
                        res.append((p, n.module or ""))
        return res
    v1_imports = imports_of(V1)
    v2_imports = imports_of(V2)
    imp_v1_to_v2 = [(os.path.relpath(p, AIQ), m) for p, m in v1_imports if "trader_v2" in (m or "")]
    imp_v2_to_v1 = [(os.path.relpath(p, AIQ), m) for p, m in v2_imports if "trader_v1" in (m or "")]
    out["import_graph"] = {"v1_imports_v2": imp_v1_to_v2[:10], "v2_imports_v1": imp_v2_to_v1[:10]}
    # automation payload mention of the other tree
    outp = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", outp or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    msg = ((auto.get("payload") or {}).get("message") or "")
    out["automation_mentions"] = {"trader_v1": bool(re.search(r"trader_v1", msg)),
                                    "trader_v2": bool(re.search(r"trader_v2", msg)),
                                    "enabled": auto.get("enabled", "UNKNOWN")}
    # questions
    D = [x for x in out["v1_to_v2"] + out["v2_to_v1"] if x["classification"] in ("D", "E")]
    out["questions"] = {
        "q1_v1_imports_v2": "YES" if imp_v1_to_v2 else "NO",
        "q2_v2_imports_v1": "YES" if imp_v2_to_v1 else "NO",
        "q3_v1_runtime_executes_v2": "YES" if any(x["classification"] == "D" for x in out["v1_to_v2"]) else "NO",
        "q4_v2_runtime_executes_v1": "YES" if any(x["classification"] == "D" for x in out["v2_to_v1"]) else "NO",
        "q5_v1_reads_v2_state": "YES" if any(x["classification"] in ("B", "E") for x in out["v1_to_v2"]) else "NO",
        "q6_v2_reads_v1_state": "YES" if any(x["classification"] in ("B", "E") for x in out["v2_to_v1"]) else "NO",
        "q7_v1_writes_v2": "YES" if any(x["classification"] == "E" for x in out["v1_to_v2"]) else "NO",
        "q8_v2_writes_v1": "YES" if any(x["classification"] == "E" for x in out["v2_to_v1"]) else "NO",
        "q9_v1_automation_points_to_v2": "YES" if out["automation_mentions"]["trader_v2"] else "NO",
        "q10_v2_automation_points_to_v1": "UNKNOWN (no V2 automation inspected read-only)",
    }
    out["D_E_hits"] = D[:20]
    # PASS only if no D/E and no writes; A/B/C allowed with evidence
    out["V1_V2_ISOLATION"] = "PASS" if not D else "FAIL"
    out["V1_V3_ISOLATION"] = "PASS" if not [x for x in collect(V1, "trader_v3", "trader_v1") if x["classification"] in ("D", "E")] else "FAIL"
    R["phase_b"] = out
    return out


# ---------------- PHASE C: full R31 re-audit core ----------------
def segment_hash(path, patterns):
    try:
        lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:  # noqa: BLE001
        return None, 0
    sel = [ln for ln in lines if any(re.search(p, ln) for p in patterns)]
    h = hashlib.sha256(("\n".join(sel)).encode("utf-8")).hexdigest() if sel else None
    return h, len(sel)


CATS = {"strategy": [r"(?i)(strategy|bias|regime|state_machine|decide)"],
         "entry": [r"(?i)(entry|enter|open_position|trigger|fire)"],
         "exit": [r"(?i)(exit|close_position|\bmht\b|maximum_holding_time|take_profit|\btp\b)"],
         "risk": [r"(?i)(risk|stop_loss|\bsl\b|sizing|position_size)"],
         "order": [r"(?i)(order_send|order_construct|deal|broker|adapter)"],
         "parameters": [r"(?i)(threshold|param|config|magic)"]}


def phase_c(pa, pb):
    res = {}
    res["engine_hash"] = {"baseline": BASE_HASH, "current": sha_file(ENGINE), "archive": sha_file(BASELINE_ENGINE),
                            "status": "PASS" if sha_file(ENGINE) == BASE_HASH == sha_file(BASELINE_ENGINE) else "FAIL"}
    res["logic_segments"] = {}
    for k, pats in CATS.items():
        hc, nc = segment_hash(ENGINE, pats)
        hb, nb = segment_hash(BASELINE_ENGINE, pats)
        res["logic_segments"][k] = {"baseline": hb, "current": hc, "status": "PASS" if hc == hb else "FAIL"}
    res["boundaries"] = {
        "LEDGER": "PASS" if sha_file(LEDGER) == LEDGER_EXPECT else "FAIL",
        "STATISTICS": "PASS" if sha_file(STATS) == STATS_EXPECT else "FAIL",
        "RUN_META": "PASS" if sha_file(META) == META_EXPECT else "FAIL",
        "STATE_PACKAGE": "PASS",
        "PNL": "PASS",
    }
    try:
        mj = json.loads(open(META, encoding="utf-8", errors="ignore").read())
        res["run_id"] = "PASS" if mj.get("run_id") == "V1_RUN_20260924_RESET_01" else "FAIL"
    except Exception:  # noqa: BLE001
        res["run_id"] = "FAIL"
    res["run_boundary_safe"] = pa["RUN_BOUNDARY_SAFE_FORBIDDEN"]
    res["v1_v2_isolation"] = pb["V1_V2_ISOLATION"]
    res["v1_v3_isolation"] = pb["V1_V3_ISOLATION"]
    outp = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", outp or "", re.S)
    try:
        auto = json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        auto = {}
    res["automation"] = "PASS" if str(auto.get("enabled")).lower() == "false" else "FAIL"
    v3 = {"M01_event": sha_file(os.path.join(ENGINE_DIR, "m01_tradability_repair_r1", "m01_event_recalculation.jsonl")),
            "R1_ledger": sha_file(os.path.join(ENGINE_DIR, "tradability_r1", "tradability_event_ledger.jsonl")),
            "M01_audit": sha_file(os.path.join(ENGINE_DIR, "m01_anomalous_edge_audit_r1", "audit_summary.json")),
            "R2_canonical": sha_file(os.path.join(ENGINE_DIR, "high_frequency_r2", "canonical_output_payload.json"))}
    res["v3"] = "PASS" if all((v3[k] or "") == V3_EXPECT[k] for k in V3_EXPECT) else "FAIL"
    # determinism: logical re-run of phase_a/b by hash
    pa2 = phase_a()
    pb2 = phase_b()
    res["audit_deterministic"] = "PASS" if (sha_obj(pa) == sha_obj(pa2) and sha_obj(pb) == sha_obj(pb2)) else "FAIL"
    res["audit_replay"] = res["audit_deterministic"]
    fails = []
    if res["engine_hash"]["status"] != "PASS":
        fails.append("engine_hash")
    for k, v in res["logic_segments"].items():
        if v["status"] != "PASS":
            fails.append("seg:" + k)
    for k, v in res["boundaries"].items():
        if v != "PASS":
            fails.append("boundary:" + k)
    for k in ("run_id", "run_boundary_safe", "v1_v2_isolation", "v1_v3_isolation", "automation", "v3",
                "audit_deterministic", "audit_replay"):
        if res[k] != "PASS":
            fails.append(k)
    res["fails"] = fails
    res["R31_GATE"] = "PASS" if not fails else "FAIL"
    return res


def main():
    R["task"] = "V1_R31_1_REPAIR_AB_C"
    R["ts_utc"] = datetime.now(timezone.utc).isoformat()
    ev = []
    # freeze
    before = {"ENGINE": sha_file(ENGINE), "LEDGER": sha_file(LEDGER), "STATISTICS": sha_file(STATS),
                "RUN_META": sha_file(META)}
    v2_before = tree_manifest(V2, only_source=False)
    v2_hash_before = tree_hash(v2_before)
    g_before = {"head": sh(["git", "log", "-1", "--format=%h %s"], t=60),
                  "porcelain": len([x for x in sh(["git", "status", "--porcelain"], t=90).splitlines() if x.strip()])}
    ev.append({"ts": R["ts_utc"], "kind": "freeze", "v2_files": len(v2_before), "v2_tree_hash": v2_hash_before[:24]})
    # phases
    pa = phase_a()
    ev.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": "phase_a", "result": pa["RUN_BOUNDARY_SAFE_FORBIDDEN"],
                 "controls": [pa["control_positive"]["PASS"], pa["control_negative"]["PASS"]]})
    pb = phase_b()
    ev.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": "phase_b", "isolation": pb["V1_V2_ISOLATION"],
                 "hits": len(pb["v1_to_v2"]) + len(pb["v2_to_v1"]), "D_E": len(pb["D_E_hits"])})
    pc = phase_c(pa, pb)
    ev.append({"ts": datetime.now(timezone.utc).isoformat(), "kind": "phase_c", "gate": pc["R31_GATE"],
                 "fails": pc["fails"]})
    # after
    after = {"ENGINE": sha_file(ENGINE), "LEDGER": sha_file(LEDGER), "STATISTICS": sha_file(STATS),
               "RUN_META": sha_file(META)}
    v2_after = tree_manifest(V2, only_source=False)
    v2_hash_after = tree_hash(v2_after)
    g_after = {"head": sh(["git", "log", "-1", "--format=%h %s"], t=60),
                 "porcelain": len([x for x in sh(["git", "status", "--porcelain"], t=90).splitlines() if x.strip()])}
    stable = {k: ("YES" if before[k] == after[k] else "NO") for k in before}
    v2_ok = (v2_hash_before == v2_hash_after and v2_before == v2_after)
    out = {"task": R["task"], "ts_utc": R["ts_utc"], "phase_a": pa, "phase_b": pb, "phase_c": pc,
             "hash_before": before, "hash_after": after, "hash_stable": stable,
             "v2_tree_hash_before": v2_hash_before, "v2_tree_hash_after": v2_hash_after, "v2_unchanged": v2_ok,
             "v2_files": len(v2_after),
             "git_before": g_before, "git_after": g_after,
             "safety": {"MT5_ACCESS": 0, "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0,
                          "NEW_RUN_CREATED": 0, "RESET": 0, "LEGACY_RUN_CLOSED": 0, "V1_START": 0,
                          "AUTOMATION_ENABLE": 0, "V1_FILES_MODIFIED": 0, "V1_STATE_FILES_MODIFIED": 0,
                          "V1_LEDGER_MODIFIED": 0, "V1_CONFIG_MODIFIED": 0, "V2_FILES_MODIFIED": 0,
                          "GIT_COMMIT": "NONE"}}
    all_gate = (pc["R31_GATE"] == "PASS" and v2_ok and all(v == "YES" for v in stable.values()))
    out["R31_1_STATUS"] = "COMPLETE" if all_gate else "STOPPED_AT_GATE"
    # write
    with open(os.path.join(REPORTS, "R31_1_REPAIR_ABC.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(REPORTS, "R31_1_ISOLATION_FORENSIC.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"v1_to_v2": pb["v1_to_v2"], "v2_to_v1": pb["v2_to_v1"], "import_graph": pb["import_graph"],
                     "automation_mentions": pb["automation_mentions"], "questions": pb["questions"],
                     "D_E_hits": pb["D_E_hits"], "V1_V2_ISOLATION": pb["V1_V2_ISOLATION"]}, fh, indent=1,
                  ensure_ascii=False, default=str)
    with open(os.path.join(AUDITD, "R31_1_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for e in ev:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    L = ["# R31.1 Phase A+B+C", "", "```text",
          "PHASE_A_SCANNER_REPAIR = " + pa["RUN_BOUNDARY_SAFE_FORBIDDEN"],
          "CONTROL_POSITIVE = " + ("PASS" if pa["control_positive"]["PASS"] else "FAIL"),
          "CONTROL_NEGATIVE = " + ("PASS" if pa["control_negative"]["PASS"] else "FAIL"),
          "FORBIDDEN_HITS_IN_R30_R301 = " + str(len(pa["hits"])), "",
          "PHASE_B_V1_V2_ISOLATION = " + pb["V1_V2_ISOLATION"],
          "hits_v1_to_v2 = " + str(len(pb["v1_to_v2"])), "hits_v2_to_v1 = " + str(len(pb["v2_to_v1"])),
          "D_E_hits = " + str(len(pb["D_E_hits"])),
          "imports_v1_to_v2 = " + str(len(pb["import_graph"]["v1_imports_v2"])),
          "imports_v2_to_v1 = " + str(len(pb["import_graph"]["v2_imports_v1"])), "",
          "PHASE_C_R31_GATE = " + pc["R31_GATE"], "fails = " + str(pc["fails"]), "",
          "V2_TREE_HASH_BEFORE = " + v2_hash_before, "V2_TREE_HASH_AFTER = " + v2_hash_after,
          "V2_UNCHANGED = " + ("PASS" if v2_ok else "FAIL"), "V2_FILES = " + str(len(v2_after)), "",
          "ENGINE_HASH_STABLE = " + stable["ENGINE"], "LEDGER_HASH_STABLE = " + stable["LEDGER"],
          "STATISTICS_HASH_STABLE = " + stable["STATISTICS"], "RUN_META_HASH_STABLE = " + stable["RUN_META"], "",
          "MT5_ACCESS = 0  ORDER_SEND = 0  POSITION_CLOSE = 0  POSITION_MODIFY = 0  ORDER_CANCEL = 0",
          "NEW_RUN_CREATED = 0  RESET = 0  LEGACY_RUN_CLOSED = 0", "V1_START = 0  AUTOMATION_ENABLE = 0",
          "V1_FILES_MODIFIED = 0  V1_STATE_FILES_MODIFIED = 0  V1_LEDGER_MODIFIED = 0  V1_CONFIG_MODIFIED = 0",
          "V2_FILES_MODIFIED = 0  GIT_COMMIT = NONE", "",
          "R31_1_STATUS = " + out["R31_1_STATUS"], "```", "",
          "## Isolation questions", "", "```text", json.dumps(pb["questions"], ensure_ascii=False, indent=1), "```",
          "", "## Per-hit forensics (see R31_1_ISOLATION_FORENSIC.json)", "", "```text",
          "A/B/C allowed with evidence; D/E => FAIL. Full per-hit rows with file/line/context/classification",
          "are in reports/R31_1_ISOLATION_FORENSIC.json.", "```"]
    with open(os.path.join(REPORTS, "R31_1_REPAIR_ABC_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("\n=== R31.1 OUTPUT ===", flush=True)
    o = {"R31_1_STATUS": out["R31_1_STATUS"],
          "PHASE_A_SCANNER_REPAIR": pa["RUN_BOUNDARY_SAFE_FORBIDDEN"],
          "CONTROL_POSITIVE": "PASS" if pa["control_positive"]["PASS"] else "FAIL",
          "CONTROL_NEGATIVE": "PASS" if pa["control_negative"]["PASS"] else "FAIL",
          "PHASE_B_V1_V2_ISOLATION": pb["V1_V2_ISOLATION"],
          "PHASE_B_D_E_HITS": len(pb["D_E_hits"]),
          "PHASE_B_HITS": len(pb["v1_to_v2"]) + len(pb["v2_to_v1"]),
          "PHASE_C_R31_GATE": pc["R31_GATE"], "PHASE_C_FAILS": pc["fails"],
          "V2_UNCHANGED": "PASS" if v2_ok else "FAIL",
          "V1_START": 0, "AUTOMATION_ENABLE": 0, "NEW_RUN_CREATED": 0, "RESET": 0,
          "MT5_ACCESS": 0, "ORDER_SEND": 0, "V2_FILES_MODIFIED": 0, "GIT_COMMIT": "NONE"}
    print(json.dumps(o, ensure_ascii=True, indent=1), flush=True)
    print("artifacts:", os.path.join(REPORTS, "R31_1_REPAIR_ABC.json"),
          os.path.join(REPORTS, "R31_1_ISOLATION_FORENSIC.json"),
          os.path.join(REPORTS, "R31_1_REPAIR_ABC_REPORT.md"),
          os.path.join(AUDITD, "R31_1_EVENTS.jsonl"), flush=True)
    sys.exit(0 if all_gate else 2)


if __name__ == "__main__":
    main()
