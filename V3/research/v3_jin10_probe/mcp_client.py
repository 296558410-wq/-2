# -*- coding: utf-8 -*-
"""Jin10 MCP client (standard flow) for V3 research.

Flow: initialize -> notifications/initialized -> tools/list / resources/list -> tools/call
Protocol: 2025-11-25. Prefers result.structuredContent. Pagination: cursor -> data.next_cursor / data.has_more.
Token: read ONLY from C:\\AIQuant\\.env.v3_jin10 ; never printed, never stored in outputs.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV_FILE = r"C:\AIQuant\.env.v3_jin10"
OUT = r"C:\AIQuant\research\v3_jin10_probe"
DEFAULT_URL = "https://mcp.jin10.com/mcp"
PROTOCOL = "2025-11-25"


def load_env():
    kv = {}
    if os.path.exists(ENV_FILE):
        for ln in open(ENV_FILE, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                kv[k.strip()] = v.strip()
    return kv


class MCPClient:
    def __init__(self, url=None, token=None, protocol=PROTOCOL, timeout=45):
        kv = load_env()
        self.url = url or kv.get("V3_JIN10_MCP_URL", DEFAULT_URL)
        self.token = token or kv.get("V3_JIN10_TOKEN", "")
        self.protocol = protocol or kv.get("V3_JIN10_PROTOCOL_VERSION", PROTOCOL)
        self.timeout = timeout
        self.session_id = None
        self._id = 0
        self.log = []

    def _headers(self):
        h = {"Content-Type": "application/json",
              "Accept": "application/json, text/event-stream",
              "User-Agent": "v3-jin10-mcp/1.0"}
        if self.token:
            h["Authorization"] = "Bearer " + self.token
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    @staticmethod
    def _parse(raw, ctype):
        txt = (raw or b"").decode("utf-8", "replace")
        if "text/event-stream" in (ctype or "") or txt.lstrip().startswith("event:") or "data:" in txt[:200]:
            for line in txt.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload and payload != "[DONE]":
                        try:
                            return json.loads(payload)
                        except Exception:  # noqa: BLE001
                            continue
            return {"_sse_unparsed": txt[:400]}
        try:
            return json.loads(txt) if txt.strip() else {}
        except Exception:  # noqa: BLE001
            return {"_raw": txt[:400]}

    def rpc(self, method, params=None, notify=False):
        self._id += 1
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            body["id"] = self._id
        data = json.dumps(body).encode()
        req = urllib.request.Request(self.url, data=data, headers=self._headers(), method="POST")
        rec = {"method": method, "ok": False, "http": None, "ctype": None, "error": None}
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                rec["http"] = getattr(r, "status", None)
                rec["ctype"] = r.headers.get("Content-Type")
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                raw = r.read(4_000_000)
            if notify:
                rec["ok"] = True
                rec["notification"] = True
            else:
                j = self._parse(raw, rec["ctype"])
                rec["ok"] = ("error" not in j)
                rec["result"] = j.get("result")
                rec["jsonrpc_error"] = j.get("error")
            self.log.append(rec)
            return rec
        except urllib.error.HTTPError as e:
            rec["http"] = e.code
            try:
                rec["body_sample"] = e.read(300).decode("utf-8", "replace")[:200]
            except Exception:  # noqa: BLE001
                pass
            rec["error"] = f"HTTPError {e.code}"
            self.log.append(rec)
            return rec
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {str(e)[:140]}"
            self.log.append(rec)
            return rec

    # --- convenience ---
    def initialize(self):
        return self.rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {},
                                        "clientInfo": {"name": "v3-jin10-mcp", "version": "1.0.0"}})

    def initialized(self):
        return self.rpc("notifications/initialized", None, notify=True)

    def tools_list(self):
        return self.rpc("tools/list", {})

    def resources_list(self):
        return self.rpc("resources/list", {})

    def resources_read(self, uri):
        return self.rpc("resources/read", {"uri": uri})

    def tools_call(self, name, args):
        return self.rpc("tools/call", {"name": name, "arguments": args})


def sc(res):
    """Preferred machine-readable payload: structuredContent, else parsed content text."""
    if not res or not isinstance(res, dict):
        return None
    r = res.get("result") or {}
    if isinstance(r, dict):
        if "structuredContent" in r:
            return r["structuredContent"]
        c = r.get("content")
        if isinstance(c, list) and c:
            for item in c:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        return json.loads(item.get("text") or "")
                    except Exception:  # noqa: BLE001
                        return {"_text": (item.get("text") or "")[:400]}
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    cli = MCPClient()
    rep = {"endpoint": cli.url, "protocol": cli.protocol, "token_present": bool(cli.token),
            "token_printed": False, "steps": {}}

    rep["steps"]["initialize"] = {k: v for k, v in cli.initialize().items() if k != "result"}
    init_res = cli.log[-1].get("result")
    rep["server_info"] = (init_res or {}).get("serverInfo") if isinstance(init_res, dict) else None
    rep["negotiated_protocol"] = (init_res or {}).get("protocolVersion") if isinstance(init_res, dict) else None
    rep["steps"]["initialized"] = {k: v for k, v in cli.initialized().items() if k != "result"}

    tl = cli.tools_list()
    tools = ((tl.get("result") or {}).get("tools") or []) if isinstance(tl.get("result"), dict) else []
    rep["tools"] = [{"name": t.get("name"), "description": (t.get("description") or "")[:90],
                      "input_keys": sorted(((t.get("inputSchema") or {}).get("properties") or {}).keys())}
                     for t in tools]
    rep["steps"]["tools_list"] = {"ok": tl.get("ok"), "http": tl.get("http"), "count": len(tools),
                                   "jsonrpc_error": tl.get("jsonrpc_error")}

    rl = cli.resources_list()
    res_items = ((rl.get("result") or {}).get("resources") or []) if isinstance(rl.get("result"), dict) else []
    rep["resources"] = [{"uri": x.get("uri"), "name": x.get("name")} for x in res_items]
    rep["steps"]["resources_list"] = {"ok": rl.get("ok"), "count": len(res_items)}

    # resource: quote://codes
    qc = cli.resources_read("quote://codes")
    rep["quote_codes"] = sc({"result": qc.get("result")}) if qc.get("result") else None
    rep["steps"]["resources_read_quote_codes"] = {"ok": qc.get("ok"), "http": qc.get("http")}

    # tools/call probes
    probes = [("get_quote", {"code": "XAUUSD"}), ("get_kline", {"code": "XAUUSD", "count": 5}),
               ("list_flash", {}), ("list_calendar", {})]
    rep["calls"] = {}
    for name, args in probes:
        r = cli.tools_call(name, args)
        payload = sc({"result": r.get("result")}) if r.get("result") else None
        rec = {"ok": r.get("ok"), "http": r.get("http"), "jsonrpc_error": r.get("jsonrpc_error"),
                "isError": ((r.get("result") or {}) or {}).get("isError") if isinstance(r.get("result"), dict) else None,
                "structured_top_keys": sorted(payload.keys())[:12] if isinstance(payload, dict) else None}
        if name == "get_quote" and isinstance(payload, dict):
            d = payload.get("data") or payload
            rec["sample_fields"] = sorted(list(d.keys())[:14]) if isinstance(d, dict) else None
        if name == "get_kline" and isinstance(payload, dict):
            d = payload.get("data") or {}
            kl = d.get("klines") if isinstance(d, dict) else None
            rec["kline_rows"] = len(kl) if isinstance(kl, list) else None
            rec["kline_sample"] = (kl or [])[:2]
        if name == "list_flash" and isinstance(payload, dict):
            d = payload.get("data") or {}
            items = d.get("items") if isinstance(d, dict) else None
            rec["items"] = len(items) if isinstance(items, list) else None
            rec["has_more"] = d.get("has_more") if isinstance(d, dict) else None
            rec["next_cursor"] = (str(d.get("next_cursor"))[:24] if isinstance(d, dict) and d.get("next_cursor") else None)
            rec["item_fields"] = sorted(list(items[0].keys())[:14]) if (isinstance(items, list) and items) else None
        if name == "list_calendar" and isinstance(payload, dict):
            d = payload.get("data")
            arr = d if isinstance(d, list) else (d.get("items") if isinstance(d, dict) else None)
            rec["rows"] = len(arr) if isinstance(arr, list) else None
            rec["item_fields"] = sorted(list(arr[0].keys())[:14]) if (isinstance(arr, list) and arr) else None
            rec["sample"] = arr[0] if (isinstance(arr, list) and arr) else None
        rep["calls"][name] = rec
        print(name, json.dumps(rec, ensure_ascii=False, default=str)[:400])

    if isinstance(rep.get("quote_codes"), (dict, list)):
        rep["quote_codes_sample"] = str(rep["quote_codes"])[:300]
    rep["handshake_ok"] = all(rep["steps"].get(k, {}).get("ok") for k in
                               ("initialize", "initialized", "tools_list", "resources_list"))
    json.dump(rep, open(os.path.join(OUT, "mcp_handshake.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False, default=str)
    print(json.dumps({"handshake_ok": rep["handshake_ok"], "server_info": rep["server_info"],
                       "negotiated_protocol": rep["negotiated_protocol"],
                       "tools": [t["name"] for t in rep["tools"]],
                       "resources": [r["uri"] for r in rep["resources"]]}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
