# ⚡ TradePulse AI – Smart Trading Journal & Market Analytics

**TradePulse AI** is a comprehensive, AI-powered trading journal and quantitative performance analytics platform built with **HTML5**, **CSS3 (Cyber-Dark Glassmorphism design)**, **JavaScript**, and **Plotly.js**. 

Designed for stock, options, crypto, and forex traders to log trades, track net P&L, analyze trading psychology, eliminate execution mistakes, and review live market technical charts.

---

## 🌟 Core Modules & Features

1. **🔐 Authentication & Multi-Account Switcher**:
   - Cyber-Dark Glassmorphism Login Modal with Quick 1-Click Demo Trader Login.
   - Dynamic top navbar user profile badge (*Ankit Mishra - PRO TRADER*) and multi-account switcher (**Personal Portfolio**, **Prop Firm Funded Account**, **Paper Sandbox**).

2. **📖 Interactive Trade Logger & Journal**:
   - Modal trade entry form (Date, Ticker, Side, Asset Class, Entry/Exit Price, Quantity, Strategy, Emotion, Mistake, Rating, Notes, Chart Snapshot URL).
   - Searchable, filterable trade history log with color-coded P&L indicators, strategy pills, and **📸 Lightbox Chart Snapshot Viewers**.

3. **🛡️ Risk Guard & Position Size Calculator**:
   - **Smart Position Sizer**: Calculates exact recommended shares/contracts based on Account Balance, Risk %, Entry Price, and Stop Loss.
   - **Daily Risk Protocol Guard**: Configurable daily max loss limit with automatic **Risk Protocol Warning Alert** banners.

4. **📚 Execution Strategy Playbook & Checklist**:
   - Interactive pre-trade verification checklist enforcing setup alignment, volume spikes, and risk:reward ≥ 2:1 discipline.

5. **📰 Economic Macro News Feed**:
   - High-impact economic calendar widget tracking CPI Inflation reports, FOMC Rate Decisions, and ECB Monetary Policy announcements.

6. **📅 Interactive Monthly P&L Calendar**:
   - Visual monthly calendar grid displaying daily net P&L ($ amount and % return) for every day of the month.

7. **🤖 AI Coach & Behavioral Insights Engine**:
   - Automated AI performance diagnosis generating plain-English insights (highest win-rate setup, best trading days, emotion drag).
   - **Mistakes Cost Breakdown**: Visualizing the exact dollar loss caused by trading mistakes (e.g. FOMO, Early Exit, Over-leveraging).

8. **📈 Equity Curve & Performance Analytics**:
   - Interactive Plotly Equity Curve tracking account balance over time.
   - Win Rate %, Profit Factor, Avg Win / Avg Loss ratio, Sharpe Ratio, Sortino Ratio, Max Drawdown %.

9. **📊 Technical Market Charting**:
   - Expanded live technical charts supporting US Megacap Tech (AAPL, MSFT, NVDA, TSLA, META, AMZN, NFLX, AMD, INTC), Finance (JPM, V, DIS), Crypto (BTC, ETH, SOL), and Indian Equities (RELIANCE, TCS, INFY).

10. **💾 Backup & CSV Data Export**:
    - Export your entire trading journal dataset to a standard CSV file or reset to default sample seed data.

---

## 📁 Repository Structure

```
stock-market-dashboard/
│
├── index.html           # TradePulse AI UI entry point & tab navigation
├── styles.css           # Cyber-Dark Glassmorphism CSS design system
├── app.js               # Trade Journal Engine, LocalStorage, AI Coach & Plotly charts
├── vercel.json          # Vercel static deployment router
├── README.md            # Documentation & project guide
│
├── app.py               # (Optional) Python Streamlit dashboard
├── data_loader.py       # Python data fetching module
├── analytics.py         # Python quantitative metrics engine
├── visualizer.py        # Python plotting module
└── requirements.txt     # Python dependencies
```

---

## 🚀 How to Launch & Run

### VS Code Live Server (`127.0.0.1:5500`)
1. Open the project folder in VS Code.
2. Click **"Go Live"** at the bottom status bar (or right-click `index.html` $\rightarrow$ *Open with Live Server*).
3. Open `http://127.0.0.1:5500` in your browser.

### Cloud Deployment (Vercel & GitHub Pages)
- **Vercel**: Native zero-error deployment via [ankit1713sr/stock-market-dashboard](https://github.com/ankit1713sr/stock-market-dashboard).
