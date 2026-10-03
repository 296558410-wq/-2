# -*- coding: utf-8 -*-
"""duka_tick_launch.py — DUKA tick-only downloader (no candle branch).

Approved: human adjudication 2026-09-06 (DUKA tick acquisition = data priority #1).
Scope must answer gap->question mapping (see data_registry/DUKA_TICK_ACQUISITION_LOG.md).
Resume-safe: per-day parquet files; existing days skipped.
Usage: python duka_tick_launch.py --months 2026-08,2023-09 --workers 6
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "C:/AIQuant/scripts")
import pandas as pd  # noqa: E402
from dukascopy import OUT  # noqa: E402
from duka_download import dl_ticks_day  # noqa: E402


def run_month(ym: str, workers: int):
    y, m = int(ym[:4]), int(ym[5:7])
    cur = datetime(y, m, 1)
    nxt = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    todo = []
    while cur < nxt and cur <= datetime.now():
        p = OUT / f"ticks_{cur.strftime('%Y%m%d')}.parquet"
        if not p.exists():
            todo.append(cur)
        cur = cur + __import__("datetime").timedelta(days=1)
    print(f"[ticks {ym}] {len(todo)} days to download", flush=True)
    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(dl_ticks_day, d): d for d in todo}
        for fut in as_completed(futs):
            d = futs[fut]
            try:
                df = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  ERR {d.date()}: {e}", flush=True)
                continue
            if df is not None and len(df):
                df.to_parquet(OUT / f"ticks_{d.strftime('%Y%m%d')}.parquet", index=False)
                ok += 1
    print(f"[ticks {ym}] done {ok}/{len(todo)}", flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", required=True, help="comma-separated YYYY-MM tick months, ordered by priority")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    months = [x.strip() for x in args.months.split(",") if x.strip()]
    for ym in months:
        run_month(ym, args.workers)
    print("ALL_TICK_MONTHS_DONE", flush=True)


if __name__ == "__main__":
    main()
