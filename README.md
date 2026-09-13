# 📈 Stock Market Data Analysis & Signal Dashboard

An interactive, responsive standalone **Web Frontend Application** built with **HTML5**, **CSS3 (Glassmorphism design)**, **JavaScript**, and **Plotly.js** to clean, process, visualize historical stock price data, compute technical indicators, and backtest trading strategies.

---

## 🌟 Features & Highlights

1. **Instant VS Code Live Server Compatibility (`127.0.0.1:5500`)**:
   - Zero server requirements! Simply click **"Go Live"** in VS Code or double-click `index.html` to launch.
2. **1-Click Cloud Deployment**:
   - Native support for **Vercel**, **Netlify**, **GitHub Pages**, and **Streamlit Community Cloud**.
3. **Interactive Financial Charting (Plotly.js)**:
   - Interactive Candlestick charts with range selectors, volume overlays, hover tooltips, and signal markers.
   - Subplots for RSI (14-day) and MACD (12, 26, 9 with histogram bars).
   - $10,000 Initial Investment Strategy Backtest growth comparison against Buy & Hold benchmark.
   - Multi-asset return correlation heatmap.
4. **Quantitative Metrics & Risk Indicators**:
   - SMA 20, SMA 50, Bollinger Bands (20, 2), 20-Day Annualized Volatility.
   - Sharpe Ratio, Sortino Ratio, Max Drawdown %, and Value at Risk (VaR 95%).
5. **CSV Dataset Exporter**:
   - Download calculated indicators and processed data on demand.

---

## 📁 Repository Structure

```
stock-market-dashboard/
│
├── index.html           # Main Web Dashboard UI entry point
├── styles.css           # Modern Dark Glassmorphism CSS design system
├── app.js               # Client-side Quantitative Math & Plotly.js Charting Engine
├── vercel.json          # Vercel deployment configuration
├── README.md            # Project documentation & usage guide
│
├── app.py               # (Optional) Streamlit Python dashboard app
├── data_loader.py       # Python data fetching module
├── analytics.py         # Python quantitative metrics engine
├── visualizer.py        # Python Matplotlib/Seaborn plotting module
└── requirements.txt     # Python dependencies
```

---

## 🚀 How to Run Locally

### Method 1: VS Code Live Server (Easiest)
1. Open the project folder in VS Code.
2. Click **"Go Live"** at the bottom right status bar (or right-click `index.html` $\rightarrow$ *Open with Live Server*).
3. The dashboard opens instantly at `http://127.0.0.1:5500`.

### Method 2: Open `index.html` directly in any Browser
Double-click `index.html` to open it in Chrome, Edge, Brave, or Firefox!

---

## 🌐 Cloud Deployment (Vercel & GitHub Pages)

- **Vercel**: Import repository `ankit1713sr/stock-market-dashboard` on Vercel. It deploys instantly as a static website.
- **GitHub Pages**: Go to Repository Settings $\rightarrow$ Pages $\rightarrow$ Select `main` branch $\rightarrow$ Save.
