"""V3 calibration round-trip P&L accounting (pure functions, no broker I/O).

Repairs the net_pnl defects of V3-HFT-CALIBRATION-PILOT-001 confirmed by
V3-HFT-COST-BRIDGE-AUDIT-001. All defects lived in the net_pnl line of
``calibration_pilot.py::_round_trip``:

1. the entry spread was deducted although it is ALREADY inside the fill price
   (the order is priced at the executable side: buy@ask / sell@bid) -> no
   separate spread term may exist.
2. entry/exit slippage was deducted although it is ALREADY inside the fill
   price (the fill price IS the executed price) -> no separate slippage term.
3. ``abs()`` turned favourable fills into costs -> only signed terms.
4. MT5 returns commission as a NEGATIVE number for a cost; the old code did
   ``net = ... - commission``, which INVERTED it into a credit (2x|comm| error)
   -> fees are added with the broker sign.
5. three quantities are now explicitly separated and never conflated:
     BROKER_REALIZED_NET  broker's own accounting  (ANCHOR, not modelled)
     CORRECTED_NET        independent rebuild from fill prices x broker spec
                          + broker-signed fees (reconciles against the anchor)
     THEORETICAL_NET      diagnostic mid-to-mid benchmark + real fees
   Friction/spread/slippage terms are diagnostics only; they are NEVER reported
   as actual broker P&L.
6. units come from the broker symbol specification (contract size x volume),
   cross-checked against tick value / tick size, with the account-currency
   conversion made explicit.

Identity guaranteed by construction (and asserted by ``assert_theoretical_identity``):
    corrected_net = theoretical_net - execution_friction
"""
from __future__ import annotations

VERSION = "v3-calibration-netpnl-2"

MONEY_TOL = 1e-6  # USD tolerance for reconciliation (float residuals ~1e-13)


def leg_side(direction: str, leg: str) -> str:
    """'BUY'/'SELL' traded on the given leg of a round trip."""
    d = (direction or "").upper()
    lg = (leg or "").lower()
    if d == "LONG":
        return "BUY" if lg == "entry" else "SELL"
    if d == "SHORT":
        return "SELL" if lg == "entry" else "BUY"
    raise ValueError(f"bad direction {direction!r}")


def signed_price_move(direction: str, entry_price: float, exit_price: float) -> float:
    """Price move in the position's own direction (already spread/slippage-inclusive)."""
    d = (direction or "").upper()
    return (exit_price - entry_price) if d == "LONG" else (entry_price - exit_price)


def leg_side_reference_price(direction: str, leg: str, bid: float, ask: float) -> float:
    """Executable reference price for a leg (buy at ask, sell at bid)."""
    return ask if leg_side(direction, leg) == "BUY" else bid


def adverse_slippage_price(side: str, ref_price: float, fill_price: float):
    """Signed slippage of one leg in price units; POSITIVE = adverse (a cost).

    Negative means the fill was better than the reference price; the sign is
    preserved (the old abs() turned that into a cost).
    """
    if ref_price is None or fill_price is None:
        return None
    return (fill_price - ref_price) if side == "BUY" else (ref_price - fill_price)


def adverse_vs_mid_price(side: str, mid: float, fill_price: float):
    """Signed fill-vs-mid distance; POSITIVE = paid away from mid (a cost)."""
    if mid is None or fill_price is None:
        return None
    return (fill_price - mid) if side == "BUY" else (mid - fill_price)


def price_unit_usd(contract_size, volume):
    """Account-currency value of a 1.0 price move for the traded volume."""
    if contract_size is None or volume is None:
        return None
    return float(contract_size) * float(volume)


def price_unit_from_tick_metadata(tick_size, tick_value, volume):
    if not tick_size or tick_value is None or volume is None:
        return None
    return (float(tick_value) / float(tick_size)) * float(volume)


def unit_crosscheck(contract_size, volume, tick_size=None, tick_value=None) -> dict:
    u = price_unit_usd(contract_size, volume)
    u_tick = price_unit_from_tick_metadata(tick_size, tick_value, volume)
    consistent = None
    if u is not None and u_tick is not None:
        consistent = abs(u - u_tick) <= 1e-9 * max(1.0, abs(u))
    if consistent is True:
        status = "PASS"
    elif consistent is False:
        status = "DATA_GAP_TICK_VALUE_INCONSISTENT"
    else:
        status = "PASS_CONTRACT_SIZE_ONLY(tick metadata unavailable)"
    return {"price_unit_usd": u, "price_unit_usd_tick_metadata": u_tick,
            "tick_metadata_consistent": consistent, "unit_status": status}


def round_trip_accounting(*, direction: str, volume, contract_size,
                          entry_fill_price, exit_fill_price,
                          entry_mid=None, exit_mid=None,
                          entry_ref_price=None, exit_ref_price=None,
                          entry_bid=None, entry_ask=None,
                          exit_bid=None, exit_ask=None,
                          commission=None, swap=None,
                          broker_gross_profit=None,
                          tick_size=None, tick_value=None,
                          profit_currency=None, account_currency=None) -> dict:
    """Broker-anchored accounting for one closed round trip.

    ``commission``/``swap`` are the broker's own signed values (MT5 commission
    is negative for a cost). ``broker_gross_profit`` is the broker's realised
    P&L of the closing deal(s) (MT5 ``deal.profit``). Nothing here re-charges
    spread or slippage: they are already inside the fill prices.
    """
    d = (direction or "").upper()
    if d not in ("LONG", "SHORT"):
        raise ValueError(f"bad direction {direction!r}")
    if entry_fill_price is None or exit_fill_price is None:
        raise ValueError("fill prices are required")

    u = price_unit_usd(contract_size, volume)
    if u is None:
        raise ValueError("contract_size/volume are required")

    units = unit_crosscheck(contract_size, volume, tick_size, tick_value)

    # --- conversion: quote/profit currency vs account currency ---
    if profit_currency and account_currency:
        conv = "IDENTITY" if str(profit_currency).upper() == str(account_currency).upper() \
            else "DATA_GAP_NO_FX_RATE"
    else:
        conv = "UNKNOWN"

    gross_price = signed_price_move(d, entry_fill_price, exit_fill_price)
    gross_usd = gross_price * u

    # --- fees, broker sign preserved (MT5 commission < 0 == cost) ---
    fees_usd = None
    if commission is not None and swap is not None:
        fees_usd = float(commission) + float(swap)

    net_status = "OK"
    if conv == "DATA_GAP_NO_FX_RATE":
        net_status = "DATA_GAP_CURRENCY_CONVERSION"
    elif conv == "UNKNOWN":
        net_status = "DATA_GAP_CURRENCY_UNKNOWN"
    elif fees_usd is None:
        net_status = "DATA_GAP_FEES"
    net_usd = None if net_status != "OK" else gross_usd + fees_usd

    # --- broker realised net (anchor) ---
    broker_net = None
    if broker_gross_profit is not None and fees_usd is not None:
        broker_net = float(broker_gross_profit) + fees_usd

    residual = None
    recon = "NOT_EVALUATED"
    if net_usd is not None and broker_net is not None:
        residual = net_usd - broker_net
        recon = "PASS" if abs(residual) <= MONEY_TOL else "FAIL"

    # --- diagnostics: spread / slippage (never deducted again) ---
    side_in, side_out = leg_side(d, "entry"), leg_side(d, "exit")
    slip_in = adverse_slippage_price(side_in, entry_ref_price, entry_fill_price)
    slip_out = adverse_slippage_price(side_out, exit_ref_price, exit_fill_price)

    mid_gross_usd = None
    friction_usd = None
    friction_spread_usd = None
    friction_slippage_usd = None
    theoretical_net = None
    identity_ok = None
    if entry_mid is not None and exit_mid is not None:
        mid_gross_usd = signed_price_move(d, entry_mid, exit_mid) * u
        f_in = adverse_vs_mid_price(side_in, entry_mid, entry_fill_price)
        f_out = adverse_vs_mid_price(side_out, exit_mid, exit_fill_price)
        friction_usd = (f_in + f_out) * u
        # friction decomposes exactly into half-spread(s) + slippage
        if entry_bid is not None and entry_ask is not None and exit_bid is not None and exit_ask is not None:
            half = ((float(entry_ask) - float(entry_bid)) + (float(exit_ask) - float(exit_bid))) / 2.0
            friction_spread_usd = half * u
            friction_slippage_usd = friction_usd - friction_spread_usd
        if fees_usd is not None:
            theoretical_net = mid_gross_usd + fees_usd
            if net_usd is not None:
                identity_ok = abs((theoretical_net - friction_usd) - net_usd) <= MONEY_TOL

    out = {
        "accounting_version": VERSION,
        "direction": d,
        "volume": volume,
        "contract_size": contract_size,
        "gross_pnl": gross_price,            # signed price move (backward compatible key)
        "gross_pnl_usd": gross_usd,          # == broker gross profit (unit reconciliation)
        "entry_fill_price": entry_fill_price,
        "exit_fill_price": exit_fill_price,
        "net_pnl": net_usd,                  # CORRECTED net, broker-anchored
        "net_pnl_basis": "BROKER_REALIZED_ANCHORED_FILL_PRICE_REBUILD",
        "net_pnl_status": net_status,
        "commission_usd": commission,
        "swap_usd": swap,
        "fees_usd": fees_usd,
        "broker_gross_profit": broker_gross_profit,
        "broker_realized_net": broker_net,
        "reconciliation_residual": residual,
        "accounting_reconciliation": recon,
        "theoretical_mid_gross": mid_gross_usd,
        "theoretical_net": theoretical_net,
        "theoretical_identity_ok": identity_ok,
        "execution_friction": friction_usd,
        "friction_spread": friction_spread_usd,
        "friction_slippage": friction_slippage_usd,
        "entry_slippage_adverse_price": slip_in,
        "exit_slippage_adverse_price": slip_out,
        "entry_spread_price": (None if (entry_bid is None or entry_ask is None)
                               else float(entry_ask) - float(entry_bid)),
        "exit_spread_price": (None if (exit_bid is None or exit_ask is None)
                              else float(exit_ask) - float(exit_bid)),
        "spread_slippage_basis": "EMBEDDED_IN_FILL_PRICE_NOT_DEDUCTED",
        "price_unit_usd": u,
        "unit_status": units["unit_status"],
        "currency_conversion": conv,
    }
    return out


def assert_theoretical_identity(rec: dict) -> bool:
    """corrected_net == theoretical_net - execution_friction (diagnostic invariant)."""
    if rec.get("net_pnl") is None or rec.get("theoretical_net") is None or rec.get("execution_friction") is None:
        return True  # nothing to check (DATA_GAP)
    return abs((rec["theoretical_net"] - rec["execution_friction"]) - rec["net_pnl"]) <= MONEY_TOL


def old_formula_net(*, direction: str, entry_fill_price, exit_fill_price,
                    spread, entry_slippage, exit_slippage, commission) -> float:
    """The FROZEN pre-fix formula (kept ONLY to quantify the defect offline).

    net = gross_from_fills - spread - |entry_slip| - |exit_slip| - commission
    """
    gross = signed_price_move(direction, entry_fill_price, exit_fill_price)
    return (gross - (spread or 0.0) - abs(entry_slippage or 0.0) - abs(exit_slippage or 0.0)
            - (commission or 0.0))
