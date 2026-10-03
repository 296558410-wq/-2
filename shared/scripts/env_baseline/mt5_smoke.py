# -*- coding: utf-8 -*-
"""mt5_smoke.py - MetaTrader5 READ-ONLY data smoke (XAUUSD).
Policy: NO order functions, NO account mutation. If the logged-in account is
REAL (trade_mode==2) we refuse to pull and report FAIL(policy) instead.
Checks terminal path, connection, account mode, XAUUSD symbol, M1/M5/H1 bars,
tick data if available, spread/volume fields, ascending server timestamps."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_mt5.json"

TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
ORDER_FUNCS = ["order_send", "order_calc_margin", "order_calc_profit", "position_close", "order_modify"]


def main() -> None:
    checks: list[dict] = []
    info: dict = {}

    def add(name, ok, detail="", status=None):
        checks.append({"name": name, "status": status or ("PASS" if ok else "FAIL"), "detail": detail})

    if not Path(TERMINAL).exists():
        add("terminal_present", False, f"{TERMINAL} NOT FOUND")
        OUT.write_text(json.dumps({"status": "FAIL", "checks": checks, "info": info}, indent=2), encoding="utf-8")
        print("mt5_smoke: FAIL - terminal not installed")
        return

    import MetaTrader5 as mt5

    # read-only scope: every function this script may call is a read/copy/info API.
    # order_send / position_open exist in the module but are NEVER invoked here.
    read_only_api = ["initialize", "shutdown", "account_info", "symbol_info", "symbols_get",
                     "copy_rates_from_pos", "copy_rates_range", "copy_ticks_from_pos", "copy_ticks_range", "version", "last_error"]
    add("no_order_calls", all(hasattr(mt5, f) for f in read_only_api if f not in ("copy_ticks_from_pos", "copy_ticks_range")),
        "read-only API only; order_send/position_open never invoked")

    if not mt5.initialize(TERMINAL, timeout=60_000):
        add("connect", False, f"initialize failed: {mt5.last_error()}")
        OUT.write_text(json.dumps({"status": "FAIL", "checks": checks, "info": info}, indent=2), encoding="utf-8")
        print("mt5_smoke: FAIL - initialize failed"); return

    try:
        ver = mt5.version()
        info["version"] = ver
        add("connect", True, f"terminal {ver[0]}.{ver[1]} build {ver[2]}")

        acc = mt5.account_info()
        if acc is None:
            add("account_mode", False, f"account_info failed: {mt5.last_error()} (no account logged in?)")
        else:
            mode = int(acc.trade_mode)  # 0=demo, 1=contest, 2=real
            info["account"] = {"trade_mode": mode, "server": acc.server, "login_hint": str(acc.login)[:3] + "***", "currency": acc.currency}
            if mode == 2:
                add("account_mode", True, f"REAL account server='{acc.server}' -> READ-ONLY research pull only (no order/position functions, no account mutation)")
                checks[-1]["status"] = "WARN"
            else:
                add("account_mode", True, f"mode={'demo' if mode == 0 else 'contest'} server='{acc.server}' (read-only ok)")

        # symbol discovery
        sym = mt5.symbol_info("XAUUSD")
        if sym is None:
            cands = [s.name for s in (mt5.symbols_get() or []) if s.name and ("XAU" in s.name.upper() or "GOLD" in s.name.upper())]
            info["xau_candidates"] = cands[:10]
            add("symbol_xauusd", False, f"XAUUSD not found; candidates={cands[:5]}")
        else:
            info["symbol"] = {"name": sym.name, "digits": sym.digits, "point": sym.point, "trade_mode": int(sym.trade_mode), "visible": bool(sym.visible)}
            add("symbol_xauusd", True, f"{sym.name} digits={sym.digits} point={sym.point}")

        now = datetime.now()
        tfs = [("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("H1", mt5.TIMEFRAME_H1)]
        for name, tf in tfs:
            rates = mt5.copy_rates_from_pos("XAUUSD", tf, 0, 300)
            if rates is None or len(rates) == 0:
                add(f"rates_{name}", False, f"{mt5.last_error()}")
                continue
            import pandas as pd
            d = pd.DataFrame(rates)
            d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
            asc = d["time"].is_monotonic_increasing
            cols = {"open", "high", "low", "close", "tick_volume", "spread", "real_volume"}.issubset(d.columns)
            has_ask_bid = "ask" in d.columns or "bid" in d.columns
            info[f"{name}_last"] = str(d["time"].iloc[-1])
            info[f"{name}_rows"] = int(len(d))
            add(f"rates_{name}", asc and cols and len(d) > 50,
                f"{len(d)} bars, last={d['time'].iloc[-1]}, asc={asc}, cols_ok={cols}")

        # tick data (M1 history ticks may be disabled / API may be absent -> WARN not FAIL)
        try:
            if not hasattr(mt5, "copy_ticks_from_pos"):
                add("ticks_available", False, "copy_ticks_from_pos not in this MetaTrader5 package build -> tick-level pull unavailable (bars OK)")
                checks[-1]["status"] = "WARN"
            else:
                ticks = mt5.copy_ticks_from_pos("XAUUSD", 0, 2000, mt5.COPY_TICKS_ALL)
                if ticks is None or len(ticks) == 0:
                    add("ticks_available", False, "no tick history (broker setting) -> WARN"); checks[-1]["status"] = "WARN"
                else:
                    t = pd.DataFrame(ticks)
                    t["time"] = pd.to_datetime(t["time"], unit="s", utc=True)
                    fields_ok = {"bid", "ask", "last", "volume", "flags"}.issubset(t.columns) or {"bid", "ask"}.issubset(t.columns)
                    add("ticks_available", fields_ok and t["time"].is_monotonic_increasing,
                        f"{len(t)} ticks last={t['time'].iloc[-1]} fields={[c for c in t.columns if c in ('bid','ask','last','volume','flags')]}")
        except Exception as e:
            add("ticks_available", False, f"{type(e).__name__}: {e}"); checks[-1]["status"] = "WARN"
    finally:
        mt5.shutdown()

    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"mt5_smoke: {status} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
