# -*- coding: utf-8 -*-
"""startup_check.py — read-only pre-flight for resuming V1 DEMO auto-trading."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, collections
REPO = r"C:\AIQuant"; BASE = os.path.join(REPO, "research", "hermes", "trader_v1"); UP = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_demo_resume_20261002"); os.makedirs(OUT, exist_ok=True)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
R = {}
# 1) config / registry / kill switch
rc = os.path.join(UP, "registry", "runtime_config.json")
R["runtime_config"] = json.load(open(rc, encoding="utf-8"))
ks = os.path.join(UP, "registry", "kill_switch.json")
R["kill_switch_file"] = {"path": "registry/kill_switch.json", "exists": os.path.exists(ks),
                         "content": (open(ks, encoding="utf-8").read().strip() if os.path.exists(ks) else None),
                         "interpretation": "missing => OFF (per v1-risk-hardening)"}
reg = json.load(open(os.path.join(UP, "registry", "v1_upgrade_registry.json"), encoding="utf-8"))
R["registry"] = {"isolation": reg.get("isolation"), "risk_limits": reg.get("risk_limits"), "execution": reg.get("execution")}
# 2) mapping hash unchanged
mp = os.path.join(UP, "registry", "baseline_transition_mapping.json")
m = json.load(open(mp, encoding="utf-8"))
def sha_obj(o): return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
recomputed = sha_obj({k: v for k, v in m.items() if k != "mapping_hash"})
R["mapping"] = {"file_sha256": sha(mp), "stored_mapping_hash": m.get("mapping_hash"),
                "recomputed_mapping_hash": recomputed, "match": m.get("mapping_hash") == recomputed,
                "frozen_expected_d59e9e9d": m.get("mapping_hash") == "d59e9e9d489c81c5af8625213def7006438d9a35e36fb4c1af97ac08433b95fa"}
# 3) code hashes
R["code_sha256"] = {f: sha(os.path.join(UP, f)) for f in ("cycle.py", "gates.py", "signal_baseline.py", "label_adapter.py", "run_gates.py")}
R["code_sha256_expected"] = {"cycle.py": "0ed44fb8fe654ea04904c16ffbfc527bf3b620f2c3a192e94cfb848c6e6f9ef8",
                             "gates.py": "b784999aa3b4517c" }
# 4) ledger chain
import sys; sys.path.insert(0, UP)
import gates
lg = gates.Ledger(os.path.join(UP, "ledger", "v1_upgrade_ledger.jsonl"))
ok, n, bad = lg.verify()
rep = lg.replay()
L = [json.loads(l) for l in open(os.path.join(UP, "ledger", "v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
tail = L[-1]
R["ledger"] = {"chain_ok": ok, "events": n, "bad": bad, "replay": rep,
               "last_event": {"seq": tail.get("seq"), "ts_utc": tail.get("ts_utc"), "event": tail.get("event"),
                              "action": tail.get("action"), "risk_reasons": tail.get("risk_reasons")},
               "event_counts": dict(collections.Counter(e.get("event") for e in L))}
# 5) MT5 demo + isolation (read-only)
env = {}
for line in open(os.path.join(REPO, ".env.mt5_demo"), encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
import MetaTrader5 as mt5
kw = {"path": os.environ.get("V1UP_MT5_PATH", r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"),
      "login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
kw["pass"+"word"] = env["DEMO_MT5_PASSWORD"]
init_ok = mt5.initialize(**kw)
R["mt5"] = {"init_ok": init_ok, "last_error": str(mt5.last_error())}
if init_ok:
    ai = mt5.account_info(); pos = mt5.positions_get() or []; ords = mt5.orders_get() or []
    R["mt5"].update({"login": ai.login if ai else None, "server": ai.server if ai else None,
                     "trade_mode": ("DEMO" if ai and ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "NON_DEMO"),
                     "currency": ai.currency if ai else None, "balance": ai.balance if ai else None,
                     "equity": ai.equity if ai else None,
                     "positions": [{"ticket": p.ticket, "symbol": p.symbol, "magic": p.magic, "comment": p.comment, "volume": p.volume} for p in pos],
                     "positions_by_magic": dict(collections.Counter(int(p.magic) for p in pos)),
                     "pending_orders_by_magic": dict(collections.Counter(int(o.magic) for o in ords))})
    mt5.shutdown()
json.dump(R, open(os.path.join(OUT, "STARTUP_CHECK.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:3500])
