"""Report the LLM interface status. No LLM endpoint -> LLM_UNAVAILABLE (no fake)."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from intelligence import IntelligenceInterface, LLM_UNAVAILABLE
from common import hashing


def main():
    it = IntelligenceInterface()
    print(f"code_commit={hashing.git_commit()}")
    print(json.dumps(it.status(), ensure_ascii=False, indent=2))
    for cap, res in [
        ("hypothesis_generation", it.hypothesis_generation(topic="x")),
        ("market_interpretation", it.market_interpretation()),
        ("evidence_synthesis", it.evidence_synthesis()),
        ("counter_evidence", it.counter_evidence()),
        ("strategy_conflict_interpretation", it.strategy_conflict_interpretation()),
    ]:
        print(cap, res.status)


if __name__ == "__main__":
    main()
