import pandas as pd
from quantlab.engine import make_demo_data
from scripts.research_case_study import build_report


def test_report_discloses_synthetic_input_and_model_limits():
    prices, _ = make_demo_data()
    report = build_report(prices, "SYNTHETIC DEMONSTRATION", "SPY")
    assert "SYNTHETIC DEMO" in report
    assert "Next research steps" in report
    assert "buy-and-hold" in report.lower()
    assert "Missing prices" in report
