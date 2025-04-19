import streamlit as st
import pandas as pd
import tempfile
import os
import logging
from datetime import datetime
from logic.file_operations import load_excel_file, validate_excel_content, find_id_column
from logic.data_processing import get_trials, save_results_to_excel
from config import BASE_URL, EUROPEAN_COUNTRIES
from io import BytesIO

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configure the Streamlit page
st.set_page_config(
    page_title="Biotrak Phase Monitor",
    page_icon="📊",
    layout="wide"
)

def main():
    # Header
    st.title("Biotrak Phase Monitor")
    st.write("Upload your Excel file containing clinical trial details to process.")

    # File upload section
    uploaded_file = st.file_uploader(
        "Choose an Excel file", 
        type=['xlsx', 'xls'],
        help="Upload an Excel file containing trial information."
    )

    if uploaded_file is not None:
        # Create a temporary file to handle the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            # Load the Excel file
            sheets = load_excel_file(tmp_path)
            logging.info(f"Successfully loaded file with {len(sheets)} sheets")
            
            # Show available sheets
            st.success(f"File loaded successfully! Found {len(sheets)} sheets.")
            
            # Display sheet selection
            sheet_names = list(sheets.keys())
            selected_sheets = st.multiselect(
                "Select sheets to process",
                options=sheet_names,
                default=sheet_names,
                help="Choose which sheets you want to process"
            )

            if selected_sheets and st.button("Process Selected Sheets"):
                with st.spinner("Processing data... This may take a few minutes."):
                    # Filter selected sheets
                    selected_data = {sheet: sheets[sheet] for sheet in selected_sheets}
                    
                    # Define required columns for validation
                    required_columns_mapping = {
                        sheet_name: ["Product Name", "Original Phase"]
                        for sheet_name in selected_data.keys()
                    }

                    # Validate sheets
                    validation_results = validate_excel_content(selected_data, required_columns_mapping)
                    
                    # Process valid sheets
                    results = {}
                    progress_bar = st.progress(0)
                    
                    for i, (sheet_name, df) in enumerate(selected_data.items()):
                        if validation_results[sheet_name][0]:  # if sheet is valid
                            st.write(f"Processing sheet: {sheet_name}")
                            try:
                                # Find the ID column
                                id_column = find_id_column(df.columns)
                                if id_column is None:
                                    st.error(f"Could not find ID column in sheet: {sheet_name}. Please ensure the sheet contains either 'TC Scrape Number' or 'bioTRAK Product ID' column.")
                                    logging.error(f"Could not find ID column in sheet: {sheet_name}")
                                    continue
                                
                                # Process the sheet using your existing logic
                                trial_data = get_trials(df, id_column)
                                
                                # Convert the list of dictionaries to a DataFrame
                                if trial_data:  # Only create DataFrame if we have data
                                    results[sheet_name] = pd.DataFrame(trial_data)
                                    logging.info(f"Successfully processed sheet: {sheet_name}")
                                else:
                                    st.warning(f"No trial data found for sheet: {sheet_name}")
                                    logging.warning(f"No trial data found for sheet: {sheet_name}")
                            except Exception as e:
                                logging.error(f"Error processing sheet {sheet_name}: {str(e)}")
                                st.error(f"Error processing sheet {sheet_name}: {str(e)}")
                                continue
                            
                            progress_bar.progress((i + 1) / len(selected_data))
                    
                    if results:
                        # Create output Excel file in memory
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            for sheet_name, result_df in results.items():
                                result_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Generate timestamp for filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_filename = f"processed_trials_{timestamp}.xlsx"
                        
                        # Provide download button
                        st.success("Processing complete! Click below to download your results.")
                        st.download_button(
                            label="Download Results",
                            data=output.getvalue(),
                            file_name=output_filename,
                            mime="application/vnd.ms-excel"
                        )
                    else:
                        st.warning("No valid results were generated from the processing.")

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            logging.error(error_msg)
            st.error(error_msg)
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logging.warning(f"Failed to delete temporary file: {str(e)}")

if __name__ == "__main__":
    main() 