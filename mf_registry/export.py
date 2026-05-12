from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd


def rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    buffer = StringIO()
    dataframe.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")

