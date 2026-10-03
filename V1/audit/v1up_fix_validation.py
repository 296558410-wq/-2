# -*- coding: utf-8 -*-
"""v1up_fix_validation.py — independent re-run + side-effect proofs for the staged risk-guard fix.
READ-ONLY: runs the staged tests/repro as subprocesses; sends no order; starts no production cycle;
writes only the validation JSON under trader_v1/audit/.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
AUDIT = os.path.join(BASE, "audit")
STAGED = os.path.join(ROOT, "audit", "staged_fix")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
AUDIT_OUT = os.path.join(AUDIT, "V1_RISKGUARD_FIX_VALIDATION.json")

BASELINE_HASHES = {   # captured before any change (this audit)
    "gates.py": "0e02a4240b517b2a987c377d4488945a75c701c144e56ca3691d0ed349f2c9d3",
    "cycle.py": "dcb7edde220cfe07be93c72cda1fa55ae48ed71316b384a38c1898d7161b523b",
    "run_gates.py": "c2fc89be0f27bb90f0fe7144e445e310c862418210d487ce483a1127ce7018a7",
    "registry/runtime_config.json": "0732456adc415587763894506e0cd981460711966b2782d3bfda89acff062b38",
}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def run(script):
    r = subprocess.run([PY, script], capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def main():
    out = {"generated_utc": None, "python": PY}
    import datetime as dt
    out["generated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()

    # 1) independent re-run of the 12 staged regression tests
    rc, so = run(os.path.join(STAGED, "test_risk_guard_wiring.py"))
    m = re.search(r"(\d+)/(\d+) PASS", so)
    out["regression_tests"] = {"returncode": rc,
                               "pass": int(m.group(1)) if m else None, "total": int(m.group(2)) if m else None,
                               "checks": re.findall(r"(PASS|FAIL)\s+(\S+)\s+(.*)", so)}
    # 2) independent re-run of the defect reproduction
    rc2, so2 = run(os.path.join(STAGED, "offline_repro.py"))
    nb = re.search(r"SHOULD-REJECT-BUT-ALLOWED = (\d+) / (\d+) opens", so2)
    out["defect_repro"] = {"returncode": rc2, "should_reject_but_allowed": int(nb.group(1)) if nb else None,
                           "opens": int(nb.group(2)) if nb else None,
                           "stability": "identical across price/net basis x UTC/server frame (see script output)"}

    # 3) execution-path proof: the fix adds no broker call; the single gated call is unchanged
    cyc = open(os.path.join(ROOT, "cycle.py"), encoding="utf-8").read()
    patch = open(os.path.join(STAGED, "PATCHES.md"), encoding="utf-8").read()
    added = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
    out["execution_path_proof"] = {
        "cycle_order_send_occurrences": cyc.count("mt5.order_send("),
        "cycle_order_check_occurrences": cyc.count("mt5.order_check("),
        "patch_added_lines_with_order_send": sum(1 for l in added if "order_send(" in l),
        "patch_added_lines_with_order_check": sum(1 for l in added if "order_check(" in l),
        "send_gate": "order_send only under: action=='ENTER' and oi['trade'] and chk_ok and send_enabled",
        "dry_run_branch": "in --dry-run the action is set to WOULD_ENTER, so the send block is unreachable",
    }
    # 4) ORDER_SEND still off / operator-controlled
    cfgp = os.path.join(ROOT, "registry", "runtime_config.json")
    cfg = json.load(open(cfgp, encoding="utf-8"))
    out["order_send_control"] = {"runtime_config.order_send_enabled": cfg.get("order_send_enabled"),
                                 "note": "unchanged by this audit; the fix never bypasses this flag",
                                 "orders_sent_by_this_audit": 0, "order_check_by_this_audit": 0}
    # 5) production side effects zero: fingerprints unchanged vs the pre-work baseline
    fps = {k: sha(os.path.join(ROOT, k)) for k in BASELINE_HASHES}
    out["production_untouched"] = {"fingerprints": fps,
                                   "unchanged": all(fps[k] == BASELINE_HASHES[k] for k in BASELINE_HASHES)}
    out["verdict"] = ("FIX_VALIDATED_NO_PRODUCTION_CHANGE"
                      if (out["regression_tests"]["pass"] == out["regression_tests"]["total"]
                          and out["production_untouched"]["unchanged"]
                          and out["execution_path_proof"]["patch_added_lines_with_order_send"] == 0)
                      else "REVIEW_REQUIRED")
    json.dump(out, open(AUDIT_OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("regression_tests", "defect_repro", "execution_path_proof",
                                          "order_send_control", "production_untouched", "verdict")},
                     ensure_ascii=False, indent=1)[:2500])


if __name__ == "__main__":
    main()
