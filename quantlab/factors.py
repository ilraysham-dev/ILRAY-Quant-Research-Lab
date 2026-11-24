"""Transparent, historical cross-sectional factors; research only.

Price momentum is backward-looking and excludes the latest skip_sessions close-to-close
returns. Fundamental features require an explicit, real uploaded snapshot. The caller
must independently verify the snapshot's as-of date and point-in-time availability.
"""
import numpy as np
import pandas as pd

FUNDAMENTAL_FIELDS = ['Ticker', 'PE', 'PB', 'ROE', 'DebtToEquity']


def momentum_factors(prices: pd.DataFrame, lookback: int = 252, skip_sessions: int = 21) -> pd.DataFrame:
    """Cross-sectional price momentum P[t-skip]/P[t-lookback]-1.

    Calculations use a common last timestamp with non-missing end points; no backfills.
    Momentum is NOT the return of a tradable, transaction-costed strategy.
    """
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise ValueError('Historical price DataFrame must not be empty.')
    if not (isinstance(lookback, int) and isinstance(skip_sessions, int) and
            lookback > skip_sessions >= 0):
        raise ValueError('Lookback must be greater than the nonnegative skip period.')
    if len(prices) <= lookback:
        raise ValueError(f'Need at least {lookback + 1} trading rows for the chosen momentum lookback.')
    p = prices.apply(pd.to_numeric, errors='coerce')
    if p.columns.duplicated().any():
        raise ValueError('Price ticker columns must be unique.')
    if not p.index.is_monotonic_increasing or p.index.has_duplicates:
        raise ValueError('Price dates must be strictly increasing and unique.')
    early = p.iloc[-(lookback + 1)]
    late = p.iloc[-(skip_sessions + 1)]
    # Explicitly reject zero/negative quotes and missing endpoints.
    valid = early.notna() & late.notna() & (early > 0) & (late > 0)
    scores = (late / early - 1).where(valid)
    result = pd.DataFrame({'Momentum Return': scores}).rename_axis('Ticker')
    result.index = result.index.map(str)
    result['Momentum Score'] = result['Momentum Return'].rank(pct=True, ascending=True)
    return result.sort_values('Momentum Score', ascending=False, na_position='last')


def parse_fundamentals(raw: pd.DataFrame) -> pd.DataFrame:
    """Validate a genuine snapshot; ROE as decimal (.15 = 15%), D/E as ratio."""
    if not isinstance(raw, pd.DataFrame) or not set(FUNDAMENTAL_FIELDS).issubset(raw.columns):
        raise ValueError('CSV needs columns: ' + ', '.join(FUNDAMENTAL_FIELDS))
    data = raw[FUNDAMENTAL_FIELDS].copy()
    data['Ticker'] = data['Ticker'].astype(str).str.strip().str.upper()
    if data['Ticker'].eq('').any() or data['Ticker'].duplicated().any():
        raise ValueError('Each fundamental snapshot ticker must be present and unique.')
    for col in FUNDAMENTAL_FIELDS[1:]:
        data[col] = pd.to_numeric(data[col], errors='coerce')
        data[col] = data[col].replace([np.inf, -np.inf], np.nan)
    # PE/PB <= 0 are not comparable conventional cheapness measures.
    data['PE'] = data['PE'].where(data['PE'] > 0)
    data['PB'] = data['PB'].where(data['PB'] > 0)
    data['DebtToEquity'] = data['DebtToEquity'].where(data['DebtToEquity'] >= 0)
    # Missing input stays missing and cannot become a manufactured zero rank.
    return data.set_index('Ticker')


def score_factors(momentum: pd.DataFrame, fundamentals: pd.DataFrame | None = None,
                  factors: tuple[str, ...] = ('Momentum',)) -> pd.DataFrame:
    """Within-universe percentile ranks; equal-weight selected factors on complete cases.

    Value = mean(reverse PE, reverse PB); Quality = mean(ROE, reverse D/E).
    Requires all relevant raw inputs per factor. No imputation or ETF lookthrough.
    """
    allowed = {'Momentum', 'Value', 'Quality'}
    if not factors or any(f not in allowed for f in factors):
        raise ValueError('Choose one or more of Momentum, Value, Quality.')
    out = momentum.copy()
    if 'Momentum Score' not in out:
        raise ValueError('Momentum Score is missing.')
    if fundamentals is not None:
        out = out.join(fundamentals, how='left')
        if {'PE','PB','ROE','DebtToEquity'}.issubset(out.columns):
            pe_rank = out['PE'].rank(pct=True, ascending=False)
            pb_rank = out['PB'].rank(pct=True, ascending=False)
            roe_rank = out['ROE'].rank(pct=True, ascending=True)
            debt_rank = out['DebtToEquity'].rank(pct=True, ascending=False)
            out['Value Score'] = (pe_rank + pb_rank) / 2
            out.loc[out[['PE','PB']].isna().any(axis=1), 'Value Score'] = np.nan
            out['Quality Score'] = (roe_rank + debt_rank) / 2
            out.loc[out[['ROE','DebtToEquity']].isna().any(axis=1), 'Quality Score'] = np.nan
    selected = [name + ' Score' for name in factors]
    if not set(selected).issubset(out.columns):
        raise ValueError('Value and Quality require an uploaded fundamental CSV; historical prices alone are insufficient.')
    out['Composite Score'] = out[selected].mean(axis=1, skipna=False)
    out['Factor Rank'] = out['Composite Score'].rank(ascending=False, method='min').astype('Int64')
    return out.sort_values('Composite Score', ascending=False, na_position='last')
