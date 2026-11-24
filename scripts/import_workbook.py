"""Extract one worksheet for review, without altering or evaluating the source model."""
import argparse
from pathlib import Path
import pandas as pd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export chosen Excel tab as CSV")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", required=True, help="Exact tab name")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=20000, help="Maximum sheet rows to import")
    args = parser.parse_args()
    engine = "calamine" if args.workbook.suffix.lower() == ".xlsb" else "openpyxl"
    data = pd.read_excel(args.workbook, sheet_name=args.sheet, engine=engine, nrows=args.rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False)
    print(f"Exported {len(data)} rows × {len(data.columns)} columns to {args.output}")
    print("Note: CSV contains cached cell VALUES, not VBA or native Excel formula logic.")
