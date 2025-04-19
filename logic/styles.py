"""CSS styles for the Biotrak Phase Monitor application."""

# Main application styles
MAIN_STYLES = """
    <style>
    .main {
        padding: 2rem;
        background-color: #0E1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: 600;
        background-color: #1E88E5;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .stProgress > div > div > div > div {
        background-color: #1E88E5;
    }
    .stAlert {
        border-radius: 5px;
        background-color: #262730;
    }
    .upload-section {
        background-color: #262730;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border: 1px solid #333;
    }
    .header-section {
        margin-bottom: 2rem;
    }
    /* Dark mode specific styles */
    .stMarkdown {
        color: #FAFAFA;
    }
    .stTextInput>div>div>input {
        background-color: #262730;
        color: #FAFAFA;
    }
    .stSelectbox>div>div>select {
        background-color: #262730;
        color: #FAFAFA;
    }
    .stFileUploader>div>div>div>div {
        background-color: #262730;
        color: #FAFAFA;
    }
    .stMultiSelect>div>div>div>div {
        background-color: #262730;
        color: #FAFAFA;
    }
    .success-message {
        background-color: #1B5E20;
        color: #FAFAFA;
    }
    .warning-message {
        background-color: #E65100;
        color: #FAFAFA;
    }
    .error-message {
        background-color: #B71C1C;
        color: #FAFAFA;
    }
    </style>
"""

# Processing section styles
PROCESSING_STYLES = """
    <div style='background-color: #262730; padding: 2rem; border-radius: 10px; margin: 2rem 0; border: 1px solid #333;'>
        <h3>Processing Data</h3>
        <p style='color: #B0B0B0;'>This may take several minutes. Please wait...</p>
    </div>
"""

# Ready to process styles
READY_STYLES = """
    <div style='margin: 2rem 0;'>
        <h3>Ready to Process</h3>
        <p style='color: #666;'>Selected {sheets_count} sheets for processing</p>
    </div>
"""

# Success message styles
SUCCESS_STYLES = """
    <div class="success-message" style='padding: 2rem; border-radius: 10px; margin: 2rem 0;'>
        <h3>Processing Complete! 🎉</h3>
        <p>Your data has been processed successfully in {processing_time:.2f} seconds.</p>
    </div>
"""

# Progress status styles
PROGRESS_STATUS_STYLES = """
    <div style='margin: 1rem 0;'>
        <p style='color: #666;'>Processing sheet {current} of {total}</p>
        <p style='font-weight: bold;'>{sheet_name}</p>
    </div>
""" 