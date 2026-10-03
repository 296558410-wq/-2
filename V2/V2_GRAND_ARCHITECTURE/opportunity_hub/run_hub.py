"""Run the Opportunity Hub and report concentration across independent sources."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import stages as S
from common import hashing, data as D


def main():
    df, man = D.load_research_dataset("1min")
    out = S.hub_run(df)
    print(f"code_commit={hashing.git_commit()} dataset_hash={man['dataset_hash']}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
