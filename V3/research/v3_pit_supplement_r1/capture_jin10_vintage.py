# -*- coding: utf-8 -*-
"""Jin10 calendar vintage capture (parse fix). Read-only; token never printed/stored.

Finding: list_calendar returns a ROLLING ~1-week window -> history is NOT retrievable.
Therefore each pull must be frozen as its own vintage with its own hash.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
VINT = os.path.join(HERE, "vintages")
os.makedirs(VINT, exist_ok=True)


def extract(r):
    """MCP tools/call -> result.content[0].text (a JSON string)."""
    res = r.get("result") if isinstance(r, dict) else None
    if not res:
        return None
    for c in res.get("content", []):
        if c.get("type") == "text":
            try:
                j = json.loads(c["text"])
            except Exception:  # noqa: BLE001
                continue
            if isinstance(j, dict) and isinstance(j.get("data"), list):
                return j["data"]
            if isinstance(j, list):
                return j
    return None


def main():
    sys.path.insert(0, r"C:\Users\surface\.openclaw\workspace\v1_reset_001")
    from v3_jin10_mcp import MCPClient  # noqa: E402
    cli = MCPClient(); cli.initialize(); cli.initialized()
    r = cli.tools_call("list_calendar", {})
    evs = extract(r)
    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%SZ")
    rec = {"schema": "v3_jin10_calendar_vintage/1", "captured_at_utc": ts.isoformat(),
           "source": "JIN10_MCP_list_calendar", "endpoint": "https://mcp.jin10.com/mcp",
           "calls_made_for_this_vintage": 2,
           "call_note": "call 1 returned data but the probe parser mis-read the envelope; call 2 re-parsed correctly (parse fix, not a window retry)",
           "count": len(evs) if evs else 0, "token_echoed": False, "events": evs or []}
    if evs:
        pt = sorted(e.get("pub_time") for e in evs if e.get("pub_time"))
        rec["pub_time_min"] = pt[0]
        rec["pub_time_max"] = pt[-1]
        rec["pub_time_timezone_original"] = "Asia/Shanghai"
        rec["raw_hash"] = hashlib.sha256(
            json.dumps(evs, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        rec["revised_non_null"] = sum(1 for e in evs if e.get("revised"))
    path = os.path.join(VINT, f"JIN10_CALENDAR_{stamp}.json")
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # compare with the previously stored vintage (2026-09-25)
    prior_p = os.path.join(os.path.dirname(HERE), "..", "..", "..", "..",
                           "v3_long_history_data", "V3_JIN10_EVENT_PIT.json")
    prior_p = os.path.normpath(prior_p)
    cmp = {}
    if os.path.exists(prior_p):
        pj = json.load(open(prior_p, encoding="utf-8"))
        cmp = {"prior_count": pj.get("count"), "prior_hash": pj.get("raw_hash"),
               "prior_window": [pj.get("events", [{}])[0].get("pub_time_original"),
                                pj.get("events", [{}])[-1].get("pub_time_original")] if pj.get("events") else None,
               "prior_retrieved_at_utc": pj.get("retrieved_at_utc")}
    rec["vs_prior_vintage"] = cmp
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"captured": stamp, "count": rec["count"],
                      "window": [rec.get("pub_time_min"), rec.get("pub_time_max")],
                      "hash": rec.get("raw_hash", "")[:24], "revised_non_null": rec.get("revised_non_null"),
                      "vs_prior": cmp}, ensure_ascii=False, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
