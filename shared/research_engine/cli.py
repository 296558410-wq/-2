# -*- coding: utf-8 -*-
"""cli.py — 自动化 CLI（§20）。

用法：
  python -m research_engine run <experiment> [--backend auto|cpu|gpu] [--seed N]
  python -m research_engine benchmark [--sizes 1000,10000,100000] [--backend auto|cpu|gpu]
  python -m research_engine validate <experiment_id|latest>
  python -m research_engine list
  python -m research_engine synthetic [--days 30] [--seed 42] [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m research_engine",
                                 description="AIQuant Research Engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行一个实验（一条命令 = 一个完整实验）")
    p_run.add_argument("experiment")
    p_run.add_argument("--backend", default="auto", choices=["auto", "cpu", "gpu"])
    p_run.add_argument("--seed", type=int, default=42)
    p_run.add_argument("--params", default="{}", help='JSON 覆盖实验参数，如 {"days": 10}')

    p_bench = sub.add_parser("benchmark", help="CPU vs GPU 真实基准（bootstrap/permutation/MC）")
    p_bench.add_argument("--sizes", default="1000,10000,100000")
    p_bench.add_argument("--backend", default="auto", choices=["auto", "cpu", "gpu"])
    p_bench.add_argument("--out", default=str(ROOT / "reports" / "cpu_gpu_benchmark.md"))

    p_val = sub.add_parser("validate", help="复核实验记录（质量门 + 关键产物存在性）")
    p_val.add_argument("experiment_id", nargs="?", default="latest")

    sub.add_parser("list", help="列出已注册实验")
    p_syn = sub.add_parser("synthetic", help="（重新）生成合成 XAUUSD 数据")
    p_syn.add_argument("--days", type=int, default=30)
    p_syn.add_argument("--seed", type=int, default=42)
    p_syn.add_argument("--force", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "benchmark":
        return _cmd_benchmark(args)
    if args.cmd == "validate":
        return _cmd_validate(args)
    if args.cmd == "list":
        from .experiments import list_experiments
        print("\n".join(list_experiments()))
        return 0
    if args.cmd == "synthetic":
        from .core.dataset import SyntheticXAUUSDGenerator, OUT
        gen = SyntheticXAUUSDGenerator(seed=args.seed)
        ds = gen.generate(days=args.days)
        gen.save(ds, OUT)
        print(f"OK: {args.days} 天合成数据已生成 → {OUT}")
        return 0
    return 2


def _cmd_run(args) -> int:
    from .core.experiment import Experiment, ExperimentRunner
    from .experiments import get_experiment
    spec = get_experiment(args.experiment)
    params = {**spec["parameters"], **json.loads(args.params)}
    exp = Experiment(name=spec["name"], hypothesis=spec["hypothesis"],
                     dataset_version=spec["dataset_version"],
                     seed=args.seed, backend=args.backend, parameters=params)
    runner = ExperimentRunner(exp)
    print(f"[run] {exp.name} seed={args.seed} backend={args.backend}")
    out = runner.run(spec["run"])
    metrics = out.metrics()
    print(f"[run] done id={out.experiment_id} status={metrics.get('status')} "
          f"conclusion={metrics.get('conclusion')}")
    print(f"[run] 产物: {out.root / out.experiment_id}")
    return 0 if metrics.get("status") in ("PASS", "REJECT") else 1


def _cmd_benchmark(args) -> int:
    from .benchmarks.cpu_gpu import run_benchmark_suite
    sizes = [int(s) for s in args.sizes.split(",")]
    report = run_benchmark_suite(sizes=sizes, backend=args.backend)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"benchmark 报告已写入 {args.out}")
    return 0


def _cmd_validate(args) -> int:
    from .core.quality import evaluate_quality
    from .registry.experiment_registry import ExperimentDir
    reg = ExperimentDir(ROOT / "experiments")
    exp_id = args.experiment_id
    if exp_id == "latest":
        exp_id = reg.latest()
        if exp_id is None:
            print("无实验记录")
            return 1
    rec = reg.load_metrics(exp_id)
    q = evaluate_quality(rec)
    print(f"experiment_id : {exp_id}")
    print(f"name/status   : {rec.get('name')} / {rec.get('status')}")
    print(f"conclusion    : {rec.get('conclusion')}")
    print(f"quality gate  : {'PASS' if q.passed else 'FAIL'}")
    for k, v in q.items.items():
        print(f"  [{'x' if v else ' '}] {k}")
    if not q.passed:
        print("关键项失败，结论不得为 SUPPORTED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
