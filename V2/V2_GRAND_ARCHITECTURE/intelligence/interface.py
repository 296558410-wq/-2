"""V2 Intelligence Interface.

Standard interface reserved for a REAL LLM (market interpretation, evidence
synthesis, counter-evidence, strategy-conflict interpretation, hypothesis
generation). An LLM NEVER holds final Risk/Execution authority.

If no LLM endpoint is configured, every method returns LLM_UNAVAILABLE. A
heuristic/rule model must NEVER be passed off as a real LLM: the class refuses
to run unless an explicit endpoint is provided, otherwise it reports
LLM_UNAVAILABLE and performs no "reasoning".
"""
from __future__ import annotations
import os
from dataclasses import dataclass, asdict

LLM_UNAVAILABLE = "LLM_UNAVAILABLE"


@dataclass
class IntelligenceResult:
    status: str
    capability: str
    content: str | None = None
    authority: str = "NONE"

    def to_dict(self):
        return asdict(self)


class IntelligenceInterface:
    """Standard LLM boundary. `endpoint` must be an explicit real LLM URL.

    Authority is always NONE: hard risk control lives in the non-LLM layer.
    """

    def __init__(self, endpoint: str | None = None, model: str | None = None):
        self.endpoint = endpoint or os.environ.get("V2_LLM_ENDPOINT")
        self.model = model
        self.authority = "NONE"

    def available(self) -> bool:
        return bool(self.endpoint)

    def _cap(self, capability: str, **kw) -> IntelligenceResult:
        if not self.available():
            return IntelligenceResult(LLM_UNAVAILABLE, capability, None, "NONE")
        # A real endpoint would be called here. We do NOT fabricate a heuristic.
        return IntelligenceResult("ENDPOINT_CONFIGURED_NOT_CALLED", capability, None, "NONE")

    def market_interpretation(self, **kw):
        return self._cap("market_interpretation", **kw)

    def evidence_synthesis(self, **kw):
        return self._cap("evidence_synthesis", **kw)

    def counter_evidence(self, **kw):
        return self._cap("counter_evidence", **kw)

    def strategy_conflict_interpretation(self, **kw):
        return self._cap("strategy_conflict_interpretation", **kw)

    def hypothesis_generation(self, **kw):
        return self._cap("hypothesis_generation", **kw)

    def status(self) -> dict:
        return {
            "status": "LLM_UNAVAILABLE" if not self.available() else "ENDPOINT_CONFIGURED",
            "endpoint_configured": self.available(),
            "authority": "NONE",
            "note": "LLM never owns Risk/Execution authority; no heuristic fallback",
        }
