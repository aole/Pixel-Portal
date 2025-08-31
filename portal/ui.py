import functools
from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QMenu, QToolButton, QVBoxLayout
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QKeySequence
from PySide6.QtCore import Qt, Slot
from .canvas import Canvas
from .layer_manager_widget import LayerManagerWidget
from .ai_panel import AIPanel
from .new_file_dialog import NewFileDialog
from .resize_dialog import ResizeDialog
from .background import Background
from .palette_dialog import PaletteDialog
from .preview_panel import PreviewPanel
from .action_manager import ActionManager

from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QColorDialog


class ColorButton(QPushButton):
    def __init__(self, color, drawing_context):
        super().__init__()
        self.drawing_context = drawing_context
        self.setFixedSize(24, 24)
        self.clicked.connect(self.on_click)
        self.set_color(color)

    def set_color(self, color):
        if isinstance(color, QColor):
            self.color = color.name()
        else:
            self.color = color
        self.setStyleSheet(f"background-color: {self.color}")
        self.setToolTip(self.color)

    def on_click(self):
        self.drawing_context.set_pen_color(self.color)


class ActiveColorButton(QPushButton):
    def __init__(self, drawing_context):
        super().__init__()
        self.drawing_context = drawing_context
        self.setFixedSize(24, 24)
        self.clicked.connect(self.on_click)
        self.update_color(self.drawing_context.pen_color)
        self.drawing_context.pen_color_changed.connect(self.update_color)

    def on_click(self):
        color = QColorDialog.getColor(self.drawing_context.pen_color, self)
        if color.isValid():
            self.drawing_context.set_pen_color(color)

    def update_color(self, color):
        self.setStyleSheet(f"background-color: {color.name()}")
        self.setToolTip(color.name())


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Pixel Portal")
        self.resize(1200, 800)

        self.action_manager = ActionManager(self)

        self.main_palette_buttons = []
        self.saturation_buttons = []
        self.value_buttons = []

        self.canvas = Canvas(self.app.drawing_context)
        self.setCentralWidget(self.canvas)
        self.canvas.set_document(self.app.document)

        # Connect DrawingContext signals to Canvas slots
        self.app.drawing_context.tool_changed.connect(self.canvas.on_tool_changed)

        # Connect Canvas signal to App and UI slots
        self.canvas.command_generated.connect(self.app.handle_command)
        self.canvas.command_generated.connect(self.handle_canvas_message)

        self.action_manager.setup_actions(self.canvas)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_manager.new_action)
        file_menu.addAction(self.action_manager.open_action)
        file_menu.addAction(self.action_manager.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action_manager.load_palette_action)
        file_menu.addAction(self.action_manager.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_manager.undo_action)
        edit_menu.addAction(self.action_manager.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.paste_as_new_layer_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_manager.clear_action)

        select_menu = menu_bar.addMenu("&Select")
        select_menu.addAction(self.action_manager.select_all_action)
        select_menu.addAction(self.action_manager.select_none_action)
        select_menu.addAction(self.action_manager.invert_selection_action)

        image_menu = menu_bar.addMenu("&Image")
        image_menu.addAction(self.action_manager.resize_action)
        image_menu.addAction(self.action_manager.crop_action)
        image_menu.addSeparator()
        image_menu.addAction(self.action_manager.flip_horizontal_action)
        image_menu.addAction(self.action_manager.flip_vertical_action)

        view_menu = menu_bar.addMenu("&View")
        background_menu = view_menu.addMenu("&Background")
        background_menu.addAction(self.action_manager.checkered_action)
        background_menu.addSeparator()
        background_menu.addAction(self.action_manager.white_action)
        background_menu.addAction(self.action_manager.black_action)
        background_menu.addAction(self.action_manager.gray_action)
        background_menu.addAction(self.action_manager.magenta_action)
        background_menu.addSeparator()
        background_menu.addAction(self.action_manager.custom_color_action)

        view_menu.addSeparator()
        view_menu.addAction(self.action_manager.ai_action)

        # Status bar
        status_bar = self.statusBar()
        self.cursor_pos_label = QLabel("Cursor: (0, 0)")
        self.selected_tool_label = QLabel("Tool: Pen")
        self.zoom_level_label = QLabel("Zoom: 100%")
        self.selection_size_label = QLabel("")
        status_bar.addWidget(self.cursor_pos_label)
        status_bar.addWidget(self.selected_tool_label)
        status_bar.addWidget(self.zoom_level_label)
        status_bar.addWidget(self.selection_size_label)

        # Connect signals
        self.canvas.cursor_pos_changed.connect(self.update_cursor_pos_label)
        self.canvas.zoom_changed.connect(self.update_zoom_level_label)
        self.canvas.selection_changed.connect(self.update_crop_action_state)
        self.app.drawing_context.tool_changed.connect(self.update_selected_tool_label)
        self.app.drawing_context.tool_changed.connect(self.update_tool_buttons)
        self.canvas.selection_size_changed.connect(self.update_selection_size_label)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_slider)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_label)
        self.app.undo_stack_changed.connect(self.update_undo_redo_actions)
        self.app.drawing_context.pen_color_changed.connect(self.update_dynamic_palette)
        self.app.drawing_context.brush_type_changed.connect(self.update_brush_button)

        # Toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        toolbar.layout().setAlignment(Qt.AlignLeft)

        top_toolbar = QToolBar("Top Toolbar")
        self.addToolBar(Qt.TopToolBarArea, top_toolbar)

        top_toolbar.addAction(self.action_manager.new_action)
        top_toolbar.addAction(self.action_manager.open_action)
        top_toolbar.addAction(self.action_manager.save_action)
        top_toolbar.addSeparator()

        # Brush size slider
        brush_icon = QLabel()
        pixmap = QPixmap("icons/brush.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        brush_icon.setPixmap(pixmap)
        top_toolbar.addWidget(brush_icon)
        
        self.pen_width_label = QLabel(f"{self.app.drawing_context.pen_width:02d}")
        top_toolbar.addWidget(self.pen_width_label)

        self.pen_width_slider = QSlider(Qt.Horizontal)
        self.pen_width_slider.setRange(1, 64)
        self.pen_width_slider.setValue(self.app.drawing_context.pen_width)
        self.pen_width_slider.setMinimumWidth(32)
        self.pen_width_slider.setMaximumWidth(100)
        self.pen_width_slider.setSingleStep(1)
        self.pen_width_slider.setPageStep(1)
        self.pen_width_slider.valueChanged.connect(self.app.drawing_context.set_pen_width)
        top_toolbar.addWidget(self.pen_width_slider)

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

        self.action_manager.grid_action.triggered.connect(self.canvas.toggle_grid)
        top_toolbar.addAction(self.action_manager.grid_action)
        
        active_color_button = ActiveColorButton(self.app.drawing_context)
        toolbar.addWidget(active_color_button)
        
        from .tools import get_tools
        tools = get_tools()
        for tool in tools:
            if tool.name in ["Line", "Rectangle", "Ellipse", "Select Rectangle", "Select Circle", "Select Lasso", "Select Color"]:
                continue

            action = QAction(QIcon(tool.icon), tool.name, self)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            button = QToolButton()
            button.setDefaultAction(action)
            toolbar.addWidget(button)

        # Shape Tools
        self.shape_button = QToolButton(self)
        self.shape_button.setIcon(QIcon("icons/toolline.png"))
        self.shape_button.setPopupMode(QToolButton.MenuButtonPopup)
        shape_menu = QMenu(self.shape_button)
        self.shape_button.setMenu(shape_menu)

        shape_tools = [tool for tool in tools if tool.name in ["Line", "Rectangle", "Ellipse"]]
        for tool in shape_tools:
            action = QAction(QIcon(tool.icon), tool.name, self)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            shape_menu.addAction(action)
            if tool.name == "Line":
                self.shape_button.setDefaultAction(action)

        toolbar.addWidget(self.shape_button)

        # Selection Tools
        self.selection_button = QToolButton(self)
        self.selection_button.setIcon(QIcon("icons/toolselectrect.png"))
        self.selection_button.setPopupMode(QToolButton.MenuButtonPopup)
        selection_menu = QMenu(self.selection_button)
        self.selection_button.setMenu(selection_menu)

        selection_tools = [tool for tool in tools if tool.name in ["Select Rectangle", "Select Circle", "Select Lasso", "Select Color"]]
        for tool in selection_tools:
            action = QAction(QIcon(tool.icon), tool.name, self)
            action.triggered.connect(functools.partial(self.app.drawing_context.set_tool, tool.name))
            selection_menu.addAction(action)
            if tool.name == "Select Rectangle":
                self.selection_button.setDefaultAction(action)

        toolbar.addWidget(self.selection_button)

        # Color Swatch Panel
        self.color_toolbar = QToolBar("Colors")
        self.addToolBar(Qt.BottomToolBarArea, self.color_toolbar)
        self.color_toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)

        self.color_container = QWidget()
        self.color_layout = QGridLayout(self.color_container)
        self.color_layout.setSpacing(0)
        self.color_layout.setContentsMargins(0, 0, 0, 0)

        # Add saturation and value swatches
        for i in range(7):
            button = ColorButton("#808080", self.app.drawing_context)
            self.saturation_buttons.append(button)

        for i in range(7):
            button = ColorButton("#808080", self.app.drawing_context)
            self.value_buttons.append(button)

        colors = self.load_palette()
        self.update_palette(colors)

        self.color_toolbar.addWidget(self.color_container)

        self.update_dynamic_palette(self.app.drawing_context.pen_color)

        # Preview Panel
        self.preview_panel = PreviewPanel(self.app)
        preview_dock_widget = QDockWidget("Preview", self)
        preview_dock_widget.setWidget(self.preview_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, preview_dock_widget)

        # Layer Manager Panel
        self.layer_manager_widget = LayerManagerWidget(self.app)
        self.layer_manager_widget.layer_changed.connect(self.canvas.update)
        layer_dock_widget = QDockWidget("Layers", self)
        layer_dock_widget.setWidget(self.layer_manager_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock_widget)

        # AI Panel
        self.ai_panel = AIPanel(self.app)
        self.ai_panel.image_generated.connect(self.app.add_new_layer_with_image)
        self.ai_dock_widget = QDockWidget("AI", self)
        self.ai_dock_widget.setWidget(self.ai_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock_widget)
        self.ai_dock_widget.setFloating(True)
        self.ai_dock_widget.hide()

        self.app.document_changed.connect(self.preview_panel.update_preview)
        self.canvas.canvas_updated.connect(self.preview_panel.update_preview)

        self.app.drawing_context.mirror_x_changed.connect(self.on_mirror_changed)
        self.app.drawing_context.mirror_y_changed.connect(self.on_mirror_changed)

        self.app.document_changed.connect(self.on_document_changed)
        self.app.select_all_triggered.connect(self.canvas.select_all)
        self.app.select_none_triggered.connect(self.canvas.select_none)
        self.app.invert_selection_triggered.connect(self.canvas.invert_selection)
        self.app.crop_to_selection_triggered.connect(self.on_crop_to_selection)
        self.app.clear_layer_triggered.connect(self.layer_manager_widget.clear_layer)
        self.app.exit_triggered.connect(self.close)

    @Slot(object)
    def handle_canvas_message(self, data):
        if not isinstance(data, tuple):
            return  # This is a Command object, ignore it

        from PySide6.QtGui import QImage, QPainter, Qt
        command_type, command_data = data
        active_layer = self.app.document.layer_manager.active_layer
        if not active_layer:
            if command_type == "get_active_layer_image":
                self.canvas.original_image = None
            return

        if command_type == "get_active_layer_image":
            self.canvas.original_image = active_layer.image.copy()
            if command_data == "line_tool_start" or command_data == "ellipse_tool_start" or command_data == "rectangle_tool_start":
                self.canvas.temp_image = self.canvas.original_image.copy()

        elif command_type == "cut_selection":
            if self.canvas.selection_shape:
                self.canvas.original_image = QImage(active_layer.image.size(), QImage.Format_ARGB32)
                self.canvas.original_image.fill(Qt.transparent)
                painter = QPainter(self.canvas.original_image)
                painter.setClipPath(self.canvas.selection_shape)
                painter.drawImage(0, 0, active_layer.image)
                painter.end()

                painter = QPainter(active_layer.image)
                painter.setClipPath(self.canvas.selection_shape)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(active_layer.image.rect(), Qt.transparent)
                painter.end()
            else:
                self.canvas.original_image = active_layer.image.copy()
                active_layer.image.fill(Qt.transparent)

            self.canvas.temp_image = QImage(active_layer.image.size(), QImage.Format_ARGB32)
            self.canvas.temp_image.fill(Qt.transparent)


    @Slot()
    def on_document_changed(self):
        self.layer_manager_widget.refresh_layers()
        self.canvas.set_document(self.app.document)
        self.canvas.update()

    @Slot()
    def on_crop_to_selection(self):
        if self.canvas.selection_shape:
            selection_rect = self.canvas.selection_shape.boundingRect().toRect()
            self.app.perform_crop(selection_rect)
            self.canvas.select_none()

    def update_tool_buttons(self, tool_name):
        for action in self.shape_button.menu().actions():
            if action.text() == tool_name:
                self.shape_button.setDefaultAction(action)
                return

        for action in self.selection_button.menu().actions():
            if action.text() == tool_name:
                self.selection_button.setDefaultAction(action)
                return

    def load_palette(self):
        try:
            with open("palettes/default.colors", "r") as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            return []

    def update_palette(self, colors):
        # Clear existing main palette buttons
        for button in self.main_palette_buttons:
            self.color_layout.removeWidget(button)
            button.deleteLater()
        self.main_palette_buttons.clear()

        # Add new color buttons
        num_default_cols = (len(colors) + 1) // 2
        for i, color in enumerate(colors):
            button = ColorButton(color, self.app.drawing_context)
            self.main_palette_buttons.append(button)
            row = i % 2
            col = i // 2
            self.color_layout.addWidget(button, row, col)

        # Re-add separator and dynamic swatches
        separator_col_index = (len(self.main_palette_buttons) + 1) // 2
        self.color_layout.setColumnMinimumWidth(separator_col_index, 12)

        for i, button in enumerate(self.saturation_buttons):
            self.color_layout.addWidget(button, 0, separator_col_index + 1 + i)

        for i, button in enumerate(self.value_buttons):
            self.color_layout.addWidget(button, 1, separator_col_index + 1 + i)

    def update_dynamic_palette(self, color):
        h, s, v, a = color.getHsv()

        # Update saturation buttons
        for i, button in enumerate(self.saturation_buttons):
            new_s = int(i / 6 * 255)
            new_color = QColor.fromHsv(h, new_s, v, a)
            button.set_color(new_color)

        # Update value buttons
        for i, button in enumerate(self.value_buttons):
            new_v = int(i / 6 * 255)
            new_color = QColor.fromHsv(h, s, new_v, a)
            button.set_color(new_color)

    def update_cursor_pos_label(self, pos):
        self.cursor_pos_label.setText(f"Cursor: ({pos.x()}, {pos.y()})")

    def update_zoom_level_label(self, zoom):
        self.zoom_level_label.setText(f"Zoom: {int(zoom * 100)}%")

    def update_selected_tool_label(self, tool):
        self.selected_tool_label.setText(f"Tool: {tool}")

    def update_selection_size_label(self, width, height):
        if width > 0 and height > 0:
            self.selection_size_label.setText(f"Selection: {width}x{height}")
        else:
            self.selection_size_label.setText("")

    def update_pen_width_label(self, width):
        self.pen_width_label.setText(f"{width:02d}")

    def update_pen_width_slider(self, width):
        self.pen_width_slider.setValue(width)

    def update_undo_redo_actions(self):
        self.action_manager.undo_action.setEnabled(len(self.app.undo_manager.undo_stack) > 0)
        self.action_manager.redo_action.setEnabled(len(self.app.undo_manager.redo_stack) > 0)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "initial_zoom_set"):
            self.canvas.set_initial_zoom()
            self.initial_zoom_set = True

    def open_palette_dialog(self):
        dialog = PaletteDialog(self)
        if dialog.exec():
            colors = dialog.get_selected_colors()
            if colors:
                self.update_palette(colors)

    def toggle_ai_panel(self):
        if self.ai_dock_widget.isVisible():
            self.ai_dock_widget.hide()
        else:
            self.ai_dock_widget.show()

    def open_new_file_dialog(self):
        dialog = NewFileDialog(self.app, self)
        dialog.exec()

    def open_resize_dialog(self):
        if self.app.document:
            dialog = ResizeDialog(self, self.app.document.width, self.app.document.height)
            if dialog.exec():
                values = dialog.get_values()
                self.app.resize_document(values["width"], values["height"], values["interpolation"])

    def open_background_color_dialog(self):
        color = QColorDialog.getColor(self.canvas.background_color, self)
        if color.isValid():
            self.canvas.set_background(Background(color))

    def update_crop_action_state(self, has_selection):
        self.action_manager.crop_action.setEnabled(has_selection)

    def update_brush_button(self, brush_type):
        self.action_manager.circular_brush_action.setChecked(brush_type == "Circular")
        self.action_manager.square_brush_action.setChecked(brush_type == "Square")

    def on_mirror_changed(self):
        is_mirroring = self.app.drawing_context.mirror_x or self.app.drawing_context.mirror_y
        