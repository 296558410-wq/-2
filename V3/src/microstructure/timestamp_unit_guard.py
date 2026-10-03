"""timestamp_unit_guard — V3-HFT-DATA-EXECUTION-GAP-CLOSURE-001 (task IX/X).

HARD RULE: **no silent unit inference.**
Every timestamp read must declare its unit and timezone. If the unit cannot be
determined, the result is `DATA_INVALID` — never a guess.

Supported units: "ms" (milliseconds), "us" (microseconds), "ns" (nanoseconds).

Regression facts (asserted by the test suite):
    1000 ms == 1 second
    1_000_000 us == 1 second
    1_000_000_000 ns == 1 second
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

UNIT_TO_NS = {"ms": 1_000_000, "us": 1_000, "ns": 1}
SUPPORTED_UNITS = tuple(UNIT_TO_NS)
DATA_INVALID = "DATA_INVALID"


class TimestampUnitError(ValueError):
    """Raised when a timestamp unit is missing or unsupported."""


def require_unit(unit):
    """Return the unit or raise. Never infer."""
    if unit is None:
        raise TimestampUnitError(f"{DATA_INVALID}: timestamp unit not declared")
    if unit not in UNIT_TO_NS:
        raise TimestampUnitError(f"{DATA_INVALID}: unsupported unit {unit!r}; use {SUPPORTED_UNITS}")
    return unit


def ns_per_unit(unit):
    return UNIT_TO_NS[require_unit(unit)]


def to_ns(values, unit):
    """Integer epoch values in `unit` -> int64 nanoseconds."""
    return np.asarray(values, np.int64) * ns_per_unit(unit)


def to_seconds(values, unit):
    return np.asarray(values, np.float64) * ns_per_unit(unit) / 1e9


def to_utc(values, unit):
    """Integer epoch values in `unit` -> tz-aware UTC DatetimeIndex."""
    ns = to_ns(values, unit)
    return pd.to_datetime(ns, unit="ns", utc=True)


def describe(series: pd.Series, unit):
    """Explicit descriptor. `unit` must be supplied by the caller."""
    require_unit(unit)
    dtype = str(series.dtype)
    tz = getattr(series.dt, "tz", None) if pd.api.types.is_datetime64_any_dtype(series) else None
    return {"timestamp_unit": unit, "timestamp_timezone": str(tz) if tz is not None else "UTC",
            "timestamp_dtype": dtype, "n": int(len(series))}


def assert_monotonic(ts_ns):
    t = np.asarray(ts_ns, np.int64)
    d = np.diff(t)
    bad = int((d < 0).sum())
    return {"monotonic": bad == 0, "violations": bad}


def find_future(ts_ns, now_ns=None):
    """Count timestamps that are in the future (sign of a unit/clock bug)."""
    t = np.asarray(ts_ns, np.int64)
    now = now_ns if now_ns is not None else int(dt.datetime.now(dt.timezone.utc).timestamp() * 1e9)
    n = int((t > now).sum())
    return {"future_count": n, "max_ns": int(t.max()) if t.size else None, "now_ns": int(now)}


def range_check(ts_ns, lo_ns, hi_ns):
    t = np.asarray(ts_ns, np.int64)
    n = int(((t < lo_ns) | (t > hi_ns)).sum())
    return {"out_of_range": n, "lo_ns": int(lo_ns), "hi_ns": int(hi_ns)}


def read_timestamp(series: pd.Series, unit, tz="UTC"):
    """The ONLY sanctioned way to enter a timestamp into research.

    Returns a dict with int64 ns + an explicit descriptor. Raises on missing unit.
    """
    require_unit(unit)
    if tz != "UTC":
        raise TimestampUnitError("only UTC is accepted for research timestamps")
    if pd.api.types.is_datetime64_any_dtype(series):
        s = series
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_convert("UTC").dt.tz_localize(None)   # -> naive UTC
        ns = s.astype("datetime64[ns]").astype("int64").to_numpy()
        return {"ts_ns": ns.astype(np.int64), "descriptor": describe(series, unit)}
    if pd.api.types.is_integer_dtype(series):
        return {"ts_ns": to_ns(series.to_numpy(), unit), "descriptor": describe(series, unit)}
    raise TimestampUnitError(f"{DATA_INVALID}: unsupported timestamp dtype {series.dtype}")
