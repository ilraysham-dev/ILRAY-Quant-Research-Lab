import numpy as np
import pandas as pd

from quantlab.engine import (backtest, classify_quad, clean_prices, etf_rankings,
                             make_demo_data, monte_carlo, performance, signals)


def test_clean_prices():
    df = pd.DataFrame({"Date": pd.date_range("2020-01-01", periods=6), "SPY": range(1, 7)})
    result = clean_prices(df)
    assert list(result.columns) == ["SPY"]
    assert result.index.is_monotonic_increasing


def test_macro_quad():
    macro = pd.DataFrame({"Date": pd.date_range("2020-01-01", periods=4),
                          "GDP": [1, 2, 3, 4], "Inflation": [4, 3, 2, 1]})
    assert classify_quad(macro, periods=1).iloc[-1]["Regime"] == "Goldilocks"


def test_backtest_applies_next_bar_not_current_bar():
    idx = pd.date_range("2020-01-01", periods=3)
    prices = pd.Series([100, 110, 121], index=idx)
    signal = pd.Series([0, 1, 0], index=idx)
    result = backtest(prices, signal, fee_bps=0)
    assert result["Strategy Return"].iloc[1] == 0
    assert np.isclose(result["Strategy Return"].iloc[2], .1)


def test_turnover_fee():
    idx = pd.date_range("2020-01-01", periods=3)
    result = backtest(pd.Series([100, 100, 100], index=idx),
                      pd.Series([1, 1, 1], index=idx), fee_bps=10)
    assert np.isclose(result["Strategy Return"].iloc[1], -.001)


def test_demo_rank_and_backtest():
    prices, macro = make_demo_data()
    assert len(prices.columns) == 10
    assert not etf_rankings(prices).empty
    assert len(classify_quad(macro)) > 0
    target = signals(prices["SPY"])
    bt = backtest(prices["SPY"], target)
    assert bt["Strategy Equity"].iloc[-1] > 0
    assert "Max Drawdown" in performance(bt["Strategy Return"], bt["Strategy Equity"])


def test_monte_carlo_is_reproducible():
    returns = pd.Series(np.linspace(-.01, .01, 50))
    a = monte_carlo(returns, days=10, paths=200, seed=12)
    b = monte_carlo(returns, days=10, paths=200, seed=12)
    pd.testing.assert_frame_equal(a, b)
    assert np.isclose(a["Median"].iloc[0], 1)


def test_missing_price_is_not_filled_or_ranked():
    idx = pd.date_range("2026-01-01", periods=100)
    prices = pd.DataFrame({"GOOD": np.linspace(100, 120, 100),
                           "BAD": np.linspace(50, 60, 100)}, index=idx)
    prices.loc[idx[-2], "BAD"] = np.nan
    cleaned = clean_prices(prices)
    assert np.isnan(cleaned.loc[idx[-2], "BAD"])
    ranking = etf_rankings(cleaned, lookback=20)
    assert "GOOD" in ranking.index
    assert "BAD" not in ranking.index
