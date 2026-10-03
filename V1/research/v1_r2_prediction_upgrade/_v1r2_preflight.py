# -*- coding: utf-8 -*-
"""V1-R2 Phase B preflight: verify actual schemas/time semantics of the three candidate datasets (read-only)."""
from __future__ import annotations

import collections
import glob
import json
import os

import pandas as pd


def blk(name, fn, out):
    try:
        out[name] = fn()
    except Exception as e:  # noqa: BLE001
        out[name] = "ERR:" + type(e).__name__ + ":" + str(e)[:140]


def ticks():
    p = r"C:\AIQuant\data\live_fxtm\ticks_20260925.parquet"
    t = pd.read_parquet(p)
    fl = t["flags"].astype("int64")
    return {"cols": list(t.columns), "rows": int(len(t)),
            "head2": t.head(2).to_dict("records"),
            "utc_ms_min": int(t["utc_ms"].min()), "utc_ms_max": int(t["utc_ms"].max()),
            "flags_top": collections.Counter(fl.tolist()).most_common(8),
            "buy_flag_32": int((fl & 32).gt(0).sum()), "sell_flag_64": int((fl & 64).gt(0).sum()),
            "volume_desc": {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in t["volume"].describe().to_dict().items()},
            "volume_real_desc": {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in t["volume_real"].describe().to_dict().items()},
            "spread_desc": {k: round(float(v), 4) for k, v in (t["ask"] - t["bid"]).describe().to_dict().items()}}


def duka():
    p = r"C:\AIQuant\data\staging_duka\candles_201001.parquet"
    d = pd.read_parquet(p)
    return {"cols": list(d.columns), "rows": int(len(d)),
            "head3": d.head(3).to_dict("records"), "tail2": d.tail(2).to_dict("records"),
            "day_min": str(d["day"].min()), "day_max": str(d["day"].max()),
            "sec_min": int(d["sec"].min()), "sec_max": int(d["sec"].max()),
            "rows_per_day": int(len(d) / max(1, d["day"].nunique())),
            "side_uniq": [str(x) for x in list(pd.unique(d["side"]))[:8]],
            "vol_desc": {k: round(float(v), 3) for k, v in d["vol"].describe().to_dict().items()}}


def duka_files():
    fs = sorted(glob.glob(r"C:\AIQuant\data\staging_duka\candles_*.parquet"))
    return {"n": len(fs), "first": os.path.basename(fs[0]) if fs else None,
            "last": os.path.basename(fs[-1]) if fs else None}


def m1():
    p = r"C:\AIQuant\research\v3_alpha_discovery_r1\xauusd_m1_histdata.parquet"
    m = pd.read_parquet(p)
    r = {"cols": list(m.columns), "rows": int(len(m)),
           "head2": m.head(2).to_dict("records"), "tail2": m.tail(2).to_dict("records")}
    try:
        r["idx_min"] = str(m.index.min())
        r["idx_max"] = str(m.index.max())
        r["idx_name"] = str(m.index.name)
        r["idx_type"] = type(m.index).__name__
    except Exception:  # noqa: BLE001
        pass
    return r


def main():
    out = {}
    blk("ticks", ticks, out)
    blk("duka_201001", duka, out)
    blk("duka_files", duka_files, out)
    blk("m1_hist", m1, out)
    rep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifests", "V1_R2_DATASET_FACTS.json")
    with open(rep, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out, ensure_ascii=False, default=str)[:4200], flush=True)
    print("FACTS_FILE:", rep, flush=True)


if __name__ == "__main__":
    main()
