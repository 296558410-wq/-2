"""Run Strategy Memory + Failure Analysis on the factory strategies."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import stages as S
from common import hashing, data as D, cost as C
from strategy_factory import factory as F


def main():
    df, man = D.load_research_dataset("1min")
    cost = C.round_trip_cost_price(df["spread"].to_numpy())
    specs = F.generate_specs()
    out = S.memory_and_failure(df, specs, cost, os.path.join(ROOT, "_tmp_memory.jsonl"))
    print(f"code_commit={hashing.git_commit()} dataset_hash={man['dataset_hash']}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
