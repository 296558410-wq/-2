# -*- coding: utf-8 -*-
"""Tiny flag helper: prints READY / NOT_READY (+numbers) from HOLD_STATUS.json. For the ready-watcher trigger."""
import json, os, sys

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HOLD_STATUS.json")
try:
    d = json.load(open(p, encoding="utf-8"))
    tag = "READY" if d.get("ready") else "NOT_READY"
    print(f"{tag} days={d.get('calendar_days')} active={d.get('active_days')} end={d.get('t_max_utc')} status={d.get('data_status')}")
except Exception as e:  # noqa: BLE001
    print(f"UNKNOWN {str(e)[:120]}")
