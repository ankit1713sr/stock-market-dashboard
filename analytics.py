import pandas as pd
import numpy as np
from backend.app.quant.technicals import (
    calculate_rsi_wilder, calculate_bollinger_bands as quant_bollinger,
    calculate_macd as quant_macd,
)
from backend.app.quant.metrics import calculate_annualized_metrics
from backend.app.quant.backtesting import BacktestEngine

def calculate_moving_averages(df: pd.DataFrame, sma_windows=[20, 50, 200], ema_windows=[12, 26]) -> pd.DataFrame:
    """
    Calculates Simple Moving Averages (SMA) and Exponential Moving Averages (EMA).
    """
    df = df.copy()
    for w in sma_windows:
        df[f'SMA_{w}'] = df['Close'].rolling(window=w).mean()
    for w in ema_windows:
        df[f'EMA_{w}'] = df['Close'].ewm(span=w, adjust=False).mean()
    return df

def calculate_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Calculates rolling daily volatility and annualized volatility.
    """
    df = df.copy()
    if 'Daily_Return' not in df.columns:
        df['Daily_Return'] = df['Close'].pct_change(fill_method=None)
        
    df[f'Rolling_Std_{window}'] = df['Daily_Return'].rolling(window=window).std()
    # Annualized volatility = daily std * sqrt(252 trading days)
    df[f'Annualized_Vol_{window}'] = df[f'Rolling_Std_{window}'] * np.sqrt(252)
    return df

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Bollinger Bands (Upper, Lower, Middle).
    """
    result = quant_bollinger(df, window=window, num_std=num_std)
    return df.copy().assign(**{col: result[col] for col in result})


def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Calculates Relative Strength Index (RSI).
    """
    return df.copy().assign(RSI=calculate_rsi_wilder(df, period=window))


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates MACD Line, Signal Line, and MACD Histogram.
    """
    result = quant_macd(df, fast=fast, slow=slow, signal=signal)
    return df.copy().assign(**{col: result[col] for col in result})


def generate_trading_signals(df, short_window=20, long_window=50, cost_model=None):
    """Causal SMA strategy. A close signal executes at the NEXT close.

    Optional costs are research-only; default zero retains legacy UI controls.
    Recompute SMAs from each historical prefix, ignoring any supplied SMA values.
    """
    df = df.copy()
    def strategy(prefix):
        prices = prefix["Close"]
        if len(prices) < max(short_window, long_window):
            return 0.0
        short = prices.iloc[-short_window:].mean()
        long = prices.iloc[-long_window:].mean()
        return 1.0 if short > long else -1.0
    if short_window <= 0 or long_window <= 0:
        raise ValueError("SMA windows must be positive")
    result = BacktestEngine(cost_model=cost_model).run_signal_backtest(df, strategy)
    history = result.history
    df["Signal"] = history["Raw_Signal"]
    df["Position_Change"] = df["Signal"].diff()
    df["Buy_Signal"] = np.where(df["Position_Change"] > 0, df["Close"], np.nan)
    df["Sell_Signal"] = np.where(df["Position_Change"] < 0, df["Close"], np.nan)
    df["Strategy_Return"] = history["Net_Strategy_Return"]
    df["Strategy_Cumulative_Return"] = history["Portfolio_Value"] / 100000.0 - 1
    return df


def calculate_performance_summary(df):
    """Shared validated metrics, retaining the Streamlit response keys."""
    prices = df["Close"].astype(float)
    returns = prices.pct_change(fill_method=None).iloc[1:]
    metrics = calculate_annualized_metrics(returns)
    return {
        "start_price": float(prices.iloc[0]) if len(prices) else 0.0,
        "end_price": float(prices.iloc[-1]) if len(prices) else 0.0,
        "total_return": metrics["total_return"], "ann_return": metrics["ann_return"],
        "ann_volatility": metrics["ann_volatility"], "sharpe_ratio": metrics["sharpe_ratio"],
        "max_drawdown": metrics["max_drawdown_pct"] / 100,
        "strategy_total_return": float(df["Strategy_Cumulative_Return"].iloc[-1])
        if len(df) and "Strategy_Cumulative_Return" in df else None,
    }
