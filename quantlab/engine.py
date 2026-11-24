"""Research engine. These are documented reference models, NOT claimed Excel/VBA parity."""
from __future__ import annotations

import numpy as np
import pandas as pd


def clean_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate a wide Date x ticker close-price table."""
    df = frame.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date")
    else:
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.loc[:, df.notna().sum() >= 5]
    if df.empty:
        raise ValueError("Need a Date column and at least one ticker with five valid prices.")
    # Missing prices must remain missing. Forward-filling them can turn absent
    # observations into artificial 0% returns and misleading low volatility.
    # Preserve gaps in individual tickers, but discard dates with no valid
    # prices for ANY ticker (e.g. an incomplete provider-wide latest row).
    # These empty dates are not trading sessions and should not invalidate
    # every ticker's trailing quality window.
    df = df.where(df > 0)
    return df.dropna(how="all")


def etf_rankings(prices: pd.DataFrame, lookback: int = 63) -> pd.DataFrame:
    """Cross-sectional trailing-return score, with explicit risk metrics."""
    if lookback < 2:
        raise ValueError("Lookback must be at least two trading days")
    if len(prices) <= lookback:
        return pd.DataFrame(columns=["Return", "Annualized Vol", "Worst Drawdown", "Score"])
    # Strict eligibility: require a complete, positive price series across
    # the entire trailing calculation window, including the latest date.
    window = prices.tail(lookback + 1)
    eligible = window.columns[window.notna().all() & window.gt(0).all()]
    if len(eligible) == 0:
        return pd.DataFrame(columns=["Return", "Annualized Vol", "Worst Drawdown", "Score"])
    clean = window[eligible]
    daily = clean.pct_change(fill_method=None)
    total = clean.iloc[-1] / clean.iloc[0] - 1
    vol = daily.iloc[1:].std() * np.sqrt(252)
    drawdown = (clean / clean.cummax() - 1).min()
    result = pd.DataFrame({"Return": total, "Annualized Vol": vol, "Worst Drawdown": drawdown})
    result["Score"] = result["Return"] / result["Annualized Vol"].replace(0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan).dropna().sort_values("Score", ascending=False)


def classify_quad(macro: pd.DataFrame, periods: int = 3) -> pd.DataFrame:
    """Quadrants from GDP and inflation *changes* (a simple, explicit assumption)."""
    df = macro.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.set_index("Date")
    df = df.sort_index()
    for col in ("GDP", "Inflation"):
        if col not in df:
            raise ValueError("Macro data needs Date, GDP, Inflation columns")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    growth_up = df["GDP"].diff(periods) > 0
    inflation_up = df["Inflation"].diff(periods) > 0
    quadrants = np.select(
        [growth_up & ~inflation_up, growth_up & inflation_up,
         ~growth_up & inflation_up, ~growth_up & ~inflation_up],
        ["Goldilocks", "Reflation", "Stagflation", "Disinflation"],
        default="Unknown",
    )
    df["Regime"] = quadrants
    df.loc[df.index[:periods], "Regime"] = "Insufficient history"
    return df


def signals(close: pd.Series, fast: int = 20, slow: int = 80) -> pd.Series:
    """Trend-following target weights, either 0 or 1, known after each close."""
    if fast >= slow or fast < 2:
        raise ValueError("Require 2 <= fast < slow")
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    return (fast_ma > slow_ma).astype(float).rename("Target Exposure")


def backtest(close: pd.Series, target: pd.Series, fee_bps: float = 5.0) -> pd.DataFrame:
    """Next-day execution; fee on absolute position change; no margin or shorts."""
    close = pd.to_numeric(close, errors="coerce").dropna()
    target = target.reindex(close.index).fillna(0).clip(0, 1)
    execution = target.shift(1).fillna(0)  # no same-bar lookahead
    returns = close.pct_change(fill_method=None).fillna(0)
    turnover = execution.diff().abs().fillna(execution.abs())
    strategy_returns = execution * returns - turnover * (fee_bps / 10000)
    return pd.DataFrame({
        "Close": close, "Signal": target, "Held Exposure": execution,
        "Market Return": returns, "Strategy Return": strategy_returns,
        "Strategy Equity": (1 + strategy_returns).cumprod(),
        "Buy Hold Equity": (1 + returns).cumprod(), "Turnover": turnover,
    })


def performance(returns: pd.Series, equity: pd.Series) -> dict[str, float]:
    returns = returns.dropna()
    if returns.empty:
        return {"Total Return": 0., "Annualized Vol": 0., "Sharpe (rf=0)": 0., "Max Drawdown": 0.}
    vol = returns.std() * np.sqrt(252)
    return {
        "Total Return": float(equity.iloc[-1] - 1),
        "Annualized Vol": float(vol),
        "Sharpe (rf=0)": float(returns.mean() * 252 / vol) if vol > 0 else 0.,
        "Max Drawdown": float((equity / equity.cummax() - 1).min()),
    }


def monte_carlo(daily_returns: pd.Series, days: int = 126,
                paths: int = 1000, seed: int = 42) -> pd.DataFrame:
    """IID bootstrap of observed returns. Scenarios are not probabilities of future outcomes."""
    sample = daily_returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if len(sample) < 10:
        raise ValueError("At least 10 observed returns required")
    rng = np.random.default_rng(seed)
    draws = rng.choice(sample, size=(days, paths), replace=True)
    equity_paths = np.vstack([np.ones(paths), np.cumprod(1 + draws, axis=0)])
    quantiles = np.percentile(equity_paths, [5, 25, 50, 75, 95], axis=1)
    return pd.DataFrame(quantiles.T, columns=["P05", "P25", "Median", "P75", "P95"]).rename_axis("Day")


def make_demo_data(seed: int = 7, days: int = 750) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic synthetic data for exploring UI, not market observations."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    names = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "GLD", "TLT", "EEM", "XLE"]
    market = rng.normal(.00025, .009, size=days)
    price = {}
    for i, name in enumerate(names):
        r = (0.5 + (i % 5) * 0.15) * market + rng.normal(.00012, .004 + .0012 * (i % 4), days)
        price[name] = 100 * np.cumprod(1 + r)
    quarterly = pd.date_range(index.min(), index.max(), freq="QS")
    gdp = 2.1 + np.sin(np.arange(len(quarterly)) / 2) * .9 + rng.normal(0, .1, len(quarterly))
    inf = 2.7 + np.cos(np.arange(len(quarterly)) / 2.8) * 1.2 + rng.normal(0, .1, len(quarterly))
    macro = pd.DataFrame({"Date": quarterly, "GDP": gdp, "Inflation": inf})
    return pd.DataFrame(price, index=index), macro
