from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap
from PySide6.QtCore import Qt
from .canvas import Canvas


class MainWindow(QMainWindow):
    COLORS = [
        "#FFFFFF", "#000000", "#FF0000", "#00FF00", "#0000FF", "#FFFF00",
        "#FF00FF", "#00FFFF", "#FF8000", "#8000FF", "#0080FF", "#FF0080",
        "#80FF00", "#00FF80", "#800000", "#008000", "#000080", "#808000",
        "#800080", "#008080"
    ]

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

        # Status bar
        status_bar = self.statusBar()
        self.cursor_pos_label = QLabel("Cursor: (0, 0)")
        self.selected_tool_label = QLabel("Tool: Pen")
        self.zoom_level_label = QLabel("Zoom: 100%")
        self.pen_color_label = QLabel(f"Color: {self.app.pen_color.name()}")
        status_bar.addWidget(self.cursor_pos_label)
        status_bar.addWidget(self.selected_tool_label)
        status_bar.addWidget(self.zoom_level_label)
        status_bar.addWidget(self.pen_color_label)

        # Connect signals
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)
        self.canvas.zoom_changed.connect(self.update_zoom_level_label)
        self.app.tool_changed.connect(self.update_selected_tool_label)
        self.app.pen_color_changed.connect(self.update_pen_color_label)

        # Toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        pen_action = QAction(QIcon("icons/toolpen.png"), "Pen", self)
        pen_action.triggered.connect(lambda: self.app.set_tool("Pen"))
        toolbar.addAction(pen_action)

        # Color Swatch Panel
        color_toolbar = QToolBar("Colors")
        self.addToolBar(Qt.RightToolBarArea, color_toolbar)
        color_toolbar.setAllowedAreas(Qt.LeftToolBarArea | Qt.RightToolBarArea)

        color_container = QWidget()
        color_layout = QGridLayout(color_container)
        color_layout.setSpacing(0)
        color_layout.setContentsMargins(0, 0, 0, 0)

        for i, color in enumerate(self.COLORS):
            button = QPushButton()
            button.setFixedSize(24, 24)
            button.setStyleSheet(f"background-color: {color}")
            button.setToolTip(color)
            button.clicked.connect(lambda c=color: self.app.set_pen_color(c))
            row = i % 10
            col = i // 10
            color_layout.addWidget(button, row, col)

        color_toolbar.addWidget(color_container)

    def update_cursor_pos_label(self, pos):
        self.cursor_pos_label.setText(f"Cursor: ({pos.x()}, {pos.y()})")

    def update_zoom_level_label(self, zoom):
        self.zoom_level_label.setText(f"Zoom: {zoom:.2f}")

    def update_selected_tool_label(self, tool):
        self.selected_tool_label.setText(f"Tool: {tool}")

    def update_pen_color_label(self, color):
        self.pen_color_label.setText(f"Color: {color.name()}")
