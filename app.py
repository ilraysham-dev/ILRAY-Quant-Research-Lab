"""ILRAY Quant Lab — launch with: streamlit run app.py"""
from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from quantlab.engine import (backtest, classify_quad, clean_prices, etf_rankings,
                             make_demo_data, monte_carlo, performance, signals)
from quantlab.portfolio import buy_and_hold_portfolio, risk_contributions, estimate_var
from quantlab.market_data import download_prices, DEFAULT_TICKERS
from quantlab.macro_data import download_us_macro
from quantlab.macro_snapshot import load_snapshot
from quantlab.validation import holdout_backtest
from quantlab.bottom_up import asset_regimes
from quantlab.options import gross_gamma_profile
from quantlab.quality import price_quality_report
from quantlab.regimes import market_regimes
from quantlab.advanced_validation import validated_ma_backtest

from quantlab.factors import momentum_factors, parse_fundamentals, score_factors

from quantlab.research_suite import clean_return_panel, basic_stats, stress_windows, random_portfolio_cloud, walk_forward_ma, html_report

st.set_page_config(page_title="ILRAY | Quant Research Lab", page_icon="📈", layout="wide")
st.markdown("""
<style>
  .stApp {background:#08101f;color:#e8efff}
  [data-testid="stSidebar"] {background:#0d1729;border-right:1px solid #20304d}
  h1,h2,h3 {letter-spacing:-.035em}
  h1 {color:#e8efff}
  [data-testid="stMetric"] {background:#10213a;border:1px solid #244065;padding:16px;border-radius:12px}
  div.stButton>button {border-radius:9px;background:#183e61;color:#d9f9f1;border:1px solid #2a947d}
  [data-testid="stAlert"] {border-radius:9px}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def demo():
    return make_demo_data()


@st.cache_data(ttl=3600, show_spinner=False)
def historical_prices(symbols: tuple[str, ...], period: str):
    return download_prices(list(symbols), period)


@st.cache_data(ttl=86400, show_spinner=False)
def historical_macro():
    return download_us_macro()


def parse_prices(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        raw = pd.read_csv(file)
    else:
        engine = "calamine" if file.name.lower().endswith(".xlsb") else "openpyxl"
        raw = pd.read_excel(file, engine=engine)
    return clean_prices(raw)


def plot_equity(results):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=results.index, y=results["Strategy Equity"], name="Strategy", line=dict(color="#46dfb0", width=3)))
    fig.add_trace(go.Scatter(x=results.index, y=results["Buy Hold Equity"], name="Buy & Hold", line=dict(color="#7197ed", width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1729", plot_bgcolor="#0d1729", height=410,
                      margin=dict(l=15,r=15,t=20,b=15), yaxis_title="Growth of $1", legend=dict(orientation="h"))
    return fig


with st.sidebar:
    st.markdown("## ◈ ILRAY LAB")
    st.caption("QUANTITATIVE RESEARCH WORKSPACE")
    page = st.radio("Workspace", ["Mission Control", "Data Quality", "Macro QUAD", "ETF Selector", "Asset Regimes", "Market Regime Detector", "Factor Research Engine", "Portfolio Risk", "Tactical Backtest", "Research Validation", "Advanced Backtest Validation", "Monte Carlo", "Options Gamma", "GEX & Workbook Bridge", "Research Suite", "Model Notes"])
    st.divider()
    st.markdown("**Research dataset**")
    mode = st.radio("Price source", ["Historical market data", "Synthetic demo (testing only)"], index=1 if os.environ.get("QUANT_LAB_OFFLINE_SMOKE") == "1" else 0)
    uploaded = st.file_uploader("Upload wide-form close prices", type=["csv", "xlsx", "xlsm", "xlsb"], help="Date,SPY,QQQ,... ; for complex Excel files use the import script to select a specific sheet")
    st.markdown("**Historical market settings**")
    ticker_input = st.text_input("Symbols (comma separated)", ", ".join(DEFAULT_TICKERS))
    period = st.selectbox("Historical window", ["1y", "2y", "5y", "10y"], index=2)
    if st.button("Download adjusted closes"):
        with st.spinner("Retrieving historical data..."):
            try:
                historical_prices.clear()
                st.session_state.pop("historical_error", None)
                st.success("Historical price cache cleared; data will refresh now.")
            except Exception as exc:
                st.error(f"Download failed: {exc}")
    st.caption("Historical prices are fetched automatically and cached for 1 hour. They are not live quotes. Demo mode is explicitly simulated.")
    st.divider()
    st.caption("Research only · No broker access · No live order execution")

prices, macro = None, None
source = "UNAVAILABLE"
if mode.startswith("Synthetic"):
    prices, macro = demo()
    source = "SYNTHETIC DEMO / NOT MARKET DATA"
else:
    try:
        prices = historical_prices(tuple(s.strip().upper() for s in ticker_input.split(",") if s.strip()), period)
        source = "YAHOO HISTORICAL ADJUSTED CLOSES (cached up to 1 hour; NOT LIVE)"
    except Exception as exc:
        st.sidebar.error(f"Historical price feed unavailable: {exc}")
if uploaded:
    try:
        prices = parse_prices(uploaded)
        source = f"UPLOADED: {uploaded.name}"
        st.sidebar.success(f"Loaded {len(prices):,} observations, {len(prices.columns)} symbols")
    except Exception as exc:
        st.sidebar.error(f"Could not load prices: {exc}")

if prices is None:
    st.error("Historical prices could not be retrieved. Check the internet connection and symbols, then click 'Download adjusted closes' to retry. Alternatively upload a verified historical CSV. No synthetic data are substituted automatically.")
    st.stop()

if mode.startswith("Historical") and page == "Macro QUAD":
    try:
        macro, macro_metadata = load_snapshot(Path(__file__).resolve().parent / "local_data")
        macro_source_label = "SCHEDULED FRED SNAPSHOT"
    except Exception as exc:
        macro_metadata = None
        macro_source_label = "DIRECT FRED DOWNLOAD"
        try:
            macro = historical_macro()
        except Exception as download_exc:
            st.warning(f"Scheduled snapshot not available ({exc}); FRED download unavailable ({download_exc}). You may upload a real quarterly macro CSV below.")

st.markdown("# ILRAY / Quant Research Lab")
st.caption(f"{page.upper()}  ·  DATA: {source}  ·  {prices.index.min().date()} – {prices.index.max().date()}")

if page == "Mission Control":
    st.markdown("### One workspace. Six research engines.")
    st.write("An integrated home for regime analysis, ETF selection, tactical signals, historical testing, Monte Carlo scenarios, and a controlled Excel-to-Python migration.")
    lookback = min(63, max(2, len(prices)//3))
    q = price_quality_report(prices, lookback)
    eligible = list(q.index[q["Status"] == "ELIGIBLE"])
    historic = prices.loc[prices.index <= pd.Timestamp.today().normalize()]
    rank = etf_rankings(historic[eligible], lookback) if eligible else pd.DataFrame()
    cols = st.columns(4)
    cols[0].metric("Symbols", len(prices.columns))
    cols[1].metric("Price sessions", f"{len(prices):,}")
    cols[2].metric("Top momentum", str(rank.index[0]) if not rank.empty else "N/A")
    cols[3].metric("Eligible symbols", f"{len(eligible)}/{len(prices.columns)}")
    st.plotly_chart(px.line(prices / prices.iloc[0], title="Normalized price paths (start = 1.0)", template="plotly_dark"), use_container_width=True)
    st.info("Historical downloads may be delayed or revised. Original workbooks remain separate source documents. Strategy formulas are reference implementations, not exact Excel macro replications.")

elif page == "Data Quality":
    st.markdown("### Market data health / safety gate")
    st.write("A missing price is **not** a 0% market return. This check finds stale prices, incomplete calculation windows, and blank observations before rankings are produced.")
    period = st.slider("Required complete price window", 20, 252, 63)
    report = price_quality_report(prices, period)
    ok = int(report["Status"].eq("ELIGIBLE").sum())
    c1,c2=st.columns(2)
    c1.metric("Eligible assets", f"{ok}/{len(report)}")
    c2.metric("Flagged assets", len(report)-ok)
    st.dataframe(report, use_container_width=True)
    st.download_button("Export quality report", report.to_csv().encode(), "data_quality.csv", "text/csv")
    st.caption("For real data, this conservative gate requires a complete trailing window and last observed price within seven calendar days. Exchange closures and unavailable market data may legitimately trigger a warning.")

elif page == "Macro QUAD":
    st.markdown("### Economic regime / QUAD")
    st.write("Classifies whether GDP growth and inflation are accelerating or decelerating. This is a simplified reference model; exact OECD transformations and lag rules from your top-down workbooks still need porting.")
    if mode.startswith("Historical"):
        if macro_metadata:
            retrieved = pd.to_datetime(macro_metadata.get("retrieved_at_utc"), utc=True, errors="coerce")
            age = (pd.Timestamp.now(tz="UTC") - retrieved).total_seconds() / 3600 if pd.notna(retrieved) else float("inf")
            st.caption(f"Source: {macro_source_label} | Last successful refresh: {macro_metadata.get('retrieved_at_utc', 'unknown')} | Most recent observation quarter: {macro_metadata.get('last_observation_quarter', 'unknown')}")
            if age > 48:
                st.warning(f"Saved macro snapshot is {age/24:.1f} days old. Check your scheduled refresh task. Economic series may have different release schedules.")
        else:
            st.caption("Source: direct FRED retrieval (cached up to 24 hours). For unattended updates, configure refresh_macro_windows.bat with Windows Task Scheduler.")
        if st.button("Refresh FRED macro data now"):
            try:
                historical_macro.clear()
                macro = historical_macro()
                st.success("FRED download refreshed in this dashboard session. For a durable scheduled snapshot, run refresh_macro_windows.bat on your Windows PC.")
            except Exception as exc:
                st.error(f"Refresh failed; no fabricated data used: {exc}")
    macro_file = st.file_uploader("Optional quarterly macro CSV (Date,GDP,Inflation)", type="csv", key="macro")
    if macro_file:
        try:
            macro = pd.read_csv(macro_file)
        except Exception as exc:
            st.error(f"Macro CSV error: {exc}")
    window = st.slider("Change comparison (periods)", 1, 6, 3)
    if macro is None:
        st.error("No historical macro dataset is available. Check the FRED connection or upload a quarterly macro CSV. Synthetic macro numbers are not used in historical mode.")
    else:
      if mode.startswith("Historical") and not macro_file:
        st.caption("Source: FRED GDPC1 (real GDP) and CPIAUCSL (CPI). Both converted to quarterly year-over-year % changes. FRED values are latest revised vintage, plotted by observation quarter, NOT release date. This QUAD is descriptive only and unsuitable for point-in-time trading backtests.")
      try:
        regime = classify_quad(macro, periods=window)
        current = regime["Regime"].iloc[-1]
        st.metric("Latest classified regime", current)
        col1, col2 = st.columns(2)
        col1.plotly_chart(px.line(regime, y="GDP", title="GDP input", template="plotly_dark"), use_container_width=True)
        col2.plotly_chart(px.line(regime, y="Inflation", title="Inflation input", template="plotly_dark"), use_container_width=True)
        st.dataframe(regime.tail(16), use_container_width=True)
      except Exception as exc:
        st.error(str(exc))

elif page == "ETF Selector":
    st.markdown("### Cross-asset / ETF ranker")
    lookback = st.slider("Trailing trading sessions", 20, 252, 63, disabled=len(prices) <= 20)
    if len(prices) <= lookback:
        st.warning("More price history required; upload a longer dataset.")
    else:
        report = price_quality_report(prices, lookback)
        eligible = list(report.index[report["Status"] == "ELIGIBLE"])
        if len(eligible) < len(prices.columns):
            st.warning(f"Excluded {len(prices.columns)-len(eligible)} ticker(s) due to missing, insufficient, or stale prices. Review Data Quality for details.")
        historical = prices.loc[prices.index <= pd.Timestamp.today().normalize()]
        ranks = etf_rankings(historical[eligible], lookback) if eligible else pd.DataFrame()
        if ranks.empty:
            st.error("No ETFs passed the data-quality checks. Download refreshed prices or upload a clean historical dataset.")
            st.stop()
        st.caption("Score = trailing return / annualized realized volatility. This is a research ranking, not an automatic buy recommendation.")
        st.dataframe(ranks.style.format({"Return":"{:.1%}","Annualized Vol":"{:.1%}","Worst Drawdown":"{:.1%}","Score":"{:.2f}"}), use_container_width=True)
        st.plotly_chart(px.bar(ranks.reset_index(), x="Ticker", y="Score", title="Risk-scaled trailing-return score", template="plotly_dark"), use_container_width=True)
        st.download_button("Download ranked ETF table", ranks.to_csv().encode(), "etf_rankings.csv", "text/csv")

elif page == "Asset Regimes":
    st.markdown("### Bottom-up ETF trend / volatility states")
    st.write("A transparent, simplified way to categorize each ETF. This is **not** a replica of the original 40-ETF workbook's formulas and is not an automatic buy/sell signal.")
    a,b,c = st.columns(3)
    tw = a.slider("Trend lookback (sessions)",20,252,63)
    vw = b.slider("Volatility lookback (sessions)",20,252,63)
    vt = c.slider("High volatility threshold (annualized)",.1,.8,.25,.05)
    # Use the same price-quality timing gate, not forward-filled observations.
    states = asset_regimes(prices,tw,vw,vt)
    st.dataframe(states.style.format({"Trend Return":"{:.1%}","Annualized Vol":"{:.1%}"}),use_container_width=True)
    st.download_button("Export asset regimes",states.to_csv().encode(),"asset_regimes.csv","text/csv")
    st.caption("States reflect past prices, not forecasts. Symbols with incomplete windows remain unclassified.")

elif page == "Portfolio Risk":
    st.markdown("### Portfolio construction / risk cockpit")
    st.write("Build a hypothetical long-only portfolio, compare allocations and examine historical risk. This is a research exercise, not an order ticket.")
    selected = st.multiselect("Choose holdings", list(prices.columns), default=list(prices.columns[:min(4, len(prices.columns))]))
    if selected:
        st.caption("Enter approximate target allocation; values automatically normalize to 100%.")
        grid = st.columns(min(len(selected), 4))
        allocations = {symbol: grid[i % len(grid)].number_input(symbol + " weight", min_value=0.0, max_value=100.0,
                                                                 value=float(round(100 / len(selected), 1)), step=1.0, key="w_"+symbol)
                       for i, symbol in enumerate(selected)}
        try:
            chosen = pd.Series(allocations)
            portfolio = buy_and_hold_portfolio(prices, chosen)
            exposure = risk_contributions(prices, chosen)
            var = estimate_var(portfolio["Portfolio Return"])
            first, second, third = st.columns(3)
            first.metric("Portfolio growth", f"{portfolio['Portfolio Equity'].iloc[-1] - 1:.1%}")
            second.metric("Historical 95% daily VaR", f"{var['Historical VaR']:.2%}")
            third.metric("Historical 95% daily expected shortfall", f"{var['Historical CVaR']:.2%}")
            st.plotly_chart(px.line(portfolio, y="Portfolio Equity", template="plotly_dark", title="Buy-and-hold portfolio: growth of $1"),use_container_width=True)
            # Historical risk-return dots for selected holdings, using overlapping data.
            st.markdown("#### Risk vs. return (dot chart)")
            daily_asset_returns = prices[selected].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna(how="any")
            if len(daily_asset_returns) >= 3:
                annualized_asset_returns = daily_asset_returns.mean() * 252
                annualized_asset_vols = daily_asset_returns.std(ddof=1) * np.sqrt(252)
                points = pd.DataFrame({
                    "Ticker": selected,
                    "Annualized Return": [float(annualized_asset_returns[t]) for t in selected],
                    "Annualized Volatility": [float(annualized_asset_vols[t]) for t in selected],
                })
                dots = px.scatter(
                    points,
                    x="Annualized Volatility", y="Annualized Return", text="Ticker",
                    title="Historical risk versus return — individual holdings",
                    template="plotly_dark",
                    labels={"Annualized Volatility": "Annualized volatility", "Annualized Return": "Annualized return"},
                )
                dots.update_traces(marker=dict(size=13, color="#58c7ec"), textposition="top center")
                dots.update_xaxes(tickformat=".0%")
                dots.update_yaxes(tickformat=".0%")
                dots.update_layout(height=430, margin=dict(l=35, r=20, t=55, b=35),
                                   paper_bgcolor="#0d1729", plot_bgcolor="#0d1729")
                st.plotly_chart(dots, use_container_width=True)
                st.caption("Each dot is a holding. Risk is historical annualized volatility, and return is historical mean daily return annualized. Past results do not predict future returns.")
            else:
                st.info("At least three matching daily return observations are needed to draw the risk-versus-return dots.")
            c1,c2=st.columns(2)
            exposure_chart = exposure.reset_index().rename(columns={exposure.index.name or "index": "Ticker"})
            c1.plotly_chart(px.pie(exposure_chart, names="Ticker", values="Weight", title="Capital weights", template="plotly_dark"), use_container_width=True)
            c2.dataframe(exposure.style.format({"Weight":"{:.1%}","Annualized Vol Contribution":"{:.2%}"}),use_container_width=True)
            st.caption("Assumes one initial purchase, fractional shares and no rebalancing, taxes, commissions or slippage. Historical VaR is not a worst-case loss.")
            st.download_button("Download portfolio returns", portfolio.to_csv().encode(), "portfolio_returns.csv", "text/csv")
        except Exception as exc:
            st.warning(str(exc))

elif page == "Tactical Backtest":
    st.markdown("### Rule-based tactical backtest")
    st.write("A fully inspectable moving-average trend strategy, with next-session execution and configurable turnover costs. Your original toy-model rules are a separate parity task.")
    c1,c2,c3,c4 = st.columns(4)
    symbol = c1.selectbox("Asset", prices.columns)
    fast = c2.number_input("Fast average", 2, 150, 20)
    slow = c3.number_input("Slow average", 3, 300, 80)
    fee = c4.number_input("Cost per trade (bps)", 0.0, 100.0, 5.0)
    try:
        sig = signals(prices[symbol], int(fast), int(slow))
        bt = backtest(prices[symbol], sig, fee)
        stats = performance(bt["Strategy Return"], bt["Strategy Equity"])
        metrics = st.columns(4)
        metrics[0].metric("Total strategy return", f"{stats['Total Return']:.1%}")
        metrics[1].metric("Annualized volatility", f"{stats['Annualized Vol']:.1%}")
        metrics[2].metric("Sharpe (0% risk-free)", f"{stats['Sharpe (rf=0)']:.2f}")
        metrics[3].metric("Max drawdown", f"{stats['Max Drawdown']:.1%}")
        st.plotly_chart(plot_equity(bt), use_container_width=True)
        st.caption(f"Latest target allocation: {int(sig.iloc[-1]*100)}%. Orders are NOT placed. Backtests omit taxes, spreads beyond selected cost, slippage, and market impact.")
        st.download_button("Export full backtest", bt.to_csv().encode(), f"{symbol}_backtest.csv", "text/csv")
    except Exception as exc:
        st.warning(str(exc))

elif page == "Research Validation":
    st.markdown("### Historical strategy holdout / benchmark")
    st.write("Separate older development data from a later holdout period. The rule is fixed in advance, and signals are held starting the next session. Never choose parameters by looking at holdout performance.")
    a, b, c, d = st.columns(4)
    symbol = a.selectbox("Asset", list(prices.columns), key="holdout_symbol")
    fast = b.number_input("Fast average", 2, 150, 20, key="holdout_fast")
    slow = c.number_input("Slow average", 3, 300, 80, key="holdout_slow")
    split = d.slider("Training %", 50, 90, 75, 5)
    fee = st.number_input("One-way trading cost (basis points)", 0., 100., 5., key="holdout_cost")
    try:
        timeline, comparison = holdout_backtest(prices[symbol], int(fast), int(slow), split/100, fee)
        st.dataframe(comparison.style.format({"Strategy Return":"{:.1%}","Benchmark Return":"{:.1%}","Strategy Max Drawdown":"{:.1%}","Strategy Sharpe (rf=0)":"{:.2f}"}), use_container_width=True)
        st.plotly_chart(plot_equity(timeline), use_container_width=True)
        st.download_button("Download validation results", comparison.to_csv().encode(), "holdout_validation.csv", "text/csv")
        st.download_button("Download full analysis", timeline.to_csv().encode(), "holdout_timeseries.csv", "text/csv")
        st.warning("A holdout split is useful, but not a complete independent study. Data are survivorship-biased toward today's ETF universe, trading costs are simplified, and results are not predictive. Macro release-vintage and GEX strategies are not used in this backtest.")
    except Exception as exc:
        st.warning(str(exc))

elif page == "Market Regime Detector":
    st.markdown("### Market Regime Detector")
    st.write("A descriptive view of trends and volatility using daily closing prices. Regimes are NOT forecasts or trading recommendations.")
    c1,c2,c3,c4 = st.columns(4)
    ticker = c1.selectbox("Asset", list(prices.columns), key="regime_asset")
    fast = c2.number_input("Fast moving average", 5, 150, 50, key="regime_fast")
    slow = c3.number_input("Slow moving average", 20, 300, 200, key="regime_slow")
    vol_window = c4.number_input("Volatility window (days)", 5, 90, 21, key="regime_vol_window")
    try:
        result = market_regimes(prices[ticker], int(fast), int(slow), int(vol_window))
        valid = result[result["Regime"] != "Insufficient data"]
        if valid.empty:
            st.warning("Not enough historical data to calculate the selected windows. Try a longer history or shorter moving averages.")
        else:
            st.metric("Latest observed regime", valid["Regime"].iloc[-1])
            st.caption(f"As of closing data: {valid.index[-1].date()}. Classification is descriptive and uses no future data.")
            fig = go.Figure()
            for field, color in [("Price", "#e5efff"), ("Fast MA", "#43d7b4"), ("Slow MA", "#f1ae62")]:
                fig.add_trace(go.Scatter(x=result.index,y=result[field],name=field,line=dict(color=color)))
            fig.update_layout(template="plotly_dark",height=390,title=f"{ticker} — Price and trend averages")
            st.plotly_chart(fig,use_container_width=True)
            st.plotly_chart(px.line(result,y=["Annualized Volatility","Historical Vol Threshold"],template="plotly_dark",
                                    title="Annualized realized volatility vs historical threshold"),use_container_width=True)
            st.dataframe(result.tail(35).iloc[::-1],use_container_width=True)
        st.download_button("Download regime history",result.to_csv().encode(),f"{ticker}_regimes.csv","text/csv")
        st.warning("Regime classification is not a trading forecast. Thresholds use earlier realized volatility only; today's close cannot be traded retroactively.")
    except Exception as exc:
        st.error(f"Regime analysis unavailable: {exc}")

elif page == "Advanced Backtest Validation":
    st.markdown("### Advanced Backtest Validation")
    st.write("Select moving-average parameters using TRAINING data only, then evaluate on later HOLDOUT data without re-optimizing.")
    c1,c2,c3 = st.columns(3)
    ticker = c1.selectbox("Asset",list(prices.columns),key="advanced_symbol")
    train_pct = c2.slider("Training portion (%)",55,85,70,5,key="advanced_train_pct")
    cost = c3.number_input("One-way cost (bps)",0.0,100.0,5.0,key="advanced_cost")
    st.caption("Parameter candidates: fast 10/20/30 days, slow 50/100/150 days. Best pair selected using training Sharpe only.")
    try:
        timeline, summary, candidates = validated_ma_backtest(prices[ticker],train_fraction=train_pct/100,
                                                              one_way_bps=float(cost))
        winning = candidates.iloc[0]
        st.success(f"Training-only choice: {int(winning['Fast'])}-day / {int(winning['Slow'])}-day moving averages.")
        st.dataframe(summary.style.format({"Total Return":"{:.1%}","Annualized Vol":"{:.1%}",
                                           "Max Drawdown":"{:.1%}","Sharpe (rf=0)":"{:.2f}"}),use_container_width=True)
        st.plotly_chart(plot_equity(timeline),use_container_width=True)
        st.markdown("#### Training-only parameter comparison")
        st.dataframe(candidates,use_container_width=True)
        st.download_button("Download strategy timeline",timeline.to_csv().encode(),f"{ticker}_advanced_validation.csv","text/csv")
        st.download_button("Download summary",summary.to_csv(index=False).encode(),f"{ticker}_validation_summary.csv","text/csv")
        st.warning("Research limitations: only one holdout, simple one-way trade costs, no borrow costs/taxes/slippage/market impact. ETF universe may suffer survivorship bias. Repeatedly inspecting holdout results and re-tuning invalidates its independence. No future performance is guaranteed.")
    except Exception as exc:
        st.error(f"Backtest validation unavailable: {exc}")

elif page == "Factor Research Engine":
    st.markdown("### Factor Research Engine / Cross-sectional screening")
    st.write("Rank historical price momentum, and optionally compare value and quality when a genuine fundamental snapshot is uploaded. These are descriptive research scores, not trade signals.")
    a, b = st.columns(2)
    factor_lookback = a.selectbox("Momentum lookback (trading sessions)", [63, 126, 252], index=2, key="factor_lookback")
    factor_skip = b.selectbox("Recent sessions to skip", [0, 5, 21], index=2, key="factor_skip")
    factor_file = st.file_uploader("Optional fundamental snapshot CSV (for value / quality)", type="csv", key="factor_csv")
    factor_snapshot = None
    if factor_file is not None:
        try:
            factor_snapshot = parse_fundamentals(pd.read_csv(factor_file))
            st.success(f"Fundamental snapshot loaded for {len(factor_snapshot)} tickers. Verify the snapshot date, provenance, and point-in-time availability before using it in research.")
        except Exception as exc:
            st.error(f"Fundamental input rejected: {exc}")
    choices = ["Momentum"] + (["Value", "Quality"] if factor_snapshot is not None else [])
    factor_selection = st.multiselect("Factors to rank (equal weight per chosen factor)", choices, default=["Momentum"], key="factor_selection")
    if factor_file is None:
        st.info("Only price-based momentum is available without fundamentals. ETFs do not have directly comparable company P/E, P/B, ROE and debt ratios without a defined look-through methodology.")
    st.caption("Momentum = close from N sessions ago to close from K sessions ago, excluding the latest K sessions. Ranks are percentiles among the current available tickers.")
    try:
        if not factor_selection:
            st.warning("Choose at least one factor.")
        else:
            factor_momentum = momentum_factors(prices, lookback=int(factor_lookback), skip_sessions=int(factor_skip))
            factor_ranked = score_factors(factor_momentum, factor_snapshot, tuple(factor_selection))
            factor_eligible = factor_ranked.dropna(subset=["Composite Score"])
            x, y, z = st.columns(3)
            x.metric("Scored tickers", f"{len(factor_eligible)}/{len(factor_ranked)}")
            y.metric("Factors selected", len(factor_selection))
            z.metric("Top-ranked ticker", str(factor_eligible.index[0]) if not factor_eligible.empty else "N/A")
            if factor_eligible.empty:
                st.warning("No ticker has all the selected factor inputs. Check missing values, the price window, and the uploaded ticker names.")
            else:
                factor_plot = factor_eligible.reset_index().rename(columns={factor_eligible.index.name or "index": "Ticker"})
                st.plotly_chart(px.bar(factor_plot.head(20), x="Ticker", y="Composite Score", title="Cross-sectional factor score (higher ranks better)", template="plotly_dark"), use_container_width=True)
            st.dataframe(factor_ranked, use_container_width=True)
            st.download_button("Download factor research table", factor_ranked.to_csv().encode(), "factor_research_scores.csv", "text/csv")
            st.warning("Price return momentum is backward-looking, not a forecast. The ranking uses today's selected universe and may be survivorship-biased. Fundamentals are user supplied, not verified or dated by this app. No point-in-time backtest, ETF holdings look-through, transaction costs, or investability study is implied.")
    except Exception as exc:
        st.error(f"Factor research unavailable: {exc}")

elif page == "Research Suite":
    st.markdown('### Research Suite / Risk, Stress, Validation & Reports')
    st.caption('Additive research tools. Historical data only; no orders, no broker connection, and no forecasts.')
    research_tab = st.tabs(['Portfolio Diagnostics', 'Stress Testing', 'Allocation Experiments', 'Walk-forward Validation', 'Research Report'])
    available = list(prices.columns)
    with research_tab[0]:
        risk_names = st.multiselect('Holdings for research suite', available, default=available[:min(4,len(available))], key='suite_names')
        if risk_names:
            w_inputs = st.columns(min(4,len(risk_names)))
            risk_weights = {symbol:w_inputs[i%len(w_inputs)].number_input(f'{symbol} weight %', min_value=0.0,max_value=100.,value=float(round(100/len(risk_names),2)),key=f'suite_weight_{symbol}') for i,symbol in enumerate(risk_names)}
            try:
                suite_returns = clean_return_panel(prices,risk_names)
                suite_stats = basic_stats(suite_returns,risk_weights)
                metric_cols=st.columns(4)
                metric_cols[0].metric('Annualized arithmetic return',f'{suite_stats["annualized_return"]:.1%}')
                metric_cols[1].metric('Annualized volatility',f'{suite_stats["annualized_volatility"]:.1%}')
                metric_cols[2].metric('Maximum drawdown',f'{suite_stats["max_drawdown"]:.1%}')
                metric_cols[3].metric('Effective holdings',f'{suite_stats["effective_holdings"]:.2f}')
                corr=suite_stats['correlations']
                st.plotly_chart(px.imshow(corr,zmin=-1,zmax=1,color_continuous_scale='RdBu_r',title='Asset return correlations'),use_container_width=True)
                st.plotly_chart(px.line(suite_stats['drawdown'],title='Constant-weight portfolio drawdown',template='plotly_dark'),use_container_width=True)
                st.dataframe(suite_stats['asset_summary'].style.format({'Weight':'{:.1%}','Annualized Arithmetic Return':'{:.1%}','Annualized Volatility':'{:.1%}','Annualized Vol Contribution':'{:.1%}'}),use_container_width=True)
                st.download_button('Download correlation CSV',corr.to_csv().encode(),'suite_correlations.csv','text/csv')
                st.caption('Only overlapping complete return dates are used. These diagnostics assume constant weights rebalanced daily, unlike the separate buy-and-hold Portfolio Risk page.')
            except Exception as exc:
                st.warning(f'Portfolio diagnostics unavailable: {exc}')
                suite_returns=None
                suite_stats=None
        else:
            suite_returns=None
            suite_stats=None
            st.info('Select at least one holding to calculate risk diagnostics.')
    with research_tab[1]:
        if suite_returns is not None:
            st.markdown('#### Rolling losses & hypothetical shocks')
            days=st.slider('Rolling trading sessions',5,126,21,key='suite_rolling')
            suite_scenarios,suite_rolling,suite_worst=stress_windows(suite_returns,risk_weights,days)
            st.dataframe(suite_scenarios.style.format({'Assumed change in each asset':'{:.1%}','Estimated portfolio change':'{:.1%}'}),hide_index=True,use_container_width=True)
            st.plotly_chart(px.line(suite_rolling.dropna(),title=f'Historical rolling {days}-session portfolio return',template='plotly_dark'),use_container_width=True)
            st.markdown('##### Ten worst rolling windows (may overlap)')
            st.dataframe(suite_worst.to_frame('Return').style.format({'Return':'{:.1%}'}),use_container_width=True)
            st.caption('Parallel shocks are user-independent, hypothetical what-if examples. They do not estimate the historical impact of a named financial crisis.')
        else:
            st.info('Select holdings in Portfolio Diagnostics first.')
    with research_tab[2]:
        if suite_returns is not None and len(risk_names)>1:
            ncloud=st.slider('Random long-only allocations',200,3000,800,200,key='suite_cloud_n')
            cloud=random_portfolio_cloud(suite_returns,count=ncloud)
            figure=px.scatter(cloud,x='Annualized Volatility',y='Annualized Return',color='Return/Volatility (rf=0)',title='Illustrative allocation cloud (not an efficient frontier)',template='plotly_dark')
            figure.update_xaxes(tickformat='.0%')
            figure.update_yaxes(tickformat='.0%')
            st.plotly_chart(figure,use_container_width=True)
            best=cloud['Return/Volatility (rf=0)'].replace([np.inf,-np.inf],np.nan).idxmax()
            st.write('Highest return/volatility ratio in this random sample (in-sample only):')
            st.dataframe(pd.DataFrame({'Ticker':risk_names,'Weight':cloud.loc[best,'Allocation']}).style.format({'Weight':'{:.1%}'}),hide_index=True)
            st.warning('This is NOT an investable optimized portfolio or verified efficient frontier. It ignores trading costs and estimation error. Do not select portfolios solely by in-sample results.')
        else:
            st.info('Choose at least two holdings in Portfolio Diagnostics first.')
    with research_tab[3]:
        ticker=st.selectbox('Single asset',available,key='suite_wf_symbol')
        a,b,c=st.columns(3)
        train=a.selectbox('Training sessions',[200,252,378,504],index=1,key='suite_wf_train')
        test=b.selectbox('Holdout block sessions',[21,42,63,126],index=2,key='suite_wf_test')
        costs=c.number_input('One-way turnover cost (bps)',0.,100.,5.,key='suite_wf_cost')
        st.caption('Uses past training periods to choose among fast MA 10/20/30 and slow MA 50/100/150; evaluates each chosen rule on the next separate block. Signals are lagged one session.')
        if st.button('Run walk-forward study',key='suite_wf_run'):
            try:
                timeline,folds=walk_forward_ma(prices[ticker],train_days=int(train),test_days=int(test),one_way_bps=float(costs))
                st.plotly_chart(px.line(timeline,y=['Strategy Equity','Buy Hold Equity'],title='Stitched out-of-sample paths (start=1)',template='plotly_dark'),use_container_width=True)
                st.dataframe(folds,use_container_width=True)
                st.download_button('Download walk-forward folds',folds.to_csv(index=False).encode(),'walkforward_folds.csv','text/csv')
                st.download_button('Download walk-forward daily returns',timeline.to_csv().encode(),'walkforward_returns.csv','text/csv')
                st.warning('This reduces some overfitting but is not independent once inspected and retuned. It does not include slippage, liquidity or survivorship-bias controls.')
            except Exception as exc:
                st.error(f'Walk-forward study unavailable: {exc}')
    with research_tab[4]:
        if suite_stats is not None:
            report_scenarios,_,_=stress_windows(suite_returns,risk_weights)
            report=html_report(prices[risk_names],suite_stats,report_scenarios,source,method_note='Data completeness and adjusted-close conventions depend on the selected source.')
            st.download_button('Download self-contained HTML research report',report.encode('utf-8'),'ILRAY_Research_Report.html','text/html')
            st.download_button('Download portfolio daily returns',suite_stats['portfolio_returns'].to_csv().encode(),'ILRAY_Portfolio_Daily_Returns.csv','text/csv')
            st.caption('The report contains data labels, exposure tables, correlation and scenario results; it is not an audited investment report. Use Print → Save as PDF in your browser if needed.')
        else:
            st.info('Select holdings in Portfolio Diagnostics to generate your report.')

elif page == "Monte Carlo":
    st.markdown("### Scenario laboratory / Monte Carlo")
    st.write("Simulate paths by resampling historical daily returns. This visualizes uncertainty; it does not predict what the market will do.")
    c1,c2,c3 = st.columns(3)
    symbol = c1.selectbox("Asset", prices.columns)
    horizon = c2.slider("Future sessions", 21, 504, 126)
    paths = c3.slider("Simulated paths", 200, 5000, 1000, 200)
    try:
        scenarios = monte_carlo(prices[symbol].pct_change(fill_method=None), horizon, paths)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=scenarios.index,y=scenarios["P95"],line=dict(width=0),showlegend=False))
        fig.add_trace(go.Scatter(x=scenarios.index,y=scenarios["P05"],fill="tonexty",fillcolor="rgba(74,210,173,.17)",line=dict(width=0),name="5–95% bootstrap band"))
        fig.add_trace(go.Scatter(x=scenarios.index,y=scenarios["Median"],line=dict(color="#48e2b0",width=3),name="Median path"))
        fig.update_layout(template="plotly_dark",paper_bgcolor="#0d1729",plot_bgcolor="#0d1729",height=470,xaxis_title="Sessions ahead",yaxis_title="Growth of $1")
        st.plotly_chart(fig,use_container_width=True)
        a,b,c=st.columns(3)
        a.metric("5th percentile terminal",f"{scenarios['P05'].iloc[-1]-1:.1%}")
        b.metric("Median terminal",f"{scenarios['Median'].iloc[-1]-1:.1%}")
        c.metric("95th percentile terminal",f"{scenarios['P95'].iloc[-1]-1:.1%}")
        st.download_button("Export scenario percentiles",scenarios.to_csv().encode(),"monte_carlo.csv","text/csv")
    except Exception as exc:
        st.warning(str(exc))

elif page == "Options Gamma":
    st.markdown("### Options chain: gross gamma sensitivity")
    st.write("Upload a **real option-chain snapshot** as CSV with `OptionType,Strike,OpenInterest,Gamma,Multiplier`. These must be consistent units for one underlying and snapshot. No synthetic options data are generated.")
    options_file = st.file_uploader("Options snapshot CSV",type="csv",key="options_input")
    spot = st.number_input("Underlying spot price (at snapshot)",min_value=.01,value=100.,step=1.)
    if options_file:
        try:
            raw_options = pd.read_csv(options_file)
            profile = gross_gamma_profile(raw_options,spot)
            st.metric("Gross gamma proxy ($ per 1% move)",f"${profile.iloc[:,0].sum():,.0f}")
            st.plotly_chart(px.bar(profile.reset_index(),x="Strike",y="Gross Gamma Proxy ($ / 1% move)",template="plotly_dark",title="Unsigned gamma/OI proxy by strike"),use_container_width=True)
            st.download_button("Export strike profile",profile.to_csv().encode(),"gross_gamma_profile.csv","text/csv")
            st.warning("Unsigned gamma × open interest is NOT signed dealer gamma exposure. Dealer positioning, trade direction, implied-volatility effects, expiry treatment and other assumptions are unknown. This output cannot establish hedging pressure or predict price direction.")
        except Exception as exc:
            st.error(str(exc))
    else:
        st.info("No options snapshot loaded. This screen remains inactive until you provide actual chain data with verified provenance.")

elif page == "GEX & Workbook Bridge":
    st.markdown("### Gamma exposure / Excel integration")
    st.info("Real dealer gamma exposure requires options-chain strikes, open interest, gamma, contract multipliers, an underlying spot reference, and an explicit dealer-position assumption. This app does not invent or silently extrapolate GEX.")
    st.markdown("**Workbook mapping**")
    st.dataframe(pd.DataFrame([
        ["Top-down Regime Segmentation", "OECD; macroeconomic PATH; Sequencing", "Macro QUAD / regime history", "Reference model only"],
        ["Top-down QUAD + ETF Selector", "ETFs; OECD; Monte Carlo", "ETF Selector + Monte Carlo", "Reference model only"],
        ["Bottoms-Up / 40 ETFs", "RegimeM/Regime%; ticker sheets", "Per-asset regime analytics", "Import/parity pending"],
        ["ETF Bucketing", "ETFs; tickers; USA", "Groups / sector tagging", "Import/parity pending"],
        ["GEX_NN_Copy", "Gamma by Strike; OI Profile; Results", "Options exposure panel", "Import/parity pending"],
        ["Tactical Trading toy models", "VIX; alerts; equity; performance", "Tactical Backtest", "Different reference strategy"],
        ["N30 TS notes", "Technical strategy specification", "Rulebook / model audit", "Review pending"],
    ],columns=["Source", "Relevant worksheets", "Target module", "Status"]),hide_index=True,use_container_width=True)
    st.write("Use `python scripts/inspect_workbooks.py /path/to/file.xlsm` to list source worksheets. Use `python scripts/import_workbook.py /path/to/file.xlsm --sheet ETFs --output data/etfs.csv` to extract a specific table for careful cleaning and mapping.")

else:
    st.markdown("### Research rules and model integrity")
    st.markdown("""
    1. **Inputs:** Historical Yahoo ETF prices by default; real FRED GDP/CPI on Macro QUAD. A synthetic test mode is available only when explicitly selected.
    2. **Timing:** Signals generated after close apply from the *next* trading session in the example backtest.
    3. **Costs:** Selected basis-point fees apply when exposure changes. Slippage, taxes and borrow costs are not modeled.
    4. **Economic quadrants:** GDP/inflation *differences*, compared over the selected periods. FRED series are revised and aligned to observation quarters, **not public release dates**, so this is NOT a tradeable historical signal or verified Excel/OECD methodology.
    5. **Ranker:** Return divided by annualized historical volatility; no optimization or investment advice implied.
    6. **Monte Carlo:** IID return resampling. It misses some regime changes, correlations, and fat tails.
    7. **No execution:** No brokerage keys, orders, position management, or live data feeds.
    8. **Portfolio:** Initial fully funded long-only buy-and-hold; historical covariance and one-day tail statistics.
    9. **Market feed:** Yahoo adjusted historical closes are fetched on demand, not guaranteed live or exchange-certified.
    10. **Historical holdout:** fixed moving-average parameters and chronological train/test segments. Never tune parameters after examining the holdout result.
    11. **Asset regimes:** simplified ETF trailing return and historical volatility states; not a validated replica of the class Bottoms-Up model.
    12. **Options Gamma:** an unsigned open-interest-weighted gamma sensitivity proxy, requiring a genuine uploaded chain and known contract multiplier. This is NOT estimated dealer positioning.
    13. **Next engineering milestone:** trace Excel formulas and VBA into Python one rule at a time, add golden-row tests, and compare outputs cell by cell.
    """)
    st.warning("For learning and research. This is not production execution software, a verified investment strategy, or financial advice.")
