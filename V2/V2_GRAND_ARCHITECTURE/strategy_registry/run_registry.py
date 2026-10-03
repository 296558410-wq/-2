"""Run the Strategy Registry lifecycle demo (deterministic, no production state)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common import hashing
from strategy_factory import factory as F
from strategy_registry import StrategyRegistry, STATES, ALLOWED


def main():
    path = os.path.join(ROOT, "_tmp_registry_demo.jsonl")
    reg = StrategyRegistry(path)
    specs = F.generate_specs()[:3]
    for s in specs:
        reg.register(s)
    reg.transition(specs[0].strategy_id, "SHADOW", "demo: FDR note only")
    reg.flush()
    print(f"code_commit={hashing.git_commit()}")
    print("states:", STATES)
    print("allowed:", {k: sorted(v) for k, v in ALLOWED.items()})
    for s in specs:
        print(s.strategy_id, reg.records[s.strategy_id]["state"])


if __name__ == "__main__":
    main()
