from __future__ import annotations
import hashlib
import json
import math
import os
import time
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        f.write(canonical(value))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


class SafetyError(RuntimeError):
    pass


class ProcessLock:
    """OS-owned lock; automatically released after a crash, including on Windows."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, 'a+b')
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                if self.path.stat().st_size == 0:
                    self.file.write(b'0')
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.file.close()
            self.file=None
            raise
        return self

    def __exit__(self, *args):
        if self.file:
            self.file.close()


class Journal:
    """Full-field, durable hash-chain. A corrupt/truncated journal refuses trading."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.seq, self.head = 0, '0' * 64
        self.events = []
        if self.path.exists():
            with self.path.open(encoding='utf-8') as f:
                for line in f:
                    if not line.endswith('\n'):
                        raise SafetyError('JOURNAL_TRUNCATED')
                    event = json.loads(line)
                    stored = event.pop('hash')
                    if event.get('seq') != self.seq + 1 or event.get('previous') != self.head or digest(event) != stored:
                        raise SafetyError('JOURNAL_CHAIN_INVALID')
                    event['hash'] = stored
                    self.seq, self.head = event['seq'], stored
                    self.events.append(event)

    def append(self, kind, **fields):
        event = dict(seq=self.seq + 1, previous=self.head, kind=kind, observed_ms=time.time_ns() // 1_000_000, **fields)
        event = json.loads(canonical(event))
        event['hash'] = digest(event)
        with self.path.open('a', encoding='utf-8') as f:
            f.write(canonical(event) + '\n')
            f.flush()
            os.fsync(f.fileno())
        self.seq, self.head = event['seq'], event['hash']
        self.events.append(event)
        return event


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if cfg.get('mode') != 'DEMO_STRATEGY' or cfg.get('live') is not False:
        raise SafetyError('INVALID_EXECUTION_MODE')
    if cfg.get('account') != 160766418 or cfg.get('server') != 'ForexTimeFXTM-Demo01':
        raise SafetyError('WRONG_V3_ACCOUNT_CONFIGURATION')
    if cfg.get('symbol') != 'XAUUSD' or cfg.get('magic') != 90004:
        raise SafetyError('WRONG_SYMBOL_OR_MAGIC')
    for key in ('volume', 'poll_seconds', 'daily_loss_usd', 'daily_loss_fraction',
                'per_trade_risk_usd', 'commission_round_trip_per_lot', 'max_spread_bp',
                'max_signal_age_ms', 'max_daily_entries', 'hold_seconds', 'cooldown_seconds'):
        if not finite(cfg.get(key)) or cfg[key] <= 0:
            raise SafetyError('INVALID_CONFIG_' + key)
    if cfg['volume'] > 0.01 or cfg['max_daily_entries'] > 50 or cfg['daily_loss_fraction'] > .01:
        raise SafetyError('EXPERIMENT_RISK_CAP_EXCEEDED')
    if cfg['hold_seconds'] != 30 or cfg['poll_seconds'] > .5:
        raise SafetyError('FROZEN_PROTOCOL_MISMATCH')
    return cfg
