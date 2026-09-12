# 📈 Stock Market Data Analysis Dashboard

An interactive Python analytics dashboard built with **Pandas**, **Matplotlib**, **Seaborn**, and **Streamlit** to clean, process, visualize historical stock price data, and generate trading signals.

---

## 🌟 Key Features

1. **Stock Data Loader & Preprocessing**:
   - Live data ingestion from Yahoo Finance (`yfinance`) for customizable tickers and date ranges.
   - Intelligent offline fallback using Geometric Brownian Motion to generate synthetic stock data.
   - Cleans missing values, handles duplicates, and calculates daily returns, log returns, and cumulative returns.

2. **Technical Indicators & Metrics**:
   - **Simple Moving Averages (SMA)** & **Exponential Moving Averages (EMA)** (20-day, 50-day, 200-day).
   - **Rolling Volatility** (20-day annualized risk metric).
   - **Bollinger Bands** (Upper, Lower, Middle bands).
   - **Momentum Indicators**: Relative Strength Index (RSI - 14 day) and MACD (Moving Average Convergence Divergence with signal line & histogram).

3. **Trading Signal & Strategy Backtesting**:
   - Golden Cross / Death Cross moving average crossover trading signal generation.
   - Backtest engine evaluating strategy cumulative returns against Buy & Hold benchmark with Sharpe Ratio and Max Drawdown calculation.

4. **Interactive Dashboard**:
   - Interactive KPI cards for Current Price, Period Return, Volatility, Drawdown, and Live Signal.
   - Tabbed layout featuring technical analysis, risk distribution, strategy backtests, multi-stock correlation heatmaps, and raw data CSV exports.

---

## 📁 Project Architecture

```
stock-market-dashboard/
│
├── data_loader.py       # Data fetching & synthetic data generator fallback
├── analytics.py         # Technical indicators, volatility, RSI, MACD & backtesting engine
├── visualizer.py        # Matplotlib & Seaborn custom plot routines
├── app.py               # Main Streamlit web dashboard application
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation & guide
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Installation

Ensure you have Python 3.9+ installed.

```bash
# Clone or navigate to the workspace directory
cd stock-market-dashboard

# Install required packages
pip install -r requirements.txt
```

### 2. Launch the Interactive Dashboard

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 📐 Formulas & Methodology

- **Daily Return**: 
  $$R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$

- **Annualized Volatility**: 
  $$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{252}$$

- **Sharpe Ratio** ($R_f = 0.02$): 
  $$\text{Sharpe} = \frac{R_{\text{annual}} - R_f}{\sigma_{\text{annual}}}$$

- **RSI (Relative Strength Index)**: 
  $$\text{RSI} = 100 - \left( \frac{100}{1 + \frac{\text{Avg Gain}}{\text{Avg Loss}}} \right)$$

- **Bollinger Bands**: 
  $$\text{Upper / Lower} = \text{SMA}_{20} \pm (2 \times \sigma_{20})$$
