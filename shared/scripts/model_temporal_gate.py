# -*- coding: utf-8 -*-
"""model_temporal_gate — Model Temporal Eligibility (RQ-08 / C10b).

Mechanical verdict function. Independent governance domain (never merged into
RLAP/search-leakage verdicts). Margin = 30 days (frozen; not tunable per results).
MODEL TRAINING/KNOWLEDGE CUTOFF and RETRIEVAL TIMESTAMP are distinct fields:
  - model_knowledge_cutoff: training-knowledge boundary of the model.
  - retrieval_timestamp: when external content was retrieved for this study.
A model retrieved-after-decision cannot have informed the decision (provenance
sanity), whereas cutoff governs what the model itself could know.
"""
from __future__ import annotations

import datetime as _dt

MARGIN_DAYS = 30  # frozen

ELIGIBLE = "ELIGIBLE"
CONDITIONAL = "CONDITIONAL"
POST_HOC_ONLY = "POST_HOC_ONLY"
UNKNOWN = "UNKNOWN"
INELIGIBLE = "INELIGIBLE"
DESIGN_ROLES = {"hypothesis_design", "judgment"}


def _iso(v):
    if not v:
        return None
    try:
        return _dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _d(v):
    d = _iso(v)
    return d.date() if d else None


def verdict(mt: dict, window_start: str | None, decision_time: str | None) -> dict:
    """mt = manifest['model_temporal']. Returns {verdict, detail, flags}."""
    role = str(mt.get("model_role", "")).strip() or "analysis"
    src = str(mt.get("model_source", "")).strip().lower()
    cv = str(mt.get("cutoff_verifiability", "")).strip().lower()
    cutoff = _d(mt.get("model_knowledge_cutoff"))
    release = _d(mt.get("release_date"))
    retrieval = _iso(mt.get("retrieval_timestamp"))
    decision = _iso(decision_time) if decision_time else None
    ws = _d(window_start)
    exposure = str(mt.get("window_exposure", "none")).strip().lower()
    flags = []

    # POST_HOC_ONLY is a declared usage restriction, not a computed verdict
    if role == "post_hoc_writing":
        return {"verdict": POST_HOC_ONLY,
                "detail": "declared post-hoc writing of frozen results only",
                "flags": ["role=post_hoc_writing"]}

    if exposure in ("yes", "true", "claimed"):
        v = INELIGIBLE if role not in ("engineering",) else CONDITIONAL
        flags.append("window_exposure_claimed")
        return {"verdict": v,
                "detail": f"claimed exposure to study window; role={role}",
                "flags": flags}

    # provenance sanity: model must exist at decision time
    if decision and release and release > decision.date():
        flags.append("release_after_decision")
        v = UNKNOWN if role in DESIGN_ROLES else CONDITIONAL
        return {"verdict": v,
                "detail": f"release_date {release} > decision_time {decision.date()}",
                "flags": flags}
    if retrieval and decision and retrieval > decision:
        flags.append("retrieval_after_decision")
        # retrieval after decision cannot inform that decision; recorded, no
        # verdict change by itself (cutoff governs knowledge).

    if not cv or cv == "unverifiable":
        if role in DESIGN_ROLES:
            return {"verdict": UNKNOWN,
                    "detail": "closed/unverifiable cutoff + design/judgment role -> "
                              "never auto-PASS (RQ-08 rule)",
                    "flags": flags}
        return {"verdict": CONDITIONAL,
                "detail": "unverifiable cutoff; engineering/analysis role allowed "
                          "CONDITIONAL with disclosure",
                "flags": flags + ["role_disclosure_required"]}

    # verifiable (published)
    if role == "engineering":
        return {"verdict": ELIGIBLE, "detail": "engineering role",
                "flags": flags}
    if cutoff is None:
        return {"verdict": UNKNOWN, "detail": "published but cutoff unparsed",
                "flags": flags}
    if ws is None:
        return {"verdict": UNKNOWN, "detail": "window_start unavailable",
                "flags": flags}
    eff = cutoff + _dt.timedelta(days=MARGIN_DAYS)
    if eff <= ws:
        return {"verdict": ELIGIBLE,
                "detail": f"cutoff+margin({MARGIN_DAYS}d) <= window_start",
                "flags": flags}
    return {"verdict": CONDITIONAL,
            "detail": "cutoff inside margin or after window start -> requires "
                      "retrieval log + human sign-off for design/judgment",
            "flags": flags + ["retrieval_log_required"]}


def blocks(v: dict, role: str) -> bool:
    return role in DESIGN_ROLES and v["verdict"] in (UNKNOWN, INELIGIBLE)
