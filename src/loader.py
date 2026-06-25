from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from .constants import EXPECTED_COLUMNS


def _read_csv_with_encodings(source: str | bytes | Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            if isinstance(source, bytes):
                buffer = io.BytesIO(source)
                return pd.read_csv(buffer, encoding=encoding, dtype=str, keep_default_na=False, engine="python")
            return pd.read_csv(source, encoding=encoding, dtype=str, keep_default_na=False, engine="python")
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError("Не удалось прочитать CSV.")


def load_calls_csv(source: str | bytes | Path) -> pd.DataFrame:
    df = _read_csv_with_encodings(source)
    df.columns = [str(column).strip() for column in df.columns]
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "Структура файла не совпадает с ожидаемой. "
            f"Не найдены колонки: {', '.join(missing)}."
        )
    return df