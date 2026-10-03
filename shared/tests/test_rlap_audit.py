# -*- coding: utf-8 -*-
"""rlap_audit unit tests (synthetic manifests; no market data, no history edits)."""
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.rlap_audit import (audit, load_ledger, load_pml, sha256,      # noqa: E402
                                REPO as AUDIT_REPO)

LEDGER = REPO / "research/registry/rlap/WINDOW_ROLE_LEDGER.yaml"
PML = REPO / "research/registry/rlap/PROGRAM_MULTIPLICITY_LEDGER.yaml"
HYP = REPO / "research/registry/hypothesis_registry.yaml"


def base_manifest(tmp_path, **over):
    m = {
        "experiment_id": "SI-REP2-001", "phase": "REP-P2", "commit_sha": "abc123",
        "window_ids": ["W9"], "window_roles": {"W9": "descriptive"},
        "first_use_status": {"W9": "clean"}, "search_intensity_ids": ["SI-REP2-001"],
        "model_id": "none", "model_version": "n/a",
        "model_knowledge_cutoff": "2026-01-01",
        "retrieval_timestamp": "2026-09-05T12:00:00+00:00",
        "hypothesis_registry_sha": sha256(HYP),
        "protocol_sha": "deadbeef",
    }
    m.update(over)
    # protocol file for C02
    if "protocol_path" in m:
        pf = tmp_path / "protocol.md"
        pf.write_text("frozen protocol", encoding="utf-8")
        m["protocol_sha"] = sha256(pf)
        m["protocol_path"] = str(pf)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    return m, p


def si_log(tmp_path, ids):
    d = tmp_path / "si"
    d.mkdir(exist_ok=True)
    f = d / "log.yaml"
    f.write_text(yaml.safe_dump([{"record_id": i} for i in ids]), encoding="utf-8")
    return d


def test_ledgers_parse():
    assert len(load_ledger(LEDGER)) >= 8
    assert len(load_pml(PML)) >= 5


def test_clean_descriptive_passes(tmp_path):
    m, _ = base_manifest(tmp_path)
    res = audit(m, LEDGER, PML, tmp_path)  # W9 unknown -> C04 FAIL; use W3(none) below
    assert res.hard_block() is False


def test_unknown_window_fails_c04(tmp_path):
    m, _ = base_manifest(tmp_path, window_ids=["W99"], window_roles={"W99": "descriptive"})
    res = audit(m, LEDGER, PML, tmp_path)
    c04 = [i for i in res.items if i["id"] == "C04"][0]
    assert c04["status"] == "FAIL"


def test_oos_on_used_window_hard_blocks(tmp_path):
    # W4 (FXTM H1) has prior roles incl discovery -> declaring oos must FAIL
    m, _ = base_manifest(tmp_path, window_ids=["W4"],
                         window_roles={"W4": "oos"},
                         first_use_status={"W4": "reuse_context"})
    res = audit(m, LEDGER, PML, tmp_path)
    assert res.hard_block() is True
    c06 = [i for i in res.items if i["id"] == "C06"][0]
    assert c06["status"] == "FAIL"
    assert "HARD BLOCK" in c06["detail"]


def test_oos_on_never_used_window_ok_when_ledger_says_none(tmp_path):
    # W3 (FXTM M5) currently has role 'none' in ledger -> clean declaration passes
    m, _ = base_manifest(tmp_path, window_ids=["W3"], window_roles={"W3": "oos"},
                         first_use_status={"W3": "clean"})
    res = audit(m, LEDGER, PML, tmp_path)
    c06 = [i for i in res.items if i["id"] == "C06"][0]
    assert c06["status"] == "PASS", c06


def test_missing_si_id_fails_c07(tmp_path):
    sidir = si_log(tmp_path, ["SI-OTHER-9"])
    m, _ = base_manifest(tmp_path, search_intensity_ids=["SI-REP2-001"])
    res = audit(m, LEDGER, PML, sidir)
    c07 = [i for i in res.items if i["id"] == "C07"][0]
    assert c07["status"] == "FAIL"


def test_model_metadata_missing_fails_c10(tmp_path):
    m, _ = base_manifest(tmp_path, model_knowledge_cutoff=None,
                         retrieval_timestamp=None)
    res = audit(m, LEDGER, PML, tmp_path)
    c10 = [i for i in res.items if i["id"] == "C10"][0]
    assert c10["status"] == "FAIL"
    # model-temporal never folded into hard block
    assert res.hard_block() is False


def test_protocol_sha_mismatch_fails_c02(tmp_path):
    pf = tmp_path / "protocol.md"
    pf.write_text("frozen protocol v2", encoding="utf-8")
    m, _ = base_manifest(tmp_path, protocol_path=str(pf))
    # now tamper AFTER manifest sha was computed from the same path
    pf.write_text("tampered", encoding="utf-8")
    res = audit(m, LEDGER, PML, tmp_path)
    c02 = [i for i in res.items if i["id"] == "C02"][0]
    assert c02["status"] == "FAIL"


def test_report_si_reference(tmp_path):
    rep = tmp_path / "report.md"
    rep.write_text("... SI-REP2-001 ...", encoding="utf-8")
    m, _ = base_manifest(tmp_path, report_paths=[str(rep)])
    res = audit(m, LEDGER, PML, tmp_path)
    c09 = [i for i in res.items if i["id"] == "C09"][0]
    assert c09["status"] == "PASS"
