import streamlit as st
import pandas as pd
import tempfile
import os
import time
from datetime import datetime
from logic.file_operations import load_excel_file, validate_excel_content, find_id_column
from logic.data_processing import get_trials
from logic.auth import login_page
from logic.monitoring import log_usage, show_admin_dashboard
from config import BASE_URL, EUROPEAN_COUNTRIES
from logic.logging_config import logger
from logic.session_manager import SessionManager
from logic.styles import MAIN_STYLES, PROCESSING_STYLES, READY_STYLES, SUCCESS_STYLES, PROGRESS_STATUS_STYLES
from io import BytesIO

# Configure the Streamlit page
st.set_page_config(
    page_title="Biotrak Phase Monitor",
    page_icon="📊",
    layout="wide"
)

# Apply main styles
st.markdown(MAIN_STYLES, unsafe_allow_html=True)

def main():
    # Initialize session state
    SessionManager.initialize_session_state()

    # Check remember me cookie
    if not SessionManager.get_state("authenticated") and SessionManager.check_remember_me():
        SessionManager.set_state("authenticated", True)
        st.rerun()

    # Show appropriate page based on authentication state
    if not SessionManager.get_state("authenticated"):
        login_page()
        return

    # Add help/documentation section to sidebar
    with st.sidebar.expander("📚 Help & Documentation", expanded=False):
        st.markdown("""
        ### Getting Started
        
        **Input File Requirements:**
        - Excel file with columns:
          - 'Product Name'
          - 'Original Phase'
          - Your specified ID column
        
        **Features:**
        - Fetches clinical trial data from ClinicalTrials.gov
        - Filters trials in US, Canada, and European countries
        - Caches API responses for faster processing
        - Exports results to Excel with automatic duplicate removal
        
        **Output Includes:**
        - Product ID and name
        - Trial phase information
        - NCT number
        - Sponsor name
        - Trial status
        - Location information
        - Start and end dates
        - FDA regulation status
        - Conditions studied
        
        **Notes:**
        - API responses are cached for improved performance
        - Results are automatically filtered by region
        - Duplicate NCT numbers are removed from output
        """)

    # Header section with improved layout
    st.markdown('<div class="header-section">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
    with col1:
        st.title("Biotrak Phase Monitor")
        st.markdown("""
            <div style='color: #B0B0B0; font-size: 1.1em;'>
                Process and analyze clinical trial data efficiently
            </div>
        """, unsafe_allow_html=True)
    with col2:
        if SessionManager.get_state("role") == "admin":
            if SessionManager.get_state("show_admin"):
                if st.button("Back to Main", key="back_to_main"):
                    SessionManager.set_state("show_admin", False)
                    st.rerun()
            else:
                if st.button("Admin Dashboard", key="admin_dashboard"):
                    SessionManager.set_state("show_admin", True)
                    st.rerun()
    with col3:
        if st.button("Logout", key="logout"):
            SessionManager.clear_session()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Welcome message
    st.markdown(f"<h3 style='color: #FAFAFA;'>Welcome, {SessionManager.get_state('username')}! 👋</h3>", unsafe_allow_html=True)

    # Main content area
    if SessionManager.get_state("show_admin"):
        show_admin_dashboard()
    else:
        # File upload section
        st.markdown("### Upload Clinical Trial Data")
        st.markdown("Upload your Excel file containing clinical trial details for processing. Supported formats: .xlsx, .xls")
        
        uploaded_file = st.file_uploader(
            "Choose an Excel file", 
            type=['xlsx', 'xls'],
            help="Upload an Excel file containing trial information.",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            # Create a temporary file to handle the upload
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            try:
                # Load the Excel file
                sheets = load_excel_file(tmp_path)
                logger.info(f"Successfully loaded file with {len(sheets)} sheets")
                
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
                    # Start processing button with improved styling
                    if not SessionManager.get_state("processing"):
                        st.markdown(READY_STYLES.format(sheets_count=len(selected_sheets)), unsafe_allow_html=True)
                        if st.button("Start Processing", key="start_processing"):
                            SessionManager.set_state("processing", True)
                            st.rerun()
                    
                    # Processing UI with enhanced visual feedback
                    if SessionManager.get_state("processing"):
                        with st.container():
                            st.markdown(PROCESSING_STYLES, unsafe_allow_html=True)
                                
                            # Progress bar and status with improved styling
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Add loading spinner
                            with st.spinner("Processing your data...this will take several minutes"):
                                # Cancel button with improved styling
                                if st.button("Cancel Processing", key="cancel_processing"):
                                    SessionManager.set_state("processing", False)
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
                                    if not SessionManager.get_state("processing"):
                                        st.warning("Processing cancelled by user")
                                        st.rerun()
                                    
                                    # Update progress
                                    progress = (i + 1) / len(selected_data)
                                    progress_bar.progress(progress)
                                    status_text.markdown(
                                        PROGRESS_STATUS_STYLES.format(
                                            current=i+1,
                                            total=len(selected_data),
                                            sheet_name=sheet_name
                                        ),
                                        unsafe_allow_html=True
                                    )
                                    
                                    if validation_results[sheet_name][0]:  # if sheet is valid
                                        try:
                                            # Find the ID column
                                            id_column = find_id_column(df.columns)
                                            if id_column is None:
                                                st.error(f"Could not find ID column in sheet: {sheet_name}. Please ensure the sheet contains either 'TC Scrape Number' or 'bioTRAK Product ID' column.")
                                                logger.error(f"Could not find ID column in sheet: {sheet_name}")
                                                continue
                                            
                                            # Process the sheet
                                            trial_data = get_trials(df, id_column)
                                            
                                            # Convert the list of dictionaries to a DataFrame
                                            if trial_data:  # Only create DataFrame if we have data
                                                results[sheet_name] = pd.DataFrame(trial_data)
                                                logger.info(f"Successfully processed sheet: {sheet_name}")
                                            else:
                                                st.warning(f"No trial data found for sheet: {sheet_name}")
                                                logger.warning(f"No trial data found for sheet: {sheet_name}")
                                        except Exception as e:
                                            logger.error(f"Error processing sheet {sheet_name}: {str(e)}")
                                            st.error(f"Error processing sheet {sheet_name}: {str(e)}")
                                            continue
                        
                        # Calculate processing time
                        processing_time = time.time() - start_time
                        
                        if results and SessionManager.get_state("processing"):
                            # Create output Excel file in memory
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                for sheet_name, result_df in results.items():
                                    result_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            # Generate timestamp for filename
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_filename = f"processed_trials_{timestamp}.xlsx"
                            
                            # Log successful processing with processing time
                            log_usage(SessionManager.get_state("username"), "processing_complete", {
                                "filename": uploaded_file.name,
                                "sheets_processed": len(results),
                                "total_sheets": len(selected_sheets),
                                "processing_time": processing_time
                            })
                            
                            # Success message with improved styling
                            st.markdown(
                                SUCCESS_STYLES.format(processing_time=processing_time),
                                unsafe_allow_html=True
                            )
                            
                            # Download button with improved styling
                            st.download_button(
                                label="Download Results",
                                data=output.getvalue(),
                                file_name=output_filename,
                                mime="application/vnd.ms-excel",
                                key="download_results"
                            )
                        elif SessionManager.get_state("processing"):
                            st.warning("No valid results were generated from the processing.")
                        
                        # Reset processing state
                        SessionManager.set_state("processing", False)

            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {str(e)}")

if __name__ == "__main__":
    main() 