"""Train-only strategy selection followed by untouched chronological holdout."""
from __future__ import annotations
import numpy as np
import pandas as pd


def _returns(prices: pd.Series, fast: int, slow: int, one_way_bps: float) -> pd.DataFrame:
    p = pd.to_numeric(prices, errors="coerce").astype(float).sort_index()
    if p.isna().any() or not np.isfinite(p).all() or (p <= 0).any():
        raise ValueError("Prices must be positive, complete, and finite; clean the source data first.")
    if not p.index.is_unique:
        raise ValueError("Price dates must be unique.")
    # This signal is known after today's close. Holding starts at the NEXT close-to-close period.
    fast_ma = p.rolling(fast, min_periods=fast).mean()
    slow_ma = p.rolling(slow, min_periods=slow).mean()
    signal = (fast_ma > slow_ma).astype(float).where(slow_ma.notna(), 0.0)
    held = signal.shift(1).fillna(0.0)
    turnover = held.diff().abs().fillna(held.abs())
    market = p.pct_change(fill_method=None).fillna(0.0)
    net = held * market - turnover * (one_way_bps / 10_000.0)
    return pd.DataFrame({"Price":p, "Market Return":market, "Signal (close)":signal,
                         "Position (next session)":held, "Turnover":turnover,
                         "Trading Cost":turnover * (one_way_bps / 10_000.0),
                         "Strategy Return":net, "Buy Hold Return":market}, index=p.index)


def _stats(r: pd.Series) -> dict:
    r = r.astype(float)
    growth = (1+r).cumprod()
    std = r.std(ddof=1)
    return {"Total Return":float(growth.iloc[-1]-1),
            "Annualized Vol":float(std*np.sqrt(252)) if pd.notna(std) else np.nan,
            "Sharpe (rf=0)":float(r.mean()/std*np.sqrt(252)) if pd.notna(std) and std > 1e-12 else np.nan,
            "Max Drawdown":float((growth/growth.cummax()-1).min())}


def validated_ma_backtest(prices: pd.Series, fast_grid: list[int] | tuple[int,...] = (10, 20, 30),
                          slow_grid: list[int] | tuple[int,...] = (50, 100, 150),
                          train_fraction: float = .7, one_way_bps: float = 5.0,
                          min_train: int = 160, min_test: int = 40):
    """Optimize MA combination on train only; evaluate it exactly once on later test.

    Returns (timeline, summary, candidate_scores). Candidate sorting and tuning
    never inspect test returns. Holdout carries historical MA observations into test.
    Buy & hold is an informational benchmark, not charged entry/exit costs.
    """
    p = pd.to_numeric(prices, errors="coerce").sort_index()
    n = len(p)
    if n < min_train + min_test or not 0.5 <= train_fraction <= 0.9:
        raise ValueError("Need enough observations and a training fraction of 0.5–0.9.")
    if one_way_bps < 0 or not np.isfinite(one_way_bps):
        raise ValueError("Trading costs must be finite and nonnegative.")
    boundary = int(n * train_fraction)
    if boundary < min_train or n-boundary < min_test:
        raise ValueError("Training or test window too short. Choose longer data history.")
    candidates = []
    for fast in sorted(set(int(x) for x in fast_grid)):
        for slow in sorted(set(int(x) for x in slow_grid)):
            if not 2 <= fast < slow or slow >= boundary:
                continue
            path = _returns(p, fast, slow, one_way_bps)
            train = path.iloc[:boundary]["Strategy Return"]
            s = _stats(train)
            candidates.append({"Fast":fast,"Slow":slow,"Train Sharpe":s["Sharpe (rf=0)"],
                               "Train Return":s["Total Return"], "Train Drawdown":s["Max Drawdown"]})
    if not candidates:
        raise ValueError("No valid fast/slow combination for this training window.")
    ranking = pd.DataFrame(candidates)
    # Stable deterministic tie breaking; invalid Sharpe ranks below finite values.
    ranking["Score"] = ranking["Train Sharpe"].replace([np.inf,-np.inf],np.nan).fillna(-1e9)
    ranking = ranking.sort_values(["Score","Fast","Slow"], ascending=[False,True,True]).reset_index(drop=True)
    best = ranking.iloc[0]
    full = _returns(p, int(best["Fast"]), int(best["Slow"]), one_way_bps)
    full["Split"] = np.where(np.arange(len(full)) < boundary,"Train","Holdout")
    full["Strategy Equity"] = (1+full["Strategy Return"]).cumprod()
    full["Buy Hold Equity"] = (1+full["Buy Hold Return"]).cumprod()
    rows=[]
    for period, segment in (("Training",full.iloc[:boundary]),("Holdout (untouched)",full.iloc[boundary:])):
        for label, key in (("Strategy","Strategy Return"),("Buy & Hold","Buy Hold Return")):
            rows.append({"Period":period,"Portfolio":label,"Fast MA":int(best["Fast"]),"Slow MA":int(best["Slow"]),
                         "Observations":len(segment),**_stats(segment[key])})
    return full, pd.DataFrame(rows), ranking.drop(columns=["Score"])
