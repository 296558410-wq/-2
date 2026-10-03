# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R5 PROBE (read-only): verify data-layer assumptions before the main scripts.
No writes anywhere. No order APIs. No rule changes."""
from __future__ import annotations

import ast
import glob
import hashlib
import importlib.util
import json
import os
import textwrap
from collections import Counter

import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
R2_PATH = os.path.join(UP, "_v1r2_phaseB_R2.py")
R1_PATH = os.path.join(UP, "_v1r2_phaseB_R1.py")
DEC = os.path.join(REPO, "research", "hermes", "trader_v1", "run_state", "decisions")
GRID = pd.Timedelta(minutes=15)


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


print("=== B4 run dir ===")
b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))
print("B4 dirs:", b4)
b4dir = b4[-1]
pq = os.path.join(b4dir, "m15_tick_bid.parquet")
df = pd.read_parquet(pq)
print("parquet cols:", list(df.columns))
print("parquet dtypes:", {c: str(df[c].dtype) for c in df.columns})
print("rows:", len(df))
print("index name:", df.index.name, "index dtype:", df.index.dtype)
print("idx min:", df.index.min(), "idx max:", df.index.max())
print("index duplicates:", int(df.index.duplicated().sum()))
cov = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
print("covered slots:", len(cov), "missing slots total:", int(len(cov) - len(df)))
# missing within decision window 09-23T23:00Z .. 09-25T16:00Z
dw0 = pd.Timestamp("2026-09-23T23:00:00Z")
dw1 = pd.Timestamp("2026-09-25T16:00:00Z")
cwdw = pd.date_range(dw0, dw1, freq="15min", tz="UTC")
bars_in_dw = df[(df.index >= dw0) & (df.index <= dw1)]
miss_in_dw = [str(x) for x in cwdw if x not in set(df.index)]
print("bars in decision window:", len(bars_in_dw), "| slots in window:", len(cwdw), "| missing in window:", len(miss_in_dw))
print("missing in window sample:", miss_in_dw[:12])
# last bars before each decision day boundary
print("last bar on 09-23:", df.index[df.index < pd.Timestamp("2026-09-24T00:00:00Z")].max())

print("\n=== B2 states (historical) ===")
b2 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B2_*")))
print("B2 dirs:", b2)
b2s = os.path.join(b2[-1], "v1_r2_states_v2.jsonl")
n = 0
first = None
last_ts = None
with open(b2s, encoding="utf-8") as fh:
    for line in fh:
        if not line.strip():
            continue
        n += 1
        if first is None:
            first = json.loads(line)
        last_ts = json.loads(line)["t"]
print("hist state rows:", n)
print("first ts:", first["t"], "last ts:", last_ts)
print("first row keys:", sorted(first.keys()))
print("next_state:", first.get("next_state"), "| direction:", first.get("direction"))

print("\n=== decisions ===")
files = sorted(os.listdir(DEC))
dec = []
for f in files:
    if not f.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(DEC, f), encoding="utf-8-sig"))
        cyc = d.get("cycle")
        t = pd.Timestamp(str(cyc).replace("Z", "+00:00"))
        t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        dec.append({"file": f, "cycle": str(cyc), "ts": t, "decision": d.get("decision"),
                      "decision_id": d.get("decision_id"), "model": d.get("model")})
    except Exception as e:  # noqa: BLE001
        dec.append({"file": f, "parse_error": str(e)})
parsed = [x for x in dec if "ts" in x]
print("total json files:", len(files), "| parsed:", len(parsed))
ts_cnt = Counter(x["ts"] for x in parsed)
dups = {k: v for k, v in ts_cnt.items() if v > 1}
print("duplicate timestamps:", {str(k): v for k, v in dups.items()})
for k, v in dups.items():
    for x in parsed:
        if x["ts"] == k:
            print("   dup file:", x["file"], "| decision_id:", x.get("decision_id"), "| model:", x.get("model"))
print("decision min:", min(x["ts"] for x in parsed), "max:", max(x["ts"] for x in parsed))
print("decision value counts:", dict(Counter(x["decision"] for x in parsed)))
print("models:", dict(Counter(x.get("model") for x in parsed)))

print("\n=== R2 module structure (original) ===")
src = open(R2_PATH, encoding="utf-8").read()
tree = ast.parse(src)
mod_fns = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
print("module-level fns:", mod_fns)
nested = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "ns_v3":
        parent = None
        for n2 in ast.walk(tree):
            if isinstance(n2, ast.FunctionDef):
                for c in ast.walk(n2):
                    if c is node and n2 is not node:
                        parent = n2.name
        nested.append({"ns_v3_in": parent, "lineno": node.lineno, "end": node.end_lineno})
print("ns_v3 definitions:", nested)
# confirm which of the four are module-level
for name in ("groups_of", "rule_mu", "rule_variant", "ns_v3"):
    in_mod = any(isinstance(n, ast.FunctionDef) and n.name == name for n in tree.body)
    print(f"  {name}: module-level={in_mod}")

print("\n=== registry v3 hash check ===")
reg3 = json.load(open(os.path.join(UP, "registry", "v1_r2_feature_registry_v3.json"), encoding="utf-8"))
def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
recomputed = sha_obj({k: v for k, v in reg3.items() if k != "new_registry_hash"})
print("stored new_registry_hash:", reg3["new_registry_hash"])
print("recomputed           :", recomputed)
print("match:", recomputed == reg3["new_registry_hash"])
print("R1 load_m15 count test follows (loading M1 parquet)...")
R1 = load_mod("v1r2_r1", R1_PATH)
h = R1.load_m15()
print("historical M15 rows:", len(h), "min:", h.index.min(), "max:", h.index.max())
print("\nPROBE DONE")
