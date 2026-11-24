"""Read/write validation for local macro observations, never a trade signal."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd


def load_snapshot(folder: Path) -> tuple[pd.DataFrame, dict]:
    """Return the last successfully saved FRED snapshot and its provenance."""
    folder = Path(folder)
    csv_path, meta_path = folder / "macro_latest.csv", folder / "macro_latest.json"
    if not csv_path.is_file() or not meta_path.is_file():
        raise FileNotFoundError("No scheduled macro snapshot found")
    frame = pd.read_csv(csv_path, parse_dates=["Date"])
    if not {"Date", "GDP", "Inflation"}.issubset(frame):
        raise ValueError("Macro snapshot missing Date, GDP or Inflation")
    for column in ("GDP", "Inflation"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame.empty or frame[["GDP", "Inflation"]].isna().any().any():
        raise ValueError("Macro snapshot contains incomplete observations")
    if not frame["Date"].is_monotonic_increasing or frame["Date"].duplicated().any():
        raise ValueError("Macro observation dates must be unique and ordered")
    return frame, json.loads(meta_path.read_text(encoding="utf-8"))
