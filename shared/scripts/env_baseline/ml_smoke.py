# -*- coding: utf-8 -*-
"""ml_smoke.py - scikit-learn / xgboost / lightgbm smoke tests (+ optional xgb GPU)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_ml.json"


def main() -> None:
    checks: list[dict] = []
    info: dict = {}
    rng = np.random.default_rng(0)

    def add(name, ok, detail=""):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    n = 4000
    X = rng.standard_normal((n, 8)).astype(np.float32)
    y = (np.sin(X[:, 0]) + 0.5 * X[:, 1] ** 2 + 0.3 * X[:, 2] * X[:, 3] + rng.standard_normal(n) * 0.2).astype(np.float32)
    Xtr, Xte, ytr, yte = X[:3000], X[3000:], y[:3000], y[3000:]

    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.metrics import r2_score

    info["sklearn"] = __import__("sklearn").__version__
    m = Ridge(alpha=1.0)
    m.fit(Xtr, ytr)
    r2 = r2_score(yte, m.predict(Xte))
    add("sklearn_ridge", r2 > 0.2, f"R2={r2:.3f} (linear baseline on nonlinear target)")

    h = HistGradientBoostingRegressor(max_iter=80, random_state=0)
    h.fit(Xtr, ytr)
    r2h = r2_score(yte, h.predict(Xte))
    add("sklearn_histgb", r2h > 0.6, f"R2={r2h:.3f}")

    import xgboost as xgb
    info["xgboost"] = xgb.__version__
    dtr = xgb.DMatrix(Xtr, ytr)
    dte = xgb.DMatrix(Xte, yte)
    bst = xgb.train({"objective": "reg:squarederror", "max_depth": 4, "eta": 0.1, "seed": 0}, dtr, num_boost_round=80)
    pred = bst.predict(dte)
    r2x = float(r2_score(yte, pred))
    add("xgboost_cpu", r2x > 0.6, f"R2={r2x:.3f}")

    # xgboost GPU attempt (best-effort -> WARN if unavailable)
    try:
        t0 = time.perf_counter()
        bstg = xgb.train({"objective": "reg:squarederror", "max_depth": 4, "eta": 0.1, "seed": 0, "device": "cuda", "nthread": 4}, dtr, num_boost_round=30)
        dt = time.perf_counter() - t0
        r2g = float(r2_score(yte, bstg.predict(dte)))
        add("xgboost_gpu", r2g > 0.5, f"R2={r2g:.3f} in {dt:.2f}s")
        info["xgboost_gpu"] = "works"
    except Exception as e:
        add("xgboost_gpu", False, f"unavailable: {type(e).__name__}: {str(e)[:150]} -> CPU fallback ok")
        checks[-1]["status"] = "WARN"
        info["xgboost_gpu"] = "unavailable"

    import lightgbm as lgb
    info["lightgbm"] = lgb.__version__
    lm = lgb.LGBMRegressor(n_estimators=80, max_depth=4, verbose=-1, random_state=0)
    lm.fit(Xtr, ytr)
    r2l = r2_score(yte, lm.predict(Xte))
    add("lightgbm_cpu", r2l > 0.6, f"R2={r2l:.3f}")

    # determinism
    m2 = Ridge(alpha=1.0).fit(Xtr, ytr)
    add("sklearn_deterministic", np.allclose(m.predict(Xte), m2.predict(Xte), atol=1e-12), "same params -> same predictions")

    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ml_smoke: {status} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
