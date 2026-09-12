import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless mode for testing

from data_loader import fetch_stock_data, preprocess_data
from analytics import (
    calculate_moving_averages,
    calculate_volatility,
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_macd,
    generate_trading_signals,
    calculate_performance_summary
)
from visualizer import (
    plot_price_and_signals,
    plot_rsi,
    plot_macd,
    plot_volatility_and_volume,
    plot_returns_distribution,
    plot_cumulative_returns_comparison
)

def run_tests():
    print("--- 1. Testing Data Loader ---")
    df_raw = fetch_stock_data("AAPL", "2023-01-01", "2024-01-01")
    assert not df_raw.empty, "Fetched data is empty!"
    print(f"Data shape: {df_raw.shape}, Columns: {list(df_raw.columns)}")

    print("\n--- 2. Testing Preprocessing ---")
    df = preprocess_data(df_raw)
    assert 'Daily_Return' in df.columns, "Daily_Return missing"
    assert 'Cumulative_Return' in df.columns, "Cumulative_Return missing"

    print("\n--- 3. Testing Analytics & Indicators ---")
    df = calculate_moving_averages(df, sma_windows=[20, 50], ema_windows=[12, 26])
    assert 'SMA_20' in df.columns and 'SMA_50' in df.columns, "SMA calculation failed"

    df = calculate_volatility(df, window=20)
    assert 'Annualized_Vol_20' in df.columns, "Volatility calculation failed"

    df = calculate_bollinger_bands(df, window=20, num_std=2.0)
    assert 'BB_Upper' in df.columns and 'BB_Lower' in df.columns, "Bollinger bands calculation failed"

    df = calculate_rsi(df, window=14)
    assert 'RSI' in df.columns, "RSI calculation failed"

    df = calculate_macd(df)
    assert 'MACD' in df.columns and 'MACD_Signal' in df.columns, "MACD calculation failed"

    df = generate_trading_signals(df, short_window=20, long_window=50)
    assert 'Signal' in df.columns and 'Strategy_Cumulative_Return' in df.columns, "Trading signal generation failed"

    summary = calculate_performance_summary(df)
    print(f"Performance Summary: {summary}")

    print("\n--- 4. Testing Visualization Plots ---")
    fig1 = plot_price_and_signals(df, "AAPL")
    fig2 = plot_rsi(df, "AAPL")
    fig3 = plot_macd(df, "AAPL")
    fig4 = plot_volatility_and_volume(df, "AAPL")
    fig5 = plot_returns_distribution(df, "AAPL")
    fig6 = plot_cumulative_returns_comparison(df, "AAPL")
    print("All Matplotlib/Seaborn figures generated successfully!")

    print("\n[OK] ALL PIPELINE TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    run_tests()

