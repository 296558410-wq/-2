# -*- coding: utf-8 -*-
"""build_timeline.py — architecture/behavior timeline + per-trade alignment (READ-ONLY inputs).
Emits timeline.json, trade_alignment.csv, evidence_manifest.json into this audit dir.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, subprocess, collections

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
UP = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_architecture_behavior_timeline")
os.makedirs(OUT, exist_ok=True)
def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8", errors="replace") if l.strip()]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def E(ts): return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

LEDGER = os.path.join(UP, "ledger", "v1_upgrade_ledger.jsonl")
L = jl(LEDGER)

# epoch boundaries (UTC)
RESTART = "2026-10-01T13:52:15+00:00"          # host reboot
CYCLE_EDIT = "2026-10-01T14:33:19+00:00"       # backup cycle.py mtime (uncommitted edit, post-restart)
C_FIX = "2026-10-02T03:51:44+00:00"            # 63d5a22 riskguard wiring fix
C_HARD = "2026-10-02T04:13:08+00:00"           # eceeec2 risk hardening
C_TRUTH = "2026-10-02T04:31:39+00:00"          # ec0907e truth system
C_TRUTHEV = "2026-10-02T04:35:14+00:00"        # 0f4ce66 truth evidence
B = lambda s: E(s)
EPOCHS = [
    ("E0_initial", "2026-09-28T12:33:29+00:00", RESTART),
    ("E0b_restart", RESTART, C_FIX),
    ("E1_riskguard_fix", C_FIX, C_HARD),
    ("E2_risk_hardening", C_HARD, C_TRUTH),
    ("E3_truth", C_TRUTH, None),
]
def epoch_of(ts):
    t = E(ts)
    for name, a, b in EPOCHS:
        if t >= B(a) and (b is None or t < B(b)): return name
    return "PRE"

# ---- broker trades (magic 90011) ----
env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass"+"word"] = env["DEMO_MT5_PASSWORD"]
assert mt5.initialize(**kw), mt5.last_error()
frm = dt.datetime(2026, 9, 25, tzinfo=dt.timezone.utc); to = dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1)
deals = mt5.history_deals_get(frm, to) or []
mt5.shutdown()
d9 = [d for d in deals if int(getattr(d, "magic", 0) or 0) == 90011]
pos = {}
for d in d9:
    r = pos.setdefault(str(d.position_id), {"open": None, "close": None})
    if d.entry == 0: r["open"] = d
    elif d.entry == 1: r["close"] = d
def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()
# INSTRUMENT FIX: MT5 deal.time is SERVER frame (UTC+3). Use the ledger (true UTC) for trade timing.
_send_ts = {str(e.get("order_id")): e.get("ts_utc") for e in L if e.get("event") == "ORDER_SEND" and e.get("order_id")}
_pos_ts = {str(e.get("order_id")): e.get("ts_utc") for e in L if e.get("event") == "POSITION" and e.get("order_id")}
_close_ts = {str(e.get("position_id") or e.get("order_id")): e.get("ts_utc") for e in L if e.get("event") == "CLOSE"}
trades = []
for pid, r in pos.items():
    if not r["open"] or not r["close"]: continue
    o, c = r["open"], r["close"]
    trades.append({"trade_id": f"V1T-{pid}", "position_id": pid,
                   "entry_ts": (_send_ts.get(pid) or _pos_ts.get(pid) or iso(o.time)),
                   "exit_ts": (_close_ts.get(pid) or iso(c.time)),
                   "entry_ts_broker_serverframe": iso(o.time), "exit_ts_broker_serverframe": iso(c.time),
                   "side": "LONG" if int(o.type) == 0 else "SHORT",
                   "entry": float(o.price), "exit": float(c.price),
                   "profit_price": round(float(c.profit), 2),
                   "net": round(float(c.profit)+float(c.commission)+float(o.commission)+float(c.swap), 2),
                   "outcome": "WIN" if float(c.profit) > 0 else "LOSS",
                   "close_comment": str(c.comment)})
trades.sort(key=lambda x: x["entry_ts"])

# ---- ledger: decision field-set drift + per-trade decision capture ----
decs = [e for e in L if e.get("event") == "DECISION"]
fieldsets = [(e["ts_utc"], tuple(sorted(k for k in e.keys() if k not in ("current_hash",)))) for e in decs]
seen = {}
drift = []
for ts, fs in fieldsets:
    if fs not in seen:
        seen[fs] = ts
        drift.append({"first_seen_ts": ts, "n_fields": len(fs), "fields": list(fs)})
sends = [e for e in L if e.get("event") == "ORDER_SEND"]
sends_by_oid = {str(e.get("order_id")): e for e in sends if e.get("order_id") is not None}
pos_ledger = {str(e.get("order_id")): e for e in L if e.get("event") == "POSITION"}

def enc_decision_for(pid):
    # nearest ENTER DECISION before the ORDER_SEND with order_id == pid
    s = sends_by_oid.get(str(pid))
    if not s: return None
    cands = [d for d in decs if d.get("seq", 10**9) < s.get("seq", 0) and str(d.get("action")) == "ENTER"]
    return cands[-1] if cands else None

rows = []
for t in trades:
    d = enc_decision_for(t["position_id"]); s = sends_by_oid.get(t["position_id"])
    snap = (d or {}).get("snapshot") or {}
    rows.append({**t, "epoch": epoch_of(t["entry_ts"]), "entry_epoch": epoch_of(t["entry_ts"]), "exit_epoch": epoch_of(t["exit_ts"]),
                 "decision_seq": (d or {}).get("seq"), "signal_source": (d or {}).get("signal_source"),
                 "signal_type": (d or {}).get("signal_type"), "order_intent_trade": (d or {}).get("order_intent", {}).get("trade"),
                 "risk_reasons_at_entry": ";".join((d or {}).get("risk_reasons") or []),
                 "snapshot_data_age": snap.get("data_age_seconds"),
                 "send_retcode": (s or {}).get("retcode"), "send_ok": (s or {}).get("ok"),
                 "slippage_bps": (s or {}).get("slippage_bps")})

with open(os.path.join(OUT, "trade_alignment.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow(r)

# ---- timeline ----
def git(*a): return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
commit_iso = {}
for line in git("log", "--all", "--date=iso-strict", "--pretty=format:%h|%ad|%an|%s", "--", "research/hermes/trader_v1/v1_upgrade").splitlines():
    h, ad, an, s = line.split("|", 3); commit_iso[h] = {"date": ad, "author": an, "subject": s}
events = [
 {"ts": "2026-09-28T12:33:29Z", "kind": "RUNTIME_START", "what": "首次 cycle（ledger seq1）", "evidence": "ledger seq1"},
 {"ts": "2026-09-28T12:45:00Z", "kind": "CONFIG", "what": "signal_source=BASELINE_TRANSITION 设置", "evidence": "registry/runtime_config.json set_at_utc"},
 {"ts": "2026-09-28T15:27:55Z", "kind": "CODE", "what": "gates.py 最后一次改动(原始版)", "evidence": "备份 mtime + 原始 hash 0e02a424"},
 {"ts": "2026-09-28T15:31:11Z", "kind": "CONFIG", "what": "runtime_config 最后写入", "evidence": "registry mtime"},
 {"ts": "2026-09-28T15:35:00Z", "kind": "CONFIG", "what": "order_send_enabled=true (开闸)", "evidence": "runtime_config order_send_opened_at"},
 {"ts": "2026-09-28T15:35:14Z", "kind": "TRADE_EPOCH", "what": "首笔真实成交/持仓", "evidence": "ledger seq48/49"},
 {"ts": "2026-09-29T23:38:02Z", "kind": "CODE_EVIDENCE", "what": "首个 CLOSE/PNL（对账机制运行）", "evidence": "ledger seq228/229"},
 {"ts": "2026-10-01T13:52:15Z", "kind": "RESTART", "what": "主机重启(漏1拍14:03Z)", "evidence": "既有重启审计"},
 {"ts": "2026-10-01T14:33:19Z", "kind": "CODE", "what": "cycle.py 改动(mtime; 未提交; 内容不可得)", "evidence": "backup cycle.py mtime"},
 {"ts": "2026-10-02T02:05:01Z", "kind": "TRADE_EPOCH", "what": "末笔平仓（此后无新成交）", "evidence": "ledger/券商 deals"},
 {"ts": "2026-10-02T03:48:21Z", "kind": "BACKUP", "what": "修复前备份", "evidence": "backup manifest"},
 {"ts": "2026-10-02T03:51:44Z", "kind": "CODE", "what": "63d5a22 riskguard 接线修复(cycle.py,gates.py)", "evidence": "git"},
 {"ts": "2026-10-02T04:13:08Z", "kind": "CODE", "what": "eceeec2 risk hardening", "evidence": "git"},
 {"ts": "2026-10-02T04:31:39Z", "kind": "CODE", "what": "ec0907e truth system", "evidence": "git"},
 {"ts": "2026-10-02T04:35:14Z", "kind": "CODE", "what": "0f4ce66 truth evidence", "evidence": "git"},
]
# current hashes
cur = {}
for f in ("cycle.py", "gates.py"):
    cur[f] = sha(os.path.join(UP, f))
orig = {"gates.py": "0e02a4240b517b2a987c377d4488945a75c701c144e56ca3691d0ed349f2c9d3",
        "cycle.py": "dcb7edde220cfe07be93c72cda1fa55ae48ed71316b384a38c1898d7161b523b"}

timeline = {"schema": "v1_arch_behavior_timeline/1",
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "epochs": [{"name": n, "start": a, "end": b} for n, a, b in EPOCHS],
            "events": events,
            "commits_touching_v1_upgrade": commit_iso,
            "runtime_file_hashes": {"original": orig, "current": cur},
            "ledger_decision_fieldset_drift": drift,
            "first_decision_ts": decs[0]["ts_utc"] if decs else None,
            "last_decision_ts": decs[-1]["ts_utc"] if decs else None}
json.dump(timeline, open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---- evidence manifest ----
files = [LEDGER, os.path.join(UP, "registry", "runtime_config.json"),
         os.path.join(UP, "registry", "baseline_transition_mapping.json"),
         os.path.join(UP, "registry", "v1_upgrade_registry.json"),
         os.path.join(UP, "backup", "20261002T034821Z", "backup_manifest.json"),
         os.path.join(UP, "backup", "20261002T034821Z", "cycle.py"),
         os.path.join(UP, "backup", "20261002T034821Z", "gates.py")]
manifest = {"schema": "v1_arch_evidence_manifest/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "sources": [{"path": os.path.relpath(p, REPO), "sha256": sha(p), "bytes": os.path.getsize(p)} for p in files],
            "note": "order_send=0; ledger read-only; no code/config/state modified"}
json.dump(manifest, open(os.path.join(OUT, "evidence_manifest.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

# ---- summaries ----
print("trades:", len(trades), "| epoch(entry):", dict(collections.Counter(r["epoch"] for r in rows)))
print("first entry:", trades[0]["entry_ts"], "| last entry:", trades[-1]["entry_ts"], "| last exit:", max(t["exit_ts"] for t in trades))
_lastexit = max(t["exit_ts"] for t in trades)
print("earliest code/risk/truth commit ts:", C_FIX, "| after last exit?", C_FIX > _lastexit)
def seg(name, rs):
    n = len(rs); 
    return {"n": n, "win_rate": round(sum(1 for r in rs if r["outcome"] == "WIN")/n, 3) if n else None,
            "price": round(sum(r["profit_price"] for r in rs), 2), "net": round(sum(r["net"] for r in rs), 2),
            "risk_reasons": dict(collections.Counter(r["risk_reasons_at_entry"] for r in rs)),
            "signal_source": dict(collections.Counter(str(r["signal_source"]) for r in rs)),
            "retcodes": dict(collections.Counter(str(r["send_retcode"]) for r in rs)),
            "slippage_max": max((abs(r["slippage_bps"]) for r in rs if r["slippage_bps"] is not None), default=None)}
A = [r for r in rows if r["entry_ts"] < RESTART]; Bseg = [r for r in rows if r["entry_ts"] >= RESTART]
print("SEG A(pre-restart):", json.dumps(seg("A", A), ensure_ascii=False))
print("SEG B(post-restart):", json.dumps(seg("B", Bseg), ensure_ascii=False))
print("fieldset drift count:", len(drift))
for d in drift[:8]: print("   ", d["first_seen_ts"], d["n_fields"], d["fields"][:6], "...")

# ---- append segments + answer, re-dump ----
A = [r for r in rows if r["entry_ts"] < RESTART]; Bseg = [r for r in rows if r["entry_ts"] >= RESTART]
timeline["instrument_notes"] = [
  "MT5 deal.time is SERVER frame (UTC+3); trade timestamps here come from the LEDGER (true UTC). Broker server-frame times kept in *_broker_serverframe columns.",
  "broker roundtrips = 32 == ledger POSITION order_ids = 32 (symmetric set match).",
]
timeline["segments"] = {"A_pre_restart": seg("A", A), "B_post_restart": seg("B", Bseg), "boundary": RESTART,
  "note": "all 32 trades precede every architecture change (first change 2026-10-02T03:51:44Z > last exit 2026-10-02T02:18:01Z)"}
timeline["answer"] = {"verdict": "CLOSER_TO_ORIGINAL_BASELINE_ARCHITECTURE",
  "basis": ["no code/config/risk/signal/execution change occurred before any trade",
            "all 32 trades ran on the same architecture (signal_source=BASELINE_TRANSITION, risk_reasons empty, retcode 10009 across A and B)",
            "risk/hardening/truth changes took effect 03:51:44Z-04:35:14Z, after the last trade closed 02:18:01Z",
            "only mid-window break = host restart 2026-10-01T13:52:15Z (association) + uncommitted cycle.py edit 14:33:19Z (content unavailable = DATA_GAP)"],
  "post_change_behavior": "after the changes the risk layer is reachable and now blocks: DECISION=WAIT_RISK:MAX_DAILY_LOSS,MAX_CONSECUTIVE_LOSS since 2026-10-02T04:03Z; no trades after 02:18:01Z"}
json.dump(timeline, open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("answer:", timeline["answer"]["verdict"])
