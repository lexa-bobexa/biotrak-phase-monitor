import io
import logging
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import pandas as pd

LOGGER = logging.getLogger(__name__)
ID_COLUMN_CANDIDATES = ("bioTRAK Product ID", "TC Scrape Number")


def load_excel_file(file_source: Any) -> Dict[str, pd.DataFrame]:
    """
    Load an Excel workbook into a dictionary of DataFrames.

    Accepts either a filesystem path, uploaded bytes, or a file-like object.
    """
    try:
        if isinstance(file_source, (bytes, bytearray)):
            workbook = io.BytesIO(file_source)
            source_label = "uploaded bytes"
        else:
            workbook = file_source
            source_label = str(file_source)

        sheets = pd.read_excel(workbook, sheet_name=None)
        LOGGER.info("Loaded workbook '%s' with sheets: %s", source_label, list(sheets.keys()))
        return sheets
    except Exception as exc:
        LOGGER.error("Failed to load workbook '%s': %s", file_source, exc)
        raise ValueError(f"Could not load file: {exc}") from exc


def validate_excel_content(
    sheets: Mapping[str, pd.DataFrame],
    required_columns_mapping: Mapping[str, Iterable[str]],
) -> Dict[str, Tuple[bool, str]]:
    """
    Validate workbook sheets with flexible substring matching on required columns.
    """
    validation_results: Dict[str, Tuple[bool, str]] = {}

    for sheet_name, dataframe in sheets.items():
        required_columns = list(required_columns_mapping.get(sheet_name, []))
        dataframe_columns = dataframe.columns.tolist()

        matching_id_columns = [
            column
            for column in dataframe_columns
            if any(required_id in column for required_id in ID_COLUMN_CANDIDATES)
        ]
        if not matching_id_columns:
            validation_results[sheet_name] = (
                False,
                (
                    f"Sheet '{sheet_name}' must contain at least one of the following "
                    f"columns: {', '.join(ID_COLUMN_CANDIDATES)}"
                ),
            )
            continue

        required_non_id_columns = [
            column for column in required_columns if column not in ID_COLUMN_CANDIDATES
        ]
        missing_columns = [
            required_column
            for required_column in required_non_id_columns
            if not any(required_column in actual_column for actual_column in dataframe_columns)
        ]
        if missing_columns:
            validation_results[sheet_name] = (
                False,
                f"Missing required columns: {', '.join(missing_columns)}",
            )
            continue

        validation_results[sheet_name] = (True, "File content is valid")

    return validation_results


def find_id_column(columns: Iterable[str]) -> Optional[str]:
    """
    Return the first matching ID column candidate from a list of columns.
    """
    for column in columns:
        if "TC Scrape Number" in column:
            return column
        if "bioTRAK Product ID" in column:
            return column
    return None