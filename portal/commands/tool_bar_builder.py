import functools
from PySide6.QtWidgets import QToolBar, QLabel, QSlider, QToolButton, QMenu
from PySide6.QtGui import QPixmap, QIcon, QAction, QActionGroup
from PySide6.QtCore import Qt
from portal.ui.color_button import ActiveColorButton

class ToolBarBuilder:
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.action_manager = main_window.action_manager
        self.top_toolbar = None
        self.left_toolbar = None

    def setup_toolbars(self):
        self._setup_top_toolbar()
        self._setup_left_toolbar()

    def _setup_top_toolbar(self):
        self.top_toolbar = QToolBar("Top Toolbar")
        self.main_window.addToolBar(Qt.TopToolBarArea, self.top_toolbar)

        self.top_toolbar.addAction(self.action_manager.new_action)
        self.top_toolbar.addAction(self.action_manager.open_action)
        self.top_toolbar.addAction(self.action_manager.save_action)
        self.top_toolbar.addSeparator()

        # Brush size slider
        brush_icon = QLabel()
        pixmap = QPixmap("icons/brush.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        brush_icon.setPixmap(pixmap)
        self.top_toolbar.addWidget(brush_icon)

        self.main_window.pen_width_label = QLabel(f"{self.app.drawing_context.pen_width:02d}")
        self.top_toolbar.addWidget(self.main_window.pen_width_label)

        self.main_window.pen_width_slider = QSlider(Qt.Horizontal)
        self.main_window.pen_width_slider.setRange(1, 64)
        self.main_window.pen_width_slider.setValue(self.app.drawing_context.pen_width)
        self.main_window.pen_width_slider.setMinimumWidth(32)
        self.main_window.pen_width_slider.setMaximumWidth(100)
        self.main_window.pen_width_slider.setSingleStep(1)
        self.main_window.pen_width_slider.setPageStep(1)
        self.main_window.pen_width_slider.valueChanged.connect(self.app.drawing_context.set_pen_width)
        self.top_toolbar.addWidget(self.main_window.pen_width_slider)

        self.action_manager.circular_brush_action.setChecked(self.app.drawing_context.brush_type == "Circular")
        self.action_manager.circular_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Circular"))
        self.top_toolbar.addAction(self.action_manager.circular_brush_action)

        self.action_manager.square_brush_action.setChecked(self.app.drawing_context.brush_type == "Square")
        self.action_manager.square_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Square"))
        self.top_toolbar.addAction(self.action_manager.square_brush_action)

        self.action_manager.pattern_brush_action.setChecked(self.app.drawing_context.brush_type == "Pattern")
        self.action_manager.pattern_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Pattern"))
        self.top_toolbar.addAction(self.action_manager.pattern_brush_action)

        self.top_toolbar.addSeparator()

        self.top_toolbar.addAction(self.action_manager.mirror_x_action)
        self.top_toolbar.addAction(self.action_manager.mirror_y_action)

        self.top_toolbar.addSeparator()

        self.action_manager.grid_action.triggered.connect(self.main_window.canvas.toggle_grid)
        self.top_toolbar.addAction(self.action_manager.grid_action)

    def _setup_left_toolbar(self):
        self.left_toolbar = QToolBar("Tools")
        self.main_window.addToolBar(Qt.LeftToolBarArea, self.left_toolbar)
        self.left_toolbar.layout().setAlignment(Qt.AlignLeft)

        active_color_button = ActiveColorButton(self.app.drawing_context)
        active_color_button.rightClicked.connect(self.main_window.add_color_to_palette)
        self.left_toolbar.addWidget(active_color_button)

        from portal.tools import registry

        tools = registry.get_tools()
        self.tool_actions = {}
        self.tool_action_group = QActionGroup(self.main_window)

        # Direct access tools (not shape or select)
        for tool in [t for t in tools if t["category"] not in ("shape", "select")]:
            action = QAction(QIcon(tool["icon"]), tool["name"], self.main_window)
            action.setCheckable(True)
            action.triggered.connect(
                functools.partial(self.app.drawing_context.set_tool, tool["name"])
            )
            button = QToolButton()
            button.setDefaultAction(action)
            self.left_toolbar.addWidget(button)
            self.tool_actions[tool["name"]] = action
            self.tool_action_group.addAction(action)
            if tool["name"] == "Pen":
                action.setChecked(True)

        # Shape Tools
        shape_tools = [t for t in tools if t["category"] == "shape"]
        if shape_tools:
            self.main_window.shape_button = QToolButton(self.main_window)
            self.main_window.shape_button.setPopupMode(QToolButton.MenuButtonPopup)
            shape_menu = QMenu(self.main_window.shape_button)
            self.main_window.shape_button.setMenu(shape_menu)

            for idx, tool in enumerate(shape_tools):
                action = QAction(QIcon(tool["icon"]), tool["name"], self.main_window)
                action.setCheckable(True)
                action.triggered.connect(
                    functools.partial(self.app.drawing_context.set_tool, tool["name"])
                )
                shape_menu.addAction(action)
                self.tool_actions[tool["name"]] = action
                self.tool_action_group.addAction(action)
                if idx == 0:
                    self.main_window.shape_button.setDefaultAction(action)

            self.left_toolbar.addWidget(self.main_window.shape_button)

        # Selection Tools
        selection_tools = [t for t in tools if t["category"] == "select"]
        if selection_tools:
            self.main_window.selection_button = QToolButton(self.main_window)
            self.main_window.selection_button.setPopupMode(QToolButton.MenuButtonPopup)
            selection_menu = QMenu(self.main_window.selection_button)
            self.main_window.selection_button.setMenu(selection_menu)

            for idx, tool in enumerate(selection_tools):
                action = QAction(QIcon(tool["icon"]), tool["name"], self.main_window)
                action.setCheckable(True)
                action.triggered.connect(
                    functools.partial(self.app.drawing_context.set_tool, tool["name"])
                )
                selection_menu.addAction(action)
                self.tool_actions[tool["name"]] = action
                self.tool_action_group.addAction(action)
                if idx == 0:
                    self.main_window.selection_button.setDefaultAction(action)

            self.left_toolbar.addWidget(self.main_window.selection_button)

    def update_tool_buttons(self, tool_name):
        if tool_name in self.tool_actions:
            self.tool_actions[tool_name].setChecked(True)

        for action in self.main_window.shape_button.menu().actions():
            if action.text() == tool_name:
                self.main_window.shape_button.setDefaultAction(action)
                return

        for action in self.main_window.selection_button.menu().actions():
            if action.text() == tool_name:
                self.main_window.selection_button.setDefaultAction(action)
                return
