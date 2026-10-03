# -*- coding: utf-8 -*-
"""V3 PIT replay interface (§8/§9). get_information_available_at(T) returns ONLY what was
knowable at T. Conservative availability; no lookahead; deterministic; hash-verified."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
REG_DIR = os.path.join(V3, "research", "v3_pit_macro_registry")
REGISTRY = os.path.join(REG_DIR, "pit_macro_registry.json")

# conservative availability delays (documented, frozen)
MARKET_BAR_DELAY = timedelta(days=1)     # a daily bar dated D is fully known at D+1 00:00Z
CALENDAR_DELAY = timedelta(seconds=-1)   # date-level events available end of that day


class PITIntegrityError(RuntimeError):
    pass


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def load_registry(path=REGISTRY):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def registry_hash(path=REGISTRY):
    return _sha(open(path, "rb").read())


def verify_hashes(reg=None):
    """Test 4: every stored series must match the hash recorded in the registry."""
    reg = reg or load_registry()
    out = {"ok": True, "checked": 0, "mismatches": []}
    for e in reg.get("admitted", []):
        p = os.path.join(V3, e["stored_at"]) if e.get("stored_at") else None
        if not p or not os.path.exists(p):
            out["ok"] = False
            out["mismatches"].append({"source": e["source"], "reason": "file missing"})
            continue
        h = _sha(open(p, "rb").read())
        out["checked"] += 1
        if h != e["hash"]:
            out["ok"] = False
            out["mismatches"].append({"source": e["source"], "expected": e["hash"][:16], "got": h[:16]})
    return out


def _parse_series(entry):
    """Return [(obs_date_utc, value, source_timezone, availability_utc)]. No unfinished bars."""
    p = os.path.join(V3, entry["stored_at"])
    raw = open(p, "rb").read()
    txt = raw.decode("utf-8", errors="replace")
    rows = []
    if txt.lstrip().startswith("{"):                      # yahoo chart json
        d = json.loads(txt)
        res = (d.get("chart") or {}).get("result") or []
        if res:
            ts = res[0].get("timestamp") or []
            q = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
            closes = q.get("close") or []
            for i, t in enumerate(ts):
                c = closes[i] if i < len(closes) else None
                if c is None:
                    continue
                dt = datetime.fromtimestamp(int(t), timezone.utc)
                rows.append((dt, float(c), "UTC", dt + MARKET_BAR_DELAY))
    else:                                                  # treasury csv
        lines = [l for l in txt.splitlines() if l.strip()]
        for l in lines[1:]:
            parts = l.split(",")
            if len(parts) < 2:
                continue
            try:
                dt = datetime.strptime(parts[0].strip(), "%m/%d/%Y").replace(tzinfo=timezone.utc)
                val = float(parts[1])
            except Exception:  # noqa: BLE001
                continue
            rows.append((dt, val, "US/Eastern(official release)", dt + MARKET_BAR_DELAY))
    return sorted(rows, key=lambda r: r[0])


def get_information_available_at(timestamp, reg=None, registry_path=REGISTRY):
    """Return ONLY observations knowable at `timestamp`. Deterministic given (registry, timestamp)."""
    reg = reg or load_registry(registry_path)
    t = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(
        str(timestamp).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    t = t.astimezone(timezone.utc)

    out, leaks = [], []
    for e in reg.get("admitted", []):
        if e.get("status") not in ("PASS", "CONDITIONAL"):
            continue
        if e.get("observation_time") == "date column" or e.get("source", "").startswith(("YAHOO", "US_TREASURY")):
            rows = _parse_series(e)
        else:
            rows = []
        visible = []
        for (obs, val, tz, avail) in rows:
            if avail <= t:
                visible.append({"observation_time": obs.isoformat(), "value": val,
                                 "source_timezone": tz, "timezone": "UTC",
                                 "availability_time": avail.isoformat()})
            else:
                leaks.append({"source": e["source"], "observation_time": obs.isoformat(),
                               "availability_time": avail.isoformat()})
        if visible:
            out.append({"source": e["source"], "series": e["series"], "status": e["status"],
                         "confidence": e.get("confidence"), "n_visible": len(visible),
                         "latest": visible[-1], "observations": visible})
    return {"timestamp": t.isoformat(), "registry_hash": registry_hash(registry_path)
            if os.path.exists(registry_path) else None,
            "sources": out, "withheld_future": len(leaks),
            "note": "withheld_future counts observations whose availability is later than the decision time"}


def assert_no_lookahead(timestamp, reg=None, registry_path=REGISTRY):
    """Test 1: nothing returned may have availability_time > timestamp."""
    res = get_information_available_at(timestamp, reg=reg, registry_path=registry_path)
    t = datetime.fromisoformat(res["timestamp"])
    for s in res["sources"]:
        for o in s["observations"]:
            if datetime.fromisoformat(o["availability_time"]) > t:
                raise PITIntegrityError(f"LOOKAHEAD: {s['source']} {o['observation_time']}")
    return True
