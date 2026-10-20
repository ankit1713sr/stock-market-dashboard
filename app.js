// TradePulse AI - Trade Journal & Analytics Engine

let activeAccount = 'Personal';
let maxDailyLossLimit = 1000;
let trades = [];
let useApiBackend = false;
let currentCalDate = new Date();

window.addEventListener('tradepulse:api-unavailable', () => {
  useApiBackend = false;
  updateConnectionStatus(false);
});

function showChartSource(id, market) {
  const node = document.getElementById(id);
  if (!node) return;
  // The existing API may silently synthesize candles. Do not certify provenance.
  node.innerText = market
    ? 'API chart data — source unverified; may be simulated or delayed. Not real-time.'
    : 'SIMULATED illustration — generated prices/indicators, not market observations.';
}


function getStorageKey() {
  return `tradepulse_journal_v1_${activeAccount}`;
}

// Pre-seeded Realistic Trade History Data (Explicitly tagged as demonstration)
const SAMPLE_TRADES = Array.from({ length: 19 }, (_, index) => {
  const number = index + 1;
  const entry = 42 + number * 1.25;
  const exit = entry + (number % 3 === 0 ? -0.75 : 1.5);
  const qty = 2 + number;
  return { id: String(number), date: `2019-02-${String(number).padStart(2, '0')}`,
    symbol: `SIM${String(number).padStart(3, '0')}`, side: 'BUY', asset: 'Stock',
    entry, exit, qty, pnl: (exit - entry) * qty, stopLoss: entry - 2, target: entry + 4,
    strategy: 'Example Trend', emotion: 'Disciplined', mistake: 'None', rating: 3,
    notes: 'FICTIONAL EXAMPLE; not a real trade.', chartUrl: '', isDemo: true, is_demo: true };
});

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  await loadTrades();
  setupEventListeners();
  updateAllViews();
});

function normalizeTrade(raw) {
  const isOpen = raw.isOpen ?? ((raw.exit ?? raw.exit_price) == null);
  const entry = Number(raw.entry ?? raw.entry_price ?? 0);
  const exit = Number(raw.exit ?? raw.exit_price ?? entry);
  const qty = Number(raw.qty ?? 0);
  const side = (raw.side || 'BUY').toUpperCase();
  let pnl = Number(raw.net_pnl ?? raw.pnl ?? 0);

  const multiplier = Number(raw.contract_multiplier ?? 1);
  if (!Number.isFinite(pnl) || (raw.net_pnl == null && raw.pnl == null)) {
    pnl = (side === 'SELL' ? (entry - exit) * qty : (exit - entry) * qty) * multiplier;
  }

  const stopLoss = raw.stopLoss !== undefined && raw.stopLoss !== null
    ? Number(raw.stopLoss)
    : (raw.stop_loss ? Number(raw.stop_loss) : null);
  const target = raw.target !== undefined && raw.target !== null
    ? Number(raw.target)
    : (raw.target_price ? Number(raw.target_price) : null);

  let rMultiple = raw.rMultiple !== undefined && raw.rMultiple !== null
    ? Number(raw.rMultiple)
    : (raw.r_multiple !== undefined && raw.r_multiple !== null ? Number(raw.r_multiple) : null);
  if (rMultiple === null && stopLoss !== null) {
    const riskUnit = Math.abs(entry - stopLoss);
    if (riskUnit > 0) {
      rMultiple = pnl / (riskUnit * qty * multiplier);
    }
  }

  return {
    brokerage_fee: raw.brokerage_fee ?? null,
    transaction_fee: raw.transaction_fee ?? null,
    slippage_cost: raw.slippage_cost ?? null,
    contract_multiplier: raw.contract_multiplier ?? null,
    cost_status: raw.cost_status ?? null,
    slippage_treatment: raw.slippage_treatment ?? null,
    cost_model_json: raw.cost_model_json ?? null,
    gross_pnl: raw.gross_pnl ?? null,
    total_costs: raw.total_costs ?? null,
    net_pnl: raw.net_pnl ?? null,
    accounting_version: raw.accounting_version ?? null,
    pnl_basis: raw.pnl_basis ?? (raw.accounting_version == null ? 'legacy_unknown' :
      (raw.cost_status === 'reported' || raw.cost_status === 'estimated' ? `net_${raw.cost_status}` : 'gross_unknown_costs')),
    isOpen,
    id: String(raw.id ?? Date.now()),
    date: raw.date || raw.trade_date || new Date().toISOString().split('T')[0],
    symbol: (raw.symbol || '').toUpperCase(),
    side,
    asset: raw.asset || 'Stock',
    entry,
    exit,
    stopLoss,
    target,
    qty,
    pnl: Math.round(pnl * 100) / 100,
    returnPct: raw.returnPct ?? raw.return_pct ?? (entry * qty * multiplier > 0 ? pnl / (entry * qty * multiplier) * 100 : 0),
    rMultiple: rMultiple !== null && Number.isFinite(rMultiple) ? Math.round(rMultiple * 100) / 100 : null,
    strategy: raw.strategy || 'Breakout',
    emotion: raw.emotion || 'Disciplined',
    mistake: raw.mistake || 'None',
    rating: Number(raw.rating || 5),
    notes: raw.notes || '',
    chartUrl: raw.chartUrl || raw.chart_url || '',
    isDemo: Boolean(raw.is_demo ?? raw.isDemo ?? false)
  };
}

function getApiClient() {
  return window.TradePulseAPI || null;
}

function updateConnectionStatus(connected, count, latency) {
  const dot = document.getElementById('footerConnDot');
  const text = document.getElementById('footerConnText');
  const latEl = document.getElementById('footerConnLatency');
  if (!text) return;

  if (connected) {
    if (dot) dot.style.background = '#10b981';
    text.innerText = count !== undefined ? `API CONNECTED (${count} Trades)` : 'API CONNECTED';
    if (latEl) latEl.innerText = Number.isFinite(latency) ? `${latency}ms` : '—';
  } else {
    if (dot) dot.style.background = '#f59e0b';
    text.innerText = 'OFFLINE (LOCAL CACHE)';
    if (latEl) latEl.innerText = 'LOCAL';
  }
  const notice = document.getElementById('connectionNotice');
  if (notice) {
    notice.style.display = connected ? 'none' : 'flex';
    notice.innerText = 'OFFLINE — local browser cache only. No server persistence; fictional examples are labeled DEMO.';
  }
}

function checkDemoBanner() {
  const banner = document.getElementById('demoDataBanner');
  if (!banner) return;
  const isDemoActive = trades.length > 0 && trades.every(t => t.isDemo);
  banner.style.display = isDemoActive ? 'flex' : 'none';
}

function seedSampleTrades() {
  trades = SAMPLE_TRADES.map(normalizeTrade);
  saveTrades();
  checkDemoBanner();
  updateAllViews();
}

function clearDemoTrades() {
  if (confirm('Clear all demo sample trades and start with an empty journal?')) {
    trades = [];
    saveTrades();
    checkDemoBanner();
    updateAllViews();
  }
}

async function loadTrades() {
  const api = getApiClient();
  if (api) {
    try {
      const ping = await api.pingBackend();
      if (ping) {
        updateConnectionStatus(true, ping.trades_count, ping.latency);
        const apiTrades = await api.getTrades();
        trades = Array.isArray(apiTrades) ? apiTrades.map(normalizeTrade) : [];
        useApiBackend = true;
        saveTrades();
        checkDemoBanner();
        return;
      }
    } catch (err) {
      console.warn('TradePulse API unreachable; falling back to local storage cache.', err);
    }
  }

  updateConnectionStatus(false);
  useApiBackend = false;
  const stored = localStorage.getItem(getStorageKey());
  if (stored) {
    try {
      trades = JSON.parse(stored).map(normalizeTrade);
    } catch (e) {
      trades = SAMPLE_TRADES.map(normalizeTrade);
    }
  } else {
    trades = SAMPLE_TRADES.map(normalizeTrade);
    saveTrades();
  }
  checkDemoBanner();
}

function saveTrades() {
  localStorage.setItem(getStorageKey(), JSON.stringify(trades));
}

function buildTradePayloadFromForm(id) {
  const entry = parseFloat(document.getElementById('tradeEntry').value);
  const exit = parseFloat(document.getElementById('tradeExit').value);
  const qty = parseFloat(document.getElementById('tradeQty').value);
  const side = document.getElementById('tradeSide').value;

  return {
    id,
    trade_date: document.getElementById('tradeDate').value,
    symbol: document.getElementById('tradeSymbol').value.trim().toUpperCase(),
    side,
    asset: document.getElementById('tradeAsset').value,
    entry_price: entry,
    exit_price: exit,
    stop_loss: document.getElementById('tradeStop') && document.getElementById('tradeStop').value ? parseFloat(document.getElementById('tradeStop').value) : null,
    target_price: document.getElementById('tradeTarget') && document.getElementById('tradeTarget').value ? parseFloat(document.getElementById('tradeTarget').value) : null,
    qty,
    strategy: document.getElementById('tradeStrategy').value,
    emotion: document.getElementById('tradeEmotion').value,
    mistake: document.getElementById('tradeMistake').value,
    rating: parseInt(document.getElementById('tradeRating').value),
    notes: document.getElementById('tradeNotes').value,
    chart_url: document.getElementById('tradeChartUrl') ? document.getElementById('tradeChartUrl').value.trim() : ''
  };
}

function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      const targetBtn = e.target.closest('.tab-btn');
      const tabId = targetBtn ? targetBtn.getAttribute('data-tab') : null;

      if (!tabId) return;

      document.querySelectorAll(`.tab-btn[data-tab="${tabId}"]`).forEach(b => b.classList.add('active'));
      const targetContent = document.getElementById(tabId);
      if (targetContent) targetContent.classList.add('active');

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
  document.getElementById('tradeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('tradeId').value || Date.now().toString();
    const payload = buildTradePayloadFromForm(id);
    const existingTrade = trades.find(t => t.id === id);
    // Cost accounting edits require the Python engine; never replace cached net
    // results with a zero-cost browser calculation after a failed API save.
    const requiresAccountingApi = existingTrade && existingTrade.accounting_version != null;
    if (requiresAccountingApi && !(useApiBackend && getApiClient())) {
      alert('Reconnect to the backend before editing a trade with accounting data.');
      return;
    }

    let tradeObj = normalizeTrade({
      ...payload,
      id,
      date: payload.trade_date,
      entry: payload.entry_price,
      exit: payload.exit_price,
      chartUrl: payload.chart_url
    });

    const api = getApiClient();
    if (useApiBackend && api) {
      try {
        const isPersistedId = /^\d+$/.test(id) && trades.some(t => t.id === id);
        const savedTrade = isPersistedId
          ? await api.updateTrade(id, payload)
          : await api.createTrade(payload);
        tradeObj = normalizeTrade(savedTrade);
      } catch (err) {
        if (requiresAccountingApi) {
          alert('Trade was not saved. Accounting data is preserved; reconnect and retry.');
          return;
        }
        console.warn('API save failed; preserving trade in local cache.', err);
        useApiBackend = false;
      }
    }

    const existingIdx = trades.findIndex(t => t.id === id);
    if (existingIdx >= 0) trades[existingIdx] = tradeObj;
    else trades.unshift(tradeObj);

    saveTrades();
    closeModal();
    updateAllViews();
  });

  // Account Switcher Listener
  document.getElementById('activeAccountSelect').addEventListener('change', async (e) => {
    activeAccount = e.target.value;
    const disp = document.getElementById('activeAccountDisplay');
    if (disp) {
      const optText = e.target.options[e.target.selectedIndex].text;
      disp.innerText = optText.split(' ')[1] || optText;
    }
    await loadTrades();
    updateAllViews();
  });

  // Auth Modal Controls
  const authModal = document.getElementById('authModal');
  document.getElementById('openAuthModalBtn').addEventListener('click', () => { authModal.style.display = 'flex'; });
  document.getElementById('closeAuthModalBtn').addEventListener('click', () => { authModal.style.display = 'none'; });
  document.getElementById('btnQuickDemoLogin').addEventListener('click', () => {
    document.getElementById('userName').innerHTML = 'Demo Trader <span class="badge-pro">DEMO</span>';
    document.getElementById('avatarBadge').innerText = 'DT';
    authModal.style.display = 'none';
  });
  document.getElementById('authForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('authEmail').value;
    const name = email.split('@')[0];
    document.getElementById('userName').innerHTML = `${name} <span class="badge-pro">DEMO</span>`;
    document.getElementById('avatarBadge').innerText = name.slice(0, 2).toUpperCase();
    authModal.style.display = 'none';
  });

  // Position Size Calculator
  document.getElementById('btnCalculatePos').addEventListener('click', async () => {
    const acc = parseFloat(document.getElementById('calcAccount').value) || 25000;
    const riskPct = parseFloat(document.getElementById('calcRiskPct').value) / 100 || 0.01;
    const entry = parseFloat(document.getElementById('calcEntry').value);
    const stop = parseFloat(document.getElementById('calcStop').value);

    if (!entry || !stop) {
      alert('Please enter valid Entry and Stop Loss prices.');
      return;
    }

    let dollarRisk = acc * riskPct;
    let dist = Math.abs(entry - stop);
    let qty = dist > 0 ? Math.floor(dollarRisk / dist) : 0;

    const api = getApiClient();
    if (useApiBackend && api) {
      try {
        const result = await api.calculatePositionSize({
          account_balance: acc,
          risk_pct: riskPct * 100,
          entry_price: entry,
          stop_loss: stop
        });
        dollarRisk = result.dollar_risk;
        dist = result.risk_per_unit;
        qty = result.quantity;
      } catch (err) {
        console.warn('API position sizing failed; using local fallback.', err);
      }
    }

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
  const tradeDetailModal = document.getElementById('tradeDetailModal');
  const closeTradeDetailBtn = document.getElementById('closeTradeDetailBtn');
  if (closeTradeDetailBtn) closeTradeDetailBtn.addEventListener('click', () => { tradeDetailModal.style.display = 'none'; });
  if (tradeDetailModal) {
    tradeDetailModal.addEventListener('click', (e) => {
      if (e.target === tradeDetailModal) tradeDetailModal.style.display = 'none';
    });
  }

  // Filters
  document.getElementById('filterStrategy').addEventListener('change', renderJournalTable);
  document.getElementById('filterEmotion').addEventListener('change', renderJournalTable);

  // Calendar Controls
  const handlePrevMonth = () => {
    currentCalDate.setMonth(currentCalDate.getMonth() - 1);
    renderCalendar();
  };
  const handleNextMonth = () => {
    currentCalDate.setMonth(currentCalDate.getMonth() + 1);
    renderCalendar();
  };

  if (document.getElementById('prevMonthBtn')) document.getElementById('prevMonthBtn').addEventListener('click', handlePrevMonth);
  if (document.getElementById('nextMonthBtn')) document.getElementById('nextMonthBtn').addEventListener('click', handleNextMonth);
  if (document.getElementById('overviewPrevMonthBtn')) document.getElementById('overviewPrevMonthBtn').addEventListener('click', handlePrevMonth);
  if (document.getElementById('overviewNextMonthBtn')) document.getElementById('overviewNextMonthBtn').addEventListener('click', handleNextMonth);

  // Demo Banner & Modal controls
  const clearBtn = document.getElementById('clearDemoDataBtn');
  if (clearBtn) clearBtn.addEventListener('click', clearDemoTrades);

  const closeCalModalBtn = document.getElementById('closeCalDayModalBtn');
  if (closeCalModalBtn) {
    closeCalModalBtn.addEventListener('click', () => {
      const modal = document.getElementById('calDayModal');
      if (modal) modal.style.display = 'none';
    });
  }
  const calModal = document.getElementById('calDayModal');
  if (calModal) {
    calModal.addEventListener('click', (e) => {
      if (e.target === calModal) calModal.style.display = 'none';
    });
  }

  // Export & Reset Buttons
  document.getElementById('exportCsvBtn').addEventListener('click', exportJournalCSV);
  document.getElementById('resetJournalBtn').addEventListener('click', () => {
    if (confirm('Reset journal to sample seed trades?')) {
      seedSampleTrades();
    }
  });

  // Technical Ticker Switcher
  document.getElementById('techTickerSelect').addEventListener('change', (e) => {
    renderTechnicalPlots(e.target.value);
  });
}

function updateAllViews() {
  updateAccountingLabel();
  updateKPICards();
  renderJournalTable();
  renderCalendar();
  renderAICoach();
  renderAnalyticsPlots();
  renderTechnicalPlots(document.getElementById('techTickerSelect').value);
}

function updateAccountingLabel() {
  const label = document.getElementById('accountingBasisLabel');
  if (!label) return;
  const completed = trades.filter(t => !t.isOpen);
  const unknown = completed.filter(t => !['net_reported', 'net_estimated'].includes(t.pnl_basis)).length;
  const estimated = completed.filter(t => t.pnl_basis === 'net_estimated').length;
  label.textContent = unknown
    ? `Mixed/unknown cost basis: ${unknown} of ${completed.length} trades have unknown costs; totals include legacy/gross P&L.`
    : (completed.length ? `Net P&L: ${estimated} estimated-cost trades; remaining costs reported.` : 'No completed trades.');
}

function tradeAccountingLabel(trade) {
  if (trade.isOpen) return 'Open trade; no realized P&L';
  if (trade.pnl_basis === 'net_reported') return 'Net P&L after reported costs';
  if (trade.pnl_basis === 'net_estimated') return 'Net P&L after estimated costs';
  return 'Legacy/gross P&L; costs unknown';
}

// ----------------------------------------------------
// KPI Cards & Metrics Calculator
// ----------------------------------------------------
async function updateKPICards() {
  const completed = trades.filter(t => !t.isOpen);
  const total = completed.length;

  if (total === 0) {
    document.getElementById('kpiNetPnl').innerHTML = '$0.00';
    document.getElementById('kpiNetPnlCard').className = 'kpi-card hero-kpi green';
    const badgeEl = document.getElementById('kpiNetPnlBadge');
    if (badgeEl) {
      badgeEl.innerText = 'NEUTRAL';
      badgeEl.className = 'kpi-badge green';
    }
    const pctEl = document.getElementById('kpiNetPnlPct');
    if (pctEl) pctEl.innerHTML = '+0.00% Account Growth';

    document.getElementById('kpiWinRate').innerHTML = '0.0%';
    document.getElementById('kpiWinCount').innerHTML = '0 Wins / 0 Losses (0 Trades)';
    document.getElementById('kpiProfitFactor').innerHTML = '0.00';
    document.getElementById('kpiTotalTrades').innerHTML = '0';
    document.getElementById('kpiAvgTradePnl').innerHTML = 'Avg P&L: $0.00';
    document.getElementById('kpiWinLossRatio').innerHTML = '0.00';
    document.getElementById('kpiExpectancy').innerHTML = 'Expectancy: +$0.00';
    return;
  }

  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const summary = await api.getDashboardSummary();
      const netPnl = Number(summary.net_pnl || 0);
      document.getElementById('kpiNetPnl').innerHTML = `${netPnl >= 0 ? '+' : ''}$${netPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      document.getElementById('kpiNetPnlCard').className = `kpi-card hero-kpi ${netPnl >= 0 ? 'green' : 'red red-hero'}`;
      const badgeEl = document.getElementById('kpiNetPnlBadge');
      if (badgeEl) {
        badgeEl.innerText = netPnl >= 0 ? 'PROFITABLE' : 'DRAWDOWN';
        badgeEl.className = `kpi-badge ${netPnl >= 0 ? 'green' : 'red'}`;
      }
      const pctEl = document.getElementById('kpiNetPnlPct');
      if (pctEl) pctEl.innerHTML = `${(netPnl / 10000 * 100).toFixed(2)}% Account Growth`;

      document.getElementById('kpiWinRate').innerHTML = `${Number(summary.win_rate || 0).toFixed(1)}%`;
      document.getElementById('kpiWinCount').innerHTML = `${summary.wins || 0} W / ${summary.losses || 0} L (${summary.total_trades || 0} Trades)`;
      document.getElementById('kpiProfitFactor').innerHTML = summary.profit_factor === null ? 'N/A' : Number(summary.profit_factor || 0).toFixed(2);
      document.getElementById('kpiTotalTrades').innerHTML = summary.total_trades || 0;
      document.getElementById('kpiAvgTradePnl').innerHTML = `Avg P&L: ${Number(summary.avg_trade_pnl || 0) >= 0 ? '+' : ''}$${Number(summary.avg_trade_pnl || 0).toFixed(2)}`;
      document.getElementById('kpiWinLossRatio').innerHTML = summary.win_loss_ratio === null ? 'N/A' : Number(summary.win_loss_ratio || 0).toFixed(2);
      const avgR = summary.avg_r_multiple !== undefined ? ` | ${summary.avg_r_multiple}R` : '';
      document.getElementById('kpiExpectancy').innerHTML = `Expectancy: ${Number(summary.expectancy || 0) >= 0 ? '+' : ''}$${Number(summary.expectancy || 0).toFixed(2)}${avgR}`;
      return;
    } catch (err) {
      console.warn('Dashboard summary API failed; using local KPI calculations.', err);
    }
  }

  let netPnl = 0;
  let wins = 0, losses = 0;
  let grossProfit = 0, grossLoss = 0;
  let winSum = 0, lossSum = 0;
  const rList = [];

  completed.forEach(t => {
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
    if (t.rMultiple !== null && t.rMultiple !== undefined && Number.isFinite(t.rMultiple)) {
      rList.push(t.rMultiple);
    }
  });

  const winRate = (wins / total) * 100;
  const pf = grossLoss > 0 ? (grossProfit / grossLoss) : (grossProfit > 0 ? null : 0);
  const avgWin = wins > 0 ? (winSum / wins) : 0;
  const avgLoss = losses > 0 ? (lossSum / losses) : 0;
  const winLossRatio = avgLoss > 0 ? (avgWin / avgLoss) : (avgWin > 0 ? null : 0);
  const expectancy = (winRate / 100 * avgWin) - (losses / total * avgLoss);
  const avgRVal = rList.length > 0 ? (rList.reduce((a, b) => a + b, 0) / rList.length).toFixed(2) : '0.00';

  document.getElementById('kpiNetPnl').innerHTML = `${netPnl >= 0 ? '+' : ''}$${netPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('kpiNetPnlCard').className = `kpi-card hero-kpi ${netPnl >= 0 ? 'green' : 'red red-hero'}`;
  const badgeEl = document.getElementById('kpiNetPnlBadge');
  if (badgeEl) {
    badgeEl.innerText = netPnl >= 0 ? 'PROFITABLE' : 'DRAWDOWN';
    badgeEl.className = `kpi-badge ${netPnl >= 0 ? 'green' : 'red'}`;
  }
  const pctEl = document.getElementById('kpiNetPnlPct');
  if (pctEl) pctEl.innerHTML = `${(netPnl / 10000 * 100).toFixed(2)}% Account Growth`;

  document.getElementById('kpiWinRate').innerHTML = `${winRate.toFixed(1)}%`;
  document.getElementById('kpiWinCount').innerHTML = `${wins} W / ${losses} L (${total} Trades)`;

  document.getElementById('kpiProfitFactor').innerHTML = pf === null ? 'N/A' : pf.toFixed(2);
  document.getElementById('kpiTotalTrades').innerHTML = total;
  document.getElementById('kpiAvgTradePnl').innerHTML = `Avg P&L: ${netPnl / total >= 0 ? '+' : ''}$${(netPnl / total).toFixed(2)}`;

  document.getElementById('kpiWinLossRatio').innerHTML = winLossRatio === null ? 'N/A' : winLossRatio.toFixed(2);
  document.getElementById('kpiExpectancy').innerHTML = `Expectancy: ${expectancy >= 0 ? '+' : ''}$${expectancy.toFixed(2)} | ${avgRVal}R`;
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

  if (filtered.length === 0) {
    const emptyRow = document.createElement('tr');
    emptyRow.innerHTML = `
      <td colspan="13" class="empty-state-cell">
        <div class="empty-state-box">
          <div class="empty-state-icon">📓</div>
          <div class="empty-state-title">${trades.length === 0 ? 'No Trade Records Yet' : 'No Trades Match Filter'}</div>
          <p class="empty-state-desc">
            ${trades.length === 0
              ? 'Your trading journal is currently empty. Record your executed trades with risk controls, or load demonstration data to preview analytics.'
              : 'Try clearing the Strategy or Mindset filter dropdowns to view all logged executions.'}
          </p>
          <div class="empty-state-actions">
            <button onclick="document.getElementById('openTradeModalBtn').click()" class="btn-add-trade">+ Log New Order</button>
            ${trades.length === 0 ? '<button onclick="seedSampleTrades()" class="form-input btn-seed-demo">⚡ Load Demo Trades</button>' : ''}
          </div>
        </div>
      </td>
    `;
    tbody.appendChild(emptyRow);
    return;
  }

  filtered.forEach(t => {
    const tr = document.createElement('tr');
    const pnlClass = t.pnl >= 0 ? 'text-green' : 'text-red';
    const sideClass = t.side === 'BUY' ? 'text-green' : 'text-red';
    const emoClass = t.emotion === 'Disciplined' ? 'tag-disciplined' : (t.emotion === 'FOMO' ? 'tag-fomo' : 'tag-revenge');
    const demoBadge = t.isDemo ? '<span class="badge-demo" title="Sample Demo Trade">DEMO</span>' : '';

    tr.innerHTML = `
      <td>${t.date}</td>
      <td style="font-weight:700;">${t.symbol} ${demoBadge}</td>
      <td class="${sideClass}" style="font-weight:700;">${t.side}</td>
      <td>${t.asset}</td>
      <td>$${Number(t.entry || 0).toFixed(2)}</td>
      <td>$${Number(t.exit || 0).toFixed(2)}</td>
      <td>${t.qty}</td>
      <td class="${pnlClass}" style="font-weight:700;" title="${tradeAccountingLabel(t)}">${t.isOpen ? 'Open' : `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}`}</td>
      <td><span class="tag-pill tag-breakout">${t.strategy}</span></td>
      <td><span class="tag-pill ${emoClass}">${t.emotion}</span></td>
      <td><span style="color:${t.mistake !== 'None' ? '#f43f5e' : '#94a3b8'};">${t.mistake}</span></td>
      <td>${'⭐'.repeat(Math.max(1, Math.min(5, t.rating || 5)))}</td>
      <td>
        <button onclick="openTradeDetail('${t.id}')" style="background:transparent; border:none; color:#38bdf8; cursor:pointer; font-weight:bold; margin-right:4px;" title="Open Trade Detail">📈</button>
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

async function openTradeDetail(id) {
  const trade = trades.find(t => t.id === id);
  if (!trade) return;

  const modal = document.getElementById('tradeDetailModal');
  const title = document.getElementById('tradeDetailTitle');
  if (!modal || !title || typeof Plotly === 'undefined') return;

  title.innerText = `${trade.symbol} ${trade.side} Trade Detail - ${trade.date}`;
  modal.style.display = 'flex';

  let candles = [];
  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const market = await api.getMarketData(trade.symbol);
      candles = market.candles || [];
      showChartSource('tradeDetailDataNotice', market);
    } catch (err) {
      console.warn('Trade detail market API failed; using generated local candles.', err);
    }
  }

  if (candles.length === 0) {
    showChartSource('tradeDetailDataNotice', null);
    let price = trade.entry || 100;
    for (let i = 45; i >= 0; i--) {
      const d = new Date(trade.date);
      d.setDate(d.getDate() - i);
      const ret = (Math.random() - 0.48) * 0.025;
      const close = price * (1 + ret);
      candles.push({
        date: d.toISOString().split('T')[0],
        open: price,
        high: Math.max(price, close) * 1.01,
        low: Math.min(price, close) * 0.99,
        close
      });
      price = close;
    }
  }

  const dates = candles.map(c => c.date);
  const markerDate = trade.date || dates[Math.floor(dates.length / 2)];
  const markerSeries = [
    { name: 'ENTRY', value: trade.entry, color: '#38bdf8', symbol: 'triangle-up' },
    { name: 'EXIT', value: trade.exit, color: trade.pnl >= 0 ? '#10b981' : '#f43f5e', symbol: 'circle' },
    { name: 'STOP LOSS', value: trade.stopLoss, color: '#f43f5e', symbol: 'x' },
    { name: 'TARGET', value: trade.target, color: '#f59e0b', symbol: 'diamond' }
  ].filter(item => item.value);

  const traces = [{
    x: dates,
    open: candles.map(c => c.open),
    high: candles.map(c => c.high),
    low: candles.map(c => c.low),
    close: candles.map(c => c.close),
    type: 'candlestick',
    name: trade.symbol,
    increasing: { line: { color: '#10b981' } },
    decreasing: { line: { color: '#f43f5e' } }
  }];

  markerSeries.forEach(item => {
    traces.push({
      x: [markerDate],
      y: [item.value],
      type: 'scatter',
      mode: 'markers+text',
      name: item.name,
      text: [item.name],
      textposition: 'top center',
      marker: { color: item.color, size: 12, symbol: item.symbol }
    });
  });

  Plotly.newPlot('tradeDetailPricePlot', traces, {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8' },
    margin: { l: 50, r: 20, t: 20, b: 40 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.06)', rangeslider: { visible: false } },
    yaxis: { title: 'Price', gridcolor: 'rgba(255,255,255,0.06)' }
  });
}

function dismissRiskAlert() {
  document.getElementById('riskGuardBanner').style.display = 'none';
}

async function deleteTrade(id) {
  if (confirm('Delete this trade record?')) {
    const api = getApiClient();
    if (useApiBackend && api && /^\d+$/.test(id)) {
      try {
        await api.deleteTrade(id);
      } catch (err) {
        console.warn('API delete failed; removing from local view only.', err);
        useApiBackend = false;
      }
    }
    trades = trades.filter(t => t.id !== id);
    saveTrades();
    updateAllViews();
  }
}

// ----------------------------------------------------
// Tab 2: Interactive Monthly P&L Calendar Grid
// ----------------------------------------------------
function formatCalendarPnl(value) {
  const num = Number(value || 0);
  const amount = Math.abs(num).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  return `${num >= 0 ? '+' : '-'}$${amount}`;
}

function buildLocalCalendarDays(year, monthIndex) {
  const tradeMap = {};
  trades.forEach(t => {
    if (!t.date) return;
    if (!tradeMap[t.date]) tradeMap[t.date] = [];
    tradeMap[t.date].push(t);
  });

  return Object.entries(tradeMap)
    .filter(([dateStr]) => {
      if (!dateStr) return false;
      const parts = dateStr.split('-');
      if (parts.length < 3) return false;
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1;
      return y === year && m === monthIndex;
    })
    .map(([dateStr, dayTrades]) => ({
      date: dateStr,
      pnl: dayTrades.filter(t => !t.isOpen).reduce((sum, trade) => sum + Number(trade.pnl || 0), 0),
      trade_count: dayTrades.length,
      trades: dayTrades
    }));
}

function openDayModal(dateStr, dayTrades, dayPnl) {
  const modal = document.getElementById('calDayModal');
  const title = document.getElementById('calDayModalTitle');
  const body = document.getElementById('calDayModalBody');
  if (!modal || !body) return;

  const wins = dayTrades.filter(t => !t.isOpen && Number(t.pnl || 0) > 0).length;
  const losses = dayTrades.filter(t => !t.isOpen && Number(t.pnl || 0) < 0).length;

  if (title) title.innerHTML = `📅 Trade Summary — ${dateStr}`;
  body.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding:12px 14px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid var(--border-subtle);">
      <div>
        <div style="font-size:12px; color:var(--text-muted);">Day Realized P&L</div>
        <div style="font-size:20px; font-weight:800; font-family:var(--font-mono);" class="${dayPnl >= 0 ? 'text-green' : 'text-red'}">
          ${formatCalendarPnl(dayPnl)}
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px; color:var(--text-muted);">${dayTrades.length} Total Executions</div>
        <div style="font-size:13px; font-weight:700;">
          <span class="text-green">${wins} Wins</span> / <span class="text-red">${losses} Losses</span>
        </div>
      </div>
    </div>
    <div style="display:flex; flex-direction:column; gap:8px;">
      ${dayTrades.map(t => `
        <div class="cal-modal-trade-item">
          <div>
            <span style="font-weight:700; color:${t.side === 'BUY' ? '#10b981' : '#f43f5e'}; margin-right:6px;">${t.side}</span>
            <strong style="color:var(--text-main);">${t.symbol}</strong>
            ${t.isDemo ? '<span class="badge-demo">DEMO</span>' : ''}
            <span style="color:var(--text-muted); font-size:12px; margin-left:6px;">(${t.asset || 'Stock'}, ${t.qty} units @ $${Number(t.entry || 0).toFixed(2)})</span>
          </div>
          <div style="text-align:right;">
            <div style="font-weight:700; font-family:var(--font-mono);" class="${Number(t.pnl || 0) >= 0 ? 'text-green' : 'text-red'}">
              ${t.isOpen ? 'Open' : formatCalendarPnl(t.pnl)}
            </div>
            <div style="font-size:11px; color:var(--text-dim);">${t.strategy} ${t.rMultiple ? `• ${Number(t.rMultiple).toFixed(2)}R` : ''} • ${tradeAccountingLabel(t)}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;

  modal.style.display = 'flex';
}

async function getCalendarDays(year, monthIndex) {
  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const response = await api.getCalendar(year, monthIndex + 1);
      return Array.isArray(response.days) ? response.days : [];
    } catch (err) {
      console.warn('Calendar API failed; using local trade cache.', err);
    }
  }
  return buildLocalCalendarDays(year, monthIndex);
}

async function renderCalendar() {
  const targets = [
    { grid: document.getElementById('calendarGrid'), title: document.getElementById('calendarMonthTitle') },
    { grid: document.getElementById('overviewCalendarGrid'), title: document.getElementById('overviewCalendarMonthTitle') }
  ];

  const year = currentCalDate.getFullYear();
  const month = currentCalDate.getMonth();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const titleText = `📅 Monthly P&L Performance Calendar - ${monthNames[month]} ${year}`;

  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const calendarDays = await getCalendarDays(year, month);
  const dayMap = {};
  calendarDays.forEach(day => {
    dayMap[day.date] = {
      pnl: Number(day.pnl || 0),
      trade_count: Number(day.trade_count || (day.trades ? day.trades.length : 0)),
      trades: (day.trades || []).map(normalizeTrade)
    };
  });
  const maxAbsPnl = Math.max(1, ...Object.values(dayMap).map(day => Math.abs(day.pnl)));

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  targets.forEach(({ grid, title }) => {
    if (!grid) return;
    grid.innerHTML = '';
    if (title) title.innerHTML = titleText;

    daysOfWeek.forEach(d => {
      const head = document.createElement('div');
      head.className = 'cal-day-header';
      head.innerHTML = d;
      grid.appendChild(head);
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
      const dayData = dayMap[dateStr] || { pnl: 0, trade_count: 0, trades: [] };
      const dayTrades = dayData.trades;
      const dayPnl = dayData.pnl;
      const heat = Math.min(1, Math.max(0.18, Math.abs(dayPnl) / maxAbsPnl));

      const cell = document.createElement('div');
      let cellClass = 'cal-cell';
      if (dayData.trade_count > 0) {
        cellClass += dayPnl >= 0 ? ' profit' : ' loss';
      }

      cell.className = cellClass;
      cell.style.setProperty('--heat', heat.toFixed(2));
      cell.innerHTML = `
        <div class="cal-date-num">${day}</div>
        ${dayData.trade_count > 0 ? `
          <div class="cal-pnl-val ${dayPnl >= 0 ? 'text-green' : 'text-red'}">
            ${formatCalendarPnl(dayPnl)}
          </div>
          <div class="cal-trades-cnt">${dayData.trade_count} Trade${dayData.trade_count > 1 ? 's' : ''}</div>
        ` : ''}
      `;

      if (dayData.trade_count > 0) {
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', () => {
          openDayModal(dateStr, dayTrades, dayPnl);
        });
      }

      grid.appendChild(cell);
    }
  });
}

// ----------------------------------------------------
// Tab 3: AI Coach Diagnosis & Behavioral Insights
// ----------------------------------------------------
async function renderAICoach() {
  const container = document.getElementById('aiInsightsContainer');
  container.innerHTML = '';

  if (trades.length === 0) {
    container.innerHTML = `
      <div class="ai-insight-box">
        <div class="ai-icon">🤖</div>
        <div class="ai-content">
          <h4>AI Coach Awaiting Journal Entries</h4>
          <p>Your trading journal has no recorded trades. Log executions with strategy tags, emotion states, and execution ratings to unlock personalized quantitative diagnosis.</p>
        </div>
      </div>
    `;
    Plotly.newPlot('mistakesPlot', [], {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      annotations: [{ text: 'No mistakes recorded yet', font: { color: '#94a3b8', size: 13 }, showarrow: false }],
      xaxis: { visible: false }, yaxis: { visible: false }
    });
    Plotly.newPlot('emotionPlot', [], {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      annotations: [{ text: 'No psychology data recorded yet', font: { color: '#94a3b8', size: 13 }, showarrow: false }],
      xaxis: { visible: false }, yaxis: { visible: false }
    });
    return;
  }

  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const [strategyStats, emotionStats, mistakeStats] = await Promise.all([
        api.getStrategyAnalytics(),
        api.getEmotionAnalytics(),
        api.getMistakeAnalytics()
      ]);

      const best = [...strategyStats].sort((a, b) => b.win_rate - a.win_rate)[0] || { name: 'N/A', win_rate: 0 };
      const totalMistakeCost = mistakeStats
        .filter(item => item.name !== 'None')
        .reduce((sum, item) => sum + Math.abs(Math.min(0, item.pnl || 0)), 0);
      const disciplined = emotionStats.find(item => item.name === 'Disciplined');

      const insights = [
        {
          icon: '🏆',
          title: 'Top Performing Edge Strategy',
          desc: `Your highest win rate is <b>${Number(best.win_rate || 0).toFixed(1)}%</b> when using the <b>${best.name}</b> setup. Focus more capital on this strategy.`
        },
        {
          icon: '⚠️',
          title: 'Execution Leak Warning',
          desc: `Trading mistakes have generated <b>$${totalMistakeCost.toLocaleString()}</b> of realized loss. Eliminating repeat errors will immediately boost net return.`
        },
        {
          icon: '🧠',
          title: 'Psychology & Discipline Analysis',
          desc: disciplined ? `Trades executed with a <b>Disciplined</b> mindset generated <b>${disciplined.pnl >= 0 ? '+' : ''}$${Number(disciplined.pnl).toLocaleString()}</b> net P&L.` : 'Maintain 100% execution discipline on every trade.'
        }
      ];

      insights.forEach(item => {
        const div = document.createElement('div');
        div.className = 'ai-insight-box';
        div.innerHTML = `<div class="ai-icon">${item.icon}</div><div class="ai-content"><h4>${item.title}</h4><p>${item.desc}</p></div>`;
        container.appendChild(div);
      });

      const mistakeFiltered = mistakeStats.filter(item => item.name !== 'None');
      Plotly.newPlot('mistakesPlot', [{
        x: mistakeFiltered.map(item => item.name),
        y: mistakeFiltered.map(item => Math.abs(Math.min(0, item.pnl || 0))),
        type: 'bar',
        marker: { color: '#f43f5e' }
      }], {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Inter, sans-serif', color: '#94a3b8' },
        margin: { l: 50, r: 20, t: 20, b: 60 },
        yaxis: { title: 'Dollar Cost ($)', gridcolor: 'rgba(255,255,255,0.06)' }
      });

      Plotly.newPlot('emotionPlot', [{
        x: emotionStats.map(item => item.name),
        y: emotionStats.map(item => item.pnl),
        type: 'bar',
        marker: { color: emotionStats.map(item => item.pnl >= 0 ? '#10b981' : '#f43f5e') }
      }], {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Inter, sans-serif', color: '#94a3b8' },
        margin: { l: 50, r: 20, t: 20, b: 60 },
        yaxis: { title: 'Net P&L ($)', gridcolor: 'rgba(255,255,255,0.06)' }
      });
      return;
    } catch (err) {
      console.warn('Behavior analytics API failed; using local analytics.', err);
    }
  }

  // Local fallback insights use the same completed-trade policy as the API.
  const stratStats = {};
  const emoStats = {};
  const mistakeCost = {};

  trades.filter(t => !t.isOpen).forEach(t => {
    if (!stratStats[t.strategy]) stratStats[t.strategy] = { wins: 0, total: 0, pnl: 0 };
    stratStats[t.strategy].total++;
    stratStats[t.strategy].pnl += t.pnl;
    if (t.pnl > 0) stratStats[t.strategy].wins++;

    if (!emoStats[t.emotion]) emoStats[t.emotion] = { pnl: 0, count: 0 };
    emoStats[t.emotion].count++;
    emoStats[t.emotion].pnl += t.pnl;

    if (t.mistake !== 'None') {
      if (!mistakeCost[t.mistake]) mistakeCost[t.mistake] = 0;
      if (t.pnl < 0) mistakeCost[t.mistake] += Math.abs(t.pnl);
    }
  });

  let bestStrat = 'Breakout', maxWinRate = 0;
  Object.keys(stratStats).forEach(s => {
    const wr = (stratStats[s].wins / stratStats[s].total) * 100;
    if (wr > maxWinRate) {
      maxWinRate = wr;
      bestStrat = s;
    }
  });

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
async function renderAnalyticsPlots() {
  if (trades.length === 0) {
    Plotly.newPlot('equityPlot', [], {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      annotations: [{
        text: 'No trade data available. Log trades to view your cumulative equity curve.',
        font: { color: '#94a3b8', size: 14 },
        showarrow: false
      }],
      xaxis: { visible: false },
      yaxis: { visible: false }
    });
    Plotly.newPlot('strategyPnlPlot', [], {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      annotations: [{
        text: 'No strategy breakdown available.',
        font: { color: '#94a3b8', size: 14 },
        showarrow: false
      }],
      xaxis: { visible: false },
      yaxis: { visible: false }
    });
    document.getElementById('statSharpe').innerHTML = '0.00';
    document.getElementById('statSortino').innerHTML = '0.00';
    document.getElementById('statMaxDD').innerHTML = '0.00%';
    document.getElementById('statVaR').innerHTML = '$0.00';
    if (document.getElementById('statAvgR')) document.getElementById('statAvgR').innerHTML = '0.00R';
    document.getElementById('statBestTrade').innerHTML = '$0.00';
    document.getElementById('statWorstTrade').innerHTML = '$0.00';
    return;
  }

  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const [summary, strategyStats] = await Promise.all([
        api.getDashboardSummary(),
        api.getStrategyAnalytics()
      ]);

      const curve = summary.equity_curve || [];
      Plotly.newPlot('equityPlot', [{
        x: curve.map(point => point.date),
        y: curve.map(point => point.equity),
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

      Plotly.newPlot('strategyPnlPlot', [{
        x: strategyStats.map(item => item.name),
        y: strategyStats.map(item => item.pnl),
        type: 'bar',
        marker: { color: strategyStats.map(item => item.pnl >= 0 ? '#38bdf8' : '#f43f5e') }
      }], {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Inter, sans-serif', color: '#94a3b8' },
        margin: { l: 50, r: 20, t: 20, b: 60 },
        yaxis: { title: 'Cumulative P&L ($)', gridcolor: 'rgba(255,255,255,0.06)' }
      });

      document.getElementById('statSharpe').innerHTML = Number(summary.sharpe || 0).toFixed(2);
      document.getElementById('statSortino').innerHTML = Number(summary.sortino || 0).toFixed(2);
      document.getElementById('statMaxDD').innerHTML = `${Number(summary.max_drawdown_pct || 0).toFixed(2)}%`;
      document.getElementById('statVaR').innerHTML = `${Number(summary.var_95 || 0) < 0 ? '-' : ''}$${Math.abs(Number(summary.var_95 || 0)).toFixed(2)}`;
      if (document.getElementById('statAvgR')) document.getElementById('statAvgR').innerHTML = `${Number(summary.avg_r_multiple || 0).toFixed(2)}R`;
      document.getElementById('statBestTrade').innerHTML = `+$${Number(summary.best_trade || 0).toLocaleString()}`;
      document.getElementById('statWorstTrade').innerHTML = `-$${Math.abs(Number(summary.worst_trade || 0)).toLocaleString()}`;
      return;
    } catch (err) {
      console.warn('Performance analytics API failed; using local analytics.', err);
    }
  }

  // Local calculation fallback with tested mathematical formulas
  const sorted = trades.filter(t => !t.isOpen).sort((a, b) => (a.date || '').localeCompare(b.date || '') || Number(a.id) - Number(b.id));
  const pnlList = sorted.map(t => Number(t.pnl || 0));
  const wins = pnlList.filter(p => p > 0);
  const losses = pnlList.filter(p => p < 0);
  const bestTrade = pnlList.length > 0 ? Math.max(...pnlList) : 0;
  const worstTrade = pnlList.length > 0 ? Math.min(...pnlList) : 0;

  let running = 10000;
  let peak = running;
  let maxDD = 0;
  const dates = [];
  const equityValues = [];

  sorted.forEach(t => {
    running += Number(t.pnl || 0);
    peak = Math.max(peak, running);
    const dd = peak > 0 ? ((running - peak) / peak * 100) : 0;
    maxDD = Math.min(maxDD, dd);
    dates.push(t.date);
    equityValues.push(Math.round(running * 100) / 100);
  });

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

  // Completed-trade account returns; no daily annualization assumption.
  let capital = 10000;
  let solvent = true;
  const returns = pnlList.map(pnl => {
    if (capital <= 0) solvent = false;
    const ret = capital > 0 ? pnl / capital : 0;
    capital += pnl;
    return ret;
  });
  const n = returns.length;
  const avg = n ? returns.reduce((a, b) => a + b, 0) / n : 0;
  const std = n > 1 ? Math.sqrt(returns.reduce((sum, r) => sum + (r - avg) ** 2, 0) / (n - 1)) : 0;
  const downside = n ? Math.sqrt(returns.reduce((sum, r) => sum + Math.min(r, 0) ** 2, 0) / n) : 0;
  const sharpe = solvent && std > 1e-12 ? (avg / std).toFixed(2) : '0.00';
  const sortino = solvent && n > 1 && downside > 1e-12 ? (avg / downside).toFixed(2) : '0.00';
  const sortedPnl = [...pnlList].sort((a, b) => a - b);
  const quantileIndex = (sortedPnl.length - 1) * 0.05;
  const lo = Math.floor(quantileIndex), hi = Math.ceil(quantileIndex);
  const var95 = sortedPnl.length ? sortedPnl[lo] + (sortedPnl[hi] - sortedPnl[lo]) * (quantileIndex - lo) : 0;

  const rMultiples = sorted.filter(t => t.rMultiple !== null && t.rMultiple !== undefined).map(t => Number(t.rMultiple));
  const avgR = rMultiples.length > 0 ? (rMultiples.reduce((a, b) => a + b, 0) / rMultiples.length).toFixed(2) : '0.00';

  document.getElementById('statSharpe').innerHTML = sharpe;
  document.getElementById('statSortino').innerHTML = sortino;
  document.getElementById('statMaxDD').innerHTML = `${maxDD.toFixed(2)}%`;
  document.getElementById('statVaR').innerHTML = `${var95 < 0 ? '-' : ''}$${Math.abs(var95).toFixed(2)}`;
  if (document.getElementById('statAvgR')) document.getElementById('statAvgR').innerHTML = `${avgR}R`;
  document.getElementById('statBestTrade').innerHTML = `+$${bestTrade.toLocaleString()}`;
  document.getElementById('statWorstTrade').innerHTML = `-$${Math.abs(worstTrade).toLocaleString()}`;
}

// ----------------------------------------------------
// Tab 5: Technical Candlestick Market Chart
// ----------------------------------------------------
async function renderTechnicalPlots(symbol) {
  const api = getApiClient();
  if (useApiBackend && api) {
    try {
      const market = await api.getMarketData(symbol);
      const candles = market.candles || [];
      if (candles.length > 0) {
        showChartSource('marketDataNotice', market);
        const dates = candles.map(c => c.date);
        const closes = candles.map(c => c.close);

        const commonLayout = {
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { family: 'Inter, sans-serif', color: '#94a3b8' },
          margin: { l: 50, r: 20, t: 20, b: 40 },
          xaxis: { gridcolor: 'rgba(255,255,255,0.06)' },
          yaxis: { gridcolor: 'rgba(255,255,255,0.06)' }
        };

        Plotly.newPlot('techPricePlot', [
          {
            x: dates,
            open: candles.map(c => c.open),
            high: candles.map(c => c.high),
            low: candles.map(c => c.low),
            close: closes,
            type: 'candlestick',
            increasing: { line: { color: '#10b981' } },
            decreasing: { line: { color: '#f43f5e' } },
            name: symbol
          },
          {
            x: dates,
            y: candles.map(c => c.sma20),
            type: 'scatter',
            mode: 'lines',
            name: 'SMA 20',
            line: { color: '#38bdf8', width: 1.5 }
          },
          {
            x: dates,
            y: candles.map(c => c.sma50),
            type: 'scatter',
            mode: 'lines',
            name: 'SMA 50',
            line: { color: '#f59e0b', width: 1.5 }
          }
        ], {
          ...commonLayout,
          xaxis: { ...commonLayout.xaxis, rangeslider: { visible: false } }
        });

        Plotly.newPlot('techRsiPlot', [{
          x: dates,
          y: candles.map(c => c.rsi),
          type: 'scatter',
          mode: 'lines',
          line: { color: '#a855f7', width: 2 }
        }], {
          ...commonLayout,
          yaxis: { range: [0, 100], title: 'RSI (14)' }
        });

        const macdVals = candles.map(c => c.macd);
        Plotly.newPlot('techMacdPlot', [{
          x: dates,
          y: macdVals,
          type: 'bar',
          marker: { color: macdVals.map(v => v >= 0 ? '#10b981' : '#f43f5e') }
        }], commonLayout);
        return;
      }
    } catch (err) {
      console.warn('Market API failed; using local synthetic technical chart.', err);
    }
  }

  showChartSource('marketDataNotice', null);
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

