"""Strategy Registry with lifecycle management.

Lifecycle: RESEARCH -> SHADOW -> CANDIDATE -> VALIDATED -> ACTIVE -> DEGRADED -> RETIRED.
A single profitable run NEVER promotes to ACTIVE. Every promotion requires an
evidence record. Old strategies are never deleted.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone

STATES = ["RESEARCH", "SHADOW", "CANDIDATE", "VALIDATED", "ACTIVE", "DEGRADED", "RETIRED"]

# allowed transitions (evidence-gated, monotone unless degradation)
ALLOWED = {
    "RESEARCH": {"SHADOW", "RETIRED"},
    "SHADOW": {"CANDIDATE", "RESEARCH", "RETIRED"},
    "CANDIDATE": {"VALIDATED", "SHADOW", "RETIRED"},
    "VALIDATED": {"ACTIVE", "DEGRADED", "RETIRED"},
    "ACTIVE": {"DEGRADED", "RETIRED"},
    "DEGRADED": {"RETIRED", "SHADOW"},
    "RETIRED": {"RESEARCH"},  # regime change may re-open for SHADOW re-validation
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrategyRegistry:
    def __init__(self, path: str):
        self.path = path
        self.records: dict[str, dict] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        r = json.loads(line)
                        self.records[r["strategy_id"]] = r

    def register(self, spec, extra: dict | None = None) -> dict:
        rec = spec.to_dict()
        rec.update({
            "state": "RESEARCH",
            "first_seen": _now(),
            "validation_history": [],
            "oos_history": [],
            "regime_history": [],
            "max_drawdown": None,
            "performance_decay": None,
            "failure_reason": None,
            "retirement_reason": None,
            "transitions": [{"to": "RESEARCH", "at": _now(), "evidence": "factory_created"}],
        })
        if extra:
            rec.update(extra)
        self.records[rec["strategy_id"]] = rec
        return rec

    def transition(self, sid: str, to: str, evidence: str) -> None:
        rec = self.records[sid]
        cur = rec["state"]
        if to not in ALLOWED.get(cur, set()):
            raise ValueError(f"illegal transition {sid}: {cur} -> {to}")
        rec["state"] = to
        rec["transitions"].append({"from": cur, "to": to, "at": _now(), "evidence": evidence})
        if to == "RETIRED":
            rec["retirement_reason"] = evidence

    def append_history(self, sid: str, kind: str, entry: dict) -> None:
        self.records[sid][f"{kind}_history"].append({"at": _now(), **entry})

    def flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            for sid in sorted(self.records):
                f.write(json.dumps(self.records[sid], ensure_ascii=False) + "\n")
