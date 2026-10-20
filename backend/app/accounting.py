"""One accounting policy for storage, trade responses, and every report.

Legacy pnl is preserved; unknown costs never become actual zero. Fully
specified reported/estimated pnl is net. All amounts use existing quant
rounding. Slippage in execution prices must not be charged a second time.
"""
import json
from math import isfinite
from .quant.cost_model import CostModel, calculate_cost_aware_pnl


COST_INPUTS = {
    "brokerage_fee", "transaction_fee", "slippage_cost", "contract_multiplier",
    "cost_status", "slippage_treatment", "cost_model",
}
FINANCIAL_INPUTS = COST_INPUTS | {"side", "entry_price", "exit_price", "qty", "stop_loss"}


def pnl_basis(trade):
    if getattr(trade, "accounting_version", None) is None:
        return "legacy_unknown"
    status = getattr(trade, "cost_status", None)
    return "net_" + status if status in {"reported", "estimated"} else "gross_unknown_costs"


def reporting_pnl(trade):
    if pnl_basis(trade) in {"net_reported", "net_estimated"}:
        return getattr(trade, "net_pnl", None)
    return getattr(trade, "pnl", None)


def apply_accounting(trade, data, legacy_calculator):
    """Called only for creates or explicit financial edits, never migration/GET."""
    opted_in = bool(COST_INPUTS & data.keys()) or trade.accounting_version is not None
    if not opted_in:
        for key, value in legacy_calculator(trade.side, trade.entry_price, trade.exit_price,
                                            trade.qty, trade.stop_loss).items():
            setattr(trade, key, value)
        return
    trade.accounting_version = 1
    if "cost_model" in data:
        trade.cost_model_json = (json.dumps(data["cost_model"], sort_keys=True)
                                 if data["cost_model"] is not None else None)
    model = json.loads(trade.cost_model_json) if trade.cost_model_json else None
    # No inference from labels, including legacy futures/options labels.
    mult = trade.contract_multiplier
    if mult is None:
        raise ValueError("An explicit contract_multiplier is required for cost accounting")
    if not isfinite(mult) or mult <= 0:
        raise ValueError("contract_multiplier must be positive and finite")
    status = trade.cost_status or ("estimated" if model else "unknown")
    trade.cost_status = status
    if model:
        if status != "estimated" or any(getattr(trade, k) is not None for k in
                                         ("brokerage_fee", "transaction_fee", "slippage_cost")):
            raise ValueError("Use a cost model OR explicit fees/slippage; estimates require estimated status")
        if trade.slippage_treatment != "additional":
            raise ValueError("Modeled slippage requires additional treatment")
        costs = CostModel(**model)
    else:
        costs = None
        if status == "estimated":
            raise ValueError("Estimated costs require a cost_model snapshot")
        if status == "reported":
            if any(getattr(trade, k) is None for k in
                   ("brokerage_fee", "transaction_fee", "slippage_cost")):
                raise ValueError("Reported costs require all three fees/slippage values, including explicit zeros")
            if trade.slippage_treatment not in {"included", "additional"}:
                raise ValueError("Specify whether slippage is included or additional")
        if trade.slippage_treatment == "included" and (trade.slippage_cost or 0) != 0:
            raise ValueError("Included slippage cannot be deducted again")
    for key in ("brokerage_fee", "transaction_fee", "slippage_cost"):
        value = getattr(trade, key)
        if value is not None and (not isfinite(value) or value < 0):
            raise ValueError(f"{key} must be nonnegative and finite")
    # Shared stop-distance convention; stricter direction rules never alter legacy stops.
    risk = abs(trade.entry_price - trade.stop_loss) * trade.qty * mult if trade.stop_loss else None
    trade.risk_amount = round(risk, 2) if risk else None
    trade.pnl = trade.return_pct = trade.r_multiple = None
    trade.gross_pnl = trade.total_costs = trade.net_pnl = None
    if trade.exit_price is None:
        return
    gross = calculate_cost_aware_pnl(trade.side, trade.entry_price, trade.exit_price, trade.qty, mult)
    trade.gross_pnl = gross["gross_pnl"]
    if status == "unknown":
        trade.pnl = trade.gross_pnl
        trade.return_pct = gross["gross_return_pct"]
    else:
        if costs is not None:
            net = calculate_cost_aware_pnl(trade.side, trade.entry_price, trade.exit_price,
                                            trade.qty, mult, cost_model=costs)
        else:
            net = calculate_cost_aware_pnl(
                trade.side, trade.entry_price, trade.exit_price, trade.qty, mult,
                fees_paid=trade.brokerage_fee + trade.transaction_fee + trade.slippage_cost)
        trade.total_costs, trade.net_pnl = net["total_costs"], net["net_pnl"]
        trade.pnl, trade.return_pct = trade.net_pnl, net["net_return_pct"]
    trade.r_multiple = round(trade.pnl / risk, 4) if risk else None


def cost_coverage(trades):
    counts = {k: 0 for k in ("legacy_unknown", "gross_unknown_costs", "net_reported", "net_estimated")}
    completed = [t for t in trades if getattr(t, "exit_price", None) is not None
                 and reporting_pnl(t) is not None and isfinite(float(reporting_pnl(t)))]
    for trade in completed:
        counts[pnl_basis(trade)] += 1
    active = [k for k, n in counts.items() if n]
    unknown = counts["legacy_unknown"] + counts["gross_unknown_costs"]
    return {"completed_trades": len(completed), "counts": counts,
            "basis": "mixed" if len(active) > 1 else (active[0] if active else "empty"),
            "fully_costed": unknown == 0 and bool(completed),
            "label": ("Mixed/unknown cost basis: totals include legacy or gross P&L; historical costs are unknown."
                      if unknown else ("Net P&L; reported and/or estimated costs are identified per trade."
                                       if completed else "No completed trades."))}
