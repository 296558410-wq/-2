# -*- coding: utf-8 -*-
"""shadow_outcomes.py — 为 Shadow 决策回填 outcome 链（MFE/MAE/future return/TP-SL path/时间窗口）。
只读 MT5 历史 M1（order_send=0）。输出 SHADOW_OUTCOMES.jsonl。
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent
REPO = V2.parents[2]
HORIZONS = [15, 30, 60, 240]  # minutes
WIN = 240                     # outcome window minutes

def to_dt(s):
    s = str(s).replace("Z", "+00:00")
    try: return datetime.fromisoformat(s)
    except Exception: return None

def main():
    rows = [json.loads(l) for l in open(HERE / "SHADOW_DECISIONS.jsonl", encoding="utf-8") if l.strip()]
    try: rows = rows[-int(sys.argv[sys.argv.index("--limit")+1]):]
    except Exception: pass
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
    out = []
    for r in rows:
        t = to_dt(r.get("ts_utc")); px = r.get("market_primary_last")
        if t is None or not px:
            out.append({**{k: r[k] for k in ("shadow_side","cycle","decision","opportunity")}, "outcome_status": "NO_TS_OR_PRICE"}); continue
        bars = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, t, t + timedelta(minutes=WIN + 5))
        if bars is None or len(bars) < 5:
            out.append({**{k: r[k] for k in ("shadow_side","cycle","decision","opportunity")}, "outcome_status": "NO_BARS"}); continue
        entry = float(px); hi = max(float(b["high"]) for b in bars); lo = min(float(b["low"]) for b in bars)
        side = r.get("direction")
        mfe = mae = None
        if side in ("LONG", "SHORT"):
            if side == "LONG": mfe = (hi - entry) / entry * 1e4; mae = (lo - entry) / entry * 1e4
            else: mfe = (entry - lo) / entry * 1e4; mae = (entry - hi) / entry * 1e4
        futs = {}
        for h in HORIZONS:
            k = next((i for i, b in enumerate(bars) if b["time"] >= (t + timedelta(minutes=h)).timestamp()), None)
            if k is not None:
                futs[f"+{h}m_bps"] = round((float(bars[k]["close"]) - entry) / entry * 1e4 * (1 if side != "SHORT" else -1), 2)
        # TP/SL first-touch (if plan has levels)
        path = None; plan = r.get("plan") or {}
        if plan.get("stop_loss") and plan.get("take_profit") and side:
            sl = float(plan["stop_loss"]); tp = float(plan["take_profit"])
            hit = None
            for b in bars:
                if side == "LONG":
                    if float(b["low"]) <= sl: hit = ("SL", b["time"]); break
                    if float(b["high"]) >= tp: hit = ("TP", b["time"]); break
                else:
                    if float(b["high"]) >= sl: hit = ("SL", b["time"]); break
                    if float(b["low"]) <= tp: hit = ("TP", b["time"]); break
            path = {"first_touch": (hit[0] if hit else "NONE"),
                    "touch_min": round((hit[1] - t.timestamp()) / 60, 1) if hit else None, "window_min": WIN,
                    "sl": sl, "tp": tp}
        out.append({"shadow_side": r["shadow_side"], "cycle": r["cycle"], "ts_utc": r.get("ts_utc"),
                    "decision": r.get("decision"), "opportunity": r.get("opportunity"), "direction": side,
                    "entry_ref": entry, "outcome_status": "OK", "window_min": WIN,
                    "mfe_bps": round(mfe, 2) if mfe is not None else None,
                    "mae_bps": round(mae, 2) if mae is not None else None,
                    "future_return": futs, "tp_sl_path": path,
                    "bars_n": int(len(bars))})
    mt5.shutdown()
    with open(HERE / "SHADOW_OUTCOMES.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for o in out: fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    ok = sum(1 for o in out if o.get("outcome_status") == "OK")
    print("outcomes:", len(out), "ok:", ok, "->", HERE / "SHADOW_OUTCOMES.jsonl")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
