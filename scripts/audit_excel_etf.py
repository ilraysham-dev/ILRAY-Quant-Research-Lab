"""Audit Excel ETF price coverage and identify masked missing-data returns.

No workbook writes, no macro execution, no recalculation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def audit(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="ETFs", engine="openpyxl")
    if "Date" not in raw:
        raise ValueError("Could not find a Date column in ETFs worksheet")
    dates = pd.to_datetime(raw["Date"], errors="coerce")
    columns = [name for name in raw.columns if isinstance(name, str)
               and name != "Date" and not name.endswith("%") and not name.startswith("$")
               and name not in {"ETF", "Regime", "Best", "Good", "Bad", "Worst"}]
    result = []
    for name in columns:
        values = pd.to_numeric(raw[name], errors="coerce")
        valid = values.gt(0) & dates.notna()
        if not valid.any():
            continue
        last = dates[valid].max()
        missing_after = ((dates > last) & values.isna()).sum()
        result.append({"Ticker": name, "Last price date": last,
                       "Valid observations": int(valid.sum()),
                       "Later rows without prices": int(missing_after)})
    return pd.DataFrame(result).sort_values("Last price date")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    print(audit(args.workbook).to_string(index=False))
    print("WARNING: Several Excel formulas use IFERROR(...,0); blank prices may be represented as zero returns.")
