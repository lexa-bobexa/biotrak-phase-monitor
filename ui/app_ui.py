import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt
import logging
from ui.drag_and_drop_widget import DragAndDropWidget
from logic.file_operations import load_excel_file, validate_excel_content
from logic.data_processing import get_trials, load_interventions_from_excel, save_results_to_excel

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Biotrak Phase Monitor")
        self.setGeometry(100, 100, 600, 400)
        self.data = None # Holds the imported data

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Drag-and-Drop Widget
        self.drag_drop_widget = DragAndDropWidget(self)
        self.drag_drop_widget.file_dropped.connect(self.on_file_dropped)  # Connect the signal
        self.layout.addWidget(self.drag_drop_widget)

        # Browse Button
        self.browse_button = QPushButton("Browse File")
        self.browse_button.clicked.connect(self.browse_file)
        self.layout.addWidget(self.browse_button)

        # Import and Generate Buttons
        self.import_button = QPushButton("Import File")
        self.import_button.clicked.connect(self.import_file)
        self.layout.addWidget(self.import_button)

        self.generate_button = QPushButton("Generate Output")
        self.generate_button.clicked.connect(self.generate_output)
        self.layout.addWidget(self.generate_button)

        self.remove_button = QPushButton("Remove Selected File")
        self.remove_button.setToolTip("Click to remove the currently selected file.")
        self.remove_button.setEnabled(False)  # Initially disabled
        self.remove_button.clicked.connect(self.remove_selected_file)
        self.layout.addWidget(self.remove_button)

        # Status Label
        self.status_label = QLabel("Status: Ready")
        self.layout.addWidget(self.status_label)

    def on_file_dropped(self, file_path):
        """Handle the file dropped signal."""
        self.remove_button.setEnabled(True)  # Enable the remove button
        self.status_label.setText(f"File selected: {file_path}")
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            self.drag_drop_widget.set_file_path(file_path)
            self.status_label.setText(f"Status: Selected {file_path}")

    def import_file(self):
        """Handles the import file button click."""
        file_path = self.drag_drop_widget.file_path
        if not file_path:
            self.status_label.setText("Error: No input file selected")
            logging.warning("No input file selected")
            return

        try:
            # Load the Excel file
            self.data = load_excel_file(file_path)

            # Enable the remove button
            self.remove_button.setEnabled(True)

            # Show success message
            self.status_label.setText(f"Status: Successfully loaded file with sheets: {', '.join(self.data.keys())}")
            logging.info(f"Loaded file with sheets: {list(self.data.keys())}")

        except ValueError as e:
            self.status_label.setText(f"Error: {e}")
            logging.error(f"Failed to import file: {e}")


    def generate_output(self):
        """Generate the output based on the selected input file."""
        def find_id_column(columns):
            """Find the ID column in the given column names."""
            for col in columns:
                if "TC Scrape Number" in col:
                    return col
                elif "bioTRAK Product ID" in col:
                    return col
            return None
        file_path = self.drag_drop_widget.file_path
        if not file_path:
            self.status_label.setText("Error: No input file selected")
            logging.warning("No input file selected")
            return
        
        try:
            # Load the Excel file
            sheets = load_excel_file(file_path)

            # Define required columns for each sheet
            required_columns_mapping = {
                sheet_name: ["Product Name", "Original Phase"]
                for sheet_name in sheets.keys()
            }

            # Validate sheets
            validation_results = validate_excel_content(sheets, required_columns_mapping)

            # Consolidate error messages
            error_messages = [
                f"Error in sheet '{sheet}': {message}"
                for sheet, (is_valid, message) in validation_results.items()
                if not is_valid
            ]
            if error_messages:
                self.status_label.setText("\n".join(error_messages))
                logging.warning("Validation failed for some sheets")
                return
            
            # Process valid sheets
            valid_sheets = {sheet: sheets[sheet] for sheet, (is_valid, _) in validation_results.items() if is_valid}
            # Skip empty sheets
            valid_sheets = {sheet: df for sheet, df in valid_sheets.items() if not df.empty}
            if not valid_sheets:
                self.status_label.setText("Error: No valid sheets to process")
                logging.warning("All sheets are empty or invalid")
                return
            
            results_dict = {}
            for sheet_name, df_input in valid_sheets.items():
                # Dynamically determine the ID column using substring matching
                id_column = find_id_column(df_input.columns)
                if id_column is None:
                    logging.warning(f"Skipping sheet '{sheet_name}' due to missing ID column")
                    self.status_label.setText(f"Error: Sheet '{sheet_name}' is missing an ID column (Expected: 'bioTRAK Product ID or 'TC Scrape Number')")
                    continue

                logging.info(f"Processing sheet '{sheet_name}' with ID column '{id_column}'")
                results = get_trials(df_input, id_column)
                results_dict[sheet_name] = pd.DataFrame(results)

            # Ask user for output directory
            output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_directory:
                self.status_label.setText("Error: No output directory selected")
                logging.warning("No output directory selected")
                return

            # Save results to Excel
            save_results_to_excel(results_dict, output_directory, valid_sheets.keys())
            self.status_label.setText(f"Status: Output file generated successfully. \nProcessed {len(valid_sheets)} sheets.")
            logging.info("Output file generated successfully")

        except ValueError as e:
            self.status_label.setText(f"Error: {e}")
            logging.error(f"Failed to process file: {e}")

    def remove_selected_file(self):
        """Remove the selected file and reset the UI."""
        self.drag_drop_widget.setText("Drag and drop your Excel file here")
        self.drag_drop_widget.file_path = None
        self.data = None  # Clear any imported data
        self.status_label.setText("Status: File removed")
        self.remove_button.setEnabled(False)  # Disable the remove button
        logging.info("Selected file has been removed.")

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())