from __future__ import annotations
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .common import load_config

HTML='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3 高频交易与研究</title><style>
body{background:#0d1420;color:#e6edf8;font:15px system-ui;margin:0;padding:28px;max-width:1400px}h1{font-size:26px;margin:0 0 6px}.muted{color:#94a5be}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:24px 0}.card{background:#172235;border:1px solid #2b3c55;border-radius:12px;padding:18px}.value{font-size:25px;margin-top:10px;color:#55dec6}table{width:100%;border-collapse:collapse;margin-top:15px}td,th{text-align:left;padding:12px;border-bottom:1px solid #293950}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#101b2b;padding:16px;border-radius:10px}.warn{color:#ffc881}canvas{width:100%;height:130px}a{color:#55dec6}
</style><h1>V3 · 高频交易机器与研究机器</h1><div class="muted">XAUUSD / Demo · 实验策略前向验证 · 每秒刷新</div>
<div class="grid"><div class="card">运行状态<div class="value" id="status">连接中</div></div><div class="card">真实策略成交往返<div class="value" id="trades">—</div></div><div class="card">完整净盈亏（USD）<div class="value" id="net">—</div></div><div class="card">日亏损上限（USD）<div class="value" id="limit">—</div></div><div class="card">行情年龄 / 处理延迟<div class="value" id="latency">—</div></div></div>
<div class="card"><b>当前决策与持仓</b><p id="reason"></p><pre id="signal"></pre><div id="position"></div><p class="warn">策略状态：未经盈利验证的 Demo 实验。研究报价测算与真实成交净盈亏分别展示。</p></div>
<div class="grid"><div class="card" style="grid-column:1/-1"><b>真实策略累计净盈亏</b><canvas id="chart" width="1100" height="130"></canvas></div></div>
<div class="card"><b>持续研究 · 全部预测周期</b><p class="muted">报价代理包含进出价差与佣金估计，不等于实际成交收益。样本有重叠，有效独立样本数尚未建立。</p><table><thead><tr><th>周期</th><th>成熟样本</th><th>成本后报价代理（bp）</th><th>随机方向控制（bp）</th><th>预测误差（bp）</th></tr></thead><tbody id="research"></tbody></table></div>
<div class="card" style="margin-top:18px"><b>最近真实策略成交</b><table><thead><tr><th>上海时间</th><th>持仓ID</th><th>净盈亏</th><th>对账</th></tr></thead><tbody id="history"></tbody></table><p class="muted" id="version"></p></div>
<script>
const $=id=>document.getElementById(id),fmt=x=>x==null?'—':Number(x).toFixed(3);let history=[];
function rows(target,data){const body=$(target);body.replaceChildren();for(const values of data){const row=document.createElement('tr');for(const v of values){const cell=document.createElement('td');cell.textContent=v;row.appendChild(cell)}body.appendChild(row)}}
function chart(trades){let sum=0;const values=[0,...trades.map(t=>sum+=t.net_pnl)],c=$('chart'),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);let lo=Math.min(...values,-.01),hi=Math.max(...values,.01);ctx.strokeStyle='#55dec6';ctx.lineWidth=2;ctx.beginPath();values.forEach((v,i)=>{let x=15+i/(Math.max(values.length-1,1))*(c.width-30),y=15+(hi-v)/(hi-lo)*(c.height-30);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()}
async function refresh(){try{const [s,r,t]=await Promise.all(['/api/status','/api/research','/api/trades'].map(p=>fetch(p,{cache:'no-store'}).then(r=>r.json())));const st=s.state||{};$('status').textContent=(s.stale?'状态已陈旧 · ':'')+(s.status||'尚未启动');$('trades').textContent=st.completed_round_trips||0;$('net').textContent=fmt(st.total_net);$('limit').textContent=fmt(s.daily_loss_limit);$('latency').textContent=(s.quote_age_ms==null?'—':s.quote_age_ms+'ms')+' / '+fmt(s.processing_latency_ms?.p95)+'ms';$('reason').textContent='当前原因：'+(s.last_reason||s.error||'等待');$('signal').textContent=JSON.stringify(s.last_signal||{},null,2);$('position').textContent=st.position?'当前持仓：'+JSON.stringify(st.position):'当前持仓：空仓';const h=r.models?.[s.model_hash]||{};rows('research',[5,10,30,60,300].map(k=>[k+'秒',h[k]?.n||0,fmt(h[k]?.mean_quote_proxy_net_bp),fmt(h[k]?.mean_random_control_net_bp),fmt(h[k]?.mean_prediction_mae_bp)]));rows('history',t.slice(-20).reverse().map(x=>[new Date(x.closed_ms).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}),x.position_id,fmt(x.net_pnl),x.reconciliation]));$('version').textContent='模型 '+(s.model_hash||'').slice(0,16)+' · 实验 '+(s.protocol||'')+' · 研究更新时间 '+(r.observed_ms?new Date(r.observed_ms).toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai'}):'等待');chart(t)}catch(e){$('status').textContent='面板连接异常';$('reason').textContent=String(e)}}refresh();setInterval(refresh,1000);
</script></html>'''


def serve(root):
    root=Path(root)
    cfg=load_config(root/'config.demo.json')
    directory=root/cfg['runtime_dir']
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            path=self.path.split('?')[0]
            if path=='/':
                body=HTML.encode('utf-8'); kind='text/html; charset=utf-8'
            elif path in ('/api/status','/api/research','/api/supervisor'):
                file=directory/(path.rsplit('/',1)[1]+'.json')
                try:
                    obj=json.loads(file.read_text(encoding='utf-8'))
                    if path=='/api/status':
                        obj['stale']=time.time()*1000-obj.get('observed_ms',0)>10000
                except (OSError,ValueError): obj={'status':'NOT_STARTED'}
                body=json.dumps(obj,ensure_ascii=False).encode('utf-8'); kind='application/json; charset=utf-8'
            elif path=='/api/trades':
                records=[]
                file=directory/'strategy_ledger.jsonl'
                if file.exists():
                    with file.open(encoding='utf-8') as f:
                        for line in f:
                            try:
                                event=json.loads(line)
                                if event.get('kind')=='ROUND_TRIP': records.append(event)
                            except ValueError: break
                body=json.dumps(records,ensure_ascii=False).encode('utf-8'); kind='application/json; charset=utf-8'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type',kind)
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers(); self.wfile.write(body)
        def do_POST(self): self.send_error(405)
        def do_PUT(self): self.send_error(405)
        def do_PATCH(self): self.send_error(405)
        def do_DELETE(self): self.send_error(405)
    ThreadingHTTPServer(('127.0.0.1',cfg['dashboard_port']),Handler).serve_forever()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    serve(p.parse_args().root)
