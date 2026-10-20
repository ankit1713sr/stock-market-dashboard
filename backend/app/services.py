from collections import defaultdict
from datetime import date
from math import isfinite
from statistics import mean
from .accounting import pnl_basis, reporting_pnl
from migrations.revisions import ACCOUNTING_COLUMNS

from .quant.cost_model import calculate_cost_aware_pnl
from .quant.metrics import (calculate_drawdown_series, calculate_expectancy,
                            calculate_sharpe_ratio, calculate_sortino_ratio, calculate_var_historical)


def round_money(value):
    return round(float(value), 2) if value is not None else None


def calculate_trade_metrics(side, entry_price, exit_price, qty, stop_loss=None):
    # Existing API has no cost fields: preserve zero-cost legacy semantics.
    pnl = return_pct = risk_amount = r_multiple = None
    if exit_price is not None:
        result = calculate_cost_aware_pnl(side, entry_price, exit_price, qty)
        pnl, return_pct = result["net_pnl"], result["net_return_pct"]
    # Preserve historic stop-distance semantics without rewriting old records.
    if stop_loss is not None:
        risk_amount = abs(float(entry_price) - float(stop_loss)) * float(qty)
        if risk_amount > 0 and pnl is not None:
            r_multiple = pnl / risk_amount
        elif risk_amount == 0:
            risk_amount = None
    return {"pnl": pnl, "return_pct": return_pct, "risk_amount": round_money(risk_amount),
            "r_multiple": round(r_multiple, 4) if r_multiple is not None else None}


def calculate_position_size(account_balance, risk_pct, entry_price, stop_loss):
    dollar_risk = float(account_balance) * (float(risk_pct) / 100)
    risk_per_unit = abs(float(entry_price) - float(stop_loss))
    quantity = int(dollar_risk // risk_per_unit) if risk_per_unit > 0 else 0
    return {
        "dollar_risk": round_money(dollar_risk),
        "risk_per_unit": round_money(risk_per_unit),
        "quantity": quantity,
    }


def serialize_trade(trade):
    return {
        **{name: getattr(trade, name, None) for name in ACCOUNTING_COLUMNS},
        "pnl_basis": pnl_basis(trade),
        "id": trade.id,
        "date": trade.trade_date or (trade.created_at.date().isoformat() if trade.created_at else None),
        "trade_date": trade.trade_date,
        "symbol": trade.symbol,
        "side": trade.side,
        "asset": trade.asset or "Stock",
        "entry": trade.entry_price,
        "entry_price": trade.entry_price,
        "exit": trade.exit_price,
        "exit_price": trade.exit_price,
        "stop_loss": trade.stop_loss,
        "target_price": trade.target_price,
        "qty": trade.qty,
        "pnl": reporting_pnl(trade),
        "return_pct": trade.return_pct,
        "risk_amount": trade.risk_amount,
        "r_multiple": trade.r_multiple,
        "strategy": trade.strategy,
        "emotion": trade.emotion,
        "mistake": trade.mistake,
        "rating": trade.rating,
        "notes": trade.notes or "",
        "chartUrl": trade.chart_url or "",
        "chart_url": trade.chart_url or "",
        "is_demo": bool(getattr(trade, "is_demo", False)),
        "created_at": trade.created_at.isoformat() if trade.created_at else None,
        "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
    }


def _completed(trade):
    return (getattr(trade, "exit_price", None) is not None
            and reporting_pnl(trade) is not None
            and isfinite(float(reporting_pnl(trade))))


def dashboard_summary(trades, initial_equity=10000):
    """Realized ledger only; ratios are NON-ANNUALIZED per-trade account returns.

    The journal has no daily marked equity or cash-flow history. Do not pretend
    that irregular trade observations are daily returns. Zero risk-free/target
    is explicit; initial equity defaults to the existing UI's $10,000 baseline.
    """
    if not isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("initial_equity must be positive and finite")
    ordered = sorted((t for t in trades if _completed(t)), key=lambda t: (t.trade_date or "", t.id))
    pnls = [float(reporting_pnl(t)) for t in ordered]
    stats = calculate_expectancy(pnls)
    equity, returns = [], []
    running = float(initial_equity)
    solvent = True
    for trade, pnl in zip(ordered, pnls):
        if running <= 0:
            solvent = False
        else:
            returns.append(pnl / running)
        running += pnl
        equity.append({"date": trade.trade_date, "equity": round_money(running), "pnl": round_money(pnl)})
    # Use unrounded equity for drawdown, round only the response.
    balances = []
    running = float(initial_equity)
    for pnl in pnls:
        running += pnl
        balances.append(running)
    dd = calculate_drawdown_series(balances, initial_equity)
    rs = [float(t.r_multiple) for t in ordered if getattr(t, "r_multiple", None) is not None
          and isfinite(float(t.r_multiple))]
    return {
        "total_trades": len(pnls), "net_pnl": round_money(sum(pnls)),
        "win_rate": stats["win_rate"], "wins": sum(p > 0 for p in pnls), "losses": sum(p < 0 for p in pnls),
        "profit_factor": stats["profit_factor"], "avg_trade_pnl": stats["expectancy"],
        "win_loss_ratio": stats["win_loss_ratio"], "avg_r_multiple": round(mean(rs), 2) if rs else 0.0,
        "expectancy": stats["expectancy"],
        "sharpe": round(calculate_sharpe_ratio(returns), 4) if solvent else 0.0,
        "sortino": round(calculate_sortino_ratio(returns), 4) if solvent else 0.0,
        "max_drawdown_pct": round(float(dd["drawdown_pct"].min()), 4) if len(dd) else 0.0,
        "var_95": round_money(calculate_var_historical(pnls)),
        "best_trade": round_money(max(pnls)) if pnls else 0.0,
        "worst_trade": round_money(min(pnls)) if pnls else 0.0, "equity_curve": equity,
    }


def calendar_month(trades, year, month):
    days = defaultdict(lambda: {"pnl": 0.0, "trade_count": 0, "trades": []})
    for trade in trades:
        t_date_str = trade.trade_date or (trade.created_at.date().isoformat() if getattr(trade, "created_at", None) else None)
        if not t_date_str:
            continue
        try:
            trade_day = date.fromisoformat(t_date_str)
        except ValueError:
            continue
        if trade_day.year == year and trade_day.month == month:
            key = trade_day.isoformat()
            if _completed(trade):
                days[key]["pnl"] += float(reporting_pnl(trade))
            days[key]["trade_count"] += 1
            days[key]["trades"].append(serialize_trade(trade))

    return {
        "year": year,
        "month": month,
        "days": [
            {"date": key, "pnl": round_money(value["pnl"]), "trade_count": value["trade_count"], "trades": value["trades"]}
            for key, value in sorted(days.items())
        ],
    }


def group_analytics(trades, field):
    grouped = defaultdict(lambda: {"count": 0, "pnl": 0.0, "wins": 0})
    for trade in trades:
        if not _completed(trade):
            continue
        key = getattr(trade, field) or "Unspecified"
        grouped[key]["count"] += 1
        grouped[key]["pnl"] += float(reporting_pnl(trade))
        if reporting_pnl(trade) > 0:
            grouped[key]["wins"] += 1

    return [
        {
            "name": key,
            "count": value["count"],
            "pnl": round_money(value["pnl"]),
            "win_rate": round((value["wins"] / value["count"]) * 100, 2) if value["count"] else 0,
        }
        for key, value in sorted(grouped.items())
    ]
