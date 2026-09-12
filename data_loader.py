import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POPULAR_TICKERS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla, Inc.",
    "AMZN": "Amazon.com Inc.",
    "BTC-USD": "Bitcoin (USD)"
}

def generate_synthetic_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Generates realistic synthetic stock data using Geometric Brownian Motion
    when live network data is unavailable.
    """
    logger.info(f"Generating synthetic stock data for {ticker} from {start_date} to {end_date}")
    dates = pd.date_range(start=start_date, end=end_date, freq='B') # Business days
    if len(dates) == 0:
        dates = pd.date_range(end=datetime.today(), periods=252, freq='B')

    np.random.seed(hash(ticker) % 2**32)
    
    # Base initial prices per ticker family
    base_prices = {
        "AAPL": 180.0, "MSFT": 410.0, "GOOGL": 175.0,
        "NVDA": 120.0, "TSLA": 220.0, "AMZN": 185.0, "BTC-USD": 60000.0
    }
    s0 = base_prices.get(ticker, 100.0)
    mu = 0.0005  # Daily drift
    sigma = 0.02 # Daily volatility
    
    returns = np.random.normal(mu, sigma, len(dates))
    price_paths = s0 * np.exp(np.cumsum(returns))
    
    # Create Open, High, Low, Close
    high_noise = np.abs(np.random.normal(0, 0.008, len(dates)))
    low_noise = np.abs(np.random.normal(0, 0.008, len(dates)))
    
    close_prices = price_paths
    open_prices = close_prices * (1 + np.random.normal(0, 0.003, len(dates)))
    high_prices = np.maximum(open_prices, close_prices) * (1 + high_noise)
    low_prices = np.minimum(open_prices, close_prices) * (1 - low_noise)
    volumes = np.random.randint(10_000_000, 80_000_000, len(dates))
    
    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Adj Close': close_prices,
        'Volume': volumes
    }, index=dates)
    
    df.index.name = 'Date'
    return df

def fetch_stock_data(ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetches stock data using yfinance. Falls back to synthetic data generator on error.
    """
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    ticker = ticker.strip().upper()
    
    try:
        import yfinance as yf
        logger.info(f"Fetching live data for {ticker} via yfinance...")
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            # Flatten multi-level columns if present
            data.columns = data.columns.get_level_values(0)
            
        if data.empty or len(data) < 5:
            logger.warning(f"yfinance returned empty data for {ticker}. Falling back to synthetic generator.")
            return generate_synthetic_data(ticker, start_date, end_date)
            
        # Standardize columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in data.columns:
                logger.warning(f"Missing column {col} in fetched data for {ticker}.")
                return generate_synthetic_data(ticker, start_date, end_date)
                
        if 'Adj Close' not in data.columns:
            data['Adj Close'] = data['Close']
            
        data = data.dropna()
        return data

    except Exception as e:
        logger.warning(f"Failed to fetch live data for {ticker}: {e}. Using synthetic fallback.")
        return generate_synthetic_data(ticker, start_date, end_date)

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans data and calculates core returns metrics.
    """
    df = df.copy()
    
    # Sort index chronologically
    df.sort_index(inplace=True)
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    # Fill any remaining NaNs
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    
    # Calculate daily percentage returns
    df['Daily_Return'] = df['Close'].pct_change()
    
    # Calculate daily log returns
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # Calculate cumulative returns
    df['Cumulative_Return'] = (1 + df['Daily_Return'].fillna(0)).cumprod() - 1
    
    return df
