import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data_loader import fetch_stock_data, preprocess_data, POPULAR_TICKERS
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
    plot_cumulative_returns_comparison,
    plot_correlation_heatmap
)

st.set_page_config(
    page_title="Stock Market Analytics & Signal Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        border-radius: 6px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .metric-card h4 {
        margin: 0;
        font-size: 0.85rem;
        color: #6c757d;
        text-transform: uppercase;
        font-weight: 600;
    }
    .metric-card p {
        margin: 4px 0 0 0;
        font-size: 1.4rem;
        font-weight: 700;
        color: #212529;
    }
    .signal-buy {
        color: #2ca02c;
        font-weight: bold;
    }
    .signal-sell {
        color: #d62728;
        font-weight: bold;
    }
    .signal-hold {
        color: #ff7f0e;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Stock Market Data Analysis & Signal Dashboard")
st.markdown("Analyze historical stock trends, technical indicators, risk metrics, and backtest SMA crossover trading strategies.")

# Sidebar Settings
st.sidebar.header("⚙️ Configuration Controls")

# Ticker Selection
preset_option = st.sidebar.selectbox(
    "Select Stock Ticker:",
    options=list(POPULAR_TICKERS.keys()),
    format_func=lambda x: f"{x} - {POPULAR_TICKERS[x]}"
)

custom_ticker = st.sidebar.text_input("Or Enter Custom Ticker (e.g. SPY, QQQ, NFLX):", value="")
ticker = custom_ticker.strip().upper() if custom_ticker.strip() else preset_option

# Date Range Selection
st.sidebar.subheader("📅 Date Horizon")
col_d1, col_d2 = st.sidebar.columns(2)
default_start = datetime.today() - timedelta(days=365*2)
default_end = datetime.today()

start_date = col_d1.date_input("Start Date", value=default_start)
end_date = col_d2.date_input("End Date", value=default_end)

# Strategy & Indicator Parameters
st.sidebar.subheader("📊 Indicator Tuning")
short_sma = st.sidebar.slider("Short Moving Average (Days)", min_value=5, max_value=50, value=20, step=5)
long_sma = st.sidebar.slider("Long Moving Average (Days)", min_value=20, max_value=200, value=50, step=5)
rsi_window = st.sidebar.slider("RSI Window (Days)", min_value=5, max_value=30, value=14)
bb_std = st.sidebar.slider("Bollinger Bands Std Dev", min_value=1.0, max_value=3.0, value=2.0, step=0.5)

# Load & Process Data
@st.cache_data(ttl=3600)
def get_processed_data(symbol, start, end, s_sma, l_sma, rsi_w, bb_s):
    raw_df = fetch_stock_data(symbol, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    df = preprocess_data(raw_df)
    df = calculate_moving_averages(df, sma_windows=[s_sma, l_sma])
    df = calculate_volatility(df, window=20)
    df = calculate_bollinger_bands(df, window=20, num_std=bb_s)
    df = calculate_rsi(df, window=rsi_w)
    df = calculate_macd(df)
    df = generate_trading_signals(df, short_window=s_sma, long_window=l_sma)
    return df

with st.spinner(f"Loading & processing data for {ticker}..."):
    try:
        df = get_processed_data(ticker, start_date, end_date, short_sma, long_sma, rsi_window, bb_std)
        summary = calculate_performance_summary(df)
    except Exception as e:
        st.error(f"Error processing dataset for {ticker}: {e}")
        st.stop()

# Header KPI Cards
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

last_close = summary['end_price']
prev_close = df['Close'].iloc[-2] if len(df) > 1 else last_close
day_change = last_close - prev_close
day_change_pct = (day_change / prev_close) * 100

with kpi1:
    st.markdown(f"""
        <div class="metric-card">
            <h4>Current Price</h4>
            <p>${last_close:.2f} <span style="font-size:0.9rem; color:{'green' if day_change>=0 else 'red'}">({day_change_pct:+.2f}%)</span></p>
        </div>
    """, unsafe_allow_html=True)

with kpi2:
    total_ret = summary['total_return'] * 100
    st.markdown(f"""
        <div class="metric-card">
            <h4>Period Return</h4>
            <p style="color:{'green' if total_ret>=0 else 'red'}">{total_ret:+.2f}%</p>
        </div>
    """, unsafe_allow_html=True)

with kpi3:
    ann_vol = summary['ann_volatility'] * 100
    st.markdown(f"""
        <div class="metric-card">
            <h4>Annual Volatility</h4>
            <p>{ann_vol:.2f}%</p>
        </div>
    """, unsafe_allow_html=True)

with kpi4:
    mdd = summary['max_drawdown'] * 100
    st.markdown(f"""
        <div class="metric-card">
            <h4>Max Drawdown</h4>
            <p style="color:#d62728;">{mdd:.2f}%</p>
        </div>
    """, unsafe_allow_html=True)

with kpi5:
    current_signal = df['Signal'].iloc[-1]
    signal_str = "BUY 🚀" if current_signal == 1 else ("SELL ⚠️" if current_signal == -1 else "NEUTRAL ➖")
    signal_class = "signal-buy" if current_signal == 1 else ("signal-sell" if current_signal == -1 else "signal-hold")
    st.markdown(f"""
        <div class="metric-card">
            <h4>Current Signal</h4>
            <p class="{signal_class}">{signal_str}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Main Content Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Price & Trend Analysis",
    "📊 Technical Indicators",
    "⚖️ Risk & Returns",
    "🤖 Trading Signals & Strategy",
    "🔗 Correlation Analysis",
    "💾 Raw Data & Export"
])

with tab1:
    st.subheader("Price Movement & Moving Averages Overlay")
    fig_price = plot_price_and_signals(df, ticker, short_sma, long_sma)
    st.pyplot(fig_price, use_container_width=True)
    
    st.subheader("Trading Volume & Volatility Dynamics")
    fig_vol = plot_volatility_and_volume(df, ticker)
    st.pyplot(fig_vol, use_container_width=True)

with tab2:
    col_ind1, col_ind2 = st.columns(2)
    with col_ind1:
        st.subheader("Relative Strength Index (RSI)")
        fig_rsi = plot_rsi(df, ticker)
        st.pyplot(fig_rsi, use_container_width=True)
        st.info("💡 **RSI Concept**: RSI values > 70 suggest overbought conditions (potential price correction), while RSI < 30 indicates oversold conditions (potential rebound).")

    with col_ind2:
        st.subheader("MACD (Moving Average Convergence Divergence)")
        fig_macd = plot_macd(df, ticker)
        st.pyplot(fig_macd, use_container_width=True)
        st.info("💡 **MACD Concept**: Bullish momentum increases when the MACD line crosses above the Signal line (green histogram bars).")

with tab3:
    col_r1, col_r2 = st.columns([1.2, 0.8])
    with col_r1:
        st.subheader("Daily Returns Distribution")
        fig_dist = plot_returns_distribution(df, ticker)
        st.pyplot(fig_dist, use_container_width=True)
    
    with col_r2:
        st.subheader("Key Risk Metrics")
        st.json({
            "Annualized Return": f"{summary['ann_return']*100:.2f}%",
            "Annualized Volatility": f"{summary['ann_volatility']*100:.2f}%",
            "Sharpe Ratio (Rf=2%)": f"{summary['sharpe_ratio']:.2f}",
            "Max Drawdown": f"{summary['max_drawdown']*100:.2f}%",
            "Average Daily Return": f"{df['Daily_Return'].mean()*100:.3f}%",
            "Daily Standard Deviation": f"{df['Daily_Return'].std()*100:.3f}%"
        })

with tab4:
    st.subheader("SMA Crossover Backtesting")
    st.write(f"Comparing **{short_sma}-Day / {long_sma}-Day SMA Golden Crossover Strategy** performance against Buy & Hold benchmark.")
    
    fig_strat = plot_cumulative_returns_comparison(df, ticker)
    st.pyplot(fig_strat, use_container_width=True)
    
    strat_ret = summary['strategy_total_return'] * 100 if summary['strategy_total_return'] is not None else 0
    bh_ret = summary['total_return'] * 100
    
    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.metric("Strategy Total Return", f"{strat_ret:+.2f}%")
    b_col2.metric("Buy & Hold Total Return", f"{bh_ret:+.2f}%")
    b_col3.metric("Alpha (Strategy - Benchmark)", f"{(strat_ret - bh_ret):+.2f}%")

with tab5:
    st.subheader("Cross-Asset Return Correlation Heatmap")
    selected_corr_tickers = st.multiselect(
        "Select Tickers for Correlation Analysis:",
        options=list(POPULAR_TICKERS.keys()),
        default=["AAPL", "MSFT", "GOOGL", "NVDA", "BTC-USD"]
    )
    
    if len(selected_corr_tickers) > 1:
        with st.spinner("Fetching data for correlation matrix..."):
            returns_dict = {}
            for t in selected_corr_tickers:
                try:
                    t_df = fetch_stock_data(t, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                    t_df = preprocess_data(t_df)
                    returns_dict[t] = t_df['Daily_Return']
                except Exception:
                    pass
            
            if returns_dict:
                combined_returns = pd.DataFrame(returns_dict).dropna()
                corr_matrix = combined_returns.corr()
                fig_corr = plot_correlation_heatmap(corr_matrix)
                st.pyplot(fig_corr, use_container_width=True)
    else:
        st.info("Select at least 2 tickers to generate correlation matrix.")

with tab6:
    st.subheader("Processed Historical Dataset")
    st.dataframe(df.style.highlight_null(color='yellow'), use_container_width=True)
    
    csv_bytes = df.to_csv().encode('utf-8')
    st.download_button(
        label=f"📥 Download {ticker} Data (CSV)",
        data=csv_bytes,
        file_name=f"{ticker}_stock_analytics_{datetime.today().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
