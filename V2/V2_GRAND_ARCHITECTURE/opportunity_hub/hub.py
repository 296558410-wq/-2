"""Opportunity Hub.

Replaces the single-source "Opportunity Discovery" with multiple independent
sources. Original Discovery is preserved as `Reference`. Flow:
Generate -> Rank -> Filter -> Strategy Brain.

No single source may monopolize opportunities long-term; the hub reports a
concentration metric and never lowers thresholds to manufacture trade count.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np

SOURCES = ["TECHNICAL", "MOMENTUM", "REVERSAL", "BREAKOUT", "VOLATILITY",
           "MACRO", "EVENT", "STRUCTURE"]


@dataclass
class Opportunity:
    source: str
    bar_time: str
    direction: int
    strength: float
    regime: str

    def to_dict(self):
        return asdict(self)


def generate(df, i: int) -> list[Opportunity]:
    """All independent sources evaluated at bar i (PIT columns only)."""
    r = df.iloc[i]
    t = str(r["bar_end_utc"])
    regime = r["regime"]
    out: list[Opportunity] = []

    def add(src, d, s):
        if d != 0 and np.isfinite(s) and s > 0:
            out.append(Opportunity(src, t, int(d), float(s), regime))

    ts = r["trend_strength"]
    if np.isfinite(ts):
        add("TECHNICAL", np.sign(ts), abs(ts))
    z20 = r["ret20"] / r["atr14"] if np.isfinite(r["atr14"]) and r["atr14"] else np.nan
    add("MOMENTUM", np.sign(z20), abs(z20) if np.isfinite(z20) else np.nan)
    add("REVERSAL", -np.sign(z20), abs(z20) if np.isfinite(z20) else np.nan)
    if np.isfinite(r["hh20"]) and np.isfinite(r["ll20"]):
        if r["close"] > r["hh20"]:
            add("BREAKOUT", 1, 1.0)
        elif r["close"] < r["ll20"]:
            add("BREAKOUT", -1, 1.0)
    if np.isfinite(r["vol_ratio"]):
        add("VOLATILITY", int(np.sign(r["vol_ratio"] - 1.2)) or 1, abs(r["vol_ratio"] - 1.0))
    if np.isfinite(r["ma60"]) and np.isfinite(r["atr14"]) and r["atr14"]:
        add("MACRO", np.sign(r["close"] - r["ma60"]), abs(r["close"] - r["ma60"]) / r["atr14"])
    if np.isfinite(r["atr14"]):
        step = r["close"] - df["close"].iloc[i - 1] if i > 0 else 0.0
        if r["atr14"] and abs(step) > 1.5 * r["atr14"]:
            add("EVENT", np.sign(step), abs(step) / r["atr14"])
    if np.isfinite(r["ret5"]) and np.isfinite(r["ret60"]):
        add("STRUCTURE", np.sign(r["ret5"] + r["ret60"]), abs(r["ret5"] + r["ret60"]) / (r["atr14"] or 1))
    return out


def rank(opps: list[Opportunity]) -> list[Opportunity]:
    return sorted(opps, key=lambda o: -o.strength)


def concentration(opps_over_time: list[list[Opportunity]]) -> dict:
    counts = {s: 0 for s in SOURCES}
    for row in opps_over_time:
        for o in row:
            counts[o.source] = counts.get(o.source, 0) + 1
    total = sum(counts.values())
    return {
        "counts": counts,
        "total": total,
        "max_share": (max(counts.values()) / total) if total else 0.0,
        "source_used": [s for s, c in counts.items() if c > 0],
    }
