import numpy as np
import pandas as pd
import pytest
from quantlab.validation import holdout_backtest


def test_holdout_is_chronological_and_partitioned():
    index = pd.bdate_range('2024-01-01', periods=220)
    close = pd.Series(100 * np.cumprod(np.full(220, 1.001)), index=index)
    timeline, report = holdout_backtest(close, 20, 80, .75, 5)
    assert len(timeline) == 220
    assert timeline['Sample'].value_counts()['Holdout'] == 55
    assert report.loc['Holdout', 'Sessions'] == 55
    assert 'Benchmark Return' in report


def test_holdout_rejects_invalid_price():
    index = pd.bdate_range('2024-01-01', periods=220)
    close = pd.Series(100., index=index)
    close.iloc[10] = 0
    with pytest.raises(ValueError):
        holdout_backtest(close)
