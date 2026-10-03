# -*- coding: utf-8 -*-
"""dashdata.py — Dashboard 数据供应层(服务端缓存刷新, 供 render 拉最新)。

职责:
1. bars_refresh(): 读 live/staging tick → 生成最新已收盘 OHLC(多周期) + 指标缓存
   (M15 主图/H1/H4/D1; MA20/50, RSI14, ATR%, 60-bar S/R, expansion, 每根 tick 数)
   缓存策略: 进程内 60s 过期重建(页面 10s 刷新不重复读盘)
2. account(): demo 账户实时(直读 broker_mt5_demo); paper → 暂无
3. health(): 逻辑健康聚合 → 红/黄/绿告警列表("一眼看出问题")
"""
import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # trader_v1

LIVE_DIR = REPO / "data/live_fxtm"
STAGE_DIR = REPO / "data/staging_fxtm"

_lock = threading.Lock()
_cache = {"ts": None, "data": None}
CACHE_SECONDS = 15  # 高频行情: 15s 缓存(原 60s)


def _now():
    return datetime.now(timezone.utc)


def load_ticks_fast(dirp, days=None):
    """快速读 parquet tick(只取 ts/bid/ask, 可只取最近 days 天文件)。"""
    import pandas as pd
    files = sorted(Path(dirp).glob("ticks_*.parquet"))
    if days is not None and len(files) > days:
        files = files[-days:]
    frames = []
    for p in files:
        try:
            df = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
        except Exception:  # noqa: BLE001
            continue
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
        frames.append(df)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values("ts_utc").drop_duplicates("ts_utc").reset_index(drop=True)
    return out


def build_bars(df, rule="15min", n=220):
    """OHLC + tick 计数。剔除未收盘 bar(以 df 最新 tick 判定)。"""
    import numpy as np
    import pandas as pd
    o = df.set_index("ts_utc").resample(rule).agg(
        o=("bid", "first"), h=("bid", "max"), l=("bid", "min"), c=("bid", "last"),
        n=("bid", "count"))
    o = o[o["n"] > 0].dropna(subset=["c"])
    if len(o):
        last_end = o.index[-1] + pd.Timedelta(rule)
        if df["ts_utc"].max() < last_end:
            o = o.iloc[:-1]  # 未收盘剔除
    o = o.tail(n).reset_index()
    # 指标(向量化, 已收盘 bars 内计算, 无 look-ahead)
    c = o["c"]
    ma20 = c.rolling(20).mean()
    ma50 = c.rolling(50).mean()
    delta = c.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    atr = (o["h"] - o["l"]).rolling(14).mean()
    hi60 = o["h"].rolling(60).max()
    lo60 = o["l"].rolling(60).min()
    rows = []
    for i in range(len(o)):
        r = {"t": o["ts_utc"].iloc[i].strftime("%m-%d %H:%M"), "o": round(float(o["o"].iloc[i]), 2),
             "h": round(float(o["h"].iloc[i]), 2), "l": round(float(o["l"].iloc[i]), 2),
             "c": round(float(o["c"].iloc[i]), 2), "n": int(o["n"].iloc[i])}
        if i >= 19 and not np.isnan(ma20.iloc[i]):
            r["ma20"] = round(float(ma20.iloc[i]), 2)
        if i >= 49 and not np.isnan(ma50.iloc[i]):
            r["ma50"] = round(float(ma50.iloc[i]), 2)
        if not np.isnan(rsi.iloc[i]):
            r["rsi"] = round(float(rsi.iloc[i]), 1)
        if not np.isnan(atr.iloc[i]):
            r["atr"] = round(float(atr.iloc[i]), 2)
        if not np.isnan(hi60.iloc[i]):
            r["hi60"] = round(float(hi60.iloc[i]), 2)
        if not np.isnan(lo60.iloc[i]):
            r["lo60"] = round(float(lo60.iloc[i]), 2)
        rows.append(r)
    return rows


def bars_refresh(force=False, live_days_files=None):
    """主入口: 进程内缓存(CACHE_SECONDS 过期)。live 全读 + staging 全量(保 D1/H4 上下文)。
    返回 {m15, h1, h4, d1, ...}"""
    with _lock:
        if not force and _cache["ts"] and (_now() - _cache["ts"]) < timedelta(seconds=CACHE_SECONDS):
            return _cache["data"]
        try:
            live = load_ticks_fast(LIVE_DIR)
            stage_all = load_ticks_fast(STAGE_DIR, days=None)
            if live is None and stage_tail is None:
                _cache.update(ts=_now(), data={"error": "no tick data"})
                return _cache["data"]
            # 合并(同 feed 定义: live 优先, stage 补历史)
            import pandas as pd
            df = pd.concat([stage_all, live], ignore_index=True) \
                if live is not None and stage_all is not None \
                else (live if live is not None else stage_all)
            df = df.sort_values("ts_utc").drop_duplicates("ts_utc").reset_index(drop=True)
            m15 = build_bars(df, "15min", 200)
            h1 = build_bars(df, "1h", 150)
            h4 = build_bars(df, "4h", 120)
            # D1: 需要更长历史; staging 24 日够 20+ D1
            d1 = build_bars(df, "1D", 60)
            last = df.iloc[-1]
            live_days = int(live["ts_utc"].dt.date.nunique()) if live is not None else 0
            out = {
                "m15": m15, "h1": h1, "h4": h4, "d1": d1,
                "last_close": round(float((last["bid"] + last["ask"]) / 2), 2),
                "last_bid": round(float(last["bid"]), 2),
                "last_ask": round(float(last["ask"]), 2),
                "last_ts": last["ts_utc"].isoformat(),
                "live_days": live_days,
                "source": "live+staging_tail",
                "generated": _now().isoformat(),
            }
            _cache.update(ts=_now(), data=out)
            return out
        except Exception as e:  # noqa: BLE001
            _cache.update(ts=_now(), data={"error": f"bars_refresh:{e}"})
            return _cache["data"]


def quote_fast():
    """高频实时报价: 直读 quote_latest.json(30s cron 写), 零成本轮询。"""
    p = LIVE_DIR / "quote_latest.json"
    try:
        if not p.exists():
            return None
        q = json.loads(p.read_text(encoding="utf-8"))
        q["age_s"] = round((_now() - datetime.fromisoformat(q["utc_ts"])).total_seconds(), 0)
        return q
    except Exception:  # noqa: BLE001
        return None


def account():
    """demo 账户实时(只读展示)。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import broker_mt5_demo as B  # noqa: PLC0415
        acc = B.get_account()
        if acc.get("ok"):
            return {"available": True, "mode": "demo", "login": acc["login"],
                    "server": acc["server"], "balance": acc["balance"],
                    "equity": acc["equity"], "margin_free": acc["margin_free"],
                    "margin_level": round(acc["margin_level"], 0),
                    "leverage": acc["leverage"], "currency": acc["currency"]}
        return {"available": False, "mode": "demo", "error": acc.get("error")}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "mode": "demo", "error": str(e)}


def health(trader, bars, account_info):
    """逻辑健康聚合 → alerts[{level: red|yellow|green, tag, msg}]。
    规则全部来自本项目已证认知(不做主观评判)。"""
    alerts = []
    # —— 数据健康 ——
    if bars.get("error"):
        alerts.append({"level": "red", "tag": "数据", "msg": f"K线数据错误: {bars['error']}"})
    else:
        try:
            age_min = (_now() - datetime.fromisoformat(bars["last_ts"])).total_seconds() / 60
            if age_min > 20:
                alerts.append({"level": "red", "tag": "数据", "msg": f"最新 tick 已 {age_min:.0f} 分钟未更新(采集器可能停滞)"})
            elif age_min > 6:
                alerts.append({"level": "yellow", "tag": "数据", "msg": f"tick 延迟 {age_min:.0f} 分钟(正常 <6)"})
            if bars["live_days"] < 14:
                alerts.append({"level": "yellow", "tag": "数据",
                               "msg": f"前瞻数据仅 {bars['live_days']} 天 — 漂移基线/状态统计需 ≥14 天(预热期, 属正常)"})
        except Exception:  # noqa: BLE001
            pass
    # —— Hermes 健康 ——
    cw = (trader or {}).get("consecutive_waits", 0)
    # 市场是否在动(最近 2 根 M15 是否有价格移动; 动而 WAIT 才可疑)
    market_moving = False
    try:
        if bars and not bars.get("error") and len(bars.get("m15", [])) >= 3:
            mm = bars["m15"]
            last2 = mm[-1]["c"]
            prev3 = mm[-3]["c"]
            market_moving = abs(last2 - prev3) > 1.0  # >$1/30min
    except Exception:  # noqa: BLE001
        pass
    if cw >= 15 and market_moving:
        alerts.append({"level": "red", "tag": "Hermes",
                       "msg": f"连续 WAIT {cw} 次 且市场在波动 — 状态包/机会识别可能有问题, 需人工核查"})
    elif cw >= 12:
        alerts.append({"level": "yellow", "tag": "Hermes",
                       "msg": f"连续 WAIT {cw} 次 — 等待是纪律(市场可能确无收盘级机会); 若波动明显仍无计划再升级"})
    elif cw >= 6:
        alerts.append({"level": "green", "tag": "Hermes", "msg": f"连续 WAIT {cw} 次 — 纪律性等待中"})
    age_dec = None
    if trader:
        try:
            age_dec = (_now() - datetime.fromisoformat((trader.get("decided_at") or "").replace("Z", "+00:00"))).total_seconds() / 60 if trader.get("decided_at") else None
        except Exception:  # noqa: BLE001
            age_dec = None
    if age_dec is not None and age_dec > 40:
        alerts.append({"level": "red", "tag": "Hermes", "msg": f"最近决策已是 {age_dec:.0f} 分钟前 — cron 可能未运行"})
    inv = (trader or {}).get("counters", {}).get("fail_closed_events", 0) or 0
    if inv:
        alerts.append({"level": "red", "tag": "风控", "msg": f"发生 {inv} 次 FAIL_CLOSED(不变量触发) — 需人工核查"})
    # —— 账户健康 ——
    if account_info.get("available"):
        ml = account_info.get("margin_level")
        bal = account_info.get("balance")
        # margin_level=0 且 margin_free≈balance → 无持仓, 正常(不告警)
        if ml is not None and ml > 0 and ml < 200:
            alerts.append({"level": "red", "tag": "账户", "msg": f"保证金率 {ml}% 过低(持仓风险)"})
        elif ml is not None and ml > 0 and ml < 400:
            alerts.append({"level": "yellow", "tag": "账户", "msg": f"保证金率 {ml}%(demo)"})
        bal_txt = f"${bal:,.2f}" if isinstance(bal, (int, float)) else "—"
        alerts.append({"level": "green", "tag": "账户", "msg": f"demo 在线 · 余额 {bal_txt} · 无持仓" if not (ml and ml > 0) else f"demo 在线 · 余额 {bal_txt}"})
    else:
        alerts.append({"level": "yellow", "tag": "账户", "msg": "demo 账户未连接(仅 Paper)"})
    # —— 状态包新鲜度(决策依据) ——
    try:
        sp = Path(REPO) / "research/hermes/trader_v1/run_state/state_package_latest.json"
        if sp.exists():
            pkg = json.loads(sp.read_text(encoding="utf-8"))
            gap = (_now() - datetime.fromisoformat(pkg.get("generated_utc", ""))).total_seconds() / 60
            if gap > 20:
                alerts.append({"level": "yellow", "tag": "决策", "msg": f"状态包已 {gap:.0f} 分钟未刷新(Hermes cron 每 15 分钟应更新)"})
    except Exception:  # noqa: BLE001
        pass
    return alerts
