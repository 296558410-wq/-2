# -*- coding: utf-8 -*-
"""dukascopy.py — Dukascopy 历史数据下载/解码（HTTP，XAUUSD）。

格式：datafeed.dukascopy.com/datafeed/XAUUSD/<YYYY>/<MM>/<DD>/<HH>h_ticks.bi5（每小时）
  BID_candles_min_1.bi5 / ASK_candles_min_1.bi5（每日 1-min 蜡烛，bid/ask 分开）
记录为 lzma(bi5)：20B/条 int32 big-endian。
  ticks:    time_ms_in_hour, ask, bid, ask_vol, bid_vol
  candles:  time_unix_s, open, close, low, high（×scale）
XAUUSD scale：1000（3 位小数）——用实际价格校准。
"""
from __future__ import annotations

import lzma
import struct
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "http://datafeed.dukascopy.com/datafeed"
OUT = Path("C:/AIQuant/data/staging_duka")
SYM = "XAUUSD"


def fetch_bytes(url: str, retries: int = 3, timeout: int = 30) -> bytes | None:
    import urllib.error
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (research; python)"})
    for a in range(retries):
        try:
            with urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or e.code == 403:  # 无此文件/拒绝 → 不重试
                return None
            if a == retries - 1:
                return None
            time.sleep(1.0 * (a + 1))
        except Exception:
            if a == retries - 1:
                return None
            time.sleep(1.0 * (a + 1))
    return None


def decode_ticks(raw: bytes) -> list[tuple[int, int, int, int, int]]:
    data = lzma.decompress(raw)
    n = len(data) // 20
    out = []
    for i in range(n):
        (t, ask, bid, avol, bvol) = struct.unpack_from(">iiiii", data, i * 20)
        out.append((t, ask, bid, avol, bvol))
    return out


def decode_candles(raw: bytes) -> list[tuple[int, int, int, int, int, int]]:
    data = lzma.decompress(raw)
    n = len(data) // 24
    out = []
    for i in range(n):
        (t, o, c, lo, hi, v) = struct.unpack_from(">iiiiii", data, i * 24)
        out.append((t, o, c, lo, hi, v))
    return out


def tick_hour_url(d: datetime, hour: int) -> str:
    return f"{BASE}/{SYM}/{d.year:04d}/{d.month:02d}/{d.day:02d}/{hour:02d}h_ticks.bi5"


def candle_day_url(d: datetime, side: str) -> str:
    return f"{BASE}/{SYM}/{d.year:04d}/{d.month:02d}/{d.day:02d}/{side}_candles_min_1.bi5"


def dl_day_candles(day: datetime, out: Path = OUT) -> tuple[int, int] | None:
    """下载某日 bid/ask M1 蜡烛 → parquet；返回 (bid_rows, ask_rows)。"""
    import pandas as pd
    res = {}
    for side in ("BID", "ASK"):
        raw = fetch_bytes(candle_day_url(day, side))
        if raw is None or len(raw) < 30:
            return None
        rows = decode_candles(raw)
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=["ts", "open", "close", "low", "high"])
        res[side] = df
    return len(res["BID"]), len(res["ASK"])
