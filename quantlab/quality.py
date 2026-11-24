"""Input quality gates: stale assets cannot silently enter an ETF ranking."""
from __future__ import annotations

import numpy as np
import pandas as pd


def price_quality_report(prices: pd.DataFrame, lookback: int = 63,
                         as_of: pd.Timestamp | None = None, max_age_days: int = 7) -> pd.DataFrame:
    """Per-symbol quality assessment, with dates and strict trailing-window eligibility.

    `as_of` is the evaluation timestamp, not the last date in the worksheet.
    This prevents a workbook with padded future dates from appearing current.
    """
    today = pd.Timestamp.today().normalize() if as_of is None else pd.Timestamp(as_of).normalize()
    if today.tz is not None:
        today = today.tz_localize(None)
    index = pd.to_datetime(prices.index)
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)
    frame = prices.copy()
    frame.index = index
    frame = frame.sort_index()
    frame = frame.loc[frame.index <= today]
    records = []
    for symbol in prices.columns:
        series = pd.to_numeric(frame[symbol], errors="coerce") if not frame.empty else pd.Series(dtype=float)
        valid = series.where(series > 0).dropna()
        recent = series.tail(lookback + 1)
        last = valid.index[-1] if not valid.empty else pd.NaT
        age = (today - last).days if pd.notna(last) else np.nan
        complete = len(recent) == lookback + 1 and recent.notna().all() and recent.gt(0).all()
        fresh = pd.notna(age) and age <= max_age_days
        status = "ELIGIBLE" if complete and fresh else (
            "STALE" if not fresh else "GAPS / SHORT HISTORY")
        records.append({"Ticker": symbol, "Last valid price": last,
                        "Days since update": age, "Recent complete": bool(complete),
                        "Status": status})
    return pd.DataFrame(records).set_index("Ticker")
