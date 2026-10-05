"""Independent forward observer; cannot modify a trading model or place an order."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from .common import atomic_json, load_config, digest, ProcessLock


class Observer:
    def __init__(self, directory):
        self.directory=Path(directory)
        self.path=self.directory/'research_checkpoint.json'
        self.state=dict(schema='v3-forward-observer/1',cursors={},models={},pending=[],
                        last_tick_ms=None,last_forecast_ms=None,censored=0,processed_forecasts=0)
        if self.path.exists():
            self.state=json.loads(self.path.read_text(encoding='utf-8'))

    def model_stats(self, model_hash):
        if model_hash not in self.state['models']:
            self.state['models'][model_hash]={str(h):dict(n=0,take_n=0,sum_gross_bp=0.,sum_proxy_net_bp=0.,
                sum_random_proxy_net_bp=0.,sum_abs_prediction_error_bp=0.,take_net_sum_bp=0.,
                predicted_net_sum_bp=0.) for h in (5,10,30,60,300)}
        return self.state['models'][model_hash]

    def feed(self,event):
        ts=event['timestamp_ms']
        if event['kind']=='FORECAST':
            if self.state['last_forecast_ms'] is not None and ts<=self.state['last_forecast_ms']:
                return
            self.state['last_forecast_ms']=ts
            self.state['processed_forecasts']+=1
            self.model_stats(event['model_hash'])
            for horizon,prediction in event['predictions'].items():
                self.state['pending'].append(dict(target_ms=ts+int(horizon)*1000,horizon=horizon,forecast=event))
        elif event['kind']=='TICK':
            previous=self.state['last_tick_ms']
            if previous is not None and ts<previous:
                return
            if previous is not None and ts-previous>5000:
                self.state['censored']+=len(self.state['pending'])
                self.state['pending']=[]
            self.state['last_tick_ms']=ts
            remaining=[]
            for pending in self.state['pending']:
                if pending['target_ms']>ts:
                    remaining.append(pending)
                    continue
                if ts-pending['target_ms']>5000:
                    self.state['censored']+=1
                    continue
                forecast=pending['forecast']
                horizon=pending['horizon']
                predicted=forecast['predictions'][horizon]
                direction=1 if predicted>=0 else -1
                random_direction=1 if int(digest([forecast['signal_id'],horizon,'seed20261005'])[:8],16)%2 else -1
                entry_mid=(forecast['bid']+forecast['ask'])/2
                exit_mid=(event['bid']+event['ask'])/2
                markout=(exit_mid/entry_mid-1)*10000
                def net(side):
                    move=event['bid']-forecast['ask'] if side>0 else forecast['bid']-event['ask']
                    return move/entry_mid*10000-forecast['commission_bp']
                proxy=net(direction)
                stats=self.model_stats(forecast['model_hash'])[horizon]
                stats['n']+=1
                stats['sum_gross_bp']+=direction*markout
                stats['sum_proxy_net_bp']+=proxy
                stats['sum_random_proxy_net_bp']+=net(random_direction)
                stats['sum_abs_prediction_error_bp']+=abs(markout-predicted)
                stats['predicted_net_sum_bp']+=abs(predicted)-forecast['estimated_cost_bp']
                if abs(predicted)>forecast['estimated_cost_bp']:
                    stats['take_n']+=1
                    stats['take_net_sum_bp']+=proxy
            self.state['pending']=remaining

    def scan(self):
        for path in sorted((self.directory/'forward').glob('forward_*.jsonl')):
            key=path.name
            offset=self.state['cursors'].get(key,0)
            if path.stat().st_size<offset:
                raise RuntimeError('FORWARD_STREAM_TRUNCATED')
            with path.open('rb') as file:
                file.seek(offset)
                while True:
                    start=file.tell()
                    line=file.readline()
                    if not line or not line.endswith(b'\n'):
                        file.seek(start)
                        break
                    self.feed(json.loads(line))
                self.state['cursors'][key]=file.tell()
        atomic_json(self.path,self.state)
        models={}
        for model,horizons in self.state['models'].items():
            models[model]={}
            for h,stats in horizons.items():
                n,takes=stats['n'],stats['take_n']
                models[model][h]=dict(n=n,eligible_by_cost_n=takes,
                    mean_directional_markout_bp=stats['sum_gross_bp']/n if n else None,
                    mean_quote_proxy_net_bp=stats['sum_proxy_net_bp']/n if n else None,
                    mean_random_control_net_bp=stats['sum_random_proxy_net_bp']/n if n else None,
                    mean_prediction_mae_bp=stats['sum_abs_prediction_error_bp']/n if n else None,
                    mean_eligible_quote_proxy_net_bp=stats['take_net_sum_bp']/takes if takes else None,
                    effective_independent_n='NOT_ESTABLISHED_OVERLAPPING_LABELS')
        report=dict(schema='v3-forward-research/1',observed_ms=time.time_ns()//1_000_000,
            status='FORWARD_OBSERVATION',strategy_status='EXPERIMENTAL_UNVALIDATED',models=models,
            forecasts=self.state['processed_forecasts'],pending_labels=len(self.state['pending']),
            censored_labels=self.state['censored'],realized_pnl_source='strategy_ledger ROUND_TRIP broker deals',
            quote_proxy_is_not_realized_pnl=True,formal_candidate_oos='NOT_EVALUATED',
            can_send_orders=False,can_change_model=False)
        atomic_json(self.directory/'research.json',report)
        return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--once',action='store_true')
    args=p.parse_args()
    root=Path(args.root)
    cfg=load_config(root/'config.demo.json')
    directory=root/cfg['runtime_dir']
    with ProcessLock(directory/'research.lock'):
        observer=Observer(directory)
        while True:
            observer.scan()
            if args.once: break
            time.sleep(cfg['research_interval_seconds'])


if __name__=='__main__':
    main()
