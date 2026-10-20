"""
Quant Package Initialization
Exposes technical indicators, performance metrics, cost models, and backtesting engines.
"""

from .technicals import calculate_rsi_wilder, calculate_bollinger_bands, calculate_macd
from .metrics import (
    calculate_annualized_metrics,
    calculate_drawdown_series,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_expectancy,
    calculate_var_historical,
)
from .cost_model import CostModel, calculate_cost_aware_pnl
from .backtesting import BacktestEngine, BacktestResult

__all__ = [
    "calculate_rsi_wilder",
    "calculate_bollinger_bands",
    "calculate_macd",
    "calculate_annualized_metrics",
    "calculate_drawdown_series",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_expectancy",
    "calculate_var_historical",
    "CostModel",
    "calculate_cost_aware_pnl",
    "BacktestEngine",
    "BacktestResult",
]
