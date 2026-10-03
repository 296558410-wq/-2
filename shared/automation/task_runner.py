"""task_runner.py — 可恢复实验任务运行器 v0.1（骨架但真实可用）。

用法示例:
    python automation/task_runner.py --name demo --seed 42
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.snapshot_env import git_head  # noqa: E402


def machine_info() -> dict:
    import platform as pf

    return {"host": pf.node(), "platform": pf.platform(), "python": pf.python_version()}


class TaskRunner:
    def __init__(self, name: str, seed: int, params: dict | None = None,
                 exp_root: str | Path = ROOT / "experiments"):
        self.exp_id = f"{datetime.now().strftime('%Y%m%d')}_{name}_{uuid.uuid4().hex[:6]}"
        self.seed = seed
        self.params = params or {}
        self.dir = Path(exp_root) / self.exp_id
        (self.dir / "checkpoint").mkdir(parents=True, exist_ok=True)
        (self.dir / "outputs").mkdir(parents=True, exist_ok=True)
        (self.dir / "logs").mkdir(parents=True, exist_ok=True)
        self.meta = {
            "experiment_id": self.exp_id,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "params": self.params,
            "git_head": git_head(),
            "machine": machine_info(),
            "status": "running",
        }
        self._save_meta()

    def _save_meta(self):
        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def log(self, msg: str):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line)
        with open(self.dir / "logs" / "run.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def checkpoint(self, key: str, obj) -> Path:
        p = self.dir / "checkpoint" / f"{key}.json"
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return p

    def finish(self, ok: bool, summary: dict | None = None):
        self.meta["status"] = "ok" if ok else "failed"
        self.meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
        if summary:
            self.meta["summary"] = summary
        self._save_meta()
        self.log(f"状态: {self.meta['status']}")


def demo_task(runner: TaskRunner):
    """示例任务：分段计算 + checkpoint + 失败恢复演示。"""
    import numpy as np

    runner.log("demo: 生成随机序列 (seed 固定)")
    rng = np.random.default_rng(runner.seed)
    data = rng.standard_normal(1_000_000)
    runner.checkpoint("data_hash", {"sha256_len": len(data), "mean": float(data.mean())})
    for i in range(1, 6):
        seg = data[(i - 1) * 200_000:i * 200_000]
        runner.log(f"demo: 段 {i}/5 mean={seg.mean():.4f}")
        time.sleep(0.2)
    return {"n": int(len(data)), "mean": float(data.mean()), "std": float(data.std())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="demo")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    runner = TaskRunner(args.name, args.seed)
    try:
        summary = demo_task(runner)
        runner.finish(True, summary)
    except Exception:
        runner.log("任务失败: " + traceback.format_exc())
        runner.finish(False)
        sys.exit(1)
    print(f"\n实验目录: {runner.dir}")


if __name__ == "__main__":
    main()
