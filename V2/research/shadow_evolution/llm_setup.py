# -*- coding: utf-8 -*-
"""llm_setup.py — resolve an OpenAI-compatible endpoint+key from OpenClaw config (IN-PROCESS ONLY).
Prints provider metadata (NO key value) and runs ONE connectivity/model verification call.
Never writes the key anywhere; never prints it.
"""
from __future__ import annotations
import json, os, time, urllib.request

CFG = os.path.expanduser("~/.openclaw/openclaw.json")
PREF = os.environ.get("V2_SHADOW_LLM_PROVIDER", "custom-yuanyuaicloud-cn")


def resolve(prefer=PREF):
    d = json.load(open(CFG, encoding="utf-8"))
    prov = ((d.get("models") or {}).get("providers") or {})
    order = [prefer] + [k for k in prov if k != prefer]
    for name in order:
        p = prov.get(name) or {}
        base = p.get("baseUrl"); key = p.get("apiKey")
        if base and key and "127.0.0.1" not in base and "localhost" not in base:
            models = p.get("models") or p.get("modelList") or []
            return {"provider": name, "baseUrl": base, "apiKey": key,
                    "models": models, "key_len": len(str(key))}
    return None


def main():
    r = resolve()
    if not r:
        print("RESOLVE_FAILED: no usable remote provider with key in OpenClaw config"); return
    print("provider:", r["provider"])
    print("baseUrl :", r["baseUrl"])
    print("models  :", json.dumps(r["models"], ensure_ascii=False)[:300])
    print("key_len :", r["key_len"], "(value not printed)")
    # model id to use
    model = os.environ.get("V2_SHADOW_LLM_MODEL") or ("deepseek-v4-flash")
    url = r["baseUrl"].rstrip("/") + "/chat/completions"
    payload = json.dumps({"model": model, "messages": [
        {"role": "system", "content": "Return ONLY JSON."},
        {"role": "user", "content": 'Return exactly this JSON: {"ok": true, "echo": "LLM_OK"}'}],
        "temperature": 0, "max_tokens": 64, "response_format": {"type": "json_object"}}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + str(r["apiKey"])})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ms = round((time.perf_counter() - t0) * 1000)
        content = body.get("choices", [{}])[0].get("message", {}).get("content")
        print("HTTP  :", 200, "| latency_ms:", ms, "| model_echo:", body.get("model"))
        print("content:", str(content)[:200])
        print("VERIFY: OK")
    except Exception as e:
        print("HTTP  :", type(e).__name__, str(e)[:200])
        try:
            print("body  :", e.read().decode("utf-8", "replace")[:300])
        except Exception: pass
        print("VERIFY: FAIL")


if __name__ == "__main__":
    main()
