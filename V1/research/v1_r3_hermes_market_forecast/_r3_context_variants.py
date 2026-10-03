# -*- coding: utf-8 -*-
"""V1-R3 — CONTEXT VARIANTS for the §61 Hermes ablation (HERMES_FULL vs HERMES_PRICE_ONLY).

Derives a price-only view (L1 RAW/DERIVED geometry only) from each frozen PIT context.
No new information is added; layers are only REMOVED. Writes under R3 only."""
from __future__ import annotations

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r3_hermes_market_forecast"
SRC = os.path.join(ROOT, "context", "samples")
DST = os.path.join(ROOT, "context", "samples_price_only")
KEEP = ["context_version", "as_of_utc", "symbol", "L1_PRICE_KLINE", "data_quality_legend"]


def main():
    os.makedirs(DST, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if not f.startswith("CTX_") or not f.endswith(".json"):
            continue
        c = json.load(open(os.path.join(SRC, f), encoding="utf-8"))
        v = {k: c[k] for k in KEEP if k in c}
        v["variant"] = "HERMES_PRICE_ONLY"
        v["variant_note"] = "ONLY Layer 1 price/K-line geometry is provided; no structure, behaviour, mechanism, state history, MTF or cross-market"
        # keep only the current bar + short sequence per timeframe to make it strictly geometry
        v["L1_PRICE_KLINE"] = {tf: {"timeframe": tf, "available": d.get("available"),
                                      "current": d.get("current"),
                                      "sequence_last_N": (d.get("sequence_last_N") or [])[-6:] if d.get("available") else None}
                                for tf, d in c["L1_PRICE_KLINE"].items()}
        out = f.replace("CTX_", "CTX_PO_")
        with open(os.path.join(DST, out), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(v, fh, indent=1, ensure_ascii=False)
        n += 1
    print("price-only variants written:", n, "->", DST)


if __name__ == "__main__":
    main()
