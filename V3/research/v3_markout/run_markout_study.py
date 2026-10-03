"""V3 markout / adverse-selection / cost-to-move study (task VI/VII/VIII/XIV).

READ-ONLY on market data. Places NO orders. Writes only under
research/v3_markout/ (results.json, markout_report.md).

Pre-registration: the ONLY entry rules used here are the two declared
diagnostic references (momentum sign, reversal sign of r1_bp). They exist to
classify failure modes, not to search for alpha. No threshold is tuned here.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import datetime as dt

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, V3)

from microstructure import spread as SP            # noqa: E402
from microstructure import markout as MK            # noqa: E402
from microstructure import adverse_selection as AS  # noqa: E402
from microstructure import volatility_state as VS   # noqa: E402
from microstructure import ofi as OFI              # noqa: E402
from microstructure import tick_flow as TF          # noqa: E402
from microstructure import arrival_rate as AR       # noqa: E402
from microstructure import microprice as MP         # noqa: E402
from microstructure import fill_probability as FP   # noqa: E402
from microstructure import data_state as DS         # noqa: E402
from execution import cost_model_v2 as CM2          # noqa: E402
from execution import execution_quality as EQ       # noqa: E402

COST_BP = 0.914
HORIZONS_COST_MOVE = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000, 60000, 300000]


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_ticks():
    fs = sorted(glob.glob(r"C:\AIQuant\data\staging_fxtm\ticks_*.parquet")) + \
         sorted(glob.glob(r"C:\AIQuant\data\live_fxtm\ticks_*.parquet"))
    frames = []
    for f in fs:
        d = pd.read_parquet(f, columns=["bid", "ask", "ts_utc"]).sort_values("ts_utc")
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    ts = d["ts_utc"].astype("int64").to_numpy()      # ms since epoch
    return ts, d["bid"].to_numpy(float), d["ask"].to_numpy(float), len(fs)


def grid_idx(ts, step_ms=1000):
    grid = np.arange(ts[0], ts[-1] + 1, step_ms, dtype=np.int64)
    idx = np.searchsorted(ts, grid, side="right") - 1
    idx = idx[idx >= 0]
    return idx


def fwd_move_bp(ts, mid, idx, h_ms):
    # ts is in MILLISECONDS since epoch (native feed resolution)
    t0 = ts[idx]
    j = np.searchsorted(ts, t0 + int(h_ms), side="left")
    ok = j < len(ts)
    jj = np.clip(j, 0, len(ts) - 1)
    out = np.full(len(idx), np.nan)
    good = ok & (mid[idx] > 0)
    out[good] = (mid[jj[good]] / mid[idx][good] - 1.0) * 1e4
    return out


def main():
    out = {"schema": "v3_markout_study/1", "generated_utc": now_utc(),
           "task": "V3-HFT-GITHUB-DISTILLATION-002", "mode": "AUDIT_ONLY / READ_ONLY",
           "cost_bp": COST_BP}
    ts, bid, ask, nfiles = load_ticks()
    mid = (bid + ask) / 2.0
    out["data"] = {"files": nfiles, "ticks": int(len(ts)),
                   "ts_min_utc": str(pd.to_datetime(ts[0], unit="ms", utc=True)),
                   "ts_max_utc": str(pd.to_datetime(ts[-1], unit="ms", utc=True))}

    # ---- L1 availability + spread
    out["spread"] = SP.spread_stats(bid, ask)
    out["data_state"] = DS.registry()
    out["microprice_status"] = MP.microprice_status(volume_nonzero_frac=0, last_nonzero_frac=0)
    out["true_ofi_status"] = OFI.true_ofi(bid, ask, None, None)[1]
    out["fill_probability"] = FP.availability()

    # ---- analysis sample: 1 s as-of grid, freshness <= 5 s
    idx = grid_idx(ts, 1000)
    fresh = (ts[idx] - (ts[idx] // 1000 * 1000)) <= 5000
    idx = idx[fresh]
    out["sample"] = {"grid_points": int(len(idx))}

    # ---- cost-to-move ratio (task VIII/XIV)
    c2m = {}
    for h in HORIZONS_COST_MOVE:
        mv = fwd_move_bp(ts, mid, idx, h)
        a = np.abs(mv[np.isfinite(mv)])
        c2m[f"{h}ms"] = {"n": int(a.size),
                         "median_abs_move_bp": float(np.median(a)) if a.size else None,
                         "p90_abs_move_bp": float(np.percentile(a, 90)) if a.size else None,
                         "cost_to_move_ratio": (round(COST_BP / float(np.median(a)), 3)
                                                if a.size and np.median(a) > 0 else None),
                         "tradable": bool(a.size and np.median(a) > COST_BP)}
    out["cost_to_move"] = c2m

    # ---- markout profile: unconditional (all grid points), both directions
    out["markout_unconditional"] = {
        "long": MK.profile(ts, mid, idx, +1, COST_BP),
        "short": MK.profile(ts, mid, idx, -1, COST_BP),
    }

    # ---- adverse selection by spread / volatility state
    vol_full = VS.rolling_vol_bp(mid, 50)
    vol_lab, vol_q = VS.state_labels(vol_full)      # full length; by_state indexes with idx
    sp_full = SP.spread_bp(bid, ask)
    sp_lab, sp_q = VS.state_labels(sp_full)         # full length
    asm = {}
    for h in AS.HORIZONS_MS:
        asm[f"{h}ms"] = {
            "long_by_vol": AS.by_state(ts, mid, idx, +1, vol_lab, h),
            "long_by_spread": AS.by_state(ts, mid, idx, +1, sp_lab, h),
        }
    out["adverse_selection"] = {"by_state": asm, "vol_q": vol_q, "spread_q": sp_q}

    # ---- pre-declared diagnostic entry rules -> Type 1..7 classification
    r1 = np.full(len(ts), np.nan)
    r1[1:] = (mid[1:] / mid[:-1] - 1.0) * 1e4
    r1g = r1[idx]
    rules = {}
    for name, sgn in (("momentum_sign", +1.0), ("reversal_sign", -1.0)):
        sig = np.sign(r1g)
        sig[~np.isfinite(sig)] = 0.0
        d = sgn * sig
        nz = d != 0
        i2 = idx[nz]
        d2 = d[nz]
        gross = fwd_move_bp(ts, mid, i2, 1000) * d2          # 1 s fixed horizon
        lat = np.zeros(len(i2))                              # measured latency handled separately
        spread_cost = SP.spread_bp(bid, ask)[i2]
        net = gross - COST_BP
        types = [EQ.classify(float(g), float(sc), 0.0, float(l), 0.0, float(nn))
                 for g, sc, l, nn in zip(np.nan_to_num(gross), np.nan_to_num(spread_cost),
                                         lat, np.nan_to_num(net))]
        from collections import Counter
        cnt = Counter(types)
        rules[name] = {"n_entries": int(nz.sum()),
                       "median_gross_bp": float(np.nanmedian(gross)) if nz.sum() else None,
                       "median_net_bp": float(np.nanmedian(net)) if nz.sum() else None,
                       "failure_type_counts": dict(cnt)}
    out["diagnostic_entry_rules"] = rules

    # ---- cost model v2 view
    cm = CM2.CostModelV2(spread_bp=out["spread"].get("median_bp"), commission_bp=0.503,
                         slippage_bp=None, latency_cost_bp=None,
                         adverse_selection_bp=None, market_impact_bp=None)
    out["cost_model_v2"] = cm.total()

    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("wrote results.json")
    print(json.dumps({"ticks": out["data"]["ticks"], "spread_median_bp": out["spread"].get("median_bp"),
                      "cost_to_move_1s": c2m["1000ms"], "1s_tradable": c2m["1000ms"]["tradable"],
                      "tradable_horizons": [k for k, v in c2m.items() if v["tradable"]]}, indent=1))


if __name__ == "__main__":
    main()
