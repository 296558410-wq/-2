# -*- coding: utf-8 -*-
"""registry/experiment_registry.py — 实验注册表（§16）。

目录约定：experiments/<experiment_id>/{config.json, metrics.json, results.parquet,
report.md, log.txt}。experiment_id = YYYYMMDD_HHMMSS_<name>。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class ExperimentDir:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._current_id: str | None = None

    def bind(self, exp_id: str) -> "ExperimentDir":
        self._current_id = exp_id
        return self

    @property
    def experiment_id(self) -> str:
        if self._current_id is None:
            raise RuntimeError("ExperimentDir 未绑定 experiment_id（先 bind）")
        return self._current_id

    def metrics(self) -> dict:
        return self.load_metrics(self.experiment_id)

    def _path(self, exp_id: str) -> Path:
        return self.root / exp_id

    def create(self, exp_id: str) -> Path:
        p = self._path(exp_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def exists(self, exp_id: str) -> bool:
        return self._path(exp_id).exists()

    def save_json(self, exp_id: str, filename: str, obj) -> Path:
        p = self._path(exp_id) / filename
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return p

    def save_parquet(self, exp_id: str, filename: str, df: pd.DataFrame) -> Path:
        p = self._path(exp_id) / filename
        df.to_parquet(p, index=True)
        return p

    def save_text(self, exp_id: str, filename: str, text: str) -> Path:
        p = self._path(exp_id) / filename
        p.write_text(text, encoding="utf-8")
        return p

    def append_text(self, exp_id: str, filename: str, text: str) -> Path:
        p = self._path(exp_id) / filename
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        return p

    def save_artifact(self, exp_id: str, filename: str, obj) -> Path:
        """自动按扩展名选择 json/parquet/txt 保存（实验自定义产物）。"""
        if filename.endswith(".json"):
            return self.save_json(exp_id, filename, obj)
        if filename.endswith(".parquet"):
            return self.save_parquet(exp_id, filename, obj)
        return self.save_text(exp_id, filename, str(obj))

    def load_json(self, exp_id: str, filename: str) -> dict:
        p = self._path(exp_id) / filename
        return json.loads(p.read_text(encoding="utf-8"))

    def load_parquet(self, exp_id: str, filename: str = "results.parquet") -> pd.DataFrame:
        return pd.read_parquet(self._path(exp_id) / filename)

    def get(self, exp_id: str) -> "ExperimentDir":
        if not self.exists(exp_id):
            raise FileNotFoundError(exp_id)
        return self.bind(exp_id)

    def list_ids(self) -> list[str]:
        return sorted([p.name for p in self.root.iterdir()
                       if p.is_dir() and (p / "config.json").exists()])

    def latest(self) -> str | None:
        ids = self.list_ids()
        return ids[-1] if ids else None

    def load_metrics(self, exp_id: str) -> dict:
        return self.load_json(exp_id, "metrics.json")
