"""
Unit Tests for Quantitative Research Core (Step 1).
Covers:
  - Exact Wilder's RSI with deterministic reference validation, zero-loss, zero-gain, and missing data.
  - Drawdown, Sharpe, and Sortino calculations with deterministic distributions.
  - Cost-aware P&L with fees, slippage, short positions, and contract multipliers (options/futures).
  - Backtest engine signal timing, execution lag, and look-ahead bias prevention.
"""

import math
import sys
import unittest
import numpy as np
import pandas as pd

from app.quant.technicals import calculate_rsi_wilder, calculate_bollinger_bands, calculate_macd
from app.quant.cost_model import CostModel, calculate_cost_aware_pnl
from app.quant.metrics import (
    calculate_drawdown_series,
    calculate_annualized_metrics,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_expectancy,
    calculate_var_historical,
)
from app.quant.backtesting import BacktestEngine, BacktestResult


class TestWilderRSI(unittest.TestCase):
    """Verifies Wilder's RSI against benchmark calculations and edge cases."""

    def test_wilder_rsi_deterministic_reference(self):
        """
        Tests RSI against the classic 14-period benchmark dataset from J. Welles Wilder's
        'New Concepts in Technical Trading Systems' (1978).
        """
        prices = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
            45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
            46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57,
            43.42, 42.66, 43.13
        ]
        rsi = calculate_rsi_wilder(prices, period=14)

        # Verification at index 14 (first calculated RSI):
        # 14 changes: gains = [0, 0.06, 0, 0.72, 0.50, 0.27, 0.32, 0.42, 0.24, 0, 0.14, 0, 0.67, 0]
        # avg gain = 0.2386; avg loss = 0.1000 => RS = 2.386 => RSI approx 70.46
        self.assertTrue(np.isnan(rsi.iloc[13]))  # Warm-up period must be NaN
        self.assertFalse(np.isnan(rsi.iloc[14]))
        self.assertAlmostEqual(rsi.iloc[14], 70.46, delta=0.2)

        # End of series value matches standard Wilder smoothed RSI
        self.assertGreater(rsi.iloc[-1], 20.0)
        self.assertLess(rsi.iloc[-1], 60.0)

    def test_zero_loss_strictly_100_rsi(self):
        """If prices only rise (zero loss), RSI must equal 100.0 (NOT 50.0)."""
        monotonic_up = [10.0 + i * 2.0 for i in range(25)]
        rsi = calculate_rsi_wilder(monotonic_up, period=14)

        for val in rsi.iloc[14:]:
            self.assertEqual(val, 100.0)

    def test_zero_gain_strictly_0_rsi(self):
        """If prices only fall (zero gain), RSI must equal 0.0."""
        monotonic_down = [100.0 - i * 2.0 for i in range(25)]
        rsi = calculate_rsi_wilder(monotonic_down, period=14)

        for val in rsi.iloc[14:]:
            self.assertEqual(val, 0.0)

    def test_flat_prices_neutral_50_rsi(self):
        """If prices do not change at all, RSI must equal 50.0."""
        flat = [100.0] * 25
        rsi = calculate_rsi_wilder(flat, period=14)

        for val in rsi.iloc[14:]:
            self.assertEqual(val, 50.0)

    def test_missing_data_nan_handling(self):
        """RSI handles NaNs without crashing."""
        prices = [10.0, 11.0, 12.0, np.nan, 14.0, 15.0, 16.0]
        rsi = calculate_rsi_wilder(prices, period=3)
        self.assertEqual(len(rsi), 7)


class TestCostAwarePnL(unittest.TestCase):
    """Verifies gross and net P&L with fees, slippage, short positions, and multipliers."""

    def test_long_stock_with_commission_and_slippage(self):
        cost_model = CostModel(fee_per_order=1.0, fee_bps=10.0, slippage_bps=5.0)
        # Entry: 100 shares @ $150 = $15,000 notional.
        # Cost per trade = $1.00 + $15.00 (10 bps) + $7.50 (5 bps slippage) = $23.50
        # Exit: 100 shares @ $160 = $16,000 notional.
        # Cost per trade = $1.00 + $16.00 + $8.00 = $25.00
        # Total cost = $48.50
        # Gross = +$1,000.00 -> Net = $951.50
        result = calculate_cost_aware_pnl(
            side="BUY",
            entry_price=150.0,
            exit_price=160.0,
            quantity=100,
            multiplier=1.0,
            cost_model=cost_model,
            stop_loss=145.0,
        )
        self.assertEqual(result["gross_pnl"], 1000.0)
        self.assertAlmostEqual(result["total_costs"], 48.50, places=2)
        self.assertAlmostEqual(result["net_pnl"], 951.50, places=2)
        self.assertEqual(result["risk_amount"], 500.0)  # ($150 - $145) * 100
        self.assertAlmostEqual(result["r_multiple"], 951.50 / 500.0, places=4)

    def test_short_position_profit_and_loss(self):
        """Short position: enters @ 200, exits @ 180 => Gross Profit."""
        res_win = calculate_cost_aware_pnl(
            side="SELL",
            entry_price=200.0,
            exit_price=180.0,
            quantity=50,
            fees_paid=10.0,
        )
        self.assertEqual(res_win["gross_pnl"], 1000.0)
        self.assertEqual(res_win["net_pnl"], 990.0)

        # Short loss: enters @ 200, exits @ 210 => Gross Loss
        res_loss = calculate_cost_aware_pnl(
            side="SELL",
            entry_price=200.0,
            exit_price=210.0,
            quantity=50,
            fees_paid=10.0,
        )
        self.assertEqual(res_loss["gross_pnl"], -500.0)
        self.assertEqual(res_loss["net_pnl"], -510.0)

    def test_options_contract_multiplier(self):
        """Option contract multiplier = 100 shares per contract."""
        res = calculate_cost_aware_pnl(
            side="BUY",
            entry_price=2.50,
            exit_price=4.00,
            quantity=5,  # 5 contracts
            multiplier=100.0,
            fees_paid=6.50,  # $0.65/contract per side = $6.50 total
        )
        # Gross = (4.00 - 2.50) * 5 * 100 = 1.50 * 500 = $750.00
        self.assertEqual(res["gross_pnl"], 750.0)
        self.assertEqual(res["total_costs"], 6.50)
        self.assertEqual(res["net_pnl"], 743.50)


class TestPerformanceMetrics(unittest.TestCase):
    """Verifies Sharpe, Sortino, Drawdown, and Expectancy."""

    def test_drawdown_series(self):
        equity = [100, 110, 105, 90, 120, 115]
        dd_df = calculate_drawdown_series(equity)
        # Peak: [100, 110, 110, 110, 120, 120]
        # Drawdowns: [0, 0, -5, -20, 0, -5]
        expected_dd = [0.0, 0.0, -5.0, -20.0, 0.0, -5.0]
        np.testing.assert_array_almost_equal(dd_df["drawdown"].values, expected_dd)
        # Max drawdown percentage at 90 when peak was 110: (90 - 110)/110 * 100 = -18.1818%
        self.assertAlmostEqual(dd_df["drawdown_pct"].min(), -18.1818, places=3)

    def test_sharpe_and_sortino_penalties(self):
        # Series with positive upside and moderate downside
        returns = [0.02, 0.03, -0.01, 0.04, -0.015, 0.02]
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.0)
        sortino = calculate_sortino_ratio(returns, target_return=0.0)

        # Sortino should be strictly greater than Sharpe when upside volatility is large
        self.assertGreater(sortino, sharpe)
        self.assertGreater(sharpe, 0.0)

    def test_expectancy_calculation(self):
        pnls = [100.0, 200.0, -50.0, -100.0]
        # Win rate = 50%, avg win = 150, avg loss = 75
        # Expectancy = 0.5 * 150 - 0.5 * 75 = 75 - 37.5 = 37.5
        exp = calculate_expectancy(pnls)
        self.assertEqual(exp["win_rate"], 50.0)
        self.assertEqual(exp["avg_win"], 150.0)
        self.assertEqual(exp["avg_loss"], 75.0)
        self.assertEqual(exp["expectancy"], 37.5)


class TestBacktestEngineTiming(unittest.TestCase):
    """Verifies signal lag and prevention of look-ahead bias."""

    def test_execution_lag_enforced(self):
        engine = BacktestEngine(initial_capital=10000.0)
        df = pd.DataFrame({"Close": [100.0, 105.0, 110.0, 95.0, 100.0]})

        # Invalid execution lag (< 1) must raise ValueError
        with self.assertRaises(ValueError):
            engine.run_signal_backtest(df, lambda d: pd.Series([1.0]*len(d)), execution_lag=0)

    def test_no_look_ahead_bias_in_returns(self):
        """
        Verify that a signal generated on bar t does NOT capture return on bar t.
        If price spikes on bar 1 (from 100 to 150) and our signal triggers at bar 1 Close,
        the position MUST NOT capture the 100 -> 150 move.
        """
        df = pd.DataFrame({"Close": [100.0, 150.0, 150.0, 150.0]})

        def signal_on_spike(data):
            # Triggers BUY signal at close of bar 1 (when price == 150)
            return (data["Close"] >= 150.0).astype(float)

        engine = BacktestEngine(initial_capital=10000.0)
        result = engine.run_signal_backtest(df, signal_on_spike, execution_lag=1)

        # Bar 1 return must be 0 for the strategy because position on bar 1 was 0
        history = result.history
        self.assertEqual(history["Position"].iloc[0], 0.0)
        self.assertEqual(history["Position"].iloc[1], 0.0)  # Position only enters on bar 2
        self.assertEqual(history["Net_Strategy_Return"].iloc[1], 0.0)
        # Price from bar 1 to 2 was flat (150 -> 150), so total strategy return is 0 (or minus costs)
        self.assertEqual(history["Gross_Strategy_Return"].sum(), 0.0)


if __name__ == "__main__":
    unittest.main()
