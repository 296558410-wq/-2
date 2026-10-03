# -*- coding: utf-8 -*-
"""duka_resume.py — 礼貌续传（单线程，2.5s/请求，按日标记断点）。

补齐 candles 缺口：2023-01..2026-08（已存在日期跳过）。
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/AIQuant/scripts")
import pandas as pd
from dukascopy import OUT, candle_day_url, decode_candles, fetch_bytes

MARK = OUT / "duka_done_days.txt"


def load_done() -> set:
    if MARK.exists():
        return set(MARK.read_text().splitlines())
    return set()


def main():
    done = load_done()
    cur = datetime(2023, 1, 1)
    today = datetime.now()
    todo = []
    while cur <= today:
        key = cur.strftime("%Y-%m-%d")
        if key not in done:
            todo.append(cur)
        cur += timedelta(days=1)
    print(f"[resume] {len(todo)} 天待补", flush=True)
    ok = 0
    with open(MARK, "a") as mf:
        for d in todo:
            key = d.strftime("%Y-%m-%d")
            rows = []
            both = True
            for side in ("BID", "ASK"):
                raw = fetch_bytes(candle_day_url(d, side), retries=2, timeout=15)
                if raw is None or len(raw) < 40:
                    both = False
                    break
                df = pd.DataFrame(decode_candles(raw),
                                  columns=["sec", "open", "close", "low", "high", "vol"])
                df["side"] = side
                df["day"] = key
                rows.append(df)
                time.sleep(2.5)
            if both and rows:
                df = pd.concat(rows, ignore_index=True)
                ym = d.strftime("%Y%m")
                p = OUT / f"candles_{ym}.parquet"
                old = pd.read_parquet(p) if p.exists() else None
                df2 = pd.concat([old, df], ignore_index=True) if old is not None else df
                df2.to_parquet(p, index=False)
                ok += 1
            mf.write(key + "\n")
            mf.flush()
            time.sleep(2.0)
    print(f"[resume] done {ok}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
