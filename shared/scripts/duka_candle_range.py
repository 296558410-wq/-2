# -*- coding: utf-8 -*-
"""duka_candle_range.py — scoped DUKA M1 candle downloader for a month range (no tick, no gaps-fill).
Appends per-day BID/ASK candle rows into data/staging_duka/candles_<YYYYMM>.parquet (with day column).
Usage: python duka_candle_range.py --start 2010-01 --end 2022-12 --workers 6
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/AIQuant/scripts")
import pandas as pd  # noqa: E402
from dukascopy import OUT  # noqa: E402
from duka_download import dl_candles  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM")
    ap.add_argument("--end", required=True, help="YYYY-MM")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    y0, m0 = int(a.start[:4]), int(a.start[5:7])
    y1, m1 = int(a.end[:4]), int(a.end[5:7])
    cur = datetime(y0, m0, 1)
    end = datetime(y1, m1, 1)
    # build per-month day lists
    months = {}
    while cur <= end:
        nxt = datetime(cur.year + 1, 1, 1) if cur.month == 12 else datetime(cur.year, cur.month + 1, 1)
        days = []
        d = cur
        while d < nxt and d <= datetime.now():
            days.append(d)
            d += timedelta(days=1)
        months[cur.strftime("%Y%m")] = days
        cur = nxt
    for ym, days in months.items():
        p = OUT / f"candles_{ym}.parquet"
        todo = [d for d in days if not _month_has_day(p, d)]
        if not todo:
            print(f"[candles {ym}] complete, skip", flush=True)
            continue
        print(f"[candles {ym}] {len(todo)} days to download", flush=True)
        ok = 0
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(dl_candles, d): d for d in todo}
            for fut in as_completed(futs):
                d = futs[fut]
                try:
                    df = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  ERR {d.date()}: {e}", flush=True)
                    continue
                if df is not None:
                    old = pd.read_parquet(p) if p.exists() else None
                    df2 = pd.concat([old, df], ignore_index=True) if old is not None else df
                    df2.to_parquet(p, index=False)
                    ok += 1
        print(f"[candles {ym}] done {ok}/{len(todo)}", flush=True)
    print("RANGE_CANDLES_DONE", flush=True)


def _month_has_day(p: Path, d: datetime) -> bool:
    if not p.exists():
        return False
    # cheap check: read day column; month files are small (~1-2MB)
    try:
        df = pd.read_parquet(p, columns=["day"])
        return (df["day"] == d.strftime("%Y-%m-%d")).any()
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    main()
