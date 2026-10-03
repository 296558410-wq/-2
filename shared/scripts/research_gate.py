# -*- coding: utf-8 -*-
"""research_gate — unified research execution gate (RLAP Phase 2, mandatory).

Usage:  python scripts/research_gate.py --manifest <experiment manifest>
Exit:   0 = PASS (experiment may run)
        1 = FAIL (STOP; no experiment)
        2 = HARD BLOCK (first-use violation on OOS/cross; STOP)

There is intentionally no skip/bypass flag. Historical market experiments are
not rerun; this gate binds all FUTURE research executions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.rlap_tools.gate import GateError, require_gate  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="research_gate (mandatory)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--pml", default=None)
    ap.add_argument("--si-dir", default=None)
    # NOTE: no --force / --skip options exist by design; unknown flags error out.
    a = ap.parse_args(argv)
    try:
        res = require_gate(a.manifest, a.ledger, a.pml, a.si_dir)
    except GateError as exc:
        print(f"RESEARCH_GATE: STOP — {exc}")
        return exc.code if hasattr(exc, "code") else 1
    status = {i["id"]: i["status"] for i in res.items}
    print("RESEARCH_GATE: PASS")
    for k, v in status.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
