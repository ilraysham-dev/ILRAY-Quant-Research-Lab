import numpy as np
import pandas as pd
from quantlab.bottom_up import asset_regimes


def test_asset_regimes_does_not_fill_missing_prices():
    idx = pd.bdate_range('2025-01-01', periods=100)
    df = pd.DataFrame({'UP':np.linspace(100,120,100),'GAP':np.linspace(100,120,100)},index=idx)
    df.loc[idx[-3],'GAP'] = np.nan
    result = asset_regimes(df, 20, 20, .3)
    assert result.loc['UP','Regime'].startswith('Rising')
    assert result.loc['GAP','Regime'] == 'Insufficient data'
