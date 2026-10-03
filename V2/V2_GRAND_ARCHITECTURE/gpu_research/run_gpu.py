"""Run the GPU research engine: measured benchmark + large-scale search."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common import hashing, data as D, cost as C
from gpu_research import engine as GE, benchmark as GB


def main():
    df, man = D.load_research_dataset("1min")
    cost = C.round_trip_cost_price(df["spread"].to_numpy())
    print(f"code_commit={hashing.git_commit()}")
    print(f"dataset_hash={man['dataset_hash']}")
    print(f"n_bars={len(df)} cost={cost:.4f}")
    b = GB.run_benchmark(df["close"].to_numpy(), cost, h=20, n_boot=60000)
    print(json.dumps({k: b.get(k) for k in
                      ["GPU_RESEARCH", "n_combos", "gpu_runtime_s", "cpu_runtime_s", "speedup",
                       "peak_vram_mb", "peak_vram_pct", "gpu_utilization_pct"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
