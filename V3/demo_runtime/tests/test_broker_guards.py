import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from demo_engine.broker import MT5Broker
from demo_engine.common import load_config,SafetyError

ROOT=Path(__file__).resolve().parents[1]


class BrokerGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.cfg=load_config(ROOT/'config.demo.json')
        tag=Path(self.tmp.name)/'fxtm_demo_v3calib';tag.mkdir()
        self.cfg['terminal']=str(tag/'terminal64.exe')
        flag=Path(self.tmp.name)/'live';flag.write_text('NO');self.cfg['legacy_live_flag']=str(flag)
        self.acct=NS(login=160766418,server='ForexTimeFXTM-Demo01',trade_mode=0,margin_mode=2,
                     trade_allowed=True,trade_expert=True,currency='USD',balance=493.,equity=493.,margin_free=490.)
        self.info=NS(data_path=str(tag),connected=True,trade_allowed=True,tradeapi_disabled=False)
        self.spec=NS(filling_mode=1,trade_exemode=2,trade_mode=4,point=.01,digits=2,
                     trade_tick_size=.01,trade_stops_level=0,trade_contract_size=100.)
        self.sent=[]
        m=NS(ACCOUNT_TRADE_MODE_DEMO=0,ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2,
             account_info=lambda:self.acct,terminal_info=lambda:self.info,symbol_info=lambda s:self.spec,
             symbol_info_tick=lambda s:NS(time_msc=int(time.time()*1000)+10800000,bid=4000.,ask=4000.2),
             positions_get=lambda:[],orders_get=lambda:[],ORDER_FILLING_FOK=0,ORDER_FILLING_IOC=1,
             ORDER_FILLING_RETURN=2,SYMBOL_TRADE_EXECUTION_MARKET=2,SYMBOL_TRADE_MODE_FULL=4,
             TRADE_ACTION_DEAL=1,ORDER_TYPE_BUY=0,ORDER_TYPE_SELL=1,ORDER_TIME_GTC=0,
             order_calc_margin=lambda *a:3.,order_check=lambda r:NS(retcode=0),
             order_send=lambda r:self.send(r),TRADE_RETCODE_DONE=10009,
             TRADE_RETCODE_DONE_PARTIAL=10010,TRADE_RETCODE_PLACED=10008,
             TRADE_RETCODE_TIMEOUT=10012,TRADE_RETCODE_CONNECTION=10031)
        self.broker=MT5Broker.__new__(MT5Broker);self.broker.mt5=m;self.broker.cfg=self.cfg
        self.broker.offset_ms=10800000;self.broker.spec=self.spec.__dict__
    def tearDown(self):self.tmp.cleanup()
    def send(self,request):
        self.sent.append(request)
        return NS(retcode=10009,_asdict=lambda:dict(retcode=10009,deal=1,order=1,price=request['price']))
    def test_real_account_guard_in_actual_adapter(self):
        self.acct.trade_mode=2
        with self.assertRaisesRegex(SafetyError,'REAL_ACCOUNT'):self.broker.request('LONG',.01,'V3S-test',stop_distance=1.)
        self.assertEqual(self.sent,[])
    def test_wrong_login_and_terminal_refused(self):
        self.acct.login=160759434
        with self.assertRaises(SafetyError):self.broker.validate()
        self.acct.login=160766418;self.info.data_path=self.tmp.name
        with self.assertRaises(SafetyError):self.broker.validate()
    def test_live_flag_must_exist_and_be_no(self):
        Path(self.cfg['legacy_live_flag']).unlink()
        with self.assertRaises(SafetyError):self.broker.validate()
    def test_broker_supported_fok_is_not_ioc(self):
        response=self.broker.request('LONG',.01,'V3S-test',stop_distance=1.)
        self.assertEqual(response['outcome'],'DONE')
        self.assertEqual(self.sent[0]['type_filling'],0)
        self.assertGreater(self.sent[0]['sl'],0)
    def test_entry_requires_protective_stop(self):
        with self.assertRaises(SafetyError):self.broker.request('LONG',.01,'V3S-test')
        self.assertFalse(self.sent)
    def test_position_query_failure_cannot_be_empty(self):
        self.broker.mt5.positions_get=lambda:None
        with self.assertRaisesRegex(SafetyError,'POSITIONS_QUERY_FAILED'):self.broker.request('LONG',.01,'V3S-test',stop_distance=1.)
        self.assertFalse(self.sent)
    def test_insufficient_margin_blocks_send(self):
        self.acct.margin_free=1
        with self.assertRaisesRegex(SafetyError,'MARGIN'):self.broker.request('LONG',.01,'V3S-test',stop_distance=1.)
        self.assertFalse(self.sent)
    def test_close_cannot_be_an_opposite_naked_entry(self):
        with self.assertRaisesRegex(SafetyError,'CLOSE_POSITION_IDENTITY'):self.broker.request('SHORT',.01,'V3S-testX',position=123)
        self.assertFalse(self.sent)
    def test_no_supported_market_filling_blocks_send(self):
        self.spec.filling_mode=0
        with self.assertRaisesRegex(SafetyError,'NO_SUPPORTED_MARKET_FILLING'):self.broker.request('LONG',.01,'V3S-test',stop_distance=1.)
        self.assertFalse(self.sent)


if __name__=='__main__':unittest.main()
