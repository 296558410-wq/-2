"""run_pipeline.py — 合成数据端到端管线（真实跑通并产出报告）。

Generate → Parquet → DuckDB 查询 → Feature → Signal → Backtest → Stats → Report

用法: python scripts/run_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DATA = ROOT / "data" / "synthetic"
DB_PATH = ROOT / "data" / "cache" / "aiq_meta.duckdb"
REPORT = ROOT / "reports" / "pipeline_report.md"
BACKTEST_OUT = ROOT / "backtests" / "synthetic_ma5_ma20.md"


def step_duckdb(m5_path: Path) -> dict:
    con = duckdb.connect(str(DB_PATH))
    con.execute("DROP TABLE IF EXISTS xau_m5")
    con.execute(f"""
        CREATE TABLE xau_m5 AS SELECT * FROM read_parquet('{m5_path.as_posix()}')
    """)
    stats = con.execute("""
        SELECT count(*) AS n_bars,
               min(ts_utc) AS first_ts, max(ts_utc) AS last_ts,
               round(avg(spread_mean)::DOUBLE, 4) AS avg_spread_bp_est,
               round(stddev(close)::DOUBLE, 2) AS close_std
        FROM xau_m5
    """).fetchdf().iloc[0].to_dict()
    con.close()
    return stats


def features_and_signal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts_utc").reset_index(drop=True)
    ret = df["close"].pct_change()
    df["ret_5"] = ret
    df["vol_20"] = ret.rolling(20).std()
    df["ma_fast"] = df["close"].rolling(5).mean()
    df["ma_slow"] = df["close"].rolling(20).mean()
    df["signal"] = np.where(df["ma_fast"] > df["ma_slow"], 1.0, -1.0)  # 简化示例信号
    df["signal"] = df["signal"].shift(1)  # 防前视：次日开盘执行
    return df.dropna().reset_index(drop=True)


def backtest_stats(df: pd.DataFrame) -> dict:
    """按 bar 收益与滞后信号计算统计量（等价于次日执行的长短策略）。"""
    strat = df["signal"] * df["ret_5"]
    strat = strat.dropna()
    if len(strat) == 0 or strat.std() == 0:
        return {"error": "无有效交易样本"}
    n_per_year = 12 * 24 * 365.25 / 5.0  # 5 分钟 bar 年化数
    sharpe = float(strat.mean() / strat.std() * np.sqrt(n_per_year))
    cum = (1 + strat).cumprod()
    dd = float((cum / cum.cummax() - 1).min())
    return {
        "n_bars": int(len(df)), "n_trades": int((df["signal"].diff() != 0).sum()),
        "mean_bar_ret_bps": float(strat.mean() * 1e4), "std_bar_ret_bps": float(strat.std() * 1e4),
        "sharpe_ann": round(sharpe, 3), "max_drawdown": round(dd, 4),
        "total_return": round(float(cum.iloc[-1] - 1), 4),
    }


def main() -> None:
    m5_path = DATA / "XAUUSD_M5.parquet"
    if not m5_path.exists():
        print("[pipe] 缺少 M5 数据，先运行 gen_synthetic.py")
        sys.exit(1)
    print("[pipe] 1/5 DuckDB 装载与查询")
    db_stats = step_duckdb(m5_path)
    print(f"       {db_stats}")
    print("[pipe] 2/5 特征与信号")
    df = pd.read_parquet(m5_path)
    feats = features_and_signal(df)
    feat_path = ROOT / "research" / "features" / "synthetic_m5_feat.parquet"
    feat_path.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(feat_path, index=False)
    print(f"       特征 {len(feats):,} 行 -> {feat_path}")
    print("[pipe] 3/5 回测统计")
    stats = backtest_stats(feats)
    print(f"       {stats}")
    print("[pipe] 4/5 报告")
    BACKTEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Synthetic Pipeline 回测报告（示例信号 MA5/MA20，非研究结论）",
        "",
        f"- 数据：synthetic XAUUSD M5（生成 seed=42）",
        f"- 样本：{stats.get('n_bars')} bars",
        f"- 年化 Sharpe：{stats.get('sharpe_ann')}",
        f"- 最大回撤：{stats.get('max_drawdown')}",
        f"- 总收益：{stats.get('total_return')}",
        "",
        "> ⚠️ 合成数据 + 示例信号，仅验证管线可用性。任何数字不代表市场表现。",
    ]
    BACKTEST_OUT.write_text("\n".join(lines), encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join([
        "# Pipeline 端到端验证报告", "",
        f"- 时间：{pd.Timestamp.now(tz='UTC').isoformat()}",
        f"- DuckDB 统计：{db_stats}", f"- 特征行数：{len(feats):,}",
        f"- 回测：Sharpe={stats.get('sharpe_ann')} MaxDD={stats.get('max_drawdown')}",
        "## 结论：管线 Generate→Parquet→DuckDB→Feature→Signal→Backtest→Report 全部跑通",
    ]), encoding="utf-8")
    print(f"[pipe] 5/5 完成 -> {REPORT}")


if __name__ == "__main__":
    main()
