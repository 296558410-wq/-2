from __future__ import annotations
import datetime as dt
import math
import time
from pathlib import Path
from .common import SafetyError, finite
from .features import Tick


class MT5Broker:
    """Only the explicitly configured V3 DEMO account; never a fallback terminal."""
    def __init__(self, cfg):
        import MetaTrader5 as mt5
        self.mt5, self.cfg = mt5, cfg
        self.offset_ms = int(cfg['broker_time_offset_seconds'] * 1000)
        self.connected = False
        self.last_raw_ms = None
        self.last_keys = set()
        self.spec = None

    def connect(self):
        c, m = self.cfg, self.mt5
        args = dict(path=c['terminal'], portable=True, timeout=15000)
        path = Path(c['credentials_file'])
        kv = {}
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    k, v = line.split('=', 1)
                    kv[k.strip()] = v.strip().strip('"').strip("'")
        if kv.get('V3_CALIB_PASSWORD'):
            args.update(login=int(kv.get('V3_CALIB_LOGIN', '0')), password=kv['V3_CALIB_PASSWORD'],
                        server=kv.get('V3_CALIB_SERVER', c['server']))
        if not m.initialize(**args):
            raise SafetyError('MT5_INITIALIZE_FAILED:' + str(m.last_error()))
        self.connected = True
        self.validate()
        s = m.symbol_info(c['symbol'])
        if s is None:
            raise SafetyError('SYMBOL_UNAVAILABLE')
        if not s.visible and not m.symbol_select(c['symbol'], True):
            raise SafetyError('SYMBOL_SELECT_FAILED')
        self.spec = s._asdict()
        if c['volume'] < s.volume_min or c['volume'] > s.volume_max:
            raise SafetyError('VOLUME_OUT_OF_RANGE')
        steps = c['volume'] / s.volume_step
        if abs(steps-round(steps)) > 1e-7:
            raise SafetyError('INVALID_VOLUME_STEP')
        if not finite(s.trade_contract_size) or s.trade_contract_size <= 0:
            raise SafetyError('CONTRACT_SIZE_UNAVAILABLE')
        account = self.account()
        if account['currency'] != 'USD':
            raise SafetyError('NON_USD_ACCOUNT_UNSUPPORTED')
        return account

    def validate(self, for_entry=False):
        m, c = self.mt5, self.cfg
        a, t = m.account_info(), m.terminal_info()
        if a is None or t is None:
            raise SafetyError('ACCOUNT_OR_TERMINAL_UNAVAILABLE')
        if a.login != c['account'] or a.server != c['server']:
            raise SafetyError('WRONG_V3_ACCOUNT')
        if a.trade_mode != m.ACCOUNT_TRADE_MODE_DEMO:
            raise SafetyError('REAL_ACCOUNT_REFUSED')
        expected = Path(c['terminal']).parent.resolve()
        if Path(t.data_path).resolve() != expected or c['terminal_tag'] not in t.data_path:
            raise SafetyError('WRONG_V3_TERMINAL')
        flag = Path(c['legacy_live_flag'])
        if not flag.exists() or flag.read_text(encoding='utf-8').strip().upper() != 'NO':
            raise SafetyError('LIVE_FLAG_NOT_EXPLICITLY_DISABLED')
        if not t.connected or not a.trade_allowed or not a.trade_expert or not t.trade_allowed or t.tradeapi_disabled:
            raise SafetyError('TRADING_CONNECTION_UNAVAILABLE')
        if a.margin_mode != m.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
            raise SafetyError('NON_HEDGE_ACCOUNT_UNSUPPORTED')
        return True

    def account(self):
        a = self.mt5.account_info()
        if a is None:
            raise SafetyError('ACCOUNT_QUERY_FAILED')
        return {k:getattr(a,k) for k in ('login','server','currency','balance','equity','margin_free','trade_mode')}

    def positions(self):
        value = self.mt5.positions_get()
        if value is None:
            raise SafetyError('POSITIONS_QUERY_FAILED')
        return [p._asdict() for p in value]

    def orders(self):
        value = self.mt5.orders_get()
        if value is None:
            raise SafetyError('ORDERS_QUERY_FAILED')
        return [p._asdict() for p in value]

    def quote(self):
        tick = self.mt5.symbol_info_tick(self.cfg['symbol'])
        if tick is None:
            raise SafetyError('QUOTE_QUERY_FAILED')
        raw = int(tick.time_msc)
        return Tick(raw-self.offset_ms, float(tick.bid), float(tick.ask))

    def ticks(self):
        raw_now = time.time_ns() // 1_000_000 + self.offset_ms
        start = self.last_raw_ms if self.last_raw_ms is not None else raw_now-300000
        utc = dt.timezone.utc
        rows = self.mt5.copy_ticks_range(self.cfg['symbol'],
               dt.datetime.fromtimestamp(start/1000, utc),
               dt.datetime.fromtimestamp(raw_now/1000, utc), self.mt5.COPY_TICKS_ALL)
        if rows is None:
            raise SafetyError('TICK_QUERY_FAILED')
        if len(rows) > 20000:
            raise SafetyError('TICK_BACKLOG_EXCEEDED')
        result = []
        previous_ms = self.last_raw_ms
        same_ms_keys = set(self.last_keys)
        for row in rows:
            raw = int(row['time_msc'])
            key = (raw, float(row['bid']), float(row['ask']))
            if previous_ms is not None and raw < previous_ms:
                continue
            if raw == previous_ms and key in same_ms_keys:
                continue
            if raw != previous_ms:
                same_ms_keys = set()
            same_ms_keys.add(key)
            previous_ms = raw
            result.append(Tick(raw-self.offset_ms, key[1], key[2]))
        if previous_ms is not None:
            self.last_raw_ms, self.last_keys = previous_ms, same_ms_keys
        return result

    def _filling(self):
        m = self.mt5
        spec = m.symbol_info(self.cfg['symbol'])
        if spec is None:
            raise SafetyError('SYMBOL_QUERY_FAILED')
        if spec.filling_mode & 1:
            return m.ORDER_FILLING_FOK
        if spec.filling_mode & 2:
            return m.ORDER_FILLING_IOC
        # RETURN is forbidden for Market Execution.
        if spec.trade_exemode == m.SYMBOL_TRADE_EXECUTION_MARKET:
            raise SafetyError('NO_SUPPORTED_MARKET_FILLING')
        return m.ORDER_FILLING_RETURN

    def request(self, side, volume, comment, stop_distance=None, position=None):
        self.validate(for_entry=position is None)
        m, c = self.mt5, self.cfg
        q = self.quote()
        age = time.time_ns()//1_000_000-q.timestamp_ms
        if age < -1000 or age > c['max_signal_age_ms']:
            raise SafetyError('STALE_OR_FUTURE_REQUEST_QUOTE')
        if q.bid <= 0 or q.ask < q.bid:
            raise SafetyError('INVALID_REQUEST_QUOTE')
        is_buy = side == 'LONG'
        req = dict(action=m.TRADE_ACTION_DEAL, symbol=c['symbol'], volume=volume,
                   type=m.ORDER_TYPE_BUY if is_buy else m.ORDER_TYPE_SELL,
                   price=q.ask if is_buy else q.bid, deviation=c['max_deviation_points'],
                   magic=c['magic'], comment=comment, type_time=m.ORDER_TIME_GTC,
                   type_filling=self._filling())
        if position is not None:
            # Every close carries an existing ticket, never an opposite naked order.
            own = [p for p in self.positions() if p['ticket'] == position]
            if len(own) != 1 or own[0]['magic'] != c['magic'] or not own[0]['comment'].startswith('V3S-'):
                raise SafetyError('CLOSE_POSITION_IDENTITY_MISMATCH')
            if own[0]['symbol'] != c['symbol'] or volume > own[0]['volume'] + 1e-9:
                raise SafetyError('CLOSE_VOLUME_OR_SYMBOL_MISMATCH')
            if (own[0]['type'] == m.POSITION_TYPE_BUY) == is_buy:
                raise SafetyError('CLOSE_DIRECTION_MISMATCH')
            req['position'] = position
        else:
            if self.positions() or self.orders():
                raise SafetyError('ACCOUNT_NOT_FLAT_FOR_ENTRY')
            spec = m.symbol_info(c['symbol'])
            if spec.trade_mode != m.SYMBOL_TRADE_MODE_FULL:
                raise SafetyError('SYMBOL_ENTRY_DISABLED')
            if not finite(stop_distance) or stop_distance <= 0:
                raise SafetyError('PROTECTIVE_STOP_REQUIRED')
            if (q.ask-q.bid)/q.mid*10000 > c['max_spread_bp']:
                raise SafetyError('REQUEST_SPREAD_LIMIT')
            # Distance is measured from executable entry. Enforce validity against exit quote.
            sl = req['price'] - stop_distance if is_buy else req['price'] + stop_distance
            tick_size = spec.trade_tick_size
            sl = (math.ceil(sl/tick_size) if is_buy else math.floor(sl/tick_size))*tick_size
            sl = round(sl, spec.digits)
            minimum = max(spec.trade_stops_level*spec.point, tick_size)
            if (q.bid-sl if is_buy else sl-q.ask) < minimum:
                raise SafetyError('STOP_DISTANCE_TOO_SMALL_FOR_BROKER')
            req['sl'] = sl
            margin = m.order_calc_margin(req['type'], c['symbol'], volume, req['price'])
            account = self.account()
            if margin is None or not finite(margin) or account['margin_free'] < margin*2:
                raise SafetyError('INSUFFICIENT_MARGIN')
        check = m.order_check(req)
        if check is None:
            raise SafetyError('ORDER_CHECK_UNKNOWN')
        if check.retcode != 0:
            return dict(outcome='REJECTED', retcode=int(check.retcode), comment=str(check.comment), request=req)
        before = time.perf_counter_ns()
        response = m.order_send(req)
        elapsed = (time.perf_counter_ns()-before)/1e6
        if response is None:
            return dict(outcome='UNKNOWN', retcode=None, last_error=list(m.last_error()), request=req, request_to_ack_ms=elapsed)
        result = response._asdict()
        result.pop('request', None)
        result['request'] = req
        result['request_to_ack_ms'] = elapsed
        if response.retcode == m.TRADE_RETCODE_DONE:
            result['outcome'] = 'DONE'
        elif response.retcode in (m.TRADE_RETCODE_DONE_PARTIAL, m.TRADE_RETCODE_PLACED,
                                  m.TRADE_RETCODE_TIMEOUT, m.TRADE_RETCODE_CONNECTION):
            result['outcome'] = 'UNKNOWN'
        else:
            result['outcome'] = 'REJECTED'
        return result

    def deals(self, position_id):
        values = self.mt5.history_deals_get(position=int(position_id))
        if values is None:
            raise SafetyError('DEALS_QUERY_FAILED')
        return [p._asdict() for p in values]

    def find_entry(self, intent):
        utc = dt.timezone.utc
        start = (intent['created_ms']+self.offset_ms)/1000-60
        end = time.time()+self.offset_ms+60
        rows = self.mt5.history_deals_get(dt.datetime.fromtimestamp(start,utc),dt.datetime.fromtimestamp(end,utc))
        if rows is None:
            raise SafetyError('ENTRY_HISTORY_QUERY_FAILED')
        rows = [d._asdict() for d in rows if d.magic == self.cfg['magic'] and d.symbol == self.cfg['symbol']
                and d.comment == intent['comment'] and d.entry == 0]
        ids = {d['position_id'] for d in rows}
        if len(ids) > 1:
            raise SafetyError('DUPLICATE_ENTRY_HISTORY')
        return rows

    def disconnect(self):
        if self.connected:
            self.mt5.shutdown()
            self.connected = False
