# -*- coding: utf-8 -*-
"""v1_upgrade — core safety primitives (fail-closed).

LEDGER      : independent SHA256-chained ledger with replay.
RISK_GUARD  : max_position / max_daily_loss / max_consecutive_loss / spread / slippage / stale data /
              duplicate order / kill switch. Any breach => deny new entries.
DEMO_GATE   : DEMO-only assertion + isolation assertion (magic/comment/instance). Fail-closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone

GENESIS = "0" * 64
EVENTS = ["DECISION", "ORDER_CHECK", "ORDER_REQUEST", "ORDER_SEND", "FILL", "POSITION", "CLOSE", "PNL"]
RESERVED_MAGIC = {90001: "v1_collect_measure", 90002: "OLD_V1_execution", 90003: "V2_execution"}
MAGIC = 90011              # NEW V1
COMMENT = "V1UP_DEMO"


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def _last(self):
        prev, seq = GENESIS, 0
        if os.path.exists(self.path):
            for line in open(self.path, encoding="utf-8"):
                line = line.strip()
                if line:
                    e = json.loads(line); prev = e["current_hash"]; seq = e["seq"]
        return prev, seq

    def append(self, event, **fields):
        assert event in EVENTS, f"unknown event {event}"
        prev, seq = self._last()
        rec = {"seq": seq + 1, "ts_utc": datetime.now(timezone.utc).isoformat(), "event": event,
                "previous_hash": prev, **fields}
        rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush(); os.fsync(fh.fileno())
        return rec

    def verify(self):
        prev, n, ok = GENESIS, 0, True
        bad = None
        if not os.path.exists(self.path):
            return True, 0, None
        for line in open(self.path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:  # noqa: BLE001
                return False, n, "MALFORMED_LINE"
            n += 1
            if e.get("previous_hash") != prev or e.get("current_hash") != sha_obj({k: v for k, v in e.items() if k != "current_hash"}):
                ok = False; bad = f"chain mismatch at seq {e.get('seq')} ({e.get('event')})"; break
            prev = e["current_hash"]
        return ok, n, bad

    def replay(self):
        """Rebuild positions / realized pnl strictly from the ledger."""
        open_pos, realized, sent = {}, 0.0, set()
        if not os.path.exists(self.path):
            return {"open_positions": {}, "realized_pnl": 0.0, "events": 0, "sends": 0}
        n = 0
        for line in open(self.path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            e = json.loads(line); n += 1
            ev = e["event"]
            if ev == "ORDER_SEND":
                sent.add(e.get("order_id")); open_pos[e.get("order_id")] = {"side": e.get("side"), "qty": e.get("qty"), "entry": e.get("price")}
            elif ev == "CLOSE":
                open_pos.pop(e.get("order_id"), None)
            elif ev == "PNL":
                realized += float(e.get("pnl") or 0.0)
        return {"open_positions": open_pos, "realized_pnl": round(realized, 6), "events": n, "sends": len(sent)}


class RiskGuard:
    """Every limit is a hard deny for NEW entries; breaches never auto-close (broker SL/TP owns that)."""
    def __init__(self, cfg=None):
        c = {"max_position": 1, "max_daily_loss": -20.0, "max_consecutive_loss": 3,
              "spread_limit_bps": 30.0, "slippage_limit_bps": 15.0, "stale_data_seconds": 900}
        c.update(cfg or {})
        self.cfg = c
        self.kill_switch = False
        self.kill_reason = ""
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.day = None
        self.unavailable = []          # fail-closed: safety inputs that could NOT be determined

    def set_kill_switch(self, on: bool, reason: str = ""):
        self.kill_switch = bool(on)
        self.kill_reason = reason

    def note_unavailable(self, reason: str):
        """Record an un-determinable safety input; evaluate() will deny (fail-closed)."""
        if reason and reason not in self.unavailable:
            self.unavailable.append(reason)

    def roll_day(self, day):
        if day != self.day:
            self.day, self.daily_loss, self.consecutive_losses = day, 0.0, 0

    def note_close(self, pnl):
        self.daily_loss += float(pnl)
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def evaluate(self, intent, market, open_positions):
        r = list(self.unavailable)          # fail-closed inputs (unknown state => deny)
        if self.kill_switch:
            r.append("KILL_SWITCH")
        if open_positions is None:
            r.append("POSITION_STATE_UNKNOWN")
        elif open_positions >= self.cfg["max_position"]:
            r.append("MAX_POSITION")
        if self.daily_loss <= self.cfg["max_daily_loss"]:
            r.append("MAX_DAILY_LOSS")
        if self.consecutive_losses >= self.cfg["max_consecutive_loss"]:
            r.append("MAX_CONSECUTIVE_LOSS")
        sp = market.get("spread_bps")
        if sp is not None and float(sp) > self.cfg["spread_limit_bps"]:
            r.append("SPREAD_LIMIT")
        sl = market.get("slippage_bps")
        if sl is None:
            r.append("SLIPPAGE_UNKNOWN")    # fail-closed: unknown slippage must not default to 0
        elif float(sl) > self.cfg["slippage_limit_bps"]:
            r.append("SLIPPAGE_LIMIT")
        age = market.get("data_age_seconds")
        if age is None or float(age) > self.cfg["stale_data_seconds"]:
            r.append("STALE_DATA")
        if intent.get("order_id") in (intent.get("already_sent") or set()):
            r.append("DUPLICATE_ORDER")
        return (len(r) == 0, r)


class DemoGate:
    """Fail-closed. Refuses to authorise execution unless the account is DEMO and the namespace is isolated."""
    @staticmethod
    def assert_demo(account_info):
        if not account_info:
            return False, "NO_ACCOUNT_INFO"
        mode = account_info.get("trade_mode")
        if mode != "DEMO":
            return False, f"NOT_DEMO:{mode}"
        if account_info.get("real_money") or account_info.get("live"):
            return False, "REAL_MONEY_FLAG"
        return True, "DEMO_OK"

    @staticmethod
    def assert_isolation(instance_dir, magic=MAGIC, comment=COMMENT):
        problems = []
        if magic in RESERVED_MAGIC:
            problems.append(f"MAGIC_RESERVED:{RESERVED_MAGIC[magic]}")
        if not instance_dir or not os.path.isdir(instance_dir):
            problems.append("INSTANCE_DIR_MISSING")
        else:
            try:
                ins = sorted(os.listdir(os.path.join(instance_dir, "..")))
            except Exception:  # noqa: BLE001
                ins = []
            name = os.path.basename(os.path.normpath(instance_dir))
            old = {"fxtm_demo_01", "fxtm_demo_v3", "fxtm_demo_v3calib"}
            if name in old:
                problems.append(f"INSTANCE_SHARED_WITH_EXISTING:{name}")
        if comment != COMMENT:
            problems.append("COMMENT_MISMATCH")
        return (len(problems) == 0, problems)


# ---------------------------------------------------------------------------------------------
# Risk-state rebuild + real-input helpers (V1 risk-guard wiring fix, operator-authorised 2026-10-02)
# Rebuild the RiskGuard counters from ledger CLOSE/PNL facts; supply same-source staleness and the
# last realised fill slippage. No limit value, alpha, mapping or execution path is changed here:
# these helpers only make the already-declared guards able to fire (fail-closed, deny-only).
# ---------------------------------------------------------------------------------------------
SERVER_OFFSET_SEC = 10800          # FXTM demo server frame = UTC+3 (audit §9)


def realized_close_utc(ev, server_offset_sec=SERVER_OFFSET_SEC):
    """UTC instant at which the broker realised the close (broker_time_utc is server frame)."""
    s = ev.get("broker_time_utc")
    if s:
        return datetime.fromisoformat(s) - timedelta(seconds=server_offset_sec)
    return datetime.fromisoformat(ev["ts_utc"])


def realized_pnl(ev, basis="net"):
    """Realised PnL of a PNL event. basis='net' adds commission/swap when recorded on the event."""
    price = float(ev.get("pnl") or 0.0)
    if basis != "net":
        return price
    c, s = ev.get("commission"), ev.get("swap")
    if c is None and s is None:
        return price            # cost not recorded on the event -> price component (documented)
    return price + float(c or 0.0) + float(s or 0.0)


def rebuild_risk_state(rg, events, day, basis="net", server_offset_sec=SERVER_OFFSET_SEC):
    """Rebuild daily_loss / consecutive_losses for `day` (UTC = NOW[:10]) from ledger PNL facts.

    Only closes realised on `day` count (engine semantics: roll_day resets both counters at the
    day boundary). Deterministic and idempotent: same ledger -> same counters.
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
    """Real staleness, SAME-SOURCE server frame (fixes the old UTC/server mixed -10590 bug).

    Age = now(server) - close time(server) of the last COMPLETED M1 bar. None if unusable
    (callers feed None into the guard, which returns STALE_DATA => deny).
    """
    if tick_server_time is None or m1_bars is None or len(m1_bars) < 2:
        return None
    return float(int(tick_server_time) - (int(m1_bars[-2]["time"]) + 60))


def last_realized_slippage_bps(events):
    """Most recent realised fill slippage from ORDER_SEND facts; None if never measured."""
    val = None
    for e in events:
        if e.get("event") == "ORDER_SEND" and e.get("slippage_bps") is not None:
            val = float(e["slippage_bps"])
    return val


# ---------------------------------------------------------------------------------------------
# Risk hardening helpers (operator-authorised 2026-10-02): kill switch, duplicate-order dedup,
# fail-closed input availability. Deny-only: they can only make the guard reject more.
# ---------------------------------------------------------------------------------------------
KILL_SWITCH_FILE = "kill_switch.json"      # in registry/; MISSING => OFF, UNREADABLE => ON


def load_kill_switch(registry_dir):
    """Read the operator kill switch. Missing => (False, ''). Unreadable/corrupt => (True, reason)."""
    p = os.path.join(registry_dir, KILL_SWITCH_FILE)
    if not os.path.exists(p):
        return False, ""
    try:
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d, dict):
            return bool(d.get("on")), str(d.get("reason", ""))
        return bool(d), "KILL_SWITCH_NON_DICT"
    except Exception:  # noqa: BLE001
        return True, "KILL_SWITCH_UNREADABLE"     # fail-closed


def dedup_key(magic, symbol, bucket):
    """Stable entry identity: one entry per symbol per M15 bucket (server frame)."""
    return f"{magic}:{symbol}:{bucket}"


def bar_bucket(m1_bars, period_sec=900):
    """Server-frame bucket start of the period containing the last COMPLETED M1 bar (deterministic)."""
    if m1_bars is None or len(m1_bars) < 2:
        return None
    close_t = int(m1_bars[-2]["time"]) + 60
    return int(close_t // period_sec * period_sec)


def rebuild_sent_keys(events):
    """Set of dedup keys already sent (for DUPLICATE_ORDER), rebuilt from ORDER_SEND facts (persisted)."""
    keys = set()
    for e in events:
        if e.get("event") == "ORDER_SEND" and e.get("ok") and e.get("dedup_key"):
            keys.add(str(e["dedup_key"]))
    return keys


def broker_recent_order_dup(broker_orders, magic, symbol, bucket_start):
    """Broker-side duplicate: an order for this magic/symbol already done in/below the bucket
    (covers 'broker filled but local ledger did not record it'). broker_orders = list of dicts."""
    if not broker_orders or bucket_start is None:
        return False
    for o in broker_orders:
        try:
            if (int(o.get("magic") or 0) == int(magic) and str(o.get("symbol") or "") == str(symbol)
                    and int(o.get("time_done") or 0) >= int(bucket_start)):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False
