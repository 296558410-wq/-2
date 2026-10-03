# PATCHES.md — STAGED, NOT APPLIED. Exact production diff for the V1 risk-guard wiring fix.

> Status: **awaiting operator consent** (task book: "必须先获用户同意再动手"). Nothing below is applied.
> Applied = copy the three `gates.py` helpers in, make the `cycle.py` edits, add the `reconcile` fields.
> No limit value, alpha, mapping, prompt, threshold, or execution path changes. Guards only deny *more*.

## A. `gates.py` — add rebuild + real-input helpers (append after `class RiskGuard`)

Add `timedelta` to the existing import (`from datetime import datetime, timezone` → `..., timedelta, timezone`), then:

```python
SERVER_OFFSET_SEC = 10800          # FXTM demo server frame = UTC+3 (audit §9)

def realized_close_utc(ev, server_offset_sec=SERVER_OFFSET_SEC):
    s = ev.get("broker_time_utc")
    if s:
        return datetime.fromisoformat(s) - timedelta(seconds=server_offset_sec)
    return datetime.fromisoformat(ev["ts_utc"])

def realized_pnl(ev, basis="net"):
    price = float(ev.get("pnl") or 0.0)
    if basis != "net":
        return price
    c, s = ev.get("commission"), ev.get("swap")
    if c is None and s is None:
        return price            # cost not recorded on the event -> price component (documented)
    return price + float(c or 0.0) + float(s or 0.0)

def rebuild_risk_state(rg, events, day, basis="net", server_offset_sec=SERVER_OFFSET_SEC):
    """Rebuild daily_loss / consecutive_losses for `day` (UTC = NOW[:10]) from ledger PNL facts."""
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
    """Real staleness, SAME-SOURCE server frame (fixes the old UTC/server mixed -10590 bug)."""
    if tick_server_time is None or m1_bars is None or len(m1_bars) < 2:
        return None
    return float(int(tick_server_time) - (int(m1_bars[-2]["time"]) + 60))

def last_realized_slippage_bps(events):
    val = None
    for e in events:
        if e.get("event") == "ORDER_SEND" and e.get("slippage_bps") is not None:
            val = float(e["slippage_bps"])
    return val
```

## B. `cycle.py` — import the helpers

```diff
-from gates import Ledger, RiskGuard, DemoGate, MAGIC, COMMENT  # noqa: E402
+from gates import (Ledger, RiskGuard, DemoGate, MAGIC, COMMENT,           # noqa: E402
+                   rebuild_risk_state, data_age_seconds, last_realized_slippage_bps)
```

## C. `cycle.py` — replace the fresh-guard + hardcoded-zero block (lines ~287-290)

```diff
         snap = snapshot(mt5)
         atr = atr_m15(mt5)
-        rg = RiskGuard(); rg.roll_day(NOW[:10])
+        # risk state is rebuilt from the ledger CLOSE/PNL facts => persists across cycles
+        _events = _ledger_rows(LEDGER)
+        rg = rebuild_risk_state(RiskGuard(), _events, NOW[:10])
         intent = {"order_id": f"{MAGIC}-{NOW}", "already_sent": set()}
-        allow, reasons = rg.evaluate(intent, {"spread_bps": (snap or {}).get("spread_bps") or 0,
-                                                "slippage_bps": 0, "data_age_seconds": 0}, len(positions))
+        # real inputs: same-source (server frame) staleness + last realized fill slippage
+        _tick = mt5.symbol_info_tick(SYMBOL)
+        _m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 3)
+        _age = data_age_seconds(getattr(_tick, "time", None), _m1)
+        _slip = last_realized_slippage_bps(_events)
+        allow, reasons = rg.evaluate(intent, {"spread_bps": (snap or {}).get("spread_bps") or 0,
+                                                "slippage_bps": (_slip if _slip is not None else 0),
+                                                "data_age_seconds": _age}, len(positions))
```

Observability (optional, same block) — surface the now-real counters in the DECISION/report:

```diff
         res.update({"action": action, "signal": sig, "order_intent": oi, "live_state": ls, "risk_allow": bool(allow),
+                     "risk_daily_loss": rg.daily_loss, "risk_consecutive_losses": rg.consecutive_losses,
+                     "data_age_seconds": _age,
```

## D. `cycle.py` — record commission/swap on new PNL events (needed for the `net` basis)

```diff
         lg.append("PNL", order_id=pid, position_id=pid, pnl=profit, entry=entry_px, exit=exit_px,
-                  qty=qty, side=side, reason=reason, realized_R=rr, sl=sl, tp=tp, broker_time_utc=close_ts)
+                  qty=qty, side=side, reason=reason, realized_R=rr, sl=sl, tp=tp, broker_time_utc=close_ts,
+                  commission=round(float(getattr(c, "commission", 0.0) or 0.0), 2),
+                  swap=round(float(getattr(c, "swap", 0.0) or 0.0), 2))
```

Additive fields only: existing keys and `Ledger.replay()` (`realized_pnl` sums `pnl` only) are unchanged,
so the ledger hash chain and replay output stay valid.

## Notes / limits of this fix (documented, fail-closed where possible)
- **Reconciliation lag is NOT fixed** (out of scope): a broker SL/TP close is only visible to the guard at
  the next reconcile, so intra-lag the counters under-count. Up to ~31h lag was observed in the audit window.
- **`already_sent` / DUPLICATE_ORDER stays structurally inert**: `order_id = f"{MAGIC}-{NOW}"` is unique per
  cycle, so it can never match. Not in the 4 listed rules; left as-is (flagged as a residual finding).
- **Old PNL events carry no commission/swap** → they are summed on the price component; new events use net.
  Mixed basis only affects pre-apply history; both are conservative for losses.
- **Slippage with no fill history** defaults to 0 (no block) — matching the original default semantics; a
  first-ever order cannot be blocked by an unmeasured quantity. Documented.
- If MT5 tick/M1 fetch fails, `data_age_seconds` is `None` → guard returns STALE_DATA (deny) = fail-closed.
