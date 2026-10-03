# -*- coding: utf-8 -*-
"""R31.3 MT5 probe: start terminal if needed, poll read-only connection with a longer window."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
AIQ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
TERMINAL = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
REP = os.path.join(HERE, "reports")
os.makedirs(REP, exist_ok=True)


def ps(cmd, t=90):
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def main():
    out = {"ts_utc": datetime.now(timezone.utc).isoformat()}
    plist = ps("Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,StartTime | ConvertTo-Json -Compress")
    out["terminal_processes"] = plist[:400]
    if "ERR:" in plist or plist in ("", "null"):
        out["start_action"] = "STARTED"
        ps(f"Start-Process -FilePath '{TERMINAL}'")
        time.sleep(10)
        plist2 = ps("Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,StartTime | ConvertTo-Json -Compress")
        out["terminal_processes_after_start"] = plist2[:400]
    else:
        out["start_action"] = "ALREADY_RUNNING"
    # poll connect
    code = ("import json,time\ntry:\n import MetaTrader5 as mt5\n"
             f" ok=False\n for i in range(40):\n  ok=mt5.initialize(path=r'{TERMINAL}')\n"
             "  if ok: break\n  time.sleep(4)\n"
             " ai=mt5.account_info(); ti=mt5.terminal_info()\n"
             " ps_=mt5.positions_get(); os_=mt5.orders_get()\n"
             " print(json.dumps({'CONNECTED':bool(ok),'login':(str(ai.login) if ai else None),"
             "'server':(ai.server if ai else None),'currency':(ai.currency if ai else None),"
             "'balance':(ai.balance if ai else None),'equity':(ai.equity if ai else None),"
             "'free_margin':(ai.margin_free if ai else None),'connected':(ti.connected if ti else None),"
             "'trade_allowed':(ti.trade_allowed if ti else None),"
             "'positions':(None if ps_ is None else len(ps_)),'orders':(None if os_ is None else len(os_)),"
             "'last_error':mt5.last_error()}))\n mt5.shutdown()\nexcept Exception as ex:\n"
             " print(json.dumps({'err':type(ex).__name__+':'+str(ex)[:150]}))\n")
    res = {}
    try:
        pr = subprocess.run([PY, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=240)
        o = (pr.stdout or "").strip()
        res = json.loads(o.splitlines()[-1]) if o else {}
        out["api_stdout_tail"] = o[-300:]
    except Exception as ex:  # noqa: BLE001
        res = {"err": type(ex).__name__}
    out["mt5"] = res
    if res.get("login"):
        s = str(res["login"])
        out["login_masked"] = "***" + s[-3:]
    with open(os.path.join(REP, "MT5_PROBE.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out, ensure_ascii=True, indent=1)[:1800], flush=True)


if __name__ == "__main__":
    main()
