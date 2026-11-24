import pandas as pd
from quantlab.macro_data import download_us_macro


class FakeResponse:
    def __init__(self, payload):
        self.content = payload.encode()

    def raise_for_status(self):
        pass


class FakeSession:
    def get(self, url, params, timeout):
        name = params['id']
        freq = 'QS' if name == 'GDPC1' else 'MS'
        length = 12 if name == 'GDPC1' else 36
        dates = pd.date_range('2020-01-01', periods=length, freq=freq)
        payload = 'DATE,' + name + '\n' + ''.join(
            f'{d.date()},{100+i}\n' for i,d in enumerate(dates)
        )
        return FakeResponse(payload)


def test_fred_quarterly_yoy_transform():
    macro = download_us_macro(FakeSession())
    assert {'Date', 'GDP', 'Inflation'} <= set(macro.columns)
    assert len(macro) == 8
    assert macro['GDP'].notna().all()
    assert macro['Inflation'].notna().all()
    assert macro['GDP'].iloc[0] > 0
