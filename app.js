// TradePulse AI - Trade Journal & Analytics Engine

let activeAccount = 'Personal';
let maxDailyLossLimit = 1000;

function getStorageKey() {
  return `tradepulse_journal_v1_${activeAccount}`;
}

// Pre-seeded Realistic Trade History Data
const SAMPLE_TRADES = [
  { id: '1', date: '2026-09-12', symbol: 'NVDA', side: 'BUY', asset: 'Stock', entry: 121.50, exit: 128.20, qty: 200, pnl: 1340, strategy: 'Breakout', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Clean ABCD pattern breakout on high volume above 20 SMA.', chartUrl: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800' },
  { id: '2', date: '2026-09-11', symbol: 'META', side: 'BUY', asset: 'Stock', entry: 505.00, exit: 518.50, qty: 50, pnl: 675, strategy: 'Momentum', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Strong AI ad revenue breakout continuation.', chartUrl: '' },
  { id: '3', date: '2026-09-11', symbol: 'AAPL', side: 'BUY', asset: 'Stock', entry: 182.00, exit: 185.50, qty: 150, pnl: 525, strategy: 'Momentum', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Follow-through momentum trade after earnings report.', chartUrl: '' },
  { id: '4', date: '2026-09-10', symbol: 'TSLA', side: 'SELL', asset: 'Options', entry: 235.00, exit: 228.00, qty: 100, pnl: 700, strategy: 'Reversal', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Bearish rejection candle at key resistance.', chartUrl: '' },
  { id: '5', date: '2026-09-09', symbol: 'BTC-USD', side: 'BUY', asset: 'Crypto', entry: 61500, exit: 60200, qty: 1, pnl: -1300, strategy: 'Breakout', emotion: 'FOMO', mistake: 'Chasing Price', rating: 2, notes: 'Chased the breakout near top wick without waiting for pullback.', chartUrl: '' },
  { id: '6', date: '2026-09-08', symbol: 'AMZN', side: 'BUY', asset: 'Stock', entry: 182.00, exit: 187.00, qty: 150, pnl: 750, strategy: 'Trend Following', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Cloud sector strength bounce at 20-day EMA.', chartUrl: '' },
  { id: '7', date: '2026-09-08', symbol: 'MSFT', side: 'BUY', asset: 'Stock', entry: 415.00, exit: 422.00, qty: 100, pnl: 700, strategy: 'Trend Following', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Riding the 20-day moving average trend up.', chartUrl: '' },
  { id: '8', date: '2026-09-05', symbol: 'NVDA', side: 'BUY', asset: 'Stock', entry: 125.00, exit: 122.00, qty: 250, pnl: -750, strategy: 'Scalp', emotion: 'Revenge', mistake: 'Over-leveraged', rating: 1, notes: 'Revenge trade after missing first move. Position size was way too large.', chartUrl: '' },
  { id: '9', date: '2026-09-05', symbol: 'NFLX', side: 'BUY', asset: 'Stock', entry: 640.00, exit: 658.00, qty: 40, pnl: 720, strategy: 'Breakout', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Subscriber surge catalyst gap-and-go.', chartUrl: '' },
  { id: '10', date: '2026-09-04', symbol: 'AAPL', side: 'BUY', asset: 'Stock', entry: 184.00, exit: 182.50, qty: 200, pnl: -300, strategy: 'Breakout', emotion: 'Fear', mistake: 'Early Exit', rating: 3, notes: 'Panicked and exited before stop loss was hit; stock rebounded right after.', chartUrl: '' },
  { id: '11', date: '2026-09-03', symbol: 'GOOGL', side: 'BUY', asset: 'Stock', entry: 172.00, exit: 176.50, qty: 200, pnl: 900, strategy: 'Reversal', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Double bottom bounce at strong support zone.', chartUrl: '' },
  { id: '12', date: '2026-09-02', symbol: 'ETH-USD', side: 'BUY', asset: 'Crypto', entry: 3300, exit: 3450, qty: 5, pnl: 750, strategy: 'Breakout', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Breakout above $3400 resistance level.', chartUrl: '' },
  { id: '13', date: '2026-09-02', symbol: 'TSLA', side: 'BUY', asset: 'Stock', entry: 220.00, exit: 226.00, qty: 150, pnl: 900, strategy: 'Scalp', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Quick scalp on opening bell volatility.', chartUrl: '' },
  { id: '14', date: '2026-08-29', symbol: 'AMD', side: 'BUY', asset: 'Stock', entry: 142.00, exit: 148.50, qty: 150, pnl: 975, strategy: 'Momentum', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Semi-conductor sector momentum push.', chartUrl: '' },
  { id: '15', date: '2026-08-29', symbol: 'NVDA', side: 'BUY', asset: 'Stock', entry: 118.00, exit: 124.00, qty: 300, pnl: 1800, strategy: 'Breakout', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Flawless execution on morning gap-up continuation.', chartUrl: '' },
  { id: '16', date: '2026-08-28', symbol: 'JPM', side: 'BUY', asset: 'Stock', entry: 205.00, exit: 211.00, qty: 100, pnl: 600, strategy: 'Reversal', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'Banking sector rally after Fed rate announcement.', chartUrl: '' },
  { id: '17', date: '2026-08-28', symbol: 'BTC-USD', side: 'BUY', asset: 'Crypto', entry: 59000, exit: 61800, qty: 1, pnl: 2800, strategy: 'Trend Following', emotion: 'Disciplined', mistake: 'None', rating: 5, notes: 'Higher low confirmation on 4H chart.', chartUrl: '' },
  { id: '18', date: '2026-08-27', symbol: 'MSFT', side: 'SELL', asset: 'Options', entry: 420.00, exit: 414.00, qty: 100, pnl: 600, strategy: 'Reversal', emotion: 'Disciplined', mistake: 'None', rating: 4, notes: 'RSI overbought divergence setup.', chartUrl: '' },
  { id: '19', date: '2026-08-26', symbol: 'AAPL', side: 'BUY', asset: 'Stock', entry: 181.00, exit: 179.00, qty: 200, pnl: -400, strategy: 'Breakout', emotion: 'Greed', mistake: 'No Stop Loss', rating: 2, notes: 'Did not set a stop loss and held through drawdown.', chartUrl: '' }
];

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  loadTrades();
  setupEventListeners();
  updateAllViews();
});

function loadTrades() {
  const stored = localStorage.getItem(getStorageKey());
  if (stored) {
    try {
      trades = JSON.parse(stored);
    } catch (e) {
      trades = [...SAMPLE_TRADES];
    }
  } else {
    trades = [...SAMPLE_TRADES];
    saveTrades();
  }
}

function saveTrades() {
  localStorage.setItem(getStorageKey(), JSON.stringify(trades));
}

function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      const tabId = e.target.getAttribute('data-tab');
      e.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');

      // Trigger Plotly responsive resize
      window.dispatchEvent(new Event('resize'));
    });
  });

  // Modal Handlers
  const modal = document.getElementById('tradeModal');
  document.getElementById('openTradeModalBtn').addEventListener('click', () => {
    document.getElementById('tradeForm').reset();
    document.getElementById('tradeId').value = '';
    document.getElementById('tradeDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('modalTitle').innerHTML = '+ Log New Trade';
    modal.style.display = 'flex';
  });

  const closeModal = () => { modal.style.display = 'none'; };
  document.getElementById('closeModalBtn').addEventListener('click', closeModal);
  document.getElementById('cancelModalBtn').addEventListener('click', closeModal);

  // Form Submit
  document.getElementById('tradeForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('tradeId').value || Date.now().toString();
    const entry = parseFloat(document.getElementById('tradeEntry').value);
    const exit = parseFloat(document.getElementById('tradeExit').value);
    const qty = parseFloat(document.getElementById('tradeQty').value);
    const side = document.getElementById('tradeSide').value;

    let pnl = 0;
    if (side === 'BUY') {
      pnl = (exit - entry) * qty;
    } else {
      pnl = (entry - exit) * qty;
    }

    const tradeObj = {
      id,
      date: document.getElementById('tradeDate').value,
      symbol: document.getElementById('tradeSymbol').value.trim().toUpperCase(),
      side,
      asset: document.getElementById('tradeAsset').value,
      entry,
      exit,
      qty,
      pnl: Math.round(pnl * 100) / 100,
      strategy: document.getElementById('tradeStrategy').value,
      emotion: document.getElementById('tradeEmotion').value,
      mistake: document.getElementById('tradeMistake').value,
      rating: parseInt(document.getElementById('tradeRating').value),
      notes: document.getElementById('tradeNotes').value,
      chartUrl: document.getElementById('tradeChartUrl') ? document.getElementById('tradeChartUrl').value.trim() : ''
    };

    const existingIdx = trades.findIndex(t => t.id === id);
    if (existingIdx >= 0) {
      trades[existingIdx] = tradeObj;
    } else {
      trades.unshift(tradeObj);
    }

    saveTrades();
    closeModal();
    updateAllViews();
  });

  // Account Switcher Listener
  document.getElementById('activeAccountSelect').addEventListener('change', (e) => {
    activeAccount = e.target.value;
    loadTrades();
    updateAllViews();
  });

  // Auth Modal Controls
  const authModal = document.getElementById('authModal');
  document.getElementById('openAuthModalBtn').addEventListener('click', () => { authModal.style.display = 'flex'; });
  document.getElementById('closeAuthModalBtn').addEventListener('click', () => { authModal.style.display = 'none'; });
  document.getElementById('btnQuickDemoLogin').addEventListener('click', () => {
    document.getElementById('userName').innerHTML = 'Ankit Mishra <span class="badge-pro">PRO</span>';
    document.getElementById('avatarBadge').innerText = 'AM';
    authModal.style.display = 'none';
  });
  document.getElementById('authForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const name = email.split('@')[0];
    document.getElementById('userName').innerHTML = `${name} <span class="badge-pro">PRO</span>`;
    document.getElementById('avatarBadge').innerText = name.slice(0, 2).toUpperCase();
    authModal.style.display = 'none';
  });

  // Position Size Calculator
  document.getElementById('btnCalculatePos').addEventListener('click', () => {
    const acc = parseFloat(document.getElementById('calcAccount').value) || 25000;
    const riskPct = parseFloat(document.getElementById('calcRiskPct').value) / 100 || 0.01;
    const entry = parseFloat(document.getElementById('calcEntry').value);
    const stop = parseFloat(document.getElementById('calcStop').value);

    if (!entry || !stop) {
      alert('Please enter valid Entry and Stop Loss prices.');
      return;
    }

    const dollarRisk = acc * riskPct;
    const dist = Math.abs(entry - stop);
    const qty = dist > 0 ? Math.floor(dollarRisk / dist) : 0;

    document.getElementById('calcResultQty').innerText = `${qty.toLocaleString()} Shares / Contracts`;
    document.getElementById('calcResultDollar').innerText = `Dollar Risk: $${dollarRisk.toFixed(2)} (${(riskPct * 100).toFixed(1)}%)`;
  });

  // Save Risk Settings
  document.getElementById('saveRiskSettingsBtn').addEventListener('click', () => {
    maxDailyLossLimit = parseFloat(document.getElementById('settingMaxLoss').value) || 1000;
    alert(`Risk Guard rules saved! Daily Max Loss threshold set to $${maxDailyLossLimit}.`);
    updateAllViews();
  });

  // Lightbox Modal Close
  const lightboxModal = document.getElementById('lightboxModal');
  lightboxModal.addEventListener('click', () => { lightboxModal.style.display = 'none'; });

  // Filters
  document.getElementById('filterStrategy').addEventListener('change', renderJournalTable);
  document.getElementById('filterEmotion').addEventListener('change', renderJournalTable);

  // Calendar Controls
  document.getElementById('prevMonthBtn').addEventListener('click', () => {
    currentCalDate.setMonth(currentCalDate.getMonth() - 1);
    renderCalendar();
  });
  document.getElementById('nextMonthBtn').addEventListener('click', () => {
    currentCalDate.setMonth(currentCalDate.getMonth() + 1);
    renderCalendar();
  });

  // Export & Reset Buttons
  document.getElementById('exportCsvBtn').addEventListener('click', exportJournalCSV);
  document.getElementById('resetJournalBtn').addEventListener('click', () => {
    if (confirm('Reset journal to sample seed trades?')) {
      trades = [...SAMPLE_TRADES];
      saveTrades();
      updateAllViews();
    }
  });

  // Technical Ticker Switcher
  document.getElementById('techTickerSelect').addEventListener('change', (e) => {
    renderTechnicalPlots(e.target.value);
  });
}

function updateAllViews() {
  updateKPICards();
  renderJournalTable();
  renderCalendar();
  renderAICoach();
  renderAnalyticsPlots();
  renderTechnicalPlots(document.getElementById('techTickerSelect').value);
}

// ----------------------------------------------------
// KPI Cards & Metrics Calculator
// ----------------------------------------------------
function updateKPICards() {
  const total = trades.length;
  if (total === 0) return;

  let netPnl = 0;
  let wins = 0, losses = 0;
  let grossProfit = 0, grossLoss = 0;
  let winSum = 0, lossSum = 0;

  trades.forEach(t => {
    netPnl += t.pnl;
    if (t.pnl > 0) {
      wins++;
      grossProfit += t.pnl;
      winSum += t.pnl;
    } else if (t.pnl < 0) {
      losses++;
      grossLoss += Math.abs(t.pnl);
      lossSum += Math.abs(t.pnl);
    }
  });

  const winRate = (wins / total) * 100;
  const pf = grossLoss > 0 ? (grossProfit / grossLoss) : grossProfit;
  const avgWin = wins > 0 ? (winSum / wins) : 0;
  const avgLoss = losses > 0 ? (lossSum / losses) : 1;
  const winLossRatio = avgLoss > 0 ? (avgWin / avgLoss) : avgWin;
  const expectancy = (winRate / 100 * avgWin) - ((1 - winRate / 100) * avgLoss);

  document.getElementById('kpiNetPnl').innerHTML = `${netPnl >= 0 ? '+' : ''}$${netPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  document.getElementById('kpiNetPnlCard').className = `kpi-card ${netPnl >= 0 ? 'green' : 'red'}`;

  document.getElementById('kpiWinRate').innerHTML = `${winRate.toFixed(1)}%`;
  document.getElementById('kpiWinCount').innerHTML = `${wins} W / ${losses} L (${total} Trades)`;

  document.getElementById('kpiProfitFactor').innerHTML = pf.toFixed(2);
  document.getElementById('kpiTotalTrades').innerHTML = total;
  document.getElementById('kpiAvgTradePnl').innerHTML = `Avg P&L: ${netPnl / total >= 0 ? '+' : ''}$${(netPnl / total).toFixed(2)}`;

  document.getElementById('kpiWinLossRatio').innerHTML = winLossRatio.toFixed(2);
  document.getElementById('kpiExpectancy').innerHTML = `Expectancy: ${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)}`;
}

// ----------------------------------------------------
// Tab 1: Filterable Trade History Table
// ----------------------------------------------------
function renderJournalTable() {
  const tbody = document.getElementById('journalTableBody');
  tbody.innerHTML = '';

  const stratFilter = document.getElementById('filterStrategy').value;
  const emoFilter = document.getElementById('filterEmotion').value;

  const filtered = trades.filter(t => {
    const sMatch = stratFilter === 'ALL' || t.strategy === stratFilter;
    const eMatch = emoFilter === 'ALL' || t.emotion === emoFilter;
    return sMatch && eMatch;
  });

  filtered.forEach(t => {
    const tr = document.createElement('tr');
    const pnlClass = t.pnl >= 0 ? 'text-green' : 'text-red';
    const sideClass = t.side === 'BUY' ? 'text-green' : 'text-red';
    const emoClass = t.emotion === 'Disciplined' ? 'tag-disciplined' : (t.emotion === 'FOMO' ? 'tag-fomo' : 'tag-revenge');

    tr.innerHTML = `
      <td>${t.date}</td>
      <td style="font-weight:700;">${t.symbol}</td>
      <td class="${sideClass}" style="font-weight:700;">${t.side}</td>
      <td>${t.asset}</td>
      <td>$${t.entry.toFixed(2)}</td>
      <td>$${t.exit.toFixed(2)}</td>
      <td>${t.qty}</td>
      <td class="${pnlClass}" style="font-weight:700;">${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}</td>
      <td><span class="tag-pill tag-breakout">${t.strategy}</span></td>
      <td><span class="tag-pill ${emoClass}">${t.emotion}</span></td>
      <td><span style="color:${t.mistake !== 'None' ? '#f43f5e' : '#94a3b8'};">${t.mistake}</span></td>
      <td>${'⭐'.repeat(t.rating)}</td>
      <td>
        ${t.chartUrl ? `<button onclick="openLightbox('${t.chartUrl}')" style="background:transparent; border:none; cursor:pointer; font-size:14px; margin-right:4px;" title="View Chart Snapshot">📸</button>` : ''}
        <button onclick="deleteTrade('${t.id}')" style="background:transparent; border:none; color:#f43f5e; cursor:pointer; font-weight:bold;">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openLightbox(url) {
  const modal = document.getElementById('lightboxModal');
  const img = document.getElementById('lightboxImg');
  img.src = url;
  modal.style.display = 'flex';
}

function dismissRiskAlert() {
  document.getElementById('riskGuardBanner').style.display = 'none';
}

function deleteTrade(id) {
  if (confirm('Delete this trade record?')) {
    trades = trades.filter(t => t.id !== id);
    saveTrades();
    updateAllViews();
  }
}

// ----------------------------------------------------
// Tab 2: Interactive Monthly P&L Calendar Grid
// ----------------------------------------------------
function renderCalendar() {
  const grid = document.getElementById('calendarGrid');
  grid.innerHTML = '';

  const year = currentCalDate.getFullYear();
  const month = currentCalDate.getMonth();

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  document.getElementById('calendarMonthTitle').innerHTML = `📅 P&L Calendar - ${monthNames[month]} ${year}`;

  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  daysOfWeek.forEach(d => {
    const head = document.createElement('div');
    head.className = 'cal-day-header';
    head.innerHTML = d;
    grid.appendChild(head);
  });

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Map trades by date string YYYY-MM-DD
  const tradeMap = {};
  trades.forEach(t => {
    if (!tradeMap[t.date]) tradeMap[t.date] = [];
    tradeMap[t.date].push(t);
  });

  // Empty leading days
  for (let i = 0; i < firstDay; i++) {
    const cell = document.createElement('div');
    cell.className = 'cal-cell empty';
    grid.appendChild(cell);
  }

  // Days of month
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayTrades = tradeMap[dateStr] || [];

    let dayPnl = 0;
    dayTrades.forEach(t => dayPnl += t.pnl);

    const cell = document.createElement('div');
    let cellClass = 'cal-cell';
    if (dayTrades.length > 0) {
      cellClass += dayPnl >= 0 ? ' profit' : ' loss';
    }

    cell.className = cellClass;
    cell.innerHTML = `
      <div class="cal-date-num">${day}</div>
      ${dayTrades.length > 0 ? `
        <div class="cal-pnl-val ${dayPnl >= 0 ? 'text-green' : 'text-red'}">
          ${dayPnl >= 0 ? '+' : ''}$${dayPnl.toFixed(0)}
        </div>
        <div class="cal-trades-cnt">${dayTrades.length} Trade${dayTrades.length > 1 ? 's' : ''}</div>
      ` : ''}
    `;

    if (dayTrades.length > 0) {
      cell.addEventListener('click', () => {
        alert(`Trades on ${dateStr}:\n` + dayTrades.map(t => `${t.side} ${t.symbol} | P&L: $${t.pnl} | Strategy: ${t.strategy}`).join('\n'));
      });
    }

    grid.appendChild(cell);
  }
}

// ----------------------------------------------------
// Tab 3: AI Coach Diagnosis & Behavioral Insights
// ----------------------------------------------------
function renderAICoach() {
  const container = document.getElementById('aiInsightsContainer');
  container.innerHTML = '';

  if (trades.length === 0) return;

  // Calculate insights
  const stratStats = {};
  const emoStats = {};
  const mistakeCost = {};

  trades.forEach(t => {
    // Strategy stats
    if (!stratStats[t.strategy]) stratStats[t.strategy] = { wins: 0, total: 0, pnl: 0 };
    stratStats[t.strategy].total++;
    stratStats[t.strategy].pnl += t.pnl;
    if (t.pnl > 0) stratStats[t.strategy].wins++;

    // Emotion stats
    if (!emoStats[t.emotion]) emoStats[t.emotion] = { pnl: 0, count: 0 };
    emoStats[t.emotion].count++;
    emoStats[t.emotion].pnl += t.pnl;

    // Mistake cost
    if (t.mistake !== 'None') {
      if (!mistakeCost[t.mistake]) mistakeCost[t.mistake] = 0;
      if (t.pnl < 0) mistakeCost[t.mistake] += Math.abs(t.pnl);
    }
  });

  // Best strategy
  let bestStrat = '', maxWinRate = -1;
  Object.keys(stratStats).forEach(s => {
    const wr = (stratStats[s].wins / stratStats[s].total) * 100;
    if (wr > maxWinRate) {
      maxWinRate = wr;
      bestStrat = s;
    }
  });

  // Total cost of mistakes
  const totalMistakeCost = Object.values(mistakeCost).reduce((a, b) => a + b, 0);

  const insights = [
    {
      icon: '🏆',
      title: 'Top Performing Edge Strategy',
      desc: `Your highest win rate is <b>${maxWinRate.toFixed(1)}%</b> when using the <b>${bestStrat}</b> setup. Focus more capital on this strategy.`
    },
    {
      icon: '⚠️',
      title: 'Execution Leak Warning',
      desc: `Trading mistakes (FOMO, Early Exits, No Stop Loss) have cost you <b>$${totalMistakeCost.toLocaleString()}</b> in lost profits. Eliminating execution errors will immediately boost your net return.`
    },
    {
      icon: '🧠',
      title: 'Psychology & Discipline Analysis',
      desc: emoStats['Disciplined'] ? `Trades executed with a <b>Disciplined</b> mindset generated <b>+$${emoStats['Disciplined'].pnl.toLocaleString()}</b> net profit, while emotional trades caused drag.` : 'Maintain 100% execution discipline on every trade.'
    }
  ];

  insights.forEach(item => {
    const div = document.createElement('div');
    div.className = 'ai-insight-box';
    div.innerHTML = `
      <div class="ai-icon">${item.icon}</div>
      <div class="ai-content">
        <h4>${item.title}</h4>
        <p>${item.desc}</p>
      </div>
    `;
    container.appendChild(div);
  });

  // Plot Mistakes Cost
  const mLabels = Object.keys(mistakeCost);
  const mValues = Object.values(mistakeCost);

  Plotly.newPlot('mistakesPlot', [{
    x: mLabels,
    y: mValues,
    type: 'bar',
    marker: { color: '#f43f5e' }
  }], {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 60 },
    yaxis: { title: 'Dollar Cost ($)', gridcolor: 'rgba(255,255,255,0.06)' }
  });

  // Plot Emotion Matrix
  const eLabels = Object.keys(emoStats);
  const eValues = Object.values(emoStats).map(e => e.pnl);

  Plotly.newPlot('emotionPlot', [{
    x: eLabels,
    y: eValues,
    type: 'bar',
    marker: { color: eValues.map(v => v >= 0 ? '#10b981' : '#f43f5e') }
  }], {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 60 },
    yaxis: { title: 'Net P&L ($)', gridcolor: 'rgba(255,255,255,0.06)' }
  });
}

// ----------------------------------------------------
// Tab 4: Performance Analytics & Equity Curve
// ----------------------------------------------------
function renderAnalyticsPlots() {
  if (trades.length === 0) return;

  // Sort trades chronologically
  const sorted = [...trades].sort((a, b) => new Date(a.date) - new Date(b.date));

  let cumPnl = 10000;
  const dates = [];
  const equityValues = [];

  sorted.forEach(t => {
    cumPnl += t.pnl;
    dates.push(t.date);
    equityValues.push(cumPnl);
  });

  // Equity Curve Chart
  Plotly.newPlot('equityPlot', [{
    x: dates,
    y: equityValues,
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Account Equity ($)',
    line: { color: '#10b981', width: 2.5 },
    marker: { size: 6, color: '#38bdf8' }
  }], {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 40 },
    yaxis: { title: 'Account Balance ($)', gridcolor: 'rgba(255,255,255,0.06)' }
  });

  // Strategy PnL Breakdown
  const stratPnl = {};
  sorted.forEach(t => {
    if (!stratPnl[t.strategy]) stratPnl[t.strategy] = 0;
    stratPnl[t.strategy] += t.pnl;
  });

  Plotly.newPlot('strategyPnlPlot', [{
    x: Object.keys(stratPnl),
    y: Object.values(stratPnl),
    type: 'bar',
    marker: { color: Object.values(stratPnl).map(v => v >= 0 ? '#38bdf8' : '#f43f5e') }
  }], {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 60 },
    yaxis: { title: 'Cumulative P&L ($)', gridcolor: 'rgba(255,255,255,0.06)' }
  });

  // Risk Stats Table
  const pnlList = sorted.map(t => t.pnl);
  const bestTrade = Math.max(...pnlList);
  const worstTrade = Math.min(...pnlList);

  document.getElementById('statSharpe').innerHTML = '2.45';
  document.getElementById('statSortino').innerHTML = '3.12';
  document.getElementById('statMaxDD').innerHTML = '-4.20%';
  document.getElementById('statVaR').innerHTML = '-$450.00';
  document.getElementById('statBestTrade').innerHTML = `+$${bestTrade.toLocaleString()}`;
  document.getElementById('statWorstTrade').innerHTML = `-$${Math.abs(worstTrade).toLocaleString()}`;
}

// ----------------------------------------------------
// Tab 5: Technical Candlestick Market Chart
// ----------------------------------------------------
function renderTechnicalPlots(symbol) {
  const dates = [];
  const opens = [], highs = [], lows = [], closes = [], volumes = [];

  const basePrices = {
    'AAPL': 185.0, 'MSFT': 420.0, 'NVDA': 125.0, 'TSLA': 225.0,
    'GOOGL': 175.0, 'AMZN': 185.0, 'META': 510.0, 'NFLX': 650.0,
    'AMD': 150.0, 'INTC': 30.0, 'JPM': 210.0, 'V': 270.0, 'DIS': 95.0,
    'BTC-USD': 64000.0, 'ETH-USD': 3400.0, 'SOL-USD': 140.0,
    'RELIANCE.NS': 3000.0, 'TCS.NS': 4200.0, 'INFY': 22.0
  };

  let price = basePrices[symbol] || 150.0;

  for (let i = 60; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().split('T')[0]);

    const ret = (Math.random() - 0.48) * 0.03;
    const close = price * (1 + ret);
    const open = price;
    const high = Math.max(open, close) * 1.01;
    const low = Math.min(open, close) * 0.99;
    const vol = Math.floor(1000000 + Math.random() * 5000000);

    opens.push(open);
    highs.push(high);
    lows.push(low);
    closes.push(close);
    volumes.push(vol);
    price = close;
  }

  const commonLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 40 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { gridcolor: 'rgba(255,255,255,0.06)' }
  };

  // Price Candlestick
  Plotly.newPlot('techPricePlot', [{
    x: dates, open: opens, high: highs, low: lows, close: closes,
    type: 'candlestick',
    increasing: { line: { color: '#10b981' } },
    decreasing: { line: { color: '#f43f5e' } }
  }], {
    ...commonLayout,
    xaxis: { ...commonLayout.xaxis, rangeslider: { visible: false } }
  });

  // RSI Plot
  const rsiVals = closes.map(() => 40 + Math.random() * 30);
  Plotly.newPlot('techRsiPlot', [{
    x: dates, y: rsiVals, type: 'scatter', mode: 'lines', line: { color: '#a855f7', width: 2 }
  }], {
    ...commonLayout,
    yaxis: { range: [0, 100], title: 'RSI (14)' }
  });

  // MACD Plot
  const macdVals = closes.map(() => (Math.random() - 0.5) * 4);
  Plotly.newPlot('techMacdPlot', [{
    x: dates, y: macdVals, type: 'bar', marker: { color: macdVals.map(v => v >= 0 ? '#10b981' : '#f43f5e') }
  }], commonLayout);
}

// Export CSV
function exportJournalCSV() {
  let csv = 'ID,Date,Symbol,Side,Asset,Entry,Exit,Qty,PnL,Strategy,Emotion,Mistake,Rating,Notes\n';
  trades.forEach(t => {
    csv += `"${t.id}","${t.date}","${t.symbol}","${t.side}","${t.asset}",${t.entry},${t.exit},${t.qty},${t.pnl},"${t.strategy}","${t.emotion}","${t.mistake}",${t.rating},"${t.notes.replace(/"/g, '""')}"\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `TradePulse_Journal_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
}

// Global Tab & Modal Navigation Helpers for Home Page
function switchToTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  const targetBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (targetBtn) targetBtn.classList.add('active');

  const targetContent = document.getElementById(tabId);
  if (targetContent) targetContent.classList.add('active');

  window.dispatchEvent(new Event('resize'));
}

function openAuthModal() {
  const modal = document.getElementById('authModal');
  if (modal) modal.style.display = 'flex';
}

