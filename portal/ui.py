from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QAction
from .canvas import Canvas


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Portal")
        self.resize(800, 600)

        self.canvas = Canvas(self.app)
        self.setCentralWidget(self.canvas)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.app.exit)
        file_menu.addAction(exit_action)

        select_menu = menu_bar.addMenu("&Select")
        select_all_action = QAction("Select &All", self)
        select_all_action.triggered.connect(self.app.select_all)
        select_menu.addAction(select_all_action)
        select_none_action = QAction("Select &None", self)
        select_none_action.triggered.connect(self.app.select_none)
        select_menu.addAction(select_none_action)
