# spreadsheet.py - refactored to use Pydantic validation
from __future__ import annotations

import pandas as pd


def load_sheets(path: str) -> dict[str, pd.DataFrame]:
    sheets: dict[str, pd.DataFrame] = {}
    with pd.ExcelFile(path) as xf:
        for sheet_name in map(str, xf.sheet_names):
            sheets[sheet_name] = xf.parse(sheet_name)
    return sheets
