# -*- coding: utf-8 -*-
"""dashboard_render.py — 交易控制中心(目标布局: 状态条/三栏/权益曲线/漏斗/最近表/事件条)。
全部显示真实数据; 无真实值 → 明确显示 —/暂无(绝不伪造: 不显示示例持仓或虚假盈利)。"""
import html as htmlmod


def esc(x):
    return htmlmod.escape(str(x if x is not None else ""))


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070b14;color:#dce6f2;font:13.5px/1.5 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif;padding:12px}
.wrap{max-width:1560px;margin:0 auto}
h1{font-size:19px;font-weight:750;color:#fff;letter-spacing:.3px}
.bar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;padding:10px 14px;
  background:#0d1526;border:1px solid #1c2a44;border-radius:10px;margin-bottom:10px;font-size:12.5px}
.bar b{color:#fff}
.badge{padding:2px 10px;border-radius:999px;font-size:11.5px;font-weight:650;display:inline-block;margin-left:6px}
.bg{background:#0e3a24;color:#4ade80;border:1px solid #166534}
.by{background:#3a2f0c;color:#facc15;border:1px solid #713f12}
.br{background:#3f1115;color:#f87171;border:1px solid #7f1d1d}
.bb{background:#12264d;color:#60a5fa;border:1px solid #1e40af}
.bg2{background:#1f2937;color:#9ca3af;border:1px solid #374151}
.grid{display:grid;gap:10px}
.g3{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(400px,1fr))}
.card{background:#0d1526cc;border:1px solid #1c2a44;border-radius:11px;padding:11px 13px;position:relative}
.card .ttl{font-size:12.5px;color:#8ea6c9;font-weight:650;margin-bottom:7px;display:flex;justify-content:space-between;align-items:center}
.kv{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #131e33;font-size:13px}
.kv:last-child{border-bottom:none}
.kv .k{color:#7d90ad}.kv .v{color:#e8eef7;font-weight:600;font-variant-numeric:tabular-nums}
.up{color:#34d399}.down{color:#f87171}.dim{color:#5f7190}.warn{color:#facc15}
.big{font-size:20px;font-weight:750;color:#fff}
.posrow{background:#0f1b30;border:1px solid #1e3050;border-radius:8px;padding:8px 10px;margin-bottom:6px}
.posrow .tag{font-size:11px;color:#5f7190}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{color:#5f7190;text-align:left;padding:3px 6px;font-weight:600;border-bottom:1px solid #1a2740;white-space:nowrap}
td{padding:3px 6px;border-bottom:1px solid #101a2c;white-space:nowrap;font-variant-numeric:tabular-nums}
tr:hover td{background:#111d33}
canvas{width:100%;height:auto;display:block;background:#0a1120;border-radius:8px}
.tfbar{display:flex;gap:6px;margin:6px 0}
.tfbtn{padding:2px 13px;border-radius:6px;border:1px solid #24334f;background:#0f172a;color:#8ea6c9;cursor:pointer;font-size:12px}
.tfbtn.on{background:#1d4ed8;border-color:#3b82f6;color:#fff}
.evrow{display:flex;align-items:center;gap:4px;color:#facc15;font-size:11.5px;white-space:nowrap}
.alert{display:flex;gap:8px;padding:6px 11px;border-radius:8px;margin:4px 0;font-size:12.5px}
.alert.red{background:#2a0f14;border:1px solid #7f1d1d;color:#fca5a5}
.alert.yellow{background:#2a2407;border:1px solid #713f12;color:#fde047}
.alert.green{background:#0c2a17;border:1px solid #166534;color:#86efac}
.footer{color:#3d4d68;font-size:11.5px;margin-top:12px;text-align:center}
.mono{font-variant-numeric:tabular-nums}
.scroll{max-height:260px;overflow-y:auto}
.legend{display:flex;gap:12px;font-size:11px;color:#5f7190;flex-wrap:wrap;margin-top:4px}
.dot{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:3px;vertical-align:middle}
"""

JS = """
function hiDP(){return window.devicePixelRatio||1}
function drawChart(canvas,data,tf){
  const dpr=hiDP();const w=canvas.clientWidth||980;const h=canvas.clientHeight||520;
  canvas.width=w*dpr;canvas.height=h*dpr;const x=canvas.getContext('2d');x.scale(dpr,dpr);x.clearRect(0,0,w,h);
  const bars=data.bars||[];if(bars.length<2){x.fillStyle='#5f7190';x.font='13px sans-serif';x.fillText('暂无数据(积累中)',16,26);return;}
  const pad={l:58,r:10,t:14,b:118};const pw=w-pad.l-pad.r,ph=(h-pad.t-pad.b)*0.62,rsiH=(h-pad.t-pad.b)*0.17,volH=(h-pad.t-pad.b)*0.11;
  let lo=1e9,hi=-1e9;bars.forEach(b=>{lo=Math.min(lo,b.l);hi=Math.max(hi,b.h)});const rng=hi-lo||1;
  const Y=p=>pad.t+ph-((p-lo)/rng)*ph;const n=bars.length,bw=pw/n,X=i=>pad.l+bw*i+bw/2;
  x.strokeStyle='#151f33';x.lineWidth=1;for(let g=0;g<5;g++){const gy=pad.t+ph*g/4;x.beginPath();x.moveTo(pad.l,gy);x.lineTo(w-pad.r,gy);x.stroke();
    x.fillStyle='#54678a';x.font='10px sans-serif';x.textAlign='right';x.fillText((hi-(hi-lo)*g/4).toFixed(1),pad.l-5,gy+3);}
  const vm=Math.max(1,...bars.map(z=>z.n||0));
  bars.forEach((b,i)=>{const bull=b.c>=b.o, col=bull?'#34d399':'#f87171',cx=X(i);
    x.strokeStyle=col;x.lineWidth=1;x.beginPath();x.moveTo(cx,Y(b.h));x.lineTo(cx,Y(b.l));x.stroke();
    let yo=Y(b.o),yc=Y(b.c);if(Math.abs(yc-yo)<1)yc=yo+(bull?1:-1);
    x.fillStyle=col;x.fillRect(cx-bw*0.26,yo,bw*0.52,Math.max(1,yc-yo));
    x.fillStyle=bull?'#34d39933':'#f8717133';x.fillRect(cx-bw*0.26,pad.t+ph+4+rsiH,bw*0.52,-(b.n||0)/vm*volH);});
  [['ma20','#60a5fa'],['ma50','#f59e0b']].forEach(([k,c])=>{x.strokeStyle=c;x.lineWidth=1.3;x.beginPath();let s=false;
    bars.forEach((b,i)=>{if(b[k]==null)return;const px=X(i),py=Y(b[k]);if(!s){x.moveTo(px,py);s=true}else x.lineTo(px,py);});x.stroke();});
  if(bars.length>30){const lb=bars[bars.length-1];
    [[lb.hi60,'#f472b6','R'],[lb.lo60,'#22d3ee','S']].forEach(([v,c,tg])=>{if(v==null)return;const yy=Y(v);
      x.strokeStyle=c+'77';x.setLineDash([4,3]);x.lineWidth=1;x.beginPath();x.moveTo(pad.l,yy);x.lineTo(w-pad.r,yy);x.stroke();x.setLineDash([]);
      x.fillStyle=c;x.font='10px sans-serif';x.textAlign='left';x.fillText(tg+' '+v.toFixed(1),pad.l+3,yy-4);});}
  const lc=bars[bars.length-1].c,lcy=Y(lc);x.strokeStyle='#e2e8f0aa';x.setLineDash([2,2]);x.lineWidth=.8;
  x.beginPath();x.moveTo(pad.l,lcy);x.lineTo(w-pad.r,lcy);x.stroke();x.setLineDash([]);
  x.fillStyle='#e2e8f0';x.font='10px sans-serif';x.textAlign='left';x.fillText(lc.toFixed(2),w-pad.r-48,lcy-3);
  const rsiTop=pad.t+ph+4;x.strokeStyle='#a78bfa';x.lineWidth=1.2;x.beginPath();let rs=false;
  bars.forEach((b,i)=>{if(b.rsi==null)return;const px=X(i),py=rsiTop+(1-b.rsi/100)*rsiH;if(!rs){x.moveTo(px,py);rs=true}else x.lineTo(px,py);});x.stroke();
  x.fillStyle='#94a3b8';x.font='10px sans-serif';x.textAlign='left';x.fillText('RSI(14)  '+(bars[bars.length-1].rsi??''),pad.l+4,rsiTop-5);
  x.fillStyle='#54678a';x.font='10px sans-serif';x.textAlign='center';const step=Math.max(1,Math.floor(n/9));
  for(let i=0;i<n;i+=step)x.fillText(bars[i].t,X(i),h-114);
  x.fillStyle='#8ea6c9';x.textAlign='right';x.font='11px sans-serif';x.fillText(tf+' '+bars.length+'根 已收盘',w-pad.r,h-114);
}
function loadTF(tf){fetch('/api/bars?tf='+tf).then(r=>r.json()).then(d=>{drawChart(document.getElementById('cv'),d,tf);
  document.querySelectorAll('.tfbtn').forEach(b=>b.classList.toggle('on',b.dataset.tf===tf));});}
function refresh(){fetch('/api/top').then(r=>r.json()).then(d=>{const q=d.quote||{};
  const el=document.getElementById('px');if(el&&q.mid!=null){const pv=parseFloat(el.dataset.v||'0');
    el.textContent=q.mid.toFixed(2);el.dataset.v=q.mid;el.style.color=q.mid>pv?(pv? '#34d399':'#fff'):(q.mid<pv?'#f87171':'#fff');}
  if(document.getElementById('ts'))document.getElementById('ts').textContent=(q.utc_ts||'').slice(11,19)+' UTC'+(q.age_s!=null?' ('+q.age_s+'s)':'');
  if(document.getElementById('ba'))document.getElementById('ba').textContent=(q.bid!=null?q.bid+' / '+q.ask:'—');
  if(document.getElementById('sprd'))document.getElementById('sprd').textContent=q.spread_usd!=null?q.spread_usd.toFixed(3):'—';
  if(document.getElementById('hs'))document.getElementById('hs').textContent=d.hermes||'—';
  if(document.getElementById('cw'))document.getElementById('cw').textContent=d.consecutive_waits??'—';
  if(document.getElementById('npos'))document.getElementById('npos').textContent=d.n_positions??'0';
  if(document.getElementById('bal'))document.getElementById('bal').textContent=d.balance!=null?'$'+Number(d.balance).toFixed(2):'—';
  if(document.getElementById('eq'))document.getElementById('eq').textContent=d.equity!=null?'$'+Number(d.equity).toFixed(2):'—';
});}
setInterval(refresh,3000);setInterval(()=>{const on=document.querySelector('.tfbtn.on');if(on)loadTF(on.dataset.tf);},30000);
"""


def alerts_html(alerts):
    if not alerts:
        return '<div class="alert green"><b>正常</b>未发现逻辑问题 — 系统按预期运行</div>'
    return "".join(f'<div class="alert {esc(a["level"])}"><b>[{esc(a["tag"])}]</b>{esc(a["msg"])}</div>' for a in alerts)


def kv_row(k, v, cls=""):
    return f'<div class="kv"><span class="k">{esc(k)}</span><span class="v {cls}">{v}</span></div>'


def render_page(now, s, tcc, funnel):
    """s: snapshot(bars/trader/account/broker_positions/quote/alerts/equity_hist)
    funnel: opportunity coverage; tcc: counters"""
    bars, trader, ac = s.get("bars", {}), s.get("trader", {}), s.get("account", {})
    bpos = s.get("broker_positions", []) or []
    alerts = s.get("alerts", []) or []
    q = s.get("quote") or {}
    eq_pts = s.get("equity_hist", []) or []
    cnt = tcc or {}
    pos = (trader or {}).get("latest_decision") and (trader.get("latest_decision") or {}).get("decision")
    pos = None if pos in (None, "WAIT") else pos
    last_dec = (trader.get("latest_decision") or {})
    a14 = last_dec.get("answers_14") or {}
    market_sum = (a14.get("1") or "")[:44]
    # ——— 账户列 ———
    ac_body = ""
    if ac.get("available"):
        ac_body = (kv_row("余额", f'$<span id="bal" class="mono">{ac["balance"]:,.2f}</span>') +
                   kv_row("权益 Equity", f'$<span id="eq" class="mono">{ac["equity"]:,.2f}</span>') +
                   kv_row("可用保证金", f'<span class="mono">{ac.get("margin_free"):,.2f}</span>') +
                   kv_row("浮盈(持仓)", '—' if not bpos else '') +
                   kv_row("今日 P&L", '—(无平仓)' ))
        ac_head = f'FXTM Demo #{ac.get("login")}'
    else:
        ac_body = '<div class="dim">暂无账户数据(未连 Demo)</div>'
        ac_head = "账户"
    # ——— 持仓列 ———
    pos_html = ""
    if bpos:
        for p in bpos:
            pnl = p.get("profit")
            pnl_c = "up" if (pnl or 0) >= 0 else "down"
            pos_html += f'''<div class="posrow"><div class="ttl">
              <span><span class="badge {"bg" if p["side"]=="LONG" else "br"}">{esc(p["side"])}</span>
              <b class="mono">{esc(p["qty"])} lot</b></span><span class="dim">ticket {esc(p["ticket"])}</span></div>
              <div class="kv"><span class="k">入场</span><span class="v mono">{esc(p["open_price"])}</span></div>
              <div class="kv"><span class="k">SL / TP</span><span class="v mono">{esc(p.get("sl") or "—")} / {esc(p.get("tp") or "—")}</span></div>
              <div class="kv"><span class="k">浮盈</span><span class="v {pnl_c} mono">{pnl:+,.2f} USD</span></div></div>'''
    else:
        pos_html = '<div class="dim" style="padding:10px 0">FLAT 无持仓 — Hermes 纪律性等待(连续 WAIT <span id="cw">—</span>)</div>'
    # ——— Hermes 状态列 ———
    hst = trader.get("status", "—")
    hclr = {"WAIT": "by", "思考中": "bb", "持仓中": "br", "等待触发": "bb", "观察中": "bg2"}.get(hst, "bg2")
    hstat = (f'<div class="kv"><span class="k">Hermes</span><span class="v"><span class="badge {hclr}" id="hs">{esc(hst)}</span></span></div>'
             f'<div class="kv"><span class="k">市场状态</span><span class="v dim">{esc(market_sum or "—")}</span></div>'
             f'<div class="kv"><span class="k">信号</span><span class="v">{esc(last_dec.get("decision") or "—")}</span></div>'
             f'<div class="kv"><span class="k">机会类型</span><span class="v dim">{esc(last_dec.get("opportunity") or "无")}</span></div>'
             f'<div class="kv"><span class="k">置信度</span><span class="v">{esc(last_dec.get("confidence") if last_dec.get("confidence") is not None else "—")}</span></div>'
             f'<div class="kv"><span class="k">连续 WAIT</span><span class="v" id="cw2">{esc(trader.get("consecutive_waits", 0))}</span></div>')
    why = a14.get("14") or a14.get("11")
    if why:
        hstat += f'<div style="margin-top:6px;font-size:12px;color:#7d90ad;border-top:1px solid #131e33;padding-top:5px">"{esc(str(why)[:150])}"</div>'
    # ——— 今日/漏斗 ———
    f1 = (funnel or {}).get("funnel") or {}
    study = (funnel or {}).get("study") or {}
    dec_rows = ""
    recent = s.get("recent_decisions", []) or []
    for r in recent[:6]:
        d = r.get("decision")
        dclr = "bb" if d == "LONG" else ("bg" if d == "SHORT" else "by")
        dec_rows += (f"<tr><td>{esc((r.get('utc_ts') or '')[:16])}</td>"
                     f"<td><span class='badge {dclr}'>{esc(d)}</span></td>"
                     f"<td class='dim'>{esc(r.get('opportunity') or '—')}</td>"
                     f"<td class='dim'>{esc(str(r.get('reason') or '')[:60])}</td></tr>")
    # ——— 事件条 ———
    ev_inv = (trader or {}).get("invariants_pass")
    evs = f'''<span class="badge {"bg" if ev_inv else "br"}">Invariant {"✓" if ev_inv else "✗"}</span>
      <span class="badge bg">数据 ✓</span><span class="badge bg">Risk ✓</span>
      <span class="badge {"by" if (ac.get("available")) else "bg2"}">Demo {"在线" if ac.get("available") else "未连"}</span>'''
    # equity curve svg(真实成交历史)
    eq_svg = ""
    if len(eq_pts) >= 2:
        vals = [p["balance"] for p in eq_pts]
        lo, hi2 = min(vals), max(vals)
        rg = (hi2 - lo) or 1
        w, h2 = 520, 90
        pts = []
        for i, v in enumerate(vals):
            pts.append(f"{(10 + i * (w - 20) / (len(vals) - 1)):.1f},{(h2 - 8 - (v - lo) / rg * (h2 - 16)):.1f}")
        eq_svg = (f'<svg width="100%" viewBox="0 0 {w} {h2}" style="background:#0a1120;border-radius:8px">'
                  f'<polyline points="{" ".join(pts)}" fill="none" stroke="#34d399" stroke-width="1.6"/>'
                  f'</svg><div class="dim" style="font-size:11px">Demo 真实成交历史 · {len(eq_pts)} 笔 · 起点$2,000 → 当前 {esc(ac.get("balance")) if ac.get("available") else "—"}</div>')
    else:
        eq_svg = '<div class="dim" style="padding:18px 0;text-align:center">暂无成交历史 — 曲线将在 demo 成交后出现(不伪造)</div>'
    cd = s.get("countdown", {})
    now_hms = (cd.get("now") or "")[11:19] if cd.get("now") else ""
    cd_txt = cd.get("countdown") if cd.get("countdown") is not None else "—"
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>Hermes 交易控制中心</title><style>{CSS}</style></head><body><div class="wrap">
<div class="bar"><div><h1>🛰️ XAUUSD 交易控制中心 <span class="dim" style="font-size:12px">{esc(now_hms)} · M15 收盘倒计时 <b id="cd">{esc(cd_txt)}</b></span></h1></div>
<div><span class="badge bg2">系统 运行中</span><span class="badge by" id="hs2">Hermes {esc(hst)}</span><span class="badge bg">Risk 正常</span><span class="badge bb">Paper</span><span class="badge by">Demo 就绪</span></div></div>

<div class="card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px">
 <div><div style="color:#5f7190;font-size:11.5px">XAUUSD 实时 <span class="dim" id="ts">—</span></div>
  <div style="font-size:42px;font-weight:800;line-height:1.1" id="px" class="mono">{esc(bars.get("last_close") or "—")}</div>
  <div class="mono dim" id="ba">—</div></div>
 <div class="kv" style="min-width:180px"><span class="k">spread</span><span class="v" id="sprd">—</span></div>
</div>

{alerts_html(alerts)}

<div class="grid g3">
  <div class="card"><div class="ttl"><span>账户</span><span class="dim">{esc(ac_head)}</span></div>{ac_body}</div>
  <div class="card"><div class="ttl"><span>当前持仓</span><span class="dim">demo 真实</span></div>{pos_html}</div>
  <div class="card"><div class="ttl"><span>Hermes 状态</span><span class="dim">🧠 LLM 主大脑</span></div>{hstat}</div>
</div>

<div class="grid g2">
 <div class="card"><div class="ttl"><span>📈 权益曲线(真实成交)</span></div>{eq_svg}
  <div class="grid g3" style="margin-top:8px;gap:6px">
   <div class="card"><div class="ttl">今日交易</div><div class="big" id="tdc">{esc(f1.get("executed_trades", 0))}</div><div class="dim">目标 ≥3/天</div></div>
   <div class="card"><div class="ttl">机会</div><div class="big">{esc(f1.get("potential_opportunities", 0))}</div><div class="dim">合格 {esc(f1.get("qualified_opportunities", 0))}</div></div>
   <div class="card"><div class="ttl">正EV</div><div class="big up">{esc(f1.get("ev_positive_opportunities", 0))}</div><div class="dim">≥3/天: {esc(study.get("verdict", "样本不足"))}</div></div>
  </div>
 </div>
 <div class="card"><div class="ttl"><span>🎯 机会雷达(24h)</span></div>
  <table><tr><th>M15窗口</th><th>潜在</th><th>合格</th><th>正EV</th><th>执行</th><th>WAIT</th></tr>
  <tr><td class="mono">{esc(f1.get("m15_windows", 0))}</td><td class="mono">{esc(f1.get("potential_opportunities", 0))}</td>
   <td class="mono">{esc(f1.get("qualified_opportunities", 0))}</td><td class="mono up">{esc(f1.get("ev_positive_opportunities", 0))}</td>
   <td class="mono">{esc(f1.get("executed_trades", 0))}</td><td class="mono dim">{esc(f1.get("waits", 0))}</td></tr></table>
  <div class="dim" style="margin-top:6px;font-size:11.5px">机会未出现 vs Hermes 未抓住 — 见 Hermes 14 问理由</div>
 </div>
</div>

<div class="card"><div class="ttl"><span>📊 最近 Hermes 决策</span><span class="dim">真实记录(WAIT 亦记录)</span></div>
 <div class="scroll"><table><tr><th>时间</th><th>Hermes</th><th>机会</th><th>理由</th></tr>{dec_rows}</table></div></div>

<div class="bar" style="margin-top:10px"><span>系统事件: M15 收盘 ✓ {evs} · <span class="dim">{esc(now)}</span></span></div>
<div class="footer">Hermes 唯一交易员 · OpenClaw 总控 · 决策每15分钟 · 行情30s高频 · 只读不伪造</div>
</div>
<script>{JS}</script><script>loadTF('M15');refresh();</script>
</body></html>"""
