# Fixes and verification notes

## Changes made
- Prepared a clean distributable copy; removed `.venv`, `.venv_old`, application backups, Python caches, duplicated old portfolio modules, local data snapshots, and generated reports **from the public copy only**.
- Corrected Windows setup so a missing Python 3.13 installation does not block users with Python 3.11/3.12. Setup checks Python, installs requirements and runs tests before reporting success.
- Added `run_windows.bat` for localhost-only use; kept the existing LAN launcher with an explicit no-authentication warning and useful failure status.
- Expanded `.gitignore` for credentials, local data, and generated content.
- Clarified documentation for historical vs synthetic research reports and local vs LAN access.

## Checks and limits
- Automated tests and Python syntax: checked in Linux testing environment; results documented in `AUDIT_RESULTS.md`.
- Browser interactions, Windows batch execution, real Yahoo/FRED feeds, options snapshot licensing, real-world market accuracy and final UI appearance: **not end-to-end verified**.
- Research engines were intentionally not rewritten without a failing test or a validated replacement reference.

## Next before publication
1. Run `setup_windows.bat` and `run_windows.bat` on your PC.
2. Inspect every dashboard page in historical and demo modes.
3. Run data download and independently validate a sample of real results against a trusted source.
4. Only then make your GitHub repository public; never include broker credentials.


## Follow-up verification (v2)
- Added `scripts/self_check.py` and `self_check_windows.bat` for reproducible on-device dashboard and public-data checks.
- Added six independent numerical/provider-contract test cases (backtest timing and fees, ETF returns/volatility/drawdown, constant-return Monte Carlo, mocked Yahoo and FRED response handling).
- Added a machine-readable `SELF_CHECK_RESULTS.json` output on the user's computer after checks run.
- Live network access, native Windows execution, and installed Streamlit UI could not be independently executed from the audit environment; use the Windows self-check and inspect any FAIL results.

- Added optional offline smoke test mode (`QUANT_LAB_OFFLINE_SMOKE=1`) so the UI can be exercised without repeatedly contacting external feeds; regular app defaults unchanged.
- Added a local Streamlit HTTP startup check and 16-page AppTest render scan; these must run where Streamlit is installed (typically your Windows machine).
