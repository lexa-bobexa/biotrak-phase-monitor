from io import BytesIO

import pandas as pd

from logic.file_operations import find_id_column, load_excel_file, validate_excel_content


def _build_workbook_bytes(sheet_mapping):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheet_mapping.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def test_load_excel_file_from_bytes():
    workbook_bytes = _build_workbook_bytes(
        {
            "SheetA": pd.DataFrame(
                {
                    "bioTRAK Product ID": ["A-1"],
                    "Product Name": ["Drug A"],
                    "Original Phase": ["Phase 2"],
                }
            )
        }
    )
    sheets = load_excel_file(workbook_bytes)
    assert list(sheets.keys()) == ["SheetA"]
    assert sheets["SheetA"].iloc[0]["Product Name"] == "Drug A"


def test_validate_excel_content_with_missing_required_column():
    sheets = {
        "SheetA": pd.DataFrame(
            {
                "TC Scrape Number": [101],
                "Product Name": ["Drug A"],
            }
        )
    }
    required_map = {"SheetA": ["Product Name", "Original Phase"]}
    validation = validate_excel_content(sheets, required_map)

    assert validation["SheetA"][0] is False
    assert "Original Phase" in validation["SheetA"][1]


def test_find_id_column_prefers_tc_scrape_number():
    columns = ["Name", "TC Scrape Number (duplicate)", "bioTRAK Product ID"]
    assert find_id_column(columns) == "TC Scrape Number (duplicate)"
