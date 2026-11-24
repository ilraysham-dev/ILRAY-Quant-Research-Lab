import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from quantlab.regimes import market_regimes
from quantlab.advanced_validation import validated_ma_backtest, _returns

class NewQuantModulesTest(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(12)
        self.prices=pd.Series(100*np.exp(np.cumsum(rng.normal(.0003,.012,600))),
                              index=pd.bdate_range('2023-01-02',periods=600),name='TEST')

    def test_regime_has_history_and_no_early_classification(self):
        output=market_regimes(self.prices)
        self.assertEqual(output.iloc[0]['Regime'],'Insufficient data')
        self.assertNotEqual(output.iloc[-1]['Regime'],'Insufficient data')

    def test_regime_no_future_data_leak(self):
        a=market_regimes(self.prices.iloc[:450])
        b=market_regimes(self.prices)
        pd.testing.assert_frame_equal(a,b.iloc[:450],check_freq=False)

    def test_trades_hold_next_session(self):
        frame=_returns(self.prices,10,50,5)
        pd.testing.assert_series_equal(frame['Position (next session)'].iloc[1:].reset_index(drop=True),
            frame['Signal (close)'].iloc[:-1].reset_index(drop=True), check_names=False)

    def test_costs_reduce_returns_by_turnover(self):
        a=_returns(self.prices,10,50,0)
        b=_returns(self.prices,10,50,15)
        np.testing.assert_allclose((a['Strategy Return']-b['Strategy Return']).to_numpy(),
                                   (b['Turnover']*15/10000).to_numpy())

    def test_training_selection_unchanged_by_future_prices(self):
        a,sa,ca=validated_ma_backtest(self.prices)
        changed=self.prices.copy()
        changed.iloc[420:] *= np.linspace(1,2,180)
        b,sb,cb=validated_ma_backtest(changed)
        self.assertEqual((ca.iloc[0]['Fast'],ca.iloc[0]['Slow']),
                         (cb.iloc[0]['Fast'],cb.iloc[0]['Slow']))
        self.assertEqual(len(sa),4)

    def test_no_invalid_windows(self):
        with self.assertRaises(ValueError): market_regimes(self.prices,200,50)
        with self.assertRaises(ValueError): validated_ma_backtest(self.prices.iloc[:100])

if __name__ == '__main__':unittest.main()
