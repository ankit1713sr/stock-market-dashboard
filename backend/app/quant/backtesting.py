"""Causal, close-executed, single-instrument backtesting.

At close t, execute the target submitted at close t-lag, then observe close t
and generate a new target from a COPY of df[:t+1]. Holdings established at
close t earn only subsequent close-to-close moves. Targets are allocations
[-1,1] sized on pre-order equity; unchanged targets retain units (no implicit
rebalance). Reversals are a close and a new entry, each with its own fee.
Completed trades are flat-to-flat position episodes, including partial exits.
Open positions are marked to market, not silently liquidated at the end.
"""
from dataclasses import dataclass, field
from numbers import Integral
from typing import Optional
import numpy as np
import pandas as pd
from .cost_model import CostModel, _number
from .metrics import calculate_annualized_metrics, calculate_drawdown_series, calculate_expectancy


@dataclass
class BacktestResult:
    trades_count: int
    total_return: float
    ann_return: float
    ann_volatility: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: Optional[float]
    history: pd.DataFrame
    completed_trades: list = field(default_factory=list)


class BacktestEngine:
    def __init__(self, cost_model=None, initial_capital=100000.0,
                 risk_free_rate=0.02, periods_per_year=252, multiplier=1.0):
        self.cost_model = cost_model or CostModel()
        self.initial_capital = _number(initial_capital, "initial_capital", positive=True)
        self.multiplier = _number(multiplier, "multiplier", positive=True)
        self.risk_free_rate = float(risk_free_rate)
        self.periods_per_year = _number(periods_per_year, "periods_per_year", positive=True)
        # Validate even when no data is provided.
        calculate_annualized_metrics([], self.risk_free_rate, self.periods_per_year)

    @staticmethod
    def _signal(callback, prefix):
        output = callback(prefix.copy(deep=True))
        if isinstance(output, pd.Series):
            if not output.index.equals(prefix.index):
                raise ValueError("Signal series must align exactly with the historical prefix")
            output = output.iloc[-1]
        if not np.isscalar(output):
            raise ValueError("Strategy must return a scalar or prefix-indexed Series")
        value = float(output)
        if np.isnan(value):
            return 0.0  # An unavailable/warm-up signal is flat.
        if not np.isfinite(value) or not -1 <= value <= 1:
            raise ValueError("Target position must be finite and within [-1,1]")
        return value

    def run_signal_backtest(self, df, signal_generator, price_col="Close", execution_lag=1):
        """Signals execute at price_col on bar t+lag (default next Close).

        Input columns must themselves be causal; callbacks must not use outside
        data/closures. This is temporal API isolation, not a Python security sandbox.
        Missing execution prices and unsorted/duplicate bars are rejected.
        """
        if isinstance(execution_lag, bool) or not isinstance(execution_lag, Integral) or execution_lag < 1:
            raise ValueError("execution_lag must be an integer >= 1")
        if price_col not in df:
            raise KeyError(f"Price column '{price_col}' not found in data.")
        if not df.index.is_unique or not df.index.is_monotonic_increasing:
            raise ValueError("Bars must have unique, chronological indices")
        prices = df[price_col].astype(float)
        if not np.isfinite(prices).all() or (prices <= 0).any():
            raise ValueError("Execution prices must be positive and finite")
        data = df.copy()
        signals, rows, completed = [], [], []
        cash, qty, last_target = self.initial_capital, 0.0, 0.0
        average_entry = episode_pnl = 0.0
        entry_bar = None
        previous_equity, previous_price = self.initial_capital, None
        mult = self.multiplier
        for i, price in enumerate(prices):
            pre_equity = cash + qty * price * mult
            if pre_equity <= 0:
                raise ValueError("Portfolio is insolvent; leveraged loss exceeds available capital")
            gross = (qty * (price - previous_price) * mult) if previous_price is not None else 0.0
            target = signals[i - execution_lag] if i >= execution_lag else 0.0
            cost = turnover = 0.0
            if target != last_target:
                desired = target * pre_equity / (price * mult)
                # Close/reduce before increasing or reversing. Track one episode
                # through same-side scaling, allocating all its execution costs.
                if qty and (desired * qty <= 0 or abs(desired) < abs(qty)):
                    closing = abs(qty) if desired * qty <= 0 else abs(qty) - abs(desired)
                    direction = np.sign(qty)
                    fee = self.cost_model.calculate_order_cost(price, closing, mult)
                    cash += direction * closing * price * mult - fee
                    episode_pnl += direction * closing * (price - average_entry) * mult - fee
                    cost += fee
                    turnover += closing * price * mult
                    qty -= direction * closing
                    if abs(qty) < 1e-12:
                        qty = 0.0
                        completed.append({"entry_bar": entry_bar, "exit_bar": data.index[i],
                                          "net_pnl": float(episode_pnl)})
                        episode_pnl = average_entry = 0.0
                        entry_bar = None
                delta = desired - qty
                if abs(delta) > 1e-12:
                    fee = self.cost_model.calculate_order_cost(price, abs(delta), mult)
                    if qty == 0:
                        entry_bar = data.index[i]
                    average_entry = (abs(qty) * average_entry + abs(delta) * price) / (abs(qty) + abs(delta))
                    cash -= delta * price * mult + fee
                    episode_pnl -= fee
                    cost += fee
                    turnover += abs(delta) * price * mult
                    qty = desired
                last_target = target
            equity = cash + qty * price * mult
            if equity <= 0:
                raise ValueError("Execution costs exhaust portfolio capital")
            signals.append(self._signal(signal_generator, df.iloc[:i+1]))
            rows.append(dict(Raw_Signal=signals[-1], Position=target, Quantity=qty,
                             Asset_Return=price / previous_price - 1 if previous_price is not None else 0.0,
                             Trade_Delta=turnover / pre_equity, Cost=cost,
                             Cost_Pct=cost / previous_equity,
                             Gross_Strategy_Return=gross / previous_equity,
                             Net_Strategy_Return=(equity - previous_equity) / previous_equity,
                             Portfolio_Value=equity))
            previous_equity, previous_price = equity, price
        columns = ["Raw_Signal", "Position", "Quantity", "Asset_Return", "Trade_Delta", "Cost",
                   "Cost_Pct", "Gross_Strategy_Return", "Net_Strategy_Return", "Portfolio_Value"]
        history = pd.DataFrame(rows, index=data.index, columns=columns, dtype=float)
        for col in columns:
            data[col] = history[col]
        dd = calculate_drawdown_series(data["Portfolio_Value"], self.initial_capital)
        data["Peak_Value"], data["Drawdown_Pct"] = dd["peak"], dd["drawdown_pct"]
        # First row is an initial observation, not an elapsed return interval.
        metrics = calculate_annualized_metrics(data["Net_Strategy_Return"].iloc[1:],
                                               self.risk_free_rate, self.periods_per_year)
        stats = calculate_expectancy([t["net_pnl"] for t in completed])
        return BacktestResult(len(completed), round(previous_equity / self.initial_capital - 1, 6),
                              metrics["ann_return"], metrics["ann_volatility"], metrics["sharpe_ratio"],
                              round(float(dd["drawdown_pct"].min()), 4) if len(dd) else 0.0,
                              stats["win_rate"], stats["profit_factor"], data, completed)
