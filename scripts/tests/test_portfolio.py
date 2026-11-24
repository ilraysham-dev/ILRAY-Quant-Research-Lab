import numpy as np
import pandas as pd
import pytest

from quantlab.portfolio import normalize_weights, buy_and_hold_portfolio, risk_contributions, estimate_var


def test_weights_sum_to_one():
    weights = normalize_weights({"A": 30, "B": 70}, ["A", "B"])
    assert np.isclose(weights.sum(), 1)
    with pytest.raises(ValueError):
        normalize_weights({"A": -1, "B": 10}, ["A", "B"])


def test_initial_buy_and_hold_allocation():
    index = pd.date_range("2022-01-01", periods=30)
    prices = pd.DataFrame({"A": [100] * 30, "B": np.linspace(100, 200, 30)}, index=index)
    result = buy_and_hold_portfolio(prices, pd.Series({"A": 50, "B": 50}))
    assert np.isclose(result["Portfolio Equity"].iloc[-1], 1.5)


def test_risk_attribution():
    rng = np.random.default_rng(11)
    idx = pd.date_range("2020-01-01", periods=150)
    prices = pd.DataFrame({"A": 100 * np.cumprod(1+rng.normal(0,.01,150)),
                           "B": 100 * np.cumprod(1+rng.normal(0,.02,150))},index=idx)
    r = risk_contributions(prices,pd.Series({"A": .5, "B": .5}))
    assert len(r) == 2
    assert np.isfinite(r.to_numpy()).all()


def test_tail_loss():
    result = estimate_var(pd.Series(np.linspace(-.2, .2, 100)))
    assert result["Historical CVaR"] >= result["Historical VaR"] >= 0
