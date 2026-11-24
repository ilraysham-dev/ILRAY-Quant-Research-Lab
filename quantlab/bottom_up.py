"""Transparent per-ETF trend/volatility regimes; not source workbook parity."""
from __future__ import annotations

import numpy as np
import pandas as pd


def asset_regimes(prices: pd.DataFrame, trend_window: int = 63,
                  vol_window: int = 63, vol_threshold: float = .25) -> pd.DataFrame:
    """Current asset states from *past* daily prices.

    Trend = trailing percent return, high volatility > user-specified annualized
    cutoff. Regime labels are descriptive; not buy/sell recommendations.
    """
    if trend_window < 5 or vol_window < 5 or not 0 < vol_threshold < 5:
        raise ValueError('Use windows >=5 and a positive annualized volatility threshold')
    output = []
    for symbol in prices.columns:
        s = pd.to_numeric(prices[symbol], errors='coerce')
        tail = s.iloc[-max(trend_window, vol_window)-1:]
        if len(tail) < max(trend_window, vol_window)+1 or tail.isna().any() or (tail <= 0).any():
            output.append({'Symbol':symbol,'Trend Return':np.nan,'Annualized Vol':np.nan,
                           'Regime':'Insufficient data'})
            continue
        t = float(tail.iloc[-1]/tail.iloc[-trend_window-1]-1)
        v = float(tail.pct_change(fill_method=None).iloc[-vol_window:].std()*np.sqrt(252))
        mode = 'Rising' if t > 0 else 'Falling'
        mode += ' / High Vol' if v > vol_threshold else ' / Lower Vol'
        output.append({'Symbol':symbol,'Trend Return':t,'Annualized Vol':v,'Regime':mode})
    return pd.DataFrame(output).set_index('Symbol')
