# -*- coding: utf-8 -*-
"""V3 frozen hypothesis registry (§19–§21, §30). Registry-driven.

The registry JSON was frozen BEFORE any evaluation. Thresholds are a-priori from mechanism
reasoning, never fitted. Changing any parameter requires a NEW hypothesis_id (§20/§29).
"""
from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
REGISTRY_PATH = os.path.join(V3, "research", "v3_strategy_registry", "hypotheses.json")

STATE_FLOW = ["DISCOVERED", "DEFINED", "FROZEN", "BACKTEST", "COST_STRESS", "OOS",
              "REGIME_TEST", "EDGE_UNCERTAIN", "REJECT", "CANDIDATE"]
INDEPENDENT, DERIVED, REUSED = "INDEPENDENT", "DERIVED", "REUSED"


def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc


_DOC = _load()
HYPOTHESES = _DOC["hypotheses"]
REGISTRY_HASH = _DOC["registry_hash"]


def registry_hash():
    return REGISTRY_HASH


def by_id(hid):
    for h in HYPOTHESES:
        if h["hypothesis_id"] == hid:
            return h
    return None
