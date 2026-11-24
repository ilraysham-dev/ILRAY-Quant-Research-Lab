import pandas as pd
import pytest
from quantlab.options import gross_gamma_profile


def test_gross_gamma_proxy_is_unsigned_and_grouped():
    data = pd.DataFrame({'OptionType':['call','put'], 'Strike':[100,100],
                         'OpenInterest':[10,20], 'Gamma':[.02,.02], 'Multiplier':[100,100]})
    profile = gross_gamma_profile(data, 100)
    assert profile.iloc[0,0] == pytest.approx(.02*30*100*100**2*.01)


def test_rejects_missing_chain_fields():
    with pytest.raises(ValueError,match='Missing options'):
        gross_gamma_profile(pd.DataFrame({'Strike':[100]}),100)
