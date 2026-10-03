"""READ-ONLY broker probe for V3 cost-bridge audit. Places ZERO orders.

Only read calls: initialize / terminal_info / account_info / symbol_info /
history_deals_get / history_orders_get / copy_ticks_range / shutdown.
Writes nothing into MT5. Dumps JSON to stdout.
"""
import json
import datetime as dt
import MetaTrader5 as mt5

TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
MAGIC = 90004

out = {}
ok = mt5.initialize(path=TERMINAL, portable=True, timeout=60000)
out["init_ok"] = bool(ok)
out["init_last_error"] = mt5.last_error()
if not ok:
    print(json.dumps(out, default=str))
    raise SystemExit(0)

ti = mt5.terminal_info()
ai = mt5.account_info()
out["terminal"] = {k: getattr(ti, k, None) for k in
                   ("data_path", "company", "name", "connected", "trade_allowed",
                    "path", "build")}
out["account"] = {k: getattr(ai, k, None) for k in
                  ("login", "server", "balance", "equity", "currency", "leverage",
                   "trade_allowed", "margin_free", "profit", "margin")}

si = mt5.symbol_info("XAUUSD")
out["spec"] = {k: getattr(si, k, None) for k in
               ("name", "digits", "point", "trade_tick_size", "trade_tick_value",
                "trade_tick_value_profit", "trade_tick_value_loss",
                "trade_contract_size", "volume_min", "volume_step", "volume_max",
                "spread", "filling_mode", "trade_exemode", "trade_mode",
                "currency_base", "currency_profit", "currency_margin", "swap_mode",
                "swap_long", "swap_short")}

frm = dt.datetime(2026, 9, 20, 0, 0, 0, tzinfo=dt.timezone.utc)
to = dt.datetime(2026, 9, 22, 0, 0, 0, tzinfo=dt.timezone.utc)

deals = mt5.history_deals_get(frm, to) or []
dd = []
for d in deals:
    if getattr(d, "magic", None) != MAGIC:
        continue
    dd.append({k: getattr(d, k, None) for k in
               ("ticket", "order", "time", "time_msc", "type", "entry",
                "position_id", "volume", "price", "commission", "swap",
                "profit", "fee", "magic", "comment", "symbol")})
out["deals_total_window"] = len(deals)
out["deals_magic_90004_n"] = len(dd)
out["deals"] = sorted(dd, key=lambda x: (x["time_msc"] or 0, x["ticket"]))

orders = mt5.history_orders_get(frm, to) or []
oo = []
for o in orders:
    if getattr(o, "magic", None) != MAGIC:
        continue
    oo.append({k: getattr(o, k, None) for k in
               ("ticket", "time_setup", "time_setup_msc", "time_done", "time_done_msc",
                "type", "state", "volume_initial", "volume_current", "price_open",
                "sl", "tp", "magic", "comment", "type_filling", "type_time",
                "position_id", "symbol")})
out["orders_magic_90004_n"] = len(oo)
out["orders"] = sorted(oo, key=lambda x: (x["time_setup_msc"] or 0, x["ticket"]))

# ticks covering the run window
tf = dt.datetime(2026, 9, 20, 23, 5, 0, tzinfo=dt.timezone.utc)
tt = dt.datetime(2026, 9, 20, 23, 7, 0, tzinfo=dt.timezone.utc)
ticks = mt5.copy_ticks_range("XAUUSD", tf, tt, mt5.COPY_TICKS_ALL)
try:
    out["ticks_n"] = int(len(ticks))
    out["ticks_head"] = [list(map(str, ticks[i])) for i in range(min(3, len(ticks)))] if ticks is not None else []
    out["ticks_tail"] = [list(map(str, ticks[i])) for i in range(max(0, len(ticks) - 3), len(ticks))] if ticks is not None else []
except Exception as e:
    out["ticks_n"] = None
    out["ticks_error"] = str(e)

mt5.shutdown()
with open("_probe_broker_out.json", "w", encoding="utf-8") as f:
    json.dump(out, f, default=str, indent=1)
print(json.dumps({"init_ok": out["init_ok"], "deals_magic": out["deals_magic_90004_n"],
                  "orders_magic": out["orders_magic_90004_n"],
                  "ticks_n": out.get("ticks_n")}, default=str))
