# -*- coding: utf-8 -*-
"""rlap_audit — programmatic Research Leakage Audit (RLAP Phase 1.5).

Converts RLAP P1-P5 ledgers & governance into an executable, blocking audit.
Checks (per adjudication 2026-09-05 21:40):
  1 experiment manifest exists           6 first-use-cleanliness (HARD BLOCK)
  2 protocol SHA frozen                  7 search-intensity IDs exist
  3 registry SHA frozen                  8 program multiplicity registered
  4 window IDs exist                     9 report references SI ID
  5 window role history exists           10 model metadata complete

Hard-block rule: any future OOS / cross-period / cross-feed declaration whose
first-use-cleanliness is not satisfied => program FAIL (exit 2). No text
explanation may bypass. UNKNOWN stays UNKNOWN (never guessed).

model_knowledge_cutoff is an INDEPENDENT Model Temporal Contamination domain:
reported separately (model_temporal), never merged into the leakage verdict.

No historical results are read or modified; forward-facing only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WRL = REPO / "research/registry/rlap/WINDOW_ROLE_LEDGER.yaml"
PML = REPO / "research/registry/rlap/PROGRAM_MULTIPLICITY_LEDGER.yaml"
SI_DIR = REPO / "research/registry/rlap/search_intensity_log"
HYP_REG = REPO / "research/registry/hypothesis_registry.yaml"

# Roles that make a window non-clean for a later oos/cross declaration.
# ANY prior usage (incl. descriptive) spends first-use per P2 spec §1 strict
# reading: clean OOS requires a window with no earlier role other than none/
# synthetic. Descriptive-only history => reason DESIGN_CONTEXT (still FAIL).
BLOCKED_PRIOR_ROLES = {"discovery", "selection", "fit", "validation", "oos",
                       "cross", "descriptive"}
OOS_CROSS_ROLES = {"oos", "cross-period", "cross-feed", "cross"}

REQUIRED_MANIFEST_FIELDS = [
    "experiment_id", "phase", "commit_sha", "window_ids", "window_roles",
    "first_use_status", "search_intensity_ids", "model_id", "model_version",
    "model_knowledge_cutoff", "retrieval_timestamp", "hypothesis_registry_sha",
    "protocol_sha",
]
# protocol_path & report_paths are optional-but-recommended (needed for checks
# 2 and 9); their absence is reported as WARN when the corresponding check
# cannot run.


class AuditResult:
    def __init__(self):
        self.items = []  # {id, name, status: PASS|FAIL|WARN|UNKNOWN, detail}

    def add(self, cid, name, status, detail):
        self.items.append({"id": cid, "name": name, "status": status,
                           "detail": detail})
        return status

    def hard_block(self):
        return any(i["id"] == "C06" and i["status"] == "FAIL" for i in self.items)

    def rqe_block(self):
        return any(i["id"] == "C10b" and i["status"] == "FAIL" for i in self.items)

    def any_fail(self):
        return any(i["status"] == "FAIL" for i in self.items)

    def to_dict(self):
        return {"items": self.items,
                "hard_block": self.hard_block(),
                "model_temporal": {"domain": "independent",
                                   "note": "model_knowledge_cutoff is Model "
                                           "Temporal Contamination; never "
                                           "merged into leakage verdict"}}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_ledger(path: Path = WRL) -> dict:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {w["id"]: w for w in d["windows"]}


def load_pml(path: Path = PML) -> dict:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {e["window"]: e for e in d["entries"]}


def prior_roles(ledger: dict, wid: str) -> list[str]:
    w = ledger.get(wid)
    if not w:
        return []
    out = []
    for r in w.get("roles", []):
        rl = str(r.get("role", ""))
        out.append(rl)
    return out


def _earliest_window_start(window_ids, ledger):
    import re  # noqa: PLC0415
    starts = []
    for wid in window_ids or []:
        w = ledger.get(wid)
        if not w:
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(w.get("span", "")))
        if m:
            starts.append(m.group(1))
    return min(starts) if starts else None


def audit(manifest: dict, ledger_path: Path = WRL, pml_path: Path = PML,
          si_dir: Path = SI_DIR) -> AuditResult:
    res = AuditResult()
    # C01 manifest exists & fields present
    missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in manifest]
    if missing:
        res.add("C01", "manifest fields", "FAIL",
                f"missing fields: {missing}")
    else:
        res.add("C01", "manifest fields", "PASS", "all 13 standard fields present")
    # C02 protocol SHA frozen (needs protocol_path)
    pp = manifest.get("protocol_path")
    if not pp:
        res.add("C02", "protocol SHA frozen", "WARN",
                "protocol_path absent -> cannot verify (field optional-recommended)")
    else:
        pf = Path(pp) if Path(pp).is_absolute() else REPO / pp
        if not pf.exists():
            res.add("C02", "protocol SHA frozen", "FAIL",
                    f"protocol file not found: {pp}")
        elif sha256(pf) != manifest.get("protocol_sha"):
            res.add("C02", "protocol SHA frozen", "FAIL",
                    "manifest.protocol_sha does not match file sha256")
        else:
            res.add("C02", "protocol SHA frozen", "PASS", "sha matches")
    # C03 registry SHA frozen
    if HYP_REG.exists():
        cur = sha256(HYP_REG)
        if manifest.get("hypothesis_registry_sha") != cur:
            res.add("C03", "registry SHA frozen", "FAIL",
                    "hypothesis_registry_sha mismatch (declared vs file)")
        else:
            res.add("C03", "registry SHA frozen", "PASS", "sha matches")
    else:
        res.add("C03", "registry SHA frozen", "FAIL",
                "registry file missing (UNKNOWN state -> block: never downgraded to PASS)")
    # C04 window IDs exist
    ledger = load_ledger(ledger_path)
    unknown_w = [w for w in manifest.get("window_ids", []) if w not in ledger]
    if unknown_w:
        res.add("C04", "window IDs exist", "FAIL",
                f"not in WINDOW_ROLE_LEDGER: {unknown_w} (register first)")
    else:
        res.add("C04", "window IDs exist", "PASS", "all window_ids in ledger")
    # C05 window role history exists
    bad = []
    for w in manifest.get("window_ids", []):
        if w not in ledger:
            bad.append(f"{w}:no-entry")
            continue
        roles = ledger[w].get("roles", [])
        if not roles:
            bad.append(f"{w}:empty-role-history")
    if bad:
        res.add("C05", "window role history", "FAIL", f"{bad}")
    else:
        res.add("C05", "window role history", "PASS", "role history present")
    # C06 first-use-cleanliness (HARD BLOCK for oos/cross)
    hard = []
    for wid, role in manifest.get("window_roles", {}).items():
        norm = str(role).lower()
        if norm in OOS_CROSS_ROLES:
            prior = prior_roles(ledger, wid)
            used = [r for r in prior if any(k in r for k in BLOCKED_PRIOR_ROLES)]
            if wid not in ledger:
                hard.append(f"{wid}:not-registered")
            elif used:
                hard.append(f"{wid}:prior-usage={used}")
            else:
                hard.append(f"{wid}:NO-PRIOR-USE(clean)")
    if hard:
        fails = [h for h in hard if not h.endswith("(clean)")]
        if fails:
            res.add("C06", "first-use-cleanliness", "FAIL",
                    f"HARD BLOCK (no text bypass allowed): {fails}")
        else:
            res.add("C06", "first-use-cleanliness", "PASS",
                    "declared oos/cross windows clean")
    else:
        res.add("C06", "first-use-cleanliness", "PASS",
                "no oos/cross declaration in this manifest")
    # C07 search-intensity IDs exist
    si_ids = manifest.get("search_intensity_ids", [])
    if not si_ids:
        res.add("C07", "search-intensity IDs", "FAIL", "empty search_intensity_ids")
    else:
        found = set()
        if si_dir.exists():
            for f in si_dir.glob("*.yaml"):
                try:
                    d = yaml.safe_load(f.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(d, list):
                    found |= {r.get("record_id") for r in d if isinstance(r, dict)}
        missing_si = [i for i in si_ids if i not in found]
        if missing_si:
            res.add("C07", "search-intensity IDs", "FAIL",
                    f"not found in SI log: {missing_si}")
        else:
            res.add("C07", "search-intensity IDs", "PASS", "all SI ids logged")
    # C08 program multiplicity registered (PML entry per window+scale)
    pml = load_pml(pml_path)
    bad8 = [w for w in manifest.get("window_ids", []) if w not in pml]
    if bad8:
        res.add("C08", "program multiplicity", "FAIL",
                f"no PML entry for windows: {bad8}")
    else:
        res.add("C08", "program multiplicity", "PASS", "PML entries present")
    # C09 report references SI ID
    reps = manifest.get("report_paths", [])
    if not reps:
        res.add("C09", "report references SI ID", "WARN",
                "report_paths absent -> not verifiable")
    else:
        miss9 = []
        for rp in reps:
            rf = Path(rp) if Path(rp).is_absolute() else REPO / rp
            if not rf.exists():
                miss9.append(f"{rp}:missing")
                continue
            txt = rf.read_text(encoding="utf-8", errors="ignore")
            for sid in si_ids:
                if sid not in txt:
                    miss9.append(f"{rp}:missing-ref-{sid}")
        if miss9:
            res.add("C09", "report references SI ID", "FAIL", f"{miss9[:6]}")
        else:
            res.add("C09", "report references SI ID", "PASS", "all SI ids referenced")
    # C10 model metadata complete (+ separate model_temporal note)
    mm_bad = []
    for fld in ("model_id", "model_version", "retrieval_timestamp"):
        v = manifest.get(fld)
        if not v:
            mm_bad.append(f"{fld}:missing")
    mt_cv = ""
    mt_block = manifest.get("model_temporal")
    if isinstance(mt_block, dict):
        mt_cv = str(mt_block.get("cutoff_verifiability", "")).lower()
    cutoff = manifest.get("model_knowledge_cutoff")
    if not cutoff and mt_cv != "unverifiable":
        mm_bad.append("model_knowledge_cutoff:missing (or declare unverifiable)")
    retr = manifest.get("retrieval_timestamp", "")
    try:
        _dt.datetime.fromisoformat(str(retr).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        mm_bad.append("retrieval_timestamp:not-ISO")
    if cutoff:
        try:
            _dt.datetime.fromisoformat(str(cutoff).replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            mm_bad.append("model_knowledge_cutoff:not-ISO")
    if mm_bad:
        res.add("C10", "model metadata complete", "FAIL", f"{mm_bad}")
    else:
        res.add("C10", "model metadata complete", "PASS",
                "model fields complete (cutoff tracked as Model Temporal "
                "Contamination domain, separate from leakage)")
    # C10b model temporal eligibility (RQ-08; independent domain; exit RQE_BLOCK=3)
    from scripts.model_temporal_gate import verdict as _mtv  # noqa: PLC0415
    mt = manifest.get("model_temporal")
    if not isinstance(mt, dict):
        res.add("C10b", "model temporal eligibility", "FAIL",
                "model_temporal block missing (must declare)")
    else:
        ws = manifest.get("window_start")
        if not ws:
            ws = _earliest_window_start(manifest.get("window_ids", []), ledger)
        dt = manifest.get("decision_time") or mt.get("retrieval_timestamp")
        v = _mtv(mt, ws, dt)
        role = str(mt.get("model_role", ""))
        if v["verdict"] in ("UNKNOWN", "INELIGIBLE") and role in \
                ("hypothesis_design", "judgment"):
            res.add("C10b", "model temporal eligibility", "FAIL",
                    f"RQE_BLOCK: verdict={v['verdict']} role={role} "
                    f"detail={v['detail']}")
        elif v["verdict"] == "UNKNOWN":
            # UNKNOWN must never downgrade to PASS (any role)
            res.add("C10b", "model temporal eligibility", "FAIL",
                    f"UNKNOWN-block: verdict=UNKNOWN role={role} "
                    f"detail={v['detail']}")
        elif v["verdict"] == "INELIGIBLE" and role not in \
                ("hypothesis_design", "judgment"):
            res.add("C10b", "model temporal eligibility", "FAIL",
                    f"INELIGIBLE-block: verdict=INELIGIBLE role={role}")
        else:
            res.add("C10b", "model temporal eligibility", "PASS",
                    f"verdict={v['verdict']} role={role} flags={v['flags']}")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="rlap_audit")
    ap.add_argument("--manifest", default=None, help="experiment manifest json/yaml")
    ap.add_argument("--ledger", default=str(WRL))
    ap.add_argument("--pml", default=str(PML))
    ap.add_argument("--si-dir", default=str(SI_DIR))
    ap.add_argument("--selfcheck", action="store_true",
                    help="repo invariants: ledgers parse; print registry sha")
    a = ap.parse_args(argv)
    if a.selfcheck:
        ld = load_ledger(Path(a.ledger))
        pm = load_pml(Path(a.pml))
        print(json.dumps({"windows": sorted(ld), "pml_entries": sorted(pm),
                          "hypothesis_registry_sha": sha256(HYP_REG)},
                         indent=1))
        return 0
    if not a.manifest:
        ap.error("--manifest is required unless --selfcheck is used")
        return 1
    mp = Path(a.manifest)
    if not mp.exists():
        print(json.dumps({"error": "manifest not found", "manifest": a.manifest}))
        return 1
    try:
        man = yaml.safe_load(mp.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"manifest parse failed: {exc!r}"}))
        return 1
    res = audit(man, Path(a.ledger), Path(a.pml), Path(a.si_dir))
    out = res.to_dict()
    out["experiment_id"] = man.get("experiment_id")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if res.rqe_block():
        return 3   # RQE_BLOCK: model temporal ineligibility (independent domain)
    if res.hard_block():
        return 2
    if res.any_fail():
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
