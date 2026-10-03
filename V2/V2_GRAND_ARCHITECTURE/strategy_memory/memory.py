"""Strategy Memory.

Records every prediction with the market state at that moment, and later the
realized outcome (MFE/MAE/failure type), so each strategy builds a lifecycle
profile. NO OUTCOME LEAKAGE: predictions are stored before the outcome is known;
any read used for a decision at time t only exposes records with outcome_time < t.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone


class StrategyMemory:
    def __init__(self, path: str):
        self.path = path
        self.records: list[dict] = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.records.append(json.loads(line))

    def record_prediction(self, *, strategy_id: str, decision_time: str, direction: int,
                          confidence: float, regime: str, price: float, horizon: int,
                          strategy_age_bars: int) -> dict:
        rec = {
            "strategy_id": strategy_id,
            "decision_time": decision_time,
            "direction": direction,
            "confidence": confidence,
            "regime": regime,
            "price_at_decision": price,
            "horizon": horizon,
            "strategy_age_bars": strategy_age_bars,
            "outcome_time": None,   # filled later -> no leakage
            "mfe": None, "mae": None, "net": None, "failure_type": None,
        }
        self.records.append(rec)
        return rec

    def attach_outcome(self, idx: int, *, outcome_time: str, mfe: float, mae: float,
                       net: float, failure_type: str | None) -> None:
        r = self.records[idx]
        r["outcome_time"] = outcome_time
        r["mfe"] = mfe
        r["mae"] = mae
        r["net"] = net
        r["failure_type"] = failure_type

    def as_of(self, t_iso: str) -> list[dict]:
        """Only outcomes strictly before t are visible (PIT-safe read)."""
        tt = datetime.fromisoformat(t_iso)
        out = []
        for r in self.records:
            ot = r.get("outcome_time")
            if ot is None:
                continue
            try:
                if datetime.fromisoformat(ot) < tt:
                    out.append(r)
            except ValueError:
                continue
        return out

    def flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
