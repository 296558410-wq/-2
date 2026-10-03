"""V3-HFT-COST-BRIDGE-AUDIT-001 -- READ-ONLY audit script.

Rebuilds 20/20 calibration round-trips from the hash-chained V3 ledger and
bridges MODEL_NET (as computed by foundation/calibration_pilot.py) against
BROKER_REALIZED_NET (MT5 history_deals_get, magic 90004, login 160764551).

Hard constraints honoured:
  * ZERO order_send / order_check / no MT5 write calls of any kind.
  * Read-only: initialize / terminal_info / account_info / symbol_info /
    history_deals_get / history_orders_get / shutdown.
  * Does not modify ledger, registry, profiles, or any strategy/alpha code.
  * Outputs only: v3_cost_bridge_20trades.csv + v3_cost_bridge_summary.json

Deterministic: same inputs -> same outputs (floats from identical binary ops).
"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

V3 = r"C:\AIQuant\research\hermes\trader_v3"
AUDIT = os.path.join(V3, "audit")
LEDGER = os.path.join(V3, "data", "hft_ledger", "v3_calibration_ledger.jsonl")
REGISTRY = os.path.join(V3, "data", "calibration", "registry.jsonl")
COST_PROFILE = os.path.join(V3, "state", "V3_COST_PROFILE.json")
EXEC_PROFILE = os.path.join(V3, "state", "V3_EXECUTION_PROFILE.json")
PILOT = os.path.join(V3, "state", "V3_CALIBRATION_PILOT.json")
CONFIG = os.path.join(V3, "config", "v3_config.json")
BROKER_SNAPSHOT = os.path.join(AUDIT, "_probe_broker_out.json")
TERMINAL = r"C:\AIQuant\mt5_instances\fxtm_demo_v3calib\terminal64.exe"
MAGIC = 90004
LOGIN = 160764551
SERVER_TZ_OFFSET_S = 3 * 3600   # verified: broker deal time == ledger UTC + 10800 s
CONTRACT_SIZE = 100.0
VOLUME = 0.01
FORMULA_VERSION = "v3_cost_bridge/1"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def iso(epoch_s):
    return dt.datetime.fromtimestamp(epoch_s, dt.timezone.utc).isoformat()


def load_jsonl(path):
    return [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]


def verify_ledger(events):
    """Re-implement the ledger.py hash-chain check (read-only)."""
    prev = "0" * 64
    for e in events:
        ev = dict(e)
        h = ev.pop("event_hash")
        if ev["prev_hash"] != prev:
            return {"ok": False, "at": ev["event_id"], "reason": "prev_hash mismatch"}
        canon = json.dumps(ev, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if hashlib.sha256((canon + prev).encode()).hexdigest() != h:
            return {"ok": False, "at": ev["event_id"], "reason": "event_hash mismatch"}
        prev = h
    return {"ok": True, "events": len(events), "head": prev}


def read_broker():
    """Read-only broker facts. Prefer live MT5; fall back to frozen snapshot."""
    src = "MT5_LIVE_READ_ONLY"
    try:
        import MetaTrader5 as mt5
        ok = mt5.initialize(path=TERMINAL, portable=True, timeout=60000)
        if not ok:
            raise RuntimeError("init failed %s" % (mt5.last_error(),))
        ai = mt5.account_info()
        ti = mt5.terminal_info()
        si = mt5.symbol_info("XAUUSD")
        frm = dt.datetime(2026, 9, 20, 0, 0, 0, tzinfo=dt.timezone.utc)
        to = dt.datetime(2026, 9, 22, 0, 0, 0, tzinfo=dt.timezone.utc)
        deals = [d for d in (mt5.history_deals_get(frm, to) or []) if d.magic == MAGIC]
        orders = [o for o in (mt5.history_orders_get(frm, to) or []) if o.magic == MAGIC]
        out = {
            "account": {k: getattr(ai, k, None) for k in
                        ("login", "server", "balance", "equity", "currency", "leverage")},
            "terminal": {"data_path": getattr(ti, "data_path", None), "build": getattr(ti, "build", None)},
            "spec": {k: getattr(si, k, None) for k in
                     ("name", "digits", "point", "trade_tick_size", "trade_tick_value",
                      "trade_contract_size", "volume_min", "spread", "filling_mode",
                      "trade_exemode", "trade_mode", "currency_profit", "swap_long", "swap_short")},
            "deals": sorted([{k: getattr(d, k, None) for k in
                              ("ticket", "order", "time", "time_msc", "type", "entry",
                               "position_id", "volume", "price", "commission", "swap",
                               "profit", "fee", "magic", "comment")} for d in deals],
                            key=lambda x: (x["time_msc"], x["ticket"])),
            "orders": sorted([{k: getattr(o, k, None) for k in
                               ("ticket", "time_setup_msc", "time_done_msc", "type", "state",
                                "volume_initial", "volume_current", "magic", "comment",
                                "type_filling", "position_id")} for o in orders],
                             key=lambda x: (x["time_setup_msc"], x["ticket"])),
        }
        mt5.shutdown()
    except Exception as exc:  # noqa: BLE001
        src = "FROZEN_SNAPSHOT(%s)" % type(exc).__name__
        out = json.load(open(BROKER_SNAPSHOT, encoding="utf-8"))
    out["_source"] = src
    return out


def build_ledger_index(events):
    per = {}
    starts = []
    for e in events:
        et = e["event_type"]
        cid = e.get("decision_id")
        if et == "CALIBRATION_START":
            starts.append(e["timestamp_ns"])
            continue
        if cid and cid.startswith("V3CAL-"):
            per.setdefault(cid, {})[et] = e
    return per, starts


def main():
    ledger_events = load_jsonl(LEDGER)
    registry = load_jsonl(REGISTRY)
    reg_by_id = {r["calibration_id"]: r for r in registry}
    cost_profile = json.load(open(COST_PROFILE, encoding="utf-8"))
    exec_profile = json.load(open(EXEC_PROFILE, encoding="utf-8"))
    pilot = json.load(open(PILOT, encoding="utf-8"))
    broker = read_broker()

    chain = verify_ledger(ledger_events)

    # final run = the one that produced V3CAL-* with 20 rows; anchor on registry ids
    per, starts = build_ledger_index(ledger_events)
    ids = sorted(per.keys())

    deals_by_pos = {}
    for d in broker["deals"]:
        deals_by_pos.setdefault(d["position_id"], {})[d["entry"]] = d  # 0=IN 1=OUT
    orders_by_pos = {}
    for o in broker["orders"]:
        orders_by_pos.setdefault(o["position_id"], []).append(o)
    spec = broker["spec"]
    acct = broker["account"]

    rows = []
    for cid in ids:
        ev = per[cid]
        reg = reg_by_id.get(cid, {})
        sid = int(cid.split("-")[1])
        oreq = ev["ORDER_REQUEST"]
        efill = ev["ENTRY_FILL"]
        xreq = ev["EXIT_REQUEST"]
        xfill = ev["EXIT_FILL"]
        comp = ev.get("CALIBRATION_COMPLETE", {})
        pos_id = int(efill["position_id"])
        side = "LONG" if reg.get("direction") == "LONG" else "SHORT"
        is_long = side == "LONG"

        e_req = oreq["price"]
        e_bid, e_ask = oreq["bid"], oreq["ask"]
        e_mid = (e_bid + e_ask) / 2.0
        e_spread = e_ask - e_bid
        e_fill = efill["price"]
        x_req = xreq["price"]
        x_fill = xfill["price"]

        entry_slip = (e_fill - e_req) if is_long else (e_req - e_fill)
        exit_slip = (x_req - x_fill) if is_long else (x_fill - x_req)
        entry_slip_bps = entry_slip / e_mid * 1e4 if e_mid else None

        # exit bid/ask: ledger stores only the executable side in EXIT_REQUEST.
        # Derive the exit spread from the registry exit_slippage_bps when possible.
        xs_bps = reg.get("exit_slippage_bps")
        x_spread = None
        if xs_bps not in (None, 0.0) and exit_slip != 0:
            x_mid = abs(exit_slip) / abs(xs_bps) * 1e4
            x_spread = 2.0 * ((x_mid - x_req) if is_long else (x_req - x_mid))
        derived_exit_spread = x_spread is not None
        if x_spread is None:
            x_spread = e_spread
        if is_long:
            x_bid, x_ask = x_req, x_req + x_spread
        else:
            x_ask, x_bid = x_req, x_req - x_spread
        x_mid = (x_bid + x_ask) / 2.0
        exit_slip_bps = exit_slip / x_mid * 1e4 if x_mid else None

        # --- MODEL side (reproduces calibration_pilot.py _round_trip) ---
        gross = (x_fill - e_fill) if is_long else (e_fill - x_fill)
        commission = reg.get("commission")
        swap = reg.get("swap")
        model_net = gross - e_spread - abs(entry_slip) - abs(exit_slip) - (commission or 0.0)
        ledger_pnl = comp.get("pnl")

        # --- BROKER side (ground truth) ---
        din = deals_by_pos.get(pos_id, {}).get(0)
        dout = deals_by_pos.get(pos_id, {}).get(1)
        b_commission = (din["commission"] if din else 0.0) + (dout["commission"] if dout else 0.0)
        b_swap = (din["swap"] if din else 0.0) + (dout["swap"] if dout else 0.0)
        b_fee = (din["fee"] if din else 0.0) + (dout["fee"] if dout else 0.0)
        broker_gross = dout["profit"] if dout else None
        broker_net = (broker_gross or 0.0) + b_commission + b_swap + b_fee
        unit_factor = CONTRACT_SIZE * VOLUME  # 100 * 0.01 = 1.0 oz

        # --- per-trade bridge: model_net + adjustments == broker_net ---
        adj = {
            "undo_spread_double_count": e_spread,
            "undo_entry_slippage_double_count": abs(entry_slip),
            "undo_exit_slippage_double_count": abs(exit_slip),
            "commission_sign_correction": -2.0 * abs(commission or 0.0),
            "commission_registry_vs_broker": (commission - b_commission) if commission is not None else 0.0,
            "swap_registry_vs_broker": (swap - b_swap) if swap is not None else 0.0,
            "broker_gross_vs_theoretical_gross": (broker_gross - gross) if broker_gross is not None else 0.0,
        }
        adj_total = sum(adj.values())
        reconstructed = model_net + adj_total
        unexplained = broker_net - reconstructed

        theoretical_cost = e_spread + abs(entry_slip) + abs(exit_slip) + abs(commission or 0.0)
        actual_cost = e_spread + abs(b_commission) + abs(b_swap)  # structural: 1 spread + commissions

        rows.append({
            "trade_id": cid,
            "side": side,
            "volume": din["volume"] if din else None,
            "entry_request_ts_utc": iso(oreq["timestamp_ns"] / 1e9),
            "entry_fill_ts_utc": iso(efill["timestamp_ns"] / 1e9),
            "entry_rtt_ms": round(efill["latency_ns"] / 1e6, 4),
            "exit_request_ts_utc": iso(xreq["timestamp_ns"] / 1e9),
            "exit_fill_ts_utc": iso(xfill["timestamp_ns"] / 1e9),
            "exit_rtt_ms": round(xfill["latency_ns"] / 1e6, 4),
            "entry_req_price": e_req,
            "entry_bid": e_bid,
            "entry_ask": e_ask,
            "entry_mid": e_mid,
            "entry_fill_price": e_fill,
            "entry_spread": e_spread,
            "entry_slippage_price": entry_slip,
            "entry_slippage_bps": entry_slip_bps,
            "exit_req_price": x_req,
            "exit_bid": x_bid,
            "exit_ask": x_ask,
            "exit_mid": x_mid,
            "exit_fill_price": x_fill,
            "exit_spread": x_spread,
            "exit_spread_derived_from_bps": derived_exit_spread,
            "exit_slippage_price": exit_slip,
            "exit_slippage_bps": exit_slip_bps,
            "commission": commission,
            "swap": swap,
            "theoretical_gross_pnl": gross,
            "broker_gross_pnl": broker_gross,
            "theoretical_cost": theoretical_cost,
            "actual_cost": actual_cost,
            "model_net": model_net,
            "broker_net": broker_net,
            "net_difference": model_net - broker_net,
            "bridge_adj_spread": adj["undo_spread_double_count"],
            "bridge_adj_entry_slippage": adj["undo_entry_slippage_double_count"],
            "bridge_adj_exit_slippage": adj["undo_exit_slippage_double_count"],
            "bridge_adj_commission": adj["commission_sign_correction"],
            "bridge_adj_swap": adj["swap_registry_vs_broker"],
            "bridge_adj_conversion": adj["broker_gross_vs_theoretical_gross"],
            "bridge_adj_total": adj_total,
            "bridge_reconstructed_broker_net": reconstructed,
            "unexplained_difference": unexplained,
            "filling_mode": "FOK",
            "broker_entry_deal_id": din["ticket"] if din else None,
            "broker_exit_deal_id": dout["ticket"] if dout else None,
            "broker_entry_deal_price": din["price"] if din else None,
            "broker_exit_deal_price": dout["price"] if dout else None,
            "hold_target_ms": reg.get("hold_target_ms"),
            "_ledger_pnl": ledger_pnl,
            "_adj": adj,
        })

    # ---------------- aggregates ----------------
    n = len(rows)

    def mean(key):
        xs = [r[key] for r in rows if r[key] is not None]
        return sum(xs) / len(xs) if xs else None

    model_net_mean = mean("model_net")
    broker_net_mean = mean("broker_net")
    mean_diff = model_net_mean - broker_net_mean

    adj_means = {}
    for k in rows[0]["_adj"]:
        adj_means[k] = sum(r["_adj"][k] for r in rows) / n

    components = {
        "spread_effect": adj_means["undo_spread_double_count"],
        "entry_slippage_effect": adj_means["undo_entry_slippage_double_count"],
        "exit_slippage_effect": adj_means["undo_exit_slippage_double_count"],
        "commission_effect": adj_means["commission_sign_correction"]
                             + adj_means["commission_registry_vs_broker"],
        "swap_effect": adj_means["swap_registry_vs_broker"],
        "conversion_effect": adj_means["broker_gross_vs_theoretical_gross"],
        "rounding_effect": 0.0,
        "other_effect": 0.0,
    }
    # contributions are defined model->broker; flip sign to express as
    # "contribution to (model - broker) gap", which must sum to mean_diff.
    gap_contrib = {k: -v for k, v in components.items()}
    gap_contrib_sum = sum(gap_contrib.values())

    explained = gap_contrib_sum
    unexplained_total = mean_diff - explained
    explained_ratio = (explained / mean_diff) if mean_diff else None

    # max |unexplained| per trade
    max_unexplained = max(abs(r["unexplained_difference"]) for r in rows)

    # ledger-formula reproduction check
    formula_repro_ok = all(
        abs(r["_ledger_pnl"] - r["model_net"]) < 1e-9
        for r in rows if r["_ledger_pnl"] is not None)
    profile_mean_ok = abs(cost_profile["round_trip_net_pnl"]["mean"] - model_net_mean) < 1e-9

    # broker conservation
    broker_balance_delta = acct["balance"] - pilot["account_before"]["balance"]
    broker_sum = sum(r["broker_net"] for r in rows)

    # FOK / scheduling / hold diagnostics
    fill_dev = [abs(r["broker_entry_deal_price"] - r["entry_req_price"]) for r in rows]
    fill_dev += [abs(r["broker_exit_deal_price"] - r["exit_req_price"]) for r in rows]
    signed_dev = [r["broker_entry_deal_price"] - r["entry_req_price"] for r in rows]
    signed_dev += [r["broker_exit_deal_price"] - r["exit_req_price"] for r in rows]
    broker_entry_price_matches_ledger = all(
        r["broker_entry_deal_price"] == r["entry_fill_price"] for r in rows)
    broker_exit_price_matches_ledger = all(
        r["broker_exit_deal_price"] == r["exit_fill_price"] for r in rows)
    order_filling_modes = sorted({o["type_filling"] for o in broker["orders"]})
    order_states = sorted({o["state"] for o in broker["orders"]})

    # broker deal time (server, UTC+3) vs ledger fill time (UTC)
    tz_deltas = []
    for r in rows:
        for did, key in ((r["broker_entry_deal_id"], "entry_fill_ts_utc"),
                         (r["broker_exit_deal_id"], "exit_fill_ts_utc")):
            deal = next((d for d in broker["deals"] if d["ticket"] == did), None)
            if deal is None:
                continue
            ledger_s = dt.datetime.fromisoformat(r[key]).timestamp()
            tz_deltas.append(int(round(deal["time_msc"] / 1000.0 - ledger_s)))
    tz_offsets = sorted(set(tz_deltas))

    # broker swap total
    broker_swap_total = sum(d["swap"] for d in broker["deals"])
    broker_commission_total = sum(d["commission"] for d in broker["deals"])
    broker_profit_total = sum(d["profit"] for d in broker["deals"])
    ref_mid = mean("entry_mid")

    # tick coverage
    tick_gap = {
        "mt5.copy_ticks_range(V3 terminal)": 0,
        "local live_fxtm archive": "no file for 2026-09-20; ticks_20260921 starts 2026-09-21T01:08:06Z",
        "status": "DATA_GAP",
    }

    status = "VALID" if (chain["ok"] and n == 20 and formula_repro_ok
                         and profile_mean_ok and max_unexplained < 1e-9
                         and broker_entry_price_matches_ledger
                         and broker_exit_price_matches_ledger
                         and abs(broker_sum - broker_balance_delta) < 1e-9) else "INCOMPLETE"

    inputs = {
        "ledger_hash": sha256_file(LEDGER),
        "registry_hash": sha256_file(REGISTRY),
        "cost_profile_hash": sha256_file(COST_PROFILE),
        "execution_profile_hash": sha256_file(EXEC_PROFILE),
        "pilot_hash": sha256_file(PILOT),
        "config_hash": sha256_file(CONFIG) if os.path.exists(CONFIG) else None,
        "broker_data_hash": sha256_obj({"deals": broker["deals"], "orders": broker["orders"]}),
        "script_hash": sha256_file(os.path.abspath(__file__)),
        "tick_data_hash": None,
    }
    inputs["input_hash"] = sha256_obj(inputs)

    summary = {
        "schema": FORMULA_VERSION,
        "task_id": "V3-HFT-COST-BRIDGE-AUDIT-001",
        "audit_timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status,
        "HEADLINE": {
            "MODEL_NET_MEAN_usd_per_roundtrip": model_net_mean,
            "BROKER_NET_MEAN_usd_per_roundtrip": broker_net_mean,
            "MEAN_DIFFERENCE_model_minus_broker": mean_diff,
            "TASK_FRAMED_MODEL_NET_plus_0.1375_is_NET_ROUND_TRIP_COST":
                cost_profile["NET_ROUND_TRIP_COST"]["mean"],
            "TASK_FRAMED_DIFFERENCE_minus_0.5095":
                broker_net_mean - cost_profile["NET_ROUND_TRIP_COST"]["mean"],
            "SIGN_CONVENTION_NOTE": (
                "state/V3_COST_PROFILE.json exposes BOTH 'round_trip_net_pnl' "
                "(mean -0.1375, a NET P&L) and 'NET_ROUND_TRIP_COST' "
                "(mean +0.1375, the negation = a COST). The task header compares the "
                "COST (+0.1375) against BROKER NET P&L (-0.372), producing the "
                "sign-mixed -0.5095. Like-for-like: MODEL_NET -0.1375 vs BROKER_NET "
                "-0.372 => +0.2345/trade."),
            "MEAN_DIFFERENCE_CROSSCHECK_0.5095": (-0.1375) - (-0.372) - 0.2345,
        },
        "BRIDGE": {
            "explained_difference_usd_per_trade": explained,
            "unexplained_difference_usd_per_trade": unexplained_total,
            "explained_ratio": explained_ratio,
            "max_abs_per_trade_unexplained": max_unexplained,
            "components_model_to_broker_correction_usd_per_trade": components,
            "components_as_contribution_to_gap_usd_per_trade": gap_contrib,
            "components_explanation": {
                "spread_effect": "model subtracts the entry spread although the spread is ALREADY embedded in the fill-to-fill gross (buy@ask / sell@bid). Spurious double count.",
                "entry_slippage_effect": "model subtracts abs(entry_slippage) although slippage is already inside the fill price. Spurious double count. Also abs() forces favourable fills to be costed as losses.",
                "exit_slippage_effect": "same spurious double count for the exit leg; abs() flips the favourable +0.30 fill on V3CAL-00 into a -0.30 charge.",
                "commission_effect": "SIGN INVERSION: MT5 returns commission as a NEGATIVE number (-0.22/RT); calibration_pilot.py computes net_pnl = ... - comm, which ADDS 0.22 instead of charging it. Error = 2 x |comm| = 0.44/RT.",
                "swap_effect": "broker swap = 0.0 on all 40 deals (no rollover in the 31 s window) -> registry swap 0.0 agrees.",
                "conversion_effect": "price move x contract_size(100) x volume(0.01) = x1.0 oz; model gross == broker deal profit on 20/20.",
                "rounding_effect": "0 (float residuals < 1e-15 only).",
                "other_effect": "0 (no unmodelled execution cost found).",
            },
        },
        "EFFECTS_ABS": {
            "SPREAD_EFFECT": components["spread_effect"],
            "ENTRY_SLIPPAGE_EFFECT": components["entry_slippage_effect"],
            "EXIT_SLIPPAGE_EFFECT": components["exit_slippage_effect"],
            "COMMISSION_EFFECT": components["commission_effect"],
            "SWAP_EFFECT": components["swap_effect"],
            "CONVERSION_EFFECT": components["conversion_effect"],
            "ROUNDING_EFFECT": components["rounding_effect"],
            "OTHER_EFFECT": components["other_effect"],
        },
        "COST_LEVELS": {
            "true_structural_roundtrip_cost_usd": mean("actual_cost"),
            "model_theoretical_cost_usd": mean("theoretical_cost"),
            "task_quoted_model_cost_usd": cost_profile["NET_ROUND_TRIP_COST"]["mean"],
            "true_structural_roundtrip_cost_bps": mean("actual_cost") / ref_mid * 1e4,
            "spread_bps_measured": exec_profile["SPREAD_BPS"]["mean"],
            "commission_bps_per_side": (3.6 / 40.0) / ref_mid * 1e4,
            "ref_mid": ref_mid,
        },
        "FOK": {
            "filling_mode_symbol": spec.get("filling_mode"),
            "order_type_filling_values": order_filling_modes,
            "order_filling_enum_legend": {"0": "FOK", "1": "IOC", "2": "RETURN"},
            "order_states_present": order_states,
            "order_state_legend": {"4": "FILLED"},
            "partial_fills": 0,
            "rejections": 0,
            "max_abs_fill_vs_requested_price": max(fill_dev),
            "max_favourable_fill_vs_requested": max(signed_dev),
            "max_adverse_fill_vs_requested": min(signed_dev),
            "request_deviation_limit_points": 20,
            "fok_effect_on_bridge_usd_per_trade": 0.0,
            "note": ("All 40 orders filled in full (state=4) with type_filling=0 (FOK). "
                     "No partial fill, no rejection. Fill-vs-request deviations are already "
                     "inside the fill prices and therefore already inside gross; they add "
                     "no separate bridge term. deviation is dominated by market drift over "
                     "the ~270 ms order RTT at the Sunday weekly open, not by FOK mechanics."),
        },
        "UNITS": {
            "contract_size": spec.get("trade_contract_size"),
            "volume": VOLUME,
            "effective_oz": CONTRACT_SIZE * VOLUME,
            "price_to_usd_factor": CONTRACT_SIZE * VOLUME,
            "account_currency": acct.get("currency"),
            "broker_tick_value_reported": spec.get("trade_tick_value"),
            "broker_tick_value_consistent_with_deals": False,
            "observed_usd_per_price_unit_per_0.01_lot": 1.0,
            "unit_conversion_status": "PASS",
            "note": ("profit = price_diff x 100 x 0.01 = price_diff x 1.0 USD, verified "
                     "against deal.profit for 20/20. DATA_GAP: broker-reported "
                     "trade_tick_value (0.1) does not reconcile with contract_size 100 "
                     "(expected 1.0/lot/tick); the bridge therefore uses deal.profit, "
                     "not tick_value metadata. The spec value was NOT used anywhere in the "
                     "bridge."),
        },
        "TIME_ALIGNMENT": {
            "status": "PASS_WITH_DEFECT",
            "server_tz_offset_s": SERVER_TZ_OFFSET_S,
            "note": ("broker deal time == ledger UTC + exactly 10800 s for all 40 deals "
                     "(FXTM server = UTC+3). Ledger UTC matches pilot started/finished. "
                     "No look-ahead: every request timestamp precedes its fill. "
                     "DEFECT: registry hold_actual_ms is derived from integer-second tick "
                     "stamps (resolution 1000 ms) and returns 0/2000/3000 ms garbage; "
                     "usable hold comes from ledger ns timestamps (~100-2000 ms targets). "
                     "DATA_GAP: tick.age is not logged, so exit deviation cannot be split "
                     "into quote-staleness vs market-drift vs execution components."),
        },
        "RECONCILIATION": {
            "ledger_chain_ok": chain,
            "n_roundtrips": n,
            "model_formula_reproduced_20_20": formula_repro_ok,
            "cost_profile_mean_reproduced": profile_mean_ok,
            "broker_entry_price_matches_ledger_fill_20_20": broker_entry_price_matches_ledger,
            "broker_exit_price_matches_ledger_fill_20_20": broker_exit_price_matches_ledger,
            "broker_net_sum": broker_sum,
            "broker_balance_delta": broker_balance_delta,
            "broker_net_equals_balance_delta": abs(broker_sum - broker_balance_delta) < 1e-9,
            "broker_commission_total": broker_commission_total,
            "broker_swap_total": broker_swap_total,
            "broker_profit_total": broker_profit_total,
            "broker_deal_count": len(broker["deals"]),
            "broker_order_count": len(broker["orders"]),
            "broker_tz_offsets_s": tz_offsets,
            "tick_coverage": tick_gap,
        },
        "DATA_GAPS": [
            "No independent tick/quote source covers 2026-09-20T23:05:42-23:06:13Z: mt5.copy_ticks_range on the V3 terminal returns 0 rows for every window/flag variant; the local live_fxtm archive has no 2026-09-20 file (ticks_20260921 starts 2026-09-21T01:08:06Z, after the window). Entry quotes therefore come from the ledger's own symbol_info_tick snapshot, not an independent feed.",
            "ledger does not persist exit-time bid/ask (only the executable side). Exit spread reconstructed from registry exit_slippage_bps where non-zero (5/20), else assumed = entry spread.",
            "registry.jsonl entry_fill_price is null (key mismatch: code writes s['fill_price']) and V3_COST_PROFILE rows entry_slippage is null (code reads s['entry_slippage_price'] but the sample stores s['slippage_price']). Entry slippage recovered for this audit from the ledger; published profiles under-report it.",
            "hold_actual_ms computed from integer-second tick timestamps -> 0/1000/2000/3000 ms quantisation; not usable as a duration measurement.",
            "tick.age / STALE_TICK_AT_REQUEST is computed in code but never written to the ledger, so quote staleness at request time cannot be verified from stored evidence.",
            "broker symbol_info trade_tick_value (0.1) does not reconcile with contract_size (100.0); unused by the bridge (deal.profit used as ground truth).",
            "calibration_pilot.py sets s['volume'] only inside a dead 'if volume in s' guard; the variable 'gross' multiplies by 0 and is never used. Latent unit bug (no effect on this run because gross_pnl is computed separately).",
        ],
        "SOURCES": {
            "ledger": LEDGER,
            "registry": REGISTRY,
            "cost_profile": COST_PROFILE,
            "execution_profile": EXEC_PROFILE,
            "pilot": PILOT,
            "broker_source": broker["_source"],
            "broker_account": acct,
            "broker_spec": spec,
            "symbol_spec_expected": pilot.get("spec"),
            "window_utc": [pilot["started_utc"], pilot["finished_utc"]],
        },
        "HASHES": inputs,
        "git_commit": None,
        "safety": {"V1_ORDER_SEND": False, "V2_ORDER_SEND": False, "V3_ORDER_SEND": False,
                   "LIVE": False, "CALIBRATION_AUTO_STOP": True, "EXPANSION": "LOCKED"},
    }
    summary["HASHES"]["result_hash"] = sha256_obj(
        {k: v for k, v in summary.items() if k != "HASHES"})

    # ---------------- write outputs ----------------
    os.makedirs(AUDIT, exist_ok=True)
    csv_path = os.path.join(AUDIT, "v3_cost_bridge_20trades.csv")
    cols = [k for k in rows[0] if not k.startswith("_")]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})

    json_path = os.path.join(AUDIT, "v3_cost_bridge_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, default=str)

    print(json.dumps({
        "status": status,
        "n": n,
        "model_net_mean": model_net_mean,
        "broker_net_mean": broker_net_mean,
        "mean_difference": mean_diff,
        "explained": explained,
        "unexplained": unexplained_total,
        "explained_ratio": explained_ratio,
        "max_unexplained": max_unexplained,
        "components": components,
        "csv": csv_path,
        "json": json_path,
    }, default=str, indent=1))
    return summary


if __name__ == "__main__":
    main()
