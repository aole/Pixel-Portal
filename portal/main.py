import sys
from PySide6.QtWidgets import QApplication
from portal.ui.ui import MainWindow
from portal.core.app import App

if __name__ == "__main__":
    q_app = QApplication(sys.argv)
    app = App()
    window = MainWindow(app)
    app.main_window = window
    window.show()
    app.undo_stack_changed.emit()
    sys.exit(q_app.exec())
