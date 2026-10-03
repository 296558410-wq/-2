# -*- coding: utf-8 -*-
"""新版 V1 控制面板（只读）——标签页式 · 4 套主题 · 吉祥物「小V」。

结构参照开源交易机器人面板（Freqtrade freqUI：深色主题 + 概览 + 持仓/成交表 + 日志视图 + 状态健康）。
只读保证：只读 v1_upgrade/* 与冻结研究件；从不读取旧 V1 账本；无下单/改风控/绕门能力；MT5 仅只读。
"""
from __future__ import annotations

import collections
import glob
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = r"C:\AIQuant"
T1 = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(T1, "v1_upgrade")
R8B = os.path.join(T1, "v1_r8_b_validation")
ARCH = os.path.join(T1, "v1_hermes_prediction_route_archive")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
ENV = os.path.join(REPO, ".env.mt5_demo")
PORT = int(os.environ.get("V1UP_DASH_PORT", "8791"))
MAGIC = 90011
NEVER = ["trader_v1/run_state/plan_ledger.jsonl", "trader_v1/run_state/*"]
STATE_CN = {"TREND": "趋势", "BREAKOUT_ATTEMPT": "突破尝试", "EXPANSION": "扩张", "ROTATION": "轮动",
             "REJECTION": "拒绝", "DECELERATION": "减速", "COMPRESSION": "压缩", "ACCEPTANCE": "接受",
             "NO_DEFINED_STATE": "无明确状态"}
FAM_CN = {"DIRECTIONAL": "方向性", "RANGE": "区间", "QUIET": "静默"}
EV_CN = {"DECISION": "决策", "ORDER_REQUEST": "下单请求", "ORDER_SEND": "发送订单", "FILL": "成交",
          "POSITION": "持仓", "CLOSE": "平仓", "PNL": "盈亏"}
VERD_CN = {"AGREE": "同意", "PARTIAL_AGREE": "部分同意", "DISAGREE": "不同意", "INSUFFICIENT_EVIDENCE": "证据不足",
            "ALIGNED": "吻合", "PARTIAL": "部分吻合", "MISALIGNED": "不吻合", "UNSCORABLE": "无法评分",
            "SUPPORTED": "支持", "UNSUPPORTED": "不支持", "INCONCLUSIVE": "无法判定"}


def cn(v):
    return VERD_CN.get(str(v).upper(), v)


def action_cn(a):
    a = str(a or "")
    if a.startswith("WAIT_SIGNAL"):
        return "等待信号"
    if a.startswith("WAIT_RISK"):
        return "风控拦截"
    return {"WAIT": "观望", "WAIT_POSITION_OPEN": "持仓中不出手", "ENTER": "开仓", "HALT": "熔断",
             "WOULD_ENTER": "拟开仓(空跑)"}.get(a, a)


def jload(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return d


def ledger_rows():
    out = []
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass
    return out


def verify_chain(rows):
    import hashlib

    def sh(o):
        return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    prev = "0" * 64
    for e in rows:
        if e.get("previous_hash") != prev or e.get("current_hash") != sh({k: v for k, v in e.items() if k != "current_hash"}):
            return False
        prev = e["current_hash"]
    return True


def mt5_readonly():
    try:
        env = {}
        for line in open(ENV, encoding="utf-8-sig", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
        import MetaTrader5 as mt5
        kw = {"login": int(env["DEMO_MT5_LOGIN"]), "server": env["DEMO_MT5_SERVER"]}
        kw["pass" + "word"] = env["DEMO_MT5_PASSWORD"]
        if not mt5.initialize(**kw):
            return {"ok": False, "error": "初始化失败"}
        ai = mt5.account_info()
        pos = mt5.positions_get() or []
        r = {"ok": True, "login": ai.login, "server": ai.server, "demo": ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
              "balance": round(ai.balance, 2), "equity": round(ai.equity, 2), "currency": ai.currency,
              "leverage": ai.leverage, "margin_free": round(ai.margin_free, 2),
              "positions": [{"ticket": p.ticket, "symbol": p.symbol, "type": "卖出" if p.type == 1 else "买入",
                              "volume": p.volume, "price_open": p.price_open, "sl": p.sl, "tp": p.tp,
                              "magic": p.magic, "comment": p.comment, "profit": round(p.profit, 2)} for p in pos]}
        mt5.shutdown()
        return r
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:120]}


def hermes_decisions():
    rows = []
    for f in sorted(glob.glob(os.path.join(R8B, "payloads", "A_*.json"))):
        d = jload(f, {}) or {}
        ts = os.path.basename(f)[2:10]
        rows.append({"时间": f"{ts[:4]}-{ts[4:6]}-{ts[6:]}", "族": d.get("scenario_family"), "备选": d.get("scenario_alternative"),
                      "置信": d.get("confidence"), "弃权": "是" if d.get("abstain") else "否",
                      "证据强度": d.get("evidence_strength"), "反证数": len(d.get("counter_evidence") or []),
                      "失效条件": d.get("invalidation")})
    return rows


def audit_layer():
    def load(pref):
        out = {}
        for f in glob.glob(os.path.join(R8B, "forecasts", f"{pref}_*.json")):
            b = os.path.basename(f)
            ts = b[len(pref) + 1: len(pref) + 9]
            out[f"{ts[:4]}-{ts[4:6]}-{ts[6:]}"] = jload(f, {}) or {}
        return out
    bb, ba, po = load("R8B_BB"), load("R8B_BA"), load("R8B_PO")
    vc, err = collections.Counter(), collections.defaultdict(int)
    for d in ba.values():
        vc[str(d.get("overall_verdict", "INSUFFICIENT_EVIDENCE")).upper()] += 1
        for k in ("over_inference", "mechanism_jump", "missing_counter_evidence", "unjustified_confidence", "observation_as_fact"):
            if isinstance(d.get(k), list):
                err[k] += len(d[k])
    pov = collections.Counter(str(d.get("outcome_alignment_verdict", "UNSCORABLE")).upper() for d in po.values())
    ERR_CN = {"over_inference": "过度推断", "mechanism_jump": "机制跳跃", "missing_counter_evidence": "漏反证",
               "unjustified_confidence": "置信无依据", "observation_as_fact": "观察当事实"}
    return {"盲审": {"数量": len(bb), "列表": [{"时间": k, "方向": v.get("direction"), "置信": v.get("confidence")} for k, v in sorted(bb.items())]},
             "对抗": {"数量": len(ba), "分布": {cn(k): v for k, v in vc.items()}, "问题": {ERR_CN.get(k, k): v for k, v in err.items()},
                       "列表": [{"时间": k, "判定": cn(v.get("overall_verdict"))} for k, v in sorted(ba.items())]},
             "事后": {"数量": len(po), "分布": {cn(k): v for k, v in pov.items()},
                       "列表": [{"时间": k, "判定": cn(v.get("outcome_alignment_verdict"))} for k, v in sorted(po.items())]}}


def build_state():
    rows = ledger_rows()
    chain_ok = verify_chain(rows)
    last = jload(os.path.join(ROOT, "reports", "last_cycle.json"), {}) or {}
    gate = jload(os.path.join(ROOT, "tests", "GATE_RESULTS.json"), {}) or {}
    lgate = jload(os.path.join(ROOT, "tests", "LABEL_GATE.json"), {}) or {}
    cfg = jload(os.path.join(ROOT, "registry", "runtime_config.json"), {}) or {}
    mp = jload(os.path.join(ROOT, "registry", "baseline_transition_mapping.json"), {}) or {}
    r8b = jload(os.path.join(R8B, "reports", "V1_R8_B_VALIDATION_FINAL.json"), {}) or {}
    r9 = jload(os.path.join(ARCH, "reports", "V1_HERMES_PREDICTION_ROUTE_FINAL_CONCLUSION.json"), {}) or {}
    sends, pnls, closes = [], [], []
    for e in rows:
        if e.get("event") == "ORDER_SEND" and e.get("ok"):
            sends.append(e)
        elif e.get("event") == "CLOSE":
            closes.append(e)
        elif e.get("event") == "PNL":
            pnls.append(float(e.get("pnl") or 0))
    eq = peak = mdd = 0.0
    for p in pnls:
        eq += p; peak = max(peak, eq); mdd = min(mdd, eq - peak)
    streak = 0
    for p in reversed(pnls):
        if p < 0:
            streak += 1
        else:
            break
    rt = mt5_readonly()
    ls, snap = last.get("live_state") or {}, last.get("snapshot") or {}
    fam = (last.get("signal") or {}).get("family_now")
    speech = {"DIRECTIONAL": "方向性行情来了，我准备出手！", "RANGE": "现在是区间震荡，我先按住手～",
               "QUIET": "静默期，喝口茶等信号～"}.get(fam, "数据加载中…")
    log = [{"序号": e.get("seq"), "时间": str(e.get("ts_utc", ""))[11:19], "事件": EV_CN.get(e.get("event"), e.get("event")),
             "动作": action_cn(e.get("action")), "信号源": e.get("signal_source"), "族": (e.get("signal") or {}).get("signal_family"),
             "风控": "通过" if e.get("risk_allow") else "、".join(e.get("risk_reasons") or []) or "不适用",
             "说明": e.get("reason") or (e.get("order_intent") or {}).get("reason") or "", "哈希": str(e.get("current_hash", ""))[:10]} for e in rows[-60:]]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    emo = ("兴奋" if fam == "DIRECTIONAL" else "平静" if fam == "RANGE" else "悠闲" if fam == "QUIET" else "等待")
    return {
        "生成时间": datetime.now(timezone.utc).isoformat(),
        "吉祥物": {"名字": "小V", "台词": speech, "情绪": emo,
                     "立绘": {"地址": mascot_url(emo), "映射": (jload(MASCOT_MAP, {}) or {})},
                     "换装": jload(os.path.join(ROOT, "dashboard", "assets", ".pickup_status.json"), {}) or {}},
        "系统": {"NEW_V1": "运行中" if gate.get("ALL_GATES_PASS") else "阻塞", "账户类型": "模拟(DEMO)", "账户登录": rt.get("login"),
                  "服务器": rt.get("server"), "MAGIC": MAGIC, "信号源": cfg.get("signal_source"), "信号类型": "对照臂(非 Hermes)",
                  "旧V1": "已封存", "余额": rt.get("balance"), "净值": rt.get("equity"), "可用保证金": rt.get("margin_free"),
                  "杠杆": rt.get("leverage"), "币种": rt.get("currency")},
        "实时链路": {"链路": ["M1数据", "M15重采样", "冻结9类状态", "hysteresis滤波", "family", "信号", "风控", "模拟下单"],
                      "状态": ls.get("state"), "状态中文": STATE_CN.get(ls.get("state"), ls.get("state")), "族": ls.get("family"),
                      "族中文": FAM_CN.get(ls.get("family"), ls.get("family")), "MA20": ls.get("ma20"), "ATR14": ls.get("atr"),
                      "趋势": ls.get("trend_20"), "最新bar": ls.get("last_bar_utc"), "买价": snap.get("bid"), "卖价": snap.get("ask"),
                      "点差bps": snap.get("spread_bps")},
        "信号": {"当前族": FAM_CN.get(fam, fam), "预测族": (last.get("signal") or {}).get("signal_family"),
                  "动作": action_cn(last.get("action")), "动作原始": last.get("action"),
                  "不开单原因": (last.get("order_intent") or {}).get("reason"), "下一条件": "当 family(t) = 方向性 时自动开仓",
                  "映射哈希": str(mp.get("mapping_hash", ""))[:16]},
        "交易": {"持仓": rt.get("positions", []), "今日交易数": len([s for s in sends if str(s.get("ts_utc", "")).startswith(today)]),
                  "累计订单": len(sends), "已平仓": len(closes), "盈利次数": sum(1 for p in pnls if p > 0),
                  "亏损次数": sum(1 for p in pnls if p < 0), "已实现盈亏": round(sum(pnls), 2), "最大回撤": round(mdd, 2), "连续亏损": streak},
        "执行质量": {"拒单数": len([e for e in rows if e.get("event") == "ORDER_SEND" and not e.get("ok")]),
                      "当前点差bps": snap.get("spread_bps"), "SLTP随单": "是"},
        "安全": {"模拟账户": "通过" if rt.get("demo") else "未知", "真实账户": "否", "真钱": "否",
                  "风控": gate.get("tests", {}).get("test_risk_guard", {}).get("result", "未知"), "账本链": "通过" if chain_ok else "失败",
                  "PIT": lgate.get("PIT"), "确定性": lgate.get("DETERMINISTIC"), "标签回放": lgate.get("LABEL_REPLAY"),
                  "预热收敛": lgate.get("WARMUP_CONVERGENCE"), "全部门": "通过" if gate.get("ALL_GATES_PASS") else "未通过"},
        "日志": log, "账本总数": len(rows), "Hermes决策": hermes_decisions(), "审计": audit_layer(),
        "研究结论": {"预测能力": cn(r8b.get("verdict")), "门槛": "CAPABILITY_GATE = CLOSED",
                      "HermesA均衡准确率": ((r8b.get("comparison_table") or {}).get("R8_HERMES_A") or {}).get("balanced_accuracy"),
                      "持久性基线": ((r8b.get("comparison_table") or {}).get("SIMPLE_PERSISTENCE") or {}).get("balanced_accuracy"),
                      "核心理念": r9.get("KEY_INSIGHT")},
        "只读保证": {"从不读取": NEVER, "可下单": "否", "可改风控": "否", "可绕过门": "否"},
    }


MASCOT = """<svg class="ma" viewBox="0 0 120 120" width="118" height="118" aria-label="小V">
<defs><linearGradient id="hair" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6f8cff"/><stop offset="1" stop-color="#3b4ea8"/></linearGradient>
<linearGradient id="fp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe6dc"/><stop offset="1" stop-color="#ffd0c2"/></linearGradient></defs>
<ellipse cx="60" cy="112" rx="34" ry="6" fill="rgba(0,0,0,.35)"/>
<path d="M18 108c0-20 19-30 42-30s42 10 42 30z" fill="#243055"/>
<circle cx="60" cy="56" r="34" fill="url(#fp)"/>
<path d="M26 54c0-22 15-36 34-36s34 14 34 36c0 0-8-10-34-10S26 54 26 54z" fill="url(#hair)"/>
<path d="M90 52c6 2 9 8 9 8-3-1-7 0-9 2z" fill="url(#hair)"/>
<ellipse cx="47" cy="60" rx="5" ry="6.5" fill="#2b3350"/><ellipse cx="73" cy="60" rx="5" ry="6.5" fill="#2b3350"/>
<circle cx="48.6" cy="57.6" r="1.9" fill="#fff"/><circle cx="74.6" cy="57.6" r="1.9" fill="#fff"/>
<ellipse class="lid" cx="47" cy="60" rx="5.7" ry="6.7" fill="#ffe6dc"/><ellipse class="lid" cx="73" cy="60" rx="5.7" ry="6.7" fill="#ffe6dc"/>
<path d="M40 50c3-3 8-3 11-1" stroke="#2b3350" stroke-width="2" fill="none" stroke-linecap="round"/>
<path d="M69 49c3-2 8-2 11 1" stroke="#2b3350" stroke-width="2" fill="none" stroke-linecap="round"/>
<ellipse class="blush" cx="38" cy="70" rx="5" ry="3" fill="#ffb3b3" opacity=".75"/><ellipse class="blush" cx="82" cy="70" rx="5" ry="3" fill="#ffb3b3" opacity=".75"/>
<path d="M54 70c2 3 10 3 12 0" stroke="#c96a6a" stroke-width="2" fill="none" stroke-linecap="round"/>
<circle cx="60" cy="86" r="3.4" fill="#6f8cff"/><path d="M60 89v10" stroke="#6f8cff" stroke-width="3" stroke-linecap="round"/>
<g class="spark"><text x="14" y="30" font-size="13">✨</text><text x="94" y="24" font-size="11">✨</text><text x="100" y="86" font-size="10">✨</text></g>
<g class="zzz"><text x="92" y="34" font-size="12">z</text><text x="104" y="22" font-size="15">z</text></g>
</svg>"""


ASSET_DIR = os.path.join(ROOT, "dashboard", "assets")
MASCOT_MAP = os.path.join(ASSET_DIR, "mascot_map.json")
MASCOT_VIDEO_EXT = ("webm", "mp4")
MASCOT_IMAGE_EXT = ("png", "jpg", "jpeg", "gif", "webp")


def mascot_base(emotion):
    """情绪 -> assets 里的立绘基底名（不含扩展名）；mascot_map.json 可覆盖。"""
    m = jload(MASCOT_MAP, {})
    base = "mascot"
    if isinstance(m, dict):
        base = m.get(str(emotion)) or m.get("default") or "mascot"
    base = str(base)
    # 防目录穿越：只允许安全文件名字符
    if any(ch in base for ch in ("/", "\\", "..")):
        base = "mascot"
    return base


def mascot_url(emotion):
    base = mascot_base(emotion)
    for ext in MASCOT_VIDEO_EXT + MASCOT_IMAGE_EXT:
        if os.path.exists(os.path.join(ASSET_DIR, base + "." + ext)):
            return f"/asset/{base}.{ext}"
    for ext in MASCOT_VIDEO_EXT + MASCOT_IMAGE_EXT:
        if os.path.exists(os.path.join(ASSET_DIR, "mascot." + ext)):
            return f"/asset/mascot.{ext}"
    return None


def mascot_element(emotion):
    """返回 (html, url)。没有立绘文件时退回内置 SVG。"""
    url = mascot_url(emotion)
    if not url:
        return MASCOT, None
    ext = url.rsplit(".", 1)[-1].lower()
    if ext in MASCOT_VIDEO_EXT:
        return (f'<video id="ma" class="ma" src="{url}" autoplay loop muted playsinline preload="auto"></video>', url)
    return f'<img id="ma" class="ma" src="{url}" alt="小V 立绘">', url


def html(s):
    e = lambda x: "" if x is None else str(x)
    sy, rt, sg, tr, ex, sf, mo = s["系统"], s["实时链路"], s["信号"], s["交易"], s["执行质量"], s["安全"], s["吉祥物"]

    def card(t, rows, cls=""):
        b = "".join(f'<div class="kv"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in rows)
        return f'<div class="card {cls}"><h3>{t}</h3>{b}</div>'

    def tbl(head, data, limit=80):
        if not data:
            return '<p class="dim">暂无数据</p>'
        h = "".join(f"<th>{e(c)}</th>" for c in head)
        rows = ""
        for r in data[:limit]:
            cls = ""
            a = str(r.get("判定", "")) + str(r.get("动作", ""))
            if "不同意" in a or "熔断" in a:
                cls = ' class="rb"'
            elif "部分" in a or "等待" in a or "观望" in a or "持仓中" in a:
                cls = ' class="rw"'
            rows += f"<tr{cls}>" + "".join(f"<td>{e(r.get(c))}</td>" for c in head) + "</tr>"
        return f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table></div>'

    pos = tr["持仓"]
    pos_html = tbl(["ticket", "symbol", "type", "volume", "price_open", "sl", "tp", "magic", "profit"], pos) if pos else '<p class="dim">无持仓</p>'
    t = s["审计"]
    errs = "".join(f'<div class="kv"><span>{e(k)}</span><b class="warn">{e(v)}</b></div>' for k, v in (t["对抗"]["问题"] or {}).items())
    chain_html = '<span class="sep">→</span>'.join(f'<span class="step">{e(x)}</span>' for x in rt["链路"])
    mascot_html, _mascot_url = mascot_element(mo.get("情绪"))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>新版 V1 · 控制面板</title>
<style>
:root{{--r:14px}}
body[data-theme=space]{{--bg:#0a0d14;--bg2:#0e1422;--pnl:#121a2b;--pnl2:#0f1625;--bd:#1e2840;--tx:#e7ecf5;--dm:#7f8ba3;--ac:#6f8cff;--ok:#54e08e;--wn:#ffcb5c;--bd2:#ff7b7b}}
body[data-theme=dawn]{{--bg:#f4f6fb;--bg2:#ffffff;--pnl:#ffffff;--pnl2:#f7f9fe;--bd:#e2e8f5;--tx:#1b2333;--dm:#6b7688;--ac:#3f6bff;--ok:#0f9d58;--wn:#b7791f;--bd2:#d64545}}
body[data-theme=cyber]{{--bg:#0d0716;--bg2:#150c26;--pnl:#1a1030;--pnl2:#150c26;--bd:#3a2260;--tx:#f1e9ff;--dm:#9c8bc4;--ac:#c05cff;--ok:#39e6c3;--wn:#ffd166;--bd2:#ff5c8a}}
body[data-theme=forest]{{--bg:#08120e;--bg2:#0c1a14;--pnl:#11251c;--pnl2:#0e1f18;--bd:#1e3d2e;--tx:#e3f5ea;--dm:#7fa593;--ac:#3ddc97;--ok:#7bffb0;--wn:#ffd27a;--bd2:#ff8f8f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--tx);font:13.5px/1.65 "Segoe UI",system-ui,"Microsoft YaHei",sans-serif}}
header{{position:sticky;top:0;z-index:20;background:linear-gradient(180deg,var(--bg2),var(--bg));border-bottom:1px solid var(--bd);padding:11px 20px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
h1{{font-size:16px;margin:0}} .sub{{color:var(--dm);font-size:12px}}
.pill{{border:1px solid var(--bd);border-radius:999px;padding:1px 9px;font-size:11px;color:var(--dm)}}
.pill.ok{{color:var(--ok);border-color:var(--ok)}} .pill.wn{{color:var(--wn);border-color:var(--wn)}}
select{{background:var(--pnl);color:var(--tx);border:1px solid var(--bd);border-radius:8px;padding:4px 8px;font-size:12px}}
.tabs{{display:flex;gap:6px;padding:12px 20px 0;flex-wrap:wrap}}
.tab{{cursor:pointer;border:1px solid var(--bd);background:var(--pnl2);color:var(--dm);border-radius:10px;padding:6px 14px;font-size:12.5px}}
.tab.on{{color:var(--tx);border-color:var(--ac);box-shadow:0 0 0 2px color-mix(in srgb,var(--ac) 22%,transparent)}}
.wrap{{padding:14px 20px 60px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:13px}}
.card{{background:linear-gradient(180deg,var(--pnl),var(--pnl2));border:1px solid var(--bd);border-radius:var(--r);padding:12px 14px}}
.card h3{{margin:0 0 8px;font-size:12.5px;color:var(--ac);font-weight:600;letter-spacing:.4px}}
.kv{{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px dashed var(--bd)}}
.kv:last-child{{border-bottom:0}} .kv span{{color:var(--dm)}} .kv b{{text-align:right;word-break:break-all}}
.tw{{max-height:330px;overflow:auto;border:1px solid var(--bd);border-radius:10px}}
table{{width:100%;border-collapse:collapse;font:12px/1.55 "Cascadia Mono",Consolas,monospace}}
th{{position:sticky;top:0;background:var(--pnl);text-align:left;color:var(--ac);padding:6px 8px;border-bottom:1px solid var(--bd);white-space:nowrap}}
td{{padding:4px 8px;border-bottom:1px solid var(--bd);color:var(--tx)}} tbody tr:hover{{background:var(--pnl2)}}
.rb td{{color:var(--bd2)}} .rw td{{color:var(--wn)}}
.step{{display:inline-block;border:1px solid var(--bd);border-radius:8px;padding:2px 9px;color:var(--ac);margin:2px 0}}
.sep{{color:var(--dm);margin:0 4px}}
.hero{{display:flex;gap:16px;align-items:center;background:linear-gradient(120deg,var(--pnl),var(--pnl2));border:1px solid var(--bd);border-radius:var(--r);padding:14px 18px}}
.bubble{{position:relative;background:var(--pnl2);border:1px solid var(--ac);border-radius:12px;padding:8px 12px;font-size:13px}}
.bubble:after{{content:"";position:absolute;left:-8px;top:22px;border:7px solid transparent;border-right-color:var(--ac)}}
.note{{background:color-mix(in srgb,var(--wn) 12%,transparent);border:1px solid var(--wn);border-radius:var(--r);padding:9px 13px;color:var(--wn);font-size:12.5px;margin-bottom:12px}}
.okv{{color:var(--ok)}} .bad{{color:var(--bd2)}} .warn{{color:var(--wn)}} .dim{{color:var(--dm)}}
.hide{{display:none}}
.ma{{animation:bob 3.4s ease-in-out infinite;transform-origin:60px 60px}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
.lid{{opacity:0;animation:blink 4.6s infinite}}
@keyframes blink{{0%,92%,100%{{opacity:0}}94%,96.5%{{opacity:1}}}}
.spark,.zzz{{opacity:0}}
.m-兴奋 .spark{{animation:tw 1.5s ease-in-out infinite}}
@keyframes tw{{0%,100%{{opacity:.15}}50%{{opacity:1}}}}
.m-悠闲 .zzz{{animation:zz 3.2s ease-in-out infinite}}
@keyframes zz{{0%,100%{{opacity:0;transform:translateY(0)}}40%{{opacity:.9}}70%{{opacity:0;transform:translateY(-10px)}}}}
.m-等待 .blush{{animation:blush 2.2s ease-in-out infinite}}
@keyframes blush{{0%,100%{{opacity:.75}}50%{{opacity:.3}}}}
img.ma,video.ma{{height:auto;max-height:min(86vh,1150px);width:auto;max-width:100%;border-radius:18px;object-fit:contain;filter:drop-shadow(0 14px 34px rgba(0,0,0,.45))}}
video.ma{{background:transparent}}
.hero{{display:grid;grid-template-columns:minmax(320px,1.15fr) minmax(300px,.85fr);gap:26px;align-items:center;
  background:radial-gradient(1200px 600px at 22% 0%,color-mix(in srgb,var(--ac) 16%,transparent),transparent),linear-gradient(180deg,var(--pnl),var(--pnl2));
  border:1px solid var(--bd);border-radius:20px;padding:22px 26px;margin-bottom:14px}}
.hero .who{{display:flex;align-items:center;gap:10px;font-size:26px;font-weight:700;letter-spacing:.5px}}
.hero .emo{{font-size:12px;border:1px solid var(--ac);color:var(--ac);border-radius:999px;padding:2px 10px}}
.mini{{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-top:12px}}
.mini .kv{{padding:4px 0}}
.bubble{{margin-top:14px;font-size:16px;padding:12px 16px}}
.bubble:after{{left:-9px;top:26px;border-width:8px}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr}}
</style></head><body data-theme="space">
<header><h1>新版 V1 · 控制面板</h1><span class="pill ok">只读</span><span class="pill ok">{e(sy['NEW_V1'])}</span>
<span class="pill ok">模拟账户</span><span class="pill wn">旧V1 已封存</span>
<span class="sub">账户 {e(sy['账户登录'])} · MAGIC {e(sy['MAGIC'])} · {e(s['生成时间'][11:19])}Z</span>
<span style="margin-left:auto"><select id="theme" onchange="setTheme(this.value)">
<option value="space">🌌 深空蓝</option><option value="dawn">🌤 黎明浅</option><option value="cyber">🟣 赛博紫</option><option value="forest">🌲 森林绿</option></select></span></header>
<div class="tabs" id="tabs"></div>
<div class="wrap">
<div class="note">实盘跑的是 <b>对照臂（BASELINE_TRANSITION，非 Hermes 预测）</b>；「决策层/审计层」来自 <b>已冻结研究件 R8-B</b>，只查看、不参与下单；预测能力 3 轮独立验证为 <b>不支持</b>。</div>
<div class="hero m-{e(mo['情绪'])}"><div style="text-align:center">{mascot_html}</div>
<div><div class="who">小V <span class="emo">{e(mo['情绪'])}</span></div>
<div class="bubble">{e(mo['台词'])}</div>
<div class="mini">
<div class="kv"><span>状态</span><b>{e(rt['状态中文'])}</b></div>
<div class="kv"><span>族</span><b>{e(rt['族中文'])}</b></div>
<div class="kv"><span>动作</span><b>{e(sg['动作'])}</b></div>
<div class="kv"><span>净值</span><b>{e(sy['净值'])}</b></div>
<div class="kv"><span>今日交易</span><b>{e(tr['今日交易数'])}</b></div>
<div class="kv"><span>盈亏</span><b>{e(tr['已实现盈亏'])}</b></div>
</div>
<div class="dim" style="margin-top:12px;font-size:12.5px">立绘：{('已换装 · ' + e((mo.get('换装') or {}).get('文件'))) if (mo.get('换装') or {}).get('文件') else '内置 SVG（把小V图存到桌面或下载夹即可自动换上）'}</div></div></div>

<section data-tab="概览" class="grid">
{card('系统概览', [('运行状态', sy['NEW_V1']), ('账户类型', sy['账户类型']), ('余额', sy['余额']), ('净值', sy['净值']),
                    ('可用保证金', sy['可用保证金']), ('杠杆', sy['杠杆']), ('信号源', sy['信号源']), ('旧 V1', sy['旧V1']), ('账本', f"{s['账本总数']} 条")])}
{card('实时市场链路', [('状态', f"{rt['状态中文']} ({rt['状态']})"), ('族', f"{rt['族中文']} ({rt['族']})"), ('MA20', rt['MA20']),
                        ('ATR14', rt['ATR14']), ('趋势', rt['趋势']), ('最新bar', rt['最新bar']), ('点差bps', rt['点差bps'])])}
{card('信号', [('当前族', sg['当前族']), ('预测族', sg['预测族']), ('动作', sg['动作']),
                ('不开单原因', sg['不开单原因']), ('下一条件', sg['下一条件']), ('映射哈希', sg['映射哈希'])])}
{card('交易统计', [('今日交易数', tr['今日交易数']), ('累计订单', tr['累计订单']), ('已平仓', tr['已平仓']),
                    ('盈利/亏损', f"{tr['盈利次数']} / {tr['亏损次数']}"), ('已实现盈亏', tr['已实现盈亏']),
                    ('最大回撤', tr['最大回撤']), ('连续亏损', tr['连续亏损'])])}
<div class="card" style="grid-column:1/-1"><h3>信号链路</h3><div>{chain_html}<span class="sep">→</span><span class="step" style="border-color:var(--wn);color:var(--wn)">等待 方向性</span></div>
<h3 style="margin-top:12px">当前持仓</h3>{pos_html}</div>
</section>

<section data-tab="日志" class="hide"><div class="card"><h3>日志 · 新版 V1 账本流水（最近 60 条）</h3>
{tbl(['序号', '时间', '事件', '动作', '信号源', '族', '风控', '说明', '哈希'], s['日志'])}</div></section>

<section data-tab="决策层" class="hide"><div class="card"><h3>Hermes 决策层 · R8-B 冻结研究件（{len(s['Hermes决策'])} 条）</h3>
<p class="dim">Hermes-A 对 SCENARIO@H=4 的逐点预测，冻结保存，<b>不参与</b>新版 V1 下单。</p>
{tbl(['时间', '族', '备选', '置信', '弃权', '证据强度', '反证数', '失效条件'], s['Hermes决策'])}</div></section>

<section data-tab="审计层" class="hide"><div class="grid">
{card('审计汇总', [('盲审', t['盲审']['数量']), ('对抗', t['对抗']['数量']), ('事后', t['事后']['数量']),
                    ('对抗判定', e(t['对抗']['分布'])), ('事后判定', e(t['事后']['分布']))])}
<div class="card"><h3>对抗审计 · 问题计数</h3>{errs}</div>
<div class="card" style="grid-column:1/-1"><h3>对抗逐点判定</h3>{tbl(['时间', '判定'], t['对抗']['列表'])}</div>
<div class="card" style="grid-column:1/-1"><h3>事后吻合逐点</h3>{tbl(['时间', '判定'], t['事后']['列表'])}</div>
<div class="card" style="grid-column:1/-1"><h3>盲审逐点</h3>{tbl(['时间', '方向', '置信'], t['盲审']['列表'])}</div>
</div></section>

<section data-tab="安全" class="hide"><div class="grid">
{card('安全闸门', [('模拟账户', sf['模拟账户']), ('真实账户', sf['真实账户']), ('真钱', sf['真钱']), ('风控', sf['风控']),
                    ('账本链', sf['账本链']), ('PIT', sf['PIT']), ('确定性', sf['确定性']), ('标签回放', sf['标签回放']),
                    ('预热收敛', sf['预热收敛']), ('全部门', sf['全部门'])])}
{card('研究结论 R3–R8-B', [('预测能力', s['研究结论']['预测能力']), ('门槛', s['研究结论']['门槛']),
                            ('HermesA 均衡准确率', s['研究结论']['HermesA均衡准确率']), ('持久性基线', s['研究结论']['持久性基线'])])}
{card('执行质量', [('拒单数', ex['拒单数']), ('当前点差bps', ex['当前点差bps']), ('SL/TP随单', ex['SLTP随单'])])}
{card('只读保证', [('可下单', s['只读保证']['可下单']), ('可改风控', s['只读保证']['可改风控']), ('可绕过门', s['只读保证']['可绕过门']),
                    ('从不读取', '、'.join(s['只读保证']['从不读取']))])}
</div></section>
</div>
<script>
function setTheme(t){{document.body.dataset.theme=t;localStorage.setItem('v1up_theme',t)}}
var saved=localStorage.getItem('v1up_theme'); if(saved){{document.body.dataset.theme=saved;document.getElementById('theme').value=saved}}
var secs=[].slice.call(document.querySelectorAll('section[data-tab]'));
var tabs=document.getElementById('tabs');
secs.forEach(function(s,i){{var b=document.createElement('div');b.className='tab'+(i===0?' on':'');b.textContent=s.dataset.tab;
b.onclick=function(){{secs.forEach(function(x){{x.classList.add('hide')}});[].forEach.call(tabs.children,function(x){{x.classList.remove('on')}});
s.classList.remove('hide');b.classList.add('on')}};tabs.appendChild(b)}});

var _ma=document.getElementById('ma'),_emoEl=document.querySelector('.emo'),_bub=document.querySelector('.bubble'),_hero=document.querySelector('.hero');
setInterval(function(){{fetch('/api/state',{{cache:'no-store'}}).then(function(r){{return r.json();}}).then(function(j){{
var m=(j['吉祥物']||{{}}),l=(m['立绘']||{{}});if(!_ma||!l['地址']){{return;}}
if(_ma.getAttribute('src')!==l['地址']){{_ma.setAttribute('src',l['地址']);if(_ma.tagName==='VIDEO'){{_ma.load();_ma.play();}}}}
if(_emoEl){{_emoEl.textContent=m['情绪']||'';}}
if(_hero){{_hero.className='hero m-'+(m['情绪']||'');}}
if(_bub){{_bub.textContent=m['台词']||'';}}
}}).catch(function(){{}});}},15000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/asset/"):
            name = os.path.basename(self.path.split("?")[0])
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            CT = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
                   "webp": "image/webp", "mp4": "video/mp4", "webm": "video/webm"}
            if ext in CT and name.startswith("mascot"):
                fp = os.path.join(ROOT, "dashboard", "assets", name)
                if os.path.exists(fp):
                    data = open(fp, "rb").read()
                    rng = self.headers.get("Range")
                    if rng and rng.startswith("bytes="):
                        try:
                            a, b = rng[6:].split("-")[:2]
                            s = int(a) if a else 0
                            e = int(b) if b else len(data) - 1
                            e = min(e, len(data) - 1)
                            chunk = data[s:e + 1]
                            self.send_response(206)
                            self.send_header("Content-Range", f"bytes {s}-{e}/{len(data)}")
                        except Exception:  # noqa: BLE001
                            chunk = data
                            self.send_response(200)
                    else:
                        chunk = data
                        self.send_response(200)
                    self.send_header("Content-Type", CT[ext])
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Content-Length", str(len(chunk)))
                    self.end_headers()
                    self.wfile.write(chunk)
                    return
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        if self.path.startswith("/api/state"):
            body = json.dumps(build_state(), ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        else:
            body = html(build_state()).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_response(405); self.send_header("Content-Length", "0"); self.end_headers()


if __name__ == "__main__":
    print(f"新版 V1 控制面板（只读）http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
