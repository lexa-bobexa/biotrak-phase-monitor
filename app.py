import streamlit as st
import pandas as pd
import tempfile
import os
import logging
import time
from datetime import datetime
from logic.file_operations import load_excel_file, validate_excel_content, find_id_column
from logic.data_processing import get_trials, save_results_to_excel
from logic.auth import login_page, signup_page, reset_password_page
from logic.monitoring import log_usage, show_admin_dashboard
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

def check_remember_me():
    """Check if the user has a valid remember me cookie."""
    if "remember_me" in st.session_state and "remember_me_expiry" in st.session_state:
        if time.time() < st.session_state["remember_me_expiry"]:
            return True
    return False

def main():
    # Initialize session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "show_signup" not in st.session_state:
        st.session_state["show_signup"] = False
    if "show_reset" not in st.session_state:
        st.session_state["show_reset"] = False

    # Check remember me cookie
    if not st.session_state["authenticated"] and check_remember_me():
        st.session_state["authenticated"] = True
        st.rerun()

    # Show appropriate page based on authentication state
    if not st.session_state["authenticated"]:
        if st.session_state["show_signup"]:
            signup_page()
        elif st.session_state["show_reset"]:
            reset_password_page()
        else:
            login_page()
        return

    # Header with logout button and admin dashboard link
    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
    with col1:
        st.title("Biotrak Phase Monitor")
    with col2:
        if st.session_state["role"] == "admin":
            if st.button("Admin Dashboard"):
                st.session_state["show_admin"] = True
                st.rerun()
    with col3:
        if st.button("Logout"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Show admin dashboard if requested
    if st.session_state.get("show_admin", False):
        show_admin_dashboard()
        if st.button("Back to Main"):
            st.session_state["show_admin"] = False
            st.rerun()
        return

    st.write(f"Welcome, {st.session_state['username']}!")
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

            if selected_sheets:
                # Initialize session state for processing
                if "processing" not in st.session_state:
                    st.session_state.processing = False
                if "cancel_processing" not in st.session_state:
                    st.session_state.cancel_processing = False

                # Create a container for the processing UI
                processing_container = st.container()
                
                # Start processing button
                if not st.session_state.processing:
                    if st.button("Process Selected Sheets"):
                        st.session_state.processing = True
                        st.session_state.cancel_processing = False
                        st.rerun()
                
                # Processing UI
                if st.session_state.processing:
                    with processing_container:
                        # Progress bar and status
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Add loading spinner
                        with st.spinner("Processing your data...this will take several minutes..."):
                            # Cancel button
                            if st.button("Cancel Processing"):
                                st.session_state.cancel_processing = True
                                st.rerun()
                            
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
                            start_time = time.time()
                            
                            for i, (sheet_name, df) in enumerate(selected_data.items()):
                                # Check for cancellation
                                if st.session_state.cancel_processing:
                                    st.warning("Processing cancelled by user")
                                    st.session_state.processing = False
                                    st.session_state.cancel_processing = False
                                    st.rerun()
                                
                                # Update progress
                                progress = (i + 1) / len(selected_data)
                                progress_bar.progress(progress)
                                status_text.text(f"Processing sheet {i+1} of {len(selected_data)}: {sheet_name}")
                                
                                if validation_results[sheet_name][0]:  # if sheet is valid
                                    try:
                                        # Find the ID column
                                        id_column = find_id_column(df.columns)
                                        if id_column is None:
                                            st.error(f"Could not find ID column in sheet: {sheet_name}. Please ensure the sheet contains either 'TC Scrape Number' or 'bioTRAK Product ID' column.")
                                            logging.error(f"Could not find ID column in sheet: {sheet_name}")
                                            continue
                                        
                                        # Process the sheet
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
                        
                        # Calculate processing time
                        processing_time = time.time() - start_time
                        
                        if results and not st.session_state.cancel_processing:
                            # Create output Excel file in memory
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                for sheet_name, result_df in results.items():
                                    result_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            # Generate timestamp for filename
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_filename = f"processed_trials_{timestamp}.xlsx"
                            
                            # Log successful processing with processing time
                            log_usage(st.session_state["username"], "processing_complete", {
                                "filename": uploaded_file.name,
                                "sheets_processed": len(results),
                                "total_sheets": len(selected_sheets),
                                "processing_time": processing_time
                            })
                            
                            # Provide download button
                            st.success(f"Processing complete in {processing_time:.2f} seconds! Click below to download your results.")
                            st.download_button(
                                label="Download Results",
                                data=output.getvalue(),
                                file_name=output_filename,
                                mime="application/vnd.ms-excel"
                            )
                        elif not st.session_state.cancel_processing:
                            st.warning("No valid results were generated from the processing.")
                        
                        # Reset processing state
                        st.session_state.processing = False
                        st.session_state.cancel_processing = False

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