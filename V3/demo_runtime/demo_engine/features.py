from __future__ import annotations
import math
from collections import deque
from dataclasses import dataclass
from .common import finite, digest

NAMES = ('spread_bp', 'spread_change_200t', 'quote_arrival_1s', 'recent_return_1s',
         'recent_volatility_50t', 'mid_return_1s', 'displacement_5s', 'mom_3t', 'mom_10t',
         'rev_5t', 'overshoot_z', 'rv_50t', 'absret_10t', 'tick_rule_proxy_20t', 'tick_rule_proxy_50t')
SCHEMA = dict(version='v3-demo-features/1', names=list(NAMES), unit='returns_in_bp',
              windows='past-and-present ticks only', tick_rule='PRICE_DIRECTION_PROXY_NOT_TRUE_OFI',
              minimum_ticks=201, max_window_ms=300000)
SCHEMA_HASH = digest(SCHEMA)


@dataclass(frozen=True)
class Tick:
    timestamp_ms: int
    bid: float
    ask: float

    @property
    def mid(self):
        return (self.bid + self.ask) / 2

    @property
    def key(self):
        return self.timestamp_ms, self.bid, self.ask


class Features:
    def __init__(self):
        self.ticks = deque(maxlen=4096)
        self.last = None
        self.duplicates = self.regressions = self.invalid = 0

    def add(self, tick):
        if not finite(tick.bid) or not finite(tick.ask) or tick.bid <= 0 or tick.ask < tick.bid:
            self.invalid += 1
            return False
        if self.last and tick.timestamp_ms < self.last.timestamp_ms:
            self.regressions += 1
            return False
        if self.last and tick.key == self.last.key:
            self.duplicates += 1
            return False
        if self.last and tick.timestamp_ms - self.last.timestamp_ms > 5000:
            self.ticks.clear()
        self.ticks.append(tick)
        self.last = tick
        while self.ticks and tick.timestamp_ms - self.ticks[0].timestamp_ms > 300000:
            self.ticks.popleft()
        return True

    def vector(self):
        if len(self.ticks) < 201:
            return None
        rows = list(self.ticks)
        now, mid = rows[-1].timestamp_ms, rows[-1].mid
        def lag(ms):
            target = now - ms
            for t in reversed(rows):
                if t.timestamp_ms <= target:
                    return t
            return None
        one, five = lag(1000), lag(5000)
        if one is None or five is None or now - one.timestamp_ms > 2000 or now - five.timestamp_ms > 6000:
            return None
        mids = [t.mid for t in rows[-51:]]
        returns = [(b / a - 1) * 10000 for a, b in zip(mids, mids[1:])]
        mean_r = sum(returns) / len(returns)
        std = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns))
        rv = math.sqrt(sum(r*r for r in returns) / len(returns))
        mean_m = sum(mids) / len(mids)
        sd_m = math.sqrt(sum((x - mean_m) ** 2 for x in mids) / len(mids))
        signs = [1 if r > 0 else -1 if r < 0 else 0 for r in returns]
        previous = rows[-201]
        r1 = (mid / one.mid - 1) * 10000
        values = [(rows[-1].ask - rows[-1].bid) / mid * 10000,
                  ((rows[-1].ask - rows[-1].bid) - (previous.ask - previous.bid)) / mid * 10000,
                  sum(t.timestamp_ms > now - 1000 for t in rows), r1, std, r1,
                  (mid / five.mid - 1) * 10000,
                  (mid / rows[-4].mid - 1) * 10000,
                  (mid / rows[-11].mid - 1) * 10000,
                  -(mid / rows[-6].mid - 1) * 10000,
                  (mid - mean_m) / sd_m if sd_m > 0 else 0., rv,
                  sum(abs(r) for r in returns[-10:]) / 10,
                  sum(signs[-20:]) / 20, sum(signs[-50:]) / 50]
        if not all(finite(v) for v in values):
            return None
        return values
