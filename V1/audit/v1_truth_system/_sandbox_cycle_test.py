# -*- coding: utf-8 -*-
"""Sandbox end-to-end run of the TRUTH-WIRED cycle.py. Production ledger/snapshots untouched."""
import json, os, shutil, subprocess, sys, tempfile

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_upgrade")
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
tmp = tempfile.mkdtemp(prefix="v1up_truth_sb_")
sb = os.path.join(tmp, "v1_upgrade")
shutil.copytree(ROOT, sb, ignore=shutil.ignore_patterns("__pycache__", "backup"))
cyp = os.path.join(sb, "cycle.py")
src = open(cyp, encoding="utf-8").read().replace(
    'ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_upgrade")', f'ROOT = r"{sb}"')
open(cyp, "w", encoding="utf-8", newline="\n").write(src)
cfgp = os.path.join(sb, "registry", "runtime_config.json")
cfg = json.load(open(cfgp, encoding="utf-8")); cfg["order_send_enabled"] = False
json.dump(cfg, open(cfgp, "w", encoding="utf-8", newline="\n"), indent=1)
r = subprocess.run([PY, cyp, "--dry-run"], capture_output=True, text=True, timeout=300, cwd=REPO)
out = {}
if r.stdout.strip():
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        out = {"_raw": r.stdout[-400:]}
print("exit:", r.returncode)
print(json.dumps({k: out.get(k) for k in ("action", "order_sent", "cycle_id", "decision_id", "truth_record_ok",
                                           "truth_record_error", "truth_incidents", "truth_check_error",
                                           "kill_switch", "dedup_key", "schedule_gap_minutes", "ledger_chain_ok")},
                 ensure_ascii=False, indent=1))
snap = os.path.join(sb, "truth", "evidence", "decision_snapshots.jsonl")
print("sandbox snapshot exists:", os.path.exists(snap), "lines:", sum(1 for _ in open(snap, encoding="utf-8")) if os.path.exists(snap) else 0)
if os.path.exists(snap):
    d = json.loads(open(snap, encoding="utf-8").read().strip().splitlines()[-1])
    print("snapshot fields:", json.dumps({k: d.get(k) for k in ("cycle_id", "decision_id", "data_age", "decision", "risk_reasons")}, ensure_ascii=False))
led = os.path.join(sb, "ledger", "v1_upgrade_ledger.jsonl")
last = [json.loads(l) for l in open(led, encoding="utf-8") if l.strip()][-1]
print("sandbox ledger last:", json.dumps({k: last.get(k) for k in ("seq", "event", "action", "cycle_id", "decision_id", "truth_record_ok")}, ensure_ascii=False))
inc = os.path.join(sb, "truth", "evidence", "incidents.jsonl")
print("sandbox incidents lines:", sum(1 for _ in open(inc, encoding="utf-8")) if os.path.exists(inc) else 0)
if r.stderr.strip():
    print("stderr tail:", r.stderr[-400:])
shutil.rmtree(tmp, ignore_errors=True)
