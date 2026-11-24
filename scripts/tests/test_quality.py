import numpy as np
import pandas as pd
from quantlab.quality import price_quality_report


def test_stale_and_recent_prices():
    idx = pd.date_range("2026-09-01", periods=65, freq="D")
    df = pd.DataFrame({"RECENT": np.arange(65)+100., "STALE": np.arange(65)+200.},index=idx)
    df.loc[idx[-14]:, "STALE"] = np.nan
    report = price_quality_report(df, lookback=20, as_of=idx[-1])
    assert report.loc["RECENT", "Status"] == "ELIGIBLE"
    assert report.loc["STALE", "Status"] == "STALE"


def test_future_padding_does_not_count_as_current():
    idx = pd.date_range("2026-01-01", periods=60, freq="D")
    df = pd.DataFrame({"SPY": np.arange(60)+100.},index=idx)
    report = price_quality_report(df, lookback=20, as_of="2026-01-20")
    assert report.loc["SPY", "Status"] == "GAPS / SHORT HISTORY"
