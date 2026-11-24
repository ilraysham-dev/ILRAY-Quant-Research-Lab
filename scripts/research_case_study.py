"""Produce a transparent ETF research memo using actual history or explicit demo.

Usage:
  python scripts/research_case_study.py --demo
  python scripts/research_case_study.py --csv data/adjusted_closes.csv --ticker SPY
  python scripts/research_case_study.py --download --ticker SPY
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantlab.engine import backtest, clean_prices, etf_rankings, make_demo_data, performance, signals
from quantlab.quality import price_quality_report
from quantlab.market_data import download_prices


def build_report(prices: pd.DataFrame, source: str, ticker: str, fast: int = 20,
                 slow: int = 80, fee_bps: float = 5.) -> str:
    if ticker not in prices.columns:
        raise ValueError(f"Ticker {ticker!r} unavailable. Choose from {list(prices)}")
    series = prices[ticker].dropna()
    if len(series) < 250:
        raise ValueError("At least 250 price observations are required for this case study")
    allocation = signals(series, fast=fast, slow=slow)
    results = backtest(series, allocation, fee_bps=fee_bps)
    # We define a historical holdout after the model parameters are fixed. The
    # signal uses only trailing prices; shifting exposure one day prevents same-
    # day execution. This is not a formal walk-forward optimization exercise.
    cutoff = int(len(results) * .75)
    held = results.iloc[cutoff:]
    strategy_equity = (1 + held["Strategy Return"]).cumprod()
    benchmark_equity = (1 + held["Market Return"]).cumprod()
    strategy = performance(held["Strategy Return"], strategy_equity)
    benchmark = performance(held["Market Return"], benchmark_equity)
    quality = price_quality_report(prices, lookback=63)
    ranks = etf_rankings(prices, lookback=63)

    def pct(value: float) -> str:
        return f"{value:.2%}"

    lines = [
        "# ETF Trend and Risk — Reproducible Research Memo",
        "",
        f"**Dataset:** {source}",
        f"**Observations:** {len(series):,} for {ticker}; {series.index.min().date()} through {series.index.max().date()}",
        f"**Research scope:** Historical, long-only signal for {ticker}, compared with buy-and-hold.",
        "",
        "## Hypothesis",
        "A simple moving-average trend filter may change the return/drawdown profile versus",
        "remaining continuously invested. We test this hypothesis; we do not assume it is true.",
        "",
        "## Methods",
        f"- Signal: long 100% if {fast}-session moving average exceeds {slow}-session moving average; otherwise cash.",
        "- Signal is calculated after each close; the position is applied to the **next** session's return.",
        f"- Turnover cost: {fee_bps:.1f} basis points per absolute change in position.",
        "- Evaluation: final 25% of observations, with fixed strategy parameters.",
        "- Benchmark: buy-and-hold of the same asset.",
        "- Annualization: 252 trading sessions; zero risk-free rate for the illustrative Sharpe ratio.",
        "",
        "## Holdout results (historical or simulated, depending on dataset)",
        "",
        "| Metric | Trend strategy | Buy and hold |",
        "|---|---:|---:|",
        f"| Cumulative return | {pct(strategy['Total Return'])} | {pct(benchmark['Total Return'])} |",
        f"| Annualized volatility | {pct(strategy['Annualized Vol'])} | {pct(benchmark['Annualized Vol'])} |",
        f"| Sharpe (rf=0) | {strategy['Sharpe (rf=0)']:.2f} | {benchmark['Sharpe (rf=0)']:.2f} |",
        f"| Maximum drawdown | {pct(strategy['Max Drawdown'])} | {pct(benchmark['Max Drawdown'])} |",
        "",
        "## Data-quality summary",
        f"- Symbols eligible for 63-session rankings: {int(quality.Status.eq('ELIGIBLE').sum())} of {len(quality)}.",
        f"- Ticker ranking: {int(ranks.index.get_loc(ticker))+1 if ticker in ranks.index else 'not eligible'} out of {len(ranks)} eligible tickers.",
        "- Missing prices are never forward-filled or interpreted as 0% returns in the ETF ranking.",
        "",
        "## Limitations",
        "- Results are *not* an investor recommendation or live-trading signal.",
        "- Source data may be delayed, revised, unadjusted, or subject to survivorship/corporate-action issues.",
        "- Only a one-way turnover fee is modeled; spread, additional slippage, taxes and market impact are excluded.",
        "- The 75/25 split is descriptive; multiple comparisons or later model tuning could overfit the holdout.",
        "- Macro QUAD and original class workbook calculations are separate, not yet verified for exact parity.",
        "- No claim is made about future returns, statistical significance or investment suitability.",
        "",
        "## Next research steps",
        "1. Validate adjusted price histories and timing using authoritative sources.",
        "2. Replicate the original Excel QUAD formulas against known cell outputs.",
        "3. Use vintage macro release data and lag publications to prevent lookahead bias.",
        "4. Test regime-dependent ETF rankings and rolling walk-forward periods.",
        "5. Add realistic costs, risk limits, paper trading and ongoing monitoring.",
        "",
    ]
    if source.startswith("SYNTHETIC"):
        lines.insert(2, "**WARNING: THIS IS A SYNTHETIC DEMO — NOT MARKET EVIDENCE.**")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, help="CSV columns Date,SPY,QQQ,... with actual price history")
    parser.add_argument("--download", action="store_true", help="Download historical Yahoo adjusted closes")
    parser.add_argument("--demo", action="store_true", help="Use synthetic test data explicitly")
    parser.add_argument("--ticker", default="SPY")
    parser.add_argument("--out", type=Path, default=Path("outputs/research_memo.md"))
    args = parser.parse_args()
    if int(bool(args.csv))+int(args.download)+int(args.demo) != 1:
        parser.error("Choose exactly one of --csv, --download or --demo")
    if args.csv:
        prices = clean_prices(pd.read_csv(args.csv))
        source = f"USER-SUPPLIED CSV: {args.csv.name}; independently validate provenance"
    elif args.download:
        prices = download_prices([args.ticker],"5y")
        source = "YAHOO HISTORICAL ADJUSTED CLOSE; downloaded on demand, independently validate provider"
    else:
        prices, _ = make_demo_data()
        source = "SYNTHETIC DEMONSTRATION (fixed random seed)"
    report = build_report(prices, source, args.ticker)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Created {args.out} ({len(report):,} characters)")
