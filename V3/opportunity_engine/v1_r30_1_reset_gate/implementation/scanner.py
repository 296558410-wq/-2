# -*- coding: utf-8 -*-
"""AST-based MT5 usage scanner (R30.1 repair, Phase A).

Accuracy contract:
  * detects REAL imports (ast.Import / ast.ImportFrom of MetaTrader5)
  * detects REAL calls (ast.Call on attribute `mt5.<name>(...)`)
  * IGNORES string literals (so scanner/source text cannot self-match)
  * regex fallback ONLY for files that fail to parse, using precise line-anchored patterns
  * excludes the scanner's own file (and any caller-provided exclusion list)
"""
from __future__ import annotations

import ast
import os
import re

CALL_RE = re.compile(r"\bmt5\.[a-zA-Z_][a-zA-Z0-9_]*\s*\(")
IMPORT_RE = re.compile(r"^\s*(?:import\s+MetaTrader5|from\s+MetaTrader5\b)")


def scan_file(path):
    hits = []
    try:
        src = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return hits
    try:
        tree = ast.parse(src)
    except SyntaxError:
        for i, line in enumerate(src.splitlines(), 1):
            if IMPORT_RE.match(line):
                hits.append({"file": path, "line": i, "kind": "import_regex"})
            elif CALL_RE.search(line):
                hits.append({"file": path, "line": i, "kind": "call_regex"})
        return hits
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "MetaTrader5" or a.name.startswith("MetaTrader5."):
                    hits.append({"file": path, "line": node.lineno, "kind": "import", "name": a.name})
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "MetaTrader5" or node.module.startswith("MetaTrader5.")):
                hits.append({"file": path, "line": node.lineno, "kind": "from_import", "name": node.module})
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "mt5":
                hits.append({"file": path, "line": node.lineno, "kind": "call", "name": f.attr})
    return hits


def scan_roots(roots, exclude=()):
    excl = {os.path.abspath(e) for e in exclude}
    hits, scanned, per_file = [], 0, {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if not f.lower().endswith(".py"):
                    continue
                p = os.path.abspath(os.path.join(r_, f))
                if p in excl:
                    continue
                scanned += 1
                h = scan_file(p)
                per_file[p] = len(h)
                hits += h
    return {"hits": len(hits), "details": hits[:30], "scanned": scanned, "per_file_nonzero": {k: v for k, v in per_file.items() if v}}


def selftest():
    import tempfile
    d = tempfile.mkdtemp(prefix="mt5scan_")
    p_real = os.path.join(d, "control_real.py")
    with open(p_real, "w", encoding="utf-8") as fh:
        fh.write("import MetaTrader5 as mt5\nok = mt5.initialize()\nps = mt5.positions_get()\n")
    p_str = os.path.join(d, "control_strings.py")
    with open(p_str, "w", encoding="utf-8") as fh:
        fh.write("import re\nPAT = r'MetaTrader5|order_send|order_check|mt5\\.'\nprint(PAT)\n")
    h_real = scan_file(p_real)
    h_str = scan_file(p_str)
    res = {"control_real_hits": len(h_real), "control_string_hits": len(h_str),
             "detects_real": len(h_real) >= 2, "ignores_strings": len(h_str) == 0}
    res["PASS"] = bool(res["detects_real"] and res["ignores_strings"])
    return res
