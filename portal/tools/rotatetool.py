import math
from PySide6.QtGui import (
    QPen,
    QColor,
    QTransform,
    QImage,
    QPainter,
    QPainterPath,
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal
from portal.tools._layer_tracker import ActiveLayerTracker
from portal.tools.basetool import BaseTool
from portal.commands.layer_commands import RotateLayerCommand
from ._transform_style import (
    TRANSFORM_GIZMO_ACTIVE_COLOR,
    TRANSFORM_GIZMO_BASE_COLOR,
    TRANSFORM_GIZMO_HANDLE_OUTLINE_COLOR,
    TRANSFORM_GIZMO_HOVER_COLOR,
    make_transform_cursor,
)


class RotateTool(BaseTool):
    """Internal rotate helper used by :class:`TransformTool`."""

    # ``name`` is ``None`` so registry discovery ignores this helper. The
    # combined transform tool exposes rotation alongside move and scale.
    name = None
    icon = "icons/toolrotate.png"
    category = "draw"
    angle_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = make_transform_cursor()
        self.angle = 0.0
        self.is_hovering_handle = False
        self.is_hovering_center = False
        self.drag_mode = None  # None, 'rotate', or 'pivot'
        self.original_image = None
        self.pivot_doc = QPoint(0, 0)
        self.original_selection_shape: QPainterPath | None = None
        self.selection_source_image: QImage | None = None
        self._manual_pivot = False
        self._layer_tracker = ActiveLayerTracker(canvas)
        self._handle_size = 14.0
        self._handle_gap = 4.0
        self._pivot_radius = 10.0
        self._rotation_handle_center: QPointF | None = None
        self._rotation_handle_radius = self._handle_size / 2.0

        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)

    def activate(self):
        self.drag_mode = None
        self.is_hovering_handle = False
        self.is_hovering_center = False
        self.original_image = None
        self.selection_source_image = None
        self.original_selection_shape = None
        self.angle = 0.0
        self._layer_tracker.reset()
        self._sync_active_layer(force=True)
        self._manual_pivot = False
        self._rotation_handle_center = None
        self._rotation_handle_radius = self._handle_size / 2.0

    def calculate_default_pivot_doc(self) -> QPoint:
        if self.canvas.selection_shape:
            return self.canvas.selection_shape.boundingRect().center().toPoint()

        layer_manager = self._get_active_layer_manager()
        if layer_manager and layer_manager.active_layer:
            return layer_manager.active_layer.image.rect().center()

        return QPoint(0, 0)  # Fallback

    def get_rotation_center_doc(self) -> QPoint:
        return self.pivot_doc

    def get_center(self) -> QPointF:
        return QPointF(self.canvas.get_canvas_coords(self.pivot_doc))

    def get_handle_pos(self) -> QPointF:
        if self._rotation_handle_center is not None:
            return QPointF(self._rotation_handle_center)

        center = self.get_center()
        return QPointF(center.x() + 100.0, center.y())

    def _sync_active_layer(self, *, force: bool = False, suppress_update: bool = False) -> bool:
        """Ensure cached geometry reflects the currently selected layer."""

        if not force and not self._layer_tracker.has_changed():
            return False

        self._layer_tracker.refresh()

        # Drop any in-progress preview so we don't leak the previous layer's
        # imagery onto the new target.
        self.canvas.temp_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.drag_mode = None

        self.original_image = None
        self.selection_source_image = None
        self.original_selection_shape = None

        new_pivot = self.calculate_default_pivot_doc()
        pivot_changed = new_pivot != self.pivot_doc
        self.pivot_doc = new_pivot
        self._manual_pivot = False

        angle_changed = not math.isclose(self.angle, 0.0, abs_tol=1e-6)
        self.angle = 0.0
        if angle_changed:
            self.angle_changed.emit(0.0)

        self.is_hovering_handle = False
        self.is_hovering_center = False
        self._rotation_handle_center = None
        self._rotation_handle_radius = self._handle_size / 2.0

        if not suppress_update:
            self.canvas.update()

        return True

    def _on_canvas_selection_changed(self, *_):
        if self.drag_mode in ("rotate", "pivot"):
            return

        self.original_image = None
        self.selection_source_image = None
        self.original_selection_shape = None

        new_pivot = self.calculate_default_pivot_doc()
        if new_pivot != self.pivot_doc:
            self.pivot_doc = new_pivot
            self.canvas.update()
        self._manual_pivot = False
        self._rotation_handle_center = None
        self._rotation_handle_radius = self._handle_size / 2.0

    def _update_hover_state_from_point(
        self, canvas_pos: QPointF, *, request_update: bool = True
    ) -> None:
        center_pos = self.get_center()
        handle_center = self._rotation_handle_center
        handle_radius = self._rotation_handle_radius

        distance_center = math.hypot(
            canvas_pos.x() - center_pos.x(), canvas_pos.y() - center_pos.y()
        )

        if handle_center is not None and handle_radius > 0.0:
            dx = canvas_pos.x() - handle_center.x()
            dy = canvas_pos.y() - handle_center.y()
            new_hover_handle = (dx * dx + dy * dy) <= handle_radius * handle_radius
        else:
            new_hover_handle = False

        new_hover_center = distance_center <= self._pivot_radius

        if (
            self.is_hovering_handle != new_hover_handle
            or self.is_hovering_center != new_hover_center
        ):
            self.is_hovering_handle = new_hover_handle
            self.is_hovering_center = new_hover_center
            if request_update:
                self.canvas.repaint()

    def set_overlay_geometry(
        self, rect_canvas: QRectF | None, handle_rects: dict[str, QRectF]
    ) -> None:
        if rect_canvas is None and not handle_rects:
            self._rotation_handle_center = None
            self._rotation_handle_radius = self._handle_size / 2.0
            return

        right_handle = handle_rects.get("right")
        if right_handle is None:
            self._rotation_handle_center = None
            self._rotation_handle_radius = self._handle_size / 2.0
            return

        gap = self._handle_gap
        handle_size = self._handle_size
        radius = handle_size / 2.0
        right_rect = QRectF(right_handle)
        center_y = right_rect.center().y()
        center_x = right_rect.right() + gap + radius

        self._rotation_handle_center = QPointF(center_x, center_y)
        self._rotation_handle_radius = radius

    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._sync_active_layer()
        self._update_hover_state_from_point(
            QPointF(event.pos()), request_update=False
        )

        if self.is_hovering_handle:
            self.drag_mode = 'rotate'
            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            active_layer = layer_manager.active_layer
            if active_layer:
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
        elif self.is_hovering_center:
            self.drag_mode = 'pivot'

    def mouseHoverEvent(self, event, doc_pos):
        self._sync_active_layer()
        self._update_hover_state_from_point(QPointF(event.pos()))

    def mouseMoveEvent(self, event, doc_pos):
        if self._sync_active_layer():
            return

        if not self.drag_mode:
            return

        if self.drag_mode == 'rotate':
            canvas_pos = QPointF(event.pos())
            center = self.get_center()

            dx = canvas_pos.x() - center.x()
            dy = canvas_pos.y() - center.y()

            angle_radians = math.atan2(dy, dx)
            angle_degrees = math.degrees(angle_radians)

            if event.modifiers() & Qt.ShiftModifier:
                snap_increment = 22.5
                angle_degrees = round(angle_degrees / snap_increment) * snap_increment
                angle_radians = math.radians(angle_degrees)

            self.angle = angle_radians
            self.angle_changed.emit(angle_degrees)

            if self.original_image:
                image_to_modify = self.original_image.copy()
                painter = QPainter(image_to_modify)
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

                center_doc = self.get_rotation_center_doc()
                angle_degrees = math.degrees(self.angle)
                transform = (
                    QTransform()
                    .translate(center_doc.x(), center_doc.y())
                    .rotate(angle_degrees)
                    .translate(-center_doc.x(), -center_doc.y())
                )

                if self.original_selection_shape:
                    source_image = self.selection_source_image or self.original_image
                    painter.setClipPath(self.original_selection_shape)
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.fillPath(self.original_selection_shape, Qt.transparent)
                    painter.end()

                    inverse_transform, invertible = transform.inverted()
                    if not invertible:
                        self.canvas.temp_image = image_to_modify
                        self.canvas.update()
                        return

                    width = source_image.width()
                    height = source_image.height()

                    for y in range(image_to_modify.height()):
                        for x in range(image_to_modify.width()):
                            source_point = inverse_transform.map(QPointF(x, y))
                            sx_float = source_point.x()
                            sy_float = source_point.y()
                            if 0 <= sx_float < width and 0 <= sy_float < height:
                                sx = int(sx_float)
                                sy = int(sy_float)
                                color = source_image.pixelColor(sx, sy)
                                if color.alpha() > 0:
                                    image_to_modify.setPixelColor(x, y, color)
                    painter = None
                else:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.fillRect(self.original_image.rect(), Qt.transparent)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.setTransform(transform)
                    painter.drawImage(0, 0, self.original_image)

                if painter is not None:
                    painter.end()
                self.canvas.temp_image = image_to_modify

                if self.original_selection_shape:
                    rotated_shape = transform.map(self.original_selection_shape)
                    self.canvas._update_selection_and_emit_size(rotated_shape)

            self.canvas.update()
        elif self.drag_mode == 'pivot':
            self.pivot_doc = doc_pos
            self._manual_pivot = True
            self.canvas.update()

    def mouseReleaseEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        if self._sync_active_layer():
            return

        if self.drag_mode == 'rotate':
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False

            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            active_layer = layer_manager.active_layer
            if active_layer:
                center_doc = self.get_rotation_center_doc()
                angle_degrees = math.degrees(self.angle)
                selection_shape = (
                    QPainterPath(self.original_selection_shape)
                    if self.original_selection_shape is not None
                    else None
                )

                rotated_shape = None
                if self.original_selection_shape:
                    transform = (
                        QTransform()
                        .translate(center_doc.x(), center_doc.y())
                        .rotate(angle_degrees)
                        .translate(-center_doc.x(), -center_doc.y())
                    )
                    rotated_shape = transform.map(self.original_selection_shape)
                    self.canvas._update_selection_and_emit_size(rotated_shape)

                command = RotateLayerCommand(
                    active_layer,
                    angle_degrees,
                    center_doc,
                    selection_shape,
                    canvas=self.canvas,
                    rotated_selection_shape=rotated_shape,
                )
                self.command_generated.emit(command)

            self.original_image = None
            self.selection_source_image = None
            self.original_selection_shape = None
            self.angle = 0.0
            self.angle_changed.emit(math.degrees(self.angle))

        self.drag_mode = None

    def deactivate(self):
        if self.drag_mode == 'rotate':
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False
            layer_manager = self._get_active_layer_manager()
            if self.original_image and layer_manager and layer_manager.active_layer:
                layer_manager.active_layer.image = self.original_image
                layer_manager.active_layer.on_image_change.emit()
            if self.original_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(
                    QPainterPath(self.original_selection_shape)
                )
            self.original_image = None
            self.selection_source_image = None
            self.original_selection_shape = None
            self.angle = 0.0
            self.angle_changed.emit(math.degrees(self.angle))
        self.drag_mode = None
        self.is_hovering_handle = False
        self.is_hovering_center = False
        self._layer_tracker.reset()
        self._manual_pivot = False
        self._rotation_handle_center = None
        self._rotation_handle_radius = self._handle_size / 2.0

    def draw_overlay(self, painter):
        self._sync_active_layer(suppress_update=True)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        center = self.get_center()

        base_color = QColor(TRANSFORM_GIZMO_BASE_COLOR)
        hover_color = QColor(TRANSFORM_GIZMO_HOVER_COLOR)
        active_color = QColor(TRANSFORM_GIZMO_ACTIVE_COLOR)
        outline_color = QColor(TRANSFORM_GIZMO_HANDLE_OUTLINE_COLOR)

        if self.drag_mode == "rotate":
            color_handle = active_color
        elif self.is_hovering_handle:
            color_handle = hover_color
        else:
            color_handle = base_color

        if self.drag_mode == "pivot":
            color_center = active_color
        elif self.is_hovering_center:
            color_center = hover_color
        else:
            color_center = base_color

        outline_pen = QPen(outline_color)
        outline_pen.setWidth(1)
        outline_pen.setCosmetic(True)

        # Circle (pivot)
        painter.setPen(outline_pen)
        painter.setBrush(color_center)
        painter.drawEllipse(center, self._pivot_radius, self._pivot_radius)

        # Handle
        if self._rotation_handle_center is not None:
            painter.setPen(outline_pen)
            painter.setBrush(color_handle)
            painter.drawEllipse(
                self._rotation_handle_center,
                self._rotation_handle_radius,
                self._rotation_handle_radius,
            )

        painter.restore()

    # ------------------------------------------------------------------
    def refresh_pivot_from_document(self) -> None:
        """Recompute the default pivot when no manual pivot is set."""

        if self._manual_pivot:
            return

        new_pivot = self.calculate_default_pivot_doc()
        if new_pivot != self.pivot_doc:
            self.pivot_doc = new_pivot
            self.canvas.update()

    # ------------------------------------------------------------------
    def pivot_is_manual(self) -> bool:
        return self._manual_pivot

    # ------------------------------------------------------------------
    def offset_pivot(self, delta: QPoint) -> None:
        if delta.isNull():
            return

        self.pivot_doc = QPoint(
            self.pivot_doc.x() + delta.x(),
            self.pivot_doc.y() + delta.y(),
        )
        self.canvas.update()
