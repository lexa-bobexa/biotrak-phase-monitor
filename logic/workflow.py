import logging
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from logic.data_processing import get_trials
from logic.file_operations import find_id_column, load_excel_file, validate_excel_content

LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = ["Product Name", "Original Phase"]


def _build_required_columns_mapping(sheets: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
    return {sheet_name: REQUIRED_COLUMNS for sheet_name in sheets.keys()}


def get_workbook_validation_report(file_bytes: bytes) -> Dict[str, object]:
    """
    Build a pre-run validation report suitable for UI rendering.
    """
    sheets = load_excel_file(file_bytes)
    if not sheets:
        raise ValueError("The uploaded workbook does not contain any sheets.")

    validation_results = validate_excel_content(sheets, _build_required_columns_mapping(sheets))
    report_rows: List[Dict[str, object]] = []

    for sheet_name, dataframe in sheets.items():
        is_valid, message = validation_results[sheet_name]
        report_rows.append(
            {
                "Sheet": sheet_name,
                "Rows": int(len(dataframe)),
                "Status": "Valid" if is_valid else "Invalid",
                "Message": message,
            }
        )

    valid_sheet_count = sum(1 for is_valid, _ in validation_results.values() if is_valid)
    non_empty_valid_sheet_count = sum(
        1
        for sheet_name, dataframe in sheets.items()
        if validation_results[sheet_name][0] and not dataframe.empty
    )

    return {
        "rows": report_rows,
        "total_sheets": len(sheets),
        "valid_sheets": valid_sheet_count,
        "non_empty_valid_sheets": non_empty_valid_sheet_count,
    }


def process_workbook(
    file_bytes: bytes,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    trial_end_cutoff_years: int = 8,
    include_unknown_end_dates: bool = True,
) -> Tuple[Dict[str, pd.DataFrame], List[str], Dict[str, int]]:
    """
    Validate and process an uploaded workbook into sheet-level trial results.
    """
    sheets = load_excel_file(file_bytes)
    if not sheets:
        raise ValueError("The uploaded workbook does not contain any sheets.")

    required_columns_mapping = _build_required_columns_mapping(sheets)
    validation_results = validate_excel_content(sheets, required_columns_mapping)

    valid_sheets: Dict[str, pd.DataFrame] = {
        sheet_name: sheets[sheet_name]
        for sheet_name, (is_valid, _) in validation_results.items()
        if is_valid
    }
    non_empty_sheets = {
        sheet_name: dataframe for sheet_name, dataframe in valid_sheets.items() if not dataframe.empty
    }
    if not non_empty_sheets:
        raise ValueError("No valid non-empty sheets were found in the uploaded file.")

    summary_messages: List[str] = []
    for sheet_name, (is_valid, message) in validation_results.items():
        prefix = "Validated" if is_valid else "Skipped"
        summary_messages.append(f"{prefix} '{sheet_name}': {message}")

    total_sheets = len(non_empty_sheets)
    results_dict: Dict[str, pd.DataFrame] = {}
    processed_sheets = 0
    skipped_missing_id = 0

    for sheet_position, (sheet_name, dataframe) in enumerate(non_empty_sheets.items(), start=1):
        id_column = find_id_column(dataframe.columns)
        if not id_column:
            LOGGER.warning("Skipping '%s' due to missing ID column", sheet_name)
            summary_messages.append(f"Skipped '{sheet_name}': missing ID column")
            skipped_missing_id += 1
            continue

        def _on_row_progress(percent_complete: int, message: str) -> None:
            if not progress_callback:
                return
            overall_progress = ((sheet_position - 1) + (percent_complete / 100.0)) / total_sheets
            progress_callback(min(max(overall_progress, 0.0), 1.0), f"{sheet_name}: {message}")

        LOGGER.info("Processing sheet '%s' with ID column '%s'", sheet_name, id_column)
        results = get_trials(
            dataframe,
            id_column,
            progress_callback=_on_row_progress,
            trial_end_cutoff_years=trial_end_cutoff_years,
            include_unknown_end_dates=include_unknown_end_dates,
        )
        results_dict[sheet_name] = pd.DataFrame(results)
        processed_sheets += 1

        if progress_callback:
            progress_callback(sheet_position / total_sheets, f"{sheet_name}: completed")

    if not results_dict:
        raise ValueError("No sheets produced results. Please verify workbook structure.")

    metrics = {
        "total_sheets": len(sheets),
        "valid_sheets": len(valid_sheets),
        "non_empty_valid_sheets": len(non_empty_sheets),
        "processed_sheets": processed_sheets,
        "skipped_missing_id": skipped_missing_id,
        "output_rows": int(sum(len(df.index) for df in results_dict.values())),
    }

    return results_dict, summary_messages, metrics
