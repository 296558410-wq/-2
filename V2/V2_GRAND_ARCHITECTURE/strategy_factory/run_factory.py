"""Run the Strategy Factory and print hashes. Reproduces the candidate set."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common import hashing, data as D
from strategy_factory import factory as F


def main():
    man = D.dataset_hash()
    specs = F.generate_specs()
    print(f"code_commit={hashing.git_commit()}")
    print(f"dataset_hash={man}")
    print(f"n_specs={len(specs)}")
    for s in specs:
        print(json.dumps({"strategy_id": s.strategy_id, "hypothesis_id": s.hypothesis_id,
                          "mechanism": s.mechanism, "config_hash": s.config_hash}, ensure_ascii=False))


if __name__ == "__main__":
    main()
