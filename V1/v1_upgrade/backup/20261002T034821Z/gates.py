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
from datetime import datetime, timezone

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
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.day = None

    def set_kill_switch(self, on: bool, reason: str = ""):
        self.kill_switch = bool(on)
        self.kill_reason = reason

    def roll_day(self, day):
        if day != self.day:
            self.day, self.daily_loss, self.consecutive_losses = day, 0.0, 0

    def note_close(self, pnl):
        self.daily_loss += float(pnl)
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def evaluate(self, intent, market, open_positions):
        r = []
        if self.kill_switch:
            r.append("KILL_SWITCH")
        if open_positions >= self.cfg["max_position"]:
            r.append("MAX_POSITION")
        if self.daily_loss <= self.cfg["max_daily_loss"]:
            r.append("MAX_DAILY_LOSS")
        if self.consecutive_losses >= self.cfg["max_consecutive_loss"]:
            r.append("MAX_CONSECUTIVE_LOSS")
        sp = float(market.get("spread_bps", 0) or 0)
        if sp > self.cfg["spread_limit_bps"]:
            r.append("SPREAD_LIMIT")
        sl = float(market.get("slippage_bps", 0) or 0)
        if sl > self.cfg["slippage_limit_bps"]:
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
