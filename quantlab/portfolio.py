"""Portfolio analytics for a fully funded, long-only, buy-and-hold research portfolio.

Risk contributions describe the *initial target weights*, not the weights after
asset prices drift. Prices should be adjusted closes at comparable trading dates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_weights(weights: dict[str, float], tickers: list[str]) -> pd.Series:
    """Validate and normalize nonnegative allocations to sum to one."""
    selected = pd.Series({t: float(weights.get(t, 0.0)) for t in tickers}, dtype=float)
    if selected.empty or (selected < 0).any() or not np.isfinite(selected).all():
        raise ValueError("Weights must be non-negative, finite numbers")
    if selected.sum() <= 0:
        raise ValueError("Allocate a positive weight to at least one asset")
    return selected / selected.sum()


def _aligned_prices(prices: pd.DataFrame, weights: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    """Start at the first common price observation; reject later missing rows.

    Dropping missing rows inside the holding period would turn multi-session
    returns into apparent one-day returns, distorting annualized risk and VaR.
    """
    if not isinstance(prices, pd.DataFrame) or not isinstance(weights, pd.Series):
        raise ValueError("Prices must be a DataFrame and weights must be a Series")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Price dates must be sorted and unique")
    if prices.columns.has_duplicates or weights.index.has_duplicates:
        raise ValueError("Ticker labels must be unique")
    weights = weights.astype(float)
    names = list(weights.index[weights > 0])
    if not names:
        raise ValueError("Allocate a positive weight to at least one asset")
    missing_tickers = [ticker for ticker in names if ticker not in prices.columns]
    if missing_tickers:
        raise ValueError(f"Missing price columns: {', '.join(map(str, missing_tickers))}")
    w = normalize_weights(weights.to_dict(), names)
    try:
        chosen = prices[names].astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Selected price columns must contain numeric prices") from exc
    chosen = chosen.replace([np.inf, -np.inf], np.nan)
    complete = chosen.notna().all(axis=1) & chosen.gt(0).all(axis=1)
    if not complete.any():
        raise ValueError("No common positive price observations for the selected assets")
    first_pos = int(np.flatnonzero(complete.to_numpy())[0])
    chosen = chosen.iloc[first_pos:]
    if not (chosen.notna() & chosen.gt(0)).all().all():
        raise ValueError(
            "Missing, non-finite or non-positive prices within the holding period. "
            "Fix price data in Data Quality before calculating portfolio risk."
        )
    return chosen, w


def buy_and_hold_portfolio(prices: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """One initial investment held without rebalancing, fees, or taxes.

    The initial observation has no preceding session; its return is NaN, not 0%.
    """
    price, w = _aligned_prices(prices, weights)
    if len(price) < 10:
        raise ValueError("Need at least 10 common price observations")
    relative = price.div(price.iloc[0])
    equity = relative.mul(w, axis=1).sum(axis=1)
    returns = equity.pct_change(fill_method=None)
    return pd.DataFrame({"Portfolio Equity": equity, "Portfolio Return": returns})


def risk_contributions(prices: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Initial-weight Euler contribution to annualized portfolio volatility.

    This is a fixed-weight covariance snapshot, *not* the changing volatility
    contribution of the drifting holdings in a buy-and-hold portfolio.
    """
    price, w = _aligned_prices(prices, weights)
    daily = price.pct_change(fill_method=None).iloc[1:]
    if len(daily) < 20:
        raise ValueError("Need 20 common daily returns for covariance estimates")
    cov = daily.cov().to_numpy() * 252
    allocations = w.to_numpy()
    variance = float(allocations @ cov @ allocations)
    volatility = float(np.sqrt(max(variance, 0.0)))
    contributions = allocations * (cov @ allocations) / volatility if volatility > 0 else np.zeros_like(allocations)
    return pd.DataFrame({"Weight": allocations, "Annualized Vol Contribution": contributions}, index=w.index)


def estimate_var(returns: pd.Series, confidence: float = 0.95) -> dict[str, float]:
    """Historical lower-tail VaR and expected shortfall from genuine returns."""
    if not 0.5 < confidence < 1:
        raise ValueError("Confidence must be between 0.5 and 1")
    observed = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    if len(observed) < 20:
        raise ValueError("Need 20 observed returns for historical VaR")
    cutoff = float(np.quantile(observed, 1 - confidence))
    tail = observed[observed <= cutoff]
    return {"Historical VaR": max(0.0, -cutoff), "Historical CVaR": max(0.0, -float(tail.mean()))}


def equal_weight_comparison(prices: pd.DataFrame) -> pd.DataFrame:
    return buy_and_hold_portfolio(prices, pd.Series(1.0, index=prices.columns))
