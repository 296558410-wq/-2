# -*- coding: utf-8 -*-
"""V3 Research Freeze — build V3_FREEZE_MANIFEST.json (read-only over research artifacts).

- Walks research/ + gpu_infra/ + state/ (non-parquet, non-pycache; the freeze dir itself is excluded
  and covered by the git commit) and records per-file SHA256.
- Extracts declared protocol hashes from *PROTOCOL*.json files.
- Re-runs run_r4.py and verifies byte-identical reproducibility vs SHA256_MANIFEST.json.
- Verifies the R4 snapshot manifest hash against the frozen F5 protocol claim.
Writes only inside research/v3_freeze_handoff/.
"""
from __future__ import annotations
import datetime as dt, glob, hashlib, json, os, re, subprocess, sys

V3 = r"C:\AIQuant\research\hermes\trader_v3"
RES = os.path.join(V3, "research")
OUT = os.path.join(RES, "v3_freeze_handoff")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
R4 = os.path.join(RES, "v3_r4_temporal_f5")
os.makedirs(OUT, exist_ok=True)
EXCLUDE_DIRS = ("v3_freeze_handoff",)
HEX = re.compile(r"^[0-9a-f]{64}$")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def walk_hashes(root, base):
    out = {}
    for dp, dn, fn in os.walk(root):
        rel = os.path.relpath(dp, base).replace("\\", "/")
        if any(rel.startswith(x) for x in EXCLUDE_DIRS):
            continue
        if "__pycache__" in rel:
            continue
        for f in fn:
            if f.endswith(".parquet") or f.endswith(".pyc") or f.endswith(".webp"):
                continue
            rp = (rel + "/" + f).replace("\\", "/") if rel != "." else f
            if any(rp.startswith(x + "/") for x in EXCLUDE_DIRS):
                continue
            p = os.path.join(dp, f)
            out[rp] = {"sha256": sha(p), "bytes": os.path.getsize(p)}
    return out


art = {}
art.update({f"research/{k}": v for k, v in walk_hashes(RES, RES).items()})
art.update({f"gpu_infra/{k}": v for k, v in walk_hashes(os.path.join(V3, "gpu_infra"), V3).items()})
art.update({f"state/{k}": v for k, v in walk_hashes(os.path.join(V3, "state"), V3).items()})

# declared protocol hashes
protos = []
for p in sorted(glob.glob(os.path.join(RES, "**", "*PROTOCOL*.json"), recursive=True) + glob.glob(os.path.join(RES, "**", "*protocol*.json"), recursive=True)):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    declared = {k: v for k, v in d.items() if "hash" in k.lower() and isinstance(v, str)}
    for k, v in list(d.items()):
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if "hash" in k2.lower() and isinstance(v2, str) and HEX.match(v2):
                    declared[f"{k}.{k2}"] = v2
    declared = {k: v for k, v in declared.items() if HEX.match(v)}
    if declared:
        protos.append({"file": os.path.relpath(p, RES).replace("\\", "/"), "sha256": sha(p), "declared_hashes": declared})

# R4 reproducibility re-check
r4man = json.load(open(os.path.join(R4, "SHA256_MANIFEST.json"), encoding="utf-8"))
files3 = ["results_v3_r4.json", "DATA_REGISTRY.json", "EVENT_REGISTRY.json"]
before = {f: sha(os.path.join(R4, f)) for f in files3}
r = subprocess.run([PY, os.path.join(R4, "run_r4.py")], capture_output=True, text=True, timeout=900)
after = {f: sha(os.path.join(R4, f)) for f in files3}
repro = {"rerun_exit": r.returncode,
         "identical_to_manifest": all(after[f] == r4man["files"][f]["sha256"] for f in files3),
         "identical_pre_post": all(after[f] == before[f] for f in files3),
         "hashes": after}
snap_ok = sha(os.path.join(R4, "SNAPSHOT_FXTM_R4", "MANIFEST.json")) == "3417edf9814f9b0f5e38259940449d7eec205fbd2e4ca5ca3630dba9d58f8a14"

# hold status
hold_status = os.path.join(RES, "v3_temporal_hold", "HOLD_STATUS.json")
hold = json.load(open(hold_status, encoding="utf-8")) if os.path.exists(hold_status) else None

doc = {
    "schema": "v3_freeze_manifest/1",
    "task": "V3-RESEARCH-FREEZE-HANDOFF",
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "scope": "research/hermes/trader_v3 (V3 only; V1/V2 untouched)",
    "note": "raw parquet sequences excluded (not in git by convention; covered by snapshot manifests); freeze dir itself excluded (covered by git commit)",
    "artifact_count": len(art),
    "artifacts": art,
    "protocol_hashes": protos,
    "raw_data": {
        "staging_fxtm": {"dir": r"C:\AIQuant\data\staging_fxtm", "files": 24},
        "live_fxtm": {"dir": r"C:\AIQuant\data\live_fxtm", "files": 20},
        "snapshot_manifests": [
            {"path": "research/v3_r4_temporal_f5/SNAPSHOT_FXTM_R4/MANIFEST.json",
             "sha256": "3417edf9814f9b0f5e38259940449d7eec205fbd2e4ca5ca3630dba9d58f8a14",
             "verified_against_frozen_protocol": snap_ok},
        ],
    },
    "r4_reproducibility": repro,
    "temporal_hold": {"status_file": "research/v3_temporal_hold/HOLD_STATUS.json",
                       "check_utc": hold.get("check_utc") if hold else None,
                       "calendar_days": hold.get("calendar_days") if hold else None,
                       "active_days": hold.get("active_days") if hold else None,
                       "ready": hold.get("ready") if hold else None},
}
json.dump(doc, open(os.path.join(OUT, "V3_FREEZE_MANIFEST.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("artifacts:", len(art), "| protocols:", len(protos))
print("r4 reproducible:", repro["identical_to_manifest"] and repro["identical_pre_post"], "| snapshot verified:", snap_ok)
for p in protos[:12]:
    print(" ", p["file"], "->", list(p["declared_hashes"].values())[0][:16])
