"""
lib_common.py — shared helpers for the V2 Historical Strategy Decay Lab.

READ-ONLY / SHADOW. Nothing here writes outside the lab directory.
Every script prints: input file hashes, code commit, data sources, and an
experiment-config hash so any reported number is reproducible.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\AIQuant")
LAB = REPO / "research" / "hermes" / "trader_v2" / "V2_HISTORICAL_STRATEGY_DECAY_LAB"
DATA = LAB / "data"
SCRIPTS = LAB / "scripts"

# ---- immutable raw evidence sources (read-only) -------------------------------
SRC = {
    "v1_trade_db": REPO / "research/hermes/audit/hermes_alpha_drift_pit/V1_HERMES_TRADE_DATABASE.jsonl",
    "v2_trade_db": REPO / "research/hermes/audit/hermes_alpha_drift_pit/V2_HERMES_TRADE_DATABASE.jsonl",
    "prior_pit_audit": REPO / "research/hermes/audit/hermes_alpha_drift_pit/PIT_AUDIT.json",
    "prior_report": REPO / "research/hermes/audit/hermes_alpha_drift_pit/ALPHA_DRIFT_FORENSICS_REPORT.md",
    "v1_upgrade_ledger": REPO / "research/hermes/trader_v1/v1_upgrade/ledger/v1_upgrade_ledger.jsonl",
    "v1_upgrade_registry": REPO / "research/hermes/trader_v1/v1_upgrade/registry/v1_upgrade_registry.json",
    "v1_upgrade_runtime_config": REPO / "research/hermes/trader_v1/v1_upgrade/registry/runtime_config.json",
    "v1_upgrade_baseline_map": REPO / "research/hermes/trader_v1/v1_upgrade/registry/baseline_transition_mapping.json",
    "v1_broker_facts": REPO / "research/hermes/trader_v1/v1_upgrade/truth/evidence/broker_facts.json",
    "v1_decision_snapshots": REPO / "research/hermes/trader_v1/v1_upgrade/truth/evidence/decision_snapshots.jsonl",
    "v1_incidents": REPO / "research/hermes/trader_v1/v1_upgrade/truth/evidence/incidents.jsonl",
    "v1_run_statistics": REPO / "research/hermes/trader_v1/run_state/statistics.json",
    "v1_run_meta": REPO / "research/hermes/trader_v1/run_state/RUN_META.json",
    "v1_plan_ledger": REPO / "research/hermes/trader_v1/run_state/plan_ledger.jsonl",
    "v1_workflow_history": REPO / "research/hermes/trader_v1/run_state/workflow_history.jsonl",
    "v2_paper_account": REPO / "research/hermes/trader_v2/state/paper_account.json",
    "v2_paper_executions": REPO / "research/hermes/trader_v2/state/paper_executions.jsonl",
    "v2_ledger": REPO / "research/hermes/trader_v2/ledger/hermes_v2_ledger.jsonl",
    "v2_run_health": REPO / "research/hermes/trader_v2/state/v2_run_health.json",
    "v2_scheduler_state": REPO / "research/hermes/trader_v2/state/v2_scheduler_state.json",
    "v2_opportunity_ledger": REPO / "research/hermes/trader_v2/state/opportunity_ledger.jsonl",
    "archive_manifest": REPO / "archive/v1_pre_reset_20260923_233741/MANIFEST.json",
    "archive_code_identity": REPO / "archive/v1_pre_reset_20260923_233741/code/CODE_IDENTITY.json",
}

# frozen experiment config (hash printed by every script; must not change mid-study)
EXPERIMENT_CONFIG = {
    "study": "V2_HISTORICAL_STRATEGY_DECAY_LAB",
    "created_utc": "2026-10-03",
    "branches": {"v1_old": {"magic": 90002}, "v1_new": {"magic": 90011}},
    "age_bucket_hours": [0, 6, 12, 24, 48, 72, 120, 240],
    "bootstrap_iters": 10000,
    "permutation_iters": 10000,
    "seed": 20261003,
    "decay_horizon_hours": [12, 24, 48, 72],
    "alpha": 0.05,
    "fdr_method": "benjamini-hochberg",
    "min_effective_n": 8,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def config_hash() -> str:
    return sha256_text(json.dumps(EXPERIMENT_CONFIG, sort_keys=True))


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True,
            text=True, check=True).stdout.strip()
    except Exception as e:  # pragma: no cover
        return f"UNKNOWN({e})"


def git_branch() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(REPO),
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "UNKNOWN"


def input_hashes(keys=None) -> dict:
    keys = keys or list(SRC.keys())
    out = {}
    for k in keys:
        p = SRC[k]
        out[k] = {
            "path": str(p.relative_to(REPO)) if p.is_absolute() else str(p),
            "exists": p.exists(),
            "sha256": sha256_file(p) if p.exists() else None,
        }
    return out


def banner(name: str, sources) -> None:
    print("=" * 78)
    print(f"SCRIPT      : {name}")
    print(f"GENERATED   : {datetime.now(timezone.utc).isoformat()}")
    print(f"CODE_COMMIT : {git_commit()[:12]}  branch={git_branch()}")
    print(f"CONFIG_HASH : {config_hash()}")
    print("DATA SOURCES:")
    for k, v in input_hashes(sources).items():
        print(f"  - {k}: exists={v['exists']} sha256={(v['sha256'] or 'NA')[:16]}  {v['path']}")
    print("=" * 78)


def read_jsonl(path: Path):
    """Tolerant JSONL reader (handles mojibake by replacing bad bytes)."""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                rows.append({"__malformed__": True, "__line__": i})
    return rows


def read_json(path: Path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"wrote {path.relative_to(REPO)}  ({path.stat().st_size} bytes)")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {path.relative_to(REPO)}  ({len(rows)} rows)")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {path.relative_to(REPO)}  ({len(text)} chars)")


# ---- tiny stats helpers (no external deps) ------------------------------------
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def stdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def parse_ts(s):
    if s is None:
        return None
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def hours_between(a, b):
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 3600.0
