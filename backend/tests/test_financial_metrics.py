import unittest
from math import isclose
from app.services import (
    calculate_trade_metrics,
    calculate_position_size,
    dashboard_summary,
    calendar_month,
    group_analytics,
)


class MockTrade:
    def __init__(self, id, trade_date, symbol, side, qty, entry_price, exit_price, stop_loss=None, strategy="Breakout", emotion="Disciplined", mistake="None", rating=5, is_demo=False):
        self.id = id
        self.trade_date = trade_date
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.stop_loss = stop_loss
        self.target_price = None
        self.strategy = strategy
        self.emotion = emotion
        self.mistake = mistake
        self.rating = rating
        self.notes = ""
        self.chart_url = ""
        self.asset = "Stock"
        self.is_demo = is_demo
        self.created_at = None
        self.updated_at = None

        metrics = calculate_trade_metrics(side, entry_price, exit_price, qty, stop_loss)
        self.pnl = metrics["pnl"]
        self.return_pct = metrics["return_pct"]
        self.risk_amount = metrics["risk_amount"]
        self.r_multiple = metrics["r_multiple"]


class TestFinancialMetrics(unittest.TestCase):

    def test_trade_metrics_buy_profit(self):
        # Buy 100 shares at $100, exit at $110, stop loss at $95 (risk $5/share = $500)
        res = calculate_trade_metrics("BUY", 100.0, 110.0, 100, stop_loss=95.0)
        self.assertEqual(res["pnl"], 1000.0)
        self.assertAlmostEqual(res["return_pct"], 10.0, places=2)
        self.assertEqual(res["risk_amount"], 500.0)
        self.assertAlmostEqual(res["r_multiple"], 2.0, places=2)

    def test_trade_metrics_buy_loss(self):
        # Buy 100 shares at $100, exit at $95, stop loss at $95
        res = calculate_trade_metrics("BUY", 100.0, 95.0, 100, stop_loss=95.0)
        self.assertEqual(res["pnl"], -500.0)
        self.assertAlmostEqual(res["return_pct"], -5.0, places=2)
        self.assertEqual(res["risk_amount"], 500.0)
        self.assertAlmostEqual(res["r_multiple"], -1.0, places=2)

    def test_trade_metrics_sell_profit(self):
        # Short 50 shares at $200, exit at $180 (profit $1000), stop loss at $210 (risk $10/share = $500)
        res = calculate_trade_metrics("SELL", 200.0, 180.0, 50, stop_loss=210.0)
        self.assertEqual(res["pnl"], 1000.0)
        self.assertAlmostEqual(res["return_pct"], 10.0, places=2)
        self.assertEqual(res["risk_amount"], 500.0)
        self.assertAlmostEqual(res["r_multiple"], 2.0, places=2)

    def test_position_sizing(self):
        # $25,000 balance, 1% risk ($250), entry $100, stop $98 (risk $2/unit) -> 125 shares
        res = calculate_position_size(25000, 1.0, 100.0, 98.0)
        self.assertEqual(res["dollar_risk"], 250.0)
        self.assertEqual(res["risk_per_unit"], 2.0)
        self.assertEqual(res["quantity"], 125)

    def test_dashboard_summary_empty(self):
        summary = dashboard_summary([])
        self.assertEqual(summary["total_trades"], 0)
        self.assertEqual(summary["net_pnl"], 0.0)
        self.assertEqual(summary["win_rate"], 0.0)
        self.assertEqual(summary["profit_factor"], 0.0)
        self.assertEqual(summary["max_drawdown_pct"], 0.0)
        self.assertEqual(summary["avg_r_multiple"], 0.0)
        self.assertEqual(len(summary["equity_curve"]), 0)

    def test_dashboard_summary_win_rate_and_drawdown(self):
        # 3 trades: +$1000, -$500, +$1500
        # initial equity = $10,000
        # Day 1: +1000 -> equity $11,000 (peak $11,000, dd 0%)
        # Day 2: -500  -> equity $10,500 (peak $11,000, dd = -4.545%)
        # Day 3: +1500 -> equity $12,000 (peak $12,000, dd 0%)
        trades = [
            MockTrade(1, "2026-09-01", "AAPL", "BUY", 100, 100, 110, stop_loss=95),  # pnl +1000, R=+2.0
            MockTrade(2, "2026-09-02", "TSLA", "BUY", 100, 100, 95, stop_loss=95),   # pnl -500, R=-1.0
            MockTrade(3, "2026-09-03", "NVDA", "BUY", 100, 100, 115, stop_loss=95),  # pnl +1500, R=+3.0
        ]
        summary = dashboard_summary(trades, initial_equity=10000)
        self.assertEqual(summary["total_trades"], 3)
        self.assertEqual(summary["wins"], 2)
        self.assertEqual(summary["losses"], 1)
        self.assertAlmostEqual(summary["win_rate"], 66.67, places=1)
        self.assertEqual(summary["net_pnl"], 2000.0)
        # Gross profit = 2500, Gross loss = 500 -> PF = 5.0
        self.assertAlmostEqual(summary["profit_factor"], 5.0, places=2)
        # Avg R multiple: (2 - 1 + 3) / 3 = 1.33R
        self.assertAlmostEqual(summary["avg_r_multiple"], 1.33, places=2)
        # Max drawdown: (10500 - 11000) / 11000 * 100 = -4.545%
        self.assertAlmostEqual(summary["max_drawdown_pct"], -4.55, places=2)

    def test_calendar_month_aggregation(self):
        trades = [
            MockTrade(1, "2026-09-01", "AAPL", "BUY", 100, 100, 110),
            MockTrade(2, "2026-09-01", "TSLA", "BUY", 50, 200, 210),
            MockTrade(3, "2026-09-05", "NVDA", "BUY", 100, 100, 90),
            MockTrade(4, "2026-10-01", "MSFT", "BUY", 100, 100, 110),
        ]
        cal = calendar_month(trades, 2026, 9)
        self.assertEqual(cal["year"], 2026)
        self.assertEqual(cal["month"], 9)
        self.assertEqual(len(cal["days"]), 2)
        day1 = next(d for d in cal["days"] if d["date"] == "2026-09-01")
        self.assertEqual(day1["trade_count"], 2)
        self.assertEqual(day1["pnl"], 1500.0)


if __name__ == "__main__":
    unittest.main()
