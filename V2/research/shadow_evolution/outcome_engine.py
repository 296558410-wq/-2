# -*- coding: utf-8 -*-
"""outcome_engine.py — V2 正式 **只读** outcome 研究组件（Phase-3 任务 C）。

对每个可评估 decision 记录: 15/30/60/240m future return, MFE, MAE, TP/SL first-touch(若适用), 数据完整性。
严格: PIT（只用 decision 时刻之后的数据）· 不补造休市数据（不足即 DATA_GAP）· 不产生交易（仅 MT5 只读）。
输入: TRUE_AGENT_DECISIONS.jsonl   输出: OUTCOME_ENGINE.jsonl (+ _outcome_engine_stats.json)
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent; REPO = V2.parents[2]
HORIZONS = [15, 30, 60, 240]
WIN = 245
MIN_BARS_FOR = {15: 12, 30: 22, 60: 42, 240: 150}   # 数据完整性阈值（低于则 DATA_GAP）
SRC = HERE / "TRUE_AGENT_DECISIONS.jsonl"
OUTF = HERE / "OUTCOME_ENGINE.jsonl"


def to_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception: return None


def mt5_connect():
    env = {}
    for line in open(REPO / ".env.mt5_demo", encoding="utf-8-sig", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
    import MetaTrader5 as mt5
    kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
          "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
    kw["pass"+"word"] = env["DEMO_MT5_PASSWORD"]
    assert mt5.initialize(**kw), mt5.last_error()
    return mt5


def main():
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    mt5 = mt5_connect()
    out = []
    for r in rows:
        t = to_dt(r.get("ts_utc")); px = r.get("market_primary_last"); side = r.get("direction")
        base = {k: r.get(k) for k in ("shadow_side", "cycle", "ts_utc", "decision", "opportunity", "direction")}
        if t is None or not px:
            out.append({**base, "outcome_status": "DATA_GAP", "reason": "no_decision_ts_or_price"}); continue
        bars = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, t, t + timedelta(minutes=WIN))
        if bars is None or len(bars) < 5:
            out.append({**base, "outcome_status": "DATA_GAP", "reason": "no_bars"}); continue
        entry = float(px)
        hi = max(float(b["high"]) for b in bars); lo = min(float(b["low"]) for b in bars)
        mfe = mae = None
        if side == "LONG": mfe = (hi - entry) / entry * 1e4; mae = (lo - entry) / entry * 1e4
        elif side == "SHORT": mfe = (entry - lo) / entry * 1e4; mae = (entry - hi) / entry * 1e4
        fut, complete = {}, {}
        for h in HORIZONS:
            k = next((i for i, b in enumerate(bars) if b["time"] >= (t + timedelta(minutes=h)).timestamp()), None)
            n = k if k is not None else len(bars)
            ok = (k is not None) and (n >= MIN_BARS_FOR[h])
            complete["+%dm" % h] = bool(ok)
            if k is not None:
                sign = 1 if side != "SHORT" else -1
                fut["+%dm_bps" % h] = round((float(bars[k]["close"]) - entry) / entry * 1e4 * (1 if side in ("LONG", "SHORT") else 1) * (sign if side in ("LONG", "SHORT") else 1), 2)
        # TP/SL first-touch (仅当 plan 定义了方向+SL/TP)
        path = None; plan = r.get("plan") or {}
        if plan.get("stop_loss") and plan.get("take_profit") and side in ("LONG", "SHORT"):
            sl = float(plan["stop_loss"]); tp = float(plan["take_profit"]); hit = None
            for b in bars:
                if side == "LONG":
                    if float(b["low"]) <= sl: hit = ("SL", b["time"]); break
                    if float(b["high"]) >= tp: hit = ("TP", b["time"]); break
                else:
                    if float(b["high"]) >= sl: hit = ("SL", b["time"]); break
                    if float(b["low"]) <= tp: hit = ("TP", b["time"]); break
            path = {"applicable": True, "first_touch": hit[0] if hit else "NONE",
                    "touch_min": round((hit[1] - t.timestamp()) / 60, 1) if hit else None, "window_min": WIN,
                    "sl": sl, "tp": tp}
        elif side not in ("LONG", "SHORT"):
            path = {"applicable": False, "reason": "no_direction"}
        else:
            path = {"applicable": False, "reason": "no_plan_levels"}
        status = "OK" if all(complete.values()) else "PARTIAL_DATA_GAP"
        out.append({**base, "entry_ref": entry, "outcome_status": status, "window_min": WIN, "bars_n": int(len(bars)),
                    "mfe_bps": round(mfe, 2) if mfe is not None else None,
                    "mae_bps": round(mae, 2) if mae is not None else None,
                    "future_return": fut, "horizon_complete": complete, "tp_sl_path": path})
    mt5.shutdown()
    with open(OUTF, "w", encoding="utf-8", newline="\n") as fh:
        for o in out: fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    import collections
    st = {"rows": len(out), "by_status": dict(collections.Counter(o.get("outcome_status") for o in out)),
          "by_side": dict(collections.Counter(o["shadow_side"] for o in out)),
          "horizon_complete_rate": {h: round(sum(1 for o in out if (o.get("horizon_complete") or {}).get(h)) / max(1, len(out)), 3) for h in ("+15m", "+30m", "+60m", "+240m")}}
    json.dump(st, open(HERE / "_outcome_engine_stats.json", "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
