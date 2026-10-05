from __future__ import annotations
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from demo_engine.common import Journal,SafetyError,load_config,atomic_json,digest,ProcessLock
from demo_engine.features import Features,Tick,NAMES
from demo_engine.engine import TradingEngine
from demo_engine.broker import MT5Broker
from demo_engine.research import Observer

ROOT=Path(__file__).resolve().parents[1]


class Model:
    hash='test-model-hash'
    data={'horizons':{'30':dict(adverse_selection_bp=.1,uncertainty_bp=.1)}}
    def predict(self,vector): return {str(h):4. for h in (5,10,30,60,300)}


class FakeBroker:
    def __init__(self,clock):
        self.clock=clock;self.spec=dict(trade_contract_size=100.,point=.01)
        self.pos=[];self.history={};self.calls=[];self.outcome='DONE';self.fail_query=False
        self.real=False;self.next_ticket=100;self.balance=493.02;self.profit=.75
        self.pending_orders=[]
    def validate(self,for_entry=False):
        if self.real: raise SafetyError('REAL_ACCOUNT_REFUSED')
    def account(self): return dict(equity=self.balance,balance=self.balance,currency='USD')
    def positions(self):
        if self.fail_query: raise SafetyError('POSITIONS_QUERY_FAILED')
        return copy.deepcopy(self.pos)
    def orders(self): return list(self.pending_orders)
    def deals(self,pid): return copy.deepcopy(self.history.get(pid,[]))
    def find_entry(self,intent):
        return [copy.deepcopy(d) for deals in self.history.values() for d in deals if d['entry']==0 and d['comment']==intent['comment']]
    def request(self,side,volume,comment,stop_distance=None,position=None):
        self.validate()
        self.calls.append(dict(side=side,volume=volume,position=position,comment=comment))
        if self.outcome=='REJECTED': return dict(outcome='REJECTED',retcode=10018)
        if self.outcome=='UNKNOWN_EMPTY': return dict(outcome='UNKNOWN',retcode=None)
        if position is None:
            self.next_ticket+=1;pid=self.next_ticket
            amount=volume/2 if self.outcome=='PARTIAL' else volume
            self.pos=[dict(ticket=pid,identifier=pid,magic=90004,symbol='XAUUSD',comment=comment,
                          type=0 if side=='LONG' else 1,volume=amount,price_open=4000.2 if side=='LONG' else 4000.,
                          sl=(4000.2-stop_distance) if side=='LONG' else (4000.+stop_distance),profit=0.)]
            self.history[pid]=[dict(ticket=pid*10,position_id=pid,entry=0,magic=90004,symbol='XAUUSD',comment=comment,
                volume=amount,profit=0.,commission=-.11,swap=0.,fee=0.,price=self.pos[0]['price_open'])]
        else:
            pid=position
            self.history[pid].append(dict(ticket=pid*10+1,position_id=pid,entry=1,magic=90004,symbol='XAUUSD',
                comment=comment,volume=volume,profit=self.profit,commission=-.11,swap=0.,fee=0.,price=4000.95))
            self.pos=[];self.balance+=self.profit-.22
        return dict(outcome='UNKNOWN' if self.outcome in ('UNKNOWN_FILLED','PARTIAL') else 'DONE',deal=pid*10,order=pid)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=Path(self.tmp.name)/'runtime'
        self.now=1791180000000
        self.cfg=load_config(ROOT/'config.demo.json')
        self.model=Model();self.broker=FakeBroker(lambda:self.now)
        self.engine=TradingEngine(self.cfg,self.model,self.broker,self.directory,clock_ms=lambda:self.now)
        self.engine.authorization=lambda:True
        self.engine.initialize()
    def tearDown(self):
        self.engine.stream.close();self.tmp.cleanup()
    def tick(self): return Tick(self.now,4000.,4000.2)
    def enter(self): self.engine.enter('LONG','abc0123456789',self.tick())
    def restart(self):
        self.engine.stream.close()
        self.engine=TradingEngine(self.cfg,self.model,self.broker,self.directory,clock_ms=lambda:self.now)
        self.engine.authorization=lambda:True
        self.engine.initialize()
    def test_complete_broker_accounting(self):
        self.enter();self.assertEqual(self.engine.state['phase'],'OPEN')
        self.now+=30001;self.engine.manage()
        self.assertIsNone(self.engine.state['position'])
        self.assertAlmostEqual(self.engine.state['total_net'],.53)
        self.assertEqual(self.engine.state['completed_round_trips'],1)
        record=[e for e in self.engine.journal.events if e['kind']=='ROUND_TRIP'][0]
        self.assertEqual(record['reconciliation'],'PASS')
        self.assertAlmostEqual(record['accounting']['commission'],-.22)
    def test_duplicate_signal_no_second_send(self):
        self.enter();self.enter();self.assertEqual(len(self.broker.calls),1)
    def test_unknown_result_never_resends(self):
        self.broker.outcome='UNKNOWN_EMPTY';self.enter()
        self.now+=20000;self.engine.manage();self.enter()
        self.assertEqual(len(self.broker.calls),1)
        self.assertIsNotNone(self.engine.state['pending'])
        self.assertEqual(self.engine.state['halted'],'ENTRY_RESULT_UNRESOLVED')
    def test_unknown_filled_managed_after_restart(self):
        self.broker.outcome='UNKNOWN_FILLED';self.enter();self.restart()
        self.assertIsNotNone(self.engine.state['position'])
        self.broker.outcome='DONE';self.engine.manage()
        self.assertEqual(len(self.broker.calls),2)
        self.assertIsNone(self.engine.state['position'])
    def test_partial_entry_is_protected_and_closed(self):
        self.broker.outcome='PARTIAL';self.enter()
        self.assertAlmostEqual(self.engine.state['position']['volume'],.005)
        self.broker.outcome='DONE';self.engine.manage()
        self.assertEqual(self.broker.calls[-1]['volume'],.005)
    def test_known_rejection_has_no_phantom_position(self):
        self.broker.outcome='REJECTED';self.enter();self.restart()
        self.assertIsNone(self.engine.state['position']);self.assertIsNone(self.engine.state['pending'])
    def test_queries_fail_closed(self):
        self.broker.fail_query=True
        with self.assertRaises(SafetyError):self.enter()
        self.assertFalse(self.broker.calls)
    def test_real_account_is_rejected(self):
        self.broker.real=True
        with self.assertRaises(SafetyError):self.enter()
        self.assertFalse(self.broker.calls)
    def test_restart_recovers_position(self):
        self.enter();self.restart();self.now+=30001;self.engine.manage()
        self.assertEqual(self.engine.state['completed_round_trips'],1)
    def test_foreign_position_is_never_adopted_or_closed(self):
        self.broker.pos=[dict(ticket=999,magic=90002,symbol='XAUUSD',comment='FOREIGN')]
        with self.assertRaises(SafetyError):self.engine.reconcile()
        self.assertFalse(self.broker.calls)
    def test_stop_flattens_owned_position(self):
        self.enter();(self.directory/'STOP').write_text('stop')
        self.engine.manage();self.assertIsNone(self.engine.state['position'])
        self.engine.enter('LONG','another',self.tick());self.assertEqual(len(self.broker.calls),2)
    def test_daily_loss_halts_and_closes(self):
        self.enter();self.broker.pos[0]['profit']=-6
        self.engine.manage();self.assertEqual(self.engine.state['halted'],'DAILY_LOSS_LIMIT')
        self.assertIsNone(self.engine.state['position'])
    def test_daily_cap_blocks_intent(self):
        self.engine.state['daily_entries']=30;self.enter();self.assertFalse(self.broker.calls)
    def test_missing_stop_triggers_risk_exit(self):
        self.enter();self.broker.pos[0]['sl']=0;self.engine.manage()
        self.assertIsNone(self.engine.state['position'])
        self.assertEqual(self.engine.state['halted'],'PROTECTIVE_STOP_MISSING')
    def test_closed_history_not_yet_visible_keeps_ownership(self):
        self.enter();pid=self.broker.pos[0]['ticket'];self.broker.pos=[]
        self.engine.reconcile();self.assertIsNotNone(self.engine.state['position'])
        self.assertEqual(self.engine.state['halted'],'CLOSED_POSITION_HISTORY_NOT_READY')
        self.assertEqual(self.engine.state['completed_round_trips'],0)
    def test_round_trip_crash_boundary_not_double_counted(self):
        self.enter();self.now+=30001
        original=self.engine.checkpoint
        def crash(reason):
            if reason=='ROUND_TRIP_RECONCILED':raise RuntimeError('crash after journal commit')
            original(reason)
        self.engine.checkpoint=crash
        with self.assertRaises(RuntimeError):self.engine.manage()
        self.restart();self.assertAlmostEqual(self.engine.state['total_net'],.53)
        self.assertEqual(self.engine.state['completed_round_trips'],1)
        self.assertEqual(len([e for e in self.engine.journal.events if e['kind']=='ROUND_TRIP']),1)
    def test_entry_crash_before_confirmation_recovers(self):
        self.enter()
        # Emulate durable intent + response, then loss of its later confirmation checkpoint.
        rows=self.engine.journal.events
        cut=next(i for i,e in enumerate(rows) if e['kind']=='POSITION_CONFIRMED')
        self.engine.stream.close()
        path=self.directory/'strategy_ledger.jsonl'
        lines=path.read_text().splitlines(keepends=True);path.write_text(''.join(lines[:cut]),encoding='utf-8')
        self.restart();self.assertEqual(self.engine.state['position']['ticket'],101)
        self.assertEqual(len(self.broker.calls),1)
    def test_authorization_disabled_blocks_entry(self):
        self.engine.authorization=lambda:False;self.enter();self.assertFalse(self.broker.calls)
    def test_post_fill_slippage_cannot_expand_risk_unnoticed(self):
        original=self.broker.request
        def slipped(*args,**kwargs):
            result=original(*args,**kwargs)
            if kwargs.get('position') is None:
                self.broker.pos[0]['price_open']+=1.
            return result
        self.broker.request=slipped;self.enter()
        self.assertEqual(self.engine.state['halted'],'POST_FILL_RISK_BUDGET_EXCEEDED')
        self.engine.manage();self.assertIsNone(self.engine.state['position'])
    def test_feature_warmup_at_current_slow_tick_rate(self):
        self.engine.authorization=lambda:False
        for i in range(240):
            self.now+=400
            mid=4000.+math.sin(i/10)*.1
            self.engine.consume(Tick(self.now,mid-.1,mid+.1))
        self.assertGreater(self.engine.decisions,0)
        self.assertFalse(self.broker.calls)


class IntegrityTests(unittest.TestCase):
    def test_feature_prefix_invariance(self):
        full=Features();prefix=Features();before=None
        for i in range(500):
            mid=4000+math.sin(i/9)*.3+i*.001
            tick=Tick(1791180000000+i*100,mid-.1,mid+.1)
            full.add(tick)
            if i<301:prefix.add(tick)
            if i==300:before=full.vector()
        self.assertEqual(before,prefix.vector());self.assertEqual(len(before),len(NAMES))
    def test_feature_invalid_and_time_regression(self):
        f=Features();self.assertTrue(f.add(Tick(1000,1.,1.1)))
        self.assertFalse(f.add(Tick(900,1.,1.1)));self.assertFalse(f.add(Tick(1100,2.,1.1)))
        self.assertFalse(f.add(Tick(1100,float('nan'),1.1)))
    def test_journal_corruption_and_partial_tail_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal';j=Journal(path);j.append('TEST',unknown_field={'kept':True})
            self.assertTrue(Journal(path).events[0]['unknown_field']['kept'])
            with path.open('a') as f:f.write('{')
            with self.assertRaises(SafetyError):Journal(path)
    def test_journal_snapshots_not_mutated(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'j');v={'nested':{'x':1}};j.append('STATE',state=v);v['nested']['x']=2
            self.assertEqual(j.events[0]['state']['nested']['x'],1)
    def test_process_lock_prevents_duplicate_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            with ProcessLock(Path(d)/'lock'):
                with self.assertRaises(OSError):
                    with ProcessLock(Path(d)/'lock'):pass
    def test_observer_future_labels_and_restart_exact_once(self):
        with tempfile.TemporaryDirectory() as d:
            o=Observer(d)
            e=dict(kind='FORECAST',timestamp_ms=10000,bid=100.,ask=100.1,signal_id='id',model_hash='m',
                   predictions={'5':10.},estimated_cost_bp=12.,commission_bp=2.)
            o.feed(e);self.assertEqual(o.state['models']['m']['5']['n'],0)
            o.feed(dict(kind='TICK',timestamp_ms=14000,bid=100.3,ask=100.4))
            self.assertEqual(o.state['models']['m']['5']['n'],0)
            o.feed(dict(kind='TICK',timestamp_ms=15000,bid=100.4,ask=100.5))
            self.assertEqual(o.state['models']['m']['5']['n'],1)
            o.feed(e);self.assertEqual(len(o.state['pending']),0)
    def test_observer_gap_censors_labels(self):
        with tempfile.TemporaryDirectory() as d:
            o=Observer(d);o.feed(dict(kind='TICK',timestamp_ms=10000,bid=100.,ask=100.1))
            o.feed(dict(kind='FORECAST',timestamp_ms=10000,bid=100.,ask=100.1,signal_id='id',model_hash='m',
                   predictions={'5':10.},estimated_cost_bp=12.,commission_bp=2.))
            o.feed(dict(kind='TICK',timestamp_ms=25000,bid=100.4,ask=100.5))
            self.assertEqual(o.state['censored'],1);self.assertEqual(o.state['models']['m']['5']['n'],0)


if __name__=='__main__':unittest.main()
