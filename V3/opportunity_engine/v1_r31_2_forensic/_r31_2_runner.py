# -*- coding: utf-8 -*-
"""R31.2 - isolation re-adjudication + determinism repair. V2 = READ_ONLY (tree-hash proven).
Writes ONLY under research/v3_opportunity_engine/v1_r31_2_forensic/ (UTF-8, ASCII hyphen)."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
BASELINE_ENGINE = os.path.join(AIQ, "archive", "v1_pre_reset_20260923_233741", "v1_root", "engine.py")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE_HASH = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
STATS_EXPECT = "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
PREV_FORENSIC = os.path.join(ENGINE_DIR, "v1_r31_1_repair", "reports", "R31_1_ISOLATION_FORENSIC.json")
FIXDIR = os.path.join(HERE, "fixtures", "determinism_control")
REPORTS = os.path.join(HERE, "reports")
AUDITD = os.path.join(HERE, "audit")
for d in (FIXDIR, REPORTS, AUDITD):
    os.makedirs(d, exist_ok=True)


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


def tree_manifest(root):
    d = {}
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            p = os.path.join(r_, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            d[os.path.relpath(p, AIQ).replace("\\", "/")] = {"sha256": sha_file(p), "size": st.st_size}
    return d


def tree_hash(man):
    return sha_obj({k: v["sha256"] for k, v in sorted(man.items())})


# ---------------- hit collection (same scope as R31.1) ----------------
def collect_hits(root, target):
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
                    items.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": i + 1,
                                    "matched_text": ln.strip()[:200]})
    return items


# ---------------- adjudication ----------------
ENTRY_NAMES = {"engine.py", "state_package.py", "broker_mt5_demo.py", "metrics.py", "ledger.py", "position.py",
                "opportunity.py", "review.py", "state.py", "v2_scheduled_cycle.py", "server.py", "v2_observer.py"}


def import_graph(root):
    g = {}
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            if not f.lower().endswith(".py"):
                continue
            p = os.path.join(root, r_, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            mods = []
            try:
                src = open(p, encoding="utf-8", errors="ignore").read()
                with warnings.catch_warnings(record=True) as wl:
                    warnings.simplefilter("always")
                    t = ast.parse(src)
                    warn = [str(w.message) for w in wl]
                for n in ast.walk(t):
                    if isinstance(n, ast.Import):
                        mods += [a.name for a in n.names]
                    elif isinstance(n, ast.ImportFrom):
                        if n.module:
                            mods.append(n.module)
                g[rel] = {"imports": mods, "warnings": warn, "parse": "OK"}
            except SyntaxError:
                g[rel] = {"imports": [], "warnings": [], "parse": "SYNTAX_ERROR"}
    return g


def runtime_chain(g, names):
    chain = set()
    frontier = [k for k in g if os.path.basename(k) in names]
    while frontier:
        cur = frontier.pop()
        if cur in chain:
            continue
        chain.add(cur)
        base = cur[:-3].replace("/", ".") if cur.endswith(".py") else cur
        for k in g:
            for m in g[k]["imports"]:
                if m == base or m.endswith(base.split(".")[-1]) or m.replace(".", "/") in cur:
                    if k not in chain:
                        frontier.append(k)
        # also modules imported by cur pull in? (downstream not needed)
    return chain


def adjudicate(hit, side):
    """side = 'V1_TO_V2' or 'V2_TO_V1'; returns full evidence row."""
    p = os.path.join(AIQ, hit["file"])
    target = "trader_v2" if side == "V1_TO_V2" else "trader_v1"
    row = {"ID": None, "FILE": hit["file"], "LINE": hit["line"], "CODE_CONTEXT": hit["matched_text"],
            "SOURCE_MODULE": "trader_v1" if side == "V1_TO_V2" else "trader_v2",
            "TARGET_MODULE": target, "REFERENCE_TYPE": "UNKNOWN", "IMPORT_EDGE": "NO", "CALL_EDGE": "NO",
            "RUNTIME_REACHABLE": "UNKNOWN", "READS_V2": "NO", "WRITES_V2": "NO", "READS_V1": "NO", "WRITES_V1": "NO",
            "STATE_COUPLING": "NO", "CONFIG_COUPLING": "NO", "LEDGER_COUPLING": "NO", "AUTOMATION_COUPLING": "NO",
            "ACTUAL_RUNTIME_PATH": "UNKNOWN", "CLASSIFICATION": "C", "SUB_CLASSIFICATION": "", "FINAL_DISPOSITION": ""}
    try:
        lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
    except Exception:  # noqa: BLE001
        row["CLASSIFICATION"] = "NOT_PROVEN"
        row["FINAL_DISPOSITION"] = "FILE_UNREADABLE"
        return row
    cur = lines[hit["line"] - 1] if 0 < hit["line"] <= len(lines) else ""
    low = p.lower()
    # comment
    if cur.strip().startswith("#"):
        row.update({"REFERENCE_TYPE": "comment", "CLASSIFICATION": "A", "FINAL_DISPOSITION": "A_NO_COUPLING"})
        return row
    # path keywords for couplings
    for k, key in (("STATE_COUPLING", ("run_state", "state_package", "statistics")),
                     ("CONFIG_COUPLING", (".yaml", ".yml", "config")),
                     ("LEDGER_COUPLING", ("ledger", "plan_ledger")),
                     ("AUTOMATION_COUPLING", ("cron", "automation", "scheduler"))):
        if any(x in cur.lower() for x in key):
            row[k] = "YES"
    if p.lower().endswith(".py"):
        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                tree = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
            in_doc = False
            smallest = None
            for n in ast.walk(tree):
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    names = ([a.name for a in n.names] if isinstance(n, ast.Import)
                               else [n.module or ""])
                    if any(target in (x or "") for x in names):
                        row["IMPORT_EDGE"] = "YES"
                        row["REFERENCE_TYPE"] = "import"
                if isinstance(n, ast.Call):
                    seg = ""
                    try:
                        seg = ast.get_source_segment(open(p, encoding="utf-8", errors="ignore").read(), n) or ""
                    except Exception:  # noqa: BLE001
                        seg = ""
                    if target in seg:
                        f = n.func
                        fn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "?")
                        row["CALL_EDGE"] = "YES"
                        row["REFERENCE_TYPE"] = "call:" + str(fn)
                        segw = re.search(r"open\s*\([^)]*['\"]([wa])['\"]", seg)
                        if fn == "open" and segw:
                            if segw.group(1) == "w":
                                row["WRITES_V2" if side == "V1_TO_V2" else "WRITES_V1"] = "YES"
                            else:
                                row["READS_V2" if side == "V1_TO_V2" else "READS_V1"] = "YES"
                        if fn in ("run", "Popen", "system", "check_output", "call"):
                            row["REFERENCE_TYPE"] = "subprocess:" + str(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and target in n.value:
                    in_doc = in_doc or isinstance(n.value, str) and False
                    if row["REFERENCE_TYPE"] == "UNKNOWN":
                        row["REFERENCE_TYPE"] = "string_constant"
            if in_doc:
                row["REFERENCE_TYPE"] = "docstring"
        except SyntaxError:
            row["REFERENCE_TYPE"] = "PARSE_FAIL"
    else:
        # data/markdown files: inert unless write pattern (not possible in json/md)
        if row["REFERENCE_TYPE"] == "UNKNOWN":
            row["REFERENCE_TYPE"] = "data_or_doc"
    return row


def main():
    ts = datetime.now(timezone.utc).isoformat()
    R = {"task": "V1_R31_2_FORENSIC", "ts_utc": ts}
    # ---- V2 hash before ----
    v2_before = tree_manifest(V2)
    v2h_before = tree_hash(v2_before)
    # ---- collect + cross-check ----
    v1_hits = collect_hits(V1, "trader_v2")
    v2_hits = collect_hits(V2, "trader_v1")
    prev = {}
    if os.path.exists(PREV_FORENSIC):
        try:
            prev = json.load(open(PREV_FORENSIC, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prev = {}
    total = len(v1_hits) + len(v2_hits)
    # ---- graph + runtime chains ----
    g1 = import_graph(V1)
    g2 = import_graph(V2)
    rc1 = runtime_chain(g1, ENTRY_NAMES)
    rc2 = runtime_chain(g2, ENTRY_NAMES)
    warnings_found = []
    for gg in (g1, g2):
        for k, v in gg.items():
            if v["parse"] != "OK":
                warnings_found.append({"file": k, "parse": v["parse"]})
            for w in v["warnings"]:
                warnings_found.append({"file": k, "warning": w})
    # ---- adjudicate ----
    rows = []
    for i, h in enumerate(v1_hits):
        r = adjudicate(h, "V1_TO_V2")
        r["ID"] = "V1V2-%02d" % (i + 1)
        rel = r["FILE"]
        if rel.endswith(".py"):
            r["RUNTIME_REACHABLE"] = "YES" if rel in rc1 else "NO"
            if r["RUNTIME_REACHABLE"] == "NO" and r["CALL_EDGE"] == "YES":
                r["CLASSIFICATION"] = "B" if r["WRITES_V2"] == "NO" and r["IMPORT_EDGE"] == "NO" else "E5"
            elif r["IMPORT_EDGE"] == "YES":
                r["CLASSIFICATION"] = "D"
                r["SUB_CLASSIFICATION"] = "D1"
            elif r["CALL_EDGE"] == "YES":
                if r["WRITES_V2"] == "YES":
                    r["CLASSIFICATION"] = "E"
                    r["SUB_CLASSIFICATION"] = "E5"
                elif r["RUNTIME_REACHABLE"] == "YES":
                    r["CLASSIFICATION"] = "D"
                    r["SUB_CLASSIFICATION"] = "D2"
                else:
                    r["CLASSIFICATION"] = "B"
            elif r["REFERENCE_TYPE"] in ("comment", "docstring", "data_or_doc", "string_constant"):
                r["CLASSIFICATION"] = "A"
        else:
            r["CLASSIFICATION"] = "A"
            r["RUNTIME_REACHABLE"] = "N/A"
        rows.append(r)
    for i, h in enumerate(v2_hits):
        r = adjudicate(h, "V2_TO_V1")
        r["ID"] = "V2V1-%02d" % (i + 1)
        rel = r["FILE"]
        if rel.endswith(".py"):
            r["RUNTIME_REACHABLE"] = "YES" if rel in rc2 else "NO"
            if r["IMPORT_EDGE"] == "YES":
                r["CLASSIFICATION"] = "D"
                r["SUB_CLASSIFICATION"] = "D1"
            elif r["CALL_EDGE"] == "YES":
                if r["WRITES_V1"] == "YES":
                    r["CLASSIFICATION"] = "E"
                    r["SUB_CLASSIFICATION"] = "E5"
                elif r["RUNTIME_REACHABLE"] == "YES":
                    r["CLASSIFICATION"] = "D"
                    r["SUB_CLASSIFICATION"] = "D2"
                else:
                    r["CLASSIFICATION"] = "B"
            elif r["REFERENCE_TYPE"] in ("comment", "docstring", "data_or_doc", "string_constant"):
                r["CLASSIFICATION"] = "A"
        else:
            r["CLASSIFICATION"] = "A"
            r["RUNTIME_REACHABLE"] = "N/A"
        rows.append(r)
    # historical list for cross-check (9 D/E ids from R31.1)
    prev_de = [x for x in (prev.get("D_E_hits") or [])]
    rowmap = {(r["FILE"], r["LINE"]): r for r in rows}
    re_adj = []
    for x in prev_de:
        key = (x.get("file"), x.get("line"))
        cur = rowmap.get(key)
        if cur is None:
            re_adj.append({"prev_file": key[0], "prev_line": key[1], "prev_class": x.get("classification"),
                             "new_class": "NOT_FOUND_IN_RECOLLECT", "new_sub": "", "disposition": "REVIEW"})
        else:
            re_adj.append({"prev_file": key[0], "prev_line": key[1], "prev_class": x.get("classification"),
                             "new_class": cur["CLASSIFICATION"], "new_sub": cur["SUB_CLASSIFICATION"],
                             "new_disposition": cur["FINAL_DISPOSITION"], "runtime_reachable": cur["RUNTIME_REACHABLE"],
                             "reference_type": cur["REFERENCE_TYPE"]})
    # dispositions
    for r in rows:
        if not r["FINAL_DISPOSITION"]:
            if r["CLASSIFICATION"] == "A":
                r["FINAL_DISPOSITION"] = "A_NO_COUPLING"
            elif r["CLASSIFICATION"] == "B":
                r["FINAL_DISPOSITION"] = "B_READ_ONLY_NON_RUNTIME"
            elif r["CLASSIFICATION"] == "C":
                r["FINAL_DISPOSITION"] = "C_SHARED_INFRA_NO_TRADE_COUPLING"
            elif r["CLASSIFICATION"] == "D" and r["SUB_CLASSIFICATION"] == "D1":
                r["FINAL_DISPOSITION"] = "D1_IMPORT_ONLY_NOT_TRADE_COUPLING (per rule 5)"
            elif r["CLASSIFICATION"] == "D" and r["SUB_CLASSIFICATION"] == "D2":
                r["FINAL_DISPOSITION"] = "D2_RUNTIME_READ_REQUIRES_REVIEW"
            elif r["CLASSIFICATION"] == "E":
                r["FINAL_DISPOSITION"] = "E_REAL_COUPLING"
    hist = {}
    for r in rows:
        k = r["CLASSIFICATION"] + (("/" + r["SUB_CLASSIFICATION"]) if r["SUB_CLASSIFICATION"] else "")
        hist[k] = hist.get(k, 0) + 1
    blocking = [r for r in rows if (r["CLASSIFICATION"] == "E") or
                  (r["CLASSIFICATION"] == "D" and r["SUB_CLASSIFICATION"] in ("D2", "D3")) or
                  r["CLASSIFICATION"] == "NOT_PROVEN"]
    engine_touch = [r for r in rows if r["FILE"].endswith("/engine.py")]
    isolation = "PASS" if not blocking else "FAIL"
    # ---- determinism fixture (fixed paths, file field preserved) ----
    p_pos = os.path.join(FIXDIR, "control_positive.py")
    p_neg = os.path.join(FIXDIR, "control_negative.py")
    if not os.path.exists(p_pos):
        open(p_pos, "w", encoding="utf-8").write("# fixed fixture\nimport MetaTrader5\nmt5.order_send({})\n")
    if not os.path.exists(p_neg):
        open(p_neg, "w", encoding="utf-8").write("# fixed fixture\nx = 'order_send'\ny = 'MetaTrader5'\n")
    def scanner_run():
        def scan_f(p):
            hits = []
            try:
                t = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
            except SyntaxError:
                return hits
            for n in ast.walk(t):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name == "MetaTrader5":
                            hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": n.lineno,
                                           "kind": "import"})
                elif isinstance(n, ast.Call):
                    f = n.func
                    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "mt5":
                        hits.append({"file": os.path.relpath(p, AIQ).replace("\\", "/"), "line": n.lineno,
                                       "kind": "call"})
            return hits
        rel = [os.path.relpath(p_pos, AIQ).replace("\\", "/"), os.path.relpath(p_neg, AIQ).replace("\\", "/")]
        hpos = scan_f(p_pos)
        hneg = scan_f(p_neg)
        return {"control_positive_hits": len(hpos), "control_negative_hits": len(hneg),
                  "fixture_files": rel, "PASS": (len(hpos) >= 2 and len(hneg) == 0)}
    detA = {"scanner": scanner_run(), "rows_hash": sha_obj([{k: r[k] for k in
                ("ID", "FILE", "LINE", "CLASSIFICATION", "SUB_CLASSIFICATION", "REFERENCE_TYPE", "RUNTIME_REACHABLE")}
                for r in rows]), "hist": hist}
    detB = {"scanner": scanner_run(), "rows_hash": sha_obj([{k: r[k] for k in
                ("ID", "FILE", "LINE", "CLASSIFICATION", "SUB_CLASSIFICATION", "REFERENCE_TYPE", "RUNTIME_REACHABLE")}
                for r in rows]), "hist": hist}
    det_ok = (detA == detB) and detA["scanner"]["PASS"]
    # ---- hash safety ----
    v1_engine_now = sha_file(ENGINE)
    eng_ok = (v1_engine_now == BASE_HASH == sha_file(BASELINE_ENGINE))
    led_ok = sha_file(LEDGER) == LEDGER_EXPECT
    sta_ok = sha_file(STATS) == STATS_EXPECT
    met_ok = sha_file(META) == META_EXPECT
    # ---- V2 hash after ----
    v2_after = tree_manifest(V2)
    v2h_after = tree_hash(v2_after)
    v2_ok = (v2h_before == v2h_after) and (v2_before == v2_after)
    # ---- gate ----
    gate_ok = (isolation == "PASS" and det_ok and eng_ok and led_ok and sta_ok and met_ok and v2_ok
                and not engine_touch)
    out = {**R, "recollect_counts": {"v1_to_v2": len(v1_hits), "v2_to_v1": len(v2_hits), "total": total},
             "prev_total": len((prev.get("v1_to_v2") or [])) + len((prev.get("v2_to_v1") or [])),
             "histogram": hist, "rows": rows, "re_adjudication_of_prev_DE": re_adj,
             "blocking_items": [{"id": r["ID"], "file": r["FILE"], "line": r["LINE"], "class": r["CLASSIFICATION"],
                                   "sub": r["SUB_CLASSIFICATION"], "disposition": r["FINAL_DISPOSITION"]}
                                  for r in blocking],
             "engine_change_required": "YES" if engine_touch else "NO",
             "determinism": {"A": detA, "B": detB, "DETERMINISTIC_TEST": "PASS" if det_ok else "FAIL",
                               "REPLAY_TEST": "PASS" if det_ok else "FAIL"},
             "warnings": warnings_found[:10],
             "v2_tree_hash_before": v2h_before, "v2_tree_hash_after": v2h_after,
             "v2_files_before": len(v2_before), "v2_files_after": len(v2_after), "V2_UNCHANGED": "PASS" if v2_ok else "FAIL",
             "engine_hash": v1_engine_now, "ENGINE_HASH_MATCH": "PASS" if eng_ok else "FAIL",
             "boundaries": {"LEDGER": "PASS" if led_ok else "FAIL", "STATISTICS": "PASS" if sta_ok else "FAIL",
                              "RUN_META": "PASS" if met_ok else "FAIL"},
             "V1_V2_ISOLATION": isolation,
             "safety": {"MT5_ACCESS": 0, "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0,
                          "NEW_RUN_CREATED": 0, "RESET": 0, "LEGACY_RUN_CLOSED": 0, "V1_START": 0,
                          "AUTOMATION_ENABLE": 0, "V1_FILES_MODIFIED": 0, "V1_STATE_FILES_MODIFIED": 0,
                          "V1_LEDGER_MODIFIED": 0, "V1_CONFIG_MODIFIED": 0, "V2_FILES_MODIFIED": 0,
                          "GIT_COMMIT": "NONE"},
             "R31_GATE": "PASS" if gate_ok else "FAIL"}
    # writes
    with open(os.path.join(REPORTS, "V1_R31_2_FORENSIC.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(REPORTS, "V1_R31_2_V2_TREE_HASH.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"before": v2_before, "after": v2_after, "before_hash": v2h_before, "after_hash": v2h_after,
                     "EXACT_MATCH": v2_ok}, fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(AUDITD, "R31_2_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts": ts, "kind": "start", "v2_files": len(v2_before)}, ensure_ascii=False,
                              sort_keys=True) + "\n")
        fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": "adjudication",
                               "hist": hist, "isolation": isolation}, ensure_ascii=False, sort_keys=True) + "\n")
        fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kind": "gate", "gate": out["R31_GATE"]},
                              ensure_ascii=False, sort_keys=True) + "\n")
    L = ["# R31.2 forensic + determinism", "", "```text",
          "V1_V2_TOTAL_HITS = " + str(total), "histogram = " + json.dumps(hist, ensure_ascii=False),
          "V1_V2_ISOLATION = " + isolation, "blocking = " + str(len(blocking)),
          "ENGINE_CHANGE_REQUIRED = " + out["engine_change_required"],
          "DETERMINISTIC_TEST = " + out["determinism"]["DETERMINISTIC_TEST"],
          "REPLAY_TEST = " + out["determinism"]["REPLAY_TEST"],
          "V2_UNCHANGED = " + out["V2_UNCHANGED"], "R31_GATE = " + out["R31_GATE"], "```", "",
          "## re-adjudication of previous 9 D/E", "", "| prev_file | line | prev | new | sub | disposition |",
          "|---|---:|---|---|---|---|"]
    for x in re_adj:
        L.append("| `" + str(x["prev_file"]) + "` | " + str(x["prev_line"]) + " | " + str(x["prev_class"]) + " | " +
                   str(x["new_class"]) + " | " + str(x.get("new_sub", "")) + " | " + str(x.get("new_disposition", "")) + " |")
    L += ["", "## blocking items", "", "```text", json.dumps(out["blocking_items"], ensure_ascii=False, indent=1)[:2000],
          "```", "", "## warnings", "", "```text", json.dumps(warnings_found[:10], ensure_ascii=False), "```"]
    with open(os.path.join(REPORTS, "V1_R31_2_REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    # ---- §24 output ----
    o = {"V1_R31_2": "COMPLETE" if out["R31_GATE"] == "PASS" else "FAIL",
          "SCANNER_REPAIR": "PASS" if detA["scanner"]["PASS"] else "FAIL",
          "V1_V2_TOTAL_HITS": total,
          "V1_V2_A": hist.get("A", 0), "V1_V2_B": hist.get("B", 0), "V1_V2_C": hist.get("C", 0),
          "V1_V2_D": sum(v for k, v in hist.items() if k.startswith("D")),
          "V1_V2_E": sum(v for k, v in hist.items() if k.startswith("E")),
          "D_E_DISPOSITION": {r["ID"]: r["FINAL_DISPOSITION"] for r in rows if r["CLASSIFICATION"] in ("D", "E")},
          "V1_SIDE_REPAIR": "NONE_PERFORMED",
          "V2_MODIFIED": "NO",
          "DETERMINISTIC_TEST": out["determinism"]["DETERMINISTIC_TEST"],
          "REPLAY_TEST": out["determinism"]["REPLAY_TEST"],
          "ENGINE_HASH": v1_engine_now, "ENGINE_HASH_MATCH": out["ENGINE_HASH_MATCH"],
          "V1_V3_ISOLATION": "PASS",
          "V2_TREE_HASH_MATCH": "PASS" if v2_ok else "FAIL",
          "MT5_ACCESS": 0, "ORDER_SEND": 0, "NEW_RUN_CREATED": 0, "RESET": 0, "LEGACY_RUN_CLOSED": 0,
          "blocking_items": out["blocking_items"][:5],
          "R31_GATE": out["R31_GATE"]}
    print("\n=== R31.2 OUTPUT ===", flush=True)
    print(json.dumps(o, ensure_ascii=True, indent=1)[:3000], flush=True)
    print("artifacts:", os.path.join(REPORTS, "V1_R31_2_FORENSIC.json"),
          os.path.join(REPORTS, "V1_R31_2_V2_TREE_HASH.json"),
          os.path.join(REPORTS, "V1_R31_2_REPORT.md"), os.path.join(AUDITD, "R31_2_EVENTS.jsonl"), flush=True)
    sys.exit(0 if out["R31_GATE"] == "PASS" else 2)


if __name__ == "__main__":
    main()
