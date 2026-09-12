import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set cohesive style settings
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica, Arial, DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

PRIMARY_COLOR = '#1f77b4' # Muted Blue
SECONDARY_COLOR = '#ff7f0e' # Coral Orange
BUY_COLOR = '#2ca02c' # Vibrant Green
SELL_COLOR = '#d62728' # Vibrant Red
ACCENT_COLOR = '#9467bd' # Purple

def plot_price_and_signals(df: pd.DataFrame, ticker: str, short_window: int = 20, long_window: int = 50) -> plt.Figure:
    """
    Plots Close price, SMA overlays, and Buy/Sell trading signals.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(df.index, df['Close'], label=f'{ticker} Close Price', color='#2b2b2b', alpha=0.75, linewidth=1.5)
    
    short_col = f'SMA_{short_window}'
    long_col = f'SMA_{long_window}'
    
    if short_col in df.columns:
        ax.plot(df.index, df[short_col], label=f'{short_window}-Day SMA', color=PRIMARY_COLOR, linestyle='--', linewidth=1.8)
    if long_col in df.columns:
        ax.plot(df.index, df[long_col], label=f'{long_window}-Day SMA', color=SECONDARY_COLOR, linestyle='--', linewidth=1.8)
        
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        ax.plot(df.index, df['BB_Upper'], color='gray', linestyle=':', alpha=0.5, label='Bollinger Upper')
        ax.plot(df.index, df['BB_Lower'], color='gray', linestyle=':', alpha=0.5, label='Bollinger Lower')
        ax.fill_between(df.index, df['BB_Lower'], df['BB_Upper'], color='gray', alpha=0.08)

    # Signal markers
    if 'Buy_Signal' in df.columns and df['Buy_Signal'].notna().any():
        ax.scatter(df.index, df['Buy_Signal'], marker='^', color=BUY_COLOR, s=120, label='Buy Signal (Golden Cross)', zorder=5)
    if 'Sell_Signal' in df.columns and df['Sell_Signal'].notna().any():
        ax.scatter(df.index, df['Sell_Signal'], marker='v', color=SELL_COLOR, s=120, label='Sell Signal (Death Cross)', zorder=5)
        
    ax.set_title(f'{ticker} - Historical Stock Price & Trading Signals', fontsize=14, fontweight='bold', pad=12)
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
    plt.tight_layout()
    return fig

def plot_rsi(df: pd.DataFrame, ticker: str) -> plt.Figure:
    """
    Plots Relative Strength Index (RSI) with 30/70 thresholds.
    """
    fig, ax = plt.subplots(figsize=(12, 3.5))
    
    if 'RSI' in df.columns:
        ax.plot(df.index, df['RSI'], color=ACCENT_COLOR, linewidth=1.5, label='RSI (14)')
        ax.axhline(70, color=SELL_COLOR, linestyle='--', alpha=0.7, label='Overbought (70)')
        ax.axhline(30, color=BUY_COLOR, linestyle='--', alpha=0.7, label='Oversold (30)')
        ax.fill_between(df.index, 70, df['RSI'], where=(df['RSI'] >= 70), color=SELL_COLOR, alpha=0.2)
        ax.fill_between(df.index, 30, df['RSI'], where=(df['RSI'] <= 30), color=BUY_COLOR, alpha=0.2)
        
    ax.set_title(f'{ticker} - Relative Strength Index (RSI)', fontsize=12, fontweight='bold')
    ax.set_ylabel('RSI', fontsize=10)
    ax.set_ylim(0, 100)
    ax.legend(loc='upper left', frameon=True, facecolor='white')
    plt.tight_layout()
    return fig

def plot_macd(df: pd.DataFrame, ticker: str) -> plt.Figure:
    """
    Plots MACD line, Signal line, and MACD Histogram.
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
        ax.plot(df.index, df['MACD'], label='MACD Line', color=PRIMARY_COLOR, linewidth=1.5)
        ax.plot(df.index, df['MACD_Signal'], label='Signal Line', color=SECONDARY_COLOR, linewidth=1.5)
        
        hist = df['MACD_Hist']
        colors = np.where(hist >= 0, BUY_COLOR, SELL_COLOR)
        ax.bar(df.index, hist, color=colors, alpha=0.5, label='MACD Hist', width=1.0)
        
    ax.set_title(f'{ticker} - Moving Average Convergence Divergence (MACD)', fontsize=12, fontweight='bold')
    ax.set_ylabel('MACD Value', fontsize=10)
    ax.legend(loc='upper left', frameon=True, facecolor='white')
    plt.tight_layout()
    return fig

def plot_volatility_and_volume(df: pd.DataFrame, ticker: str) -> plt.Figure:
    """
    Plots Volume and 20-Day Annualized Volatility subplots.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    
    # Volume subplot
    colors = np.where(df['Close'] >= df['Open'], BUY_COLOR, SELL_COLOR)
    ax1.bar(df.index, df['Volume'] / 1e6, color=colors, alpha=0.6, width=1.0)
    ax1.set_title(f'{ticker} - Trading Volume (Millions)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Volume (M)', fontsize=10)
    
    # Volatility subplot
    vol_col = [c for c in df.columns if 'Annualized_Vol' in c]
    if vol_col:
        ax2.plot(df.index, df[vol_col[0]] * 100, color='#e377c2', linewidth=1.8, label='20-Day Annualized Volatility (%)')
        ax2.set_ylabel('Volatility (%)', fontsize=10)
        ax2.set_title(f'{ticker} - Rolling Volatility Trends', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper left', frameon=True, facecolor='white')
        
    ax2.set_xlabel('Date', fontsize=10)
    plt.tight_layout()
    return fig

def plot_returns_distribution(df: pd.DataFrame, ticker: str) -> plt.Figure:
    """
    Plots histogram and Kernel Density Estimation (KDE) of Daily Returns.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    if 'Daily_Return' in df.columns:
        returns = df['Daily_Return'].dropna() * 100
        sns.histplot(returns, kde=True, ax=ax, color=PRIMARY_COLOR, bins=50, stat="density", alpha=0.5)
        mean_ret = returns.mean()
        std_ret = returns.std()
        
        ax.axvline(mean_ret, color=SELL_COLOR, linestyle='--', linewidth=1.5, label=f'Mean Return: {mean_ret:.2f}%')
        ax.axvline(mean_ret - 2*std_ret, color='gray', linestyle=':', label=f'-2 Std Dev ({mean_ret - 2*std_ret:.2f}%)')
        ax.axvline(mean_ret + 2*std_ret, color='gray', linestyle=':', label=f'+2 Std Dev ({mean_ret + 2*std_ret:.2f}%)')
        
    ax.set_title(f'{ticker} - Daily Returns Distribution (%)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Daily Return (%)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.legend(loc='upper right', frameon=True, facecolor='white')
    plt.tight_layout()
    return fig

def plot_cumulative_returns_comparison(df: pd.DataFrame, ticker: str) -> plt.Figure:
    """
    Plots Strategy Cumulative Return vs Buy & Hold Cumulative Return.
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    
    if 'Cumulative_Return' in df.columns:
        ax.plot(df.index, df['Cumulative_Return'] * 100, label=f'{ticker} Buy & Hold', color='#2b2b2b', linewidth=2.0)
    if 'Strategy_Cumulative_Return' in df.columns:
        ax.plot(df.index, df['Strategy_Cumulative_Return'] * 100, label='SMA Crossover Strategy', color=BUY_COLOR, linewidth=2.0)
        
    ax.axhline(0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    ax.set_title(f'{ticker} - Strategy Backtest vs. Buy & Hold Benchmark (%)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Return (%)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(loc='upper left', frameon=True, facecolor='white')
    plt.tight_layout()
    return fig

def plot_correlation_heatmap(corr_matrix: pd.DataFrame) -> plt.Figure:
    """
    Plots correlation matrix heatmap across multiple assets.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1, ax=ax, cbar=True, square=True)
    ax.set_title('Asset Price Correlation Matrix', fontsize=14, fontweight='bold', pad=12)
    plt.tight_layout()
    return fig
