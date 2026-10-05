from __future__ import annotations
import datetime as dt
import json
import time
from pathlib import Path
from .common import Journal, SafetyError, atomic_json, digest, finite, file_hash
from .features import Features

SHANGHAI = dt.timezone(dt.timedelta(hours=8))


def day_key(now_ms):
    return dt.datetime.fromtimestamp(now_ms/1000, SHANGHAI).strftime('%Y-%m-%d')


class ForwardStream:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = None
        self.day = None
        self.last_flush = 0

    def append(self, event):
        day = day_key(event['timestamp_ms'])
        if day != self.day:
            self.flush()
            if self.file:
                self.file.close()
            self.file = (self.directory / ('forward_' + day + '.jsonl')).open('a', encoding='utf-8')
            self.day = day
        self.file.write(json.dumps(event, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
        if time.monotonic()-self.last_flush >= 1:
            self.flush()

    def flush(self):
        if self.file:
            self.file.flush()
            import os
            os.fsync(self.file.fileno())
        self.last_flush = time.monotonic()

    def close(self):
        self.flush()
        if self.file:
            self.file.close()


class TradingEngine:
    def __init__(self, cfg, model, broker, directory, clock_ms=None, observe_only=False):
        self.cfg, self.model, self.broker = cfg, model, broker
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.clock = clock_ms or (lambda: time.time_ns()//1_000_000)
        self.observe_only = observe_only
        self.journal = Journal(self.directory/'strategy_ledger.jsonl')
        self.stream = ForwardStream(self.directory/'forward')
        self.features = Features()
        self.last_grid = -1
        self.last_reason = 'STARTING'
        self.last_signal = None
        self.ticks_seen = self.decisions = 0
        self.latencies = []
        self.last_error = None
        self.state = dict(schema='v3-demo-state/1', protocol=cfg['protocol'], model_hash=model.hash,
                          config_hash=digest(cfg), phase='FLAT', pending=None, position=None,
                          halted=None, day=None, day_start_equity=None, daily_net=0.,
                          daily_entries=0, completed_round_trips=0, total_net=0.,
                          rejected=0, cooldown_until_ms=0, last_signal_id=None,
                          exit_attempts=0, last_exit_attempt_ms=0, stop_requested=False)
        for event in self.journal.events:
            if event['kind'] == 'STATE':
                self.state = event['state']
            elif event['kind'] == 'ENTRY_RESPONSE' and self.state['pending'] and self.state['pending']['action']=='ENTRY':
                response = event['response']
                if response['outcome']=='REJECTED':
                    self.state.update(pending=None,phase='FLAT',rejected=self.state['rejected']+1,
                                      cooldown_until_ms=event['intent']['created_ms']+60000)
                elif response['outcome']=='UNKNOWN':
                    self.state['halted']='ENTRY_RESULT_UNKNOWN'
            elif event['kind'] == 'ROUND_TRIP':
                # The reconciliation event is authoritative even if the process died before its checkpoint.
                if self.state['position'] and self.state['position']['identifier']==event['position_id']:
                    net=event['net_pnl']
                    self.state.update(position=None,pending=None,phase='FLAT',exit_attempts=0,
                        cooldown_until_ms=event['closed_ms']+int(cfg['cooldown_seconds']*1000),
                        completed_round_trips=self.state['completed_round_trips']+1,
                        total_net=self.state['total_net']+net,daily_net=self.state['daily_net']+net)
        if self.state['model_hash'] != model.hash or self.state['config_hash'] != digest(cfg):
            raise SafetyError('ACTIVE_EPOCH_MODEL_OR_CONFIG_CHANGED')
        self.latest_account = None

    def checkpoint(self, reason):
        self.journal.append('STATE', reason=reason, state=self.state.copy())
        atomic_json(self.directory/'state.json', self.state)

    def halt(self, reason):
        if self.state['halted'] != reason:
            self.state['halted'] = reason
            self.checkpoint(reason)
        self.last_reason = reason

    def authorization(self):
        if self.observe_only:
            return False
        try:
            auth = json.loads((self.directory/'authorization.json').read_text(encoding='utf-8'))
            ok = (auth.get('enabled') is True and auth.get('mode') == 'DEMO_STRATEGY'
                  and auth.get('live') is False and auth.get('account') == self.cfg['account']
                  and auth.get('model_hash') == self.model.hash and auth.get('config_hash') == digest(self.cfg)
                  and auth.get('protocol') == self.cfg['protocol'])
            if not ok:
                return False
            root = self.directory.parent
            current_cfg = json.loads((root/'config.demo.json').read_text(encoding='utf-8-sig'))
            current_model = json.loads((root/self.cfg['model_path']).read_text(encoding='utf-8'))
            code={p.name:file_hash(p) for p in sorted((root/'demo_engine').glob('*.py'))}
            return (digest(current_cfg) == digest(self.cfg) and digest(current_model) == self.model.hash
                    and auth.get('code_hash') == digest(code))
        except (OSError, ValueError, KeyError):
            return False

    def initialize(self):
        self.broker.validate()
        self.latest_account = self.broker.account()
        self.roll_day()
        self.reconcile()
        start_marker=self.directory/'START'
        if start_marker.exists() and self.authorization() and not self.state['position'] and not self.state['pending']:
            self.state['stop_requested']=False
            self.checkpoint('EXPLICIT_START_REQUEST')
            start_marker.unlink()
        self.journal.append('ENGINE_START', model_hash=self.model.hash, config_hash=digest(self.cfg),
                            mode='DEMO_STRATEGY', observe_only=self.observe_only, account=self.cfg['account'],
                            trade_source='STRATEGY_SIGNAL_EXPERIMENTAL', strategy_status='EXPERIMENTAL_UNVALIDATED')

    def roll_day(self):
        key = day_key(self.clock())
        if self.state['day'] != key:
            previous = self.state['day']
            self.state.update(day=key, day_start_equity=self.latest_account['equity'],
                              daily_net=0., daily_entries=0, rejected=0)
            # Day-scoped economic limits reset; identity, unknown-order, or reconciliation halts do not.
            if self.state['halted'] in ('DAILY_LOSS_LIMIT', 'DAILY_ENTRY_CAP'):
                self.state['halted'] = None
            self.checkpoint('DAY_ROLLOVER_FROM_' + str(previous))

    def _own_position(self, positions):
        c = self.cfg
        if any(p['magic'] != c['magic'] or p['symbol'] != c['symbol'] or not p.get('comment','').startswith('V3S-') for p in positions):
            raise SafetyError('UNEXPECTED_ACCOUNT_POSITION')
        if len(positions) > 1:
            raise SafetyError('MULTIPLE_V3_POSITIONS')
        return positions[0] if positions else None

    def reconcile(self):
        self.broker.validate()
        positions, orders = self.broker.positions(), self.broker.orders()
        if orders:
            self.halt('UNEXPECTED_OR_PENDING_BROKER_ORDER')
            return
        actual = self._own_position(positions)
        pending, owned = self.state['pending'], self.state['position']
        if actual and owned:
            if int(actual['ticket']) != int(owned['ticket']):
                raise SafetyError('POSITION_TICKET_MISMATCH')
            if abs(actual['volume']-owned['volume']) > 1e-8:
                self.halt('POSITION_VOLUME_CHANGED')
            self.state['position']['floating'] = actual['profit']
            if not finite(actual.get('sl')) or actual['sl'] <= 0:
                self.halt('PROTECTIVE_STOP_MISSING')
        elif actual and pending and pending['action'] == 'ENTRY':
            if actual.get('comment') != pending['comment'] or actual['volume'] <= 0 or actual['volume'] > self.cfg['volume']+1e-8:
                raise SafetyError('ENTRY_POSITION_IDENTITY_MISMATCH')
            self.state['position'] = dict(ticket=int(actual['ticket']), identifier=int(actual.get('identifier', actual['ticket'])),
                side=pending['side'], volume=float(actual['volume']), entry_price=float(actual['price_open']),
                opened_ms=int(pending['created_ms']), signal_id=pending['signal_id'], comment=pending['comment'],
                floating=float(actual['profit']), entry_fees=None)
            self.state.update(pending=None, phase='OPEN', rejected=0, exit_attempts=0)
            self.journal.append('POSITION_CONFIRMED', position=self.state['position'], broker_position=actual)
            self.checkpoint('ENTRY_CONFIRMED')
            if not actual.get('sl'):
                self.halt('PROTECTIVE_STOP_MISSING')
            else:
                actual_risk=abs(actual['price_open']-actual['sl'])*actual['volume']*self.broker.spec['trade_contract_size']
                actual_risk+=self.cfg['commission_round_trip_per_lot']*actual['volume']
                if actual_risk>self.cfg['per_trade_risk_usd']+.011:
                    self.halt('POST_FILL_RISK_BUDGET_EXCEEDED')
        elif actual and not owned:
            # Unknown legacy/foreign ownership is never adopted without a durable intent.
            raise SafetyError('UNJOURNALED_POSITION')
        elif not actual and owned:
            deals = self.broker.deals(owned['identifier'])
            entry = [d for d in deals if d['entry'] == 0]
            exits = [d for d in deals if d['entry'] == 1]
            if not entry or not exits:
                self.halt('CLOSED_POSITION_HISTORY_NOT_READY')
                return
            for deal in deals:
                if deal['magic'] != self.cfg['magic'] or deal['symbol'] != self.cfg['symbol']:
                    raise SafetyError('DEAL_IDENTITY_MISMATCH')
                if any(not finite(deal.get(k)) for k in ('profit','commission','swap','fee','volume')):
                    raise SafetyError('DEAL_ACCOUNTING_UNKNOWN')
            volume_in = sum(d['volume'] for d in entry)
            volume_out = sum(d['volume'] for d in exits)
            if abs(volume_in-volume_out) > 1e-8 or abs(volume_in-owned['volume']) > 1e-8:
                raise SafetyError('DEAL_VOLUME_RECONCILIATION_FAILED')
            totals = {k:sum(float(d[k]) for d in deals) for k in ('profit','commission','swap','fee')}
            net = sum(totals.values())
            self.journal.append('ROUND_TRIP', signal_id=owned['signal_id'], model_hash=self.model.hash,
                account=self.cfg['account'], position_id=owned['identifier'], deals=deals, net_pnl=net,
                accounting=totals, closed_ms=self.clock(), day=day_key(self.clock()),
                trade_source='STRATEGY_SIGNAL_EXPERIMENTAL', reconciliation='PASS')
            self.state.update(position=None, pending=None, phase='FLAT', exit_attempts=0,
                cooldown_until_ms=self.clock()+int(self.cfg['cooldown_seconds']*1000),
                completed_round_trips=self.state['completed_round_trips']+1,
                total_net=self.state['total_net']+net, daily_net=self.state['daily_net']+net)
            if self.state['halted'] == 'CLOSED_POSITION_HISTORY_NOT_READY':
                self.state['halted'] = None
            self.checkpoint('ROUND_TRIP_RECONCILED')
        elif not actual and pending:
            if pending['action'] == 'ENTRY':
                entries = self.broker.find_entry(pending)
                if entries:
                    first=entries[0]
                    self.state['position']=dict(ticket=int(first['position_id']),identifier=int(first['position_id']),
                        side=pending['side'],volume=sum(d['volume'] for d in entries),entry_price=first['price'],
                        opened_ms=pending['created_ms'],signal_id=pending['signal_id'],comment=pending['comment'],
                        floating=0.,entry_fees=None)
                    self.state.update(pending=None,phase='OPEN')
                    self.checkpoint('ENTRY_FOUND_IN_HISTORY')
                    self.reconcile()
                elif self.clock()-pending['created_ms'] > self.cfg['pending_timeout_seconds']*1000:
                    # No automatic resend even if no position is currently visible.
                    self.halt('ENTRY_RESULT_UNRESOLVED')
            elif pending['action'] == 'EXIT':
                raise SafetyError('EXIT_WITHOUT_OWNED_POSITION')
        if self.state['position']:
            p = self.state['position']
            deals = self.broker.deals(p['identifier'])
            if not deals:
                p['entry_fees'] = None
            else:
                if any(d['magic'] != self.cfg['magic'] or d['symbol'] != self.cfg['symbol'] for d in deals):
                    raise SafetyError('OPEN_DEAL_IDENTITY_MISMATCH')
                if any(not finite(d.get(k)) for d in deals for k in ('commission','swap','fee')):
                    raise SafetyError('OPEN_ENTRY_FEES_UNKNOWN')
                p['entry_fees'] = sum(d['commission']+d['swap']+d['fee'] for d in deals)

    def risk_loss(self):
        p = self.state['position']
        if p and p['entry_fees'] is None:
            return None
        return self.state['daily_net'] + (p['floating']+p['entry_fees'] if p else 0.)

    def manage(self):
        self.latest_account = self.broker.account()
        self.roll_day()
        self.reconcile()
        limit = min(self.cfg['daily_loss_usd'], self.cfg['daily_loss_fraction']*self.state['day_start_equity'])
        risk_net = self.risk_loss()
        if risk_net is not None and risk_net <= -limit:
            self.halt('DAILY_LOSS_LIMIT')
        kill = self.directory/'STOP'
        if kill.exists() and not self.state['stop_requested']:
            self.state['stop_requested'] = True
            self.checkpoint('STOP_REQUESTED')
        p = self.state['position']
        if not p:
            return
        expired = self.clock()-p['opened_ms'] >= self.cfg['hold_seconds']*1000
        if expired or self.state['halted'] or self.state['stop_requested']:
            self.close('HORIZON_EXIT' if expired else 'RISK_OR_STOP_EXIT')

    def close(self, reason):
        p = self.state['position']
        if not p:
            return
        # Reconcile after every attempt; a close never retries from stale volume/state.
        if self.clock()-self.state['last_exit_attempt_ms'] < 1000:
            return
        if self.state['exit_attempts'] >= self.cfg['max_exit_attempts']:
            self.halt('EXIT_ATTEMPTS_EXHAUSTED_PROTECTED_BY_BROKER_SL')
            return
        actual = self._own_position(self.broker.positions())
        if not actual:
            self.reconcile()
            return
        if self.broker.orders():
            self.halt('EXIT_PENDING_BROKER_ORDER')
            return
        intent = dict(action='EXIT', created_ms=self.clock(), ticket=p['ticket'], side='SHORT' if p['side']=='LONG' else 'LONG',
                      volume=actual['volume'], signal_id=p['signal_id'], comment=p['comment']+'X', reason=reason)
        self.state.update(pending=intent, phase='EXIT_PENDING', exit_attempts=self.state['exit_attempts']+1,
                          last_exit_attempt_ms=self.clock())
        self.checkpoint('EXIT_INTENT_BEFORE_SEND')
        response = self.broker.request(intent['side'], intent['volume'], intent['comment'], position=p['ticket'])
        self.journal.append('EXIT_RESPONSE', intent=intent, response=response)
        if response['outcome'] != 'DONE':
            self.halt('EXIT_' + response['outcome'])
        self.reconcile()

    def consume(self, tick):
        started = time.perf_counter_ns()
        if not self.features.add(tick):
            self.last_reason = 'INVALID_DUPLICATE_OR_REGRESSED_TICK'
            return
        self.ticks_seen += 1
        self.stream.append(dict(kind='TICK', timestamp_ms=tick.timestamp_ms, bid=tick.bid, ask=tick.ask,
            raw_broker_timestamp_ms=tick.timestamp_ms+int(self.cfg['broker_time_offset_seconds']*1000),
            received_ms=self.clock(),broker_time_offset_ms=int(self.cfg['broker_time_offset_seconds']*1000)))
        grid = tick.timestamp_ms//self.cfg['decision_grid_ms']
        if grid <= self.last_grid:
            return
        self.last_grid = grid
        age = self.clock()-tick.timestamp_ms
        if age < -1000 or age > self.cfg['max_signal_age_ms']:
            self.last_reason = 'STALE_OR_FUTURE_QUOTE'
            return
        vector = self.features.vector()
        if vector is None:
            self.last_reason = 'FEATURE_WARMUP'
            return
        predictions = self.model.predict(vector)
        if predictions is None:
            self.last_reason = 'FEATURE_OUTSIDE_DEVELOPMENT_SUPPORT'
            return
        h = self.model.data['horizons']['30']
        predicted = predictions['30']
        side = 'LONG' if predicted > 0 else 'SHORT'
        contract = self.broker.spec['trade_contract_size']
        commission_price = self.cfg['commission_round_trip_per_lot']/contract
        cost_price = max(self.cfg['round_trip_cost_floor_price'], tick.ask-tick.bid+commission_price)
        cost_bp = cost_price/tick.mid*10000
        net_edge = abs(predicted)-cost_bp-h['adverse_selection_bp']-h['uncertainty_bp']
        signal_id = digest(dict(model=self.model.hash, timestamp=tick.timestamp_ms, vector=vector))[:24]
        self.last_signal = dict(signal_id=signal_id, timestamp_ms=tick.timestamp_ms, side=side,
            predicted_gross_bp=predicted, estimated_cost_bp=cost_bp, adverse_selection_bp=h['adverse_selection_bp'],
            uncertainty_bp=h['uncertainty_bp'], net_edge_after_margin_bp=net_edge)
        self.decisions += 1
        self.stream.append(dict(kind='FORECAST', timestamp_ms=tick.timestamp_ms, bid=tick.bid, ask=tick.ask,
            model_hash=self.model.hash, signal_id=signal_id, predictions=predictions, estimated_cost_bp=cost_bp,
            commission_bp=commission_price/tick.mid*10000, primary_horizon_s=30,
            primary_trade_eligible=net_edge > 0, feature_hash=digest(vector), features=vector,
            latest_input_ms=tick.timestamp_ms,decision_received_ms=self.clock(),
            model_status='EXPERIMENTAL_UNVALIDATED'))
        reasons = []
        if net_edge <= 0: reasons.append('NO_POSITIVE_EXPECTED_NET_EDGE')
        if not self.authorization(): reasons.append('DEMO_AUTHORIZATION_DISABLED')
        if self.state['halted']: reasons.append(self.state['halted'])
        if self.state['stop_requested']: reasons.append('STOP_REQUESTED')
        if self.state['position'] or self.state['pending']: reasons.append('POSITION_OR_INTENT_ACTIVE')
        if self.clock() < self.state['cooldown_until_ms']: reasons.append('COOLDOWN')
        if (tick.ask-tick.bid)/tick.mid*10000 > self.cfg['max_spread_bp']: reasons.append('SPREAD_LIMIT')
        if self.state['daily_entries'] >= self.cfg['max_daily_entries']: reasons.append('DAILY_ENTRY_CAP')
        if signal_id == self.state['last_signal_id']: reasons.append('DUPLICATE_SIGNAL')
        if reasons:
            self.last_reason = reasons[0]
        else:
            self.enter(side, signal_id, tick)
        self.latencies.append((time.perf_counter_ns()-started)/1e6)
        self.latencies = self.latencies[-1000:]

    def enter(self, side, signal_id, tick):
        if not self.authorization() or self.state['halted'] or self.state['stop_requested']:
            self.last_reason='ENTRY_AUTHORIZATION_OR_HALT'
            return
        if self.state['pending'] or self.state['position'] or signal_id==self.state['last_signal_id']:
            self.last_reason='DUPLICATE_OR_ACTIVE_INTENT'
            return
        if self.state['daily_entries']>=self.cfg['max_daily_entries'] or (self.directory/'STOP').exists():
            self.last_reason='DAILY_CAP_OR_STOP'
            return
        self.broker.validate(for_entry=True)
        if self.broker.positions() or self.broker.orders():
            raise SafetyError('ENTRY_ACCOUNT_NOT_FLAT')
        contract = self.broker.spec['trade_contract_size']
        dollars_per_price = contract*self.cfg['volume']
        fee_reserve = self.cfg['commission_round_trip_per_lot']*self.cfg['volume']
        slip_reserve = self.cfg['max_deviation_points']*self.broker.spec['point']*dollars_per_price
        stop_distance = (self.cfg['per_trade_risk_usd']-fee_reserve-slip_reserve)/dollars_per_price
        if not finite(stop_distance) or stop_distance <= 0:
            raise SafetyError('RISK_BUDGET_TOO_SMALL')
        intent = dict(action='ENTRY', created_ms=self.clock(), side=side, signal_id=signal_id,
                      comment='V3S-'+signal_id[:16], stop_distance=stop_distance)
        self.state.update(pending=intent, phase='ENTRY_PENDING', last_signal_id=signal_id,
                          daily_entries=self.state['daily_entries']+1)
        self.checkpoint('ENTRY_INTENT_BEFORE_SEND')
        try:
            response = self.broker.request(side, self.cfg['volume'], intent['comment'], stop_distance=stop_distance)
        except SafetyError as e:
            # Failure during precheck has not called order_send. Treat as an explicit rejection.
            response = dict(outcome='REJECTED', precheck_error=str(e))
        self.journal.append('ENTRY_RESPONSE', intent=intent, response=response, model_hash=self.model.hash)
        if response['outcome'] == 'REJECTED':
            self.state.update(pending=None, phase='FLAT', rejected=self.state['rejected']+1,
                              cooldown_until_ms=self.clock()+60000)
            self.last_reason = 'ENTRY_REJECTED'
            self.checkpoint('ENTRY_REJECTED')
            if self.state['rejected'] >= self.cfg['max_consecutive_rejections']:
                self.halt('CONSECUTIVE_REJECTIONS')
        elif response['outcome'] == 'UNKNOWN':
            self.halt('ENTRY_RESULT_UNKNOWN')
            self.reconcile()
        else:
            self.last_reason = 'ORDER_SENT'
            self.reconcile()

    def status(self):
        latency = sorted(self.latencies)
        stats = dict(n=len(latency), p50=latency[len(latency)//2] if latency else None,
                     p95=latency[min(len(latency)-1,int(len(latency)*.95))] if latency else None)
        phase = ('HALTED' if self.state['halted'] else 'STOPPING' if self.state['stop_requested'] else
                 'OBSERVING' if self.observe_only else 'RUNNING')
        return dict(schema='v3-demo-status/1', pid=__import__('os').getpid(), status=phase,
            observed_ms=self.clock(), mode='DEMO_STRATEGY', strategy_status='EXPERIMENTAL_UNVALIDATED',
            account=self.cfg['account'], live=False, protocol=self.cfg['protocol'], model_hash=self.model.hash,
            config_hash=digest(self.cfg), ticks_seen=self.ticks_seen, decisions=self.decisions,
            last_reason=self.last_reason, last_signal=self.last_signal,
            quote_age_ms=self.clock()-self.features.last.timestamp_ms if self.features.last else None,
            processing_latency_ms=stats, state=self.state.copy(), account_snapshot=self.latest_account,
            feature_buffer_ticks=len(self.features.ticks),minimum_feature_ticks=201,
            daily_risk_net=self.risk_loss(), daily_loss_limit=min(self.cfg['daily_loss_usd'],
              self.cfg['daily_loss_fraction']*(self.state['day_start_equity'] or 0)),
            last_error=self.last_error, journal_events=self.journal.seq, journal_head=self.journal.head,
            tick_integrity=dict(duplicates=self.features.duplicates,regressions=self.features.regressions,invalid=self.features.invalid))

    def publish(self):
        self.stream.flush()
        status=self.status()
        atomic_json(self.directory/'status.json', status)
        atomic_json(self.directory/'state.json', self.state)
        if not self.observe_only and self.cfg.get('global_status_path'):
            atomic_json(self.cfg['global_status_path'],status)
