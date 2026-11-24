"""Research-only deterministic portfolio diagnostics; no live trading or price downloads."""
from __future__ import annotations
import html
import math
import numpy as np
import pandas as pd

SESSIONS=252

def clean_return_panel(prices: pd.DataFrame, symbols=None, min_rows=30):
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise ValueError('Provide a nonempty historical price table.')
    subset=prices[list(symbols)] if symbols is not None else prices
    p=subset.apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan)
    p=p.where(p>0)
    returns=p.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan).dropna(how='any')
    if len(returns)<min_rows: raise ValueError(f'At least {min_rows} complete shared return observations are required; found {len(returns)}.')
    return returns

def normalized_weights(weights:dict|pd.Series,columns):
    w=pd.Series(weights,dtype=float).reindex(columns)
    if w.isna().any() or not np.isfinite(w.to_numpy()).all() or (w<0).any() or w.sum()<=0:
        raise ValueError('Weights must be finite, nonnegative and add to a positive number.')
    return w/w.sum()

def basic_stats(returns:pd.DataFrame, weights:dict|pd.Series):
    w=normalized_weights(weights,returns.columns)
    cov=returns.cov()*SESSIONS
    portfolio=(returns*w).sum(axis=1)
    ann_return=float(portfolio.mean()*SESSIONS)
    ann_vol=float(portfolio.std(ddof=1)*math.sqrt(SESSIONS))
    peak=(1+portfolio).cumprod().cummax().clip(lower=1)
    equity=(1+portfolio).cumprod()
    drawdown=equity/peak-1
    marginal=cov@w
    variance=float(w@marginal)
    contributions=(w*marginal)/math.sqrt(variance) if variance>0 else pd.Series(0.,index=w.index)
    asset_summary=pd.DataFrame({'Weight':w,'Annualized Arithmetic Return':returns.mean()*SESSIONS,'Annualized Volatility':returns.std()*math.sqrt(SESSIONS),'Annualized Vol Contribution':contributions})
    return {'weights':w,'correlations':returns.corr(),'asset_summary':asset_summary,'portfolio_returns':portfolio,'drawdown':drawdown,'annualized_return':ann_return,'annualized_volatility':ann_vol,'max_drawdown':float(drawdown.min()),'effective_holdings':float(1/(w.pow(2).sum())),'largest_weight':float(w.max())}

def stress_windows(returns:pd.DataFrame,weights:dict|pd.Series,rolling_days:int=21,stresses:dict|None=None):
    w=normalized_weights(weights,returns.columns)
    daily=(returns*w).sum(axis=1)
    roll=(1+daily).rolling(rolling_days).apply(np.prod,raw=True)-1
    # Scenario shocks are illustrative parallel price shocks, not historical event attributions.
    shocks=stresses or {'Parallel −5%':-0.05,'Parallel −10%':-0.10,'Parallel −20%':-0.20,'Parallel +10%':0.10}
    scenarios=pd.DataFrame([{'Scenario':name,'Assumed change in each asset':shock,'Estimated portfolio change':float((w*shock).sum())} for name,shock in shocks.items()])
    worst=roll.dropna().nsmallest(min(10,len(roll.dropna())))
    return scenarios,roll,worst

def random_portfolio_cloud(returns:pd.DataFrame, count=1000, seed=1729):
    """Exploratory fully invested long-only allocation cloud, not an efficient frontier."""
    if count<1 or count>10000: raise ValueError('Count must be between 1 and 10,000.')
    if returns.shape[1]>40: raise ValueError('Limit the allocation experiment to 40 assets.')
    rng=np.random.default_rng(seed)
    w=rng.dirichlet(np.ones(returns.shape[1]),size=count)
    mu=returns.mean().to_numpy()*SESSIONS
    cov=returns.cov().to_numpy()*SESSIONS
    r=w@mu
    v=np.sqrt(np.maximum(np.einsum('ij,jk,ik->i',w,cov,w),0))
    out=pd.DataFrame({'Annualized Return':r,'Annualized Volatility':v})
    out['Return/Volatility (rf=0)']=np.divide(r,v,out=np.full_like(r,np.nan),where=v>0)
    out['Allocation']=list(w)
    return out

def walk_forward_ma(close:pd.Series,train_days=252,test_days=63,fast_candidates=(10,20,30),slow_candidates=(50,100,150),one_way_bps=5.0):
    """Repeated fit-on-past, evaluate-on-next-block MA with positions lagged one session."""
    s=pd.to_numeric(close,errors='coerce').replace([np.inf,-np.inf],np.nan)
    s=s.where(s>0).dropna()
    if not s.index.is_monotonic_increasing or s.index.has_duplicates:raise ValueError('Price index must be sorted and unique.')
    if train_days<=max(slow_candidates) or test_days<5:raise ValueError('Training days must exceed slow MA and test days must be >= 5.')
    if len(s)<train_days+test_days:raise ValueError(f'Need at least {train_days+test_days} prices for one walk-forward window.')
    if not np.isfinite(one_way_bps) or one_way_bps<0:raise ValueError('Trading cost must be nonnegative.')
    daily=s.pct_change(fill_method=None).fillna(0.)
    candidates=[(f,l) for f in fast_candidates for l in slow_candidates if 0<f<l]
    def portfolio_returns(f,l):
        raw=(s.rolling(f,min_periods=f).mean()>s.rolling(l,min_periods=l).mean()).astype(float)
        # Today's indicator applies next trading session; cost at that next-session transition.
        pos=raw.shift(1).fillna(0.)
        turnovers=pos.diff().abs().fillna(pos.abs())
        return pos*daily-turnovers*(one_way_bps/10000)
    strategy={pair:portfolio_returns(*pair) for pair in candidates}
    folds=[]; segments=[]; start=train_days
    while start+test_days<=len(s):
        train_slice=slice(start-train_days,start)
        best=None; best_score=-float('inf')
        for pair,ret in strategy.items():
            r=ret.iloc[train_slice]
            sd=float(r.std(ddof=1))
            sharpe=float(r.mean()/sd*math.sqrt(SESSIONS)) if sd>1e-12 else (-float('inf') if r.mean()<=0 else float('inf'))
            if sharpe>best_score:best_score=sharpe;best=pair
        if best is None: raise ValueError('No valid strategy pair for training window.')
        test=strategy[best].iloc[start:start+test_days]
        benchmark=daily.iloc[start:start+test_days]
        frame=pd.DataFrame({'Strategy Return':test,'Buy Hold Return':benchmark,'Fold':len(folds)+1})
        segments.append(frame)
        folds.append({'Fold':len(folds)+1,'Training end':str(s.index[start-1]),'Test start':str(s.index[start]),'Test end':str(s.index[start+test_days-1]),'Fast':best[0],'Slow':best[1],'Test Strategy Return':float((1+test).prod()-1),'Test Benchmark Return':float((1+benchmark).prod()-1)})
        start+=test_days
    stitched=pd.concat(segments)
    stitched['Strategy Equity']=(1+stitched['Strategy Return']).cumprod()
    stitched['Buy Hold Equity']=(1+stitched['Buy Hold Return']).cumprod()
    return stitched,pd.DataFrame(folds)

def html_report(prices:pd.DataFrame,stats:dict,scenarios:pd.DataFrame,source:str,method_note:str=''):
    """Self-contained report with sanitized text; no external resources."""
    def esc(s):return html.escape(str(s),quote=True)
    def table(df):return df.to_html(classes='data',border=0,escape=True,float_format=lambda v:f'{v:,.4f}')
    metrics=[('Price start',str(prices.index.min())),('Price end',str(prices.index.max())),('Source',source),('Annualized arithmetic return',f"{stats['annualized_return']:.2%}"),('Annualized volatility',f"{stats['annualized_volatility']:.2%}"),('Maximum drawdown',f"{stats['max_drawdown']:.2%}"),('Effective number of holdings',f"{stats['effective_holdings']:.2f}")]
    rows=''.join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in metrics)
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>ILRAY Research Report</title>'
            '<style>body{font-family:Arial,sans-serif;max-width:980px;margin:40px auto;color:#17202e}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}h1{color:#17365a}small{color:#666}</style>'
            '<h1>ILRAY Quant Lab | Research Summary</h1><p><strong>Research only — not investment advice or live trading.</strong></p>'
            f'<table>{rows}</table><h2>Asset exposures</h2>{table(stats["asset_summary"])}'
            f'<h2>Correlation</h2>{table(stats["correlations"])}<h2>Illustrative parallel-shock scenarios</h2>{table(scenarios)}'
            f'<p><small>{esc(method_note)} Assumes a daily rebalanced constant-weight return series for research diagnostics; no commissions, borrowing, taxes, or price impact. Scenario shocks are hypothetical, not forecasts. Historical data may include survivorship bias.</small></p></html>')
