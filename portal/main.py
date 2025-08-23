import sys
from PySide6.QtWidgets import QApplication
from .ui import MainWindow
from .app import App

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    app = App()
    window = MainWindow(app)
    app.set_window(window)
    window.show()
    sys.exit(q_app.exec())
