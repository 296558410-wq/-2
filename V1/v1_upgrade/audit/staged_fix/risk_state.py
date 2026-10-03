# -*- coding: utf-8 -*-
"""risk_state.py — STAGED, NOT WIRED. Drop-in helpers for the V1 risk-guard wiring fix.

This module does NOT modify production code. It uses the production `gates.RiskGuard`
unmodified and only (a) rebuilds its counters from ledger facts and (b) derives the real
`data_age_seconds` / `slippage_bps` inputs. On approval these functions move into
`gates.py` (`rebuild_risk_state`) and `cycle.py` (feed real inputs), per
audit/staged_fix/PATCHES.md.

Design (per task book, minimal, fail-closed):
  * state persistence  : replay CLOSE/PNL facts from the SHA256 ledger (no new state file).
  * realized pnl       : broker fact; `basis="net"` = profit + commission + swap.
  * day boundary/frame : UTC date of the BROKER close time (server frame UTC+3 -> UTC),
                         i.e. the same frame the audit used for the -19.70 figure.
  * data_age_seconds   : same-source (server frame) tick.time - last COMPLETED M1 bar close.
  * slippage_bps       : most recent realized ORDER_SEND slippage from the ledger.
No limit value, alpha, mapping, or execution path is changed; guards only ever deny more.
"""
from __future__ import annotations

import datetime as dt

from gates import RiskGuard

SERVER_OFFSET_SEC = 10800          # FXTM demo server frame = UTC+3 (audit §9)


def realized_close_utc(ev, server_offset_sec=SERVER_OFFSET_SEC):
    """UTC instant at which the broker realized the close. broker_time_utc is server frame."""
    s = ev.get("broker_time_utc")
    if s:
        return dt.datetime.fromisoformat(s) - dt.timedelta(seconds=server_offset_sec)
    return dt.datetime.fromisoformat(ev["ts_utc"])


def realized_pnl(ev, basis="net"):
    """Realized PnL of a PNL event. basis='net' adds commission/swap when present."""
    price = float(ev.get("pnl") or 0.0)
    if basis != "net":
        return price
    c, s = ev.get("commission"), ev.get("swap")
    if c is None and s is None:
        return price            # cost not recorded on the event -> price component (documented)
    return price + float(c or 0.0) + float(s or 0.0)


def rebuild_risk_state(rg: RiskGuard, events, day, basis="net", server_offset_sec=SERVER_OFFSET_SEC):
    """Rebuild daily_loss / consecutive_losses for `day` (UTC, NOW[:10]) from ledger PNL facts.

    Only closes realized on `day` count (engine semantics: roll_day resets both counters at
    the day boundary). Deterministic and idempotent: same ledger -> same counters.
    """
    day_closes = []
    for e in events:
        if e.get("event") != "PNL":
            continue
        utc = realized_close_utc(e, server_offset_sec)
        if utc.date().isoformat() == day:
            day_closes.append((utc, realized_pnl(e, basis)))
    day_closes.sort(key=lambda t: t[0])
    rg.roll_day(day)
    for _, pnl in day_closes:
        rg.note_close(pnl)
    return rg


def data_age_seconds(tick_server_time, m1_bars):
    """Real staleness, SAME-SOURCE server frame (fixes the old mixed UTC/server -10590 bug).

    Age = now(server) - close time(server) of the last COMPLETED M1 bar. m1_bars is the
    MetaTrader5 rate array (oldest..newest, newest may be the forming bar). None if unusable.
    """
    if tick_server_time is None or m1_bars is None or len(m1_bars) < 2:
        return None
    last_completed_close = int(m1_bars[-2]["time"]) + 60
    return float(int(tick_server_time) - last_completed_close)


def last_realized_slippage_bps(events):
    """Most recent realized fill slippage from ORDER_SEND facts; None if never measured."""
    val = None
    for e in events:
        if e.get("event") == "ORDER_SEND" and e.get("slippage_bps") is not None:
            val = float(e["slippage_bps"])
    return val
