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

    def setup_toolbars(self):
        self._setup_top_toolbar()
        self._setup_left_toolbar()

    def _setup_top_toolbar(self):
        top_toolbar = QToolBar("Top Toolbar")
        self.main_window.addToolBar(Qt.TopToolBarArea, top_toolbar)

        top_toolbar.addAction(self.action_manager.new_action)
        top_toolbar.addAction(self.action_manager.open_action)
        top_toolbar.addAction(self.action_manager.save_action)
        top_toolbar.addSeparator()

        # Brush size slider
        brush_icon = QLabel()
        pixmap = QPixmap("icons/brush.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        brush_icon.setPixmap(pixmap)
        top_toolbar.addWidget(brush_icon)

        self.main_window.pen_width_label = QLabel(f"{self.app.drawing_context.pen_width:02d}")
        top_toolbar.addWidget(self.main_window.pen_width_label)

        self.main_window.pen_width_slider = QSlider(Qt.Horizontal)
        self.main_window.pen_width_slider.setRange(1, 64)
        self.main_window.pen_width_slider.setValue(self.app.drawing_context.pen_width)
        self.main_window.pen_width_slider.setMinimumWidth(32)
        self.main_window.pen_width_slider.setMaximumWidth(100)
        self.main_window.pen_width_slider.setSingleStep(1)
        self.main_window.pen_width_slider.setPageStep(1)
        self.main_window.pen_width_slider.valueChanged.connect(self.app.drawing_context.set_pen_width)
        top_toolbar.addWidget(self.main_window.pen_width_slider)

        self.action_manager.circular_brush_action.setChecked(self.app.drawing_context.brush_type == "Circular")
        self.action_manager.circular_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Circular"))
        top_toolbar.addAction(self.action_manager.circular_brush_action)

        self.action_manager.square_brush_action.setChecked(self.app.drawing_context.brush_type == "Square")
        self.action_manager.square_brush_action.triggered.connect(lambda: self.app.drawing_context.set_brush_type("Square"))
        top_toolbar.addAction(self.action_manager.square_brush_action)

        top_toolbar.addSeparator()

        top_toolbar.addAction(self.action_manager.mirror_x_action)
        top_toolbar.addAction(self.action_manager.mirror_y_action)

        top_toolbar.addSeparator()

        self.action_manager.grid_action.triggered.connect(self.main_window.canvas.toggle_grid)
        top_toolbar.addAction(self.action_manager.grid_action)

    def _setup_left_toolbar(self):
        toolbar = QToolBar("Tools")
        self.main_window.addToolBar(Qt.LeftToolBarArea, toolbar)
        toolbar.layout().setAlignment(Qt.AlignLeft)

        active_color_button = ActiveColorButton(self.app.drawing_context)
        toolbar.addWidget(active_color_button)

        from portal.tools import get_tools
        tools = get_tools()
        self.tool_actions = {}
        self.tool_action_group = QActionGroup(self.main_window)

        for tool in tools:
            if tool.name in ["Line", "Rectangle", "Ellipse", "Select Rectangle", "Select Circle", "Select Lasso", "Select Color"]:
                continue

            action = QAction(QIcon(tool.icon), tool.name, self.main_window)
            action.setCheckable(True)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            button = QToolButton()
            button.setDefaultAction(action)
            toolbar.addWidget(button)
            self.tool_actions[tool.name] = action
            self.tool_action_group.addAction(action)
            if tool.name == "Pen":
                action.setChecked(True)

        # Shape Tools
        self.main_window.shape_button = QToolButton(self.main_window)
        self.main_window.shape_button.setIcon(QIcon("icons/toolline.png"))
        self.main_window.shape_button.setPopupMode(QToolButton.MenuButtonPopup)
        shape_menu = QMenu(self.main_window.shape_button)
        self.main_window.shape_button.setMenu(shape_menu)

        shape_tools = [tool for tool in tools if tool.name in ["Line", "Rectangle", "Ellipse"]]
        for tool in shape_tools:
            action = QAction(QIcon(tool.icon), tool.name, self.main_window)
            action.setCheckable(True)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            shape_menu.addAction(action)
            self.tool_actions[tool.name] = action
            self.tool_action_group.addAction(action)
            if tool.name == "Line":
                self.main_window.shape_button.setDefaultAction(action)

        toolbar.addWidget(self.main_window.shape_button)

        # Selection Tools
        self.main_window.selection_button = QToolButton(self.main_window)
        self.main_window.selection_button.setIcon(QIcon("icons/toolselectrect.png"))
        self.main_window.selection_button.setPopupMode(QToolButton.MenuButtonPopup)
        selection_menu = QMenu(self.main_window.selection_button)
        self.main_window.selection_button.setMenu(selection_menu)

        selection_tools = [tool for tool in tools if tool.name in ["Select Rectangle", "Select Circle", "Select Lasso", "Select Color"]]
        for tool in selection_tools:
            action = QAction(QIcon(tool.icon), tool.name, self.main_window)
            action.setCheckable(True)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            selection_menu.addAction(action)
            self.tool_actions[tool.name] = action
            self.tool_action_group.addAction(action)
            if tool.name == "Select Rectangle":
                self.main_window.selection_button.setDefaultAction(action)

        toolbar.addWidget(self.main_window.selection_button)

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
