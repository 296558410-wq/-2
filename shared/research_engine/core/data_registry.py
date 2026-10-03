# -*- coding: utf-8 -*-
"""core/data_registry.py — 数据集版本注册表（Phase 2 §3）。

目录：C:\AIQuant\data_registry\
每个数据集：data_registry/<dataset_id>/{dataset.json, data.parquet}
dataset.json 字段：dataset_id/source/symbol/timeframe/start/end/rows/timezone/
schema/sha256/created_at/extra。
index.json 为全量索引。禁止实验直接读取未注册的浮动文件。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "data_registry"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _index_path() -> Path:
    return REGISTRY_ROOT / "index.json"


def load_index() -> dict:
    if _index_path().exists():
        return json.loads(_index_path().read_text(encoding="utf-8"))
    return {"datasets": {}}


def save_index(idx: dict) -> None:
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    _index_path().write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def register_dataset(df: pd.DataFrame, *, source: str, symbol: str, timeframe: str,
                     timezone_name: str = "UTC", extra: dict | None = None,
                     dataset_id: str | None = None) -> dict:
    """注册一个数据集：落盘 + 元数据 + sha256 + 更新索引。"""
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    ts_col = "ts_utc" if "ts_utc" in df.columns else df.index.name
    ts = pd.DatetimeIndex(df[ts_col] if ts_col != df.index.name else df.index)
    if dataset_id is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        dataset_id = f"{symbol}_{timeframe}_{source}_{stamp}_v001"
    d = REGISTRY_ROOT / dataset_id
    d.mkdir(parents=True, exist_ok=True)
    data_path = d / "data.parquet"
    df.to_parquet(data_path, index=ts_col == df.index.name)
    meta = {
        "dataset_id": dataset_id,
        "source": source,
        "symbol": symbol,
        "timeframe": timeframe,
        "start": str(ts.min()),
        "end": str(ts.max()),
        "rows": int(len(df)),
        "timezone": timezone_name,
        "schema": [str(c) for c in df.columns],
        "sha256": sha256_file(data_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file": str(data_path),
    }
    if extra:
        meta["extra"] = extra
    (d / "dataset.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                                    encoding="utf-8")
    idx = load_index()
    idx["datasets"][dataset_id] = {k: meta.get(k) for k in
                                   ("dataset_id", "source", "symbol", "timeframe",
                                    "start", "end", "rows", "sha256", "created_at")}
    save_index(idx)
    return meta


def load_dataset(dataset_id: str) -> tuple[pd.DataFrame, dict]:
    meta = json.loads((REGISTRY_ROOT / dataset_id / "dataset.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(REGISTRY_ROOT / dataset_id / "data.parquet")
    return df, meta


def list_datasets() -> list[dict]:
    idx = load_index()
    return list(idx["datasets"].values())


def find_dataset(symbol: str, timeframe: str, source: str | None = None) -> list[dict]:
    out = []
    for m in list_datasets():
        if m["symbol"] == symbol and m["timeframe"] == timeframe:
            if source is None or m["source"] == source:
                out.append(m)
    return sorted(out, key=lambda x: x["created_at"])
