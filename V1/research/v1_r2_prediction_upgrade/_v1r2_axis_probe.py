# -*- coding: utf-8 -*-
"""V1-R2 Phase B-R4 决定性探针：原始证据读取 + 轴偏移扫描 N=-16..+16（只读）。"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
TICKDIR = os.path.join(REPO, "data", "live_fxtm")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
GRID = pd.Timedelta(minutes=15)
OUT = {}


def rd(p, n=400000):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()[:n]
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__


def grep(roots, pats, cap=60, maxsize=400000):
    hits, scanned = [], 0
    rx = re.compile("|".join(pats), re.I)
    for root in roots:
        if not os.path.isdir(root):
            continue
        for r_, ds, fs in os.walk(root):
            if any(x in r_ for x in ("__pycache__", ".git", ".venv", "node_modules")):
                continue
            for f in fs:
                if not f.lower().endswith((".py", ".ps1", ".cmd", ".bat", ".json", ".yaml", ".yml", ".md")):
                    continue
                p = os.path.join(r_, f)
                try:
                    if os.path.getsize(p) > maxsize:
                        continue
                except OSError:
                    continue
                scanned += 1
                txt = rd(p, maxsize)
                if not txt:
                    continue
                for m in rx.finditer(txt):
                    ln = txt[:m.start()].count("\n") + 1
                    line = txt.splitlines()[ln - 1].strip()[:190]
                    hits.append({"file": os.path.relpath(p, REPO).replace("\\", "/"), "line": ln,
                                   "kw": m.group(0), "text": line})
                    if len(hits) >= cap:
                        return {"scanned": scanned, "hits": hits}
    return {"scanned": scanned, "hits": hits}


# ---------- 1. collector source ----------
SC = os.path.join(REPO, "research", "self_collect", "tick_collect_once.ps1")
OUT["collector_ps1"] = {"path": os.path.relpath(SC, REPO).replace("\\", "/"), "exists": os.path.exists(SC),
                          "size": (os.path.getsize(SC) if os.path.exists(SC) else None),
                          "content": (rd(SC, 8000) if os.path.exists(SC) else None)}
# ---------- 2. quote_latest ----------
QL = os.path.join(TICKDIR, "quote_latest.json")
q = {}
if os.path.exists(QL):
    try:
        q = json.load(open(QL, encoding="utf-8-sig"))
    except Exception as e:  # noqa: BLE001
        q = {"ERR": type(e).__name__}
OUT["quote_latest"] = {"path": os.path.relpath(QL, REPO).replace("\\", "/"), "fields": q,
                         "types": {k: type(v).__name__ for k, v in q.items()},
                         "digits": {k: (len(str(v)) if isinstance(v, (int, float)) else None) for k, v in q.items()}}
# ---------- 3. grep evidence ----------
OUT["grep"] = grep([os.path.join(REPO, "research", "self_collect"), TICKDIR,
                      os.path.join(REPO, "research", "hermes", "trader_v1"),
                      os.path.join(REPO, "research", "hermes", "trader_v2", "data_sources"),
                      os.path.join(REPO, "tools")],
                     ["server_ms", "copy_ticks", "time_msc", "utc_ms", "dt_est", "histdata", "quote_latest"])
# ---------- 4. shift scan ----------
frames = []
for p in sorted(glob.glob(os.path.join(TICKDIR, "ticks_*.parquet"))):
    d = pd.read_parquet(p, columns=["utc_ms", "bid", "ask"])
    d = d[(d["utc_ms"].notna()) & (d["bid"] > 0) & (d["ask"] > 0) & (d["bid"] <= d["ask"])]
    d["ts"] = pd.to_datetime(d["utc_ms"], unit="ms", utc=True)
    frames.append(d[["ts", "bid", "ask"]])
tk = pd.concat(frames, ignore_index=True).sort_values("ts")
g = tk.groupby(tk["ts"].dt.floor("15min"))["bid"]
tick = pd.DataFrame({"o": g.first(), "h": g.max(), "l": g.min(), "c": g.last()}).dropna()
m = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
m["dt"] = pd.to_datetime(m["dt_utc"], utc=True)
m = m.set_index("dt").sort_index()
h = pd.DataFrame({"o": m["open"].resample("15min").first(), "h": m["high"].resample("15min").max(),
                    "l": m["low"].resample("15min").min(), "c": m["close"].resample("15min").last()}).dropna()
exp_overlap = len(tick.index.intersection(h.index))
rows = []
for N in range(-16, 17):
    t2 = tick.copy()
    t2.index = t2.index + N * GRID
    j = h.join(t2, how="inner", rsuffix="_t")
    if j.empty:
        rows.append({"N": N, "overlap": 0})
        continue
    err = {}
    for k in ("o", "h", "l", "c"):
        e = (j[k] - j[k + "_t"]).abs().to_numpy()
        err[k] = {"mis_001": float((e > 0.01).mean()), "mis_005": float((e > 0.05).mean()),
                    "mis_010": float((e > 0.10).mean()), "mis_050": float((e > 0.50).mean()),
                    "p50": float(np.percentile(e, 50)), "p95": float(np.percentile(e, 95)),
                    "p99": float(np.percentile(e, 99)), "max": float(e.max())}
    comb = float(np.mean([err[k]["mis_005"] for k in ("o", "h", "l", "c")]))
    rows.append({"N": N, "overlap": int(len(j)), "coverage": round(len(j) / max(1, exp_overlap), 4),
                   "combined_mis_005": round(comb, 6),
                   "mis_005": {k: round(err[k]["mis_005"], 5) for k in ("o", "h", "l", "c")},
                   "p95": {k: round(err[k]["p95"], 4) for k in ("o", "h", "l", "c")}})
ok = [r for r in rows if r.get("overlap", 0) >= 0.9 * exp_overlap]
best = min(ok, key=lambda r: r["combined_mis_005"]) if ok else None
OUT["shift_scan"] = {"expected_overlap": exp_overlap, "tick_bars": int(len(tick)), "hist_bars": int(len(h)),
                        "table": rows, "best_by_combined_mis005": best,
                        "neighbors": ([r for r in rows if best and abs(r["N"] - best["N"]) == 1] if best else [])}
print("== collector ps1 (first 1200 chars) ==")
print((OUT["collector_ps1"]["content"] or "(missing)")[:1200])
print("\n== quote_latest ==")
print(json.dumps({"fields": OUT["quote_latest"]["fields"], "types": OUT["quote_latest"]["types"],
                    "digits": OUT["quote_latest"]["digits"]}, ensure_ascii=False))
print("\n== grep hits (top 25) ==")
for hidx, hh in enumerate(OUT["grep"]["hits"][:25]):
    print(f"  {hh['file']}:{hh['line']} [{hh['kw']}] {hh['text']}")
print("\n== shift scan ==")
print(f"expected_overlap={exp_overlap} tick_bars={len(tick)} hist_bars={len(h)}")
for r in rows:
    if r.get("overlap"):
        print("  N=%+3d ov=%4d cov=%.2f comb=%.5f mis=%s p95=%s" % (r["N"], r["overlap"], r["coverage"],
                                                                     r["combined_mis_005"],
                                                                     json.dumps(r["mis_005"]),
                                                                     json.dumps(r["p95"])))
    else:
        print("  N=%+3d ov=0" % r["N"])
print("\nBEST:", json.dumps(OUT["shift_scan"]["best_by_combined_mis005"], ensure_ascii=False))
with open(os.path.join(UP, "reports", "V1_R2_AXIS_PROBE.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(OUT, fh, indent=1, ensure_ascii=False, default=str)
print("\nwritten:", os.path.join(UP, "reports", "V1_R2_AXIS_PROBE.json"))
