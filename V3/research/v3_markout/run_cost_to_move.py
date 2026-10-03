"""run_cost_to_move — task XXIX, computed on the IMMUTABLE SNAPSHOT only.

Reads trader_v3/data/snapshots/<SNAPSHOT_ID>/... Never reads the live feed.
Declares timestamp unit explicitly (ms) via timestamp_unit_guard.
Places NO orders. Writes research/v3_markout/{cost_to_move_v2,markout_v2,adverse_selection_v2}.json
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, V3)
from microstructure import timestamp_unit_guard as TG   # noqa: E402
from microstructure import markout as MK                 # noqa: E402
from microstructure import adverse_selection as AS       # noqa: E402
from microstructure import volatility_state as VS        # noqa: E402
from microstructure import data_state as DS              # noqa: E402
from execution import cost_model_v2 as CM2               # noqa: E402
from execution import observability as OBS               # noqa: E402
from execution import execution_quality as EQ            # noqa: E402

SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAPSHOT_ID)
COST_BP = CM2.REAL_RT_COST_BP
HORIZONS = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000, 60000, 300000]
TS_UNIT = "ms"


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_snapshot():
    paths = sorted(glob.glob(os.path.join(SNAP, "staging_fxtm", "ticks_*.parquet"))) + \
            sorted(glob.glob(os.path.join(SNAP, "live_fxtm", "ticks_*.parquet")))
    fr = [pd.read_parquet(p, columns=["bid", "ask", "ts_utc"]).sort_values("ts_utc") for p in paths]
    d = pd.concat(fr, ignore_index=True)
    chk = TG.read_timestamp(d["ts_utc"], TS_UNIT)         # explicit unit; raises if absent
    ts = chk["ts_ns"] // 1_000_000                        # ns -> ms (declared)
    return ts, d["bid"].to_numpy(float), d["ask"].to_numpy(float), len(paths), chk["descriptor"]


def grid_idx(ts, step_ms=1000, fresh_ms=5000):
    g = np.arange(ts[0], ts[-1] + 1, step_ms, dtype=np.int64)
    idx = np.searchsorted(ts, g, side="right") - 1
    idx = idx[idx >= 0]
    return idx[(ts[idx] - (ts[idx] // step_ms * step_ms)) <= fresh_ms]


def fwd(ts, mid, idx, h_ms):
    j = np.searchsorted(ts, ts[idx] + int(h_ms), side="left")
    elig = j < len(ts)
    jj = np.clip(j, 0, len(ts) - 1)
    mv = np.where(elig, (mid[jj] / mid[idx] - 1.0) * 1e4, np.nan)
    return mv, elig


def main():
    ts, bid, ask, nfiles, desc = load_snapshot()
    mid = (bid + ask) / 2.0
    idx = grid_idx(ts)
    med_dt = float(np.median(np.diff(ts)))
    out = {"schema": "v3_cost_to_move_v2/1", "generated_utc": now_utc(),
           "SNAPSHOT_ID": SNAPSHOT_ID, "data": {"files": nfiles, "ticks": int(len(ts)),
           "grid_points": int(len(idx)), "median_inter_tick_ms": med_dt,
           "timestamp": desc, "cost_model": CM2.header()},
           "cost_bp": COST_BP, "horizons": {}}

    for h in HORIZONS:
        mv, elig = fwd(ts, mid, idx, h)
        a = np.abs(mv[np.isfinite(mv)])
        rho = max(1.0, h / med_dt)
        eff_n = int(a.size // rho)
        clean_frac = float(elig.mean())
        med = float(np.median(a)) if a.size else None
        ratio = (COST_BP / med) if (med and med > 0) else None
        if eff_n < 30 or clean_frac < 0.5:
            status = "DATA_INSUFFICIENT"
        elif ratio is not None and ratio >= 1.0:
            status = "RESEARCH_BLOCKED_BY_COST"
        else:
            status = "RESEARCHABLE"
        out["horizons"][f"{h}ms"] = {
            "median_abs_move": med,
            "p75_abs_move": float(np.percentile(a, 75)) if a.size else None,
            "p90_abs_move": float(np.percentile(a, 90)) if a.size else None,
            "cost": COST_BP, "cost_to_move": round(ratio, 4) if ratio else None,
            "effective_n": eff_n, "eligible_n": int(elig.sum()),
            "censored_n": int((~elig).sum()), "clean_frac": clean_frac,
            "status": status}

    # markout profiles (censoring-aware)
    out["markout"] = {"long": MK.profile(ts, mid, bid, ask, idx, +1, COST_BP),
                      "short": MK.profile(ts, mid, bid, ask, idx, -1, COST_BP)}
    # adverse selection, overall + by volatility state
    vol_lab, vol_q = VS.state_labels(VS.rolling_vol_bp(mid, 50))
    asm = {}
    for h in AS.HORIZONS_MS:
        r = AS.adverse_selection(ts, mid, bid, ask, idx, h, +1)
        ok = r["eligibility"] == AS.ELIGIBLE
        asm[f"{h}ms"] = {"long_overall": AS.stats(r["AS_bp"][ok]),
                         "eligible_n": r["eligible_n"], "censored_n": r["censored_n"]}
    out["adverse_selection"] = {"by_horizon": asm, "vol_q": vol_q,
                                "self_test": AS.self_test()}
    out["observability"] = OBS.registry()
    out["failure_taxonomy"] = EQ.taxonomy_status()
    out["data_state"] = DS.registry()

    with open(os.path.join(HERE, "cost_to_move_v2.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    hz = out["horizons"]
    print(json.dumps({k: {"cost_to_move": v["cost_to_move"], "status": v["status"],
                          "eff_n": v["effective_n"]} for k, v in hz.items()}, indent=1))
    print("blocked:", [k for k, v in hz.items() if v["status"] == "RESEARCH_BLOCKED_BY_COST"])
    print("researchable:", [k for k, v in hz.items() if v["status"] == "RESEARCHABLE"])
    print("AS self_test:", out["adverse_selection"]["self_test"]["result"])


if __name__ == "__main__":
    main()
