from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

class DragAndDropWidget(QLabel):
    file_dropped = pyqtSignal(str) # Define a signal with the dropped file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Drag and drop your Excel file here")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 2px dashed #aaa; padding: 10px;")
        self.file_path = None

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_path = urls[0].toLocalFile()
            if file_path.endswith((".xlsx", ".xls")):
                self.file_path = file_path
                self.setText(f"File: {file_path}")
                self.file_dropped.emit(file_path) # Emit the signal
            else:
                self.setText("Invalid file type. Please drop an Excel file.")
        else:
            event.ignore()

    def set_file_path(self, file_path):
        self.file_path = file_path
        self.setText(f"File: {file_path}")