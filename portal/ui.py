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
from .menu_bar_builder import MenuBarBuilder
from .tool_bar_builder import ToolBarBuilder
from .status_bar_manager import StatusBarManager


from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QColorDialog
from .color_button import ColorButton, ActiveColorButton


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
        menu_bar_builder = MenuBarBuilder(self, self.action_manager)
        menu_bar_builder.setup_menus()

        # Toolbar
        toolbar_builder = ToolBarBuilder(self, self.app)
        toolbar_builder.setup_toolbars()

        # Status bar
        self.status_bar_manager = StatusBarManager(self)

        # Connect signals
        self.canvas.selection_changed.connect(self.update_crop_action_state)
        self.app.drawing_context.tool_changed.connect(self.update_tool_buttons)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_slider)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_label)
        self.app.undo_stack_changed.connect(self.update_undo_redo_actions)
        self.app.drawing_context.pen_color_changed.connect(self.update_dynamic_palette)
        self.app.drawing_context.brush_type_changed.connect(self.update_brush_button)

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
        