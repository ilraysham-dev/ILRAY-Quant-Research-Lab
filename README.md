> **Fixed publication copy.** This edition omits Windows virtual environments, older application backups, cached source datasets and generated reports. Your original project was left unchanged. Python syntax and automated tests were checked in the audit environment, but full Windows operation, Streamlit browser interactions and live external data were not independently verified. Do not treat historical backtests as evidence of future performance.

# ILRAY Quant Research Lab

**Research-only edition.** A local Python/Streamlit application for exploring historical ETFs and economic data. It has no brokerage integration or order execution. Screens using proprietary options data and faithful Excel formula replication require additional sources and verification; the app does not fabricate missing results.

## Quick start

On a Mac terminal, inside the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, double-click `setup_windows.bat` (installs dependencies and runs automated tests), then double-click **`run_windows.bat`** for a private, this-PC-only dashboard. Use **`run_windows_LAN.bat` only on a trusted private home network** if you want to view the Windows-hosted app from your Mac. There is no login/authentication; never port-forward port 8501 or expose this app to the public internet.

## Where the research features stand

| Screen | Research use | Important limitation |
|---|---|---|
| Mission Control, Data Quality | Historical ETF price overview and missing/stale checks | Provider may be delayed; downloads need internet |
| ETF Selector | Trailing return, volatility, drawdown and relative scoring | Descriptive rank, not an investment recommendation |
| Asset Regimes | Simplified per-ETF trend and realized-volatility states | Not an exact port of the class 40-ETF formulas |
| Macro QUAD | FRED GDP and CPI historical direction | Revised economic values are not original publication vintages |
| Portfolio Risk | Hypothetical buy-and-hold allocations, VaR and CVaR | No intraperiod rebalancing, taxes or real execution |
| Tactical Backtest, Research Validation | Fixed moving average rule and chronological holdout | Example rule, not a validated alpha-generating strategy |
| Monte Carlo | Bootstrap scenarios using loaded daily returns | Simulated future paths, not forecasts |
| Options Gamma | Real uploaded option snapshot gross gamma/OI proxy | Cannot infer *signed dealer gamma exposure* from OI alone |
| GEX & Workbook Bridge | Legacy workbook mapping and import instructions | Source Excel macro/model parity is unfinished |

## Repeatable research and data updates

### Automatic macro updates on Windows

1. Run `setup_windows.bat` once, then double-click `refresh_macro_windows.bat` to confirm that FRED data download works.
2. In **Task Scheduler**, select **Create Basic Task**, name it `ILRAY Macro Refresh`, choose **Daily**, and select **Start a program**.
3. Browse to the full path of `refresh_macro_windows.bat` in this unzipped project folder, then finish. Choose a daily time when the PC will be awake with internet access.
4. Open **Macro QUAD** in the dashboard to see the timestamp of the latest saved snapshot and warnings when it is older than 48 hours. Refresh the browser to see newly saved output.

The job updates `local_data/macro_latest.csv` and `local_data/macro_latest.json`. If a retrieval fails, the last successful snapshot remains available, but it may become stale. GDP, CPI, employment, and market rates have different release schedules; daily checks do **not** mean every series changes daily. Currently the calculated QUAD uses `GDPC1` and `CPIAUCSL`; the broader economic indicators discussed for future development are **not** yet included in its model. The latest revised vintage is *not* suitable for historical point-in-time strategy backtests.

**Important:** This is scheduled polling, not a direct live-feed notification service. Windows Task Scheduler must run on your Windows PC for unattended refreshes. There is no automatic order execution.

To download fresh historical adjusted closes with a quality report, run:

```bash
python scripts/refresh_market_snapshot.py --period 5y --out-dir local_data
```

On Windows you can run `refresh_windows.bat`. The script writes timestamped CSVs and JSON metadata. You may schedule the batch with Windows Task Scheduler after verifying it works manually. It does not run continuously on its own, send trades, or monitor brokerage positions. Keep its `local_data/` folder private and out of GitHub until licensing/redistribution terms are checked.

To create a *historical* research memo after downloading the data:

```bash
python scripts/research_case_study.py --download --ticker SPY --out outputs/sp500_historical_memo.md
```

To test the report format on explicitly simulated data, use `--demo`; the report prominently labels the simulation. Actual downloaded results still require independent source verification before publication.

To run tests after setup:

```bash
python -m pytest -q
```

A standalone **Python + Streamlit** research dashboard built as the foundation for migrating Excel trading and investing workbooks into an auditable software project. Historical ETF prices are the default and historical GDP/CPI are available on the macro page.

## Historical-first data, with explicit limits

The dashboard **automatically fetches adjusted historical ETF closes via Yahoo Finance** (`yfinance`) and caches them for up to an hour. If the connection fails, the dashboard **stops with an error**; it does not silently substitute synthetic prices. You can refresh, upload vetted historical CSV/Excel prices, or explicitly choose **Synthetic demo (testing only)**.

The **Macro QUAD** page retrieves FRED `GDPC1` real GDP and `CPIAUCSL` CPI and converts both to quarterly year-over-year percentage changes (quarterly CPI averages). These **latest revised observations are labeled by economic quarter, not original public release dates**. They can describe past regimes, but cannot support a point-in-time historical trading claim. FRED may be unreachable on restricted networks; the app then permits manual historical CSV upload. Source: https://fred.stlouisfed.org/ .

**Remaining boundaries:** GEX still requires verified options data and dealer-position assumptions; the full Excel/VBA logic is not replicated; the tactical rule is a reference strategy. Monte Carlo is intentionally simulated future returns drawn from loaded historical returns. The sample `outputs/research_memo.md` and default CLI study still use explicitly labeled synthetic data. Do not represent those as real performance.

## Version 6 research-validation workflow

The **Research Validation** page adds a chronological training/holdout comparison against buy-and-hold. Enter a predeclared fast/slow moving-average rule and transaction cost, then inspect training and later holdout performance. It reports results separately, and exports reproducible CSVs. Do not select hyperparameters based on holdout results: doing so destroys the independent evaluation. Historical adjusted closes are not point-in-time security-selection data; a fixed current ETF universe still introduces selection bias. This feature does **not** validate profitability or migrate your original Excel tactical logic.

## Portfolio / resume project

Read **`RECRUITER_PROJECT.md`** for the project narrative, a four-minute demonstration plan, and an honest interview explanation. Run the reproducible research study:

```bash
python scripts/research_case_study.py --download --ticker SPY
```

The generated `outputs/research_memo.md` depends on the command: `--demo` uses synthetic data; `--download` or `--csv` uses historical data. Inspect the report source label before sharing any results. To produce a historical analysis with your own data:

```bash
python scripts/research_case_study.py --csv data/adjusted_closes.csv --ticker SPY --out outputs/sp500_study.md
```

The example's trend strategy is a transparent reference model, not a validated source of investment advice. Compare against the buy-and-hold benchmark and read the limitations before discussing results with employers.

## Windows PC host + MacBook dashboard viewer

1. Transfer the *whole unzipped project folder* to the Windows PC.
2. Install Python 3.11–3.13 on Windows. In the project folder, double-click **`setup_windows.bat`**; wait for the successful dependency-installation and test messages. The setup chooses an available compatible interpreter rather than requiring Python 3.13.
3. Double-click **`run_windows_LAN.bat`** and leave its terminal open. If Windows Firewall asks, permit access on **Private networks only**, not Public.
4. On the Windows PC, open Command Prompt and type `ipconfig`. Find the **IPv4 Address** of the active Wi-Fi/Ethernet adapter, such as `192.168.1.23` (example only).
5. Connect your MacBook to the **same trusted home Wi-Fi** and open `http://192.168.1.23:8501` in a browser, replacing the example with the Windows address.
6. Use the Windows launcher whenever you want to host the app. Windows must stay powered on, awake, connected to the network, and running the terminal for the dashboard to remain available. Set power sleep options appropriately if monitoring later.

**Security:** This local dashboard has **no login/authentication**. Anyone who can access its port on your network may see it. Keep it limited to a trusted private network. Do **not** enable router port forwarding, expose port 8501 to the internet, or add brokerage credentials to the app. For remote access outside home, implement proper authentication and a trusted VPN first.

**Mac-only alternative:** If you're continuing on Mac for now, follow the next section and run it locally. The `localhost` URL refers to whichever machine is hosting Streamlit.

## Start on your Mac (VS Code terminal)

```bash
cd ILRAY_Quant_Research_Lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address Streamlit prints (usually `http://localhost:8501`). The dashboard downloads **historical market data** automatically when connected. You may explicitly select synthetic demo mode for offline testing. Alternatively upload a CSV with this structure:

```csv
Date,SPY,QQQ,TLT
2026-01-02,100.00,200.00,88.00
2026-01-05,100.30,201.10,88.25
```

Use **many more historical dates** for the rankings/backtests to be meaningful. You can also upload a simple Excel worksheet with the same wide format; the upload control does **not** automatically interpret a complicated `.xlsm` or `.xlsb` model.

## Dashboard modules

| Module | Works now | Planned source workbook |
|---|---|---|
| Mission Control | Price overview, navigation | All models |
| Macro QUAD | Transparent rising/falling GDP and inflation classification; CSV import | Tops-Down Regime Segmentation |
| ETF Selector | Trailing returns, risk, drawdowns and ranking | Tops-Down QUAD + ETF Selector / ETF Bucketing |
| Portfolio Risk | Hypothetical allocation, buy-and-hold equity, historical VaR/CVaR, volatility attribution | New portfolio research module |
| Tactical Backtest | Moving average strategy, next-session execution, transaction fees, benchmark | Tactical Trading Toy Models |
| Research Validation | Chronological holdout evaluation of fixed example strategy, benchmark and exports | New research integrity module |
| Monte Carlo | IID return bootstrap and uncertainty bands | Monte Carlo Output |
| Asset Regimes | Simple ETF trend and realized-volatility states; not workbook-exact | Bottoms-Up 40 ETFs |
| Options Gamma | Uploaded real options snapshot; unsigned open-interest gamma proxy | GEX_NN_Copy |
| GEX & Workbook Bridge | Honest integration inventory; no fabricated dealer GEX values | GEX_NN_Copy / other workbooks |
| Model Notes | Scope, limitations and reproducibility notes | All models |

## Getting historical prices (no live orders)

In the sidebar, enter tickers like `SPY, QQQ, IWM, XLK` and click **Download adjusted closes** to clear the cache and refresh prices. You need a working internet connection. Historical data are delayed and may be incomplete or revised. Cross-check prices and corporate actions before interpreting a signal. This app never sends orders.

## Why the data-quality gate matters

The source **Top-Down QUAD with ETF Selector** workbook's raw ETF price columns stop on **December 30, 2022**, but the `ETFs` worksheet continues for another **1,013 dates** with blank raw prices. Excel formulas such as `=IFERROR(LN(B3/B2),0)` then return 0 for missing-price errors. This can artificially flatten returns and understate risk.

In the Python lab:

- Missing/nonpositive prices **stay missing**; they are never silently forward-filled.
- An ETF is **excluded from trailing rankings** unless its entire trailing price window is complete.
- The **Data Quality** screen separately flags recent-data gaps and assets whose last observed price is over seven calendar days old.
- Future-dated blank rows cannot make old observations appear current.

To examine the source workbook without modifying it:

```bash
python scripts/audit_excel_etf.py "/path/to/Tops-Down QUAD with ETF Selector MAC.xlsm"
```

The remaining Excel formula/macro parity work is **not finished**; do not use the source model's historical scores as executable trade signals without further validation.

## Inspect and migrate the original Excel files

Do not put giant workbooks in the app ZIP or GitHub repo. Keep them in a private folder on your computer. Start with individual tabs:

```bash
python scripts/inspect_workbooks.py "/path/to/Tops-Down Regime Segmentation(4).xlsm"
python scripts/import_workbook.py "/path/to/ETF_Bucketing(4).xlsm" --sheet tickers --output data/tickers.csv
```

The importer exports the **cached values** from a tab. It does not execute Excel macros, recalculate formula chains, or automatically translate VBA. Preserve the originals. For each migration: (1) identify input cells, (2) list formulas/VBA dependencies, (3) implement Python rules, (4) compare identical input snapshots and expected outputs, (5) add regression tests, (6) only then replace the placeholder model in the app.

## Important engineering boundaries

- The QUAD classifier uses the change in supplied GDP and inflation series; it is **not** a verified port of the OECD transformations in the source workbooks.
- The ETF score is simply return ÷ annualized realized volatility; **not** the Excel ETF Selector proprietary scoring method.
- The sample tactical strategy uses fast/slow moving averages; it is **not** the Excel toy strategy, VIX signal logic, or an optimization result.
- The Monte Carlo engine independently resamples daily returns, assumes independent draws, and is not a predictive confidence interval.
- The GEX module currently maps input sheets, not exposure metrics. Dealer positioning cannot be inferred reliably from gamma and OI alone without assumptions.
- Portfolio Risk assumes an initial fully-funded, long-only buy-and-hold basket with no rebalancing, no commissions and no margin. Historical VaR/CVaR are estimates, not loss ceilings.
- This is **research software**, not a broker-connected live trading system. No order execution, live feeds, security custody, compliance, monitoring, tax tracking, or position-risk limits are claimed.

## Tests

```bash
python -m pytest -q
```

Tests cover data validation, regime classification, **no-lookahead next-bar execution**, transaction fees, backtest outputs, and deterministic Monte Carlo output.

## Roadmap to a professional, portfolio-ready application

1. **Faithful Excel migration:** examine exact macro signals, ETF bucket weights, bottoms-up regimes, tactical/VIX rules, and GEX calculations; build spreadsheet parity tests.
2. **Historical datasets:** source and timestamp reputable price, fundamental, macro, rates, and options feeds; track adjusted vs unadjusted prices and survivorship bias.
3. **Research quality:** walk-forward validation, corporate actions, realistic slippage, stable train/test splits, turnover, regime sensitivity and drawdown controls.
4. **Production engineering:** SQLite/Postgres, scheduled pipelines, authentication, observability, CI tests, versioned configs, audit logs, deployment.
5. **Optional paper trading:** separate tested paper-broker integration, position and risk limits; live execution only after careful safeguards.

The best proof of skill to recruiters is not a dashboard screenshot; it's a reproducible tested data pipeline, a documented strategy hypothesis, honest out-of-sample evaluation, and a clear explanation of what does *not* work.


## Run the comprehensive verification on your Windows PC
After `setup_windows.bat` finishes, double-click `self_check_windows.bat`.
It executes the automated unit tests, checks **all 16 Streamlit pages using explicitly synthetic demonstration data**, and probes public Yahoo Finance / FRED historical-data downloads.
Read `SELF_CHECK_RESULTS.json` for PASS/FAIL details and any error messages.
The run may take several minutes, and internet access is needed for the external-provider portion.
Passing these checks is **not** a guarantee of correct investment forecasts, real-world trading performance, or complete brokerage/execution readiness. It does not test every button or Windows configuration.

**Important:** A passing `self_check_windows.bat` result tests synthetic-data rendering and local HTTP startup, not every possible control, actual Windows BAT semantics, market-data correctness, or historical trade profitability. If any step reports `NOT VERIFIED` or `FAIL`, do not mark the platform fully validated.
