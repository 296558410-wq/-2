# -*- coding: utf-8 -*-
"""Jin10 read-only probe (connectivity + endpoint inspection). No orders/trade/account/MT5/broker.

Credentials (if ever provided) come only from the local environment:
    os.getenv("V3_JIN10_TOKEN")   # never read from git / chat / this file
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) v3-jin10-probe"
ENDPOINTS = [
    ("web", "https://www.jin10.com/"),
    ("flash_web", "https://flash.jin10.com/"),
    ("rili_web", "https://rili.jin10.com/"),
    ("official_mcp", "https://mcp.jin10.com/mcp"),
    ("official_mcp_oauth_metadata", "https://mcp.jin10.com/.well-known/oauth-authorization-server"),
    ("flash_api_unofficial", "https://flash-api.jin10.com/get_flash_list"),
    ("datacenter_api_unofficial", "https://datacenter-api.jin10.com/"),
]


def probe(url, cap=120_000):
    rec = {"endpoint": url, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dns_result": None, "connect_result": None, "tls_result": None, "http_status": None,
            "latency_ms": None, "response_size": 0, "response_hash": None, "error": None}
    host = url.split("//", 1)[1].split("/")[0]
    try:
        rec["dns_result"] = sorted({a[4][0] for a in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"dns: {e}"; return rec
    t0 = time.time()
    try:
        with socket.create_connection((host, 443), timeout=8) as s:
            rec["connect_result"] = "OK"
            with ssl.create_default_context().wrap_socket(s, server_hostname=host) as ss:
                rec["tls_result"] = ss.version()
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"tcp/tls: {e}"; rec["latency_ms"] = round((time.time()-t0)*1000, 1); return rec
    try:
        hdr = {"User-Agent": UA}
        tok = os.getenv("V3_JIN10_TOKEN")
        if tok:
            hdr["Authorization"] = "Bearer " + tok          # only from local env; never stored here
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=12) as r:
            b = r.read(cap)
            rec.update(http_status=getattr(r, "status", None), response_size=len(b),
                        response_hash=hashlib.sha256(b).hexdigest())
    except urllib.error.HTTPError as e:
        rec.update(http_status=e.code, error=f"HTTPError {e.code}")
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {str(e)[:100]}"
    rec["latency_ms"] = round((time.time()-t0)*1000, 1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connectivity", action="store_true")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    out = [probe(u) for _, u in ENDPOINTS] if (a.connectivity or a.inspect or not any([a.connectivity, a.inspect])) else []
    doc = {"schema": "v3_jin10_probe/1", "ts_utc": datetime.now(timezone.utc).isoformat(),
            "token_present": bool(os.getenv("V3_JIN10_TOKEN")), "results": out}
    if a.json:
        json.dump(doc, open(a.json, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    for r in out:
        print(f"{r['endpoint'][:52]:54s} dns={'ok' if r['dns_result'] else 'FAIL'} "
              f"tls={str(r['tls_result']):8s} http={str(r['http_status']):6s} "
              f"{str(r['latency_ms']):>7s}ms {r['error'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
