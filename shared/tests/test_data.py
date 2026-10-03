"""test_data.py — Parquet 读写 + DuckDB 查询测试。"""
import duckdb
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_df():
    n = 5000
    ts = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({
        "ts_utc": ts,
        "symbol": "XAUUSD",
        "close": 2400 + np.cumsum(np.random.default_rng(0).normal(0, 1, n)),
        "volume": np.random.default_rng(1).integers(1, 50, n),
    })


def test_parquet_roundtrip(tmp_path, sample_df):
    p = tmp_path / "t.parquet"
    sample_df.to_parquet(p, index=False)
    back = pd.read_parquet(p)
    pd.testing.assert_frame_equal(back, sample_df)


def test_duckdb_query(tmp_path, sample_df):
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE x AS SELECT * FROM sample_df")
    n = con.execute("SELECT count(*) FROM x").fetchone()[0]
    assert n == len(sample_df)
    avg = con.execute("SELECT avg(close) FROM x").fetchone()[0]
    assert abs(avg - sample_df["close"].mean()) < 1e-6
    con.close()
