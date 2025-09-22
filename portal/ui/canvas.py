import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QBrush,
    QPainter,
    QWheelEvent,
    QImage,
    QPixmap,
    QColor,
    QPen,
    QPainterPath,
    QTransform,
    QCursor,
    QPalette,
    QMouseEvent,
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, Slot, QSize, QPointF, QRectF
from portal.core.drawing import Drawing
from portal.core.renderer import CanvasRenderer
from portal.ui.background import Background, BackgroundImageMode
from portal.tools import get_tools
from portal.commands.canvas_input_handler import CanvasInputHandler
from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from PIL import Image, ImageQt


class Canvas(QWidget):
    cursor_pos_changed = Signal(QPoint)
    zoom_changed = Signal(float)
    selection_changed = Signal(bool)
    selection_size_changed = Signal(int, int)
    ruler_distance_changed = Signal(object)
    canvas_updated = Signal()
    command_generated = Signal(object)
    background_mode_changed = Signal(object)
    background_alpha_changed = Signal(float)

    def __init__(self, drawing_context, parent=None):
        super().__init__(parent)
        self.drawing_context = drawing_context
        self.renderer = CanvasRenderer(self, self.drawing_context)
        self.app = None
        self.input_handler = CanvasInputHandler(self)
        self.document = None
        self.drawing = Drawing()
        self.dragging = False
        self.x_offset = 0
        self.y_offset = 0
        self.zoom = 1.0
        self.min_zoom = 0.05
        self.max_zoom = 20.0
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.temp_image = None
        self.temp_image_replaces_active_layer = False
        self.original_image = None
        self.tile_preview_image = None
        self.preview_layer = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.background_pixmap = QPixmap("alphabg.png")
        self.background_image = None
        self.background_mode = BackgroundImageMode.FIT
        self.background_image_alpha = 1.0
        self.cursor_doc_pos = QPoint()
        self.mouse_over_canvas = False
        self.grid_visible = False
        self.grid_major_visible = True
        self.grid_minor_visible = True
        self.grid_major_spacing = 8
        self.grid_minor_spacing = 1
        self.grid_major_color = self.palette().color(QPalette.ColorRole.Text)
        self.grid_major_color.setAlpha(100)
        self.grid_minor_color = self.palette().color(QPalette.ColorRole.Mid)
        self.grid_minor_color.setAlpha(100)
        self.tile_preview_enabled = False
        self.tile_preview_rows = 3
        self.tile_preview_cols = 3
        self.background = Background()
        self.background.image_mode = self.background_mode
        self.background.image_alpha = self.background_image_alpha
        self.background_color = self.palette().window().color()
        self.selection_shape = None
        self.selection_overlay_hidden = False
        self.ctrl_pressed = False
        self.picker_cursor = QCursor(QPixmap("icons/toolpicker.png"), 0, 31)
        self.is_erasing_preview = False

        # Properties that were previously in App
        self._document_size = QSize(64, 64)

        # Onion skin settings
        self.onion_skin_enabled = False
        self.onion_skin_prev_frames = 1
        self.onion_skin_next_frames = 1
        self.onion_skin_prev_color = QColor(255, 96, 96, 168)
        self.onion_skin_next_color = QColor(96, 160, 255, 168)

        self.animation_playback_active = False

        tool_defs = get_tools()
        self.tools = {tool_def["name"]: tool_def["class"](self) for tool_def in tool_defs}
        for tool in self.tools.values():
            if hasattr(tool, "command_generated"):
                tool.command_generated.connect(self.command_generated)
        self.current_tool = self.tools["Pen"]

        self._mirror_handle_radius = 11
        self._mirror_handle_margin = 22
        self._mirror_handle_hit_padding = 6
        self._mirror_handle_hover: str | None = None
        self._mirror_handle_drag: str | None = None
        self._mirror_handle_prev_cursor: QCursor | None = None

        self.ai_output_rect = QRect(0, 0, 1, 1)
        self.ai_output_edit_enabled = False
        self._ai_output_handle_size = 14.0
        self._ai_output_active_handle: str | None = None
        self._ai_output_hover_handle: str | None = None
        self._ai_output_initial_edges: dict[str, int] | None = None
        self._ai_output_move_offset = QPointF(0, 0)
        
        self.ruler_enabled = False
        self._ruler_start: QPointF | None = None
        self._ruler_end: QPointF | None = None
        self._ruler_handle_radius = 8
        self._ruler_handle_hit_padding = 4
        self._ruler_handle_hover: str | None = None
        self._ruler_handle_drag: str | None = None
        self._ruler_handle_prev_cursor: QCursor | None = None
        self._ruler_segments = 2

        self.drawing_context.mirror_x_position_changed.connect(self.update)
        self.drawing_context.mirror_y_position_changed.connect(self.update)
        self._reset_mirror_axes(force_center=True)

    def set_preview_layer(self, layer) -> None:
        """Record the layer that preview buffers should mirror."""

        self.preview_layer = layer

    def clear_preview_layer(self) -> None:
        """Forget any cached preview layer reference."""

        self.preview_layer = None

    def redraw_temp_from_preview_layer(self, layer=None) -> bool:
        """Copy the current preview layer image into ``temp_image``.

        Returns ``True`` when the redraw succeeds and ``False`` if the
        operation was skipped because either the preview layer or
        ``temp_image`` is missing.
        """

        source_layer = layer if layer is not None else self.preview_layer
        if source_layer is None or getattr(source_layer, "image", None) is None:
            return False

        if self.temp_image is None:
            return False

        painter = QPainter(self.temp_image)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.temp_image.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.drawImage(0, 0, source_layer.image)
        painter.end()
        return True

    @Slot(QSize)
    def set_document_size(self, size):
        previous_width = self._document_size.width()
        previous_height = self._document_size.height()

        new_width = size.width()
        new_height = size.height()

        size_changed = (
            new_width != previous_width or new_height != previous_height
        )

        self._document_size = size
        self._reset_mirror_axes(force_center=size_changed)
        if size_changed or self._ruler_start is None or self._ruler_end is None:
            self._initialize_ruler_handles()
        else:
            self._emit_ruler_distance()
        self.update()

    def is_auto_key_enabled(self) -> bool:
        app = getattr(self, "app", None)
        if app is None:
            return False
        if hasattr(app, "is_auto_key_enabled"):
            return bool(app.is_auto_key_enabled())
        controller = getattr(app, "document_controller", None)
        if controller is None:
            return False
        return bool(getattr(controller, "auto_key_enabled", False))

    def keyPressEvent(self, event):
        self.input_handler.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.input_handler.keyReleaseEvent(event)

    def set_background(self, background: Background):
        previous_mode = self.background_mode
        self.background = background

        mode = background.image_mode
        if mode is None:
            mode = self.background_mode
        elif not isinstance(mode, BackgroundImageMode):
            try:
                mode = BackgroundImageMode(mode)
            except ValueError:
                mode = self.background_mode

        self.background_mode = mode
        self.background.image_mode = self.background_mode

        if background.image_path:
            pixmap = QPixmap(background.image_path)
            self.background_image = pixmap if not pixmap.isNull() else None
        else:
            self.background_image = None

        normalized_alpha = Background._normalize_alpha(background.image_alpha)
        if normalized_alpha is None:
            normalized_alpha = self.background_image_alpha
        self.set_background_image_alpha(normalized_alpha)

        if previous_mode != self.background_mode:
            self.background_mode_changed.emit(self.background_mode)

        self.update()

    def set_background_image_mode(self, mode: BackgroundImageMode):
        if not isinstance(mode, BackgroundImageMode):
            try:
                mode = BackgroundImageMode(mode)
            except ValueError:
                return

        if mode == self.background_mode:
            return

        self.background_mode = mode
        if self.background:
            self.background.image_mode = mode

        self.update()
        self.background_mode_changed.emit(self.background_mode)

    def set_background_image_alpha(self, alpha):
        normalized = Background._normalize_alpha(alpha)
        if normalized is None:
            return

        if self.background:
            self.background.image_alpha = normalized

        if math.isclose(normalized, self.background_image_alpha, abs_tol=1e-6):
            return

        self.background_image_alpha = normalized

        self.update()
        self.background_alpha_changed.emit(self.background_image_alpha)

    @Slot(bool)
    def toggle_tile_preview(self, enabled: bool):
        self.tile_preview_enabled = enabled
        self.update()

    @Slot(str)
    def on_tool_changed(self, tool):
        if self.ctrl_pressed:
            return

        if hasattr(self.current_tool, 'deactivate'):
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool]
        if hasattr(self.current_tool, 'activate'):
            self.current_tool.activate()
        self.update()
        self.setCursor(self.current_tool.cursor)

    def _update_selection_and_emit_size(self, shape):
        self.selection_shape = shape
        if shape is None:
            self.selection_size_changed.emit(0, 0)
        else:
            bounds = shape.boundingRect()
            self.selection_size_changed.emit(int(bounds.width()), int(bounds.height()))
        self.update()
        self.selection_changed.emit(True)

    def set_selection_overlay_hidden(self, hidden: bool) -> None:
        if self.selection_overlay_hidden == hidden:
            return
        self.selection_overlay_hidden = hidden
        self.update()

    def is_selection_overlay_hidden(self) -> bool:
        return self.selection_overlay_hidden

    def _emit_selection_command(
        self,
        previous_shape: QPainterPath | None,
        new_shape: QPainterPath | None,
    ) -> None:
        previous = clone_selection_path(previous_shape)
        new = clone_selection_path(new_shape)
        if selection_paths_equal(previous, new):
            self._update_selection_and_emit_size(clone_selection_path(new))
            return
        command = SelectionChangeCommand(self, previous, new)
        # Update immediately so the UI reflects the new selection even when no
        # command handler is connected (e.g., in tests). The command is still
        # emitted for undo/redo bookkeeping.
        self._update_selection_and_emit_size(clone_selection_path(new))
        self.command_generated.emit(command)

    def select_all(self):
        qpp = QPainterPath()
        qpp.addRect(
            QRect(
                0,
                0,
                self._document_size.width(),
                self._document_size.height(),
            ).normalized()
        )
        self._emit_selection_command(self.selection_shape, qpp)

    def select_none(self):
        self._emit_selection_command(self.selection_shape, None)

    def invert_selection(self):
        current_selection = clone_selection_path(self.selection_shape)
        if current_selection is None:
            return
        qpp = QPainterPath()
        qpp.addRect(
            QRect(
                0,
                0,
                self._document_size.width(),
                self._document_size.height(),
            ).normalized()
        )
        if not current_selection.isEmpty():
            new_shape = qpp.subtracted(current_selection)
        else:
            new_shape = qpp
        self._emit_selection_command(current_selection, new_shape)

    def get_selection_mask_pil(self) -> Image.Image:
        if self.selection_shape is None:
            return None

        mask = QImage(self._document_size, QImage.Format_ARGB32)
        mask.fill(Qt.black)

        painter = QPainter(mask)
        painter.setBrush(Qt.white)
        painter.setPen(Qt.white)
        painter.drawPath(self.selection_shape)
        painter.end()

        return ImageQt.fromqimage(mask)

    def enterEvent(self, event):
        self.setFocus()
        self.mouse_over_canvas = True
        current_tool_name = getattr(self.current_tool, "name", None)
        if current_tool_name != self.drawing_context.tool:
            self.on_tool_changed(self.drawing_context.tool)
        elif self.current_tool is not None:
            self.setCursor(self.current_tool.cursor)
        self.update()
        self.zoom_changed.emit(self.zoom)
        doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(doc_pos)

    def leaveEvent(self, event):
        self.mouse_over_canvas = False
        self.unsetCursor()
        if self._ruler_handle_drag is None:
            self._ruler_handle_prev_cursor = None
        self._ruler_handle_hover = None
        self.update()

    def get_doc_coords(self, canvas_pos, wrap=True):
        doc_width_scaled = self._document_size.width() * self.zoom
        doc_height_scaled = self._document_size.height() * self.zoom
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        if self.zoom == 0:
            return QPoint(0, 0)
        doc_x = (canvas_pos.x() - x_offset) / self.zoom
        doc_y = (canvas_pos.y() - y_offset) / self.zoom
        if wrap and self.tile_preview_enabled:
            doc_width = self._document_size.width()
            doc_height = self._document_size.height()
            if doc_width:
                doc_x %= doc_width
            if doc_height:
                doc_y %= doc_height
        return QPoint(int(doc_x), int(doc_y))

    def get_canvas_coords(self, doc_pos):
        doc_width_scaled = self._document_size.width() * self.zoom
        doc_height_scaled = self._document_size.height() * self.zoom
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        return QPoint(
            doc_pos.x() * self.zoom + x_offset,
            doc_pos.y() * self.zoom + y_offset,
        )

    def _ai_output_edges_from_rect(self, rect: QRect) -> dict[str, int]:
        width = max(1, int(rect.width()))
        height = max(1, int(rect.height()))
        left = int(rect.x())
        top = int(rect.y())
        return {
            "left": left,
            "top": top,
            "right": left + width - 1,
            "bottom": top + height - 1,
        }

    def _ai_output_rect_from_edges(self, edges: dict[str, int]) -> QRect:
        left = int(edges.get("left", 0))
        top = int(edges.get("top", 0))
        right = int(edges.get("right", left))
        bottom = int(edges.get("bottom", top))
        width = max(1, right - left + 1)
        height = max(1, bottom - top + 1)
        return QRect(left, top, width, height)

    def _ai_output_clamp_edges(self, edges: dict[str, int]) -> dict[str, int]:
        doc_width = max(1, int(self._document_size.width()))
        doc_height = max(1, int(self._document_size.height()))
        min_width = min(32, doc_width)
        min_height = min(32, doc_height)

        left = max(0, min(int(edges.get("left", 0)), doc_width - 1))
        right = max(left, min(int(edges.get("right", left)), doc_width - 1))
        top = max(0, min(int(edges.get("top", 0)), doc_height - 1))
        bottom = max(top, min(int(edges.get("bottom", top)), doc_height - 1))

        width = right - left + 1
        if width < min_width:
            handle = self._ai_output_active_handle
            if handle == "left":
                left = max(0, right - (min_width - 1))
                if right - left + 1 < min_width:
                    right = min(doc_width - 1, left + min_width - 1)
            elif handle == "right":
                right = min(doc_width - 1, left + min_width - 1)
                if right - left + 1 < min_width:
                    left = max(0, right - (min_width - 1))
            else:
                deficit = min_width - width
                proposed_left = left - deficit // 2
                proposed_left = max(0, min(proposed_left, doc_width - min_width))
                left = proposed_left
                right = min(doc_width - 1, left + min_width - 1)
                if right - left + 1 < min_width:
                    left = max(0, right - (min_width - 1))

        height = bottom - top + 1
        if height < min_height:
            handle = self._ai_output_active_handle
            if handle == "top":
                top = max(0, bottom - (min_height - 1))
                if bottom - top + 1 < min_height:
                    bottom = min(doc_height - 1, top + min_height - 1)
            elif handle == "bottom":
                bottom = min(doc_height - 1, top + min_height - 1)
                if bottom - top + 1 < min_height:
                    top = max(0, bottom - (min_height - 1))
            else:
                deficit = min_height - height
                proposed_top = top - deficit // 2
                proposed_top = max(0, min(proposed_top, doc_height - min_height))
                top = proposed_top
                bottom = min(doc_height - 1, top + min_height - 1)
                if bottom - top + 1 < min_height:
                    top = max(0, bottom - (min_height - 1))

        return {"left": left, "top": top, "right": right, "bottom": bottom}

    def _ai_output_overlay_rect(self) -> QRectF | None:
        rect = self.ai_output_rect
        if rect.width() <= 0 or rect.height() <= 0:
            return None

        top_left = self.get_canvas_coords(rect.topLeft())
        bottom_right_point = QPoint(
            rect.x() + rect.width(),
            rect.y() + rect.height(),
        )
        bottom_right = self.get_canvas_coords(bottom_right_point)
        return QRectF(QPointF(top_left), QPointF(bottom_right)).normalized()

    def _ai_output_handle_rects(self) -> dict[str, QRectF]:
        overlay_rect = self._ai_output_overlay_rect()
        if overlay_rect is None:
            return {}

        center = overlay_rect.center()
        points = {
            "left": QPointF(overlay_rect.left(), center.y()),
            "right": QPointF(overlay_rect.right(), center.y()),
            "top": QPointF(center.x(), overlay_rect.top()),
            "bottom": QPointF(center.x(), overlay_rect.bottom()),
        }

        half = self._ai_output_handle_size / 2.0
        rects: dict[str, QRectF] = {}
        for name, point in points.items():
            rects[name] = QRectF(
                point.x() - half,
                point.y() - half,
                self._ai_output_handle_size,
                self._ai_output_handle_size,
            )
        return rects

    def _ai_output_hit_test_handles(self, pos: QPointF) -> str | None:
        for name, rect in self._ai_output_handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def _set_ai_output_cursor(self, handle: str | None):
        if handle in {"left", "right"}:
            self.setCursor(Qt.SizeHorCursor)
        elif handle in {"top", "bottom"}:
            self.setCursor(Qt.SizeVerCursor)
        elif handle == "move":
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _ai_output_doc_pos_from_event(self, pos: QPointF) -> QPoint:
        doc_point = self.get_doc_coords(pos.toPoint(), wrap=False)
        doc_width = max(1, int(self._document_size.width()))
        doc_height = max(1, int(self._document_size.height()))
        x = max(0, min(doc_point.x(), doc_width - 1))
        y = max(0, min(doc_point.y(), doc_height - 1))
        return QPoint(x, y)

    def _update_ai_output_hover(self, pos: QPointF):
        if not self.ai_output_edit_enabled or self._ai_output_active_handle:
            return

        handle = self._ai_output_hit_test_handles(pos)
        if handle != self._ai_output_hover_handle:
            self._ai_output_hover_handle = handle
            self.update()

        overlay_rect = self._ai_output_overlay_rect()
        if handle:
            self._set_ai_output_cursor(handle)
        elif overlay_rect and overlay_rect.contains(pos):
            self._set_ai_output_cursor("move")
        else:
            self.setCursor(Qt.ArrowCursor)

    def _handle_ai_output_mouse_press(self, event: QMouseEvent) -> bool:
        if not self.ai_output_edit_enabled or event.button() != Qt.LeftButton:
            return False

        overlay_rect = self._ai_output_overlay_rect()
        handle = self._ai_output_hit_test_handles(event.position())
        inside = overlay_rect.contains(event.position()) if overlay_rect else False

        if handle is None and not inside:
            self._ai_output_hover_handle = None
            self._ai_output_active_handle = None
            self.setCursor(Qt.ArrowCursor)
            return True

        self._ai_output_active_handle = handle or "move"
        self._ai_output_hover_handle = handle
        self._ai_output_initial_edges = self._ai_output_edges_from_rect(self.ai_output_rect)
        doc_point = self._ai_output_doc_pos_from_event(event.position())

        if self._ai_output_active_handle == "move":
            self._ai_output_move_offset = QPointF(
                doc_point.x() - self._ai_output_initial_edges["left"],
                doc_point.y() - self._ai_output_initial_edges["top"],
            )
            self._set_ai_output_cursor("move")
        else:
            self._set_ai_output_cursor(self._ai_output_active_handle)
        return True

    def _drag_ai_output(self, pos: QPointF):
        if self._ai_output_active_handle is None:
            return

        if self._ai_output_initial_edges is None:
            self._ai_output_initial_edges = self._ai_output_edges_from_rect(
                self.ai_output_rect
            )

        doc_point = self._ai_output_doc_pos_from_event(pos)
        edges = dict(self._ai_output_initial_edges)
        handle = self._ai_output_active_handle

        if handle == "left":
            edges["left"] = min(doc_point.x(), edges["right"])
        elif handle == "right":
            edges["right"] = max(doc_point.x(), edges["left"])
        elif handle == "top":
            edges["top"] = min(doc_point.y(), edges["bottom"])
        elif handle == "bottom":
            edges["bottom"] = max(doc_point.y(), edges["top"])
        elif handle == "move":
            width = edges["right"] - edges["left"] + 1
            height = edges["bottom"] - edges["top"] + 1
            offset_x = int(round(self._ai_output_move_offset.x()))
            offset_y = int(round(self._ai_output_move_offset.y()))
            left = doc_point.x() - offset_x
            top = doc_point.y() - offset_y

            doc_width = max(1, int(self._document_size.width()))
            doc_height = max(1, int(self._document_size.height()))

            left = max(0, min(left, doc_width - width))
            top = max(0, min(top, doc_height - height))

            edges["left"] = left
            edges["right"] = left + width - 1
            edges["top"] = top
            edges["bottom"] = top + height - 1

        edges = self._ai_output_clamp_edges(edges)
        rect = self._ai_output_rect_from_edges(edges)
        if rect == self.ai_output_rect:
            return

        self.ai_output_rect = rect
        self.update()
        if self.app is not None:
            self.app.set_ai_output_rect(rect)

    def _initialize_ruler_handles(self) -> None:
        width = float(max(0, self._document_size.width()))
        height = float(max(0, self._document_size.height()))

        if width <= 0 and height <= 0:
            self._ruler_start = QPointF(0.0, 0.0)
            self._ruler_end = QPointF(0.0, 0.0)
            self._emit_ruler_distance()
            return

        center_x = width / 2.0
        center_y = height / 2.0
        span = max(1.0, max(width, height) / 3.0)
        start_x = center_x - span / 2.0
        end_x = center_x + span / 2.0

        if start_x < 0.0:
            end_x -= start_x
            start_x = 0.0
        if end_x > width:
            start_x -= end_x - width
            end_x = width

        start_point = QPointF(start_x, center_y)
        end_point = QPointF(end_x, center_y)

        start_point = self._clamp_point_to_document(start_point)
        end_point = self._clamp_point_to_document(end_point)

        if (
            math.isclose(start_point.x(), end_point.x())
            and math.isclose(start_point.y(), end_point.y())
        ):
            fallback = self._clamp_point_to_document(
                QPointF(end_point.x() + 1.0, end_point.y())
            )
            if (
                math.isclose(fallback.x(), end_point.x())
                and math.isclose(fallback.y(), end_point.y())
            ):
                fallback = self._clamp_point_to_document(
                    QPointF(end_point.x(), end_point.y() + 1.0)
                )
            end_point = fallback

        self._ruler_start = start_point
        self._ruler_end = end_point
        self._emit_ruler_distance()

    def _clamp_point_to_document(
        self, point: QPointF, *, allow_outside: bool = False
    ) -> QPointF:
        if allow_outside:
            return QPointF(point)
        width = float(max(0, self._document_size.width()))
        height = float(max(0, self._document_size.height()))
        clamped_x = min(max(point.x(), 0.0), width)
        clamped_y = min(max(point.y(), 0.0), height)
        return QPointF(clamped_x, clamped_y)

    def _emit_ruler_distance(self) -> None:
        if not self.ruler_enabled:
            self.ruler_distance_changed.emit(None)
            return
        if self._ruler_start is None or self._ruler_end is None:
            self.ruler_distance_changed.emit(None)
            return

        dx = float(self._ruler_end.x() - self._ruler_start.x())
        dy = float(self._ruler_end.y() - self._ruler_start.y())
        distance = math.hypot(dx, dy)
        self.ruler_distance_changed.emit(distance)

    def _doc_point_to_canvas(self, point: QPointF) -> QPointF:
        target_rect = self.get_target_rect()
        return QPointF(
            target_rect.x() + point.x() * self.zoom,
            target_rect.y() + point.y() * self.zoom,
        )

    def _canvas_pos_to_doc_point(self, canvas_pos: QPoint) -> QPointF:
        zoom = self.zoom
        if zoom == 0:
            return QPointF(0.0, 0.0)
        target_rect = self.get_target_rect()
        doc_x = (canvas_pos.x() - target_rect.x()) / zoom
        doc_y = (canvas_pos.y() - target_rect.y()) / zoom
        return QPointF(doc_x, doc_y)

    def _ruler_handle_centers(self) -> dict[str, QPointF]:
        if not self.ruler_enabled:
            return {}
        if self._ruler_start is None or self._ruler_end is None:
            return {}
        if self.zoom <= 0:
            return {}
        return {
            "start": self._doc_point_to_canvas(self._ruler_start),
            "end": self._doc_point_to_canvas(self._ruler_end),
        }

    def _hit_test_ruler_handles(self, pos: QPoint) -> str | None:
        if not self.ruler_enabled:
            return None
        hit_radius = float(self._ruler_handle_radius + self._ruler_handle_hit_padding)
        if hit_radius <= 0:
            return None
        for name, center in self._ruler_handle_centers().items():
            dx = pos.x() - center.x()
            dy = pos.y() - center.y()
            if math.hypot(dx, dy) <= hit_radius:
                return name
        return None

    def _update_ruler_handle_from_position(
        self,
        pos: QPoint,
        handle: str,
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,
    ) -> None:
        point = self._canvas_pos_to_doc_point(pos)
        if modifiers & Qt.ControlModifier:
            point = QPointF(round(point.x()), round(point.y()))
        if (
            modifiers & Qt.ShiftModifier
            and handle in {"start", "end"}
            and self._ruler_start is not None
            and self._ruler_end is not None
        ):
            start_point = self._ruler_start
            end_point = self._ruler_end
            if handle == "start":
                current_point = start_point
            else:
                current_point = end_point

            delta_x = point.x() - current_point.x()
            delta_y = point.y() - current_point.y()

            translated_start = QPointF(
                start_point.x() + delta_x, start_point.y() + delta_y
            )
            translated_end = QPointF(
                end_point.x() + delta_x, end_point.y() + delta_y
            )

            self._ruler_start = translated_start
            self._ruler_end = translated_end
        else:
            if handle == "start":
                self._ruler_start = point
            elif handle == "end":
                self._ruler_end = point
        self.update()
        self._emit_ruler_distance()

    def _update_ruler_hover_state(self, handle: str | None) -> None:
        if handle == self._ruler_handle_hover:
            return

        if handle is not None:
            if self._ruler_handle_prev_cursor is None:
                self._ruler_handle_prev_cursor = self.cursor()
            if self._ruler_handle_drag is None:
                self.setCursor(Qt.OpenHandCursor)
        elif self._ruler_handle_hover is not None:
            if self._ruler_handle_drag is None:
                if self._ruler_handle_prev_cursor is not None:
                    self.setCursor(self._ruler_handle_prev_cursor)
                else:
                    self.setCursor(self.current_tool.cursor)
            self._ruler_handle_prev_cursor = None

        self._ruler_handle_hover = handle

    @Slot(bool)
    def toggle_ruler(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.ruler_enabled:
            return

        self.ruler_enabled = enabled

        if enabled:
            if self._ruler_start is None or self._ruler_end is None:
                self._initialize_ruler_handles()
        else:
            self._ruler_handle_drag = None
            self._ruler_handle_hover = None
            if self.mouse_over_canvas:
                if self._ruler_handle_prev_cursor is not None:
                    self.setCursor(self._ruler_handle_prev_cursor)
                else:
                    self.setCursor(self.current_tool.cursor)
            self._ruler_handle_prev_cursor = None

        self.update()
        self._emit_ruler_distance()

    def mousePressEvent(self, event):
        if self.ai_output_edit_enabled and event.button() == Qt.LeftButton:
            if self._handle_ai_output_mouse_press(event):
                return

        pos = event.position().toPoint()
        if event.button() == Qt.LeftButton:
            if self.ruler_enabled:
                handle = self._hit_test_ruler_handles(pos)
                if handle is not None:
                    self._ruler_handle_drag = handle
                    self._ruler_handle_hover = handle
                    if self._ruler_handle_prev_cursor is None:
                        self._ruler_handle_prev_cursor = self.cursor()
                    self.setCursor(Qt.ClosedHandCursor)
                    self._update_ruler_handle_from_position(
                        pos, handle, modifiers=event.modifiers()
                    )
                    return

            handle = self._hit_test_mirror_handles(pos)
            if handle is not None:
                self._mirror_handle_drag = handle
                self._mirror_handle_hover = handle
                self._update_mirror_axis_from_position(pos, handle)
                if self._mirror_handle_prev_cursor is None:
                    self._mirror_handle_prev_cursor = self.cursor()
                self.setCursor(Qt.ClosedHandCursor)
                return

        self.input_handler.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.ai_output_edit_enabled:
            if event.buttons() & Qt.LeftButton:
                self._update_cursor_position_from_event(event)
                if self._ai_output_active_handle is not None:
                    self._drag_ai_output(event.position())
                    self._set_ai_output_cursor(self._ai_output_active_handle)
                return
            if event.buttons() & Qt.MiddleButton:
                self.input_handler.mouseMoveEvent(event)
                return
            self._update_cursor_position_from_event(event)
            if not event.buttons():
                self._update_ai_output_hover(event.position())
            return
        pos = event.position().toPoint()
        if self._mirror_handle_drag is not None or self._ruler_handle_drag is not None:
            self._update_cursor_position_from_event(event)
            self._update_ruler_handle_from_position(
                pos,
                self._ruler_handle_drag,
                modifiers=event.modifiers(),
            )
            return

        if self._mirror_handle_drag is not None:
            self._update_cursor_position_from_event(event)
            self._update_mirror_axis_from_position(pos, self._mirror_handle_drag)
            return

        self.input_handler.mouseMoveEvent(event)

        ruler_handle = None
        if self.ruler_enabled:
            ruler_handle = self._hit_test_ruler_handles(pos)
            self._update_ruler_hover_state(ruler_handle)

        if ruler_handle is not None:
            return

        handle = self._hit_test_mirror_handles(pos)
        if handle != self._mirror_handle_hover:
            if handle is not None:
                if self._mirror_handle_drag is None:
                    if self._mirror_handle_prev_cursor is None:
                        self._mirror_handle_prev_cursor = self.cursor()
                    self.setCursor(Qt.OpenHandCursor)
            elif self._mirror_handle_hover is not None:
                if self._mirror_handle_prev_cursor is not None:
                    self.setCursor(self._mirror_handle_prev_cursor)
                else:
                    self.setCursor(self.current_tool.cursor)
                self._mirror_handle_prev_cursor = None
        self._mirror_handle_hover = handle

    def mouseReleaseEvent(self, event):
        if self.ai_output_edit_enabled and event.button() == Qt.LeftButton:
            if self._ai_output_active_handle is not None:
                self._drag_ai_output(event.position())
                self._ai_output_active_handle = None
                self._ai_output_initial_edges = None
                self._ai_output_move_offset = QPointF(0, 0)
            self._update_ai_output_hover(event.position())
            return
        pos = event.position().toPoint()
        if (
            self._ruler_handle_drag is not None
            and event.button() == Qt.LeftButton
        ):
            self._update_cursor_position_from_event(event)
            self._update_ruler_handle_from_position(
                pos,
                self._ruler_handle_drag,
                modifiers=event.modifiers(),
            )
            self._ruler_handle_drag = None
            handle = None
            if self.ruler_enabled:
                handle = self._hit_test_ruler_handles(pos)
            if handle is not None:
                self.setCursor(Qt.OpenHandCursor)
            else:
                if self._ruler_handle_prev_cursor is not None:
                    self.setCursor(self._ruler_handle_prev_cursor)
                else:
                    self.setCursor(self.current_tool.cursor)
                self._ruler_handle_prev_cursor = None
            self._ruler_handle_hover = handle
            return

        if (
            self._mirror_handle_drag is not None
            and event.button() == Qt.LeftButton
        ):
            self._update_mirror_axis_from_position(pos, self._mirror_handle_drag)
            self._mirror_handle_drag = None
            handle = self._hit_test_mirror_handles(pos)
            if handle is not None:
                self.setCursor(Qt.OpenHandCursor)
            else:
                if self._mirror_handle_prev_cursor is not None:
                    self.setCursor(self._mirror_handle_prev_cursor)
                else:
                    self.setCursor(self.current_tool.cursor)
                self._mirror_handle_prev_cursor = None
            self._mirror_handle_hover = handle
            return

        self.input_handler.mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        self.input_handler.wheelEvent(event)

    def get_target_rect(self):
        doc_width = self._document_size.width()
        doc_height = self._document_size.height()
        canvas_width = self.width()
        canvas_height = self.height()

        doc_width_scaled = doc_width * self.zoom
        doc_height_scaled = doc_height * self.zoom

        x = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y = (canvas_height - doc_height_scaled) / 2 + self.y_offset
        return QRect(x, y, int(doc_width_scaled), int(doc_height_scaled))

    def _reset_mirror_axes(self, *, force_center: bool = False):
        width = self._document_size.width()
        if width > 0:
            current = self.drawing_context.mirror_x_position
            if force_center or current is None:
                self.drawing_context.set_mirror_x_position(
                    self._default_mirror_position(width)
                )
            else:
                clamped = self._clamp_mirror_position(current, width)
                self.drawing_context.set_mirror_x_position(clamped)

        height = self._document_size.height()
        if height > 0:
            current = self.drawing_context.mirror_y_position
            if force_center or current is None:
                self.drawing_context.set_mirror_y_position(
                    self._default_mirror_position(height)
                )
            else:
                clamped = self._clamp_mirror_position(current, height)
                self.drawing_context.set_mirror_y_position(clamped)

    @staticmethod
    def _default_mirror_position(length: int) -> float:
        if length <= 0:
            return 0.0
        return (length - 1) / 2.0

    @staticmethod
    def _clamp_mirror_position(value: float, length: int) -> float:
        if length <= 0:
            return value
        minimum = -0.5
        maximum = length - 0.5
        return max(minimum, min(maximum, value))

    def _resolve_mirror_x_position(self) -> float | None:
        width = self._document_size.width()
        if width <= 0:
            return None
        position = self.drawing_context.mirror_x_position
        if position is None:
            return self._default_mirror_position(width)
        return self._clamp_mirror_position(position, width)

    def _resolve_mirror_y_position(self) -> float | None:
        height = self._document_size.height()
        if height <= 0:
            return None
        position = self.drawing_context.mirror_y_position
        if position is None:
            return self._default_mirror_position(height)
        return self._clamp_mirror_position(position, height)

    def _mirror_handle_rects(self) -> dict[str, QRect]:
        rects: dict[str, QRect] = {}
        target_rect = self.get_target_rect()
        zoom = self.zoom
        if zoom <= 0:
            return rects

        radius = self._mirror_handle_radius
        diameter = radius * 2
        margin = self._mirror_handle_margin
        canvas_width = self.width()
        canvas_height = self.height()
        max_x = canvas_width - radius
        max_y = canvas_height - radius
        if max_x < radius:
            max_x = radius
        if max_y < radius:
            max_y = radius

        if self.drawing_context.mirror_x:
            axis_x = self._resolve_mirror_x_position()
            if axis_x is not None:
                center_x = target_rect.x() + (axis_x + 0.5) * zoom
                center_y = target_rect.y() - margin
                center_x = max(radius, min(max_x, center_x))
                center_y = max(radius, min(max_y, center_y))
                rects["x"] = QRect(
                    int(round(center_x - radius)),
                    int(round(center_y - radius)),
                    diameter,
                    diameter,
                )

        if self.drawing_context.mirror_y:
            axis_y = self._resolve_mirror_y_position()
            if axis_y is not None:
                center_y = target_rect.y() + (axis_y + 0.5) * zoom
                center_x = target_rect.x() - margin
                center_x = max(radius, min(max_x, center_x))
                center_y = max(radius, min(max_y, center_y))
                rects["y"] = QRect(
                    int(round(center_x - radius)),
                    int(round(center_y - radius)),
                    diameter,
                    diameter,
                )

        return rects

    def _hit_test_mirror_handles(self, pos: QPoint) -> str | None:
        for axis, rect in self._mirror_handle_hit_rects().items():
            if rect.contains(pos):
                return axis
        return None

    def _mirror_handle_hit_rects(self) -> dict[str, QRect]:
        padding = max(0, int(self._mirror_handle_hit_padding))
        rects = self._mirror_handle_rects()
        if padding <= 0:
            return rects
        return {
            axis: rect.adjusted(-padding, -padding, padding, padding)
            for axis, rect in rects.items()
        }

    def _update_mirror_axis_from_position(self, pos: QPoint, axis: str):
        target_rect = self.get_target_rect()
        zoom = self.zoom
        if zoom <= 0:
            return

        if axis == "x":
            length = self._document_size.width()
            if length <= 0:
                return
            relative = (pos.x() - target_rect.x()) / zoom - 0.5
            clamped = self._clamp_mirror_position(relative, length)
            self.drawing_context.set_mirror_x_position(clamped)
        elif axis == "y":
            length = self._document_size.height()
            if length <= 0:
                return
            relative = (pos.y() - target_rect.y()) / zoom - 0.5
            clamped = self._clamp_mirror_position(relative, length)
            self.drawing_context.set_mirror_y_position(clamped)

    def _update_cursor_position_from_event(self, event: QMouseEvent):
        pos = event.position().toPoint()
        self.cursor_doc_pos = self.get_doc_coords(pos, wrap=False)
        self.cursor_pos_changed.emit(self.cursor_doc_pos)

    def set_document(self, document):
        self.document = document
        self.set_document_size(QSize(document.width, document.height))
        if hasattr(document, "get_ai_output_rect"):
            rect = document.get_ai_output_rect()
            if rect is not None:
                self.set_ai_output_rect(rect)
        self.update()

    def set_ai_output_rect(self, rect: QRect | None):
        if rect is None:
            rect = QRect(0, 0, self._document_size.width(), self._document_size.height())
        normalized = QRect(rect)
        if normalized == self.ai_output_rect:
            return
        self.ai_output_rect = normalized
        if not self.ai_output_edit_enabled:
            self._ai_output_active_handle = None
            self._ai_output_hover_handle = None
        self.update()

    def enable_ai_output_editing(self, enabled: bool):
        normalized = bool(enabled)
        if normalized == self.ai_output_edit_enabled:
            return
        self.ai_output_edit_enabled = normalized
        self._ai_output_active_handle = None
        self._ai_output_hover_handle = None
        self._ai_output_initial_edges = None
        self._ai_output_move_offset = QPointF(0, 0)
        if normalized:
            self.setCursor(Qt.ArrowCursor)
        else:
            if self.current_tool is not None:
                self.setCursor(self.current_tool.cursor)
        self.update()

    def set_onion_skin_enabled(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self.onion_skin_enabled:
            return
        self.onion_skin_enabled = normalized
        self.update()

    def set_animation_playback_active(self, playing: bool) -> None:
        normalized = bool(playing)
        if normalized == self.animation_playback_active:
            return
        self.animation_playback_active = normalized
        self.update()

    def set_onion_skin_range(
        self, *, previous: int | None = None, next: int | None = None
    ) -> None:
        changed = False
        if previous is not None:
            try:
                normalized_prev = int(previous)
            except (TypeError, ValueError):
                normalized_prev = self.onion_skin_prev_frames
            else:
                normalized_prev = max(0, normalized_prev)
            if normalized_prev != self.onion_skin_prev_frames:
                self.onion_skin_prev_frames = normalized_prev
                changed = True
        if next is not None:
            try:
                normalized_next = int(next)
            except (TypeError, ValueError):
                normalized_next = self.onion_skin_next_frames
            else:
                normalized_next = max(0, normalized_next)
            if normalized_next != self.onion_skin_next_frames:
                self.onion_skin_next_frames = normalized_next
                changed = True
        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.renderer.paint(painter, self.document)

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.update()

    def set_grid_settings(
        self,
        *,
        major_visible=None,
        major_spacing=None,
        minor_visible=None,
        minor_spacing=None,
        major_color=None,
        minor_color=None,
    ):
        if major_visible is not None:
            self.grid_major_visible = bool(major_visible)
        if major_spacing is not None:
            self.grid_major_spacing = max(1, int(major_spacing))
        if minor_visible is not None:
            self.grid_minor_visible = bool(minor_visible)
        if minor_spacing is not None:
            self.grid_minor_spacing = max(1, int(minor_spacing))
        if major_color is not None:
            color = QColor(major_color)
            if color.isValid():
                self.grid_major_color = color
        if minor_color is not None:
            color = QColor(minor_color)
            if color.isValid():
                self.grid_minor_color = color
        self.update()

    def set_ruler_settings(self, *, segments=None, interval=None):
        if segments is None and interval is not None:
            segments = interval
        if segments is None:
            return
        try:
            segments_value = int(segments)
        except (TypeError, ValueError):
            return
        segments_value = max(1, segments_value)
        if segments_value == self._ruler_segments:
            return
        self._ruler_segments = segments_value
        self.update()

    def get_ruler_settings(self):
        return {"segments": int(self._ruler_segments)}

    def get_grid_settings(self):
        return {
            "major_visible": self.grid_major_visible,
            "major_spacing": self.grid_major_spacing,
            "minor_visible": self.grid_minor_visible,
            "minor_spacing": self.grid_minor_spacing,
            "major_color": self.grid_major_color.name(QColor.NameFormat.HexArgb),
            "minor_color": self.grid_minor_color.name(QColor.NameFormat.HexArgb),
        }

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass

    def set_initial_zoom(self):
        canvas_width = self.width()
        canvas_height = self.height()
        doc_width = self._document_size.width()
        doc_height = self._document_size.height()

        if doc_width == 0 or doc_height == 0:
            return

        zoom_x = (0.8 * canvas_width) / doc_width
        zoom_y = (0.8 * canvas_height) / doc_height
        self.zoom = min(zoom_x, zoom_y)
        self.min_zoom = min(self.min_zoom, self.zoom)
        self.zoom_changed.emit(self.zoom)
        self.update()

        