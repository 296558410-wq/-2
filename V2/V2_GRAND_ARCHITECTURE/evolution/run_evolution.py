"""Run the Evolution Engine over computed strategy results (evidence-triggered)."""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import program as P
from strategy_registry import StrategyRegistry
from evolution import engine as EVO
import numpy as np


def main():
    from common import data as D, cost as C
    from common import hashing
    df, man = D.load_research_dataset("1min")
    reg = StrategyRegistry(os.path.join(ROOT, "_tmp_evo_registry.jsonl"))
    specs, results, cost = P.stage_factory_and_eval(df, man, reg)
    out = {}
    for s in specs:
        d = results[s.strategy_id]["splits"]["discovery"]
        v = results[s.strategy_id]["splits"]["validation"]
        o = results[s.strategy_id]["splits"]["oos"]
        m = EVO.MonitorState(s.strategy_id,
                             edge=v["expectancy"] if np.isfinite(v["expectancy"]) else 0.0,
                             edge_baseline=d["expectancy"] if np.isfinite(d["expectancy"]) else 0.0,
                             mfe=v["mfe"], mae=v["mae"], confidence_mean=0.5,
                             hit_rate=v["precision"] if np.isfinite(v["precision"]) else 0.0,
                             regime_now="UNKNOWN", regime_then="UNKNOWN", cost_sens=0.0)
        hist = {"pass": bool(np.isfinite(v["expectancy"]) and v["expectancy"] > 0 and v["n_eff"] >= 5)}
        oosr = {"pass": bool(np.isfinite(o["expectancy"]) and o["expectancy"] > 0 and o["n_eff"] >= 5)}
        out[s.strategy_id] = EVO.evolve(m, oos_result=oosr, historical_result=hist)
    print(f"code_commit={hashing.git_commit()} dataset_hash={man['dataset_hash']}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
