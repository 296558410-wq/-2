# -*- coding: utf-8 -*-
"""dashboard/pickup_mascot.py — 自动从桌面接小V的立绘（只复制，绝不删除/移动你的文件）。

规则：
  * 只看 %USERPROFILE%\\Desktop 下最近 30 分钟内的图片（png/jpg/jpeg/webp/gif）
  * 文件名含 小v / mascot / 豆包 / doubao  ->  直接安装
  * 否则只有“仅一张新图”时才安装；多于一张 -> 只报告不安装
  * 安装 = 复制到 v1_upgrade/dashboard/assets/mascot.<ext>，并清掉其它扩展名的旧 mascot
  * 已处理过的文件名记在 assets/.pickup_state.txt，避免重复动作
输出：有动作/有待确认时打印一行中文；无事发生时不打印任何内容（保持静默）。
"""
from __future__ import annotations

import os
import shutil
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HOME = os.path.expanduser("~")
DESK = os.path.join(HOME, "Desktop")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
STATE = os.path.join(ASSETS, ".pickup_state.txt")
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
VEXTS = (".mp4", ".webm")
ALL_EXT = EXTS + VEXTS
SOURCES = [os.path.join(HOME, "Desktop"), os.path.join(HOME, "Downloads")]
KEYWORDS = ("小v", "小V", "mascot", "豆包", "doubao")
WINDOW_SEC = 30 * 60


def load_state():
    if os.path.exists(STATE):
        return set(x.strip() for x in open(STATE, encoding="utf-8") if x.strip())
    return set()


def save_state(s):
    os.makedirs(ASSETS, exist_ok=True)
    open(STATE, "w", encoding="utf-8", newline="\n").write("\n".join(sorted(s)) + "\n")


def write_status(d):
    import json as _j
    from datetime import datetime as _dt, timezone as _tz
    os.makedirs(ASSETS, exist_ok=True)
    d = dict(d)
    d["ts_utc"] = _dt.now(_tz.utc).isoformat()
    open(os.path.join(ASSETS, ".pickup_status.json"), "w", encoding="utf-8", newline="\n").write(_j.dumps(d, ensure_ascii=False, indent=1))


def install(src):
    os.makedirs(ASSETS, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    # 只要一个立绘：清掉其它扩展名的旧 mascot
    for e in ALL_EXT:
        p = os.path.join(ASSETS, "mascot" + e)
        if os.path.exists(p) and e != ext:
            os.remove(p)
    dst = os.path.join(ASSETS, "mascot" + ext)
    shutil.copy2(src, dst)
    return dst


def main():
    now = time.time()
    cand = []
    for d in SOURCES:
        if not os.path.isdir(d):
            continue
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if not os.path.isfile(p) or os.path.splitext(n)[1].lower() not in ALL_EXT:
                continue
            try:
                if now - os.path.getmtime(p) <= WINDOW_SEC:
                    cand.append(p)
            except OSError:
                continue
    seen = load_state()
    new = [p for p in cand if os.path.basename(p) not in seen]
    if not new:
        return
    named = [p for p in new if any(k.lower() in os.path.basename(p).lower() for k in KEYWORDS)]
    if named:
        pick = max(named, key=os.path.getmtime)
        dst = install(pick)
        seen.update(os.path.basename(p) for p in new)
        save_state(seen)
        write_status({"结果": "已换装", "文件": os.path.basename(pick), "方式": "文件名匹配关键词", "目标": os.path.basename(dst)})
        print(f"✅ 小V 已换装：{os.path.basename(pick)} → {os.path.relpath(dst)}")
        return
    if len(new) == 1:
        pick = new[0]
        dst = install(pick)
        seen.add(os.path.basename(pick))
        save_state(seen)
        write_status({"结果": "已换装", "文件": os.path.basename(pick), "方式": "桌面当时只有这一张新图", "目标": os.path.basename(dst)})
        print(f"✅ 小V 已换装：{os.path.basename(pick)} → {os.path.relpath(dst)}（桌面当时只有这一张新图）")
        return
    seen.update(os.path.basename(p) for p in new)
    save_state(seen)
    write_status({"结果": "待确认（多张新图）", "候选": [os.path.basename(p) for p in new]})
    print("⚠️ 桌面出现多张新图，我没敢乱装。请告诉我用哪一张：" + "、".join(os.path.basename(p) for p in new))


if __name__ == "__main__":
    main()
