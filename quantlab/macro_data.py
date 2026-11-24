"""Historical US macro inputs from FRED CSV, with provenance and no synthetic fallback.

GDPC1: quarterly real GDP (billions of chained dollars).
CPIAUCSL: monthly consumer price index (index level).
Both are converted to year-over-year percent changes; CPI is averaged by quarter.
FRED's latest vintage is revised history, not point-in-time/release-date data.
"""
from __future__ import annotations

import io
import pandas as pd
import requests


FRED_GRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def _fred_series(series_id: str, session=None) -> pd.Series:
    requester = session or requests
    response = requester.get(FRED_GRAPH, params={"id": series_id}, timeout=25)
    response.raise_for_status()
    frame = pd.read_csv(io.BytesIO(response.content))
    date_col = "DATE" if "DATE" in frame else "observation_date"
    if date_col not in frame or series_id not in frame:
        raise ValueError(f"FRED response missing {series_id} or observation date")
    idx = pd.to_datetime(frame[date_col], errors="coerce")
    vals = pd.to_numeric(frame[series_id].replace(".", pd.NA), errors="coerce")
    result = pd.Series(vals.to_numpy(), index=idx, name=series_id).dropna().sort_index()
    if result.empty:
        raise ValueError(f"No observations returned for {series_id}")
    return result


def download_us_macro(session=None) -> pd.DataFrame:
    """Return historical quarterly GDP and CPI year-over-year % rates.

    Observation quarters are NOT the dates at which figures were released.
    Never use this revised series as a contemporaneously tradable backtest signal.
    """
    real_gdp = _fred_series("GDPC1", session)
    cpi_monthly = _fred_series("CPIAUCSL", session)
    gdp = real_gdp.resample("QS").last().pct_change(4, fill_method=None).mul(100)
    cpi_quarterly = cpi_monthly.resample("QS").mean()
    inflation = cpi_quarterly.pct_change(4, fill_method=None).mul(100)
    combined = pd.concat([gdp.rename("GDP"), inflation.rename("Inflation")], axis=1).dropna()
    if combined.empty:
        raise ValueError("Real GDP and CPI data have no common quarterly observations")
    return combined.rename_axis("Date").reset_index()
