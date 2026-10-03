# -*- coding: utf-8 -*-
"""Backup production files/state before applying the V1 risk-guard patch. Writes only into a backup dir."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, shutil, subprocess

BASE = r"C:\AIQuant\research\hermes\trader_v1\v1_upgrade"
FILES = ["gates.py", "cycle.py", "registry/runtime_config.json", "ledger/v1_upgrade_ledger.jsonl"]
ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
bdir = os.path.join(BASE, "backup", ts)
os.makedirs(bdir, exist_ok=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


man = {"backup_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "ts": ts, "files": {}}
for f in FILES:
    src = os.path.join(BASE, f)
    dst = os.path.join(bdir, f.replace("/", "__"))
    shutil.copy2(src, dst)
    man["files"][f] = {"sha256": sha(src), "size": os.path.getsize(src), "backup": os.path.basename(dst)}
led = os.path.join(BASE, "ledger", "v1_upgrade_ledger.jsonl")
lines = [l for l in open(led, encoding="utf-8") if l.strip()]
man["ledger_lines"] = len(lines)
man["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=r"C:\AIQuant", capture_output=True, text=True).stdout.strip()
json.dump(man, open(os.path.join(bdir, "backup_manifest.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
# also record the pre-apply ledger snapshot at a stable path for before/after accounting
snap = {"snapshot_utc": man["backup_utc"], "ledger_sha256": man["files"]["ledger/v1_upgrade_ledger.jsonl"]["sha256"],
        "ledger_lines": len(lines), "last_event": json.loads(lines[-1]), "backup_dir": bdir}
json.dump(snap, open(os.path.join(BASE, "ledger", "_pre_apply_snapshot.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(man, ensure_ascii=False, indent=1))
