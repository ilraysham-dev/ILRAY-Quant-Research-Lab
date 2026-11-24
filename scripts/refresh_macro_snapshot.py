"""Retrieve real FRED macro data and save a provenance-stamped local snapshot.

Designed for daily Windows Task Scheduler execution. Historical data are latest
revised vintage and observation dates are NOT known-at-the-time release dates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantlab.macro_data import download_us_macro


def _atomic_bytes(destination: Path, data: bytes) -> None:
    """Prevent a failed refresh from replacing the last good snapshot."""
    descriptor, name = tempfile.mkstemp(dir=destination.parent, prefix=".macro_tmp_")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def refresh(out_dir: Path) -> dict:
    frame = download_us_macro()
    if len(frame) < 8 or frame[["GDP", "Inflation"]].isna().any().any():
        raise ValueError("Macro feed incomplete; existing snapshot preserved")
    now = dt.datetime.now(dt.timezone.utc)
    metadata = {
        "retrieved_at_utc": now.isoformat(),
        "source": "Federal Reserve Economic Data (FRED) public CSV",
        "series": {"GDP": "GDPC1", "Inflation": "CPIAUCSL"},
        "transform": "quarterly year-over-year percent change; CPI averaged by quarter",
        "data_vintage": "latest revised, NOT point-in-time or release-date aligned",
        "rows": len(frame),
        "last_observation_quarter": frame["Date"].iloc[-1].strftime("%Y-%m-%d"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(out_dir / "macro_latest.csv", frame.to_csv(index=False).encode("utf-8"))
    _atomic_bytes(out_dir / "macro_latest.json", json.dumps(metadata, indent=2).encode("utf-8"))
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "local_data")
    args = parser.parse_args()
    print(json.dumps(refresh(args.out_dir), indent=2))
