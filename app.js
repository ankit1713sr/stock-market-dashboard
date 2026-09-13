// Global State
let currentSymbol = 'AAPL';
let processedData = null;

// Preset Ticker Initial Prices for Fallback Data Engine
const TICKER_BASES = {
  'AAPL': { price: 185.0, name: 'Apple Inc.' },
  'MSFT': { price: 420.0, name: 'Microsoft Corp.' },
  'GOOGL': { price: 175.0, name: 'Alphabet Inc.' },
  'NVDA': { price: 125.0, name: 'NVIDIA Corp.' },
  'TSLA': { price: 230.0, name: 'Tesla Inc.' },
  'BTC-USD': { price: 62000.0, name: 'Bitcoin' }
};

// Initialize App on DOM Load
document.addEventListener('DOMContentLoaded', () => {
  setupDefaultDates();
  setupEventListeners();
  loadDashboardData(currentSymbol);
});

function setupDefaultDates() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 2);

  document.getElementById('endDate').value = end.toISOString().split('T')[0];
  document.getElementById('startDate').value = start.toISOString().split('T')[0];
}

function setupEventListeners() {
  // Tab Switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      const tabId = e.target.getAttribute('data-tab');
      e.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');

      // Trigger Plotly relayout to adjust responsive widths
      window.dispatchEvent(new Event('resize'));
    });
  });

  // Ticker Pills Selection
  document.querySelectorAll('.ticker-pills .pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      document.querySelectorAll('.ticker-pills .pill').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      currentSymbol = e.target.getAttribute('data-symbol');
      document.getElementById('tickerSelect').value = currentSymbol;
      document.getElementById('customTickerInput').value = '';
      loadDashboardData(currentSymbol);
    });
  });

  // Ticker Dropdown Select
  document.getElementById('tickerSelect').addEventListener('change', (e) => {
    currentSymbol = e.target.value;
    document.getElementById('customTickerInput').value = '';
    syncPillState(currentSymbol);
    loadDashboardData(currentSymbol);
  });

  // Update Button
  document.getElementById('updateBtn').addEventListener('click', () => {
    const custom = document.getElementById('customTickerInput').value.trim().toUpperCase();
    if (custom) {
      currentSymbol = custom;
    } else {
      currentSymbol = document.getElementById('tickerSelect').value;
    }
    loadDashboardData(currentSymbol);
  });

  // CSV Download Button
  document.getElementById('downloadCsvBtn').addEventListener('click', exportCSV);
}

function syncPillState(symbol) {
  document.querySelectorAll('.ticker-pills .pill').forEach(p => {
    if (p.getAttribute('data-symbol') === symbol) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });
}

function showLoading(show) {
  document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

// ----------------------------------------------------
// Data Engine: Synthetic Geometric Brownian Motion
// ----------------------------------------------------
function generateData(symbol, startDateStr, endDateStr) {
  const dates = [];
  const start = new Date(startDateStr);
  const end = new Date(endDateStr);
  
  let curr = new Date(start);
  while (curr <= end) {
    const day = curr.getDay();
    if (day !== 0 && day !== 6) { // Skip weekends
      dates.push(new Date(curr));
    }
    curr.setDate(curr.getDate() + 1);
  }
  
  if (dates.length === 0) return null;

  const baseObj = TICKER_BASES[symbol] || { price: 100.0, name: symbol };
  let price = baseObj.price;
  const mu = 0.0006;
  const sigma = 0.018;

  // Pseudo random hash for consistent data generation per symbol
  let seed = 0;
  for (let i = 0; i < symbol.length; i++) seed += symbol.charCodeAt(i);

  const seededRandom = () => {
    const x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
  };

  const opens = [], highs = [], lows = [], closes = [], volumes = [];

  for (let i = 0; i < dates.length; i++) {
    const u1 = seededRandom();
    const u2 = seededRandom();
    const z = Math.sqrt(-2.0 * Math.log(u1 || 0.001)) * Math.cos(2.0 * Math.PI * u2);

    const ret = mu + sigma * z;
    const close = price * Math.exp(ret);
    const open = price * (1 + (seededRandom() - 0.5) * 0.006);
    const high = Math.max(open, close) * (1 + seededRandom() * 0.012);
    const low = Math.min(open, close) * (1 - seededRandom() * 0.012);
    const volume = Math.floor(10000000 + seededRandom() * 50000000);

    opens.push(open);
    highs.push(high);
    lows.push(low);
    closes.push(close);
    volumes.push(volume);

    price = close;
  }

  return {
    dates: dates.map(d => d.toISOString().split('T')[0]),
    open: opens,
    high: highs,
    low: lows,
    close: closes,
    volume: volumes
  };
}

// ----------------------------------------------------
// Financial Mathematics & Technical Indicators
// ----------------------------------------------------
function computeIndicators(raw) {
  const n = raw.close.length;
  const close = raw.close;

  // Daily Returns & Cumulative Returns
  const dailyReturns = [0];
  const cumReturns = [0];
  let cumProd = 1.0;

  for (let i = 1; i < n; i++) {
    const ret = (close[i] - close[i - 1]) / close[i - 1];
    dailyReturns.push(ret);
    cumProd *= (1 + ret);
    cumReturns.push(cumProd - 1);
  }

  // SMA 20 & SMA 50
  const sma20 = calculateSMA(close, 20);
  const sma50 = calculateSMA(close, 50);

  // Bollinger Bands (20, 2)
  const bb = calculateBollingerBands(close, 20, 2.0);

  // RSI 14
  const rsi = calculateRSI(close, 14);

  // MACD (12, 26, 9)
  const macd = calculateMACD(close, 12, 26, 9);

  // Rolling Volatility (20-day annualized)
  const rollingVol = calculateRollingVol(dailyReturns, 20);

  // Signals & Strategy Returns (Golden Cross SMA 20 vs 50)
  const signals = [];
  const buySignals = new Array(n).fill(null);
  const sellSignals = new Array(n).fill(null);
  const stratReturns = [0];

  let position = 0;
  for (let i = 0; i < n; i++) {
    if (i >= 50 && sma20[i] !== null && sma50[i] !== null) {
      if (sma20[i] > sma50[i]) {
        if (position !== 1 && i > 0) buySignals[i] = close[i];
        position = 1;
      } else {
        if (position !== -1 && i > 0) sellSignals[i] = close[i];
        position = -1;
      }
    }
    signals.push(position);
    if (i > 0) {
      stratReturns.push(position * dailyReturns[i]);
    }
  }

  // Strategy Cumulative Return ($10,000 initial investment simulator)
  const stratCumValue = [10000];
  const bhCumValue = [10000];
  let sVal = 10000;
  let bhVal = 10000;

  for (let i = 1; i < n; i++) {
    sVal *= (1 + stratReturns[i]);
    bhVal *= (1 + dailyReturns[i]);
    stratCumValue.push(sVal);
    bhCumValue.push(bhVal);
  }

  return {
    ...raw,
    dailyReturns,
    cumReturns,
    sma20,
    sma50,
    bbUpper: bb.upper,
    bbLower: bb.lower,
    rsi,
    macd: macd.line,
    macdSignal: macd.signal,
    macdHist: macd.hist,
    rollingVol,
    signals,
    buySignals,
    sellSignals,
    stratReturns,
    stratCumValue,
    bhCumValue
  };
}

function calculateSMA(data, period) {
  const res = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      res.push(null);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += data[j];
      res.push(sum / period);
    }
  }
  return res;
}

function calculateBollingerBands(data, period, numStd) {
  const upper = [], lower = [];
  const sma = calculateSMA(data, period);

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push(null);
      lower.push(null);
    } else {
      let sumSq = 0;
      const mean = sma[i];
      for (let j = i - period + 1; j <= i; j++) {
        sumSq += Math.pow(data[j] - mean, 2);
      }
      const std = Math.sqrt(sumSq / period);
      upper.push(mean + numStd * std);
      lower.push(mean - numStd * std);
    }
  }
  return { upper, lower };
}

function calculateRSI(data, period) {
  const rsi = [];
  let gains = 0, losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = data[i] - data[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;
  rsi.push(...new Array(period).fill(50));

  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i] - data[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    if (avgLoss === 0) {
      rsi.push(100);
    } else {
      const rs = avgGain / avgLoss;
      rsi.push(100 - (100 / (1 + rs)));
    }
  }
  return rsi;
}

function calculateEMA(data, period) {
  const k = 2 / (period + 1);
  const ema = [data[0]];
  for (let i = 1; i < data.length; i++) {
    ema.push(data[i] * k + ema[i - 1] * (1 - k));
  }
  return ema;
}

function calculateMACD(data, fastP, slowP, signalP) {
  const emaFast = calculateEMA(data, fastP);
  const emaSlow = calculateEMA(data, slowP);
  const macdLine = emaFast.map((v, i) => v - emaSlow[i]);
  const signalLine = calculateEMA(macdLine, signalP);
  const hist = macdLine.map((v, i) => v - signalLine[i]);

  return { line: macdLine, signal: signalLine, hist };
}

function calculateRollingVol(returns, period) {
  const res = [];
  for (let i = 0; i < returns.length; i++) {
    if (i < period - 1) {
      res.push(null);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += returns[j];
      const mean = sum / period;

      let sumSq = 0;
      for (let j = i - period + 1; j <= i; j++) sumSq += Math.pow(returns[j] - mean, 2);
      const dailyStd = Math.sqrt(sumSq / period);
      res.push(dailyStd * Math.sqrt(252)); // Annualized
    }
  }
  return res;
}

// ----------------------------------------------------
// Main Dashboard Controller & Plotly Rendering
// ----------------------------------------------------
function loadDashboardData(symbol) {
  showLoading(true);

  setTimeout(() => {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    const raw = generateData(symbol, startDate, endDate);
    if (!raw) {
      showLoading(false);
      alert('Invalid date range!');
      return;
    }

    processedData = computeIndicators(raw);
    updateKPICards(processedData, symbol);
    renderAllPlots(processedData, symbol);
    renderDataTable(processedData);

    showLoading(false);
  }, 250);
}

function updateKPICards(df, symbol) {
  const n = df.close.length;
  const lastClose = df.close[n - 1];
  const prevClose = df.close[n - 2] || lastClose;
  const change = lastClose - prevClose;
  const changePct = (change / prevClose) * 100;

  document.getElementById('kpiPrice').innerHTML = `$${lastClose.toFixed(2)}`;
  const changeEl = document.getElementById('kpiChange');
  changeEl.innerHTML = `${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}% ($${change.toFixed(2)})`;
  changeEl.className = `kpi-subtext ${changePct >= 0 ? 'text-green' : 'text-red'}`;

  const periodReturn = df.cumReturns[n - 1] * 100;
  const retEl = document.getElementById('kpiReturn');
  retEl.innerHTML = `${periodReturn >= 0 ? '+' : ''}${periodReturn.toFixed(2)}%`;
  retEl.className = `kpi-value ${periodReturn >= 0 ? 'text-green' : 'text-red'}`;

  const annVol = (df.rollingVol[n - 1] || 0) * 100;
  document.getElementById('kpiVol').innerHTML = `${annVol.toFixed(2)}%`;

  // Max Drawdown calculation
  let peak = -Infinity;
  let maxDD = 0;
  for (let i = 0; i < n; i++) {
    if (df.close[i] > peak) peak = df.close[i];
    const dd = (df.close[i] - peak) / peak;
    if (dd < maxDD) maxDD = dd;
  }
  document.getElementById('kpiDrawdown').innerHTML = `${(maxDD * 100).toFixed(2)}%`;

  const signal = df.signals[n - 1];
  const sigEl = document.getElementById('kpiSignal');
  if (signal === 1) {
    sigEl.innerHTML = 'BUY 🚀';
    sigEl.className = 'kpi-value text-green';
  } else if (signal === -1) {
    sigEl.innerHTML = 'SELL ⚠️';
    sigEl.className = 'kpi-value text-red';
  } else {
    sigEl.innerHTML = 'NEUTRAL ➖';
    sigEl.className = 'kpi-value text-cyan';
  }

  // Risk Table Metrics
  const meanRet = df.dailyReturns.reduce((a, b) => a + b, 0) / n;
  const stdRet = Math.sqrt(df.dailyReturns.reduce((a, b) => a + Math.pow(b - meanRet, 2), 0) / n);
  const annRet = (Math.pow(1 + meanRet, 252) - 1) * 100;
  const annVolVal = stdRet * Math.sqrt(252) * 100;
  const sharpe = (annRet - 2.0) / (annVolVal || 1);

  // Sortino Ratio (Downside std)
  const downsideReturns = df.dailyReturns.filter(r => r < 0);
  const downsideStd = Math.sqrt(downsideReturns.reduce((a, b) => a + Math.pow(b, 2), 0) / n) * Math.sqrt(252);
  const sortino = downsideStd > 0 ? (annRet - 2.0) / (downsideStd * 100) : 0;

  // VaR 95%
  const sortedReturns = [...df.dailyReturns].sort((a, b) => a - b);
  const var95 = sortedReturns[Math.floor(n * 0.05)] * 100;

  document.getElementById('riskAnnReturn').innerHTML = `${annRet >= 0 ? '+' : ''}${annRet.toFixed(2)}%`;
  document.getElementById('riskAnnVol').innerHTML = `${annVolVal.toFixed(2)}%`;
  document.getElementById('riskSharpe').innerHTML = sharpe.toFixed(2);
  document.getElementById('riskSortino').innerHTML = sortino.toFixed(2);
  document.getElementById('riskMaxDD').innerHTML = `${(maxDD * 100).toFixed(2)}%`;
  document.getElementById('riskVaR95').innerHTML = `${var95.toFixed(2)}%`;
}

function renderAllPlots(df, symbol) {
  const commonLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 30, b: 40 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)' },
    yaxis: { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)' }
  };

  // 1. Candlestick + Indicators Chart
  document.getElementById('priceChartTitle').innerHTML = `${symbol} - Candlestick & Moving Averages (20 / 50 SMA)`;

  const candleTrace = {
    x: df.dates,
    open: df.open,
    high: df.high,
    low: df.low,
    close: df.close,
    type: 'candlestick',
    name: symbol,
    increasing: { line: { color: '#10b981' } },
    decreasing: { line: { color: '#f43f5e' } }
  };

  const sma20Trace = {
    x: df.dates,
    y: df.sma20,
    type: 'scatter',
    mode: 'lines',
    name: '20 SMA',
    line: { color: '#38bdf8', width: 1.8, dash: 'dot' }
  };

  const sma50Trace = {
    x: df.dates,
    y: df.sma50,
    type: 'scatter',
    mode: 'lines',
    name: '50 SMA',
    line: { color: '#f59e0b', width: 1.8, dash: 'dot' }
  };

  const bbUpperTrace = {
    x: df.dates,
    y: df.bbUpper,
    type: 'scatter',
    mode: 'lines',
    name: 'Bollinger Upper',
    line: { color: 'rgba(148, 163, 184, 0.4)', width: 1 }
  };

  const bbLowerTrace = {
    x: df.dates,
    y: df.bbLower,
    type: 'scatter',
    mode: 'lines',
    name: 'Bollinger Lower',
    line: { color: 'rgba(148, 163, 184, 0.4)', width: 1 },
    fill: 'tonexty',
    fillcolor: 'rgba(148, 163, 184, 0.05)'
  };

  // Buy / Sell Signal Markers
  const buyTrace = {
    x: df.dates.filter((_, i) => df.buySignals[i] !== null),
    y: df.buySignals.filter(v => v !== null),
    type: 'scatter',
    mode: 'markers',
    name: 'Buy Signal',
    marker: { symbol: 'triangle-up', size: 12, color: '#10b981' }
  };

  const sellTrace = {
    x: df.dates.filter((_, i) => df.sellSignals[i] !== null),
    y: df.sellSignals.filter(v => v !== null),
    type: 'scatter',
    mode: 'markers',
    name: 'Sell Signal',
    marker: { symbol: 'triangle-down', size: 12, color: '#f43f5e' }
  };

  Plotly.newPlot('pricePlot', [candleTrace, sma20Trace, sma50Trace, bbUpperTrace, bbLowerTrace, buyTrace, sellTrace], {
    ...commonLayout,
    xaxis: { ...commonLayout.xaxis, rangeslider: { visible: false } },
    legend: { orientation: 'h', y: 1.15 }
  });

  // 2. Volume Plot
  const volumeTrace = {
    x: df.dates,
    y: df.volume.map(v => v / 1e6),
    type: 'bar',
    name: 'Volume (M)',
    marker: { color: df.close.map((c, i) => c >= df.open[i] ? 'rgba(16, 185, 129, 0.6)' : 'rgba(244, 63, 94, 0.6)') }
  };

  Plotly.newPlot('volumePlot', [volumeTrace], {
    ...commonLayout,
    yaxis: { ...commonLayout.yaxis, title: 'Volume (Millions)' }
  });

  // 3. RSI Plot
  const rsiTrace = {
    x: df.dates,
    y: df.rsi,
    type: 'scatter',
    mode: 'lines',
    name: 'RSI (14)',
    line: { color: '#a855f7', width: 2 }
  };

  Plotly.newPlot('rsiPlot', [rsiTrace], {
    ...commonLayout,
    yaxis: { ...commonLayout.yaxis, range: [0, 100], title: 'RSI' },
    shapes: [
      { type: 'line', y0: 70, y1: 70, x0: df.dates[0], x1: df.dates[df.dates.length - 1], line: { color: '#f43f5e', dash: 'dash' } },
      { type: 'line', y0: 30, y1: 30, x0: df.dates[0], x1: df.dates[df.dates.length - 1], line: { color: '#10b981', dash: 'dash' } }
    ]
  });

  // 4. MACD Plot
  const macdTrace = { x: df.dates, y: df.macd, type: 'scatter', mode: 'lines', name: 'MACD', line: { color: '#06b6d4', width: 1.8 } };
  const macdSigTrace = { x: df.dates, y: df.macdSignal, type: 'scatter', mode: 'lines', name: 'Signal', line: { color: '#f59e0b', width: 1.8 } };
  const macdHistTrace = {
    x: df.dates,
    y: df.macdHist,
    type: 'bar',
    name: 'Histogram',
    marker: { color: df.macdHist.map(h => h >= 0 ? '#10b981' : '#f43f5e') }
  };

  Plotly.newPlot('macdPlot', [macdTrace, macdSigTrace, macdHistTrace], {
    ...commonLayout,
    legend: { orientation: 'h', y: 1.15 }
  });

  // 5. Strategy Investment Growth Plot ($10,000 Initial Investment)
  const stratGrowthTrace = {
    x: df.dates,
    y: df.stratCumValue,
    type: 'scatter',
    mode: 'lines',
    name: 'SMA Crossover Strategy ($)',
    line: { color: '#10b981', width: 2.5 }
  };

  const bhGrowthTrace = {
    x: df.dates,
    y: df.bhCumValue,
    type: 'scatter',
    mode: 'lines',
    name: `${symbol} Buy & Hold ($)`,
    line: { color: '#38bdf8', width: 2 }
  };

  Plotly.newPlot('strategyPlot', [stratGrowthTrace, bhGrowthTrace], {
    ...commonLayout,
    yaxis: { ...commonLayout.yaxis, title: 'Portfolio Value ($)' },
    legend: { orientation: 'h', y: 1.15 }
  });

  // 6. Distribution Plot
  const distTrace = {
    x: df.dailyReturns.map(r => r * 100),
    type: 'histogram',
    name: 'Daily Returns (%)',
    marker: { color: 'rgba(56, 189, 248, 0.6)', line: { color: '#06b6d4', width: 1 } },
    nbinsx: 40
  };

  Plotly.newPlot('distributionPlot', [distTrace], {
    ...commonLayout,
    xaxis: { ...commonLayout.xaxis, title: 'Daily Return (%)' },
    yaxis: { ...commonLayout.yaxis, title: 'Frequency' }
  });

  // 7. Correlation Heatmap
  renderCorrelationHeatmap(commonLayout);
}

function renderCorrelationHeatmap(commonLayout) {
  const tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'BTC'];
  const z = [
    [1.00, 0.78, 0.72, 0.68, 0.55, 0.32],
    [0.78, 1.00, 0.81, 0.71, 0.52, 0.28],
    [0.72, 0.81, 1.00, 0.69, 0.48, 0.30],
    [0.68, 0.71, 0.69, 1.00, 0.62, 0.41],
    [0.55, 0.52, 0.48, 0.62, 1.00, 0.45],
    [0.32, 0.28, 0.30, 0.41, 0.45, 1.00]
  ];

  const heatmapTrace = {
    x: tickers,
    y: tickers,
    z: z,
    type: 'heatmap',
    colorscale: 'Viridis',
    showscale: true
  };

  Plotly.newPlot('correlationPlot', [heatmapTrace], {
    ...commonLayout,
    margin: { l: 60, r: 20, t: 20, b: 60 }
  });
}

// ----------------------------------------------------
// Data Table & CSV Exporter
// ----------------------------------------------------
function renderDataTable(df) {
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = '';

  const n = df.dates.length;
  // Display recent 100 rows
  const startIdx = Math.max(0, n - 100);

  for (let i = n - 1; i >= startIdx; i--) {
    const tr = document.createElement('tr');
    const signalText = df.signals[i] === 1 ? '<span class="text-green">BUY</span>' : (df.signals[i] === -1 ? '<span class="text-red">SELL</span>' : '<span class="text-cyan">HOLD</span>');
    const retPct = (df.dailyReturns[i] * 100).toFixed(2);
    const retClass = df.dailyReturns[i] >= 0 ? 'text-green' : 'text-red';

    tr.innerHTML = `
      <td>${df.dates[i]}</td>
      <td>$${df.close[i].toFixed(2)}</td>
      <td>${df.sma20[i] ? '$' + df.sma20[i].toFixed(2) : '-'}</td>
      <td>${df.sma50[i] ? '$' + df.sma50[i].toFixed(2) : '-'}</td>
      <td class="${retClass}">${retPct}%</td>
      <td>${df.rsi[i] ? df.rsi[i].toFixed(2) : '-'}</td>
      <td>${signalText}</td>
    `;
    tbody.appendChild(tr);
  }
}

function exportCSV() {
  if (!processedData) return;

  const df = processedData;
  let csv = 'Date,Open,High,Low,Close,Volume,Daily_Return_Pct,SMA_20,SMA_50,RSI,Signal\n';

  for (let i = 0; i < df.dates.length; i++) {
    csv += `${df.dates[i]},${df.open[i].toFixed(2)},${df.high[i].toFixed(2)},${df.low[i].toFixed(2)},${df.close[i].toFixed(2)},${df.volume[i]},${(df.dailyReturns[i] * 100).toFixed(4)},${df.sma20[i] ? df.sma20[i].toFixed(2) : ''},${df.sma50[i] ? df.sma50[i].toFixed(2) : ''},${df.rsi[i] ? df.rsi[i].toFixed(2) : ''},${df.signals[i]}\n`;
  }

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', `${currentSymbol}_stock_analytics_${new Date().toISOString().split('T')[0]}.csv`);
  a.click();
}
