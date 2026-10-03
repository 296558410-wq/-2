# -*- coding: utf-8 -*-
"""RLAP Phase 2 enforcement tests: research_gate / require_gate, no bypass."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.rlap_tools.gate import GateError, require_gate            # noqa: E402
from scripts.rlap_audit import sha256                                   # noqa: E402
from scripts.rlap_audit import HYP_REG                                  # noqa: E402

LEDGER = REPO / "research/registry/rlap/WINDOW_ROLE_LEDGER.yaml"
PML = REPO / "research/registry/rlap/PROGRAM_MULTIPLICITY_LEDGER.yaml"
GATE = REPO / "scripts/research_gate.py"


def write_manifest(tmp_path, wid="W3", role="descriptive", clean=True,
                   si_ids=None, model_ok=True, **kw):
    si_ids = si_ids or ["SI-TEST-1"]
    m = {
        "experiment_id": "SI-TEST-1", "phase": "TEST", "commit_sha": "test",
        "window_ids": [wid], "window_roles": {wid: role},
        "first_use_status": {wid: "clean" if clean else "reuse_context"},
        "search_intensity_ids": si_ids,
        "model_id": "none", "model_version": "n/a",
        "model_knowledge_cutoff": "2026-01-01" if model_ok else None,
        "retrieval_timestamp": "2026-09-05T12:00:00+00:00" if model_ok else None,
        "hypothesis_registry_sha": sha256(HYP_REG),
        "protocol_sha": "test",
        "window_start": "2026-05-26",
        "decision_time": "2026-09-05T12:00:00+00:00",
        "model_temporal": {
            "model_source": "open", "cutoff_verifiability": "published",
            "model_knowledge_cutoff": "2026-01-01", "release_date": "2026-01-01",
            "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
            "model_role": "analysis", "window_exposure": "none",
        },
    }
    m.update(kw)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    return p


def si_log(tmp_path, ids):
    d = tmp_path / "si"
    d.mkdir(exist_ok=True)
    (d / "log.yaml").write_text(
        "".join(f"- record_id: {i}\n" for i in ids), encoding="utf-8")
    return d


def test_gate_passes_clean_descriptive(tmp_path):
    sid = si_log(tmp_path, ["SI-TEST-1"])
    mp = write_manifest(tmp_path)
    res = require_gate(mp, si_dir=str(sid))
    assert res.hard_block() is False


def test_gate_hard_blocks_oos_on_used_window(tmp_path):
    sid = si_log(tmp_path, ["SI-TEST-1"])
    mp = write_manifest(tmp_path, wid="W4", role="oos", clean=False)
    with pytest.raises(GateError) as ei:
        require_gate(mp, si_dir=str(sid))
    assert "HARD BLOCK" in str(ei.value)


def test_gate_stops_on_unknown_window(tmp_path):
    sid = si_log(tmp_path, ["SI-TEST-1"])
    mp = write_manifest(tmp_path, wid="W999", role="descriptive")
    with pytest.raises(GateError):
        require_gate(mp, si_dir=str(sid))


def test_no_skip_flag_exists():
    """--skip/--force must NOT be accepted (no bypass path by construction)."""
    r = subprocess.run([sys.executable, str(GATE), "--manifest", "x.json",
                        "--skip"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode != 0
    assert "unrecognized" in r.stderr.lower() or "error" in r.stderr.lower()


def test_cli_gate_pass_and_stop_codes(tmp_path):
    sid = si_log(tmp_path, ["SI-TEST-1"])
    mp = write_manifest(tmp_path)  # W3 descriptive -> pass (no oos decl)
    r = subprocess.run([sys.executable, str(GATE), "--manifest", str(mp),
                        "--si-dir", str(sid)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0 and "PASS" in r.stdout
    # hard block -> exit 2
    mp2 = write_manifest(tmp_path, wid="W4", role="cross-feed", clean=False)
    r2 = subprocess.run([sys.executable, str(GATE), "--manifest", str(mp2),
                         "--si-dir", str(sid)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r2.returncode == 2 and "STOP" in r2.stdout


def test_model_temporal_never_blocks(tmp_path):
    sid = si_log(tmp_path, ["SI-TEST-1"])
    mp = write_manifest(tmp_path, model_ok=False)  # C10 fails but not hard block
    with pytest.raises(GateError) as ei:
        require_gate(mp, si_dir=str(sid))
    assert "HARD BLOCK" not in str(ei.value)
