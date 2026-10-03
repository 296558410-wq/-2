# -*- coding: utf-8 -*-
"""dashboard.py — Hermes 交易控制中心(全中文, localhost)。
数据: dashdata(行情 15s/K线缓存) + broker demo(账户/持仓/成交史) + trader run_state。
启动: .venv\\Scripts\\python.exe research\\money_hunter\\dashboard\\dashboard.py → http://127.0.0.1:8787
"""
import json
import sys
import threading
import time as _time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "research/hermes/trader_v1"))

import dashdata  # noqa: E402
import dashboard_render as R  # noqa: E402

# —— MT5 实时 tick 后台线程(10s 轮询, 零 LLM 成本; 替代被移除的 30s agent cron) ——
def _quote_loop(stop_event):
    """每 10s 读 real 终端 tick → 写 quote_latest.json(dashdata.quote_fast 读取)。
    只读; 异常静默重试(终端可能短暂不可达)。"""
    import MetaTrader5 as mt5
    out_p = REPO / "data/live_fxtm/quote_latest.json"
    while not stop_event.is_set():
        try:
            if not mt5.initialize(path=r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"):  # INSTANCE-ISOLATION-FIX-001: pin V1 terminal (no-path default caused cross-instance launch)
                stop_event.wait(10)
                continue
            mt5.symbol_select("XAUUSD", True)
            t = mt5.symbol_info_tick("XAUUSD")
            if t:
                now = datetime.now(timezone.utc)
                q = {"utc_ts": now.isoformat(), "bid": round(t.bid, 3), "ask": round(t.ask, 3),
                     "mid": round((t.bid + t.ask) / 2, 2),
                     "spread_usd": round(t.ask - t.bid, 3),
                     "server_ms": t.time_msc, "source": "dashboard-live"}
                try:
                    out_p.parent.mkdir(parents=True, exist_ok=True)
                    out_p.write_text(json.dumps(q, ensure_ascii=False), encoding="utf-8")
                except Exception:  # noqa: BLE001
                    pass
            mt5.shutdown()
        except Exception:  # noqa: BLE001
            pass
        stop_event.wait(10)

_stop_evt = threading.Event()
threading.Thread(target=_quote_loop, args=(_stop_evt,), daemon=True).start()

PORT = 8787
TRADER = REPO / "research/hermes/trader_v1"
RUN = TRADER / "run_state"

_broker_lock = threading.Lock()
_broker_cache = {"ts": 0.0, "data": None}
BROKER_TTL = 15.0


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default if default is not None else {}


def broker_snapshot():
    """demo 账户+持仓+成交史(15s 缓存)。"""
    with _broker_lock:
        if _broker_cache["data"] and (_time.time() - _broker_cache["ts"]) < BROKER_TTL:
            return _broker_cache["data"]
        import broker_mt5_demo as B  # noqa: PLC0415
        ac = dashdata.account()
        poss, hist = [], []
        try:
            bp = B.get_positions()
            if bp.get("ok"):
                poss = bp.get("positions", [])
            hb = B.history_balance()
            if hb.get("ok"):
                hist = hb.get("points", [])
        except Exception:  # noqa: BLE001
            pass
        out = {"account": ac, "broker_positions": poss, "equity_hist": hist}
        _broker_cache.update(ts=_time.time(), data=out)
        return out


def m15_countdown():
    """当前时间 + 距下一个 M15 收盘的秒数(:00/:15/:30/:45)。"""
    now = datetime.now(timezone.utc)
    nxt = now.replace(minute=(now.minute // 15 + 1) * 15 % 60, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(minutes=15)
    return {"now": now.isoformat(), "countdown": int((nxt - now).total_seconds())}


def trader_state():
    out = {"status": "未启动", "counters": {}, "waits": {}, "consecutive_waits": 0,
           "latest_decision": None, "invariants_pass": None}
    try:
        st = load_json(RUN / "statistics.json")
        if not st:
            return out
        wf = load_json(RUN / "workflow_latest.json")
        steps = {x.get("step"): x for x in (wf.get("steps") or [])}
        decide = steps.get("DECIDE") or {}
        think = steps.get("THINK") or {}
        out["counters"] = st.get("counters", {})
        out["waits"] = st.get("waits", {})
        out["consecutive_waits"] = (st.get("waits") or {}).get("consecutive_waits", 0)
        if think.get("status") == "running":
            out["status"] = "思考中"
        elif decide.get("result") in ("LONG", "SHORT"):
            out["status"] = "等待触发"
        elif out["consecutive_waits"] > 0:
            out["status"] = "WAIT"
        else:
            out["status"] = "观察中"
        dec_dir = RUN / "decisions"
        if dec_dir.exists():
            fs = sorted(dec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            if fs:
                out["latest_decision"] = load_json(fs[-1])
        out["invariants_pass"] = (st.get("last_invariants") or {}).get("pass")
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def recent_decisions(n=6):
    out = []
    dec_dir = RUN / "decisions"
    if not dec_dir.exists():
        return out
    fs = sorted(dec_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for f in fs[-n:][::-1]:
        d = load_json(f)
        if d:
            a14 = d.get("answers_14") or {}
            out.append({"utc_ts": d.get("utc_ts") or d.get("cycle", ""),
                        "decision": d.get("decision"), "opportunity": d.get("opportunity"),
                        "reason": a14.get("14") or a14.get("1") or ""})
    return out


def snapshot():
    bars = dashdata.bars_refresh()
    bs = broker_snapshot()
    trader = trader_state()
    alerts = dashdata.health(trader, bars, bs["account"])
    funnel = {}
    try:
        import opportunity as OPP  # noqa: PLC0415
        funnel = OPP.coverage_summary()
    except Exception:  # noqa: BLE001
        pass
    return {"bars": bars, "trader": trader, "account": bs["account"],
            "broker_positions": bs.get("broker_positions", []),
            "equity_hist": bs.get("equity_hist", []),
            "alerts": alerts, "quote": dashdata.quote_fast(),
            "funnel": funnel, "recent_decisions": recent_decisions(),
            "countdown": m15_countdown(), "now": now_iso()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8"):
        body = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            s = snapshot()
            html = R.render_page(s["now"], s, s["trader"].get("counters", {}), s["funnel"])
            self._send(html)
        elif self.path.startswith("/api/bars"):
            tf = self.path.split("tf=")[-1] if "tf=" in self.path else "M15"
            tf = tf if tf in ("M15", "H1", "H4", "D1") else "M15"
            b = dashdata.bars_refresh()
            key = {"M15": "m15", "H1": "h1", "H4": "h4", "D1": "d1"}[tf]
            self._send(json.dumps({"bars": b.get(key, []), "tf": tf}, ensure_ascii=False),
                       "application/json; charset=utf-8")
        elif self.path == "/api/top":
            b = dashdata.bars_refresh()
            q = dashdata.quote_fast() or {}
            bs = broker_snapshot()
            ac = bs["account"]
            trader = trader_state()
            payload = {"last_close": b.get("last_close"), "quote": q,
                       "live_days": b.get("live_days"), "generated": b.get("generated", ""),
                       "balance": ac.get("balance") if ac.get("available") else None,
                       "equity": ac.get("equity") if ac.get("available") else None,
                       "hermes": trader.get("status"),
                       "consecutive_waits": trader.get("consecutive_waits"),
                       "n_positions": len(bs.get("broker_positions", []))}
            self._send(json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")
        elif self.path == "/api/positions":
            bs = broker_snapshot()
            self._send(json.dumps({"positions": bs.get("broker_positions", [])},
                                  ensure_ascii=False), "application/json; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"DASHBOARD http://127.0.0.1:{PORT}  (交易控制中心 · 只读)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
