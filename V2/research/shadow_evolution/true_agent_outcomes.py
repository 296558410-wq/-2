# -*- coding: utf-8 -*-
"""true_agent_outcomes.py — 对 TRUE_AGENT_DECISIONS.jsonl 三侧统一回填 outcome（MT5 历史 M1，只读）。"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent; REPO = V2.parents[2]
HORIZONS = [15, 30, 60, 240]; WIN = 240

def to_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception: return None

def main():
    rows = [json.loads(l) for l in open(HERE / "TRUE_AGENT_DECISIONS.jsonl", encoding="utf-8") if l.strip()]
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
        base = {k: r.get(k) for k in ("shadow_side", "cycle", "decision", "opportunity")}
        if t is None or not px:
            out.append({**base, "outcome_status": "NO_TS_OR_PRICE"}); continue
        bars = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, t, t + timedelta(minutes=WIN + 5))
        if bars is None or len(bars) < 5:
            out.append({**base, "outcome_status": "NO_BARS"}); continue
        entry = float(px); side = r.get("direction")
        hi = max(float(b["high"]) for b in bars); lo = min(float(b["low"]) for b in bars)
        mfe = mae = None
        if side == "LONG": mfe = (hi - entry) / entry * 1e4; mae = (lo - entry) / entry * 1e4
        elif side == "SHORT": mfe = (entry - lo) / entry * 1e4; mae = (entry - hi) / entry * 1e4
        futs = {}
        for h in HORIZONS:
            k = next((i for i, b in enumerate(bars) if b["time"] >= (t + timedelta(minutes=h)).timestamp()), None)
            if k is not None:
                futs[f"+{h}m_bps"] = round((float(bars[k]["close"]) - entry) / entry * 1e4 * (1 if side != "SHORT" else -1), 2)
        out.append({**base, "ts_utc": r.get("ts_utc"), "direction": side, "entry_ref": entry,
                    "outcome_status": "OK", "window_min": WIN,
                    "mfe_bps": round(mfe, 2) if mfe is not None else None,
                    "mae_bps": round(mae, 2) if mae is not None else None,
                    "future_return": futs, "bars_n": int(len(bars))})
    mt5.shutdown()
    with open(HERE / "TRUE_AGENT_OUTCOMES.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for o in out: fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    ok = sum(1 for o in out if o.get("outcome_status") == "OK")
    print("rows:", len(out), "ok:", ok, "->", HERE / "TRUE_AGENT_OUTCOMES.jsonl")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
