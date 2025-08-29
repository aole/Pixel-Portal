from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QMenu, QToolButton, QVBoxLayout
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QKeySequence
from PySide6.QtCore import Qt
from .canvas import Canvas
from .layer_manager_widget import LayerManagerWidget
from .ai.dialog import AiDialog
from .new_file_dialog import NewFileDialog
from .resize_dialog import ResizeDialog
from .background import Background
from .palette_dialog import PaletteDialog
from .preview_panel import PreviewPanel

from PySide6.QtWidgets import QMainWindow, QLabel, QToolBar, QPushButton, QWidget, QGridLayout, QDockWidget, QSlider, QColorDialog


class ColorButton(QPushButton):
    def __init__(self, color, app):
        super().__init__()
        self.app = app
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
        self.app.set_pen_color(self.color)


class ActiveColorButton(QPushButton):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setFixedSize(24, 24)
        self.clicked.connect(self.on_click)
        self.update_color(self.app.pen_color)
        self.app.pen_color_changed.connect(self.update_color)

    def on_click(self):
        color = QColorDialog.getColor(self.app.pen_color, self)
        if color.isValid():
            self.app.set_pen_color(color.name())

    def update_color(self, color):
        self.setStyleSheet(f"background-color: {color.name()}")
        self.setToolTip(color.name())


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Pixel Portal")
        self.resize(1200, 800)

        self.main_palette_buttons = []
        self.saturation_buttons = []
        self.value_buttons = []

        self.canvas = Canvas(self.app)
        self.setCentralWidget(self.canvas)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction(QIcon("icons/new.png"), "&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.open_new_file_dialog)
        file_menu.addAction(new_action)

        open_action = QAction(QIcon("icons/load.png"), "&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.app.open_document)
        file_menu.addAction(open_action)

        save_action = QAction(QIcon("icons/save.png"), "&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.app.save_document)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        load_palette_action = QAction("Load Palette from Image...", self)
        load_palette_action.triggered.connect(self.open_palette_dialog)
        file_menu.addAction(load_palette_action)

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

        edit_menu.addSeparator()

        paste_as_new_layer_action = QAction("Paste as New Layer", self)
        paste_as_new_layer_action.setShortcut("Ctrl+Shift+V")
        paste_as_new_layer_action.triggered.connect(self.app.paste_as_new_layer)
        edit_menu.addAction(paste_as_new_layer_action)

        edit_menu.addSeparator()

        clear_action = QAction(QIcon("icons/clear.png"), "Clear", self)
        clear_action.setShortcut(QKeySequence.Delete)
        clear_action.triggered.connect(self.app.clear_layer)
        edit_menu.addAction(clear_action)

        select_menu = menu_bar.addMenu("&Select")

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.app.select_all)
        select_menu.addAction(select_all_action)

        select_none_action = QAction("Select &None", self)
        select_none_action.setShortcut("Ctrl+D")
        select_none_action.triggered.connect(self.app.select_none)
        select_menu.addAction(select_none_action)

        invert_selection_action = QAction("&Invert Selection", self)
        invert_selection_action.setShortcut("Ctrl+I")
        invert_selection_action.triggered.connect(self.app.invert_selection)
        select_menu.addAction(invert_selection_action)

        image_menu = menu_bar.addMenu("&Image")
        resize_action = QAction(QIcon("icons/resize.png"), "&Resize", self)
        resize_action.setShortcut("Ctrl+R")
        resize_action.triggered.connect(self.open_resize_dialog)
        image_menu.addAction(resize_action)

        self.crop_action = QAction("Crop to Selection", self)
        self.crop_action.triggered.connect(self.app.crop_to_selection)
        self.crop_action.setEnabled(False)
        image_menu.addAction(self.crop_action)

        image_menu.addSeparator()

        flip_horizontal_action = QAction("Flip Horizontal", self)
        flip_horizontal_action.triggered.connect(self.app.flip_horizontal)
        image_menu.addAction(flip_horizontal_action)

        flip_vertical_action = QAction("Flip Vertical", self)
        flip_vertical_action.triggered.connect(self.app.flip_vertical)
        image_menu.addAction(flip_vertical_action)

        view_menu = menu_bar.addMenu("&View")
        background_menu = view_menu.addMenu("&Background")

        checkered_action = QAction("Checkered Background", self)
        checkered_action.triggered.connect(lambda: self.canvas.set_background(Background()))
        background_menu.addAction(checkered_action)

        background_menu.addSeparator()

        white_action = QAction("White", self)
        white_action.triggered.connect(lambda: self.canvas.set_background(Background(QColor("white"))))
        background_menu.addAction(white_action)

        black_action = QAction("Black", self)
        black_action.triggered.connect(lambda: self.canvas.set_background(Background(QColor("black"))))
        background_menu.addAction(black_action)

        gray_action = QAction("Gray", self)
        gray_action.triggered.connect(lambda: self.canvas.set_background(Background(QColor("gray"))))
        background_menu.addAction(gray_action)

        magenta_action = QAction("Magenta", self)
        magenta_action.triggered.connect(lambda: self.canvas.set_background(Background(QColor("magenta"))))
        background_menu.addAction(magenta_action)

        background_menu.addSeparator()

        custom_color_action = QAction("Custom Color...", self)
        custom_color_action.triggered.connect(self.open_background_color_dialog)
        background_menu.addAction(custom_color_action)

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
        self.app.tool_changed.connect(self.update_selected_tool_label)
        self.canvas.selection_size_changed.connect(self.update_selection_size_label)
        self.app.pen_width_changed.connect(self.update_pen_width_slider)
        self.app.pen_width_changed.connect(self.update_pen_width_label)
        self.app.undo_stack_changed.connect(self.update_undo_redo_actions)
        self.app.pen_color_changed.connect(self.update_dynamic_palette)

        # Toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        toolbar.layout().setAlignment(Qt.AlignLeft)

        top_toolbar = QToolBar("Top Toolbar")
        self.addToolBar(Qt.TopToolBarArea, top_toolbar)

        top_toolbar.addAction(new_action)
        top_toolbar.addAction(open_action)
        top_toolbar.addAction(save_action)
        top_toolbar.addSeparator()

        # Brush size slider
        brush_icon = QLabel()
        pixmap = QPixmap("icons/brush.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        brush_icon.setPixmap(pixmap)
        top_toolbar.addWidget(brush_icon)
        
        self.pen_width_label = QLabel(f"{self.app.pen_width:02d}")
        top_toolbar.addWidget(self.pen_width_label)

        self.pen_width_slider = QSlider(Qt.Horizontal)
        self.pen_width_slider.setRange(1, 64)
        self.pen_width_slider.setValue(self.app.pen_width)
        self.pen_width_slider.setMinimumWidth(32)
        self.pen_width_slider.setMaximumWidth(100)
        self.pen_width_slider.setSingleStep(1)
        self.pen_width_slider.setPageStep(1)
        self.pen_width_slider.valueChanged.connect(self.app.set_pen_width)
        top_toolbar.addWidget(self.pen_width_slider)
        
        top_toolbar.addSeparator()

        grid_action = QAction(QIcon("icons/grid.png"), "Toggle Grid", self)
        grid_action.setCheckable(True)
        grid_action.triggered.connect(self.canvas.toggle_grid)
        top_toolbar.addAction(grid_action)
        
        active_color_button = ActiveColorButton(self.app)
        toolbar.addWidget(active_color_button)
        
        pen_action = QAction(QIcon("icons/toolpen.png"), "Pen", self)
        pen_action.triggered.connect(lambda: self.app.set_tool("Pen"))
        pen_button = QToolButton()
        pen_button.setDefaultAction(pen_action)
        toolbar.addWidget(pen_button)

        bucket_action = QAction(QIcon("icons/toolbucket.png"), "Bucket", self)
        bucket_action.triggered.connect(lambda: self.app.set_tool("Bucket"))
        bucket_button = QToolButton()
        bucket_button.setDefaultAction(bucket_action)
        toolbar.addWidget(bucket_button)

        picker_action = QAction(QIcon("icons/toolpicker.png"), "Picker", self)
        picker_action.triggered.connect(lambda: self.app.set_tool("Picker"))
        picker_button = QToolButton()
        picker_button.setDefaultAction(picker_action)
        toolbar.addWidget(picker_button)

        # Shape Tools
        self.shape_button = QToolButton(self)
        self.shape_button.setIcon(QIcon("icons/toolline.png"))
        self.shape_button.setPopupMode(QToolButton.MenuButtonPopup)
        shape_menu = QMenu(self.shape_button)
        self.shape_button.setMenu(shape_menu)

        line_action = QAction(QIcon("icons/toolline.png"), "Line", self)
        line_action.triggered.connect(lambda: self.set_shape_tool(line_action))
        shape_menu.addAction(line_action)
        self.shape_button.setDefaultAction(line_action)

        rect_action = QAction(QIcon("icons/toolrect.png"), "Rectangle", self)
        rect_action.triggered.connect(lambda: self.set_shape_tool(rect_action))
        shape_menu.addAction(rect_action)

        ellipse_action = QAction(QIcon("icons/toolellipse.png"), "Ellipse", self)
        ellipse_action.triggered.connect(lambda: self.set_shape_tool(ellipse_action))
        shape_menu.addAction(ellipse_action)

        toolbar.addWidget(self.shape_button)

        # Selection Tools
        self.selection_button = QToolButton(self)
        self.selection_button.setIcon(QIcon("icons/toolselectrect.png"))
        self.selection_button.setPopupMode(QToolButton.MenuButtonPopup)
        selection_menu = QMenu(self.selection_button)
        self.selection_button.setMenu(selection_menu)

        select_rect_action = QAction(QIcon("icons/toolselectrect.png"), "Select Rectangle", self)
        select_rect_action.triggered.connect(lambda: self.set_selection_tool(select_rect_action))
        selection_menu.addAction(select_rect_action)
        self.selection_button.setDefaultAction(select_rect_action)

        select_circle_action = QAction(QIcon("icons/toolselectcircle.png"), "Select Circle", self)
        select_circle_action.triggered.connect(lambda: self.set_selection_tool(select_circle_action))
        selection_menu.addAction(select_circle_action)

        select_lasso_action = QAction(QIcon("icons/toolselectlasso.png"), "Select Lasso", self)
        select_lasso_action.triggered.connect(lambda: self.set_selection_tool(select_lasso_action))
        selection_menu.addAction(select_lasso_action)

        select_color_action = QAction(QIcon("icons/toolselectcolor.png"), "Select Color", self)
        select_color_action.triggered.connect(lambda: self.set_selection_tool(select_color_action))
        selection_menu.addAction(select_color_action)

        toolbar.addWidget(self.selection_button)

        ai_action = QAction(QIcon("icons/AI.png"), "AI Image", self)
        ai_action.triggered.connect(self.open_ai_dialog)
        ai_button = QToolButton()
        ai_button.setDefaultAction(ai_action)
        toolbar.addWidget(ai_button)

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
            button = ColorButton("#808080", self.app)
            self.saturation_buttons.append(button)

        for i in range(7):
            button = ColorButton("#808080", self.app)
            self.value_buttons.append(button)

        colors = self.load_palette()
        self.update_palette(colors)

        self.color_toolbar.addWidget(self.color_container)

        self.update_dynamic_palette(self.app.pen_color)

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

        self.app.document_changed.connect(self.preview_panel.update_preview)
        self.canvas.canvas_updated.connect(self.preview_panel.update_preview)

    def set_shape_tool(self, action):
        self.app.set_tool(action.text())
        self.shape_button.setIcon(action.icon())
        self.shape_button.setDefaultAction(action)

    def set_selection_tool(self, action):
        self.app.set_tool(action.text())
        self.selection_button.setIcon(action.icon())
        self.selection_button.setDefaultAction(action)

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
            button = ColorButton(color, self.app)
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
        self.undo_action.setEnabled(len(self.app.undo_manager.undo_stack) > 1)
        self.redo_action.setEnabled(len(self.app.undo_manager.redo_stack) > 0)

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

    def open_ai_dialog(self):
        dialog = AiDialog(self.app, self)
        dialog.exec()

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
        self.crop_action.setEnabled(has_selection)
