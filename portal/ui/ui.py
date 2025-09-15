import functools
import os
from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QMenu, QToolButton, QVBoxLayout, QFileDialog
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QKeySequence, QImage
from PySide6.QtCore import Qt, Slot
from portal.ui.canvas import Canvas
from portal.ui.layer_manager_widget import LayerManagerWidget
try:
    from portal.ui.ai_panel import AIPanel
except Exception:  # Optional dependency may be missing or heavy to load
    AIPanel = None
from portal.ui.new_file_dialog import NewFileDialog
from portal.ui.resize_dialog import ResizeDialog
from portal.ui.background import Background
from portal.ui.preview_panel import PreviewPanel
from portal.commands.action_manager import ActionManager
from portal.commands.menu_bar_builder import MenuBarBuilder
from portal.commands.tool_bar_builder import ToolBarBuilder
from portal.commands.status_bar_manager import StatusBarManager
from portal.ui.flip_dialog import FlipDialog


from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QColorDialog
from portal.ui.color_button import ColorButton, ActiveColorButton


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Pixel Portal")
        self.resize(1200, 800)

        self.action_manager = ActionManager(self)

        self.main_palette_buttons = []

        self.canvas = Canvas(self.app.drawing_context)
        self.setCentralWidget(self.canvas)
        self.canvas.set_document(self.app.document)

        # Connect DrawingContext signals to Canvas slots
        self.app.drawing_context.tool_changed.connect(self.canvas.on_tool_changed)

        # Connect Canvas signal to App and UI slots
        self.canvas.command_generated.connect(self.app.handle_command)
        self.canvas.command_generated.connect(self.handle_canvas_message)

        self.action_manager.setup_actions(self.canvas)
        self.addAction(self.action_manager.clear_action)

        # Menu bar
        menu_bar_builder = MenuBarBuilder(self, self.action_manager)
        menu_bar_builder.setup_menus()

        # Toolbar
        toolbar_builder = ToolBarBuilder(self, self.app)
        toolbar_builder.setup_toolbars()

        # Status bar
        self.status_bar_manager = StatusBarManager(self)

        # Connect signals for RotateTool
        if "Rotate" in self.canvas.tools:
            rotate_tool = self.canvas.tools["Rotate"]
            rotate_tool.angle_changed.connect(self.status_bar_manager.update_rotation_angle_label)

        # Connect signals
        self.canvas.selection_changed.connect(self.update_crop_action_state)
        self.app.drawing_context.tool_changed.connect(toolbar_builder.update_tool_buttons)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_slider)
        self.app.drawing_context.pen_width_changed.connect(self.update_pen_width_label)
        self.app.undo_stack_changed.connect(self.update_undo_redo_actions)
        self.app.drawing_context.brush_type_changed.connect(self.update_brush_button)
        self.app.drawing_context.tool_changed.connect(self.on_tool_changed_for_status_bar)

        # Color Swatch Panel
        self.color_toolbar = QToolBar("Colors")
        self.addToolBar(Qt.BottomToolBarArea, self.color_toolbar)
        self.color_toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)

        self.color_container = QWidget()
        self.color_layout = QGridLayout(self.color_container)
        self.color_layout.setSpacing(0)
        self.color_layout.setContentsMargins(0, 0, 0, 0)

        colors = self.load_palette()
        self.update_palette(colors)

        self.color_toolbar.addWidget(self.color_container)

        # Preview Panel
        self.preview_panel = PreviewPanel(self.app)
        self.preview_dock = QDockWidget("Preview", self)
        self.preview_dock.setWidget(self.preview_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.preview_dock)

        # Layer Manager Panel
        self.layer_manager_widget = LayerManagerWidget(self.app, self.canvas)
        self.layer_manager_widget.layer_changed.connect(self.canvas.update)
        self.layer_manager_dock = QDockWidget("Layers", self)
        self.layer_manager_dock.setWidget(self.layer_manager_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_manager_dock)

        # AI Panel (optional)
        self.ai_panel = None
        self.ai_panel_dock = None
        if AIPanel is not None:
            self.ai_panel = AIPanel(self.app, self.preview_panel)
            self.ai_panel.image_generated.connect(self.app.add_new_layer_with_image)
            self.ai_panel_dock = QDockWidget("AI", self)
            self.ai_panel_dock.setWidget(self.ai_panel)
            self.addDockWidget(Qt.RightDockWidgetArea, self.ai_panel_dock)

            self.tabifyDockWidget(self.layer_manager_dock, self.ai_panel_dock)
            self.layer_manager_dock.raise_()

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

        menu_bar_builder.set_panels(self.layer_manager_dock, self.preview_dock, self.ai_panel_dock)
        menu_bar_builder.set_toolbars([
            toolbar_builder.top_toolbar,
            toolbar_builder.left_toolbar,
            self.color_toolbar
        ])

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
            if command_data in ["line_tool_start", "ellipse_tool_start", "rectangle_tool_start", "move_tool_start_no_selection"]:
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
            button.color_removed.connect(self.remove_color_from_palette)
            self.main_palette_buttons.append(button)
            row = i % 2
            col = i // 2
            self.color_layout.addWidget(button, row, col)

    def remove_color_from_palette(self, color_to_remove):
        colors = self.get_palette()
        # Case-insensitive removal
        colors_lower = [c.lower() for c in colors]
        if color_to_remove.lower() in colors_lower:
            index_to_remove = colors_lower.index(color_to_remove.lower())
            colors.pop(index_to_remove)
            self.update_palette(colors)
            self.save_palette(colors)

    def add_color_to_palette(self, color):
        colors = self.get_palette()
        # Case-insensitive check
        if color.name().lower() not in [c.lower() for c in colors]:
            colors.append(color.name())
            self.update_palette(colors)
            self.save_palette(colors)

    def save_palette(self, colors):
        with open("palettes/default.colors", "w") as f:
            for color in colors:
                f.write(f"{color}\n")

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

    def load_palette_from_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image for Palette",
            self.app.last_directory,
            "Image Files (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.app.last_directory = os.path.dirname(file_path)
            self.app.config.set('General', 'last_directory', self.app.last_directory)

            colors = self.extract_unique_colors(file_path)
            if colors:
                self.update_palette(colors)

    def extract_unique_colors(self, image_path):
        image = QImage(image_path)
        if image.isNull():
            return []

        unique_colors = set()
        for y in range(image.height()):
            for x in range(image.width()):
                if len(unique_colors) >= 256:
                    break
                pixel_color = image.pixelColor(x, y)
                unique_colors.add(pixel_color.name())
            if len(unique_colors) >= 256:
                break
        return list(unique_colors)

    def toggle_ai_panel(self):
        if not self.ai_panel_dock:
            return
        if self.ai_panel_dock.isVisible():
            self.ai_panel_dock.hide()
        else:
            self.ai_panel_dock.show()

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

    def open_background_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Background Image",
            self.app.last_directory,
            "Image Files (*.png *.jpg *.bmp)",
        )
        if file_path:
            self.app.last_directory = os.path.dirname(file_path)
            self.app.config.set('General', 'last_directory', self.app.last_directory)
            self.canvas.set_background(Background(image_path=file_path))

    def update_crop_action_state(self, has_selection):
        self.action_manager.crop_action.setEnabled(has_selection)

    def update_brush_button(self, brush_type):
        self.action_manager.circular_brush_action.setChecked(brush_type == "Circular")
        self.action_manager.square_brush_action.setChecked(brush_type == "Square")

    def on_tool_changed_for_status_bar(self, tool_name):
        if tool_name != "Rotate":
            self.status_bar_manager.update_rotation_angle_label(None)
        else:
            # When switching to the Rotate tool, display the initial angle (0)
            self.status_bar_manager.update_rotation_angle_label(0)

    def on_mirror_changed(self):
        is_mirroring = self.app.drawing_context.mirror_x or self.app.drawing_context.mirror_y

    def open_flip_dialog(self):
        if self.app.document:
            dialog = FlipDialog(self)
            if dialog.exec():
                values = dialog.get_values()
                self.app.flip(values["horizontal"], values["vertical"], values["all_layers"])

    def get_palette(self):
        return [button.color for button in self.main_palette_buttons]

    def closeEvent(self, event):
        if self.app.check_for_unsaved_changes():
            ai_settings = self.ai_panel.get_settings()
            if not self.app.config.has_section('AI'):
                self.app.config.add_section('AI')
            self.app.config.set('AI', 'last_prompt', ai_settings['prompt'])
            self.app.save_settings()
            event.accept()
        else:
            event.ignore()

    def save_palette_as_png(self):
        colors = self.get_palette()
        if not colors:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Palette as PNG",
            self.app.last_directory,
            "PNG Files (*.png)"
        )

        if not file_path:
            return

        self.app.last_directory = os.path.dirname(file_path)
        self.app.config.set('General', 'last_directory', self.app.last_directory)

        from PySide6.QtGui import QPainter

        image = QImage(len(colors) * 4, 4, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)

        for i, color_hex in enumerate(colors):
            color = QColor(color_hex)
            painter.fillRect(i * 4, 0, 4, 4, color)

        painter.end()
        image.save(file_path)
        