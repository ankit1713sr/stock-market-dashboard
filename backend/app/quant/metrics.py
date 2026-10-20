"""Shared metrics. Returns are decimal fractions; P&Ls are currency amounts.

Sharpe risk_free_rate and Sortino target_return are PER OBSERVATION, in the
same units as the input. Only annualize equally spaced returns with a known
frequency. Undefined ratios use 0 for compatibility, except positive-profit /
zero-loss trade ratios, which use None (JSON null), never a currency amount.
"""
from math import sqrt
import numpy as np
import pandas as pd


def _clean(values):
    s = pd.Series(values, dtype=float).dropna()
    if not np.isfinite(s).all():
        raise ValueError("Observations must be finite (NaN observations may be omitted).")
    return s


def _frequency(periods_per_year):
    if not np.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive and finite")


def calculate_drawdown_series(equity_or_returns, initial_equity=None):
    """Input is EQUITY, not returns. Supply initial_equity for post-return values.

    Without it, the first equity observation is the initial peak. Negative
    equity is supported (drawdown may exceed 100%); peaks must be positive.
    """
    s = pd.Series(equity_or_returns, dtype=float)
    if not np.isfinite(s).all():
        raise ValueError("Equity must be finite")
    if initial_equity is not None and (not np.isfinite(initial_equity) or initial_equity <= 0):
        raise ValueError("initial_equity must be positive and finite")
    if s.empty:
        return pd.DataFrame(columns=["equity", "peak", "drawdown", "drawdown_pct"], index=s.index)
    peak = s.cummax()
    if initial_equity is not None:
        peak = peak.clip(lower=initial_equity)
    if (peak <= 0).any():
        raise ValueError("A positive initial equity peak is required")
    dd = s - peak
    return pd.DataFrame({"equity": s, "peak": peak, "drawdown": dd,
                         "drawdown_pct": dd / peak * 100}, index=s.index)


def calculate_sharpe_ratio(returns_or_pnls, risk_free_rate=0.0, annualize=False, periods_per_year=252):
    """Arithmetic mean excess / sample standard deviation; zero if undefined."""
    _frequency(periods_per_year)
    if not np.isfinite(risk_free_rate):
        raise ValueError("risk_free_rate must be finite and per observation")
    s = _clean(returns_or_pnls) - risk_free_rate
    if len(s) < 2 or s.std(ddof=1) <= 1e-12:
        return 0.0
    return float(s.mean() / s.std(ddof=1) * (sqrt(periods_per_year) if annualize else 1))


def calculate_sortino_ratio(returns_or_pnls, target_return=0.0, annualize=False, periods_per_year=252):
    """Mean excess / sqrt(mean(min(excess, 0)^2)), over ALL observations.

    target_return is per observation. Fewer than two observations or no
    downside deviation returns the documented compatibility sentinel 0.
    """
    _frequency(periods_per_year)
    if not np.isfinite(target_return):
        raise ValueError("target_return must be finite and per observation")
    s = _clean(returns_or_pnls) - target_return
    if len(s) < 2:
        return 0.0
    dev = float(np.sqrt(np.mean(np.minimum(s, 0.0) ** 2)))
    return float(s.mean() / dev * (sqrt(periods_per_year) if annualize else 1)) if dev > 1e-12 else 0.0


def calculate_annualized_metrics(daily_returns, risk_free_rate=0.02, trading_days=252):
    """CAGR, sample volatility and arithmetic Sharpe for periodic returns.

    risk_free_rate is an effective ANNUAL rate, converted geometrically to
    the observation frequency. An initial equity of 1 catches first-bar losses.
    """
    _frequency(trading_days)
    if not np.isfinite(risk_free_rate) or risk_free_rate <= -1:
        raise ValueError("Annual risk-free rate must be finite and greater than -1")
    s = _clean(daily_returns)
    if (s < -1).any():
        raise ValueError("Periodic returns cannot be below -100%")
    if s.empty:
        return dict(total_return=0.0, ann_return=0.0, ann_volatility=0.0,
                    sharpe_ratio=0.0, max_drawdown_pct=0.0)
    equity = (1 + s).cumprod()
    total = float(equity.iloc[-1] - 1)
    ann = float(equity.iloc[-1] ** (trading_days / len(s)) - 1)
    vol = float(s.std(ddof=1) * sqrt(trading_days)) if len(s) > 1 else 0.0
    rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    return dict(total_return=round(total, 6), ann_return=round(ann, 6),
                ann_volatility=round(vol, 6),
                sharpe_ratio=round(calculate_sharpe_ratio(s, rf, True, trading_days), 4),
                max_drawdown_pct=round(float(calculate_drawdown_series(equity, 1)["drawdown_pct"].min()), 4))


def calculate_expectancy(pnls):
    """Completed-trade statistics; breakeven trades count in the denominator."""
    s = _clean(pnls)
    wins, losses = s[s > 0], -s[s < 0]
    n = len(s)
    gp, gl = float(wins.sum()), float(losses.sum())
    aw = float(wins.mean()) if len(wins) else 0.0
    al = float(losses.mean()) if len(losses) else 0.0
    return dict(total_trades=n, win_rate=round(len(wins) / n * 100, 2) if n else 0.0,
                profit_factor=round(gp / gl, 4) if gl else (None if gp else 0.0),
                avg_win=round(aw, 2), avg_loss=round(al, 2),
                win_loss_ratio=round(aw / al, 4) if al else (None if aw else 0.0),
                expectancy=round(float(s.mean()), 2) if n else 0.0)


def calculate_var_historical(values, confidence_level=0.95):
    """Signed lower-tail quantile, in input units (not positive loss VaR)."""
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    s = _clean(values)
    return float(np.percentile(s, (1 - confidence_level) * 100)) if len(s) else 0.0
