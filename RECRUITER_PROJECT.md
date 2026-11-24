# ILRAY Quant Research Lab — Recruiter Overview

**Version 5 disclosure:** Historical Yahoo ETF adjusted closes are the dashboard default, while FRED provides revised historical macroeconomic inputs. The included sample research memo remains synthetic. Real historical macro observations are NOT aligned to original release dates and should not be backtested as contemporaneous trade signals. The GEX and Excel/VBA parity migration remain incomplete.

**Version 6:** A chronological holdout evaluation screen now separates older research data from later test data and reports both against buy-and-hold. This is a transparent educational evaluation of a *prespecified* moving-average rule—not a verified strategy edge, exhaustive walk-forward study, or institution-grade execution system.

**Category:** Financial data analysis / investment research / portfolio analytics

**Technology:** Python, Pandas, NumPy, Plotly, Streamlit, Excel import, statistical testing, Git-ready project structure.

## Problem

Financial research spread across disconnected Excel files is difficult to reproduce, validate, and update. A missing-price formula in the educational ETF workbook had masked some missing observations as zero returns, demonstrating the importance of data-quality checks.

## Working solution

- A local web dashboard with views for ETF comparisons, macro regime experiments, portfolio allocations and risk, trend strategy backtesting, and return-resampling Monte Carlo scenarios.
- An optional historical price download interface and an explicit demonstration-data mode.
- Data-quality rules to flag stale, missing and nonpositive prices before ETF selection.
- Next-session strategy execution (preventing a common same-bar lookahead error) with configurable turnover fees.
- Historical VaR, expected shortfall, portfolio risk contributions and exportable reports.
- A reproducible CLI research memo and unit tests for major calculations.

## What is not claimed

- Not a verified profitable trading strategy, hedge fund, automated broker, or live signal service.
- Not an exact migration of every classroom Excel worksheet or VBA macro.
- No claims of independently sourcing proprietary school materials, creating all code without assistance, or having run live trading capital.
- Synthetic examples in `outputs/research_memo.md` are intentionally marked as synthetic.

## Interview demonstration (4 minutes)

1. Show the Data Quality page and explain the old ETF price-gap failure.
2. Display ETF rankings from a clearly labeled and vetted historical data source.
3. Explain why the backtest shifts signals by one session and how fees are charged.
4. Show the risk cockpit, an equity curve, and the research memo's limitations.

## Suggested truthful interview explanation

"I built this as a learning and portfolio project with AI-assisted development. I focused on understanding the financial models, testing data quality, and translating Excel-based research workflows into Python. One concrete problem I investigated was an Excel formula that treated missing prices as zero returns. I introduced explicit data-quality checks and documented which advanced models still require validation."

You should personally run, study, and explain the code before using this description.
