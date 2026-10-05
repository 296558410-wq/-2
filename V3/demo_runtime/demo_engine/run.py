from __future__ import annotations
import argparse
import json
import signal
import time
import traceback
from pathlib import Path
from .common import load_config, atomic_json, SafetyError, ProcessLock
from .model import FrozenModel
from .broker import MT5Broker
from .engine import TradingEngine

TRANSIENT={'TRADING_CONNECTION_UNAVAILABLE','TICK_QUERY_FAILED','POSITIONS_QUERY_FAILED',
           'ACCOUNT_QUERY_FAILED','DEALS_QUERY_FAILED','QUOTE_QUERY_FAILED','ACCOUNT_OR_TERMINAL_UNAVAILABLE'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--observe-only',action='store_true')
    p.add_argument('--duration',type=float)
    p.add_argument('--preflight',action='store_true')
    p.add_argument('--runtime-subdir',help='Isolated output directory for read-only acceptance only')
    args=p.parse_args()
    root=Path(args.root)
    cfg=load_config(root/'config.demo.json')
    model=FrozenModel(root/cfg['model_path'])
    if args.runtime_subdir and not (args.observe_only or args.preflight):
        raise SafetyError('RUNTIME_OVERRIDE_ONLY_FOR_READONLY_ACCEPTANCE')
    directory=(root/(args.runtime_subdir or cfg['runtime_dir'])).resolve()
    if root.resolve() not in directory.parents:
        raise SafetyError('RUNTIME_DIRECTORY_OUTSIDE_PROJECT')
    directory.mkdir(parents=True,exist_ok=True)
    with ProcessLock(directory/'trader.lock'):
        broker=MT5Broker(cfg)
        engine=None
        try:
            account=broker.connect()
            if args.preflight:
                result=dict(account=account,spec=broker.spec,positions=broker.positions(),orders=broker.orders(),
                            quote=broker.quote().__dict__,live=False,model_hash=model.hash)
                atomic_json(directory/'preflight.json',result)
                print(json.dumps(result,ensure_ascii=False))
                return
            engine=TradingEngine(cfg,model,broker,directory,observe_only=args.observe_only)
            engine.initialize()
            stopping=False
            def stop(*unused):
                nonlocal stopping
                stopping=True
                engine.state['stop_requested']=True
                engine.checkpoint('PROCESS_STOP_SIGNAL')
            signal.signal(signal.SIGINT,stop)
            if hasattr(signal,'SIGTERM'): signal.signal(signal.SIGTERM,stop)
            started=time.monotonic()
            last_publish=0
            healthy=0
            while True:
                if args.duration and time.monotonic()-started>=args.duration:
                    stopping=True
                    engine.state['stop_requested']=True
                try:
                    engine.manage()
                    for tick in broker.ticks():
                        engine.consume(tick)
                    healthy+=1
                    if healthy>=10 and str(engine.state['halted'] or '').startswith('TRANSIENT:') and not engine.state['pending']:
                        engine.state['halted']=None
                        engine.checkpoint('CONNECTION_RECOVERED')
                except SafetyError as e:
                    healthy=0
                    reason=str(e)
                    engine.last_error=reason
                    engine.halt(('TRANSIENT:' if reason in TRANSIENT else '')+reason)
                    time.sleep(1)
                except Exception as e:
                    healthy=0
                    engine.last_error=type(e).__name__+':'+str(e)
                    engine.halt('UNEXPECTED_RUNTIME_ERROR')
                    # Keep the ownership record and broker SL; restart cannot resend a pending entry.
                    traceback.print_exc()
                    time.sleep(1)
                if time.monotonic()-last_publish>=1:
                    engine.publish()
                    last_publish=time.monotonic()
                if (stopping or engine.state['stop_requested']) and not engine.state['position'] and not engine.state['pending']:
                    break
                time.sleep(cfg['poll_seconds'])
            engine.journal.append('ENGINE_STOP',state=engine.state)
            engine.publish()
            print(json.dumps(engine.status(),ensure_ascii=False))
        finally:
            if engine:
                engine.stream.close()
            broker.disconnect()


if __name__=='__main__':
    main()
