# -*- coding: utf-8 -*-
"""market_understanding — XAUUSD Market Understanding Engine（Phase 6）。

OBSERVE → ANALYZE → ATTRIBUTE → STATE → TRANSITION → ANTICIPATE
数据驱动；任何“状态/机制”标签只来自证据，不预设类别。
"""
from .state import build_state_features, fit_states_gmm, state_profiles, transition_matrix
from .events import detect_events
from .autopsy import autopsies_markdown

__all__ = ["build_state_features", "fit_states_gmm", "state_profiles",
           "transition_matrix", "detect_events", "autopsies_markdown"]
