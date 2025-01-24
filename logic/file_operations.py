# logic/file_operations.py

import pandas as pd
import logging

def load_excel_file(file_path):
    """
    Load the Excel file and return its content as a dictionary of DataFrames.
    
    Args:
        file_path (str): Path to the Excel file.
    
    Returns:
        dict: A dictionary where keys are sheet names, and values are DataFrames.
    """
    try:
        sheets = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
        logging.info(f"Successfully loaded file: {file_path} with sheets: {list(sheets.keys())}")
        return sheets
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        raise ValueError(f"Could not load file: {e}")
    
def validate_excel_content(sheets, required_columns_mapping):
    """
    Validate the content of multiple Excel sheets, ensuring at least one ID column is present 
    and performing substring matching for column names.

    Args:
        sheets (dict): A dictionary where keys are sheet names, and values are DataFrames.
        required_columns_mapping (dict): A mapping of sheet names to their required columns.

    Returns:
        dict: A dictionary where keys are sheet names, and values are tuples (is_valid, message).
    """
    validation_results = {}

    for sheet_name, df in sheets.items():
        required_columns = required_columns_mapping.get(sheet_name, [])
        df_columns = df.columns.tolist()

        # Ensure at least one of the required ID columns (with substring matching) is present
        id_columns = ["bioTRAK Product ID", "TC Scrape Number"]
        matching_id_columns = [
            col for col in df_columns if any(required_id in col for required_id in id_columns)
        ]

        if not matching_id_columns:
            validation_results[sheet_name] = (
                False,
                f"Sheet '{sheet_name}' must contain at least one of the following columns: {', '.join(id_columns)}"
            )
            continue

        # Check for other required columns with substring matching
        required_non_id_columns = [col for col in required_columns if col not in id_columns]
        missing_columns = [
            col for col in required_non_id_columns
            if not any(required_col in actual_col for actual_col in df_columns for required_col in [col])
        ]
        if missing_columns:
            validation_results[sheet_name] = (
                False,
                f"Missing required columns: {', '.join(missing_columns)}"
            )
            continue

        # Validation passed
        validation_results[sheet_name] = (True, "File content is valid")

    return validation_results

def find_id_column(columns):
    """
    Find the relevant ID column in the given column names.
    Returns the matching column name if found, otherwise None.

    This function checks for either "TC Scrape Number" or "bioTRAK Product ID".
    If the column name contains additional text (e.g., "TC Scrape Number (Duplicates...)"),
    it will be matched as well.
    """
    for col in columns:
        if "TC Scrape Number" in col:
            return col
        elif "bioTRAK Product ID" in col:
            return col
    return None