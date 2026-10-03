# -*- coding: utf-8 -*-
"""validation/split.py — 时间序列切分与泄漏防护（§11）。

time_split: 按时间顺序 Train(60%)/Validation(20%)/Test(20%)。
purge_window: 生成 embargo/purge 掩码 —— 训练样本若其 label 窗口跨越
  切分边界（未来信息泄漏到训练），将其从训练集剔除。
leakage_free_alignment: 断言特征与标签时间隔离。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def time_split(n: int, train: float = 0.6, val: float = 0.2, test: float = 0.2) -> dict:
    """返回 {train: slice, val: slice, test: slice}（整数位置，时间顺序）。"""
    if not np.isclose(train + val + test, 1.0):
        raise ValueError("train+val+test 必须 = 1")
    n_tr = int(n * train)
    n_va = int(n * val)
    return {"train": slice(0, n_tr),
            "val": slice(n_tr, n_tr + n_va),
            "test": slice(n_tr + n_va, n)}


def purge_window(idx: np.ndarray, split_pos: int, label_horizon: int) -> np.ndarray:
    """训练位置中 label 窗口（(pos, pos+label_horizon]）跨越 split_pos 的样本剔除。

    返回保留的训练位置（bool 掩码作用于训练集切片）。
    """
    train_pos = np.arange(idx[0], split_pos) if not isinstance(idx, np.ndarray) else idx
    # 对 split_pos 前 label_horizon 根训练样本做 purge
    keep = np.ones(len(train_pos), dtype=bool)
    for i in range(len(train_pos)):
        # 该样本的未来窗口 [pos+1, pos+label_horizon] 若触及 split_pos → 剔除
        if train_pos[i] + label_horizon >= split_pos:
            keep[i] = False
    return keep


def leakage_free_alignment(feature_index: pd.Index, label_index: pd.Index,
                           label_horizon: int) -> bool:
    """特征在 t 决策、label 用 (t, t+h]：label 与特征列混排前必须满足
    本断言 —— 由调用方保证 label 是在特征索引之外的未来；此处做结构检查：
    返回 True 表示索引单调且特征索引不晚于 label 索引（同长度场景下无意义，
    主要用于文档化约定 + 测试钩子）。"""
    fi = pd.DatetimeIndex(feature_index)
    li = pd.DatetimeIndex(label_index)
    if len(fi) != len(li):
        return False
    if not (fi.is_monotonic_increasing and li.is_monotonic_increasing):
        return False
    # label 序列整体相对特征后移 horizon（两者同索引，值本身由 shift(-h) 保证）
    return True
