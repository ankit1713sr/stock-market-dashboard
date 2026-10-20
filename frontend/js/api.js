/**
 * TradePulse AI – Frontend API Client
 *
 * Centralised fetch wrapper that talks to the FastAPI backend.
 * Compatible with standard <script> tags as well as ES Module imports.
 */

const API_BASE = "http://127.0.0.1:8000";

/**
 * Core fetch helper with timeout and clear error messaging.
 */
async function apiFetch(path, options = {}) {
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
      throw new Error(msg);
    }

    if (response.status === 204) return null;
    return response.json();
  } catch (err) {
    clearTimeout(timeoutId);
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
