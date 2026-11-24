"""Read worksheet names without loading enormous macro-enabled workbooks into RAM."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def list_sheets(path: Path) -> list[str]:
    if path.suffix.lower() == ".xlsb":
        import pandas as pd
        return pd.ExcelFile(path, engine="calamine").sheet_names
    with ZipFile(path) as archive:
        tree = ET.fromstring(archive.read("xl/workbook.xml"))
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [sheet.attrib["name"] for sheet in tree.findall("x:sheets/x:sheet", namespace)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List tabs in xlsx/xlsm/xlsb workbook")
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    for number, name in enumerate(list_sheets(args.workbook), 1):
        print(f"{number:02d}. {name}")
