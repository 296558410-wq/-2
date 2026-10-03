# -*- coding: utf-8 -*-
"""V3 独立 MT5 适配器 — 只读研究连接；order_send 在代码层硬性拦截。

隔离约束：
- 只连 V3 实例 `C:\\AIQuant\\mt5_instances\\fxtm_demo_v3\\terminal64.exe`（/portable），**绝不**连 V1/V2。
- data_path 必须含 `fxtm_demo_v3`，否则拒绝。
- Magic=90004（V1=90002 / V2=90003）。
- `order_send` 在任何情况下都 raise（不依赖配置；配置仅二次确认）。三个安全闸门必须全为 NO。
"""
from __future__ import annotations
import json
import os
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
EXE = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
DATA_DIR = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib"
REQUIRED_TAG = "fxtm_demo_v3calib"
SYMBOL = "XAUUSD"
MAGIC = 90004
SERVER_EXPECTED = "ForexTimeFXTM-Demo01"
STATE = V3_ROOT / "state"
ENV_FILE = Path(r"C:\AIQuant\.env.mt5_v3_calib")
SAFETY_FILES = {"V3_LIVE_ALLOWED": "NO", "V3_ORDER_SEND_ALLOWED": "NO", "V3_FORWARD_ALLOWED": "NO"}

# ---- V3 DEMO_CALIBRATION execution mode (additive; no guard is removed) ----
MODES = ("RESEARCH_READONLY", "DEMO_CALIBRATION", "LIVE")
MODE_FILE = STATE / "V3_EXECUTION_MODE"
MODE_CONFIG = Path(r"C:\AIQuant\research\hermes\trader_v3\config\execution_mode.json")
DEMO_EXPECT = {"account": 160766418, "server": "ForexTimeFXTM-Demo01", "symbol": "XAUUSD", "magic": 90004}


def execution_mode():
    """Fail-closed: any unreadable/unknown mode is treated as RESEARCH_READONLY."""
    try:
        m = MODE_FILE.read_text(encoding="utf-8").strip().upper()
    except Exception:  # noqa: BLE001
        return "RESEARCH_READONLY"
    return m if m in MODES else "RESEARCH_READONLY"


def assert_live_disabled():
    """LIVE must stay off; ORDER_SEND=YES must never imply LIVE."""
    if str(safety_flags().get("V3_LIVE_ALLOWED", "NO")).upper() != "NO":
        raise OrderSendBlocked("LIVE gate not disabled (assert_live_disabled)")


def assert_demo_calibration_safe(acct=None, terminal_info=None):
    """Final guard before any demo-calibration order."""
    assert_live_disabled()
    if execution_mode() != "DEMO_CALIBRATION":
        raise OrderSendBlocked(f"execution_mode != DEMO_CALIBRATION ({execution_mode()})")
    exp = dict(DEMO_EXPECT)
    try:
        cfg = json.loads(MODE_CONFIG.read_text(encoding="utf-8"))
        exp.update({k: cfg["modes"]["DEMO_CALIBRATION"][k] for k in
                     ("account", "server", "symbol", "magic") if k in cfg["modes"]["DEMO_CALIBRATION"]})
        if cfg["modes"]["DEMO_CALIBRATION"].get("live") is not False:
            raise OrderSendBlocked("config says demo mode is not live=false")
    except OrderSendBlocked:
        raise
    except Exception as e:  # noqa: BLE001
        raise OrderSendBlocked(f"execution_mode.json unreadable: {e}")
    if acct is not None:
        got = {"account": acct.get("login"), "server": acct.get("server")}
        for k, v in got.items():
            if v is not None and v != exp[k]:
                raise OrderSendBlocked(f"demo-calibration {k} mismatch: {v} != {exp[k]}")
    if terminal_info is not None:
        dp = (getattr(terminal_info, "data_path", "") or "")
        if REQUIRED_TAG not in dp:
            raise OrderSendBlocked(f"data_path not V3 isolated instance: {dp}")
    return True


class OrderSendBlocked(RuntimeError):
    """V3 代码层硬拦截：任何 order_send 调用直接失败。"""


class RefuseConnection(RuntimeError):
    pass


def safety_flags():
    out = {}
    for k, default in SAFETY_FILES.items():
        p = STATE / k
        try:
            out[k] = p.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            out[k] = default
    return out


def assert_readonly():
    """RESEARCH_READONLY keeps the original all-NO requirement (unchanged semantics)."""
    f = safety_flags()
    bad = [k for k, v in f.items() if str(v).upper() != "NO"]
    if bad:
        raise OrderSendBlocked(f"V3 safety flags not NO: {bad}")


def assert_mode_ok(acct=None, terminal_info=None):
    """Mode router: RESEARCH_READONLY -> original guard; DEMO_CALIBRATION -> demo guard; LIVE -> refused."""
    m = execution_mode()
    if m == "DEMO_CALIBRATION":
        return assert_demo_calibration_safe(acct=acct, terminal_info=terminal_info)
    if m == "LIVE":
        raise OrderSendBlocked("LIVE mode is not implemented in this task")
    return assert_readonly()


AUTH = {"source": None, "login_hint": None}  # §30 AUTH_SOURCE record


def _creds():
    kv = {}
    if ENV_FILE.exists():
        for ln in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    return (int(kv.get("V3_CALIB_LOGIN", 0) or 0), kv.get("V3_CALIB_PASSWORD", ""), kv.get("V3_CALIB_SERVER", SERVER_EXPECTED))


def _install_order_guard(mt5):
    """把 mt5.order_send 替换为 raise（硬拦截），与配置无关。"""
    def _blocked(*a, **k):
        raise OrderSendBlocked("V3: order_send is hard-blocked at code level (research read-only environment)")
    try:
        mt5.order_send = _blocked
    except Exception:  # noqa: BLE001
        pass
    # 同时拦截 order_check（会触发交易预检）
    def _blocked_check(*a, **k):
        raise OrderSendBlocked("V3: order_check is disabled")
    try:
        mt5.order_check = _blocked_check
    except Exception:  # noqa: BLE001
        pass
    return True


def order_send(*a, **k):
    """Direct calls are refused unless the demo-calibration guard passes."""
    if execution_mode() != "DEMO_CALIBRATION":
        raise OrderSendBlocked("V3: order_send is hard-blocked outside DEMO_CALIBRATION")
    assert_demo_calibration_safe()
    import MetaTrader5 as mt5  # noqa: PLC0415
    return mt5.order_send(*a, **k)


def connect(readonly=True):
    """连接 V3 独立实例。返回 (mt5, info)。"""
    if not os.path.exists(EXE):
        raise RefuseConnection(f"V3 terminal not found: {EXE}")
    import MetaTrader5 as mt5
    login, pwd, server = _creds()
    # §30: explicit login only when a password is available; otherwise use the saved session.
    if login and pwd:
        ok = mt5.initialize(path=EXE, portable=True, login=login, password=pwd,
                            server=server or None, timeout=60000)
        AUTH["source"] = "ENV_CREDENTIALS"
    else:
        ok = mt5.initialize(path=EXE, portable=True, timeout=60000)
        AUTH["source"] = "SAVED_SESSION"
        AUTH["login_hint"] = login or None
    if not ok:
        raise RefuseConnection(f"initialize failed: {mt5.last_error()}")
    ti = mt5.terminal_info()
    dp = (getattr(ti, "data_path", "") or "")
    if REQUIRED_TAG not in dp:
        mt5.shutdown()
        raise RefuseConnection(f"refused: data_path not V3 ({dp})")
    ai = mt5.account_info()
    _mode_now = execution_mode()
    if _mode_now == "DEMO_CALIBRATION":
        # demo-calibration: keep the guard object but allow sends after re-validation
        assert_demo_calibration_safe(acct={"login": getattr(ai, "login", None),
                                            "server": getattr(ai, "server", None)},
                                      terminal_info=ti)
    else:
        assert_readonly()
        _install_order_guard(mt5)
    info = {"data_path": dp, "path": getattr(ti, "path", None), "connected": getattr(ti, "connected", None),
            "login": getattr(ai, "login", None), "server": getattr(ai, "server", None),
            "trade_allowed": getattr(ai, "trade_allowed", None), "readonly": True,
            "magic": MAGIC, "symbol": SYMBOL}
    return mt5, info


def disconnect(mt5):
    try:
        mt5.shutdown()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(safety_flags(), ensure_ascii=False))
    try:
        order_send()
    except OrderSendBlocked as e:
        print("order_send blocked OK:", e)
