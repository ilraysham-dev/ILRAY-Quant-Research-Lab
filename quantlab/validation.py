"""Transparent holdout evaluation of a prespecified moving-average rule.

This is *not* walk-forward parameter optimization or evidence of predictive edge.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import backtest, performance, signals


def holdout_backtest(close: pd.Series, fast: int = 20, slow: int = 80,
                     split: float = .75, fee_bps: float = 5.) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute a frozen strategy once, evaluate last (1-split) share separately.

    A predeclared fast/slow rule is assumed. Applying the same rule to the full
    history only warms up moving averages; signals use past and current prices,
    positions are lagged by one session. Never tune on the holdout results.
    """
    close = pd.to_numeric(close, errors="coerce").dropna().sort_index()
    if not close.index.is_unique:
        raise ValueError("Duplicate trading sessions")
    if (close <= 0).any():
        raise ValueError("Prices must be positive")
    if not 0.5 <= split <= 0.9:
        raise ValueError("Training fraction must be 50–90%")
    if len(close) < max(120, slow * 2):
        raise ValueError("Need at least 120 sessions and twice the slow average")
    cut = int(len(close) * split)
    if cut <= slow or len(close) - cut < 20:
        raise ValueError("Insufficient training or test history")
    full = backtest(close, signals(close, fast, slow), fee_bps)
    full["Sample"] = "Training"
    full.iloc[cut:, full.columns.get_loc("Sample")] = "Holdout"
    stats = []
    for segment, frame in full.groupby("Sample", sort=False):
        result = performance(frame["Strategy Return"], (1 + frame["Strategy Return"]).cumprod())
        benchmark = performance(frame["Market Return"], (1 + frame["Market Return"]).cumprod())
        stats.append({"Sample": segment, "Start": frame.index[0].date(),
                      "End": frame.index[-1].date(), "Sessions": len(frame),
                      "Strategy Return": result["Total Return"],
                      "Benchmark Return": benchmark["Total Return"],
                      "Strategy Sharpe (rf=0)": result["Sharpe (rf=0)"],
                      "Strategy Max Drawdown": result["Max Drawdown"],
                      "Fee (bps/change)": float(fee_bps)})
    return full, pd.DataFrame(stats).set_index("Sample")
