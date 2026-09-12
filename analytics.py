import pandas as pd
import numpy as np

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
        df['Daily_Return'] = df['Close'].pct_change()
        
    df[f'Rolling_Std_{window}'] = df['Daily_Return'].rolling(window=window).std()
    # Annualized volatility = daily std * sqrt(252 trading days)
    df[f'Annualized_Vol_{window}'] = df[f'Rolling_Std_{window}'] * np.sqrt(252)
    return df

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Bollinger Bands (Upper, Lower, Middle).
    """
    df = df.copy()
    sma = df['Close'].rolling(window=window).mean()
    std = df['Close'].rolling(window=window).std()
    
    df['BB_Middle'] = sma
    df['BB_Upper'] = sma + (std * num_std)
    df['BB_Lower'] = sma - (std * num_std)
    return df

def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Calculates Relative Strength Index (RSI).
    """
    df = df.copy()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    df['RSI'] = rsi.fillna(50)
    return df

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates MACD Line, Signal Line, and MACD Histogram.
    """
    df = df.copy()
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
    
    df['MACD'] = ema_fast - ema_slow
    df['MACD_Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df

def generate_trading_signals(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    """
    Generates trading signals based on SMA Golden/Death Crossover and calculates Strategy Returns.
    Signal convention: 1 = Buy / Long, -1 = Sell / Short, 0 = Hold / Neutral
    """
    df = df.copy()
    
    short_col = f'SMA_{short_window}'
    long_col = f'SMA_{long_window}'
    
    if short_col not in df.columns or long_col not in df.columns:
        df = calculate_moving_averages(df, sma_windows=[short_window, long_window])
        
    df['Signal'] = 0
    # Position: 1 when short SMA > long SMA, else -1
    df.loc[df[short_col] > df[long_col], 'Signal'] = 1
    df.loc[df[short_col] <= df[long_col], 'Signal'] = -1
    
    # Crossover Points: 2 = Buy trigger (crossover up), -2 = Sell trigger (crossover down)
    df['Position_Change'] = df['Signal'].diff()
    df['Buy_Signal'] = np.where(df['Position_Change'] == 2, df['Close'], np.nan)
    df['Sell_Signal'] = np.where(df['Position_Change'] == -2, df['Close'], np.nan)
    
    # Calculate Strategy Daily Returns (shift signal by 1 day to avoid look-ahead bias)
    if 'Daily_Return' not in df.columns:
        df['Daily_Return'] = df['Close'].pct_change()
        
    df['Strategy_Return'] = df['Signal'].shift(1) * df['Daily_Return']
    df['Strategy_Cumulative_Return'] = (1 + df['Strategy_Return'].fillna(0)).cumprod() - 1
    
    return df

def calculate_performance_summary(df: pd.DataFrame) -> dict:
    """
    Calculates summary performance metrics including Period Return, Volatility, Sharpe Ratio, and Max Drawdown.
    """
    if 'Daily_Return' not in df.columns:
        df = df.copy()
        df['Daily_Return'] = df['Close'].pct_change()

    total_return = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
    daily_mean = df['Daily_Return'].mean()
    daily_std = df['Daily_Return'].std()
    
    # Annualized Metrics
    ann_return = ((1 + daily_mean) ** 252) - 1 if not np.isnan(daily_mean) else 0.0
    ann_volatility = daily_std * np.sqrt(252) if not np.isnan(daily_std) else 0.0
    
    # Sharpe Ratio (Assuming 2% Risk-Free Rate)
    rf = 0.02
    sharpe_ratio = (ann_return - rf) / ann_volatility if ann_volatility > 0 else 0.0
    
    # Maximum Drawdown
    cum_returns = (1 + df['Daily_Return'].fillna(0)).cumprod()
    peak = cum_returns.cummax()
    drawdown = (cum_returns - peak) / peak
    max_drawdown = drawdown.min()
    
    # Strategy Return comparison if calculated
    strat_total_return = None
    if 'Strategy_Cumulative_Return' in df.columns:
        strat_total_return = df['Strategy_Cumulative_Return'].iloc[-1]

    return {
        "start_price": float(df['Close'].iloc[0]),
        "end_price": float(df['Close'].iloc[-1]),
        "total_return": float(total_return),
        "ann_return": float(ann_return),
        "ann_volatility": float(ann_volatility),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "strategy_total_return": float(strat_total_return) if strat_total_return is not None else None
    }
