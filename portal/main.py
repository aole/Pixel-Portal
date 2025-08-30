import sys
from PySide6.QtWidgets import QApplication
from .ui import MainWindow
from .app import App

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    app = App()
    window = MainWindow(app)
    window.show()
    app.undo_stack_changed.emit()
    sys.exit(q_app.exec())
