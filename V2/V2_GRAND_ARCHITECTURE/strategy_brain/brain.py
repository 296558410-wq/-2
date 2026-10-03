"""Multi-Strategy Brain.

Inputs: market state + opportunities + each strategy's prediction/confidence/
recent performance/long-term stability + cost + regime + risk state.
Outputs: strategy_candidates, direction, confidence, evidence, counter_evidence,
conflict_state, final_decision.

Never forces a trade. Absence of agreeing strategies, hard conflict, or a data
gap all yield WAIT (or WAIT/DATA_GAP).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class StrategyVote:
    strategy_id: str
    mechanism: str
    direction: int  # -1/0/+1
    confidence: float  # 0..1
    regime_fit: float  # 0..1 (1 if current regime in applicable_regime)
    recent_stability: float  # 0..1


@dataclass
class BrainDecision:
    direction: int
    confidence: float
    conflict_state: str
    final_decision: str  # ENTER_LONG / ENTER_SHORT / WAIT / WAIT_DATA_GAP
    strategy_candidates: list
    evidence: list
    counter_evidence: list


CONFLICT_AGREE = "AGREEMENT"
CONFLICT_CONFLICT = "CONFLICT"
CONFLICT_ABSENT = "ABSENT"
CONFLICT_DATA_GAP = "DATA_GAP"


def decide(votes: list[StrategyVote], data_ok: bool = True,
           risk_allows: bool = True, min_votes: int = 2,
           min_confidence: float = 0.55) -> BrainDecision:
    if not data_ok:
        return BrainDecision(0, 0.0, CONFLICT_DATA_GAP, "WAIT_DATA_GAP", [], [], [])
    if not votes:
        return BrainDecision(0, 0.0, CONFLICT_ABSENT, "WAIT", [], [], [])

    longs = [v for v in votes if v.direction > 0]
    shorts = [v for v in votes if v.direction < 0]
    active = longs + shorts

    # weighted score
    def w(v):
        return max(0.0, v.confidence) * max(0.0, v.regime_fit) * max(0.0, v.recent_stability)

    long_score = sum(w(v) for v in longs)
    short_score = sum(w(v) for v in shorts)
    total = long_score + short_score

    if len(longs) and len(shorts):
        # genuine conflict
        if total == 0 or min(long_score, short_score) / total > 0.3:
            return BrainDecision(0, 0.0, CONFLICT_CONFLICT, "WAIT",
                                 [v.strategy_id for v in active],
                                 [f"{len(longs)} long", f"{len(shorts)} short"],
                                 ["directional conflict above threshold"])
        conflict_state = CONFLICT_CONFLICT
    else:
        conflict_state = CONFLICT_AGREE

    direction = 1 if long_score > short_score else (-1 if short_score > long_score else 0)
    winning = longs if direction > 0 else shorts
    if len(winning) < min_votes:
        return BrainDecision(0, 0.0, CONFLICT_ABSENT, "WAIT",
                             [v.strategy_id for v in active], ["insufficient agreeing strategies"], [])
    conf = (max(long_score, short_score) / total) if total > 0 else 0.0
    if conf < min_confidence or direction == 0:
        final = "WAIT"
    elif not risk_allows:
        final = "WAIT"
    else:
        final = "ENTER_LONG" if direction > 0 else "ENTER_SHORT"

    evidence = [f"{v.strategy_id}({v.mechanism}) conf={v.confidence:.2f} fit={v.regime_fit:.2f}"
                for v in winning]
    counter = [f"{v.strategy_id} opposite" for v in (shorts if direction > 0 else longs)]
    return BrainDecision(direction, round(float(conf), 3), conflict_state, final,
                         [v.strategy_id for v in winning], evidence, counter)


def vote_from_signal(strategy_id: str, mechanism: str, signal_val: float,
                     confidence: float, regime: str, applicable: list[str],
                     recent_stability: float) -> StrategyVote:
    direction = int(np.sign(signal_val))
    fit = 1.0 if regime in applicable else 0.35
    return StrategyVote(strategy_id, mechanism, direction,
                        float(confidence), fit, float(recent_stability))
