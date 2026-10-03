# -*- coding: utf-8 -*-
"""v1_loss_build.py — V1 loss forensics: rebuild all 32 trades (decision scene / path / counterfactuals).
READ-ONLY (no orders; no writes outside this audit dir). Strict PIT: decision features use only data
with timestamp <= decision_ts; outcome features use only data > decision_ts.
Writes: TRADE_ERROR_DATABASE.jsonl + V1_LOSS_MACHINE.json + m1_bars_snapshot.parquet (input snapshot).
"""
from __future__ import annotations
import datetime as dt, glob, hashlib, json, os, sys
import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_loss_forensics")
os.makedirs(OUT, exist_ok=True)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "truth"))
import gates, truth_lib as TR  # noqa: E402

LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
TICKS = r"C:\AIQuant\data\live_fxtm"
M1_TFS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "60m": 3_600_000}
SRV_OFF = 10_800_000
NOW = dt.datetime.now(dt.timezone.utc)

L = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
LEDGER_SHA = hashlib.sha256(open(LEDGER, "rb").read()).hexdigest()

# ---------- broker deals (read-only) ----------
env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5  # noqa: E402
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
assert mt5.initialize(**kw), mt5.last_error()
frm = dt.datetime(2026, 9, 25, tzinfo=dt.timezone.utc); to = NOW + dt.timedelta(days=1)
deals = mt5.history_deals_get(frm, to) or []
bars = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M1, frm, to)
mt5.shutdown()
d90011 = [d for d in deals if int(getattr(d, "magic", 0) or 0) == 90011]
by_pos = {}
for d in d90011:
    r = by_pos.setdefault(str(d.position_id), {"open": None, "close": None})
    if d.entry == 0: r["open"] = d
    elif d.entry == 1: r["close"] = d

m1 = pd.DataFrame(bars)
m1["ts"] = pd.to_datetime(m1["time"], unit="s", utc=True)
m1 = m1.set_index("ts").sort_index()[["open", "high", "low", "close"]]
m1.to_parquet(os.path.join(OUT, "m1_bars_snapshot.parquet"))   # RAW as-read (server frame); frame documented
M1_SHA = hashlib.sha256(open(os.path.join(OUT, "m1_bars_snapshot.parquet"), "rb").read()).hexdigest()
# INSTRUMENT FIX: MT5 bar 'time' is server frame (UTC+3). Convert once for ALL downstream analytics.
m1.index = m1.index - pd.Timedelta(hours=3)

# ---------- tick loader with per-day cache ----------
# INSTRUMENT FINDING (2026-10-02): archive ts_utc labels are SERVER frame (UTC+3), NOT true UTC.
# Verified vs engine snapshots (328/390 align at +3h) and per-trade fill/exit anchoring.
# Also the collector fetches with a ~3h lag (param-frame mismatch) — labels converted here; raw kept.
LABEL_TO_TRUE_MS = 10_800_000
_tick_cache = {}


def ticks_between(a_ms, b_ms):
    """Ticks (converted to TRUE-UTC ms) within true-frame window [a_ms, b_ms]."""
    d0 = dt.datetime.fromtimestamp(a_ms / 1000, dt.timezone.utc).date()
    d1 = dt.datetime.fromtimestamp((b_ms + LABEL_TO_TRUE_MS) / 1000, dt.timezone.utc).date()
    days = pd.date_range(d0, d1 + dt.timedelta(days=1), freq="D")
    parts = []
    for d in days:
        key = d.strftime("%Y%m%d")
        if key not in _tick_cache:
            p = os.path.join(TICKS, f"ticks_{key}.parquet")
            if os.path.exists(p):
                t = pd.read_parquet(p, columns=["ts_utc", "bid", "ask"])
                _tick_cache[key] = (t["ts_utc"].astype("int64").to_numpy() - LABEL_TO_TRUE_MS,
                                    t["bid"].to_numpy(np.float64), t["ask"].to_numpy(np.float64))
            else:
                _tick_cache[key] = (np.array([], dtype=np.int64), np.array([]), np.array([]))
        parts.append(_tick_cache[key])
    ts = np.concatenate([p[0] for p in parts]); b = np.concatenate([p[1] for p in parts]); a = np.concatenate([p[2] for p in parts])
    m = (ts >= a_ms) & (ts <= b_ms)
    ts, b, a = ts[m], b[m], a[m]
    o = np.argsort(ts, kind="mergesort")
    return ts[o], b[o], a[o]

def at_or_after(ts, x):
    i = np.searchsorted(ts, x, side="left")
    return i if i < len(ts) else None

def scan_levels(ts, b, a, t0, side, sl, tp, cap_ms):
    """First touch of sl/tp after t0 using exit-side prices (long->bid, short->ask); None if no touch."""
    m = ts >= t0; i0 = int(np.searchsorted(ts, t0, side="left"))
    if i0 >= len(ts): return None
    if side == "LONG": seq = b[i0:]
    else: seq = a[i0:]
    tseq = ts[i0:]
    cap = tseq <= cap_ms
    seq = np.where(cap, seq, np.nan)
    hit_tp = seq >= tp; hit_sl = seq <= sl
    j_tp = np.argmax(hit_tp) if hit_tp.any() else None
    j_sl = np.argmax(hit_sl) if hit_sl.any() else None
    if j_tp is None and j_sl is None: return None
    if j_tp is None: return ("SL", int(tseq[j_sl]), float(seq[j_sl]))
    if j_sl is None: return ("TP", int(tseq[j_tp]), float(seq[j_tp]))
    return ("SL", int(tseq[j_sl]), float(seq[j_sl])) if j_sl <= j_tp else ("TP", int(tseq[j_tp]), float(seq[j_tp]))

def resample_ok(tf_ms):
    g = m1.resample(f"{tf_ms // 60000}min", label="left", closed="left")
    o = g.agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    o["close_ms"] = np.asarray(o.index.values, dtype="datetime64[ms]").astype(np.int64) + tf_ms
    return o

BARS = {v: resample_ok(v) for v in M1_TFS.values()}

def tf_features(tf_ms, cutoff_ms):
    df = BARS[tf_ms]
    d = df[df["close_ms"] <= cutoff_ms]           # PIT: only CLOSED bars
    if len(d) < 30: return None, None
    c = d["close"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy()
    ma20 = c[-20:].mean(); ma_prev = c[-23:-3].mean()
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    atr14 = float(tr[-14:].mean())
    rng_hi, rng_lo = h[-20:].max(), l[-20:].min()
    rets = np.diff(c[-15:]) / c[-15:-1]
    feat = {"last_close": round(float(c[-1]), 3), "ma20": round(float(ma20), 3),
            "dir_vs_ma20": int(np.sign(c[-1] - ma20)), "ma20_slope": round(float(ma20 - ma_prev), 4),
            "atr14": round(atr14, 3), "range_pos": round(float((c[-1] - rng_lo) / max(rng_hi - rng_lo, 1e-9)), 3),
            "ret4_bps": round(float((c[-1] - c[-5]) / c[-5] * 1e4), 2) if len(c) >= 5 else None,
            "vol14_bps": round(float(np.std(rets) * 1e4), 2) if len(rets) > 2 else None,
            "trend_strength_atr": round(float(abs(c[-1] - ma20) / max(atr14, 1e-9)), 3)}
    return feat, int(d["close_ms"].iloc[-1])

def session_of(ts_utc):
    h = ts_utc.hour
    return "ASIA" if h < 7 else "LONDON" if h < 13 else "NY" if h < 21 else "LATE"

# ---------- guard counterfactual for all trades ----------
def net_of(pid):
    r = by_pos.get(str(pid))
    if not r or not r["close"] or not r["open"]: return None
    return round(float(r["close"].profit) + float(r["close"].commission) + float(r["open"].commission) + float(r["close"].swap), 2)

def gstate(when_utc, day, basis):
    tot, cons = 0.0, 0
    recs = []
    for e in L:
        if e.get("event") != "PNL": continue
        utc = gates.realized_close_utc(e)
        if utc > when_utc or utc.date().isoformat() != day: continue
        v = float(e.get("pnl") or 0) if basis == "price" else (net_of(e.get("position_id")) if net_of(e.get("position_id")) is not None else float(e.get("pnl") or 0))
        recs.append((utc, v))
    recs.sort()
    for _, v in recs:
        tot += v; cons = cons + 1 if v < 0 else 0
    return {"daily": round(tot, 2), "cons": cons}

# ---------- build ----------
DB = []
for e in [x for x in L if x["event"] == "POSITION"]:
    pid = str(e.get("order_id"))
    rr = by_pos.get(pid)
    if not rr or not rr["open"] or not rr["close"]:
        continue
    o, c = rr["open"], rr["close"]
    entry_ms = (int(o.time) - 10800) * 1000
    exit_ms = (int(c.time) - 10800) * 1000
    send = next((x for x in L if x.get("event") == "ORDER_SEND" and str(x.get("order_id")) == pid), None)
    dec = None
    if send:
        cands = [x for x in L if x.get("event") == "DECISION" and x.get("seq", 0) < send.get("seq", 0)]
        dec = next((x for x in reversed(cands) if str(x.get("action")) in ("ENTER", "WOULD_ENTER")), None)
    if dec is None: continue
    dec_ms = int(dt.datetime.fromisoformat(dec["ts_utc"]).timestamp() * 1000)
    oi = dec.get("order_intent") or {}
    side = "LONG" if int(o.type) == 0 else "SHORT"
    entry_px = float(o.price); risk = abs(entry_px - float(oi.get("sl") or 0)) or None
    # structure (PIT)
    struct, cut_used = {}, dec_ms
    for tf, ms in M1_TFS.items():
        f, cu = tf_features(ms, dec_ms)
        struct[tf] = f
        if cu: cut_used = min(cut_used, dec_ms) if False else cut_used
    # liquidity proxy from ticks <= dec_ms
    lt0 = dec_ms - 15 * 60_000
    tts, tb, ta = ticks_between(lt0 - 60_000, dec_ms + 60_000)
    n_pre = int(((tts >= lt0) & (tts <= dec_ms)).sum())
    liq = round(n_pre / 15.0, 1)
    max_tick_dec = int(tts[tts <= dec_ms].max()) if (tts <= dec_ms).any() else None
    # outcome path (ticks) — entry..exit
    pts, mfe_r, mae_r, t_mfe, t_mae = {}, None, None, None, None
    win_ts, win_b, win_a = ticks_between(entry_ms - 30_000, min(exit_ms + 8 * 3_600_000, int(NOW.timestamp() * 1000)))
    if len(win_ts):
        for mark in (5, 15, 30, 60):
            t = entry_ms + mark * 60_000
            k = at_or_after(win_ts, t)
            if k is not None:
                mv = (win_b[k] + win_a[k]) / 2
                pts[f"+{mark}m"] = round((mv - entry_px) / entry_px * 1e4 * (1 if side == "LONG" else -1), 2)
        msk = (win_ts >= entry_ms) & (win_ts <= exit_ms)
        if msk.any() and risk:
            if side == "LONG":
                fav = win_b[msk].max(); adv = win_b[msk].min()
                i_f = np.argmax(win_b[msk]); i_a = np.argmin(win_b[msk])
            else:
                fav = win_a[msk].min(); adv = win_a[msk].max()
                i_f = np.argmin(win_a[msk]); i_a = np.argmax(win_a[msk])
            mfe_r = round((abs(fav - entry_px)) / risk, 3); mae_r = round(abs(adv - entry_px) / risk, 3)
            t_mfe = round((win_ts[msk][i_f] - entry_ms) / 60_000, 1); t_mae = round((win_ts[msk][i_a] - entry_ms) / 60_000, 1)
    # actual R (price based)
    r_val = None
    if risk and risk > 0:
        r_val = round((float(c.price) - entry_px) / risk * (1 if side == "LONG" else -1), 3)
    dur_min = round((exit_ms - entry_ms) / 60_000, 1)
    # counterfactuals
    cf = {}
    for dly in (15, 30):
        k = at_or_after(win_ts, entry_ms + dly * 60_000)
        if k is not None and risk:
            ep = (win_b[k] + win_a[k]) / 2
            sl2 = ep - risk if side == "LONG" else ep + risk
            tp2 = ep + 1.5 * risk if side == "LONG" else ep - 1.5 * risk
            hit = scan_levels(win_ts, win_b, win_a, entry_ms + dly * 60_000, side, sl2, tp2, exit_ms + 3_600_000)
            if hit:
                cf[f"timing_{dly}m"] = {"entry": round(ep, 2), "hit": hit[0],
                                         "out_r": round(1.5 if hit[0] == "TP" else -1.0, 2)}
            else:
                kk = at_or_after(win_ts, exit_ms + 3_600_000) or len(win_ts) - 1
                mp = (win_b[kk] + win_a[kk]) / 2
                cf[f"timing_{dly}m"] = {"entry": round(ep, 2), "hit": "NONE",
                                         "out_r": round((mp - ep) / risk * (1 if side == "LONG" else -1), 2)}
    # opposite direction at entry
    if risk and len(win_ts):
        k0 = at_or_after(win_ts, entry_ms)
        if k0 is not None:
            opp = "SHORT" if side == "LONG" else "LONG"
            ep = (win_b[k0] + win_a[k0]) / 2
            sl2 = ep + risk if opp == "SHORT" else ep - risk
            tp2 = ep - 1.5 * risk if opp == "SHORT" else ep + 1.5 * risk
            hit = scan_levels(win_ts, win_b, win_a, entry_ms, opp, sl2, tp2, exit_ms + 3_600_000)
            cf["opposite"] = {"side": opp, "hit": hit[0] if hit else "NONE",
                              "out_r": round(1.5 if (hit and hit[0] == "TP") else (-1.0 if hit else 0.0), 2)}
    for mark in (15, 30, 60):
        k = at_or_after(win_ts, entry_ms + mark * 60_000)
        if k is not None and risk:
            mp = (win_b[k] + win_a[k]) / 2
            cf[f"time_stop_{mark}m"] = round((mp - entry_px) / risk * (1 if side == "LONG" else -1), 2)
    k60 = at_or_after(win_ts, dec_ms + 60 * 60_000)
    if k60 is not None and risk:
        mp = (win_b[k60] + win_a[k60]) / 2
        cf["no_trade_move_60m_r"] = round((mp - entry_px) / risk * (1 if side == "LONG" else -1), 2)
    ke = at_or_after(win_ts, exit_ms + 30 * 60_000)
    if ke is not None and risk:
        mp = (win_b[ke] + win_a[ke]) / 2
        cf["reversal_after_exit_30m_r"] = round((mp - float(c.price)) / risk * (1 if side == "LONG" else -1), 2)
    # guard counterfactual
    dts = dt.datetime.fromisoformat(dec["ts_utc"])
    gp = gstate(dts, dts.date().isoformat(), "price"); gn = gstate(dts, dts.date().isoformat(), "net")
    blk_p = (gp["daily"] <= -20) or (gp["cons"] >= 3); blk_n = (gn["daily"] <= -20) or (gn["cons"] >= 3)
    # error classification (losses)
    pnl_price = float(c.profit)
    is_loss = pnl_price < 0
    exec_anom = bool(send is None or send.get("ok") is not True or send.get("retcode") != 10009
                     or (send.get("slippage_bps") is not None and abs(send.get("slippage_bps")) > 15)
                     or oi.get("sl") is None or oi.get("tp") is None)
    t60 = struct.get("60m") or {}
    against60 = bool(t60.get("dir_vs_ma20") and side != ("LONG" if t60["dir_vs_ma20"] > 0 else "SHORT"))
    weak_trend = bool(t60.get("trend_strength_atr") is not None and t60["trend_strength_atr"] < 0.3)
    contrib = []
    if blk_p: contrib.append("declared_guard_would_block(price basis)")
    if blk_n: contrib.append("declared_guard_would_block(net basis)")
    if against60: contrib.append("entry_against_60m_ma20")
    if mfe_r is not None and mfe_r >= 0.5: contrib.append("MFE>=0.5R_given_back")
    if is_loss:
        if exec_anom: primary = "EXECUTION_ERROR"
        elif blk_p or blk_n: primary = "RISK_ERROR"
        elif mfe_r is not None and mfe_r >= 0.5: primary = "TIMING_ERROR"
        elif against60: primary = "DIRECTION_ERROR"
        elif weak_trend: primary = "REGIME_ERROR"
        else: primary = "NO_IDENTIFIABLE_ERROR"
    else:
        primary = "N_A_WIN"
    if struct.get("15m") is None or struct.get("60m") is None or mfe_r is None:
        primary = "UNKNOWN"
    rec = {
        "trade_id": TR.trade_id(pid), "position_id": pid, "outcome": ("LOSS" if is_loss else "WIN"),
        "entry": {"ts_utc": dt.datetime.fromtimestamp(entry_ms / 1000, dt.timezone.utc).isoformat(), "price": entry_px,
                   "side": side, "qty": float(o.volume), "deal_ticket": int(o.ticket)},
        "exit": {"ts_utc": dt.datetime.fromtimestamp(exit_ms / 1000, dt.timezone.utc).isoformat(), "price": float(c.price),
                  "comment": str(c.comment), "deal_ticket": int(c.ticket)},
        "pnl_price": round(pnl_price, 2), "commission": round(float(c.commission) + float(o.commission), 2),
        "swap": float(c.swap), "net": net_of(pid), "R": r_val,
        "decision": {"seq": dec.get("seq"), "ts_utc": dec.get("ts_utc"), "action": dec.get("action"),
                      "event_id": TR.event_id(dec), "signal": dec.get("signal"), "live_state": dec.get("live_state"),
                      "risk_reasons": dec.get("risk_reasons"), "snapshot": dec.get("snapshot"), "order_intent": oi,
                      "signal_type": dec.get("signal_type"), "not_hermes_alpha": dec.get("not_hermes_alpha")},
        "execution": {"retcode": (send or {}).get("retcode"), "slippage_bps": (send or {}).get("slippage_bps"),
                       "latency_ms": (send or {}).get("latency_ms"), "req_price": (send or {}).get("price"),
                       "fill_price": (send or {}).get("fill_price")},
        "guard_cf": {"state_price": gp, "state_net": gn, "block_price": blk_p, "block_net": blk_n},
        "session": session_of(dt.datetime.fromtimestamp(dec_ms / 1000, dt.timezone.utc)),
        "spread_bps": (dec.get("snapshot") or {}).get("spread_bps"), "liquidity_ticks_per_min_15m": liq,
        "structure": struct, "path": {"pts_bps": pts, "mfe_r": mfe_r, "mae_r": mae_r, "t_mfe_min": t_mfe,
                                       "t_mae_min": t_mae, "duration_min": dur_min},
        "cf": cf, "primary_root_cause": primary, "contributing": contrib,
        "pit": {"decision_cutoff_ms": dec_ms, "max_decision_tick_ms": max_tick_dec,
                 "max_bar_close_ms": max((BARS[tf]["close_ms"][BARS[tf]["close_ms"] <= dec_ms].max()
                                          for tf in BARS if (BARS[tf]["close_ms"] <= dec_ms).any()), default=None)},
    }
    DB.append(rec)

with open(os.path.join(OUT, "TRADE_ERROR_DATABASE.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
    for r in DB:
        fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
machine = {"schema": "v1_loss_machine/1", "generated_utc": NOW.isoformat(), "n_trades": len(DB),
           "ledger_sha256": LEDGER_SHA, "m1_snapshot_sha256": M1_SHA,
           "wins": sum(1 for r in DB if r["outcome"] == "WIN"), "losses": sum(1 for r in DB if r["outcome"] == "LOSS")}
json.dump(machine, open(os.path.join(OUT, "V1_LOSS_MACHINE.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# summary print
import collections
cc = collections.Counter(r["primary_root_cause"] for r in DB)
print("trades:", len(DB), "| wins:", machine["wins"], "| losses:", machine["losses"])
print("primary:", dict(cc))
for r in DB:
    print(f"{r['trade_id']} {r['outcome']:<4} R={r['R']} mfe={r['path']['mfe_r']} mae={r['path']['mae_r']} "
          f"dur={r['path']['duration_min']}m {r['session']:<6} spread={r['spread_bps']} "
          f"blk={r['guard_cf']['block_price']}/{r['guard_cf']['block_net']} cause={r['primary_root_cause']}")
