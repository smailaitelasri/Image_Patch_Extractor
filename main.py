import sys

# =============================
# app/main.py
# =============================
from PyQt5.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    """
    Initializes and runs the PyQt5 application.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Patch Extractor")
    app.setOrganizationName("Smail Ait El Asri")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
