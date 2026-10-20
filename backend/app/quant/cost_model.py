"""
Transaction Cost, Slippage, and Asset Multiplier Models.
Provides realistic accounting for equities, options, futures, and crypto.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Optional


def _number(value, name, positive=False):
    value = float(value)
    if not isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return value


@dataclass
class CostModel:
    """
    Cost model configuration:
    - fee_per_order: Fixed flat fee per trade execution (e.g. $1.00 broker ticket fee)
    - fee_bps: Basis points of total traded dollar volume (1 bps = 0.01% = 0.0001)
    - slippage_bps: Expected market slippage in basis points per order (entry and exit)
    - min_fee: Minimum execution fee
    - max_fee: Maximum execution fee cap (optional)
    """
    fee_per_order: float = 0.0
    fee_bps: float = 0.0
    slippage_bps: float = 0.0
    min_fee: float = 0.0
    max_fee: Optional[float] = None

    def __post_init__(self):
        for name in ("fee_per_order", "fee_bps", "slippage_bps", "min_fee"):
            setattr(self, name, _number(getattr(self, name), name))
        if self.max_fee is not None:
            self.max_fee = _number(self.max_fee, "max_fee")
            if self.max_fee < self.min_fee:
                raise ValueError("max_fee cannot be below min_fee")

    def calculate_order_cost(self, price: float, quantity: float, multiplier: float = 1.0) -> float:
        """Commission cap/floor applies before slippage. Zero quantity is no order."""
        price = _number(price, "price")
        quantity = _number(quantity, "quantity")
        multiplier = _number(multiplier, "multiplier", positive=True)
        if quantity == 0:
            return 0.0
        notional = price * quantity * multiplier
        fee = self.fee_per_order + (notional * (self.fee_bps / 10000.0))
        if self.min_fee > 0:
            fee = max(fee, self.min_fee)
        if self.max_fee is not None:
            fee = min(fee, self.max_fee)

        slippage = notional * (self.slippage_bps / 10000.0)
        return fee + slippage


def calculate_cost_aware_pnl(
    side: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
    multiplier: float = 1.0,
    cost_model: Optional[CostModel] = None,
    fees_paid: Optional[float] = None,
    slippage_per_unit: float = 0.0,
    stop_loss: Optional[float] = None,
) -> dict:
    """
    Computes rigorous gross and net P&L with explicit transaction costs,
    slippage, and contract multipliers (e.g., multiplier=100 for equity options).

    Direction:
      BUY (Long): gross = (exit - entry) * qty * multiplier
      SELL (Short): gross = (entry - exit) * qty * multiplier

    Net P&L:
      net = gross - total_costs
    """
    side_clean = (side or "").strip().upper()
    if side_clean not in ("BUY", "SELL", "LONG", "SHORT"):
        raise ValueError(f"Invalid trade side: '{side}'. Must be 'BUY' or 'SELL'.")

    direction = 1.0 if side_clean in ("BUY", "LONG") else -1.0
    entry = float(entry_price)
    exit_p = float(exit_price)
    entry = _number(entry, "entry_price", positive=True)
    exit_p = _number(exit_p, "exit_price")
    qty = _number(quantity, "quantity", positive=True)
    mult = _number(multiplier, "multiplier", positive=True)
    explicit_fees = _number(fees_paid if fees_paid is not None else 0.0, "fees_paid")
    slippage_per_unit = _number(slippage_per_unit, "slippage_per_unit")
    if cost_model is not None and (fees_paid is not None or slippage_per_unit != 0):
        raise ValueError("Use a cost model OR explicit round-trip fees/slippage, not both")

    # Gross P&L
    gross_pnl = (exit_p - entry) * qty * mult * direction
    gross_return_pct = ((exit_p - entry) / entry) * 100.0 * direction

    # Total costs computation
    if cost_model is not None:
        entry_cost = cost_model.calculate_order_cost(entry, qty, mult)
        exit_cost = cost_model.calculate_order_cost(exit_p, qty, mult)
        total_costs = entry_cost + exit_cost
    else:
        # Explicit fees and per-unit slippage are ROUND-TRIP totals.
        slippage_cost = float(slippage_per_unit) * qty * mult
        total_costs = explicit_fees + slippage_cost

    net_pnl = gross_pnl - total_costs

    # Invested capital / notional
    initial_notional = entry * qty * mult
    net_return_pct = (net_pnl / initial_notional) * 100.0 if initial_notional > 0 else 0.0

    # Risk metrics (R-Multiple)
    risk_amount = None
    r_multiple = None
    if stop_loss is not None:
        stop = _number(stop_loss, "stop_loss")
        if (direction > 0 and stop >= entry) or (direction < 0 and stop <= entry):
            raise ValueError("stop_loss must be below a long entry or above a short entry")
        risk_per_unit = abs(entry - stop)
        if risk_per_unit > 0:
            risk_amount = risk_per_unit * qty * mult
            r_multiple = net_pnl / risk_amount

    return {
        "side": side_clean,
        "entry_price": round(entry, 4),
        "exit_price": round(exit_p, 4),
        "quantity": qty,
        "multiplier": mult,
        "initial_notional": round(initial_notional, 2),
        "gross_pnl": round(gross_pnl, 2),
        "total_costs": round(total_costs, 2),
        "net_pnl": round(net_pnl, 2),
        "gross_return_pct": round(gross_return_pct, 4),
        "net_return_pct": round(net_return_pct, 4),
        "risk_amount": round(risk_amount, 2) if risk_amount is not None else None,
        "r_multiple": round(r_multiple, 4) if r_multiple is not None else None,
    }
