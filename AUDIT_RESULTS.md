# Audit results (November 2026)

| Check | Result |
|---|---|
| Automated Python test suite | PASS — 28 passed |
| Python syntax compilation | PASS |
| Offline demo research report generation | PASS |
| Representative ETF rankings and moving-average backtest | PASS — synthetic data smoke check |
| Performance summary and Monte Carlo generation | PASS — synthetic data smoke check |
| Gross options gamma proxy | PASS — synthetic sample |
| Local import paths used by `app.py` | PASS — all `quantlab.*` source modules present |
| Obvious credential file patterns (`.env`, `.pem`, `.key`) | None in distribution |
| Complete Streamlit browser workflow | NOT VERIFIED — Streamlit not installed in this audit runtime |
| Yahoo / FRED live downloads | NOT VERIFIED — network data retrieval not tested |
| Windows batch execution and Mac LAN access | NOT VERIFIED — this audit ran on Linux |
| Model correctness against independent market reference data | NOT VERIFIED — tests cover examples and certain invariants only |

Passing tests does not certify trading performance, data rights, broker readiness, or institutional software quality.
