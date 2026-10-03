# -*- coding: utf-8 -*-
"""RLAP FINAL INTEGRATION AUDIT — end-to-end chain through real entrypoints.

Chain under test (non-bypassable):
  research kickoff -> manifest -> research_gate -> rlap_audit
  -> first-use cleanliness -> search-intensity -> program multiplicity
  -> registry SHA -> model temporal eligibility -> experiment entry
Scenarios 1-8 + no-bypass evidence. No market data; no history edits.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.rlap_audit import sha256, HYP_REG                        # noqa: E402

GATE = REPO / "scripts/research_gate.py"


def manifest(tmp_path, si_ids=("SI-I-1",), wid="W3", wrole="descriptive",
             hyp_sha=None, protocol_ok=True, si_ok=True, pml_win="W3",
             report_ok=True, mt=None, first_use_clean=True, ws="2026-05-26"):
    sid = tmp_path / "si"
    if si_ok:
        sid.mkdir(exist_ok=True)
        (sid / "log.yaml").write_text(
            "".join(f"- record_id: {i}\n" for i in si_ids), encoding="utf-8")
    pf = tmp_path / "protocol.md"
    pf.write_text("proto", encoding="utf-8")
    rep = tmp_path / "report.md"
    rep.write_text("SI-I-1" if report_ok else "no-ref", encoding="utf-8")
    mt = mt or {"model_source": "open", "cutoff_verifiability": "published",
                "model_knowledge_cutoff": "2026-01-01",
                "release_date": "2026-01-01",
                "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
                "retrieval_log": "logs/r.yaml", "window_exposure": "none",
                "model_role": "analysis"}
    m = {
        "experiment_id": "SI-I-1", "phase": "INT", "commit_sha": "x",
        "window_ids": [wid], "window_roles": {wid: wrole},
        "first_use_status": {wid: "clean" if first_use_clean else "reuse"},
        "search_intensity_ids": list(si_ids),
        "model_id": "M-I", "model_version": "1",
        "model_knowledge_cutoff": mt.get("model_knowledge_cutoff"),
        "retrieval_timestamp": mt.get("retrieval_timestamp"),
        "hypothesis_registry_sha": hyp_sha or sha256(HYP_REG),
        "protocol_sha": "bad" if not protocol_ok else sha256(pf),
        "protocol_path": str(pf),
        "report_paths": [str(rep)],
        "window_start": ws, "decision_time": "2026-09-05T12:00:00+00:00",
        "model_temporal": mt,
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(m), encoding="utf-8")
    return mp, sid


def run(mp, sid=None, extra=None):
    cmd = [sys.executable, str(GATE), "--manifest", str(mp)]
    if sid is not None:
        cmd += ["--si-dir", str(sid)]
    for k, v in (extra or {}).items():
        cmd += [k, str(v)]
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# 1. all compliant -> PASS / exit 0
def test_scenario1_all_compliant_pass(tmp_path):
    mp, sid = manifest(tmp_path)
    r = run(mp, sid)
    assert r.returncode == 0 and "RESEARCH_GATE: PASS" in r.stdout


# 2. C06 first-use violation -> HARD BLOCK / exit 2
def test_scenario2_first_use_hard_block(tmp_path):
    mp, sid = manifest(tmp_path, wid="W4", wrole="oos", first_use_clean=False)
    r = run(mp, sid)
    assert r.returncode == 2 and "HARD BLOCK" in r.stdout


# 3. C10b model temporal violation -> RQE_BLOCK / exit 3
def test_scenario3_model_temporal_rqe_block(tmp_path):
    mt = {"model_source": "closed", "cutoff_verifiability": "unverifiable",
          "model_knowledge_cutoff": None, "release_date": None,
          "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
          "model_role": "judgment"}
    mp, sid = manifest(tmp_path, mt=mt)
    r = run(mp, sid)
    assert r.returncode == 3 and "RQE_BLOCK" in r.stdout


# 4. UNKNOWN -> STOP (never downgraded to PASS)
def test_scenario4_unknown_stops(tmp_path):
    mt = {"model_source": "open", "cutoff_verifiability": "published",
          "model_knowledge_cutoff": None,   # published but cutoff unparsed -> UNKNOWN
          "release_date": "2026-01-01",
          "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
          "model_role": "analysis"}
    mp, sid = manifest(tmp_path, mt=mt)
    r = run(mp, sid)
    assert r.returncode != 0 and "STOP" in r.stdout
    assert "PASS" not in r.stdout.split("RESEARCH_GATE:")[1][:30] or \
           "RESEARCH_GATE: PASS" not in r.stdout


# 5. registry SHA mismatch -> STOP
def test_scenario5_registry_sha_mismatch(tmp_path):
    mp, sid = manifest(tmp_path, hyp_sha="0" * 64)
    r = run(mp, sid)
    assert r.returncode == 1 and "STOP" in r.stdout


# 6. missing SI -> STOP
def test_scenario6_missing_si(tmp_path):
    mp, _ = manifest(tmp_path, si_ids=("SI-I-1",))
    # si dir intentionally not created (si_ok default True -> create empty? no):
    mp2, _ = manifest(tmp_path, si_ids=("SI-MISSING",))
    r = run(mp2)  # no --si-dir => default SI_DIR (repo) lacks SI-MISSING
    assert r.returncode == 1 and "STOP" in r.stdout


# 7. missing PML -> STOP
# scenario7 needs a window in the ledger but absent from PML. The real PML now
# covers every ledger window, so we audit against a TRIMMED copy (override --pml).
def test_scenario7_missing_pml(tmp_path):
    import yaml as _y
    real = _y.safe_load(
        (REPO / "research/registry/rlap/PROGRAM_MULTIPLICITY_LEDGER.yaml")
        .read_text(encoding="utf-8"))
    trimmed = [e for e in real["entries"] if e["window"] != "W3"]
    pm = tmp_path / "pml_trimmed.yaml"
    pm.write_text(_y.safe_dump({"entries": trimmed}), encoding="utf-8")
    mp, sid = manifest(tmp_path)  # uses W3 -> missing in trimmed PML
    r = run(mp, sid, extra={"--pml": str(pm)})
    assert r.returncode == 1 and "STOP" in r.stdout


# 8. missing report SI reference -> STOP
def test_scenario8_missing_report_ref(tmp_path):
    mp, sid = manifest(tmp_path, report_ok=False)
    r = run(mp, sid)
    assert r.returncode == 1 and "STOP" in r.stdout


# special: no skip/force/bypass legitimate execution path (option registration
# check only; docstrings that mention the rule are allowed)
def test_no_bypass_flags_in_entrypoints():
    import re as _re
    for f in ("scripts/research_gate.py", "scripts/rlap_audit.py",
              "research/rlap_tools/gate.py"):
        src = (REPO / f).read_text(encoding="utf-8")
        for m in _re.finditer(r"add_argument\([^)]*\)", src):
            assert "skip" not in m.group(0), (f, m.group(0))
            assert "force" not in m.group(0), (f, m.group(0))


def test_unknown_flag_rejected():
    r = subprocess.run([sys.executable, str(GATE), "--manifest", "x",
                        "--skip"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode != 0
