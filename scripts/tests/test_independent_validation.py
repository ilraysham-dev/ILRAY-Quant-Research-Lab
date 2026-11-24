"""Independent numerical fixtures and mocked provider contracts.
These tests do NOT substitute for full financial-model validation with real data.
"""
import sys
import types
import numpy as np
import pandas as pd
import pytest
from quantlab.engine import backtest, etf_rankings, monte_carlo
from quantlab.market_data import download_prices
from quantlab.macro_data import download_us_macro


def test_backtest_known_positions_fees_and_lag():
    idx = pd.bdate_range("2024-01-01", periods=5)
    close = pd.Series([100., 110., 121., 108.9, 119.79], index=idx)
    signal = pd.Series([1., 1., 0., 0., 1.], index=idx)
    out = backtest(close, signal, fee_bps=10)
    # First session: no position. Next-session execution and 10 bps one-way fees.
    assert out["Held Exposure"].to_list() == [0., 1., 1., 0., 0.]
    assert out["Strategy Return"].to_numpy() == pytest.approx([0., .099, .10, -.001, 0.])
    expected_equity = np.prod([1., 1.099, 1.1, .999, 1.])
    assert out["Strategy Equity"].iloc[-1] == pytest.approx(expected_equity)


def test_etf_ranker_checks_return_and_volatility_independently():
    idx = pd.bdate_range("2024-01-01", periods=6)
    vals = np.array([100., 103., 101., 106., 105., 110.])
    prices = pd.DataFrame({"AAA": vals}, index=idx)
    out = etf_rankings(prices, lookback=5)
    daily = np.diff(vals) / vals[:-1]
    assert out.loc["AAA", "Return"] == pytest.approx(.10)
    assert out.loc["AAA", "Annualized Vol"] == pytest.approx(np.std(daily, ddof=1) * np.sqrt(252))
    assert out.loc["AAA", "Worst Drawdown"] == pytest.approx(min(vals / np.maximum.accumulate(vals) - 1))


def test_monte_carlo_constant_return_compounds_exactly():
    sample = pd.Series([.01] * 30)
    scenarios = monte_carlo(sample, days=5, paths=300, seed=4)
    for d in range(6):
        assert scenarios.loc[d, "Median"] == pytest.approx(1.01 ** d)
        assert scenarios.loc[d, "P05"] == pytest.approx(1.01 ** d)


def test_yahoo_adapter_mocked_multi_ticker(monkeypatch):
    idx = pd.bdate_range("2024-01-01", periods=50)
    columns = pd.MultiIndex.from_product([["Close"], ["SPY", "QQQ"]])
    frame = pd.DataFrame(np.column_stack([100 + np.arange(50), 200 + np.arange(50)]), index=idx, columns=columns)
    fake = types.SimpleNamespace(download=lambda *a, **k: frame)
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    actual = download_prices(["SPY", "QQQ"], period="1y")
    assert list(actual.columns) == ["SPY", "QQQ"]
    assert len(actual) == 50
    assert actual.iloc[0, 0] == 100


def test_yahoo_adapter_empty_response_is_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=lambda *a, **k: pd.DataFrame()))
    with pytest.raises(ValueError, match="no prices"):
        download_prices(["SPY"])


def test_fred_returns_quarterly_inflation_growth(monkeypatch):
    class Response:
        def __init__(self, data):
            self.content = data.encode()
        def raise_for_status(self): pass
    class Session:
        def get(self, url, params, timeout):
            kind = params["id"]
            dates = pd.date_range("2019-01-01", periods=32 if kind == "GDPC1" else 96,
                                  freq="QS" if kind == "GDPC1" else "MS")
            vals = np.arange(len(dates)) + 100
            return Response("DATE," + kind + "\n" + "".join(f"{dt.date()},{val}\n" for dt, val in zip(dates, vals)))
    macro = download_us_macro(Session())
    assert len(macro) >= 20
    assert (macro["GDP"] > 0).all() and (macro["Inflation"] > 0).all()
    assert macro["Date"].is_monotonic_increasing
