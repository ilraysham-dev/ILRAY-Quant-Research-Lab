"""Options-chain analytics from explicitly supplied snapshot data.

This module computes a *gross* gamma open-interest proxy. Without dealer
inventory or transaction signs it cannot estimate signed dealer GEX.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED = {'OptionType','Strike','OpenInterest','Gamma','Multiplier'}


def gross_gamma_profile(chain: pd.DataFrame, spot: float) -> pd.DataFrame:
    """By-strike unsigned gamma-dollar proxy for a 1% underlying move.

    Formula: gamma * open interest * contract multiplier * spot**2 * 0.01.
    The result is a sensitivity proxy in dollars; neither direction of dealer
    exposure nor market impact follows from this value alone.
    """
    if not np.isfinite(spot) or spot <= 0:
        raise ValueError('Underlying spot must be a positive number')
    missing = REQUIRED - set(chain.columns)
    if missing:
        raise ValueError(f'Missing options columns: {sorted(missing)}')
    data = chain.copy()
    for col in ['Strike','OpenInterest','Gamma','Multiplier']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    if data[list(REQUIRED-{'OptionType'})].isna().any().any():
        raise ValueError('Options numeric fields contain missing/non-numeric values')
    if (data['Strike']<=0).any() or (data['OpenInterest']<0).any() or (data['Gamma']<0).any() or (data['Multiplier']<=0).any():
        raise ValueError('Invalid strike, open interest, gamma or multiplier')
    types = data['OptionType'].astype(str).str.lower().str.strip()
    if not types.isin(['call','put']).all():
        raise ValueError('OptionType must be call or put')
    data['Gross Gamma Proxy ($ / 1% move)'] = (
        data['Gamma']*data['OpenInterest']*data['Multiplier']*spot**2*.01)
    profile = data.groupby('Strike',sort=True)['Gross Gamma Proxy ($ / 1% move)'].sum().to_frame()
    return profile
