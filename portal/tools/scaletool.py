import math

from PySide6.QtCore import Qt, QPointF, QRect, QRectF, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QTransform,
)

from portal.commands.layer_commands import (
    ScaleLayerCommand,
    apply_qimage_transform_nearest,
)
from portal.tools._layer_tracker import ActiveLayerTracker
from portal.tools.basetool import BaseTool
from ._transform_style import (
    TRANSFORM_DEFAULT_CURSOR,
    TRANSFORM_GIZMO_ACTIVE_COLOR,
    TRANSFORM_GIZMO_BASE_COLOR,
    TRANSFORM_GIZMO_HOVER_COLOR,
)


class ScaleTool(BaseTool):
    """Interactive scaling helper composed by :class:`TransformTool`."""

    # ``name`` is ``None`` so discovery skips this helper. The public transform
    # tool exposes scaling alongside move and rotate.
    name = None
    icon = "icons/toolscale.png"
    category = "draw"
    scale_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = TRANSFORM_DEFAULT_CURSOR
        self.scale_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.drag_mode: str | None = None
        self.original_image: QImage | None = None
        self.original_selection_shape: QPainterPath | None = None
        self.selection_source_image: QImage | None = None
        self._hover_handle: str | None = None
        self._active_handle: str | None = None
        self._handle_size = 14.0
        self._bounds_dirty = True
        self._base_edge_rect_doc: QRectF | None = None
        self._scaled_edge_rect_doc: QRectF | None = None
        self._drag_base_edge_rect_doc: QRectF | None = None
        self._drag_handle_axis: str | None = None
        self._current_pivot_doc: QPointF | None = None
        self._layer_tracker = ActiveLayerTracker(canvas)

        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)

    # ------------------------------------------------------------------
    def _on_canvas_selection_changed(self, *_):
        if self.drag_mode == "scale":
            return

        self._drag_base_edge_rect_doc = None
        self._current_pivot_doc = None
        self._hover_handle = None
        self._refresh_base_rect()
        self.canvas.setCursor(self.cursor)
        self.canvas.update()

    # ------------------------------------------------------------------
    def activate(self):
        self.scale_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scale_changed.emit(self.scale_factor)
        self.drag_mode = None
        self._hover_handle = None
        self._active_handle = None
        self._drag_base_edge_rect_doc = None
        self._drag_handle_axis = None
        self._current_pivot_doc = None
        self._bounds_dirty = True
        self._layer_tracker.reset()
        self._refresh_base_rect()

    # ------------------------------------------------------------------
    def deactivate(self):
        if self.drag_mode == "scale":
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False

            layer_manager = self._get_active_layer_manager()
            if (
                self.original_image is not None
                and layer_manager is not None
                and layer_manager.active_layer is not None
            ):
                layer_manager.active_layer.image = self.original_image
                layer_manager.active_layer.on_image_change.emit()

            if self.original_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(
                    QPainterPath(self.original_selection_shape)
                )

        self.original_image = None
        self.selection_source_image = None
        self.original_selection_shape = None
        self.scale_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scale_changed.emit(self.scale_factor)
        self.drag_mode = None
        self._hover_handle = None
        self._active_handle = None
        self._drag_base_edge_rect_doc = None
        self._drag_handle_axis = None
        self._current_pivot_doc = None
        self._bounds_dirty = True
        self._layer_tracker.reset()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._ensure_base_rect()

        canvas_pos = QPointF(event.position())
        handle = self._hit_test_handles(canvas_pos)

        if handle is not None:
            if self._start_scale_drag(handle):
                self._update_cursor()
            return

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        if self._active_handle is not None:
            return

        self._ensure_base_rect()

        canvas_pos = QPointF(event.position())
        handle = self._hit_test_handles(canvas_pos)

        if handle != self._hover_handle:
            self._hover_handle = handle
            self._update_cursor()
            self.canvas.update()

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        if self.drag_mode == "scale" and self._active_handle is not None:
            result = self._compute_scale_from_handle(event)
            if result is None:
                return

            scale_x, scale_y, pivot = result

            self.scale_x = scale_x
            self.scale_y = scale_y
            self._current_pivot_doc = pivot

            if self._drag_handle_axis == "horizontal":
                display_value = self.scale_x
            elif self._drag_handle_axis == "vertical":
                display_value = self.scale_y
            else:
                display_value = max(self.scale_x, self.scale_y)

            if not math.isclose(display_value, self.scale_factor, abs_tol=1e-3):
                self.scale_factor = display_value
                self.scale_changed.emit(self.scale_factor)

            self._update_scaled_rect_from_current_scale()
            self._update_preview_image()

            self.canvas.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        if self.drag_mode != "scale":
            self.drag_mode = None
            self._active_handle = None
            self._update_cursor()
            return

        self.canvas.temp_image = None
        self.canvas.temp_image_replaces_active_layer = False

        layer_manager = self._get_active_layer_manager()
        active_layer = None if layer_manager is None else layer_manager.active_layer

        if active_layer is not None and self.original_image is not None:
            if math.isclose(self.scale_x, 1.0, abs_tol=1e-3) and math.isclose(
                self.scale_y, 1.0, abs_tol=1e-3
            ):
                if self.original_selection_shape is not None:
                    self.canvas._update_selection_and_emit_size(
                        QPainterPath(self.original_selection_shape)
                    )
            else:
                center_doc = self._current_pivot_point().toPoint()
                selection_shape = (
                    QPainterPath(self.original_selection_shape)
                    if self.original_selection_shape is not None
                    else None
                )
                scaled_shape = None
                if self.original_selection_shape is not None:
                    transform = self._build_transform()
                    scaled_shape = transform.map(self.original_selection_shape)
                    self.canvas._update_selection_and_emit_size(scaled_shape)

                command = ScaleLayerCommand(
                    active_layer,
                    self.scale_x,
                    self.scale_y,
                    center_doc,
                    selection_shape,
                    canvas=self.canvas,
                    scaled_selection_shape=scaled_shape,
                )
                self.command_generated.emit(command)

        elif self.original_selection_shape is not None:
            self.canvas._update_selection_and_emit_size(
                QPainterPath(self.original_selection_shape)
            )

        self.original_image = None
        self.selection_source_image = None
        self.original_selection_shape = None
        self.scale_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scale_changed.emit(self.scale_factor)
        self.drag_mode = None
        self._active_handle = None
        self._hover_handle = None
        self._drag_base_edge_rect_doc = None
        self._drag_handle_axis = None
        self._scaled_edge_rect_doc = None
        self._current_pivot_doc = None
        self._bounds_dirty = True
        self._update_cursor()
        self.canvas.update()

    # ------------------------------------------------------------------
    def refresh_handles_from_document(self) -> None:
        """Sync handle geometry with the latest selection or layer bounds."""

        self._drag_base_edge_rect_doc = None
        self._current_pivot_doc = None
        self._refresh_base_rect()
        self.canvas.update()

    # ------------------------------------------------------------------
    def _update_preview_image(self):
        if self.original_image is None:
            return

        transform = self._build_transform()

        if self.original_selection_shape is not None:
            image_to_modify = self.original_image.copy()
            painter = QPainter(image_to_modify)
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            painter.setClipPath(self.original_selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(self.original_selection_shape, Qt.transparent)
            painter.end()

            source_image = (
                self.selection_source_image
                if self.selection_source_image is not None
                else self.original_image
            )

            if not apply_qimage_transform_nearest(
                image_to_modify, source_image, transform
            ):
                self.canvas.temp_image = self.original_image.copy()
                if self._drag_base_edge_rect_doc is not None:
                    self._scaled_edge_rect_doc = QRectF(self._drag_base_edge_rect_doc)
                return

            scaled_shape = transform.map(self.original_selection_shape)
            self.canvas._update_selection_and_emit_size(scaled_shape)
        else:
            image_to_modify = QImage(
                self.original_image.size(),
                self.original_image.format(),
            )
            image_to_modify.fill(Qt.transparent)

            if not apply_qimage_transform_nearest(
                image_to_modify, self.original_image, transform
            ):
                self.canvas.temp_image = self.original_image.copy()
                if self._drag_base_edge_rect_doc is not None:
                    self._scaled_edge_rect_doc = QRectF(self._drag_base_edge_rect_doc)
                return

        self.canvas.temp_image = image_to_modify

    # ------------------------------------------------------------------
    def draw_overlay(self, painter):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        _, overlay_rect, handle_rects = self._overlay_geometry()

        base_color = QColor(TRANSFORM_GIZMO_BASE_COLOR)
        hover_color = QColor(TRANSFORM_GIZMO_HOVER_COLOR)
        active_color = QColor(TRANSFORM_GIZMO_ACTIVE_COLOR)

        if overlay_rect is not None:
            border_pen = QPen(base_color)
            border_pen.setWidth(1)
            border_pen.setCosmetic(True)
            painter.setPen(border_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(overlay_rect)

            handle_pen = QPen(base_color.darker(150))
            handle_pen.setWidth(1)
            handle_pen.setCosmetic(True)
            painter.setPen(handle_pen)

            for name, rect in handle_rects.items():
                if name == self._active_handle:
                    brush = active_color
                elif name == self._hover_handle:
                    brush = hover_color
                else:
                    brush = base_color
                painter.setBrush(brush)
                painter.drawRect(rect)

        text = self._scale_display_text()
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text) + 16
        text_height = metrics.height() + 8

        if overlay_rect is not None:
            text_rect = QRectF(
                overlay_rect.center().x() - text_width / 2,
                overlay_rect.top() - text_height - 6,
                text_width,
                text_height,
            )
        else:
            pivot_point = self._doc_to_canvas_point(self._current_pivot_point())
            text_rect = QRectF(
                pivot_point.x() - text_width / 2,
                pivot_point.y() - text_height - 6,
                text_width,
                text_height,
            )

        painter.setBrush(QColor(0, 0, 0, 160))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(text_rect, 4, 4)

        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(text_rect, Qt.AlignCenter, text)

        painter.restore()

    # ------------------------------------------------------------------
    def _start_scale_drag(self, handle: str) -> bool:
        layer_manager = self._get_active_layer_manager()
        if layer_manager is None or layer_manager.active_layer is None:
            return False

        base_rect = self._base_edge_rect_doc
        if base_rect is None or base_rect.isEmpty():
            return False

        if handle in ("left", "right") and math.isclose(base_rect.width(), 0.0):
            return False
        if handle in ("top", "bottom") and math.isclose(base_rect.height(), 0.0):
            return False

        active_layer = layer_manager.active_layer
        self.original_image = active_layer.image.copy()
        self.canvas.temp_image_replaces_active_layer = True
        self.original_selection_shape = None
        self.selection_source_image = None

        if self.canvas.selection_shape:
            self.original_selection_shape = QPainterPath(self.canvas.selection_shape)
            self.selection_source_image = QImage(
                self.original_image.size(),
                self.original_image.format(),
            )
            self.selection_source_image.fill(Qt.transparent)

            selection_painter = QPainter(self.selection_source_image)
            selection_painter.setRenderHint(QPainter.Antialiasing, False)
            selection_painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            selection_painter.setClipPath(self.original_selection_shape)
            selection_painter.drawImage(0, 0, self.original_image)
            selection_painter.end()

        if handle in ("left", "right"):
            self._drag_handle_axis = "horizontal"
            pivot_point = QPointF(
                base_rect.right() if handle == "left" else base_rect.left(),
                base_rect.center().y(),
            )
        else:
            self._drag_handle_axis = "vertical"
            pivot_point = QPointF(
                base_rect.center().x(),
                base_rect.bottom() if handle == "top" else base_rect.top(),
            )

        self.drag_mode = "scale"
        self._active_handle = handle
        self._hover_handle = handle
        self._drag_base_edge_rect_doc = QRectF(base_rect)
        self._current_pivot_doc = QPointF(pivot_point)
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scale_factor = 1.0
        self.scale_changed.emit(self.scale_factor)
        self._scaled_edge_rect_doc = QRectF(self._drag_base_edge_rect_doc)
        return True

    # ------------------------------------------------------------------
    def _compute_scale_from_handle(self, event) -> tuple[float, float, QPointF] | None:
        if self._active_handle is None or self._drag_base_edge_rect_doc is None:
            return None

        rect = self._drag_base_edge_rect_doc
        handle = self._active_handle
        canvas_pos = QPointF(event.position())
        doc_point = self._canvas_to_doc_point(canvas_pos)

        min_scale = 0.125
        scale_x = 1.0
        scale_y = 1.0

        if handle in ("left", "right"):
            width = rect.width()
            if math.isclose(width, 0.0):
                return None
            anchor_x = rect.right() if handle == "left" else rect.left()
            raw_width = (
                anchor_x - doc_point.x()
                if handle == "left"
                else doc_point.x() - anchor_x
            )
            min_width = width * min_scale
            if raw_width < min_width:
                raw_width = min_width
            scale_x = max(min_scale, raw_width / width)
        else:
            height = rect.height()
            if math.isclose(height, 0.0):
                return None
            anchor_y = rect.bottom() if handle == "top" else rect.top()
            raw_height = (
                anchor_y - doc_point.y()
                if handle == "top"
                else doc_point.y() - anchor_y
            )
            min_height = height * min_scale
            if raw_height < min_height:
                raw_height = min_height
            scale_y = max(min_scale, raw_height / height)

        if event.modifiers() & Qt.ShiftModifier:
            uniform = scale_x if handle in ("left", "right") else scale_y
            uniform = max(min_scale, uniform)
            scale_x = uniform
            scale_y = uniform

        pivot = self._current_pivot_doc
        if pivot is None:
            pivot = rect.center()

        return scale_x, scale_y, QPointF(pivot)

    # ------------------------------------------------------------------
    def _current_edge_rect_doc(self) -> QRectF | None:
        selection_shape = getattr(self.canvas, "selection_shape", None)
        if selection_shape:
            rect = selection_shape.boundingRect().toAlignedRect()
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                return QRectF(rect.left(), rect.top(), rect.width(), rect.height())

        if self._scaled_edge_rect_doc is not None and not self._scaled_edge_rect_doc.isEmpty():
            return QRectF(self._scaled_edge_rect_doc)

        self._ensure_base_rect()
        if self._base_edge_rect_doc is not None and not self._base_edge_rect_doc.isEmpty():
            return QRectF(self._base_edge_rect_doc)

        return None

    # ------------------------------------------------------------------
    def _refresh_base_rect(self):
        rect = self._calculate_target_edge_rect_doc()
        if rect is None:
            self._base_edge_rect_doc = None
            self._scaled_edge_rect_doc = None
        else:
            self._base_edge_rect_doc = QRectF(rect)
            self._scaled_edge_rect_doc = QRectF(rect)
        self._layer_tracker.refresh()
        self._bounds_dirty = False

    # ------------------------------------------------------------------
    def _ensure_base_rect(self):
        if self._layer_tracker.has_changed():
            self._bounds_dirty = True

        if self._bounds_dirty:
            self._refresh_base_rect()

    # ------------------------------------------------------------------
    def _calculate_target_edge_rect_doc(self) -> QRectF | None:
        selection_shape = getattr(self.canvas, "selection_shape", None)
        if selection_shape:
            rect = selection_shape.boundingRect().toAlignedRect()
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                return QRectF(rect.left(), rect.top(), rect.width(), rect.height())

        layer_manager = self._get_active_layer_manager()
        if layer_manager and layer_manager.active_layer is not None:
            image = layer_manager.active_layer.image
            if image is not None and not image.isNull():
                bounds = self._find_non_transparent_bounds(image)
                if bounds is None:
                    bounds = image.rect()
                if bounds.isValid() and bounds.width() > 0 and bounds.height() > 0:
                    return QRectF(bounds.left(), bounds.top(), bounds.width(), bounds.height())

        document = getattr(self.canvas, "document", None)
        if document is not None:
            width = getattr(document, "width", None)
            height = getattr(document, "height", None)
            if width is not None and height is not None:
                width_int = max(1, int(width))
                height_int = max(1, int(height))
                return QRectF(0, 0, width_int, height_int)

        return None

    # ------------------------------------------------------------------
    def _find_non_transparent_bounds(self, image: QImage) -> QRect | None:
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return None

        left = width
        right = -1
        top = height
        bottom = -1

        for y in range(height):
            row_left = None
            row_right = None

            for x in range(width):
                if image.pixelColor(x, y).alpha() > 0:
                    row_left = x
                    break

            if row_left is None:
                continue

            for x in range(width - 1, -1, -1):
                if image.pixelColor(x, y).alpha() > 0:
                    row_right = x
                    break

            if row_right is None:
                continue

            if row_left < left:
                left = row_left
            if row_right > right:
                right = row_right
            if top == height:
                top = y
            bottom = y

        if right < left or bottom < top:
            return None

        return QRect(left, top, right - left + 1, bottom - top + 1)

    # ------------------------------------------------------------------
    def _current_pivot_point(self) -> QPointF:
        if self._current_pivot_doc is not None:
            return QPointF(self._current_pivot_doc)

        rect = self._drag_base_edge_rect_doc or self._base_edge_rect_doc
        if rect is not None and not rect.isEmpty():
            return rect.center()

        return QPointF(0.0, 0.0)

    # ------------------------------------------------------------------
    def _build_transform(self) -> QTransform:
        pivot = self._current_pivot_point()
        return (
            QTransform()
            .translate(pivot.x(), pivot.y())
            .scale(self.scale_x, self.scale_y)
            .translate(-pivot.x(), -pivot.y())
        )

    # ------------------------------------------------------------------
    def _scale_display_text(self) -> str:
        if math.isclose(self.scale_x, self.scale_y, abs_tol=1e-3):
            return f"{self.scale_x:.2f}x"
        return f"W {self.scale_x:.2f}x  H {self.scale_y:.2f}x"

    # ------------------------------------------------------------------
    def _update_scaled_rect_from_current_scale(self):
        base_rect = self._drag_base_edge_rect_doc or self._base_edge_rect_doc
        if base_rect is None or base_rect.isEmpty():
            self._scaled_edge_rect_doc = None
            return

        if math.isclose(self.scale_x, 1.0, abs_tol=1e-4) and math.isclose(
            self.scale_y, 1.0, abs_tol=1e-4
        ):
            self._scaled_edge_rect_doc = QRectF(base_rect)
        else:
            pivot = self._current_pivot_point()
            self._scaled_edge_rect_doc = self._scale_edge_rect(
                base_rect, self.scale_x, self.scale_y, pivot
            )

    # ------------------------------------------------------------------
    def _scale_edge_rect(
        self, rect: QRectF, scale_x: float, scale_y: float, pivot: QPointF
    ) -> QRectF:
        transform = (
            QTransform()
            .translate(pivot.x(), pivot.y())
            .scale(scale_x, scale_y)
            .translate(-pivot.x(), -pivot.y())
        )
        top_left = transform.map(rect.topLeft())
        bottom_right = transform.map(rect.bottomRight())
        return QRectF(top_left, bottom_right).normalized()

    # ------------------------------------------------------------------
    def _doc_to_canvas_point(self, point: QPointF) -> QPointF:
        zoom = self.canvas.zoom if self.canvas.zoom != 0 else 1.0
        doc_width_scaled = self.canvas._document_size.width() * zoom
        doc_height_scaled = self.canvas._document_size.height() * zoom
        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        x_offset = (canvas_width - doc_width_scaled) / 2 + self.canvas.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.canvas.y_offset
        return QPointF(point.x() * zoom + x_offset, point.y() * zoom + y_offset)

    # ------------------------------------------------------------------
    def _canvas_to_doc_point(self, point: QPointF) -> QPointF:
        zoom = self.canvas.zoom if self.canvas.zoom != 0 else 1.0
        doc_width_scaled = self.canvas._document_size.width() * zoom
        doc_height_scaled = self.canvas._document_size.height() * zoom
        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        x_offset = (canvas_width - doc_width_scaled) / 2 + self.canvas.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.canvas.y_offset
        doc_x = (point.x() - x_offset) / zoom
        doc_y = (point.y() - y_offset) / zoom
        return QPointF(doc_x, doc_y)

    # ------------------------------------------------------------------
    def _edge_rect_doc_to_canvas(self, rect: QRectF) -> QRectF:
        top_left = self._doc_to_canvas_point(rect.topLeft())
        bottom_right = self._doc_to_canvas_point(rect.bottomRight())
        return QRectF(top_left, bottom_right).normalized()

    # ------------------------------------------------------------------
    def _handle_positions_for_edge_rect(self, rect: QRectF) -> dict[str, QPointF]:
        center = rect.center()
        return {
            "left": QPointF(rect.left(), center.y()),
            "right": QPointF(rect.right(), center.y()),
            "top": QPointF(center.x(), rect.top()),
            "bottom": QPointF(center.x(), rect.bottom()),
        }

    # ------------------------------------------------------------------
    def _overlay_geometry(self):
        rect_doc = self._current_edge_rect_doc()
        if rect_doc is None or rect_doc.isEmpty():
            return None, None, {}

        rect_canvas = self._edge_rect_doc_to_canvas(rect_doc)
        handle_rects = self._handle_rects_for_canvas_rect(rect_canvas)
        return rect_doc, rect_canvas, handle_rects

    # ------------------------------------------------------------------
    def _handle_rects_for_canvas_rect(self, rect: QRectF) -> dict[str, QRectF]:
        center = rect.center()
        positions = {
            "left": QPointF(rect.left(), center.y()),
            "right": QPointF(rect.right(), center.y()),
            "top": QPointF(center.x(), rect.top()),
            "bottom": QPointF(center.x(), rect.bottom()),
        }

        half = self._handle_size / 2.0
        handle_rects: dict[str, QRectF] = {}
        for name, point in positions.items():
            handle_rects[name] = QRectF(
                point.x() - half,
                point.y() - half,
                self._handle_size,
                self._handle_size,
            )
        return handle_rects

    # ------------------------------------------------------------------
    def _hit_test_handles(self, canvas_pos: QPointF) -> str | None:
        _, _, handle_rects = self._overlay_geometry()
        for name, rect in handle_rects.items():
            if rect.contains(canvas_pos):
                return name
        return None

    # ------------------------------------------------------------------
    def _cursor_for_handle(self, handle: str | None):
        if handle in ("left", "right"):
            return Qt.SizeHorCursor
        if handle in ("top", "bottom"):
            return Qt.SizeVerCursor
        return None

    # ------------------------------------------------------------------
    def _update_cursor(self):
        handle = self._active_handle or self._hover_handle
        cursor = self._cursor_for_handle(handle)
        if cursor is not None:
            self.canvas.setCursor(cursor)
            return

        self.canvas.setCursor(self.cursor)

