"""Descriptive, end-of-day market regime classification. Research only."""
from __future__ import annotations
import numpy as np
import pandas as pd


def market_regimes(prices: pd.Series, fast: int = 50, slow: int = 200,
                   volatility_window: int = 21, history_window: int = 252,
                   high_vol_percentile: float = 0.75) -> pd.DataFrame:
    """Classify price history as Uptrend, Downtrend, Sideways, or High volatility.

    Signal uses same-day closing data and is descriptive AS OF the close, never a
    tradeable before-close forecast. High-vol threshold uses only PREVIOUS vol
    measurements (shifted rolling quantile). Missing rows are not forward-filled.
    """
    if not (2 <= fast < slow):
        raise ValueError("Require 2 <= fast < slow.")
    if volatility_window < 2 or history_window < 10:
        raise ValueError("Volatility window must be >=2 and history window >=10.")
    if not (0 < high_vol_percentile < 1):
        raise ValueError("High-vol percentile must lie between 0 and 1.")
    p = pd.to_numeric(prices, errors="coerce").astype(float).sort_index()
    if not p.index.is_unique:
        raise ValueError("Price dates must be unique.")
    p = p.where(np.isfinite(p) & (p > 0))
    ret = p.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    a = p.rolling(fast, min_periods=fast).mean()
    b = p.rolling(slow, min_periods=slow).mean()
    vol = ret.rolling(volatility_window, min_periods=volatility_window).std() * np.sqrt(252)
    threshold = vol.shift(1).rolling(history_window, min_periods=max(10, history_window // 4)).quantile(high_vol_percentile)
    label = pd.Series("Insufficient data", index=p.index, dtype="object")
    ready = a.notna() & b.notna() & vol.notna() & threshold.notna() & p.notna()
    label.loc[ready & (a > b) & (p > b)] = "Uptrend"
    label.loc[ready & (a < b) & (p < b)] = "Downtrend"
    label.loc[ready & ~((a > b) & (p > b)) & ~((a < b) & (p < b))] = "Sideways"
    label.loc[ready & (vol > threshold)] = "High volatility"
    return pd.DataFrame({"Price":p, "Daily Return":ret, "Fast MA":a, "Slow MA":b,
                         "Annualized Volatility":vol, "Historical Vol Threshold":threshold,
                         "Regime":label})
