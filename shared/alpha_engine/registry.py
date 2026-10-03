# -*- coding: utf-8 -*-
"""alpha_engine/registry.py — Alpha Registry（§17）。

目录：C:\AIQuant\alpha_registry\candidates.json + alpha_registry/<alpha_id>.json
状态机：DISCOVERED → TESTING → SUPPORTED | EDGE_UNCERTAIN | REJECTED
SUPPORTED 仅表示“在当前研究协议下存在较强证据”，不等于可交易。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALPHA_ROOT = ROOT / "alpha_registry"
CANDIDATES = ALPHA_ROOT / "candidates.json"


def _load() -> dict:
    if CANDIDATES.exists():
        return json.loads(CANDIDATES.read_text(encoding="utf-8"))
    return {"updated_at": "", "candidates": {}}


def _save(db: dict) -> None:
    ALPHA_ROOT.mkdir(parents=True, exist_ok=True)
    db["updated_at"] = datetime.now(timezone.utc).isoformat()
    CANDIDATES.write_text(json.dumps(db, ensure_ascii=False, indent=2, default=str),
                          encoding="utf-8")


def register_candidate(alpha_id: str, record: dict) -> dict:
    """record 至少含 §17 字段：hypothesis/features/parameters/dataset/
    train_period/test_period/OOS/FDR/WF/cost_stress/subperiod/status/git_commit"""
    db = _load()
    rec = {**record, "alpha_id": alpha_id,
           "created_at": datetime.now(timezone.utc).isoformat(),
           "git_commit": record.get("git_commit", "no-git")}
    db["candidates"][alpha_id] = rec
    _save(db)
    p = ALPHA_ROOT / f"{alpha_id}.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return rec


def update_status(alpha_id: str, status: str, note: str = "") -> dict:
    db = _load()
    if alpha_id not in db["candidates"]:
        raise KeyError(alpha_id)
    rec = db["candidates"][alpha_id]
    rec["status"] = status
    if note:
        rec["status_note"] = note
    rec["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(db)
    return rec


def summary() -> dict:
    db = _load()
    cands = db["candidates"]
    from collections import Counter
    return {"n": len(cands), "by_status": dict(Counter(c["status"] for c in cands.values()))}
