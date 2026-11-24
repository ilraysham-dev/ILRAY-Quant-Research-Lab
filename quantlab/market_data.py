"""Optional Yahoo historical-price adapter. Always label source and freshness."""
from __future__ import annotations

import pandas as pd
from .engine import clean_prices


DEFAULT_TICKERS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "TLT", "GLD", "EEM"]


def download_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    import yfinance as yf

    symbols = list(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))
    if not 1 <= len(symbols) <= 30:
        raise ValueError("Select between 1 and 30 ticker symbols")
    raw = yf.download(symbols, period=period, auto_adjust=True, progress=False,
                      threads=False, group_by="column")
    if raw.empty:
        raise ValueError("Data provider returned no prices. Check symbols or network access.")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]].rename(columns={"Close": symbols[0]})
    prices = clean_prices(close)
    if len(prices) < 30:
        raise ValueError("Provider returned fewer than 30 sessions; inspect coverage before using results")
    return prices
