"""One-shot entry: run the full Grand Architecture research program."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

from pipeline import run_program  # noqa: E402

if __name__ == "__main__":
    run_program.main()
