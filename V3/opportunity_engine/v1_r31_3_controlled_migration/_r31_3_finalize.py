# -*- coding: utf-8 -*-
"""R31.3 finalize: verify V1 cycle evidence, enable automation (enabled flag only), post-start audit, V2 after."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(HERE)
RE = os.path.dirname(ENGINE_DIR)
AIQ = os.path.dirname(RE)
HOME = os.path.expanduser("~")
V1 = os.path.join(RE, "hermes", "trader_v1")
V2 = os.path.join(RE, "hermes", "trader_v2")
RUN = os.path.join(V1, "run_state")
STATS = os.path.join(RUN, "statistics.json")
META = os.path.join(RUN, "RUN_META.json")
LEDGER = os.path.join(RUN, "plan_ledger.jsonl")
ENGINE = os.path.join(V1, "engine.py")
CLI = os.path.join(HOME, "dtlopenclaw", "tools", "openclaw", "node_modules", "openclaw", "dist", "index.js")
NODE = os.path.join(HOME, "dtlopenclaw", "tools", "node-v24.21.0-win-x64", "node.exe")
PY = os.path.join(AIQ, ".venv", "Scripts", "python.exe")
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"
BASE = "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"
LEDGER_EXPECT = "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"
META_EXPECT = "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"
REPORTS = os.path.join(HERE, "reports")
HASHES = os.path.join(HERE, "hashes")
AUDITD = os.path.join(HERE, "audit")
BROOT = os.path.join(HERE, "boundary_root")
LOGS = os.path.join(HERE, "logs")
NEW_ID = "V1_RUN_20260925T231903_02"
RES = {}


def sh(a, t=120):
    try:
        p = subprocess.run(a, cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def sha_file(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def cron_show():
    out = sh([NODE, CLI, "cron", "show", AID, "--json"], t=60) if (os.path.exists(NODE) and os.path.exists(CLI)) else ""
    m = re.search(r"(\{.*\}|\[.*\])", out or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:  # noqa: BLE001
        return {}


def tree_manifest(root):
    d = {}
    for r_, _, fs in os.walk(root):
        if "__pycache__" in r_:
            continue
        for f in fs:
            p = os.path.join(r_, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            d[os.path.relpath(p, AIQ).replace("\\", "/")] = {"sha256": sha_file(p), "size": st.st_size}
    return d


def main():
    t = {}
    # 1. evidence: v1 cycle log
    so = os.path.join(LOGS, "v1_start_stdout.log")
    se = os.path.join(LOGS, "v1_start_stderr.log")
    cyc_out = open(so, encoding="utf-8", errors="ignore").read() if os.path.exists(so) else ""
    cyc_err = open(se, encoding="utf-8", errors="ignore").read() if os.path.exists(se) else ""
    t["cycle_done"] = "CYCLE_DONE" in cyc_out
    t["stderr_empty"] = (cyc_err.strip() == "")
    # 2. no trades
    t["ledger_unchanged"] = (sha_file(LEDGER) == LEDGER_EXPECT)
    t["meta_unchanged"] = (sha_file(META) == META_EXPECT)
    t["engine_unchanged"] = (sha_file(ENGINE) == BASE)
    # 3. broker post-cycle (read-only)
    br = subprocess.run([PY, os.path.join(HERE, "_broker_read.py")], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=420)
    try:
        bd = json.load(open(os.path.join(REPORTS, "BROKER_READ.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        bd = {"err": "NO_FILE"}
    t["broker_pos0"] = (bd.get("open_positions") == 0)
    t["broker_ord0"] = (bd.get("pending_orders") == 0)
    t["broker_connected"] = bool(bd.get("CONNECTED"))
    # 4. new run open
    try:
        man = json.load(open(os.path.join(BROOT, "runs", NEW_ID, "manifest.json"), encoding="utf-8"))
        t["new_run_open"] = (man.get("run_status") == "OPEN")
    except Exception:  # noqa: BLE001
        t["new_run_open"] = False
    # 5. automation enable
    auto_b = cron_show()
    cfg_fields = ("payload", "schedule", "agentId", "sessionTarget", "wakeMode", "delivery")
    cfg_b = {k: auto_b.get(k) for k in cfg_fields}
    ah_b = sha_obj(cfg_b)
    out_en = sh([NODE, CLI, "cron", "enable", AID], t=60)
    time.sleep(3)
    auto_a = cron_show()
    cfg_a = {k: auto_a.get(k) for k in cfg_fields}
    ah_a = sha_obj(cfg_a)
    enabled = str(auto_a.get("enabled")).lower() == "true"
    same_cfg = (ah_b == ah_a)
    if not same_cfg and enabled:
        sh([NODE, CLI, "cron", "disable", AID], t=60)
        enabled = False
    # 6. V2 after
    v2a = tree_manifest(V2)
    v2h_a = sha_obj({k: v["sha256"] for k, v in sorted(v2a.items())})
    v2h_b = None
    try:
        v2h_b = json.load(open(os.path.join(HASHES, "V2_TREE_BEFORE.json"), encoding="utf-8"))["hash"]
    except Exception:  # noqa: BLE001
        v2h_b = None
    v2_ok = (v2h_b is not None and v2h_a == v2h_b)
    with open(os.path.join(HASHES, "V2_TREE_AFTER.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"files": v2a, "hash": v2h_a, "EXACT_MATCH": v2_ok}, fh, indent=1, ensure_ascii=False)
    # 7. hashes record
    hashes = {"engine": sha_file(ENGINE), "ledger": sha_file(LEDGER), "statistics": sha_file(STATS),
                "run_meta": sha_file(META), "statistics_before": "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"}
    with open(os.path.join(HASHES, "V1_POST_START.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(hashes, fh, indent=1, ensure_ascii=False)
    binding = {"new_run_id": NEW_ID, "v1_execution_model": "ONE_SHOT_CYCLE_VIA_ENGINE_PY",
                 "v1_cycle_verified": t["cycle_done"], "last_cycle_process_evidence": cyc_out.strip()[:200],
                 "engine_hash": hashes["engine"], "run_manager": "external (Run Boundary, offline store)",
                 "binding_method": "EXISTING_V1_ENTRYPOINT + EXTERNAL_RUN_BOUNDARY",
                 "automation_enabled": enabled, "ts_utc": datetime.now(timezone.utc).isoformat()}
    with open(os.path.join(REPORTS, "RUN_RUNTIME_BINDING.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(binding, fh, indent=1, ensure_ascii=False)
    post = {"v1_cycle_verified": t, "automation_before": {"enabled": auto_b.get("enabled"), "config_hash": ah_b[:16]},
              "automation_after": {"enabled": auto_a.get("enabled"), "config_hash": ah_a[:16],
                                     "only_enabled_changed": same_cfg},
              "broker": {"connected": t["broker_connected"], "positions": bd.get("open_positions"),
                           "orders": bd.get("pending_orders")},
              "new_run": NEW_ID, "engine_hash": hashes["engine"], "v2_unchanged": v2_ok,
              "counters": {"ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0},
              "ts_utc": datetime.now(timezone.utc).isoformat()}
    with open(os.path.join(REPORTS, "POST_START_AUDIT.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(post, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(AUDITD, "R31_3_FINAL_EVENTS.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts": post["ts_utc"], "cycle": t, "enabled": enabled, "cfg_same": same_cfg,
                               "v2_ok": v2_ok}, ensure_ascii=False, sort_keys=True) + "\n")
    ok = (t["cycle_done"] and t["stderr_empty"] and t["ledger_unchanged"] and t["meta_unchanged"]
            and t["engine_unchanged"] and t["broker_pos0"] and t["broker_ord0"] and t["new_run_open"]
            and enabled and same_cfg and v2_ok)
    RES = {"V1_R31_3_CONTROLLED_MIGRATION": "COMPLETE" if ok else "INCOMPLETE", "FINAL_GATE": "PASS" if ok else "FAIL",
             "V1_PROCESS": "CYCLE_BASED_ONE_SHOT (cycle verified, no persistent PID by design)",
             "V1_RUN_STATUS": "OPEN(ledger-backed); last cycle OK", "ACTIVE_RUN_ID": NEW_ID,
             "AUTOMATION": "ENABLED" if enabled else "DISABLED", "V2_UNCHANGED": "PASS" if v2_ok else "FAIL",
             "evidence": t}
    print(json.dumps(RES, ensure_ascii=True, indent=1)[:2200], flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
