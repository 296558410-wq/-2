"""
90_finalize.py — EXPERIMENT_MANIFEST.json + SHA256SUMS.txt

Hashes every artifact in the lab dir (data + scripts + narrative) and writes the
manifest. Run LAST, after all narratives exist.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import LAB, DATA, banner, git_commit, git_branch, sha256_file, write_json, config_hash

SOURCES = ["v1_trade_db", "v2_trade_db", "v1_upgrade_ledger"]


def main():
    banner("90_finalize.py", SOURCES)
    artifacts = []
    for p in sorted(LAB.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(LAB)).replace("\\", "/")
        if rel.startswith("__pycache__") or rel.endswith(".pyc"):
            continue
        if p.name in ("SHA256SUMS.txt", "EXPERIMENT_MANIFEST.json"):
            continue
        artifacts.append({"path": rel, "size": p.stat().st_size, "sha256": sha256_file(p)})

    manifest = {
        "schema": "experiment_manifest/1",
        "study": "V2_HISTORICAL_STRATEGY_DECAY_LAB",
        "generated_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "code_commit": git_commit(),
        "git_branch": git_branch(),
        "experiment_config_hash": config_hash(),
        "artifacts": artifacts,
        "n_artifacts": len(artifacts),
        "scripts": [a["path"] for a in artifacts if a["path"].startswith("scripts/")],
        "data": [a["path"] for a in artifacts if a["path"].startswith("data/")],
    }
    write_json(LAB / "EXPERIMENT_MANIFEST.json", manifest)

    lines = []
    for a in artifacts + [{"path": "EXPERIMENT_MANIFEST.json",
                           "sha256": sha256_file(LAB / "EXPERIMENT_MANIFEST.json")}]:
        lines.append(f"{a['sha256']}  {a['path']}")
    with open(LAB / "SHA256SUMS.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nwrote {LAB / 'SHA256SUMS.txt'} ({len(lines)} entries)")
    print(f"Artifacts : {len(artifacts)}")
    print(f"Scripts   : {len(manifest['scripts'])}")
    print(f"Data      : {len(manifest['data'])}")


if __name__ == "__main__":
    main()
