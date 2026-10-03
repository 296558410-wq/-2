# -*- coding: utf-8 -*-
"""experiments/registry.py — 实验注册表（CLI 用）。"""
from __future__ import annotations

from typing import Callable

EXPERIMENTS: dict[str, dict] = {}


def register(name: str, hypothesis: str, dataset_version: str, parameters: dict,
             build: Callable, run: Callable) -> None:
    EXPERIMENTS[name] = {"name": name, "hypothesis": hypothesis,
                         "dataset_version": dataset_version,
                         "parameters": parameters, "build": build, "run": run}


def get_experiment(name: str) -> dict:
    if name not in EXPERIMENTS:
        raise KeyError(f"未知实验: {name}（可用: {list(EXPERIMENTS)}）")
    return EXPERIMENTS[name]


def list_experiments() -> list[str]:
    return sorted(EXPERIMENTS)
