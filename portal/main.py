import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QAction


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portal")
        self.resize(800, 600)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
