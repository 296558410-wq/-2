"""V3-HFT-CALIBRATION-FORMULA-FIX-001: offline OLD vs CORRECTED recompute.

Recomputes the 20 frozen V3 calibration round trips with
  * the OLD (defective) net_pnl formula, and
  * the CORRECTED broker-anchored formula,
without touching the broker: NO order_send, NO new calibration order, NO write
to any pilot artifact. Inputs are READ-ONLY frozen artifacts:

  data/hft_ledger/v3_calibration_ledger.jsonl   (fills / requested prices / quotes)
  data/calibration/registry.jsonl               (direction, commission, swap, deal ids)
  audit/_probe_broker_out.json                  (broker deal facts + symbol spec)
  audit/v3_cost_bridge_20trades.csv             (SUPPLEMENTARY: exit-side quotes only;
                                                 exit bid/ask are not in the ledger)

Broker facts are never adjusted. Run from trader_v3:
    python audit/v3_formula_fix_recompute.py
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
if V3 not in sys.path:
    sys.path.insert(0, V3)

from foundation import ledger as LED, pnl_accounting as PNA  # noqa: E402

LEDGER = os.path.join(V3, "data", "hft_ledger", "v3_calibration_ledger.jsonl")
REGISTRY = os.path.join(V3, "data", "calibration", "registry.jsonl")
PROBE = os.path.join(HERE, "_probe_broker_out.json")
AUDIT_CSV = os.path.join(HERE, "v3_cost_bridge_20trades.csv")
OUT_CSV = os.path.join(HERE, "v3_formula_fix_comparison.csv")
OUT_JSON = os.path.join(HERE, "v3_formula_fix_summary.json")

# task-briefed immutability baselines (must stay byte-identical)
BASELINE_SHA256 = {
    "data/hft_ledger/v3_calibration_ledger.jsonl":
        "FC8FD01E5AC487DD63558241D67584D453CCD21D8AA3A91D8BB804304E06750C",
    "data/calibration/PILOT_DONE":
        "DEC80E9F5166DD4ECDBB76DA3B62F8EDC7C61D857F5A9AC87269D6BD588339C6",
    "data/calibration/registry.jsonl":
        "7AD9596C4CAB88BB95E0650DAABBB169B53C3D3B796B07EA8BACB7C6366F4F25",
    "audit/_probe_broker_out.json":
        "F76782CE347738E7B31547C04C9BF5936022E9261A3BA5BB7A2877565BD70CA0",
}

CSV_COLUMNS = ["trade_id", "side", "volume", "price_unit_usd",
               "entry_fill_price", "exit_fill_price",
               "gross_pnl_price", "gross_pnl_usd", "commission", "swap",
               "old_net_pnl", "corrected_net_pnl", "broker_realized_net",
               "old_error", "corrected_error",
               "old_published_model_net", "old_formula_reproduced",
               "entry_slippage_adverse", "exit_slippage_adverse",
               "spread_at_entry", "theoretical_net", "execution_friction",
               "friction_spread", "friction_slippage",
               "broker_gross_profit", "reconciliation_residual",
               "accounting_reconciliation", "unit_status", "net_pnl_status",
               "exit_quote_source"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_baselines() -> dict:
    out = {}
    for rel, want in BASELINE_SHA256.items():
        p = os.path.join(V3, rel.replace("/", os.sep))
        got = sha256(p) if os.path.exists(p) else None
        out[rel] = {"expected": want, "actual": got,
                    "UNCHANGED": (got is not None and got.upper() == want.upper())}
    return out


def load_ledger() -> dict:
    ev = LED.Ledger.replay(LEDGER)
    per: dict = {}
    for e in ev:
        cid = e.get("decision_id")
        if not cid or not cid.startswith("V3CAL-"):
            continue
        d = per.setdefault(cid, {})
        t = e.get("event_type")
        if t == "ORDER_REQUEST":
            d["entry_req_price"] = e.get("price")
            d["entry_bid"] = e.get("bid")
            d["entry_ask"] = e.get("ask")
            d["entry_spread"] = e.get("spread")
            d["entry_request_ns"] = e.get("timestamp_ns")
        elif t == "ENTRY_FILL":
            d["entry_fill_price"] = e.get("price")
            d["entry_fill_ns"] = e.get("timestamp_ns")
            d["position_id"] = e.get("position_id")
        elif t == "EXIT_REQUEST":
            d["exit_req_price"] = e.get("price")
            d["exit_request_ns"] = e.get("timestamp_ns")
        elif t == "EXIT_FILL":
            d["exit_fill_price"] = e.get("price")
            d["exit_fill_ns"] = e.get("timestamp_ns")
    return per


def load_registry() -> dict:
    out = {}
    with open(REGISTRY, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                out[r["calibration_id"]] = r
    return out


def load_probe() -> dict:
    with open(PROBE, encoding="utf-8") as f:
        return json.load(f)


def load_audit_csv() -> dict:
    out = {}
    if not os.path.exists(AUDIT_CSV):
        return out
    with open(AUDIT_CSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["trade_id"]] = r
    return out


def _f(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def broker_facts_by_position(probe: dict) -> dict:
    """Broker deal facts, keyed by position id (= registry order_id)."""
    out: dict = {}
    for d in probe.get("deals", []):
        pid = str(d.get("position_id"))
        rec = out.setdefault(pid, {"profit": 0.0, "commission": 0.0, "swap": 0.0,
                                   "volume": 0.0, "entry": None, "exit": None})
        rec["profit"] += float(d.get("profit") or 0.0)
        rec["commission"] += float(d.get("commission") or 0.0)
        rec["swap"] += float(d.get("swap") or 0.0)
        # position size: one leg of the round trip, NEVER the sum of both legs
        rec["volume"] = max(rec["volume"], float(d.get("volume") or 0.0))
        if d.get("entry") == 0:
            rec["entry"] = d
        elif d.get("entry") == 1:
            rec["exit"] = d
    return out


def recompute() -> dict:
    led = load_ledger()
    reg = load_registry()
    probe = load_probe()
    sup = load_audit_csv()
    facts = broker_facts_by_position(probe)
    spec = probe.get("spec", {})
    acct_ccy = (probe.get("account") or {}).get("currency")

    rows = []
    for cid in sorted(reg):
        r = reg[cid]
        l = led.get(cid, {})
        pid = str(r.get("order_id"))
        bf = facts.get(pid)
        if bf is None:
            raise SystemExit(f"HALT: no broker facts for {cid} (position {pid})")
        direction = r.get("direction")
        volume = bf["volume"]
        if not volume:
            raise SystemExit(f"HALT: broker volume missing for {cid}")

        entry_fill = l.get("entry_fill_price")
        exit_fill = l.get("exit_fill_price")
        if entry_fill is None or exit_fill is None:
            raise SystemExit(f"HALT: ledger fills missing for {cid}")

        # ledger is authoritative for requested prices / quotes; exit quotes are
        # NOT persisted in the ledger -> supplementary (flagged), else DATA_GAP.
        entry_bid, entry_ask = l.get("entry_bid"), l.get("entry_ask")
        entry_spread = l.get("entry_spread")
        entry_req = l.get("entry_req_price")
        exit_req = l.get("exit_req_price")
        exit_bid = exit_ask = exit_mid = None
        quote_src = "LEDGER"
        srow = sup.get(cid)
        if srow is not None and srow.get("exit_bid") and srow.get("exit_ask"):
            exit_bid, exit_ask = _f(srow["exit_bid"]), _f(srow["exit_ask"])
            exit_mid = _f(srow.get("exit_mid"))
            quote_src = "AUDIT_CSV_SUPPLEMENTARY"
        else:
            quote_src = "DATA_GAP_EXIT_QUOTES_NOT_PERSISTED"
        entry_mid = (entry_bid + entry_ask) / 2.0 if (entry_bid and entry_ask) else None

        side_in, side_out = PNA.leg_side(direction, "entry"), PNA.leg_side(direction, "exit")
        slip_in = PNA.adverse_slippage_price(side_in, entry_req, entry_fill)
        slip_out = PNA.adverse_slippage_price(side_out, exit_req, exit_fill)
        broker_gross = bf["profit"]
        comm = bf["commission"]
        swap = bf["swap"]

        # OLD (frozen, defective) formula: charges spread + |slippage| again and
        # subtracts the broker-signed (negative) commission.
        old_net = PNA.old_formula_net(direction=direction, entry_fill_price=entry_fill,
                                      exit_fill_price=exit_fill, spread=entry_spread,
                                      entry_slippage=slip_in, exit_slippage=slip_out,
                                      commission=comm)
        # CORRECTED (broker-anchored)
        acc = PNA.round_trip_accounting(
            direction=direction, volume=volume,
            contract_size=spec.get("trade_contract_size"),
            tick_size=spec.get("trade_tick_size"), tick_value=spec.get("trade_tick_value"),
            entry_fill_price=entry_fill, exit_fill_price=exit_fill,
            entry_mid=entry_mid, exit_mid=exit_mid,
            entry_ref_price=entry_req, exit_ref_price=exit_req,
            entry_bid=entry_bid, entry_ask=entry_ask, exit_bid=exit_bid, exit_ask=exit_ask,
            commission=comm, swap=swap, broker_gross_profit=broker_gross,
            profit_currency=spec.get("currency_profit"), account_currency=acct_ccy)

        published = _f((srow or {}).get("model_net"))
        rows.append({
            "trade_id": cid, "side": direction, "volume": volume,
            "price_unit_usd": acc["price_unit_usd"],
            "entry_fill_price": entry_fill, "exit_fill_price": exit_fill,
            "gross_pnl_price": acc["gross_pnl"], "gross_pnl_usd": acc["gross_pnl_usd"],
            "commission": comm, "swap": swap,
            "old_net_pnl": old_net,
            "corrected_net_pnl": acc["net_pnl"],
            "broker_realized_net": acc["broker_realized_net"],
            "old_error": None if acc["broker_realized_net"] is None else old_net - acc["broker_realized_net"],
            "corrected_error": acc["reconciliation_residual"],
            "old_published_model_net": published,
            "old_formula_reproduced": (None if published is None
                                       else abs(published - old_net) <= 1e-9),
            "entry_slippage_adverse": slip_in, "exit_slippage_adverse": slip_out,
            "spread_at_entry": entry_spread,
            "theoretical_net": acc["theoretical_net"],
            "execution_friction": acc["execution_friction"],
            "friction_spread": acc["friction_spread"],
            "friction_slippage": acc["friction_slippage"],
            "broker_gross_profit": broker_gross,
            "reconciliation_residual": acc["reconciliation_residual"],
            "accounting_reconciliation": acc["accounting_reconciliation"],
            "unit_status": acc["unit_status"], "net_pnl_status": acc["net_pnl_status"],
            "exit_quote_source": quote_src,
        })

    n = len(rows)

    def mean(key):
        xs = [r[key] for r in rows if r[key] is not None]
        return (sum(xs) / len(xs)) if xs else None

    def total(key):
        xs = [r[key] for r in rows if r[key] is not None]
        return sum(xs)

    corrected_resid = [abs(r["corrected_error"]) for r in rows if r["corrected_error"] is not None]
    hashes = verify_baselines()
    summary = {
        "schema": "v3_formula_fix/1",
        "task_id": "V3-HFT-CALIBRATION-FORMULA-FIX-001",
        "net_pnl_formula_version": PNA.VERSION,
        "n_roundtrips": n,
        "OLD_MODEL_NET_MEAN": mean("old_net_pnl"),
        "CORRECTED_MODEL_NET_MEAN": mean("corrected_net_pnl"),
        "BROKER_NET_MEAN": mean("broker_realized_net"),
        "OLD_TOTAL_ERROR": total("old_error"),
        "CORRECTED_TOTAL_ERROR": total("corrected_error"),
        "MAX_ABS_RESIDUAL": max(corrected_resid) if corrected_resid else None,
        "MEAN_ABS_RESIDUAL": (sum(corrected_resid) / len(corrected_resid)) if corrected_resid else None,
        "BROKER_NET_SUM": total("broker_realized_net"),
        "BROKER_GROSS_SUM": total("broker_gross_profit"),
        "BROKER_COMMISSION_SUM": total("commission"),
        "BROKER_SWAP_SUM": total("swap"),
        "UNIT": {"price_unit_usd": rows[0]["price_unit_usd"], "volume": rows[0]["volume"],
                 "contract_size": spec.get("trade_contract_size"),
                 "tick_size": spec.get("trade_tick_size"),
                 "tick_value": spec.get("trade_tick_value"),
                 "account_currency": acct_ccy,
                 "profit_currency": spec.get("currency_profit"),
                 "unit_status": rows[0]["unit_status"]},
        "OLD_FORMULA_REPRODUCED_ALL": all(r["old_formula_reproduced"] for r in rows
                                          if r["old_formula_reproduced"] is not None),
        "CORRECTED_RECONCILED_ALL": all(r["accounting_reconciliation"] == "PASS" for r in rows),
        "CROSS_CHECK_audit_summary": {
            "MODEL_NET_MEAN_expected": -0.1375, "MODEL_NET_MEAN_actual": mean("old_net_pnl"),
            "BROKER_NET_MEAN_expected": -0.372, "BROKER_NET_MEAN_actual": mean("broker_realized_net"),
            "BROKER_NET_SUM_expected": -7.44, "BROKER_NET_SUM_actual": total("broker_realized_net"),
            "BROKER_BALANCE_DELTA_expected": -7.44,
        },
        "RAW_DATA_BASELINE_HASHES": hashes,
        "RAW_DATA_IMMUTABLE": all(v["UNCHANGED"] for v in hashes.values()),
        "ORDER_SENT": False, "LIVE": False, "EXPANSION": "LOCKED",
        "exit_quote_note": ("exit-side bid/ask are not persisted by the pilot ledger; "
                            "friction/theoretical decomposition uses the previous audit CSV "
                            "(supplementary) and is flagged per row. Broker facts and the "
                            "corrected net use ONLY the ledger fills + broker deals."),
        "rows": rows,
    }
    return summary


def write_outputs(summary: dict) -> None:
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in summary["rows"]:
            w.writerow(r)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, default=str)


def main() -> int:
    s = recompute()
    write_outputs(s)
    print(json.dumps({k: s[k] for k in
                      ("n_roundtrips", "OLD_MODEL_NET_MEAN", "CORRECTED_MODEL_NET_MEAN",
                       "BROKER_NET_MEAN", "OLD_TOTAL_ERROR", "CORRECTED_TOTAL_ERROR",
                       "MAX_ABS_RESIDUAL", "MEAN_ABS_RESIDUAL", "BROKER_NET_SUM",
                       "OLD_FORMULA_REPRODUCED_ALL", "CORRECTED_RECONCILED_ALL",
                       "RAW_DATA_IMMUTABLE")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
