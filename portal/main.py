import sys
from PySide6.QtWidgets import QApplication
from portal.ui import MainWindow
from portal.app import App

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    window.show()
    sys.exit(q_app.exec())
