"""
Technical indicators with mathematically robust formulations.
Implements J. Welles Wilder's exact RSI calculation including smoothing initialization and edge cases.
"""

from typing import Union
import numpy as np
import pandas as pd


def calculate_rsi_wilder(prices, period=14, column="Close", warmup_neutral=False):
    """Wilder RSI seeded with period consecutive price changes.

    A missing price resets smoothing; require period+1 consecutive prices to
    resume. Missing inputs always yield NaN. warmup_neutral displays 50 only
    for observed prices during warm-up, never imputing a missing price.
    """
    if isinstance(period, bool) or not isinstance(period, (int, np.integer)) or period <= 0:
        raise ValueError("period must be a positive integer")
    if isinstance(prices, pd.DataFrame):
        s = prices[column].astype(float).copy()
    else:
        s = pd.Series(prices, dtype=float).copy()
    if np.isinf(s).any():
        raise ValueError("Prices must be finite or NaN")
    out = pd.Series(np.nan, index=s.index, dtype=float)
    previous = None
    count = 0
    gain_sum = loss_sum = 0.0
    avg_gain = avg_loss = None
    for i, price in enumerate(s):
        if pd.isna(price):
            previous = None
            count = 0
            gain_sum = loss_sum = 0.0
            avg_gain = avg_loss = None
            continue
        if warmup_neutral:
            out.iloc[i] = 50.0
        if previous is None:
            previous = price
            continue
        change = price - previous
        previous = price
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if avg_gain is None:
            count += 1
            gain_sum += gain
            loss_sum += loss
            if count < period:
                continue
            avg_gain, avg_loss = gain_sum / period, loss_sum / period
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        out.iloc[i] = (50.0 if avg_gain == avg_loss == 0 else
                       100.0 if avg_loss == 0 else
                       100.0 - 100.0 / (1.0 + avg_gain / avg_loss))
    return out


def calculate_bollinger_bands(
    prices: Union[pd.Series, pd.DataFrame],
    window: int = 20,
    num_std: float = 2.0,
    column: str = "Close",
) -> pd.DataFrame:
    """
    Calculates standard Bollinger Bands (Upper, Middle, Lower, Bandwidth).
    """
    if isinstance(prices, pd.DataFrame):
        s = prices[column].astype(float)
    else:
        s = prices.astype(float)

    middle = s.rolling(window=window).mean()
    std = s.rolling(window=window).std(ddof=0)
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    bandwidth = np.where(middle > 0, (upper - lower) / middle, 0.0)

    return pd.DataFrame(
        {
            "BB_Middle": middle,
            "BB_Upper": upper,
            "BB_Lower": lower,
            "BB_Bandwidth": bandwidth,
        },
        index=s.index,
    )


def calculate_macd(
    prices: Union[pd.Series, pd.DataFrame],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "Close",
) -> pd.DataFrame:
    """
    Calculates standard MACD, Signal Line, and Histogram.
    """
    if isinstance(prices, pd.DataFrame):
        s = prices[column].astype(float)
    else:
        s = prices.astype(float)

    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {
            "MACD": macd_line,
            "MACD_Signal": signal_line,
            "MACD_Hist": histogram,
        },
        index=s.index,
    )
