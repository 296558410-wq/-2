# -*- coding: utf-8 -*-
"""manifest.py — evidence_manifest.json for v1_restart_behavior_forensics (READ-ONLY)."""
import hashlib, os, json, datetime as dt
REPO = r"C:\AIQuant"; BASE = os.path.join(REPO, "research", "hermes", "trader_v1"); UP = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_restart_behavior_forensics")
WS = r"C:\Users\surface\.openclaw\workspace"
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
srcs = [
 ("workspace/_cycle.py.backup_20260930_073745 (V0 cycle.py, mtime 09-28T15:34:50Z)", os.path.join(WS, "_cycle.py.backup_20260930_073745")),
 ("v1_upgrade/backup/20261002T034821Z/cycle.py (V2, mtime 10-01T14:33:19Z)", os.path.join(UP, "backup", "20261002T034821Z", "cycle.py")),
 ("v1_upgrade/cycle.py (current V5)", os.path.join(UP, "cycle.py")),
 ("v1_upgrade/gates.py (current)", os.path.join(UP, "gates.py")),
 ("v1_upgrade/label_adapter.py", os.path.join(UP, "label_adapter.py")),
 ("v1_upgrade/ledger/v1_upgrade_ledger.jsonl", os.path.join(UP, "ledger", "v1_upgrade_ledger.jsonl")),
 ("v1_r2_full_optimization/states/state_v2_series.parquet", os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")),
 ("v3_alpha_discovery_r1/xauusd_m1_histdata.parquet", os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")),
]
man = {"schema": "v1_restart_evidence_manifest/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "boundaries": {"order_send": 0, "modified": "none", "mode": "read-only"},
       "recovered_cycle_py_versions": {
         "V0_20260928_baseline":  {"sha256": sha(os.path.join(WS, "_cycle.py.backup_20260930_073745")), "bytes": 15946},
         "V2_20261001_1433_pre_fix": {"sha256": "dcb7edde220cfe07be93c72cda1fa55ae48ed71316b384a38c1898d7161b523b", "bytes": 19909},
         "V3_20261002_63d5a22": {"sha256": "a98d8d0eed4d6c08d5c98b58578b13e5b3cf6dbd3a5eee6a2b5f0b9a2b8cfe15", "git_blob": "565a74c04b8ef74534287dda36eafd00d707fb6e", "bytes": 20895},
         "V4_20261002_eceeec2": {"sha256": "2d8f50d52cbb67d9", "git_blob": "fcc686251b0f683c55b739fa6dc1454476ffd00b", "bytes": 23483},
         "V5_20261002_current": {"sha256": "0ed44fb8fe654ea04904c16ffbfc527bf3b620f2c3a192e94cfb848c6e6f9ef8", "git_blob": "ea2a0fa350cd1f86fce183d1f560ca1845f47dff", "bytes": 26864}},
       "sources": [{"path": p, "sha256": sha(p)} for _, p in srcs]}
json.dump(man, open(os.path.join(OUT, "evidence_manifest.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(man["recovered_cycle_py_versions"], ensure_ascii=False, indent=1))
print("manifest written; m1/state hashes:", [s["sha256"][:12] if s["sha256"] else None for s in man["sources"][-2:]])
