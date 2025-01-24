import os
import pandas as pd
from PyQt6.QtGui import QMovie, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
import logging
from ui.drag_and_drop_widget import DragAndDropWidget
from logic.file_operations import load_excel_file, validate_excel_content, find_id_column
from logic.data_processing import get_trials, save_results_to_excel

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

        # Initialize spinner in the UI setup
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center alignment
        self.spinner_movie = QMovie("assets/icons/Ripple@1x-1.0s-200px-200px.gif")
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.hide()  # Hide spinner initially
        self.layout.addWidget(self.spinner_label)

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
        self.generate_button.setEnabled(False) # Initally disabled
        self.generate_button.clicked.connect(self.generate_output)
        self.layout.addWidget(self.generate_button)

        self.remove_button = QPushButton("Remove Selected File")
        self.remove_button.setToolTip("Click to remove the currently selected file.")
        self.remove_button.setEnabled(False)  # Initially disabled
        self.remove_button.clicked.connect(self.remove_selected_file)
        self.layout.addWidget(self.remove_button)

        self.view_logs_button = QPushButton("View Logs")
        self.view_logs_button.setToolTip("Open the log file to view errors or messages.")
        self.view_logs_button.clicked.connect(self.view_logs)
        self.layout.addWidget(self.view_logs_button)

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

            # Enable the generate output and remove button
            self.remove_button.setEnabled(True)
            self.generate_button.setEnabled(True)

            # Show success message
            self.status_label.setText(f"Status: Successfully loaded file with sheets: {', '.join(self.data.keys())}")
            logging.info(f"Loaded file with sheets: {list(self.data.keys())}")

        except ValueError as e:
            self.status_label.setText(f"Error: {e}")
            logging.error(f"Failed to import file: {e}")

    def generate_output(self):
        """Generate the output based on the selected input file."""
        file_path = self.drag_drop_widget.file_path
        if not file_path:
            self.status_label.setText("Error: No input file selected")
            logging.warning("No input file selected")
            return
        
        # Ask user for output directory
        output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_directory:
            self.status_label.setText("Error: No output directory selected")
            logging.warning("No output directory selected")
            return
        
        # Show the spinner
        self.spinner_label.show()
        self.spinner_movie.start()
        self.status_label.setText("Status: Processing, please wait...")

        # Start the processing thread
        self.processing_thread = ProcessingThread(file_path, output_directory)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.error.connect(self.on_processing_error)
        self.processing_thread.start()
            
    def on_processing_finished(self):
        self.spinner_movie.stop()
        self.spinner_label.hide()
        self.status_label.setText("Status: Output file generated successfully")

    def on_processing_error(self, error_message):
        self.spinner_movie.stop()
        self.spinner_label.hide()
        self.status_label.setText(f"Error: {error_message}")
        logging.error(error_message)

    def remove_selected_file(self):
        """Remove the selected file and reset the UI."""
        self.drag_drop_widget.setText("Drag and drop your Excel file here")
        self.drag_drop_widget.file_path = None
        self.data = None  # Clear any imported data
        self.status_label.setText("Status: File removed")
        self.remove_button.setEnabled(False)  # Disable the remove button
        logging.info("Selected file has been removed.")

    def view_logs(self):
        """Open the log file in the user's default text editor."""
        log_path = os.path.abspath("app.log")
        if os.path.exists(log_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_path))
        else:
            self.status_label.setText("Error: Log file not found.")

class ProcessingThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # Emits (progress percentage, message)

    def __init__(self, file_path, output_directory):
        super().__init__()
        self.file_path = file_path
        self.output_directory = output_directory

    def run(self):
        try:
            logging.info(f"Processing file: {self.file_path}")

            # Load the excel file
            sheets = load_excel_file(self.file_path)
            if not sheets:
                raise ValueError("The Excel file does not contain any sheets.")

            # Define required columns for each sheet
            required_columns_mapping = {
                sheet_name: ["Product Name", "Original Phase"]
                for sheet_name in sheets.keys()
            }

            # Validate sheets
            validation_results = validate_excel_content(sheets, required_columns_mapping)
            # Filter valid sheets
            valid_sheets = {
                sheet_name: sheets[sheet_name] for sheet_name, (is_valid, _) in validation_results.items() if is_valid
            }
            # Filter non-empty sheets
            non_empty_sheets = {
                sheet: df for sheet, df in valid_sheets.items() if not df.empty
            }
            if not non_empty_sheets:
                raise ValueError("No valid sheets to process.")

            # Process valid sheets
            results_dict = {}
            total_sheets = len(non_empty_sheets)
            for i, (sheet_name, df_input) in enumerate(non_empty_sheets.items(), start=1):
                id_column = find_id_column(df_input.columns)
                if not id_column:
                    logging.warning(f"Skipping '{sheet_name}' due to missing ID column")
                    self.progress.emit(int(i / total_sheets * 100), f"Skipped sheet '{sheet_name}'")
                    continue

                logging.info(f"Processing sheet '{sheet_name}' with ID column '{id_column}'")
                results = get_trials(df_input, id_column)
                results_dict[sheet_name] = pd.DataFrame(results)
                self.progress.emit(int(i / total_sheets * 100), f"Processed sheet '{sheet_name}'")

            # Save results to excel
            save_results_to_excel(results_dict, self.output_directory, non_empty_sheets.keys())
            self.progress.emit(100, "Processing complete.")

        except Exception as e:
            self.error.emit(f"Error during processing: {e}")
            logging.error(f"Processing error: {e}")
        finally:
            self.finished.emit()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())