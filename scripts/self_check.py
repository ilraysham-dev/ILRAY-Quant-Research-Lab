"""Windows/local verification utility. Does not place trades or require broker secrets.

Usage:
  python scripts/self_check.py             # offline UI checks using synthetic data
  python scripts/self_check.py --live      # also probe historical Yahoo/FRED feeds
"""
from __future__ import annotations
import argparse
import json
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "SELF_CHECK_RESULTS.json"

PAGES = ["Mission Control", "Data Quality", "Macro QUAD", "ETF Selector",
         "Asset Regimes", "Market Regime Detector", "Factor Research Engine",
         "Portfolio Risk", "Tactical Backtest", "Research Validation",
         "Advanced Backtest Validation", "Monte Carlo", "Options Gamma",
         "GEX & Workbook Bridge", "Research Suite", "Model Notes"]


def check_ui():
    results = {}
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as exc:
        return {"dependency": {"status": "NOT VERIFIED", "details": str(exc)}}
    os.environ["QUANT_LAB_OFFLINE_SMOKE"] = "1"
    for page in PAGES:
        try:
            # Every page uses synthetic data, and no real data feed is needed.
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
            at.run()
            at.sidebar.radio[0].set_value(page).run()
            problems = [str(item.message) for item in at.exception]
            problems += [str(item.message) for item in at.error]
            results[page] = {"status": "PASS" if not problems else "FAIL", "details": problems[:8]}
        except Exception as exc:
            results[page] = {"status": "FAIL", "details": [str(exc), traceback.format_exc(limit=2)]}
    os.environ.pop("QUANT_LAB_OFFLINE_SMOKE", None)
    return results


def check_startup():
    """Independent Streamlit process/HTTP health smoke test. Not a native .bat run."""
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env["QUANT_LAB_OFFLINE_SMOKE"] = "1"
        cmd = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
               "--server.address", "127.0.0.1", "--server.port", str(port),
               "--server.headless", "true", "--browser.gatherUsageStats", "false"]
        process = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(50):
                if process.poll() is not None:
                    return {"status": "FAIL", "details": "Streamlit exited before HTTP health check: " + process.stderr.read()[-1200:]}
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            return {"status": "PASS", "details": "Local Streamlit HTTP health endpoint responded on localhost"}
                except Exception:
                    time.sleep(0.3)
            return {"status": "FAIL", "details": "Streamlit did not answer /_stcore/health within 15 seconds"}
        finally:
            process.terminate()
            try: process.communicate(timeout=4)
            except subprocess.TimeoutExpired: process.kill(); process.communicate()
    except Exception as exc:
        return {"status": "FAIL", "details": str(exc)}


def check_live():
    results = {}
    from quantlab.market_data import download_prices
    from quantlab.macro_data import download_us_macro
    try:
        prices = download_prices(["SPY", "QQQ"], period="1y")
        if not {"SPY", "QQQ"}.issubset(prices.columns):
            raise AssertionError(f"Missing expected tickers: {list(prices.columns)}")
        if prices.empty or len(prices) < 100 or not prices.index.is_monotonic_increasing:
            raise AssertionError("Unexpected historical price coverage")
        results["Yahoo Finance"] = {"status": "PASS", "rows": len(prices),
                                    "last_date": str(prices.index[-1].date()), "tickers": list(prices.columns)}
    except Exception as exc:
        results["Yahoo Finance"] = {"status": "FAIL", "details": str(exc)}
    try:
        macro = download_us_macro()
        if not {"Date", "GDP", "Inflation"}.issubset(macro.columns) or len(macro) < 12:
            raise AssertionError("Unexpected GDP/CPI response")
        if macro[["GDP", "Inflation"]].isna().any().any():
            raise AssertionError("Nonfinite macro values")
        results["FRED"] = {"status": "PASS", "rows": len(macro),
                           "last_quarter": str(macro["Date"].iloc[-1].date())}
    except Exception as exc:
        results["FRED"] = {"status": "FAIL", "details": str(exc)}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="probe public financial-data providers")
    args = parser.parse_args()
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "machine": os.name,
              "streamlit_pages": check_ui(),
              "local_server_startup": check_startup(),
              "live_data": check_live() if args.live else {"status": "NOT VERIFIED", "reason": "Run with --live on a computer with internet access"}}
    print("\nQUANT LAB SELF-CHECK")
    all_statuses = []
    for section in ("streamlit_pages", "local_server_startup", "live_data"):
        print("\n" + section.upper())
        block = report[section]
        items = [(section, block)] if "status" in block else list(block.items())
        for name, item in items:
            if isinstance(item, dict):
                status = item.get("status", "UNKNOWN")
                all_statuses.append(status)
                print(f"  {name}: {status}")
                if item.get("details"):
                    print("    " + str(item["details"])[:250])
    report["overall_status"] = "FAIL" if "FAIL" in all_statuses else ("INCOMPLETE" if "NOT VERIFIED" in all_statuses else "PASS")
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\nOverall:", report["overall_status"])
    print("Saved:", REPORT)
    return 1 if report["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
