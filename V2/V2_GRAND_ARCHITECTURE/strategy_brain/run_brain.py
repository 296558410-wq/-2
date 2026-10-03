"""Run the Multi-Strategy Brain over the PIT dataset and print conflict stats."""
import os
import sys
import json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import program as P
import stages as S
from common import hashing, data as D, cost as C
from strategy_factory import factory as F
from strategy_registry import StrategyRegistry


def main():
    df, man = D.load_research_dataset("1min")
    cost = C.round_trip_cost_price(df["spread"].to_numpy())
    specs = F.generate_specs()
    reg = StrategyRegistry(os.path.join(ROOT, "_tmp_registry.jsonl"))
    specs, results, cost = P.stage_factory_and_eval(df, man, reg)
    b = S.brain_run(df, specs, results, cost)
    print(f"code_commit={hashing.git_commit()} dataset_hash={man['dataset_hash']}")
    print(json.dumps(b["stats"], ensure_ascii=False, indent=2))
    print(json.dumps(b["conflict_counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
