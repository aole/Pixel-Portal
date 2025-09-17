import functools
import os
from PySide6.QtWidgets import (
    QFileDialog,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QKeySequence, QImage
from PySide6.QtCore import Qt, Slot, QSignalBlocker
from portal.core.animation_player import AnimationPlayer
from portal.ui.canvas import Canvas
from portal.ui.layer_manager_widget import LayerManagerWidget
from portal.ui.animation_timeline_widget import AnimationTimelineWidget
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
from portal.ui.settings_dialog import SettingsDialog


from PySide6.QtWidgets import QColorDialog
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
        self.canvas.set_background_image_alpha(
            self.app.settings_controller.background_image_alpha
        )
        self.canvas.set_background_image_mode(
            self.app.settings_controller.background_image_mode
        )

        self.animation_player = AnimationPlayer(self)

        self.timeline_widget = AnimationTimelineWidget(self)
        self.timeline_widget.set_playback_total_frames(self.animation_player.total_frames)
        self.timeline_widget.set_total_frames(max(0, self.animation_player.total_frames - 1))

        self.timeline_panel = QFrame(self)
        self.timeline_panel.setObjectName("animationTimelinePanel")
        self.timeline_panel.setFrameShape(QFrame.StyledPanel)
        self.timeline_panel.setFrameShadow(QFrame.Plain)
        self.timeline_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        timeline_layout = QVBoxLayout(self.timeline_panel)
        timeline_layout.setContentsMargins(12, 8, 12, 12)
        timeline_layout.setSpacing(6)

        timeline_header_layout = QHBoxLayout()
        timeline_header_layout.setContentsMargins(0, 0, 0, 0)
        timeline_header_layout.setSpacing(8)

        self.timeline_play_button = QToolButton(self.timeline_panel)
        self.timeline_play_button.setText("Play")
        self.timeline_play_button.setCheckable(True)
        timeline_header_layout.addWidget(self.timeline_play_button)

        self.timeline_stop_button = QToolButton(self.timeline_panel)
        self.timeline_stop_button.setText("Stop")
        timeline_header_layout.addWidget(self.timeline_stop_button)

        self.timeline_current_frame_label = QLabel("Frame 0", self.timeline_panel)
        self.timeline_current_frame_label.setObjectName("animationTimelineCurrentFrameLabel")
        self.timeline_current_frame_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        timeline_header_layout.addWidget(self.timeline_current_frame_label, 0)

        total_frames_text_label = QLabel("Total", self.timeline_panel)
        total_frames_text_label.setObjectName("animationTimelineTotalFramesLabel")
        total_frames_text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        timeline_header_layout.addWidget(total_frames_text_label, 0)

        self.timeline_total_frames_spinbox = QSpinBox(self.timeline_panel)
        self.timeline_total_frames_spinbox.setObjectName("animationTimelineTotalFramesSpinBox")
        self.timeline_total_frames_spinbox.setRange(1, 9999)
        self.timeline_total_frames_spinbox.setAccelerated(True)
        self.timeline_total_frames_spinbox.setKeyboardTracking(False)
        self.timeline_total_frames_spinbox.setFixedWidth(80)
        self.timeline_total_frames_spinbox.setValue(self.animation_player.total_frames)
        timeline_header_layout.addWidget(self.timeline_total_frames_spinbox, 0)

        timeline_header_layout.addStretch()

        fps_label = QLabel("FPS", self.timeline_panel)
        timeline_header_layout.addWidget(fps_label)

        self.timeline_fps_slider = QSlider(Qt.Horizontal, self.timeline_panel)
        self.timeline_fps_slider.setRange(1, 60)
        self.timeline_fps_slider.setValue(int(round(self.animation_player.fps)))
        self.timeline_fps_slider.setFixedWidth(120)
        timeline_header_layout.addWidget(self.timeline_fps_slider)

        self.timeline_fps_value_label = QLabel(self.timeline_panel)
        timeline_header_layout.addWidget(self.timeline_fps_value_label)

        timeline_header_layout.addStretch()

        self.timeline_layer_label = QLabel("", self.timeline_panel)
        self.timeline_layer_label.setObjectName("animationTimelineLayerLabel")
        self.timeline_layer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        timeline_header_layout.addWidget(self.timeline_layer_label, 0)

        timeline_layout.addLayout(timeline_header_layout)
        timeline_layout.addWidget(self.timeline_widget)

        self.timeline_play_button.toggled.connect(self._on_timeline_play_toggled)
        self.timeline_stop_button.clicked.connect(self._on_timeline_stop_clicked)
        self.timeline_fps_slider.valueChanged.connect(self._on_timeline_fps_changed)
        self.timeline_total_frames_spinbox.valueChanged.connect(self._on_timeline_total_frames_changed)

        self.timeline_widget.current_frame_changed.connect(self._update_current_frame_label)
        self.timeline_widget.current_frame_changed.connect(self.on_timeline_frame_changed)
        self.timeline_widget.key_add_requested.connect(self.on_timeline_add_key)
        self.timeline_widget.key_remove_requested.connect(self.on_timeline_remove_key)
        self.timeline_widget.key_copy_requested.connect(self.on_timeline_copy_key)
        self.timeline_widget.key_paste_requested.connect(self.on_timeline_paste_key)

        self.animation_player.frame_changed.connect(self.timeline_widget.set_current_frame)
        self.animation_player.playing_changed.connect(self._on_player_state_changed)
        self.animation_player.fps_changed.connect(self._update_timeline_fps_label)

        self.timeline_widget.set_has_copied_key(self.app.has_copied_keyframe())

        self._update_current_frame_label(self.timeline_widget.current_frame())
        self._update_timeline_layer_label(None)
        self._on_player_state_changed(self.animation_player.is_playing)
        self._update_timeline_fps_label(self.animation_player.fps)
        self.sync_timeline_from_document()

        central_container = QWidget(self)
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.canvas, 1)
        central_layout.addWidget(self.timeline_panel, 0)

        self.setCentralWidget(central_container)
        self.canvas.set_document(self.app.document)
        self.apply_grid_settings_from_settings()
        self._current_document_id = id(self.app.document)

        # Connect DrawingContext signals to Canvas slots
        self.app.drawing_context.tool_changed.connect(self.canvas.on_tool_changed)

        # Connect Canvas signal to App and UI slots
        self.canvas.command_generated.connect(self.app.handle_command)
        self.canvas.command_generated.connect(self.handle_canvas_message)

        self.action_manager.setup_actions(self.canvas)
        self.addAction(self.action_manager.clear_action)

        self.canvas.background_mode_changed.connect(
            self.on_background_image_mode_changed
        )
        self.canvas.background_alpha_changed.connect(
            self.on_background_image_alpha_changed
        )

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
        self.layer_manager_widget.layer_changed.connect(self.sync_timeline_from_document)
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
        self.app.document_changed.connect(self.sync_timeline_from_document)
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

    def _update_current_frame_label(self, frame: int) -> None:
        self.timeline_current_frame_label.setText(f"Frame {frame}")
        self._update_stop_button_state()

    def _update_timeline_layer_label(self, layer_name: str | None) -> None:
        if layer_name:
            text = f"Layer: {layer_name}"
        else:
            text = "Layer: (none)"
        self.timeline_layer_label.setText(text)

    def _update_timeline_fps_label(self, value: float) -> None:
        if isinstance(value, (int, float)):
            text = f"{value:.0f}"
            slider_value = int(round(value))
            with QSignalBlocker(self.timeline_fps_slider):
                self.timeline_fps_slider.setValue(slider_value)
        else:
            text = ""
        self.timeline_fps_value_label.setText(text)

    def _update_stop_button_state(self) -> None:
        should_enable = (
            self.animation_player.is_playing
            or self.timeline_widget.current_frame() != 0
        )
        self.timeline_stop_button.setEnabled(should_enable)

    @Slot(bool)
    def _on_timeline_play_toggled(self, checked: bool) -> None:
        if checked:
            self.animation_player.play()
        else:
            self.animation_player.pause()

    @Slot()
    def _on_timeline_stop_clicked(self) -> None:
        self.animation_player.stop()

    @Slot(int)
    def _on_timeline_fps_changed(self, value: int) -> None:
        self.animation_player.set_fps(value)

    @Slot(int)
    def _on_timeline_total_frames_changed(self, value: int) -> None:
        value = max(1, int(value))
        document = self.app.document
        doc_max_index = 0
        if document:
            frame_manager = getattr(document, "frame_manager", None)
            if frame_manager is not None:
                frame_count = len(frame_manager.frames)
                doc_max_index = max(0, frame_count - 1) if frame_count else 0
        keys = self.timeline_widget.keys()
        highest_key = max(keys) if keys else 0
        target_base = max(doc_max_index, highest_key, value - 1)
        self.timeline_widget.set_total_frames(target_base)
        self.timeline_widget.set_playback_total_frames(value)
        timeline_blocker = QSignalBlocker(self.timeline_widget)
        player_blocker = QSignalBlocker(self.animation_player)
        try:
            self.animation_player.set_total_frames(value)
        finally:
            del player_blocker
            del timeline_blocker
        current_frame = self.timeline_widget.current_frame()
        if (
            current_frame < self.animation_player.total_frames
            and self.animation_player.current_frame != current_frame
        ):
            self.animation_player.set_current_frame(current_frame)
        self._update_stop_button_state()

    @Slot(bool)
    def _on_player_state_changed(self, playing: bool) -> None:
        with QSignalBlocker(self.timeline_play_button):
            self.timeline_play_button.setChecked(playing)
        self.timeline_play_button.setText("Pause" if playing else "Play")
        self._update_stop_button_state()

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
    def sync_timeline_from_document(self):
        playback_total = max(1, self.timeline_total_frames_spinbox.value())
        self.timeline_widget.set_playback_total_frames(playback_total)

        document = self.app.document
        frame_manager = getattr(document, "frame_manager", None) if document else None
        if not document or frame_manager is None:
            self._update_timeline_layer_label(None)
            timeline_blocker = QSignalBlocker(self.timeline_widget)
            try:
                self.timeline_widget.set_total_frames(max(0, playback_total - 1))
                self.timeline_widget.set_keys([0])
                self.timeline_widget.set_current_frame(0)
            finally:
                del timeline_blocker
            player_blocker = QSignalBlocker(self.animation_player)
            try:
                self.animation_player.set_total_frames(playback_total)
                if self.animation_player.current_frame != 0:
                    self.animation_player.set_current_frame(0)
            finally:
                del player_blocker
            self._update_current_frame_label(self.timeline_widget.current_frame())
            self._update_stop_button_state()
            return

        layer_manager = getattr(frame_manager, "current_layer_manager", None)
        active_layer = getattr(layer_manager, "active_layer", None) if layer_manager else None
        layer_name = getattr(active_layer, "name", None)
        self._update_timeline_layer_label(layer_name)

        frame_count = len(frame_manager.frames)
        doc_max_index = max(0, frame_count - 1) if frame_count else 0
        current_frame = frame_manager.active_frame_index
        if current_frame < 0 and frame_count:
            current_frame = 0
        current_frame = max(0, min(current_frame, doc_max_index))
        keys = list(document.key_frames)
        highest_key = max(keys) if keys else 0
        base_target = max(doc_max_index, highest_key, playback_total - 1)

        timeline_blocker = QSignalBlocker(self.timeline_widget)
        try:
            self.timeline_widget.set_total_frames(base_target)
            self.timeline_widget.set_keys(keys)
            self.timeline_widget.set_current_frame(current_frame)
        finally:
            del timeline_blocker

        player_blocker = QSignalBlocker(self.animation_player)
        try:
            self.animation_player.set_total_frames(playback_total)
        finally:
            del player_blocker

        if (
            current_frame < self.animation_player.total_frames
            and self.animation_player.current_frame != current_frame
        ):
            self.animation_player.set_current_frame(current_frame)

        self._update_current_frame_label(self.timeline_widget.current_frame())
        self._update_stop_button_state()

    @Slot()
    def on_document_changed(self):
        document = self.app.document
        document_id = id(document)
        if getattr(self, "_current_document_id", None) != document_id:
            self._current_document_id = document_id
            self.animation_player.stop()
        self.layer_manager_widget.refresh_layers()
        self.canvas.set_document(document)
        self.canvas.update()

    @Slot(int)
    def on_timeline_add_key(self, frame: int) -> None:
        self.app.add_keyframe(frame)

    @Slot(int)
    def on_timeline_remove_key(self, frame: int) -> None:
        self.app.remove_keyframe(frame)

    @Slot(int)
    def on_timeline_copy_key(self, frame: int) -> None:
        self.app.copy_keyframe(frame)
        self.timeline_widget.set_has_copied_key(self.app.has_copied_keyframe())

    @Slot(int)
    def on_timeline_paste_key(self, frame: int) -> None:
        pasted = self.app.paste_keyframe(frame)
        self.timeline_widget.set_has_copied_key(self.app.has_copied_keyframe())
        if pasted:
            self.timeline_widget.set_current_frame(frame)

    @Slot(int)
    def on_timeline_frame_changed(self, frame: int) -> None:
        document = self.app.document
        if not document:
            return
        frame_manager = getattr(document, "frame_manager", None)
        if frame_manager is None:
            return
        if not (0 <= frame < len(frame_manager.frames)):
            return
        if frame_manager.active_frame_index == frame:
            return
        if (
            frame < self.animation_player.total_frames
            and self.animation_player.current_frame != frame
        ):
            self.animation_player.set_current_frame(frame)
        self.app.select_frame(frame)

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

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.app.settings_controller, self)
        dialog.settings_applied.connect(self.apply_settings_from_controller)
        dialog.exec()

    @Slot()
    def apply_settings_from_controller(self):
        self.apply_grid_settings_from_settings()

        controller = self.app.settings_controller
        new_alpha = controller.background_image_alpha
        new_mode = controller.background_image_mode

        blocker = QSignalBlocker(self.canvas)
        try:
            self.canvas.set_background_image_alpha(new_alpha)
            self.canvas.set_background_image_mode(new_mode)
        finally:
            del blocker

        controller.update_background_settings(
            image_mode=self.canvas.background_mode,
            image_alpha=self.canvas.background_image_alpha,
        )
        self.app.save_settings()

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
            self.canvas.set_background(
                Background(
                    image_path=file_path,
                    image_mode=self.canvas.background_mode,
                    image_alpha=self.canvas.background_image_alpha,
                )
            )

    def update_crop_action_state(self, has_selection):
        self.action_manager.crop_action.setEnabled(has_selection)

    def update_brush_button(self, brush_type):
        self.action_manager.circular_brush_action.setChecked(brush_type == "Circular")
        self.action_manager.square_brush_action.setChecked(brush_type == "Square")
        self.action_manager.pattern_brush_action.setChecked(brush_type == "Pattern")

    def on_tool_changed_for_status_bar(self, tool_name):
        if tool_name != "Rotate":
            self.status_bar_manager.update_rotation_angle_label(None)
        else:
            # When switching to the Rotate tool, display the initial angle (0)
            self.status_bar_manager.update_rotation_angle_label(0)

    def on_mirror_changed(self):
        is_mirroring = self.app.drawing_context.mirror_x or self.app.drawing_context.mirror_y

    @Slot(object)
    def on_background_image_mode_changed(self, mode):
        self.app.settings_controller.update_background_settings(
            image_mode=mode,
            image_alpha=self.canvas.background_image_alpha,
        )

    @Slot(float)
    def on_background_image_alpha_changed(self, alpha):
        self.app.settings_controller.update_background_settings(
            image_mode=self.canvas.background_mode,
            image_alpha=alpha,
        )

    def open_flip_dialog(self):
        if self.app.document:
            dialog = FlipDialog(self)
            if dialog.exec():
                values = dialog.get_values()
                self.app.flip(values["horizontal"], values["vertical"], values["all_layers"])

    def apply_grid_settings_from_settings(self):
        self.canvas.set_grid_settings(**self.app.settings_controller.get_grid_settings())

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
        