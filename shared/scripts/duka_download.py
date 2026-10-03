# -*- coding: utf-8 -*-
"""duka_download.py — Dukascopy 批量下载（并发、可续传）。

1) M1 BID/ASK 蜡烛：2023-01-01 → 今天（每日 2 文件）
2) tick（可选月份）：逐小时文件
输出：data/staging_duka/candles_<YYYYMM>.parquet / ticks_<YYYYMM>.parquet（原始 int，未缩放）
用法: python duka_download.py --start 2023-01 --ticks 2026-08,2024-01
"""
import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/AIQuant/scripts")
import pandas as pd
from dukascopy import (OUT, candle_day_url, decode_candles, decode_ticks,
                       fetch_bytes, tick_hour_url)

SCALE = 1000.0  # XAUUSD ×1000（价格 = int/1000）


def day_range(start_ym: str):
    y, m = int(start_ym[:4]), int(start_ym[5:7])
    cur = datetime(y, m, 1)
    today = datetime.now()
    days = []
    while cur <= today:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def dl_candles(day: datetime, sides=("BID", "ASK")) -> pd.DataFrame | None:
    out = None
    for side in sides:
        raw = fetch_bytes(candle_day_url(day, side), retries=3, timeout=25)
        if raw is None or len(raw) < 40:
            return None
        rows = decode_candles(raw)
        df = pd.DataFrame(rows, columns=["sec", "open", "close", "low", "high", "vol"])
        df["side"] = side
        df["day"] = day.strftime("%Y-%m-%d")
        out = df if out is None else pd.concat([out, df], ignore_index=True)
    return out


def dl_ticks_day(day: datetime) -> pd.DataFrame | None:
    frames = []
    for h in range(24):
        raw = fetch_bytes(tick_hour_url(day, h), retries=2, timeout=20)
        if raw is None or len(raw) < 30:
            continue
        rows = decode_ticks(raw)
        if rows:
            df = pd.DataFrame(rows, columns=["ms", "ask", "bid", "ask_vol", "bid_vol"])
            df["hour"] = h
            frames.append(df)
        time.sleep(0.05)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01")
    ap.add_argument("--ticks", default="", help="逗号分隔的 YYYY-MM 月份做 tick 下载")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--candles", action="store_true", default=True)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if args.candles:
        days = day_range(args.start)
        todo = []
        for d in days:
            p = OUT / f"candles_{d.strftime('%Y%m')}.parquet"
            if not p.exists():
                todo.append(d)
        print(f"[candles] {len(todo)} 天待下载（已存在跳过）", flush=True)
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(dl_candles, d): d for d in todo}
            for fut in as_completed(futs):
                d = futs[fut]
                try:
                    df = fut.result()
                except Exception as e:
                    df = None
                    print(f"  ERR {d.date()}: {e}", flush=True)
                if df is not None:
                    ym = d.strftime("%Y%m")
                    p = OUT / f"candles_{ym}.parquet"
                    old = pd.read_parquet(p) if p.exists() else None
                    df2 = pd.concat([old, df], ignore_index=True) if old is not None else df
                    p = OUT / f"candles_{ym}.parquet"
                    df2.to_parquet(p, index=False)
                    done += 1
        print(f"[candles] 完成 {done}/{len(todo)}", flush=True)

    if args.ticks:
        for ym in args.ticks.split(","):
            ym = ym.strip()
            y, m = int(ym[:4]), int(ym[5:7])
            cur = datetime(y, m, 1)
            nxt = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
            todo = []
            while cur < nxt and cur <= datetime.now():
                p = OUT / f"ticks_{cur.strftime('%Y%m%d')}.parquet"
                if not p.exists():
                    todo.append(cur)
                cur += timedelta(days=1)
            print(f"[ticks {ym}] {len(todo)} 天待下载", flush=True)
            ok = 0
            with ThreadPoolExecutor(max_workers=6) as ex:
                futs = {ex.submit(dl_ticks_day, d): d for d in todo}
                for fut in as_completed(futs):
                    d = futs[fut]
                    df = fut.result()
                    if df is not None and len(df):
                        df.to_parquet(OUT / f"ticks_{d.strftime('%Y%m%d')}.parquet", index=False)
                        ok += 1
            print(f"[ticks {ym}] 完成 {ok}/{len(todo)}", flush=True)
    print("download done", flush=True)


if __name__ == "__main__":
    main()
