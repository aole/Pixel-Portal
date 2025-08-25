from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QKeySequence
from PySide6.QtCore import Qt
from .canvas import Canvas
from .layer_manager_widget import LayerManagerWidget
from .ai.dialog import AiDialog


class ColorButton(QPushButton):
    def __init__(self, color, app):
        super().__init__()
        self.color = color
        self.app = app
        self.setFixedSize(24, 24)
        self.setStyleSheet(f"background-color: {self.color}")
        self.setToolTip(self.color)
        self.clicked.connect(self.on_click)

    def on_click(self):
        self.app.set_pen_color(self.color)


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

        edit_menu = menu_bar.addMenu("&Edit")
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(self.app.undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut("Ctrl+Shift+Z")
        self.redo_action.triggered.connect(self.app.redo)
        edit_menu.addAction(self.redo_action)

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
        self.app.pen_width_changed.connect(self.update_pen_width_slider)
        self.app.undo_stack_changed.connect(self.update_undo_redo_actions)

        # Toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        top_toolbar = QToolBar("Top Toolbar")
        self.addToolBar(Qt.TopToolBarArea, top_toolbar)

        # Brush size slider
        top_toolbar.addWidget(QLabel("Brush Size:"))
        self.pen_width_slider = QSlider(Qt.Horizontal)
        self.pen_width_slider.setRange(1, 100)
        self.pen_width_slider.setValue(self.app.pen_width)
        self.pen_width_slider.setMinimumWidth(200)
        self.pen_width_slider.valueChanged.connect(self.app.set_pen_width)
        top_toolbar.addWidget(self.pen_width_slider)
        
        pen_action = QAction(QIcon("icons/toolpen.png"), "Pen", self)
        pen_action.triggered.connect(lambda: self.app.set_tool("Pen"))
        toolbar.addAction(pen_action)

        bucket_action = QAction(QIcon("icons/toolbucket.png"), "Bucket", self)
        bucket_action.triggered.connect(lambda: self.app.set_tool("Bucket"))
        toolbar.addAction(bucket_action)

        ai_action = QAction(QIcon("icons/NA.png"), "AI Image", self)
        ai_action.triggered.connect(self.open_ai_dialog)
        toolbar.addAction(ai_action)

        # Color Swatch Panel
        color_toolbar = QToolBar("Colors")
        self.addToolBar(Qt.BottomToolBarArea, color_toolbar)
        color_toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)

        color_container = QWidget()
        color_layout = QGridLayout(color_container)
        color_layout.setSpacing(0)
        color_layout.setContentsMargins(0, 0, 0, 0)

        colors = self.load_palette()
        for i, color in enumerate(colors):
            button = ColorButton(color, self.app)
            row = i % 2
            col = i // 2
            color_layout.addWidget(button, row, col)

        color_toolbar.addWidget(color_container)

        # Layer Manager Panel
        self.layer_manager_widget = LayerManagerWidget(self.app)
        self.layer_manager_widget.layer_changed.connect(self.canvas.update)
        dock_widget = QDockWidget("Layers", self)
        dock_widget.setWidget(self.layer_manager_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_widget)

    def load_palette(self):
        try:
            with open("palettes/default.colors", "r") as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            return []

    def update_cursor_pos_label(self, pos):
        self.cursor_pos_label.setText(f"Cursor: ({pos.x()}, {pos.y()})")

    def update_zoom_level_label(self, zoom):
        self.zoom_level_label.setText(f"Zoom: {int(zoom * 100)}%")

    def update_selected_tool_label(self, tool):
        self.selected_tool_label.setText(f"Tool: {tool}")

    def update_pen_color_label(self, color):
        self.pen_color_label.setText(f"Color: {color.name()}")

    def update_pen_width_slider(self, width):
        self.pen_width_slider.setValue(width)

    def update_undo_redo_actions(self):
        self.undo_action.setEnabled(len(self.app.undo_manager.undo_stack) > 1)
        self.redo_action.setEnabled(len(self.app.undo_manager.redo_stack) > 0)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "initial_zoom_set"):
            self.canvas.set_initial_zoom()
            self.initial_zoom_set = True

    def open_ai_dialog(self):
        dialog = AiDialog(self.app, self)
        dialog.exec()
