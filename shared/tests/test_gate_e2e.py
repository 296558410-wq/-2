# -*- coding: utf-8 -*-
"""End-to-end: research_gate exit codes incl. RQE_BLOCK=3 (C10b)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.rlap_audit import sha256, HYP_REG                        # noqa: E402

GATE = REPO / "scripts/research_gate.py"


def build(tmp_path, model_temporal, role_top="judgment", wid="W3",
          wrole="descriptive"):
    sid = tmp_path / "si"
    sid.mkdir(exist_ok=True)
    (sid / "log.yaml").write_text("- record_id: SI-E2E-1\n", encoding="utf-8")
    pf = tmp_path / "protocol.md"
    pf.write_text("proto", encoding="utf-8")
    rep = tmp_path / "report.md"
    rep.write_text("SI-E2E-1", encoding="utf-8")
    m = {
        "experiment_id": "SI-E2E-1", "phase": "TEST", "commit_sha": "x",
        "window_ids": [wid], "window_roles": {wid: wrole},
        "first_use_status": {wid: "clean"}, "search_intensity_ids": ["SI-E2E-1"],
        "model_id": "M-T", "model_version": "1",
        "model_knowledge_cutoff": model_temporal.get("model_knowledge_cutoff"),
        "retrieval_timestamp": model_temporal.get("retrieval_timestamp"),
        "hypothesis_registry_sha": sha256(HYP_REG),
        "protocol_sha": sha256(pf), "protocol_path": str(pf),
        "report_paths": [str(rep)],
        "window_start": "2026-05-26", "decision_time": "2026-09-05T12:00:00+00:00",
        "model_temporal": dict(model_temporal, model_role=role_top),
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(m), encoding="utf-8")
    return mp, sid


def run(mp, sid):
    return subprocess.run([sys.executable, str(GATE), "--manifest", str(mp),
                           "--si-dir", str(sid)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def test_gate_rqe_block_exit3(tmp_path):
    mt = {"model_source": "closed", "cutoff_verifiability": "unverifiable",
          "model_knowledge_cutoff": None, "release_date": None,
          "retrieval_timestamp": "2026-09-05T10:00:00+00:00"}
    mp, sid = build(tmp_path, mt, role_top="judgment")
    r = run(mp, sid)
    assert r.returncode == 3, r.stdout
    assert "RQE_BLOCK" in r.stdout


def test_gate_full_pass_exit0(tmp_path):
    mt = {"model_source": "open", "cutoff_verifiability": "published",
          "model_knowledge_cutoff": "2026-01-01", "release_date": "2026-01-01",
          "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
          "retrieval_log": "logs/r.yaml", "window_exposure": "none"}
    mp, sid = build(tmp_path, mt, role_top="hypothesis_design")
    r = run(mp, sid)
    assert r.returncode == 0, r.stdout
    assert "RESEARCH_GATE: PASS" in r.stdout
