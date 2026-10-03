# -*- coding: utf-8 -*-
"""C10b — Model Temporal Eligibility Audit tests (RQ-08; independent domain)."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.model_temporal_gate import (                         # noqa: E402
    verdict, blocks, ELIGIBLE, CONDITIONAL, POST_HOC_ONLY, UNKNOWN,
    INELIGIBLE, DESIGN_ROLES,
)

WS = "2026-05-26"          # study window start
DEC = "2026-09-05T12:00:00+00:00"   # decision time


def mt(**kw):
    base = {
        "model_source": "open", "cutoff_verifiability": "published",
        "model_knowledge_cutoff": "2026-03-01", "release_date": "2026-03-01",
        "retrieval_timestamp": "2026-09-05T10:00:00+00:00",
        "retrieval_log": "logs/retrieval.yaml", "model_role": "analysis",
        "window_exposure": "none",
    }
    base.update(kw)
    return base


def test_eligible_sufficient_margin():
    v = verdict(mt(model_role="hypothesis_design",
                   model_knowledge_cutoff="2026-01-01",
                   release_date="2026-01-01"), WS, DEC)
    assert v["verdict"] == ELIGIBLE
    assert blocks(v, "hypothesis_design") is False


def test_conditional_cutoff_inside_margin():
    # cutoff 2026-05-10 -> +30d = 2026-06-09 > window start -> CONDITIONAL
    v = verdict(mt(model_knowledge_cutoff="2026-05-10",
                   release_date="2026-05-10"), WS, DEC)
    assert v["verdict"] == CONDITIONAL


def test_conditional_cutoff_after_window_start():
    v = verdict(mt(model_knowledge_cutoff="2026-07-01",
                   release_date="2026-07-01"), WS, DEC)
    assert v["verdict"] == CONDITIONAL


def test_engineering_eligible_regardless():
    v = verdict(mt(model_role="engineering"), WS, DEC)
    assert v["verdict"] == ELIGIBLE


def test_post_hoc_only_declared():
    v = verdict(mt(model_role="post_hoc_writing"), WS, DEC)
    assert v["verdict"] == POST_HOC_ONLY
    assert blocks(v, "post_hoc_writing") is False


def test_closed_source_unknown_cutoff_design_unknown():
    v = verdict(mt(model_source="closed", cutoff_verifiability="unverifiable",
                   model_knowledge_cutoff=None, release_date=None,
                   model_role="judgment"), WS, DEC)
    assert v["verdict"] == UNKNOWN
    assert blocks(v, "judgment") is True


def test_closed_source_unknown_cutoff_engineering_conditional():
    v = verdict(mt(model_source="closed", cutoff_verifiability="unverifiable",
                   model_knowledge_cutoff=None, release_date=None,
                   model_role="engineering"), WS, DEC)
    assert v["verdict"] == CONDITIONAL
    assert blocks(v, "engineering") is False


def test_ineligible_window_exposure():
    v = verdict(mt(model_role="judgment", window_exposure="claimed"), WS, DEC)
    assert v["verdict"] == INELIGIBLE
    assert blocks(v, "judgment") is True


def test_unknown_not_ineligible_distinct():
    u = verdict(mt(model_source="closed", cutoff_verifiability="unverifiable",
                   model_role="judgment"), WS, DEC)
    i = verdict(mt(model_role="judgment", window_exposure="claimed"), WS, DEC)
    assert u["verdict"] == UNKNOWN and i["verdict"] == INELIGIBLE
    assert UNKNOWN != INELIGIBLE


def test_release_after_decision_time():
    v = verdict(mt(model_role="hypothesis_design", release_date="2026-12-01"),
                WS, DEC)
    assert "release_after_decision" in v["flags"]
    assert v["verdict"] == UNKNOWN
    assert blocks(v, "hypothesis_design") is True


def test_retrieval_after_decision_time_distinct_field():
    # retrieval timestamp is a SEPARATE field from knowledge cutoff; retrieval
    # after decision cannot inform that decision -> flag only, verdict governed
    # by cutoff (eligible here since cutoff+marg <= window start)
    v = verdict(mt(model_role="hypothesis_design",
                   model_knowledge_cutoff="2026-01-01",
                   retrieval_timestamp="2026-10-01T00:00:00+00:00"), WS, DEC)
    assert "retrieval_after_decision" in v["flags"]
    assert v["verdict"] == ELIGIBLE


def test_cutoff_and_retrieval_not_merged():
    # a model whose cutoff is old but retrieval is recent: knowledge of the
    # window can only come from retrieval -> retrieval path is what matters for
    # contamination; still reported separately (cutoff verdict + retrieval flag)
    v = verdict(mt(model_knowledge_cutoff="2025-01-01",
                   retrieval_timestamp="2026-08-01T00:00:00+00:00"), WS, DEC)
    assert v["verdict"] == ELIGIBLE   # cutoff old; retrieval flagged domain
    assert "retrieval_after_decision" not in v["flags"]
