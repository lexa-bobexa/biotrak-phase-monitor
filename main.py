from PyQt6.QtWidgets import QApplication
from ui.app_ui import MainApp  # Import the main UI class
import sys

def main():
    """Entry point for the application."""
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()