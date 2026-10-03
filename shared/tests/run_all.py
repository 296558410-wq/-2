"""run_all.py — 测试总入口：分类执行并输出 PASS/FAIL/SKIP + REASON 到 tests/results_<ts>.md。

用法: python tests/run_all.py   （需在 C:\AIQuant 根执行：python -m tests.run_all 亦可）
"""
from __future__ import annotations

import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROWS: list[tuple[str, str, str]] = []  # (category, status, reason)


def check(category: str, fn):
    try:
        fn()
        ROWS.append((category, "PASS", ""))
    except Exception as e:
        ROWS.append((category, "FAIL", f"{type(e).__name__}: {str(e)[:200]}"))


def main() -> None:
    print("AIQuant 测试套件 run_all —", datetime.now(timezone.utc).isoformat())

    # ---- Environment ----
    def env():
        import numpy, pandas, scipy, numba, pyarrow, polars, duckdb  # noqa
        import statsmodels, sklearn, xgboost, lightgbm  # noqa
        import pandera, hydra  # noqa
        assert sys.version_info[:2] == (3, 12), f"Python {sys.version_info[:2]} != 3.12"
    check("Environment: python3.12+imports", env)

    # ---- GPU ----
    def gpu():
        import torch
        assert torch.cuda.is_available(), "torch.cuda.is_available()=False"
        p = torch.cuda.get_device_properties(0)
        assert p.major == 8 and p.minor == 6, f"CC {p.major}.{p.minor} != 8.6"
    check("GPU: CUDA available + CC8.6", gpu)

    # ---- Data ----
    def data():
        import numpy as np, pandas as pd, duckdb, tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.parquet"
            df = pd.DataFrame({"a": np.arange(1000), "b": np.random.default_rng(0).normal(size=1000)})
            df.to_parquet(p)
            assert len(pd.read_parquet(p)) == 1000
            con = duckdb.connect()
            n = con.execute(f"SELECT count(*) FROM read_parquet('{p.as_posix()}')").fetchone()[0]
            assert n == 1000
    check("Data: parquet+duckdb", data)

    # ---- Quant ----
    def quant():
        import numpy as np
        from research_engine.validation import permutation_test
        x = np.random.default_rng(1).normal(0, 1, 1000)
        assert permutation_test(x, n_iter=200, seed=1)["p_value"] > 0.01
    check("Quant: returns/permutation", quant)

    # ---- Stats: bootstrap 一致性（CPU 后端） ----
    def stats_boot():
        import numpy as np
        from research_engine.backends import CPUBackend
        x = np.random.default_rng(0).standard_normal(50_000)
        r1 = CPUBackend(seed=11).run_bootstrap(x, n_iter=500).to_dict()
        r2 = CPUBackend(seed=11).run_bootstrap(x, n_iter=500).to_dict()
        assert abs(r1["dist_mean"] - r2["dist_mean"]) < 1e-9, "seed 不可复现"
        assert abs(r1["dist_mean"]) < 0.05
    check("Stats: bootstrap reproducible", stats_boot)

    # ---- ML ----
    def ml():
        import numpy as np
        import xgboost as xgb
        X = np.random.default_rng(0).standard_normal((500, 5))
        y = X[:, 0] + X[:, 1]
        m = xgb.XGBRegressor(n_estimators=20, verbosity=0)
        m.fit(X, y)
        assert m.predict(X[:5]).shape == (5,)
    check("ML: xgboost", ml)

    # ---- Pipeline（合成数据端到端快速版） ----
    def pipeline():
        import subprocess, sys as _sys
        r = subprocess.run([_sys.executable, "scripts/gen_synthetic.py", "--days", "1", "--seed", "42"],
                           capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stderr[-500:]
        r2 = subprocess.run([_sys.executable, "scripts/run_pipeline.py"], capture_output=True, text=True, cwd=ROOT)
        assert r2.returncode == 0, r2.stderr[-500:]
    check("Pipeline: synthetic e2e", pipeline)

    # ---- 结果表 ----
    out = ROOT / "tests" / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    lines = ["# 测试结果", "", f"- 时间：{datetime.now(timezone.utc).isoformat()}",
             f"- 机器：{platform.node()} · Python {platform.python_version()}",
             "", "| 类别 | 状态 | 说明 |", "|---|---|---|"]
    for cat, st, reason in ROWS:
        lines.append(f"| {cat} | {st} | {reason} |")
    n_pass = sum(1 for _, s, _ in ROWS if s == "PASS")
    lines += ["", f"**PASS={n_pass} / FAIL={len(ROWS)-n_pass}**"]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"结果已写入 {out}")
    print(f"PASS={n_pass} FAIL={len(ROWS)-n_pass}")
    sys.exit(0 if n_pass == len(ROWS) else 1)


if __name__ == "__main__":
    main()
