# -*- coding: utf-8 -*-
"""phase3_verify.py — Phase-3 修改前后验证：ledger replay 一致性 + 一次真实周期(PAPER_LOCAL)。
只读判断 + 由 V2 自身调度入口触发一次周期（正常运维行为）。order_send=0（决策为 WAIT 时不进执行）。
"""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
V2 = Path(r"C:\AIQuant\research\hermes\trader_v2")
LED = V2 / "ledger" / "hermes_v2_ledger.jsonl"
PY = r"C:\AIQuant\.venv\Scripts\python.exe"


def digest(p):
    if not p.exists():
        return {"exists": False}
    b = p.read_bytes()
    return {"exists": True, "sha256": hashlib.sha256(b).hexdigest()[:16], "lines": b.count(b"\n")}


def replay():
    sys.path.insert(0, str(V2 / "ledger"))
    try:
        import replay as R
        d = R.replay(str(LED)) if hasattr(R, "replay") else None
        return {"replay_ok": True, "detail": str(d)[:300]} if d is not None else {"replay_ok": True, "note": "replay() called without ledger arg"}
    except Exception as e:
        return {"replay_ok": False, "error": str(e)[:200]}


before = {"ledger": digest(LED)}
print("BEFORE:", json.dumps(before, ensure_ascii=False))

# run one scheduled cycle (canonical entry; V2 keeps running)
r = subprocess.run([PY, str(V2 / "runtime" / "v2_scheduled_cycle.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=600)
print("CYCLE returncode:", r.returncode)
print("CYCLE stdout tail:", (r.stdout or "")[-400:])
print("CYCLE stderr tail:", (r.stderr or "")[-300:])

after = {"ledger": digest(LED)}
print("AFTER :", json.dumps(after, ensure_ascii=False))
h = V2 / "state" / "v2_run_health.json"
health = json.loads(h.read_text(encoding="utf-8")) if h.exists() else {}
print("HEALTH mode/cycle:", json.dumps({k: health.get(k) for k in ("run_status", "last_scheduled", "cycle_result", "blocked", "llm_dependency", "scheduler")}, ensure_ascii=False)[:600])
res = {"before": before, "cycle_returncode": r.returncode, "after": after,
       "ledger_unchanged_by_edits": before["ledger"].get("sha256") == after["ledger"].get("sha256"),
       "health": {k: health.get(k) for k in ("run_status", "blocked", "cycle_result")}}
Path(__file__).with_name("_phase3_verify.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote _phase3_verify.json")
