from __future__ import annotations
import math
from typing import Literal, Optional

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QTransform,
)

from portal.commands.layer_commands import (
    RotateLayerCommand,
    ScaleLayerCommand,
    apply_qimage_transform_nearest,
)
from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from portal.core.command import CompositeCommand, MoveCommand

from ._layer_tracker import ActiveLayerTracker
from .basetool import BaseTool
from ._transform_style import (
    TRANSFORM_GIZMO_ACTIVE_COLOR,
    TRANSFORM_GIZMO_BASE_COLOR,
    TRANSFORM_GIZMO_BORDER_COLOR,
    TRANSFORM_GIZMO_HANDLE_OUTLINE_COLOR,
    TRANSFORM_GIZMO_HOVER_COLOR,
    make_transform_cursor,
)


Operation = Literal["move", "rotate", "scale"]


class _MoveHelper(BaseTool):
    """Internal move helper composed by :class:`TransformTool`."""

    # ``name`` remains ``None`` so this helper is not auto-registered.
    name = None
    icon = "icons/toolmove.png"
    shortcut = "m"
    category = "draw"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.moving_selection = False
        self.original_selection_shape: QPainterPath | None = None
        self.before_image = None
        self.cursor = QCursor(Qt.OpenHandCursor)
        self._layer_tracker = ActiveLayerTracker(canvas)

        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)

    # ------------------------------------------------------------------
    def _reset_preview_buffers(self) -> None:
        self.before_image = None
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.moving_selection = False
        self.original_selection_shape = None
        if hasattr(self.canvas, "clear_preview_layer"):
            self.canvas.clear_preview_layer()

    # ------------------------------------------------------------------
    def _sync_active_layer(self) -> bool:
        if not self._layer_tracker.has_changed():
            return False

        self._layer_tracker.refresh()
        self._reset_preview_buffers()
        self.start_point = QPoint()
        self.canvas.update()
        return True

    # ------------------------------------------------------------------
    def _on_canvas_selection_changed(self, *_):
        if self.canvas.selection_shape is None:
            self.moving_selection = False
            self.original_selection_shape = None

    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if event.button() != Qt.LeftButton:
            return

        self._sync_active_layer()
        self.start_point = doc_pos

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            return
        self.before_image = active_layer.image.copy()

        self._allocate_preview_images(replace_active_layer=True)
        if hasattr(self.canvas, "set_preview_layer"):
            self.canvas.set_preview_layer(active_layer)

        if self.canvas.selection_shape:
            self.moving_selection = True
            self.original_selection_shape = QPainterPath(self.canvas.selection_shape)
            self.command_generated.emit(("cut_selection", "move_tool_start"))
        else:
            self.command_generated.emit(("cut_selection", "move_tool_start_no_selection"))

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self._sync_active_layer():
            return

        if self.canvas.original_image is None:
            return

        if not self._redraw_temp_from_preview_layer():
            if self.canvas.temp_image is None:
                return
            self.canvas.temp_image.fill(Qt.transparent)

        delta = doc_pos - self.start_point
        painter = QPainter(self.canvas.temp_image)
        painter.drawImage(delta, self.canvas.original_image)
        painter.end()

        if self.moving_selection:
            self.canvas.selection_shape = self.original_selection_shape.translated(
                delta.x(), delta.y()
            )

        self.canvas.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if event.button() != Qt.LeftButton:
            return

        if self._sync_active_layer():
            return

        if self.canvas.original_image is None or self.before_image is None:
            return

        delta = doc_pos - self.start_point

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            return

        move_command = MoveCommand(
            layer=active_layer,
            before_move_image=self.before_image,
            after_cut_image=active_layer.image.copy(),
            moved_image=self.canvas.original_image,
            delta=delta,
            original_selection_shape=self.original_selection_shape,
        )
        command_to_emit: MoveCommand | CompositeCommand = move_command
        if self.moving_selection and self.original_selection_shape is not None:
            final_selection = getattr(self.canvas, "selection_shape", None)
            previous_selection = clone_selection_path(self.original_selection_shape)
            current_selection = clone_selection_path(final_selection)
            if not selection_paths_equal(previous_selection, current_selection):
                selection_command = SelectionChangeCommand(
                    self.canvas,
                    previous_selection,
                    current_selection,
                )
                command_to_emit = CompositeCommand(
                    [move_command, selection_command], name="Move Selection"
                )

        self.command_generated.emit(command_to_emit)

        if self.moving_selection:
            self.moving_selection = False
            self.original_selection_shape = None

        self._reset_preview_buffers()
        self.canvas.update()

    # ------------------------------------------------------------------
    def deactivate(self):
        self._reset_preview_buffers()
        self.canvas.update()
        self._layer_tracker.reset()


class _RotateHelper(BaseTool):
    """Internal rotate helper used by :class:`TransformTool`."""

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
        self._rotation_press_radians = 0.0

        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)

    # ------------------------------------------------------------------
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
        self._rotation_press_radians = 0.0

    # ------------------------------------------------------------------
    def calculate_default_pivot_doc(self) -> QPoint:
        target_rect = self._calculate_transform_bounds()
        if target_rect is not None and not target_rect.isEmpty():
            return target_rect.center()

        return QPoint(0, 0)  # Fallback

    # ------------------------------------------------------------------
    def _calculate_transform_bounds(self) -> QRect | None:
        selection_shape = getattr(self.canvas, "selection_shape", None)
        if selection_shape:
            rect = selection_shape.boundingRect().toAlignedRect()
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                return rect

        layer_manager = self._get_active_layer_manager()
        if layer_manager and layer_manager.active_layer is not None:
            layer = layer_manager.active_layer
            image = layer.image
            if image is not None and not image.isNull():
                bounds = layer.non_transparent_bounds
                if bounds is None:
                    bounds = image.rect()
                if bounds.isValid() and bounds.width() > 0 and bounds.height() > 0:
                    return bounds

        document = getattr(self.canvas, "document", None)
        if document is not None:
            width = getattr(document, "width", None)
            height = getattr(document, "height", None)
            if width is not None and height is not None:
                width_int = max(1, int(width))
                height_int = max(1, int(height))
                return QRect(0, 0, width_int, height_int)

        return None

    # ------------------------------------------------------------------
    def get_rotation_center_doc(self) -> QPoint:
        return self.pivot_doc

    # ------------------------------------------------------------------
    def get_center(self) -> QPointF:
        return QPointF(self.canvas.get_canvas_coords(self.pivot_doc))

    # ------------------------------------------------------------------
    def get_handle_pos(self) -> QPointF:
        if self._rotation_handle_center is not None:
            return QPointF(self._rotation_handle_center)

        center = self.get_center()
        return QPointF(center.x() + 100.0, center.y())

    # ------------------------------------------------------------------
    def _sync_active_layer(
        self, *, force: bool = False, suppress_update: bool = False
    ) -> bool:
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
        self._rotation_press_radians = 0.0

        if not suppress_update:
            self.canvas.update()

        return True

    # ------------------------------------------------------------------
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
        self._rotation_press_radians = 0.0

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._sync_active_layer()
        self._update_hover_state_from_point(
            QPointF(event.pos()), request_update=False
        )

        if self.is_hovering_handle:
            self.drag_mode = "rotate"
            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            center = self.get_center()
            press_pos = QPointF(event.pos())
            dx = press_pos.x() - center.x()
            dy = press_pos.y() - center.y()
            self._rotation_press_radians = math.atan2(dy, dx)
            self.angle = 0.0
            self.angle_changed.emit(0.0)

            active_layer = layer_manager.active_layer
            if active_layer:
                self.original_image = active_layer.image.copy()
                self.canvas.temp_image_replaces_active_layer = True
                self.original_selection_shape = None
                self.selection_source_image = None
                if self.canvas.selection_shape:
                    self.original_selection_shape = QPainterPath(
                        self.canvas.selection_shape
                    )
                    self.selection_source_image = QImage(
                        self.original_image.size(),
                        self.original_image.format(),
                    )
                    self.selection_source_image.fill(Qt.transparent)

                    selection_painter = QPainter(self.selection_source_image)
                    selection_painter.setRenderHint(QPainter.Antialiasing, False)
                    selection_painter.setRenderHint(
                        QPainter.SmoothPixmapTransform, False
                    )
                    selection_painter.setClipPath(self.original_selection_shape)
                    selection_painter.drawImage(0, 0, self.original_image)
                    selection_painter.end()
        elif self.is_hovering_center:
            self.drag_mode = "pivot"

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        self._sync_active_layer()
        self._update_hover_state_from_point(QPointF(event.pos()))

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        if self._sync_active_layer():
            return

        if not self.drag_mode:
            return

        if self.drag_mode == "rotate":
            canvas_pos = QPointF(event.pos())
            center = self.get_center()

            dx = canvas_pos.x() - center.x()
            dy = canvas_pos.y() - center.y()

            angle_radians = math.atan2(dy, dx)
            relative_radians = angle_radians - self._rotation_press_radians
            relative_degrees = math.degrees(relative_radians)

            if event.modifiers() & Qt.ShiftModifier:
                snap_increment = 22.5
                relative_degrees = (
                    round(relative_degrees / snap_increment) * snap_increment
                )
                relative_radians = math.radians(relative_degrees)

            self.angle = relative_radians
            self.angle_changed.emit(relative_degrees)

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
        elif self.drag_mode == "pivot":
            self.pivot_doc = doc_pos
            self._manual_pivot = True
            self.canvas.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        if self._sync_active_layer():
            return

        if self.drag_mode == "rotate":
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
            self._rotation_press_radians = 0.0

        self.drag_mode = None

    # ------------------------------------------------------------------
    def deactivate(self):
        if self.drag_mode == "rotate":
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
        self._rotation_press_radians = 0.0

    # ------------------------------------------------------------------
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
            self._rotation_press_radians = 0.0
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
        self._rotation_press_radians = 0.0
        self.canvas.update()

    # ------------------------------------------------------------------
    def reset_pivot_to_default(self) -> None:
        """Recenter the pivot and mark it as automatic."""

        self._manual_pivot = False
        self._rotation_press_radians = 0.0
        new_pivot = self.calculate_default_pivot_doc()
        if new_pivot != self.pivot_doc:
            self.pivot_doc = new_pivot
            self.canvas.update()


class _ScaleHelper(BaseTool):
    """Interactive scaling helper composed by :class:`TransformTool`."""

    name = None
    icon = "icons/toolscale.png"
    category = "draw"
    scale_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = make_transform_cursor()
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
        self._did_apply_scale = False

        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)

    # ------------------------------------------------------------------
    def _on_canvas_selection_changed(self, *_):
        if self.drag_mode == "scale":
            return

        self._drag_base_edge_rect_doc = None
        self._current_pivot_doc = None
        self._hover_handle = None
        self._did_apply_scale = False
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
        self._did_apply_scale = False
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
        self._did_apply_scale = False
        self._layer_tracker.reset()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if event.button() != Qt.LeftButton:
            return

        self._ensure_base_rect()
        self._did_apply_scale = False

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
        applied_scale = not (
            math.isclose(self.scale_x, 1.0, abs_tol=1e-3)
            and math.isclose(self.scale_y, 1.0, abs_tol=1e-3)
        )

        if active_layer is not None and self.original_image is not None:
            if not applied_scale:
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

        self._did_apply_scale = applied_scale

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
    def consume_did_apply_scale(self) -> bool:
        """Return whether the last interaction applied a scale and reset the flag."""

        did_apply = self._did_apply_scale
        self._did_apply_scale = False
        return did_apply

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
        border_color = QColor(TRANSFORM_GIZMO_BORDER_COLOR)
        outline_color = QColor(TRANSFORM_GIZMO_HANDLE_OUTLINE_COLOR)

        if overlay_rect is not None:
            border_pen = QPen(border_color)
            border_pen.setWidth(1)
            border_pen.setCosmetic(True)
            painter.setPen(border_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(overlay_rect)

            handle_pen = QPen(outline_color)
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

        layer_manager = self._get_active_layer_manager()
        if layer_manager and layer_manager.active_layer is not None:
            layer = layer_manager.active_layer
            bounds = getattr(layer, "non_transparent_bounds", None)
            if bounds is not None and bounds.isValid():
                return QRectF(bounds)
            if layer.image is not None and not layer.image.isNull():
                rect = layer.image.rect()
                if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                    return QRectF(rect)

        document = getattr(self.canvas, "document", None)
        if document is not None:
            width = getattr(document, "width", None)
            height = getattr(document, "height", None)
            if width is not None and height is not None:
                return QRectF(0, 0, float(width), float(height))

        return None

    # ------------------------------------------------------------------
    def _ensure_base_rect(self) -> None:
        if not self._bounds_dirty:
            return

        rect = self._current_edge_rect_doc()
        if rect is None or rect.isEmpty():
            self._base_edge_rect_doc = None
        else:
            self._base_edge_rect_doc = QRectF(rect)
        self._bounds_dirty = False

    # ------------------------------------------------------------------
    def _refresh_base_rect(self) -> None:
        self._bounds_dirty = True
        self._scaled_edge_rect_doc = None
        self._ensure_base_rect()

    # ------------------------------------------------------------------
    def _current_pivot_point(self) -> QPointF:
        if self._current_pivot_doc is not None:
            return QPointF(self._current_pivot_doc)

        rect = self._drag_base_edge_rect_doc
        if rect is not None:
            return rect.center()

        rect = self._current_edge_rect_doc()
        if rect is not None:
            return rect.center()

        return QPointF(0.0, 0.0)

    # ------------------------------------------------------------------
    def _update_scaled_rect_from_current_scale(self) -> None:
        base_rect = self._drag_base_edge_rect_doc
        if base_rect is None:
            return

        pivot = self._current_pivot_point()
        self._scaled_edge_rect_doc = self._scale_edge_rect(
            base_rect, self.scale_x, self.scale_y, pivot
        )

    # ------------------------------------------------------------------
    def _build_transform(self) -> QTransform:
        pivot = self._current_pivot_point()
        transform = QTransform()
        transform.translate(pivot.x(), pivot.y())
        transform.scale(self.scale_x, self.scale_y)
        transform.translate(-pivot.x(), -pivot.y())
        return transform

    # ------------------------------------------------------------------
    def _scale_display_text(self) -> str:
        return f"{self.scale_factor * 100:.1f}%"

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
    def get_overlay_geometry(self):
        """Return the canvas overlay rect and handle rectangles."""

        rect_doc, rect_canvas, handle_rects = self._overlay_geometry()
        if rect_canvas is None and not handle_rects:
            return None

        rect_canvas_copy = QRectF(rect_canvas) if rect_canvas is not None else None
        handle_rects_copy = {
            name: QRectF(rect) for name, rect in handle_rects.items()
        }
        return rect_canvas_copy, handle_rects_copy

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


class TransformTool(BaseTool):
    """Combined move/rotate/scale tool that exposes all gizmos together."""

    name = "Transform"
    icon = "icons/toolmove.png"
    shortcut = "m"
    category = "draw"

    angle_changed = Signal(float)
    scale_changed = Signal(float)

    def __init__(
        self,
        canvas,
        *,
        move_tool: Optional[BaseTool] = None,
        rotate_tool: Optional[BaseTool] = None,
        scale_tool: Optional[BaseTool] = None,
    ):
        super().__init__(canvas)
        self.cursor = make_transform_cursor()

        self._move_tool = move_tool or _MoveHelper(canvas)
        self._rotate_tool = rotate_tool or _RotateHelper(canvas)
        self._scale_tool = scale_tool or _ScaleHelper(canvas)

        self._connect_signal(self._move_tool, "command_generated", self.command_generated.emit)
        self._connect_signal(self._rotate_tool, "command_generated", self.command_generated.emit)
        self._connect_signal(self._scale_tool, "command_generated", self.command_generated.emit)

        self._connect_signal(self._rotate_tool, "angle_changed", self.angle_changed.emit)
        self._connect_signal(self._scale_tool, "scale_changed", self.scale_changed.emit)

        self._active_operation: Operation | None = None
        self._dragging_transform = False
        self._last_move_delta = QPoint()
        self._update_rotation_overlay_geometry()

    # ------------------------------------------------------------------
    @staticmethod
    def _connect_signal(tool, signal_name: str, slot):
        signal = getattr(tool, signal_name, None)
        connect = getattr(signal, "connect", None)
        if callable(connect):
            connect(slot)

    # ------------------------------------------------------------------
    @staticmethod
    def _invoke(tool, method_name: str, *args, **kwargs):
        method = getattr(tool, method_name, None)
        if callable(method):
            return method(*args, **kwargs)
        return None

    # ------------------------------------------------------------------
    def activate(self):
        self._active_operation = None
        self._set_dragging_transform(False)
        # Reset cached state for the composed tools so their gizmos reflect
        # the newly selected layer/selection.
        self._invoke(self._move_tool, "deactivate")
        self._invoke(self._rotate_tool, "activate")
        self._invoke(self._scale_tool, "activate")
        self.angle_changed.emit(0.0)
        self._last_move_delta = QPoint()
        self._update_rotation_overlay_geometry()

    # ------------------------------------------------------------------
    def deactivate(self):
        self._active_operation = None
        self._set_dragging_transform(False)
        self._invoke(self._move_tool, "deactivate")
        self._invoke(self._rotate_tool, "deactivate")
        self._invoke(self._scale_tool, "deactivate")
        self._last_move_delta = QPoint()
        self._update_rotation_overlay_geometry()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        self._update_rotation_overlay_geometry()
        if event.button() != Qt.LeftButton:
            return

        self._active_operation = None
        self._set_dragging_transform(False)
        self._last_move_delta = QPoint()

        self._invoke(self._rotate_tool, "mousePressEvent", event, doc_pos)
        rotate_mode = getattr(self._rotate_tool, "drag_mode", None)
        if rotate_mode in {"rotate", "pivot"}:
            self._active_operation = "rotate"
            return

        self._invoke(self._scale_tool, "mousePressEvent", event, doc_pos)
        if getattr(self._scale_tool, "drag_mode", None) == "scale":
            self._active_operation = "scale"
            return

        self._invoke(self._move_tool, "mousePressEvent", event, doc_pos)
        self._active_operation = "move"

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        self._update_rotation_overlay_geometry()
        if self._active_operation == "rotate":
            if getattr(self._rotate_tool, "drag_mode", None) == "rotate":
                self._set_dragging_transform(True)
            else:
                self._set_dragging_transform(False)
            self._invoke(self._rotate_tool, "mouseMoveEvent", event, doc_pos)
        elif self._active_operation == "scale":
            if getattr(self._scale_tool, "drag_mode", None) == "scale":
                self._set_dragging_transform(True)
            else:
                self._set_dragging_transform(False)
            self._invoke(self._scale_tool, "mouseMoveEvent", event, doc_pos)
        else:
            dragging_move = bool(
                self._active_operation == "move"
                and event.buttons() & Qt.LeftButton
            )
            if dragging_move:
                self._set_dragging_transform(True)
            else:
                self._set_dragging_transform(False)
            self._invoke(self._move_tool, "mouseMoveEvent", event, doc_pos)
            if dragging_move:
                self._update_move_gizmos(doc_pos)

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        self._update_rotation_overlay_geometry()
        if event.button() != Qt.LeftButton:
            return

        operation = self._active_operation
        self._set_dragging_transform(False)

        if operation == "rotate":
            previous_mode = getattr(self._rotate_tool, "drag_mode", None)
            self._invoke(self._rotate_tool, "mouseReleaseEvent", event, doc_pos)
            self._handle_rotation_finished(previous_mode == "rotate")
        elif operation == "scale":
            self._invoke(self._scale_tool, "mouseReleaseEvent", event, doc_pos)
            self._handle_scale_finished()
        elif operation == "move":
            start_point = QPoint(getattr(self._move_tool, "start_point", QPoint()))
            self._invoke(self._move_tool, "mouseReleaseEvent", event, doc_pos)
            delta = doc_pos - start_point
            self._handle_move_finished(delta)
        else:
            self._invoke(self._move_tool, "mouseReleaseEvent", event, doc_pos)
            self._refresh_scale_handles()
            self._refresh_pivot()

        self._active_operation = None
        self._last_move_delta = QPoint()

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        self._update_rotation_overlay_geometry()
        self._invoke(self._rotate_tool, "mouseHoverEvent", event, doc_pos)
        self._invoke(self._scale_tool, "mouseHoverEvent", event, doc_pos)

    # ------------------------------------------------------------------
    def draw_overlay(self, painter):
        if self._dragging_transform:
            return
        self._invoke(self._scale_tool, "draw_overlay", painter)
        self._update_rotation_overlay_geometry()
        self._invoke(self._rotate_tool, "draw_overlay", painter)

    # ------------------------------------------------------------------
    def _set_dragging_transform(self, active: bool) -> None:
        if self._dragging_transform == active:
            return
        self._dragging_transform = active
        setter = getattr(self.canvas, "set_selection_overlay_hidden", None)
        if callable(setter):
            setter(active)

    # ------------------------------------------------------------------
    def _handle_rotation_finished(self, did_rotate: bool) -> None:
        if did_rotate:
            self._refresh_scale_handles()
        self._refresh_pivot()

    # ------------------------------------------------------------------
    def _handle_scale_finished(self) -> None:
        did_scale = bool(self._invoke(self._scale_tool, "consume_did_apply_scale"))
        self._refresh_scale_handles()
        if did_scale:
            self._invoke(self._rotate_tool, "reset_pivot_to_default")
            self._update_rotation_overlay_geometry()
        else:
            self._refresh_pivot()

    # ------------------------------------------------------------------
    def _handle_move_finished(self, delta: QPoint) -> None:
        pivot_is_manual = getattr(self._rotate_tool, "pivot_is_manual", None)
        pivot_manual = callable(pivot_is_manual) and pivot_is_manual()
        remaining_delta = delta - self._last_move_delta
        if pivot_manual:
            if not remaining_delta.isNull():
                self._invoke(self._rotate_tool, "offset_pivot", remaining_delta)
        else:
            if not remaining_delta.isNull():
                self._invoke(self._rotate_tool, "offset_pivot", remaining_delta)
            selection_shape = getattr(self.canvas, "selection_shape", None)
            if selection_shape is not None:
                self._refresh_pivot()
        self._refresh_scale_handles()

    # ------------------------------------------------------------------
    def _refresh_scale_handles(self) -> None:
        self._invoke(self._scale_tool, "refresh_handles_from_document")
        self._update_rotation_overlay_geometry()

    # ------------------------------------------------------------------
    def _refresh_pivot(self) -> None:
        self._invoke(self._rotate_tool, "refresh_pivot_from_document")
        self._update_rotation_overlay_geometry()

    # ------------------------------------------------------------------
    def _update_rotation_overlay_geometry(self) -> None:
        overlay = self._invoke(self._scale_tool, "get_overlay_geometry")
        if overlay is None:
            rect_canvas = None
            handle_rects: dict[str, object] = {}
        else:
            rect_canvas, handle_rects = overlay
        self._invoke(
            self._rotate_tool,
            "set_overlay_geometry",
            rect_canvas,
            handle_rects or {},
        )

    # ------------------------------------------------------------------
    def _update_move_gizmos(self, doc_pos: QPoint) -> None:
        start_point = getattr(self._move_tool, "start_point", None)
        if start_point is None:
            return
        if not isinstance(start_point, QPoint):
            try:
                start_point = QPoint(start_point)
            except TypeError:
                return

        delta = doc_pos - start_point
        if delta == self._last_move_delta:
            return

        step = delta - self._last_move_delta
        if not step.isNull():
            self._invoke(self._rotate_tool, "offset_pivot", step)

        self._last_move_delta = QPoint(delta)

        selection_shape = getattr(self.canvas, "selection_shape", None)
        if selection_shape is not None:
            self._refresh_pivot()

