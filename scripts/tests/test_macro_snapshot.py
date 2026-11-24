import json
import pandas as pd
import pytest

from quantlab.macro_snapshot import load_snapshot


def test_read_snapshot(tmp_path):
    pd.DataFrame({"Date": ["2026-01-01", "2026-04-01"], "GDP": [2.0, 2.2],
                  "Inflation": [3.0, 2.9]}).to_csv(tmp_path / "macro_latest.csv", index=False)
    (tmp_path / "macro_latest.json").write_text(json.dumps({"retrieved_at_utc": "2026-11-11T01:00:00+00:00"}))
    values, meta = load_snapshot(tmp_path)
    assert len(values) == 2
    assert meta["retrieved_at_utc"].startswith("2026")


def test_reject_missing_data(tmp_path):
    pd.DataFrame({"Date": ["2026-01-01"], "GDP": [2.0]}).to_csv(tmp_path / "macro_latest.csv", index=False)
    (tmp_path / "macro_latest.json").write_text("{}")
    with pytest.raises(ValueError, match="missing"):
        load_snapshot(tmp_path)
