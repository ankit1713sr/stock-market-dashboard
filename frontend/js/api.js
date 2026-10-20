/**
 * TradePulse AI – Frontend API Client
 *
 * Centralised fetch wrapper that talks to the FastAPI backend.
 * Compatible with standard <script> tags as well as ES Module imports.
 */

function configuredApiBase() {
  const value = typeof window !== 'undefined' ? window.TRADEPULSE_CONFIG?.apiBaseUrl : '';
  if (!value) return '';
  const url = new URL(value);
  const localHosts = ['localhost', '127.0.0.1', '[::1]'];
  const localPage = typeof window !== 'undefined' && localHosts.includes(window.location?.hostname);
  if (url.username || url.password || url.search || url.hash ||
      (url.protocol !== 'https:' && !(localPage && localHosts.includes(url.hostname) && url.protocol === 'http:')) ||
      (!localPage && localHosts.includes(url.hostname))) {
    throw new Error('Invalid public API address; use HTTPS without credentials or query parameters.');
  }
  return url.href.replace(/\/$/, '');
}
const API_BASE = configuredApiBase();

/**
 * Core fetch helper with timeout and clear error messaging.
 */
async function apiFetch(path, options = {}) {
  if (!API_BASE) throw new Error('API not configured; offline/local-cache mode.');
  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || 6000);

  const defaults = {
    headers: { "Content-Type": "application/json" },
    signal: controller.signal
  };

  try {
    const response = await fetch(url, { ...defaults, ...options });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let msg = `API error ${response.status}`;
      try {
        const err = await response.json();
        msg = err.detail || msg;
      } catch (_) { /* non-JSON body */ }
      const error = new Error(msg);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) return null;
    return response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if ((!err.status || err.status >= 500) && typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new Event('tradepulse:api-unavailable'));
    }
    throw err;
  }
}

// ─── Public API Surface ───────────────────────────────────────────────────────

async function checkHealth() {
  return apiFetch("/health", { timeout: 3000 });
}

async function getTrades() {
  return apiFetch("/api/trades");
}

async function createTrade(trade) {
  return apiFetch("/api/v1/trades", {
    method: "POST",
    body: JSON.stringify(trade),
  });
}

async function updateTrade(id, trade) {
  return apiFetch(`/api/v1/trades/${id}`, {
    method: "PUT",
    body: JSON.stringify(trade),
  });
}

async function deleteTrade(id) {
  return apiFetch(`/api/v1/trades/${id}`, { method: "DELETE" });
}

async function getCalendar(year, month) {
  return apiFetch(`/api/v1/calendar/${year}/${month}`);
}

async function getDashboardSummary() {
  return apiFetch("/api/v1/dashboard/summary");
}

async function getCostCoverage() {
  return apiFetch("/api/v1/analytics/cost-coverage");
}

async function getStrategyAnalytics() {
  return apiFetch("/api/v1/analytics/strategy");
}

async function getEmotionAnalytics() {
  return apiFetch("/api/v1/analytics/emotion");
}

async function getMistakeAnalytics() {
  return apiFetch("/api/v1/analytics/mistakes");
}

async function calculatePositionSize(payload) {
  return apiFetch("/api/v1/risk/position-size", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function getMarketData(ticker) {
  return apiFetch(`/api/v1/market/${encodeURIComponent(ticker)}`);
}

async function pingBackend() {
  try {
    const t0 = performance.now();
    const health = await checkHealth();
    const latency = Math.round(performance.now() - t0);
    console.info(
      `%c[TradePulse API] Connected: ${health.service} | SQLite DB (${health.trades_count} trades) | Latency: ${latency}ms`,
      "color: #10b981; font-weight: 700;"
    );
    return { ...health, latency };
  } catch (err) {
    console.warn(
      `%c[TradePulse API] Offline / Unreachable — falling back to local storage cache. (${err.message})`,
      "color: #f59e0b; font-weight: 700;"
    );
    return null;
  }
}

const TradePulseAPI = {
  checkHealth,
  getTrades,
  createTrade,
  updateTrade,
  deleteTrade,
  getCalendar,
  getDashboardSummary,
  getCostCoverage,
  getStrategyAnalytics,
  getEmotionAnalytics,
  getMistakeAnalytics,
  calculatePositionSize,
  getMarketData,
  pingBackend,
};

if (typeof window !== "undefined") {
  window.TradePulseAPI = TradePulseAPI;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = TradePulseAPI;
}
