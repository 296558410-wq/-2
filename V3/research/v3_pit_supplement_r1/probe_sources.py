# -*- coding: utf-8 -*-
"""V3 Phase-2 PIT supplement R1 - bounded source probe (ONE attempt per candidate).

Read-only. No purchases, no registrations, no keys printed/stored.
Writes SOURCE_AUDIT.json. Never mutates the frozen dictionary.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
DICT_PATH = os.path.join(HERE, "PIT_FIELD_DICTIONARY.json")
OUT = os.path.join(HERE, "SOURCE_AUDIT.json")
CKPT = os.path.join(HERE, "_probe_cache")

YAHOO = {
    "YAHOO_DXY_1H_2Y": ("DX-Y.NYB", "1h", "2y"),
    "YAHOO_VIX_1H_2Y": ("%5EVIX", "1h", "2y"),
    "YAHOO_DXY_5M_60D": ("DX-Y.NYB", "5m", "60d"),
    "YAHOO_VIX_5M_60D": ("%5EVIX", "5m", "60d"),
}
# prior stored sha256 (source_matrix.json, 2026-09-25) for reproducibility comparison
PRIOR_HASH = {
    "YAHOO_DXY_1H_2Y": "9507d567ab1be9a460cf9555c246693d",
    "YAHOO_VIX_1H_2Y": None,
    "YAHOO_DXY_5M_60D": "daf153ccd1c7244eb8ddf4acb041adf1",
    "YAHOO_VIX_5M_60D": "fd75313b15142072464fd99de1bb78f0",
}


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:32]


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def parse_yahoo(raw):
    j = json.loads(raw.decode("utf-8", "replace"))
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        return None
    ts = res[0].get("timestamp") or []
    return {"rows": len(ts),
            "first_utc": datetime.fromtimestamp(ts[0], tz=timezone.utc).isoformat() if ts else None,
            "last_utc": datetime.fromtimestamp(ts[-1], tz=timezone.utc).isoformat() if ts else None}


def main():
    dict_hash = hashlib.sha256(open(DICT_PATH, "rb").read()).hexdigest()
    audit = {
        "schema": "v3_pit_supplement_source_audit/1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "dictionary_frozen_hash": dict_hash,
        "dictionary_frozen_at": json.load(open(DICT_PATH, encoding="utf-8"))["ts_utc"],
        "probe_policy": "one attempt per candidate; no window retry; rate-limit/error pages are not data",
        "sources": {},
    }
    os.makedirs(CKPT, exist_ok=True)

    # ---- T3 Yahoo (reproducibility re-fetch) ----
    for name, (sym, iv, rng) in YAHOO.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={iv}&range={rng}"
        rec = {"tier": "T3_market", "url": url, "http_status": None, "bytes": None,
               "payload_verified": False, "reproduced": None, "prior_sha256": PRIOR_HASH.get(name)}
        try:
            st, raw = fetch(url)
            rec["http_status"] = st
            rec["bytes"] = len(raw)
            open(os.path.join(CKPT, name + ".json"), "wb").write(raw)
            rec["sha256"] = sha16(raw)
            p = parse_yahoo(raw)
            if p and p["rows"] > 100:
                rec.update(p)
                rec["payload_verified"] = True
                rec["reproduced"] = (p["rows"] > 0)
            else:
                rec["note"] = "payload not a series"
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}:{e}"
        audit["sources"][name] = rec

    # ---- T2 Jin10 MCP calendar (one call) ----
    jin = {"tier": "T2_event_calendar", "endpoint": "https://mcp.jin10.com/mcp",
           "http_status": None, "payload_verified": False, "reproduced": None,
           "token_echoed": False}
    try:
        sys.path.insert(0, r"C:\Users\surface\.openclaw\workspace\v1_reset_001")
        from v3_jin10_mcp import MCPClient  # noqa: E402
        cli = MCPClient()
        cli.initialize()
        cli.initialized()
        r = cli.tools_call("list_calendar", {})
        evs = r.get("events") if isinstance(r, dict) else None
        if evs is None and isinstance(r, list):
            evs = r
        raw = json.dumps(evs, ensure_ascii=False, sort_keys=True).encode("utf-8")
        jin["http_status"] = 200
        jin["rows"] = len(evs) if evs else 0
        jin["raw_hash"] = sha16(raw)
        if evs:
            pt = [e.get("pub_time") for e in evs if e.get("pub_time")]
            jin["pub_time_min"] = min(pt) if pt else None
            jin["pub_time_max"] = max(pt) if pt else None
            jin["payload_verified"] = len(evs) > 50
        # compare with the stored prior pull
        prior = os.path.join(os.path.dirname(V3), "v3_long_history_data", "V3_JIN10_EVENT_PIT.json")
        if os.path.exists(prior):
            pj = json.load(open(prior, encoding="utf-8"))
            jin["prior_count"] = pj.get("count")
            jin["prior_raw_hash"] = pj.get("raw_hash")
            jin["prior_retrieved_at_utc"] = pj.get("retrieved_at_utc")
            jin["reproduced"] = (jin.get("rows") == pj.get("count"))
    except Exception as e:  # noqa: BLE001
        jin["error"] = f"{type(e).__name__}:{e}"
    audit["sources"]["JIN10_MCP_list_calendar"] = jin

    # ---- T1 official (local control, no fetch) ----
    tre = {"tier": "T1_official", "name": "US_TREASURY_YIELD_CURVE", "signal": "local-file-hash-check"}
    reg = os.path.join(V3, "research", "v3_pit_macro_registry", "pit_macro_registry.json")
    try:
        d = json.load(open(reg, encoding="utf-8"))
        entries = {e["source"]: e for e in d.get("admitted", [])}
        ok = []
        for k, e in entries.items():
            if not k.startswith("US_TREASURY"):
                continue
            p = os.path.join(V3, e["stored_at"])
            if os.path.exists(p):
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                ok.append({"source": k, "hash_match": h == e["hash"]})
        tre["entries"] = ok
        tre["payload_verified"] = all(x["hash_match"] for x in ok) if ok else False
    except Exception as e:  # noqa: BLE001
        tre["error"] = f"{type(e).__name__}:{e}"
    audit["sources"]["US_TREASURY_YIELD_CURVE"] = tre

    json.dump(audit, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("dict frozen hash:", dict_hash[:24])
    for k, v in audit["sources"].items():
        print(f"{k:26s} http={v.get('http_status')} bytes={v.get('bytes')} rows={v.get('rows')} "
              f"verified={v.get('payload_verified')} reproduced={v.get('reproduced')} err={v.get('error','')}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
