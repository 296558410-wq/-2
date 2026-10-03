"""test_ml.py — XGBoost / LightGBM / sklearn 冒烟测试。"""
import numpy as np
import pytest

rng = np.random.default_rng(0)
X = rng.standard_normal((2000, 8))
y = X[:, 0] * 2 + X[:, 1] - X[:, 2] ** 2 + rng.standard_normal(2000) * 0.01


def test_xgboost_cpu():
    xgb = pytest.importorskip("xgboost")
    m = xgb.XGBRegressor(n_estimators=20, max_depth=4, tree_method="hist", verbosity=0)
    m.fit(X, y)
    pred = m.predict(X[:100])
    assert pred.shape == (100,)
    # 结构数据上应能学到大部分信号
    assert float(np.corrcoef(pred, y[:100])[0, 1]) > 0.9


def test_lightgbm_cpu():
    lgb = pytest.importorskip("lightgbm")
    m = lgb.LGBMRegressor(n_estimators=20, max_depth=4, verbosity=-1)
    m.fit(X, y)
    pred = m.predict(X[:100])
    assert pred.shape == (100,)
    assert float(np.corrcoef(pred, y[:100])[0, 1]) > 0.9


def test_sklearn_cv():
    sklearn = pytest.importorskip("sklearn")
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(RandomForestRegressor(n_estimators=10, random_state=0), X, y, cv=3)
    assert scores.mean() > 0.5
