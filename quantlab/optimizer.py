"""Educational long-only optimizer: train estimates; evaluate on chronological holdout.

Reference models, not trading recommendations. Training periods use complete
common-session adjusted prices; no forward filling, no short selling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


def prepare_returns(prices: pd.DataFrame, tickers: list[str], train_fraction: float = .75,
                    min_training: int = 60, min_holdout: int = 20) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(tickers) < 2 or len(set(tickers)) != len(tickers):
        raise ValueError("Select at least two distinct ETFs.")
    if not 0.5 <= train_fraction <= .9:
        raise ValueError("Training fraction must be between 50% and 90%.")
    if not set(tickers).issubset(prices.columns):
        raise ValueError("One or more selected ETF tickers are missing.")
    selected = prices.loc[:, tickers].copy()
    if not isinstance(selected.index, pd.DatetimeIndex):
        selected.index = pd.to_datetime(selected.index, errors='coerce')
    selected = selected.loc[~selected.index.isna()].sort_index()
    if selected.index.has_duplicates:
        raise ValueError("Duplicate dates in historical prices.")
    selected = selected.apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(selected.dropna().to_numpy()).all():
        raise ValueError("Non-finite price detected.")
    selected = selected.where(selected > 0)
    # Retain only dates on which ALL selected assets have real positive prices.
    # Reject gaps rather than letting pct_change bridge stale/missing sessions.
    full = selected.dropna()
    if len(full) < min_training + min_holdout + 1:
        raise ValueError("Not enough common complete price observations for training and holdout.")
    # Missing dates are allowed for weekends/holidays; large holes flag data issues.
    if (full.index.to_series().diff().dropna() > pd.Timedelta(days=10)).any():
        raise ValueError("Selected ETFs have a gap over 10 calendar days; inspect Data Quality.")
    # Split by rows of prices, then get returns independently, keeping the previous
    # training close as the reference price for the first holdout return.
    split = int(len(full) * train_fraction)
    split = max(min_training + 1, min(split, len(full) - min_holdout))
    all_returns = full.pct_change(fill_method=None).iloc[1:]
    if (all_returns <= -1).any().any() or not np.isfinite(all_returns.to_numpy()).all():
        raise ValueError("Invalid return series.")
    train = all_returns.iloc[:split - 1]
    test = all_returns.iloc[split - 1:]
    return train, test


def risk_contributions(weights: np.ndarray, cov_annual: np.ndarray) -> np.ndarray:
    vol = float(np.sqrt(max(weights @ cov_annual @ weights, 0)))
    return weights * (cov_annual @ weights) / vol if vol > 1e-12 else np.zeros_like(weights)


def optimize_weights(train_returns: pd.DataFrame, objective: str = "Minimum volatility",
                     max_weight: float = 1., risk_free_rate: float = 0.) -> pd.Series:
    n = train_returns.shape[1]
    if n < 2 or len(train_returns) < 20:
        raise ValueError("Need at least two assets and 20 complete training returns.")
    if max_weight <= 0 or max_weight > 1 or n * max_weight < 1 - 1e-9:
        raise ValueError("Maximum weight too small for this many assets.")
    mu = train_returns.mean().to_numpy(dtype=float) * TRADING_DAYS
    cov = train_returns.cov().to_numpy(dtype=float) * TRADING_DAYS
    if not np.isfinite(mu).all() or not np.isfinite(cov).all():
        raise ValueError("Return estimates contain invalid values.")
    if np.trace(cov) <= 1e-12:
        raise ValueError("No measurable volatility; optimization is not meaningful.")
    # Tiny ridge only to improve numerical stability of near-singular covariance.
    cov = cov + np.eye(n) * 1e-10
    equal = np.full(n, 1. / n)

    def objective_fn(w: np.ndarray) -> float:
        variance = max(float(w @ cov @ w), 1e-16)
        if objective == "Minimum volatility":
            return variance
        if objective == "Maximum historical Sharpe":
            return -float((w @ mu - risk_free_rate) / np.sqrt(variance))
        if objective == "Risk parity":
            # Match *risk contributions* across assets, not capital weights.
            rc = risk_contributions(w, cov)
            return float(np.sum((rc - np.mean(rc)) ** 2) / variance)
        raise ValueError("Unknown optimization objective.")

    if objective not in {"Minimum volatility", "Maximum historical Sharpe", "Risk parity"}:
        raise ValueError("Unknown optimization objective.")
    result = minimize(objective_fn, equal, method="SLSQP", bounds=[(0., max_weight)] * n,
                      constraints=[{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}],
                      options={'maxiter': 2000, 'ftol': 1e-12})
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"Optimizer did not converge: {result.message}")
    w = np.clip(result.x, 0, max_weight)
    if abs(w.sum() - 1) > 1e-5:
        raise RuntimeError("Optimizer produced invalid allocation weights.")
    return pd.Series(w / w.sum(), index=train_returns.columns, name=objective)


def summary_metrics(returns: pd.Series, risk_free_rate: float = 0.) -> dict[str, float]:
    series = returns.dropna()
    if series.empty:
        raise ValueError("Empty return series")
    equity = (1 + series).cumprod()
    vol = float(series.std(ddof=1) * np.sqrt(TRADING_DAYS))
    sharpe = float((series.mean() * TRADING_DAYS - risk_free_rate) / vol) if vol > 0 else float('nan')
    wealth = pd.concat([pd.Series([1.], index=[-1]), pd.Series(equity.to_numpy())], ignore_index=True)
    return {'Total return': float(equity.iloc[-1] - 1), 'Annualized volatility': vol,
            'Sharpe (rf assumed)': sharpe, 'Maximum drawdown': float((wealth / wealth.cummax() - 1).min())}


def holdout_comparison(test_returns: pd.DataFrame, optimized: pd.Series,
                       risk_free_rate: float = 0.) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Constant daily weights (daily rebalancing), no costs. Evaluate only holdout."""
    w = optimized.reindex(test_returns.columns).to_numpy()
    equal = np.full(len(w), 1. / len(w))
    strategy = pd.Series(test_returns.to_numpy() @ w, index=test_returns.index)
    reference = pd.Series(test_returns.to_numpy() @ equal, index=test_returns.index)
    equity = pd.DataFrame({'Optimized (holdout)': (1 + strategy).cumprod(),
                           'Equal weight (holdout)': (1 + reference).cumprod()})
    stats = pd.DataFrame({'Optimized': summary_metrics(strategy, risk_free_rate),
                          'Equal weight': summary_metrics(reference, risk_free_rate)})
    return equity, stats


def sample_portfolios(train_returns: pd.DataFrame, count: int = 400,
                      seed: int = 7, risk_free_rate: float = 0.) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = train_returns.shape[1]
    weights = rng.dirichlet(np.ones(n), size=count)
    mu = train_returns.mean().to_numpy() * TRADING_DAYS
    cov = train_returns.cov().to_numpy() * TRADING_DAYS
    vols = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', weights, cov, weights), 0))
    returns = weights @ mu
    return pd.DataFrame({'Historical annual return': returns,
                         'Historical annual volatility': vols,
                         'Historical Sharpe': np.divide(returns - risk_free_rate, vols,
                                                       out=np.full(count, np.nan), where=vols > 0)})
