"""V3-HFT-CALIBRATION-PILOT-001: real MT5 demo execution calibration.

NOT a strategy. NOT alpha. Measures the real broker execution chain
(request -> fill -> close -> cost -> reconciliation -> ledger).

Hard rules:
- independent V3 demo instance only (login 160766418, /portable, data_path *_v3calib)
- MAGIC=90004; comment CALIB-V3; CALIBRATION_ORDER=true
- MAX_CALIBRATION_ROUND_TRIPS = 20 (HARD CAP; CALIBRATION_AUTO_STOP at cap)
- frozen direction sequence + frozen holding sequence (hashed, pre-registered)
- NO_AUTO_RETRY=TRUE; any UNKNOWN -> HALT
- any safety-gate failure -> CALIBRATION_STATUS=HALTED
- MOCK_EXECUTION=FALSE for the real run
- never touches V1/V2
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
sys.path.insert(0, V3)

from foundation import timeutil, ledger as LED, pnl_accounting as PNA

# ---- V3-HFT-CALIBRATION-FORMULA-FIX-001 ----
# net_pnl formula version. v3-calibration-netpnl-1 (frozen, defective) charged
# spread + slippage a second time, used abs() on slippage and subtracted the
# broker-signed (negative) commission. v3-calibration-netpnl-2 is broker-anchored;
# see foundation/pnl_accounting.py.

# ---- spec constants (frozen) ----
MAX_ROUND_TRIPS = 20
SYMBOL = "XAUUSD"
MAGIC = 90004
EXPECTED_LOGIN = 160766418
FOREIGN_LOGINS = {160759434, 160761384, 160764551}  # 160764551 = retired V3 demo (password lost)
SERVER_EXPECTED = "ForexTimeFXTM-Demo01"
TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
REQUIRED_TAG = "fxtm_demo_v3calib"
ENV_FILE = r"C:\AIQuant\.env.mt5_v3_calib"
STATE = os.path.join(V3, "state")
OUT = os.path.join(V3, "data", "calibration_160766418")  # ACCOUNT-EPOCH-20260925: new epoch only
LEDGER_PATH = os.path.join(V3, "data", "hft_ledger", "v3_calibration_ledger_160766418.jsonl")  # ACCOUNT-EPOCH-20260925: never mixes with the retired 160764551 ledger
_PFX = "V3_CALIB_" + ""

DIRECTIONS = (["LONG", "SHORT"] * 10)[:MAX_ROUND_TRIPS]
HOLDS_MS = ([100, 250, 500, 1000, 2000] * 4)[:MAX_ROUND_TRIPS]
SEQ_HASH = hashlib.sha256(json.dumps({"dir": DIRECTIONS, "hold": HOLDS_MS},
                                     separators=(",", ":")).encode()).hexdigest()

OTHER_TERMINALS = {
    "v1_host": r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe",
    "v2_fxtm_demo_01": r"C:\AIQuant\mt5_instances\fxtm_demo_01\terminal64.exe",
}


# ---- helpers ----
def _creds():
    kv = {}
    if os.path.exists(ENV_FILE):
        for ln in open(ENV_FILE, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


def _flags():
    out = {}
    for k in ("V3_LIVE_ALLOWED", "V3_ORDER_SEND_ALLOWED", "V3_FORWARD_ALLOWED"):
        try:
            out[k] = open(os.path.join(STATE, k), encoding="utf-8").read().strip()
        except Exception:
            out[k] = "NO"
    return out


AUTH = {"source": None, "login_hint": None}  # §30 AUTH_SOURCE record


def _connect_v3(mt5):
    """Connect to the V3 isolated instance.

    AUTH_SOURCE resolution (task §30):
      - local password present -> explicit login  (AUTH_SOURCE=ENV_CREDENTIALS)
      - local password absent  -> attach to the terminal's SAVED SESSION
                                   (AUTH_SOURCE=SAVED_SESSION); the account is still
                                   hard-verified right after connect (EXPECTED_LOGIN /
                                   FOREIGN_LOGINS) and by hard_gates().
    Never invents, guesses or prints a password.
    """
    kv = _creds()
    args = {"path": TERMINAL, "portable": True, "timeout": 60000}
    lg = int(kv.get(_PFX + "LOGIN", 0) or 0)
    pw = kv.get(_PFX + "PASSWORD")
    if lg and pw:
        args["login"] = lg
        args["password"] = pw
        srv = kv.get(_PFX + "SERVER")
        if srv:
            args["server"] = srv
        AUTH["source"] = "ENV_CREDENTIALS"
    else:
        AUTH["source"] = "SAVED_SESSION"
        AUTH["login_hint"] = lg or None
    return mt5.initialize(**args)


def _acct(mt5):
    a = mt5.account_info()
    return {k: getattr(a, k, None) for k in
            ("login", "server", "balance", "equity", "margin_free", "margin_level",
             "margin", "trade_allowed")}


def _spec(mt5):
    s = mt5.symbol_info(SYMBOL)
    return {k: getattr(s, k, None) for k in
            ("name", "digits", "point", "trade_tick_size", "trade_tick_value",
             "trade_tick_value_profit", "trade_tick_value_loss",
             "trade_contract_size", "volume_min", "volume_step", "volume_max",
             "spread", "visible", "trade_mode", "filling_mode",
             "currency_base", "currency_profit", "currency_margin")}


def _pos(mt5):
    return [p for p in (mt5.positions_get(symbol=SYMBOL) or []) if p.magic == MAGIC]


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    i = min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))
    return xs[i]


def _stats(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": sum(xs) / len(xs), "median": _median(xs), "p50": _median(xs),
            "p95": _pct(xs, 95), "p99": _pct(xs, 99), "min": min(xs), "max": max(xs)}


class Halt(RuntimeError):
    pass


TRADE_SOURCE = "CALIBRATION"  # never recorded as STRATEGY_SIGNAL


def _write_state(name, obj):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)


# ---- selftest (MOCK, never counted) ----
class _FakeMT5:
    """Mock broker for chain validation only. MOCK_EXECUTION=TRUE, not calibration data."""
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009

    class _R:
        def __init__(self, price, retcode=10009, order=1):
            self.price = price; self.retcode = retcode; self.order = order; self.comment = "mock"

    def __init__(self):
        self._t = 0

    def symbol_info_tick(self, s):
        self._t += 1
        return type("T", (), {"bid": 2000.0 + self._t * 0.01, "ask": 2000.2 + self._t * 0.01,
                              "time": time.time()})()

    def order_send(self, req):
        return self._R(req["price"] + 0.01)


def selftest():
    """Validate measurement/profile/reconciliation math on MOCK data (not calibration)."""
    import random
    rng = random.Random(0)
    samples = []
    for i in range(20):
        hold = HOLDS_MS[i]
        e = {"calibration_id": f"MOCK-{i}", "direction": DIRECTIONS[i], "hold_target_ms": hold,
             "valid_entry": True, "valid_exit": True}
        e["signal_to_request_ms"] = rng.uniform(0.01, 0.1)
        e["request_to_ack_ms"] = rng.uniform(5, 40)
        e["ack_to_fill_ms"] = rng.uniform(1, 10)
        e["signal_to_fill_ms"] = e["signal_to_request_ms"] + e["request_to_ack_ms"] + e["ack_to_fill_ms"]
        e["entry_slippage_bps"] = rng.uniform(-0.5, 1.5)
        e["exit_slippage_bps"] = rng.uniform(-1.5, 0.5)
        e["spread_bps"] = rng.uniform(1.2, 2.2)
        e["commission"] = 0.0
        samples.append(e)
    prof = _profiles(samples)
    ok = prof["ENTRY_LATENCY"]["signal_to_fill_ms"]["n"] == 20
    print(json.dumps({"MOCK_EXECUTION": True, "labels": "MOCK_DATA", "samples": 20,
                      "chain_ok": ok, "profiles": prof}, ensure_ascii=False, indent=1))
    return ok


# ---- profiles ----
def _profiles(samples):
    en = [s for s in samples if s.get("valid_entry")]
    ex = [s for s in samples if s.get("valid_exit")]
    return {
        "ENTRY_LATENCY": {
            "signal_to_request_ms": _stats([s.get("signal_to_request_ms") for s in en]),
            "request_to_ack_ms": _stats([s.get("request_to_ack_ms") for s in en]),
            "ack_to_fill_ms": _stats([s.get("ack_to_fill_ms") for s in en]),
            "signal_to_fill_ms": _stats([s.get("signal_to_fill_ms") for s in en]),
        },
        "EXIT_LATENCY": {
            "exit_signal_to_fill_ms": _stats([s.get("exit_latency_ms") for s in ex]),
        },
        "ENTRY_SLIPPAGE": _stats([s.get("entry_slippage_bps") for s in en]),
        "EXIT_SLIPPAGE": _stats([s.get("exit_slippage_bps") for s in ex]),
        "SPREAD_BPS": _stats([s.get("spread_bps") for s in samples]),
    }


def _slippage_signs(samples):
    out = {}
    for side, key in (("entry", "entry_slippage_bps"), ("exit", "exit_slippage_bps")):
        xs = [s.get(key) for s in samples if s.get(key) is not None]
        out[side] = {"positive": sum(1 for x in xs if x > 0),
                     "negative": sum(1 for x in xs if x < 0),
                     "zero": sum(1 for x in xs if x == 0)}
    return out


def _gacct(mt5):
    return {**_acct(mt5), "positions": len(_pos(mt5))}


def _running_terminals():
    ps = "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | ForEach-Object { [string]$_.Id + '|' + [string]$_.Path }"
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    rows = []
    for ln in (r.stdout or "").splitlines():
        ln = ln.strip()
        if "|" in ln:
            pid, path = ln.split("|", 1)
            if path.strip():
                rows.append((pid.strip(), path.strip()))
    return rows


V1_EXE = r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe"
V2_EXE = r"C:\AIQuant\mt5_instances\fxtm_demo_01\terminal64.exe"
PHANTOM_SUFFIX = r"mt5_instances\fxtm_demo_v3\terminal64.exe".lower()


def _filling_mode(mt5):
    """Pick a broker-supported filling mode (symbol flags: 1=FOK, 2=IOC).

    FXTM demo XAUUSD reports filling_mode=1 (FOK only); a hardcoded IOC
    request is rejected with retcode 10030 (TRADE_RETCODE_INVALID_FILL).
    """
    si = mt5.symbol_info(SYMBOL)
    fm = int(getattr(si, "filling_mode", 0) or 0)
    if fm & 1:  # SYMBOL_FILLING_FOK
        return mt5.ORDER_FILLING_FOK
    if fm & 2:  # SYMBOL_FILLING_IOC
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def hard_gates(acct=None, market=None):
    terms = _running_terminals()
    if terms is None:
        return {"TERMINAL_ENUM_AVAILABLE": False}
    g = {"TERMINAL_ENUM_AVAILABLE": True}
    paths = [p.lower() for _, p in terms]

    def has(exe):
        return any(p == exe.lower() for p in paths)
    phantom = [p for p in paths if p.endswith(PHANTOM_SUFFIX)]
    g["MT5_INSTANCE_COUNT_EQ_3"] = (len(terms) == 3)
    g["V1_INSTANCE_PRESENT"] = has(V1_EXE)
    g["V2_INSTANCE_PRESENT"] = has(V2_EXE)
    g["V3_INSTANCE_PRESENT"] = has(TERMINAL)
    g["NO_FXTM_DEMO_V3_PHANTOM"] = (len(phantom) == 0)
    g["NO_UNMAPPED_OR_ORPHAN"] = (len(terms) == 3 and has(V1_EXE) and has(V2_EXE)
                                  and has(TERMINAL) and len(phantom) == 0)
    fl = _flags()
    g["LIVE_GATE_OK"] = (str(fl.get("V3_LIVE_ALLOWED", "NO")).upper() == "NO")
    if acct is not None:
        g["V3_ACCOUNT_OK"] = (acct.get("login") == EXPECTED_LOGIN)
        g["V3_NO_UNEXPECTED_POSITION"] = (acct.get("positions", 0) == 0)
    if market is not None:
        g["MARKET_OPEN"] = bool(market)
    return g


def _assert_hard_gates(acct=None):
    g = hard_gates(acct=acct)
    fails = [k for k, v in g.items() if not v]
    if fails:
        raise Halt("HARD_GATE_FAIL: " + ",".join(fails))


# ---- real run ----
def run(n_roundtrips: int = MAX_ROUND_TRIPS, mock: bool = False, from_index: int = 0):
    import MetaTrader5 as mt5
    if n_roundtrips > MAX_ROUND_TRIPS:
        raise SystemExit(f"REFUSE: n={n_roundtrips} > MAX_CALIBRATION_ROUND_TRIPS={MAX_ROUND_TRIPS}")
    # ---- slice support (engineering only; never alters the frozen sequence) ----
    if not (0 <= from_index < MAX_ROUND_TRIPS) or (from_index + n_roundtrips) > MAX_ROUND_TRIPS:
        raise SystemExit(f"REFUSE: slice out of range from={from_index} n={n_roundtrips}")
    slice_full = (from_index == 0 and n_roundtrips == MAX_ROUND_TRIPS)
    if str(_flags().get("V3_LIVE_ALLOWED", "NO")).upper() != "NO":
        raise SystemExit("REFUSE: V3_LIVE_ALLOWED != NO")
    if mock:
        raise SystemExit("REFUSE: MOCK_EXECUTION is not permitted for the calibration run (see selftest)")

    if not _connect_v3(mt5):
        raise SystemExit(f"REFUSE: V3 init failed {mt5.last_error()}")
    ti = mt5.terminal_info(); ai = mt5.account_info()
    dpath = getattr(ti, "data_path", "") or ""
    login = getattr(ai, "login", None)
    if REQUIRED_TAG not in dpath:
        mt5.shutdown(); raise SystemExit("REFUSE: data_path not V3 isolated instance")
    if login != EXPECTED_LOGIN or login in FOREIGN_LOGINS:
        mt5.shutdown(); raise SystemExit(f"REFUSE: login {login} != {EXPECTED_LOGIN}")
    _assert_hard_gates(_gacct(mt5))

    spec = _spec(mt5)
    volume = float(spec["volume_min"] or 0.01)  # FIXED = broker minimum
    acct0 = _acct(mt5)
    pos0 = _pos(mt5)
    if pos0:
        mt5.shutdown()
        raise SystemExit(f"REFUSE: unexpected initial positions {[p.ticket for p in pos0]}")
    if not _market_open(mt5):
        mt5.shutdown()
        raise SystemExit("REFUSE: market closed / stale tick")

    os.makedirs(OUT, exist_ok=True)
    done_marker = os.path.join(OUT, "PILOT_DONE")
    slice_marker = os.path.join(OUT, f"SLICE_{from_index:02d}_{from_index + n_roundtrips:02d}.done")
    if os.path.exists(done_marker):
        mt5.shutdown(); raise SystemExit("REFUSE: pilot already completed (PILOT_DONE)")
    if os.path.exists(slice_marker):
        mt5.shutdown(); raise SystemExit(f"REFUSE: slice already executed ({os.path.basename(slice_marker)})")

    lg = LED.Ledger(LEDGER_PATH)
    lg.append("CALIBRATION_START", timeutil.utc_ns(), run_id="CALIB-PILOT-001",
              model_version=None, decision_id="calibration")

    samples = []
    halt_reason = None
    started = timeutil.now_iso()
    for i in range(from_index, from_index + n_roundtrips):
        try:
            _assert_hard_gates(_gacct(mt5))
            s = _round_trip(mt5, i, float(volume), lg, spec=spec)
        except Halt as h:
            halt_reason = str(h)
            break
        samples.append(s)
    lg.append("CALIBRATION_COMPLETE", timeutil.utc_ns(), run_id="CALIB-PILOT-001",
              decision_id=f"roundtrips={len(samples)}")

    pos1 = _pos(mt5)
    acct1 = _acct(mt5)
    mt5.shutdown()

    # reconcile
    valid_entry = [s for s in samples if s.get("valid_entry")]
    valid_exit = [s for s in samples if s.get("valid_exit")]
    reconciled = [s for s in samples if s.get("reconciliation") == "PASS"]
    profiles = _profiles(samples)
    registry = [{k: s.get(k) for k in
                 ("calibration_id", "order_id", "entry_deal_id", "exit_deal_id", "direction",
                  "hold_target_ms", "hold_actual_ms", "hold_actual_ms_tick_stamp",
                  "entry_fill_price", "exit_fill_price", "exit_bid", "exit_ask",
                  "tick_age_ms", "exit_tick_age_ms", "STALE_TICK_AT_REQUEST",
                  "entry_slippage_bps", "exit_slippage_bps", "commission", "swap",
                  "broker_gross_profit", "broker_realized_net", "reconciliation_residual",
                  "accounting_reconciliation", "price_unit_usd", "unit_status",
                  "gross_pnl_usd", "net_pnl", "net_pnl_status", "sample_hash")
                 } for s in samples]

    if halt_reason:
        status = "HALTED"
    elif not valid_entry or not valid_exit:
        status = "INCOMPLETE"
    elif all(s.get("reconciliation") == "PASS" for s in samples) and len(samples) >= 1:
        status = "PASS"
    else:
        status = "PARTIAL"

    pilot = {
        "schema": "v3_calibration_pilot/1",
        "task_id": "V3-HFT-CALIBRATION-PILOT-001",
        "started_utc": started, "finished_utc": timeutil.now_iso(),
        "status": status,
        "halt_reason": halt_reason,
        "MAX_CALIBRATION_ROUND_TRIPS": MAX_ROUND_TRIPS,
        "CALIBRATION_AUTO_STOP": len(samples) >= MAX_ROUND_TRIPS,
        "n_samples": len(samples),
        "VALID_ENTRY_FILL_SAMPLE": len(valid_entry),
        "VALID_EXIT_FILL_SAMPLE": len(valid_exit),
        "RECONCILIATION": "PASS" if samples and len(reconciled) == len(samples) else "PARTIAL",
        "frozen_sequence_hash": SEQ_HASH,
        "directions": list(DIRECTIONS), "holds_ms": list(HOLDS_MS),
        "volume": volume, "spec": spec,
        "account_before": acct0, "account_after": acct1,
        "V3_INITIAL_POSITIONS": len(pos0), "V3_FINAL_POSITIONS": len(pos1),
        "V3_CALIBRATION_OPEN_POSITIONS": len(pos1),
        "MOCK_EXECUTION": False,
        "net_pnl_formula_version": PNA.VERSION,
        "accounting": {"net_pnl_basis": "BROKER_REALIZED_ANCHORED_FILL_PRICE_REBUILD",
                       "spread_slippage_basis": "EMBEDDED_IN_FILL_PRICE_NOT_DEDUCTED",
                       "fees_sign": "BROKER_SIGNED (MT5 commission<0 == cost)",
                       "broker_realized_net_source": "MT5 history_deals_get (profit+commission+swap)",
                       "theoretical_net": "DIAGNOSTIC_ONLY (never reported as broker P&L)",
                       "formula_fix_task": "V3-HFT-CALIBRATION-FORMULA-FIX-001"},
        "labels": {"REAL_DATA": len([s for s in samples if s.get("real")]),
                   "MOCK_DATA": 0, "SYNTHETIC_DATA": 0},
        "NO_AUTO_RETRY": True,
        "safety": {"V3_AUTO_TRADING": False, "V3_LIVE": False, "V3_STRATEGY_AUTO_DECISION": False,
                   "V3_HERMES_AUTO_ORDER": False, "V3_MODEL_AUTO_ORDER": False,
                   "V1_UNTOUCHED": True, "V2_UNTOUCHED": True},
        "WAIT_FOR_AUDIT": True,
        "trade_source": TRADE_SOURCE,
        "slice": {"from_index": from_index, "n": n_roundtrips, "full_sequence": slice_full},
    }
    _write_state("V3_CALIBRATION_PILOT.json", pilot)
    _write_state("V3_EXECUTION_PROFILE.json", profiles)
    _write_state("V3_COST_PROFILE.json", _cost_profile(samples))
    reg_path = os.path.join(OUT, "registry.jsonl")
    with open(reg_path, "a", encoding="utf-8") as f:
        for r in registry:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    if slice_full:
        with open(done_marker, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": timeutil.now_iso(), "status": status, "n": len(samples)}))
    else:
        with open(slice_marker, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": timeutil.now_iso(), "status": status, "n": len(samples),
                                 "from_index": from_index, "to_index": from_index + n_roundtrips,
                                 "slices_do_not_complete_the_frozen_sequence": True}))

    out = {"pilot": pilot, "execution_profile": profiles,
           "cost_profile": _cost_profile(samples), "slippage_signs": _slippage_signs(samples)}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return out


def _cost_profile(samples):
    rows = []
    for s in samples:
        if s.get("net_pnl") is None:
            continue
        rows.append({
            "calibration_id": s.get("calibration_id"),
            "gross_pnl": s.get("gross_pnl"), "gross_pnl_usd": s.get("gross_pnl_usd"),
            "spread_price": s.get("spread_price"),
            "entry_slippage_price": s.get("entry_slippage_price"),
            "exit_slippage_price": s.get("exit_slippage_price"),
            "commission": s.get("commission"), "swap": s.get("swap"),
            "fees_usd": s.get("fees_usd"),
            "net_pnl": s.get("net_pnl"),
            "broker_realized_net": s.get("broker_realized_net"),
            "theoretical_net": s.get("theoretical_net"),
            "execution_friction": s.get("execution_friction"),
        })
    net = [r["net_pnl"] for r in rows]
    broker = [r["broker_realized_net"] for r in rows if r["broker_realized_net"] is not None]
    theo = [r["theoretical_net"] for r in rows if r["theoretical_net"] is not None]
    return {"n": len(rows), "round_trip_net_pnl": _stats(net), "rows": rows,
            "broker_realized_net": _stats(broker),
            "theoretical_net": _stats(theo),
            "net_pnl_basis": "BROKER_REALIZED_ANCHORED_FILL_PRICE_REBUILD",
            "net_pnl_formula_version": PNA.VERSION,
            "spread_slippage_basis": "EMBEDDED_IN_FILL_PRICE_NOT_DEDUCTED",
            "commission_source": "MT5 history_deals_get (UNKNOWN if absent)"}


def _market_open(mt5):
    t = mt5.symbol_info_tick(SYMBOL)
    import datetime as dt
    return bool(t and (dt.datetime.now(dt.timezone.utc).timestamp() - (t.time or 0)) < 120)


def _sample_hash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


def _wall_epoch_s(wall_ns):
    return None if wall_ns is None else wall_ns / 1e9


def _deal_time_offset_s(deal, wall_ns):
    """Broker deal stamp vs local wall clock (FXTM server = UTC+3 -> ~10800 s).

    Recorded for alignment only; the broker stamp is NEVER rewritten as UTC.
    """
    if deal is None or wall_ns is None:
        return None
    msc = getattr(deal, "time_msc", None)
    if msc:
        return round(msc / 1000.0 - _wall_epoch_s(wall_ns), 3)
    t = getattr(deal, "time", None)
    return None if not t else round(float(t) - _wall_epoch_s(wall_ns), 3)


def _tick_age_ms(tick):
    """Age of a quote in ms at read time (quote staleness observability)."""
    import datetime as dt
    if tick is None or not getattr(tick, "time", None):
        return None
    return round((dt.datetime.now(dt.timezone.utc).timestamp() - tick.time) * 1000.0, 3)


def _round_trip(mt5, i, volume, lg, spec=None):
    """One calibration round trip; accounting is broker-anchored (see PNA)."""
    if spec is None:
        spec = _spec(mt5)
    fill_mode = _filling_mode(mt5)
    cid = f"V3CAL-{i:02d}"
    hold_target = HOLDS_MS[i]
    direction = DIRECTIONS[i]
    t = mt5.symbol_info_tick(SYMBOL)
    if not t:
        raise Halt("no tick")
    bid, ask = t.bid, t.ask
    mid = (bid + ask) / 2.0
    spread = ask - bid
    import datetime as dt
    stale = (dt.datetime.now(dt.timezone.utc).timestamp() - (t.time or 0)) > 120
    tick_age_ms = _tick_age_ms(t)
    if bid <= 0 or ask <= 0 or ask < bid or spread < 0:
        raise Halt(f"bad quote {bid}/{ask}")

    is_long = direction == "LONG"
    sig = timeutil.mono_ns(); req = timeutil.mono_ns()
    order = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL,
        "price": ask if is_long else bid, "deviation": 20, "magic": MAGIC,
        "comment": f"CALIB-V3-{i:02d}", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": fill_mode,
    }
    lg.append("ORDER_REQUEST", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              price=order["price"], bid=bid, ask=ask, spread=spread)
    send = timeutil.mono_ns()
    r = mt5.order_send(order)
    ack = timeutil.mono_ns()
    lg.append("BROKER_RESPONSE", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              order_id=str(getattr(r, "order", "")) if r else None,
              price=getattr(r, "price", None))
    if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
        raise Halt(f"UNKNOWN entry retcode={getattr(r,'retcode',None)} (NO_AUTO_RETRY)")
    fill = timeutil.mono_ns()
    fill_price = r.price
    pos = _pos(mt5)
    if len(pos) != 1:
        raise Halt(f"unexpected positions after entry: {len(pos)}")
    pid = pos[0].ticket
    s = {"calibration_id": cid, "direction": direction, "real": True,
         "timestamp_signal": timeutil.utc_ns(), "bid_at_request": bid, "ask_at_request": ask,
         "mid_at_request": mid, "spread_price": spread,
         "spread_bps": (spread / mid * 1e4) if mid else None,
         "requested_price": order["price"], "fill_price": fill_price,
         "signal_to_request_ms": (req - sig) / 1e6, "request_to_ack_ms": (ack - req) / 1e6,
         "ack_to_fill_ms": (fill - ack) / 1e6, "signal_to_fill_ms": (fill - sig) / 1e6,
         "slippage_price": (fill_price - order["price"]) if is_long else (order["price"] - fill_price),
         "order_id": str(getattr(r, "order", "")),
         "STALE_TICK_AT_REQUEST": bool(stale), "hold_target_ms": hold_target,
         "tick_age_ms": tick_age_ms,
         "entry_bid": bid, "entry_ask": ask, "entry_tick_time_utc_epoch": t.time}
    # adverse-positive slippage is the SAME value under the compat key
    s["entry_slippage_price"] = s["slippage_price"]
    s["entry_slippage_bps"] = (s["slippage_price"] / mid * 1e4) if mid else None
    s["valid_entry"] = True
    lg.append("ENTRY_FILL", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              position_id=str(pid), price=fill_price, bid=bid, ask=ask, spread=spread,
              latency_ns=fill - sig)

    # hold then close (fixed, pre-registered)
    t0 = timeutil.mono_ns()
    time.sleep(hold_target / 1000.0)
    t2 = mt5.symbol_info_tick(SYMBOL)
    e_bid, e_ask = t2.bid, t2.ask
    e_mid = (e_bid + e_ask) / 2.0
    e_sig = timeutil.mono_ns()
    e_order = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": volume,
        "type": mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY,
        "position": pid, "price": e_bid if is_long else e_ask, "deviation": 20, "magic": MAGIC,
        "comment": f"CALIB-V3-X-{i:02d}", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": fill_mode,
    }
    lg.append("EXIT_REQUEST", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              position_id=str(pid), price=e_order["price"])
    e_send = timeutil.mono_ns()
    r2 = mt5.order_send(e_order)
    e_ack = timeutil.mono_ns()
    if r2 is None or r2.retcode != mt5.TRADE_RETCODE_DONE:
        raise Halt(f"UNKNOWN exit retcode={getattr(r2,'retcode',None)} (NO_AUTO_RETRY)")
    e_fill = timeutil.mono_ns()
    exit_price = r2.price
    s.update({
        "exit_requested_price": e_order["price"], "exit_bid": e_bid, "exit_ask": e_ask,
        "exit_mid": e_mid, "exit_fill_price": exit_price,
        "exit_slippage_price": (e_order["price"] - exit_price) if is_long else (exit_price - e_order["price"]),
        "exit_latency_ms": (e_fill - e_sig) / 1e6,
        "hold_actual_ms": (e_fill - t0) / 1e6,          # monotonic: accurate hold duration
        "hold_actual_ms_tick_stamp": (t2.time - t.time) * 1000 if (t2 and t) else None,
        "exit_tick_age_ms": _tick_age_ms(t2),
        "entry_fill_wall_ns": fill, "exit_fill_wall_ns": e_fill,
        "valid_exit": True,
    })
    s["exit_slippage_bps"] = (s["exit_slippage_price"] / e_mid * 1e4) if e_mid else None
    if s["hold_actual_ms"] is None or s["hold_actual_ms"] < hold_target * 0.5:
        s["CALIBRATION_HORIZON_LIMITATION"] = True
    lg.append("EXIT_FILL", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              position_id=str(pid), price=exit_price, latency_ns=e_fill - e_sig)

    # deals / commission / swap / broker facts / reconciliation
    deals = mt5.history_deals_get(position=pid) or []
    entry_deal = exit_deal = None
    for d in deals:
        if d.entry == mt5.DEAL_ENTRY_IN:
            entry_deal = d
        elif d.entry == mt5.DEAL_ENTRY_OUT:
            exit_deal = d
    comm = swap = broker_profit = None
    if deals:
        comm = sum(float(getattr(d, "commission", 0.0) or 0.0) for d in deals)
        swap = sum(float(getattr(d, "swap", 0.0) or 0.0) for d in deals)
        broker_profit = sum(float(getattr(d, "profit", 0.0) or 0.0) for d in deals)
    s["commission"] = comm          # None => UNKNOWN (never silently 0)
    s["swap"] = swap
    s["fee"] = None
    s["volume"] = volume
    s["entry_fill_price"] = fill_price
    s["broker_gross_profit"] = broker_profit
    s["entry_deal_id"] = getattr(entry_deal, "ticket", None)
    s["exit_deal_id"] = getattr(exit_deal, "ticket", None)
    s["broker_entry_deal_price"] = getattr(entry_deal, "price", None)
    s["broker_exit_deal_price"] = getattr(exit_deal, "price", None)
    s["entry_deal_time"] = getattr(entry_deal, "time", None)
    s["exit_deal_time"] = getattr(exit_deal, "time", None)
    s["entry_deal_time_msc"] = getattr(entry_deal, "time_msc", None)
    s["exit_deal_time_msc"] = getattr(exit_deal, "time_msc", None)
    s["entry_deal_time_offset_s"] = _deal_time_offset_s(entry_deal, fill)
    s["exit_deal_time_offset_s"] = _deal_time_offset_s(exit_deal, e_fill)

    # ---- V3-HFT-CALIBRATION-FORMULA-FIX-001: broker-anchored accounting ----
    # spread and slippage are ALREADY inside fill_price/exit_price; they are
    # reported as diagnostics and NEVER deducted a second time. Commission and
    # swap keep the broker sign (MT5 commission < 0 == a cost).
    acct = mt5.account_info()
    try:
        acc = PNA.round_trip_accounting(
            direction=direction, volume=volume,
            contract_size=spec.get("trade_contract_size"),
            tick_size=spec.get("trade_tick_size"), tick_value=spec.get("trade_tick_value"),
            entry_fill_price=fill_price, exit_fill_price=exit_price,
            entry_mid=mid, exit_mid=e_mid,
            entry_ref_price=order["price"], exit_ref_price=e_order["price"],
            entry_bid=bid, entry_ask=ask, exit_bid=e_bid, exit_ask=e_ask,
            commission=comm, swap=swap, broker_gross_profit=broker_profit,
            profit_currency=spec.get("currency_profit"),
            account_currency=getattr(acct, "currency", None))
    except ValueError as ve:
        raise Halt(f"ACCOUNTING_SPEC_GAP at {cid}: {ve} (NO_AUTO_RETRY)")
    s.update(acc)
    s["spread_cost"] = spread   # informational only: embedded in the fill price
    s["spread_cost_basis"] = "EMBEDDED_IN_FILL_PRICE_NOT_DEDUCTED"

    recon = (entry_deal is not None and exit_deal is not None and len(_pos(mt5)) == 0)
    s["reconciliation"] = "PASS" if recon else "FAIL"
    if recon and s.get("accounting_reconciliation") != "PASS":
        # unit / currency / fee rebuild does not match the broker's own books
        recon = False
        s["reconciliation"] = "FAIL"
        s["ACCOUNTING_RECONCILIATION_FAIL"] = {
            "residual": s.get("reconciliation_residual"),
            "unit_status": s.get("unit_status"),
            "net_pnl_status": s.get("net_pnl_status")}
    if not recon:
        # still record sample but reconciliation failure should stop the pilot
        s["sample_hash"] = _sample_hash(s)
        lg.append("CALIBRATION_COMPLETE", timeutil.utc_ns(), run_id="CALIB-PILOT-001",
                  decision_id=cid, pnl=s["net_pnl"])
        raise Halt(f"RECONCILIATION_FAIL at {cid}")
    s["sample_hash"] = _sample_hash(s)
    lg.append("CALIBRATION_COMPLETE", timeutil.utc_ns(), run_id="CALIB-PILOT-001", decision_id=cid,
              pnl=s["net_pnl"])
    # post-sample gates
    if len(_pos(mt5)) != 0:
        raise Halt("unexpected open position after round trip")
    return s


def preflight():
    import MetaTrader5 as mt5
    rep = {"name": "V3_CALIBRATION_PREFLIGHT", "ts": timeutil.now_iso(),
           "expected_login": EXPECTED_LOGIN, "expected_magic": MAGIC,
           "frozen_sequence_hash": SEQ_HASH, "MAX_CALIBRATION_ROUND_TRIPS": MAX_ROUND_TRIPS}
    rep["safety_flags"] = _flags()
    rep["AUTH_SOURCE"] = None  # filled after connect
    connected = _connect_v3(mt5)
    rep["AUTH_SOURCE"] = AUTH.get("source")
    acct = None
    if connected:
        ti = mt5.terminal_info()
        acct = _gacct(mt5)
        rep["v3"] = {"data_path": getattr(ti, "data_path", None), "login": acct.get("login"),
                     "server": acct.get("server"), "balance": acct.get("balance"),
                     "positions": acct.get("positions"), "spec": _spec(mt5)}
        market = _market_open(mt5)
        mt5.shutdown()
    else:
        rep["v3"] = {"ok": False, "error": mt5.last_error()}
        market = False
    g = hard_gates(acct=acct, market=market)
    rep["gates"] = g
    rep["MARKET_OPEN"] = market
    fails = [k for k, v in g.items() if not v]
    rep["HARD_GATES_ALL_PASS"] = (len(fails) == 0)
    rep["FAILED_GATES"] = fails
    rep["READY_TO_START"] = rep["HARD_GATES_ALL_PASS"]
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--n", type=int, default=MAX_ROUND_TRIPS)
    ap.add_argument("--from-index", type=int, default=0,
                    help="start at this index of the FROZEN sequence (default 0); slicing never alters the sequence")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(0 if selftest() else 1)
    elif a.preflight:
        preflight()
    elif a.run:
        run(a.n, from_index=a.from_index)
    else:
        ap.print_help()
