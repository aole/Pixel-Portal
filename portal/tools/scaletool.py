import math

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
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
from portal.tools.basetool import BaseTool


class ScaleTool(BaseTool):
    """Interactive scaling tool that honours pixel-art constraints."""

    name = "Scale"
    icon = "icons/toolscale.png"
    category = "draw"
    scale_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)
        self.scale_factor = 1.0
        self.is_hovering_handle = False
        self.is_hovering_center = False
        self.drag_mode: str | None = None
        self.original_image: QImage | None = None
        self.pivot_doc = QPoint(0, 0)
        self.original_selection_shape: QPainterPath | None = None
        self.selection_source_image: QImage | None = None
        self.base_handle_distance = 80.0

    # ------------------------------------------------------------------
    def activate(self):
        self.scale_factor = 1.0
        self.scale_changed.emit(self.scale_factor)
        self.pivot_doc = self._calculate_default_pivot_doc()

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
        self.scale_changed.emit(self.scale_factor)
        self.drag_mode = None

    # ------------------------------------------------------------------
    def _calculate_default_pivot_doc(self) -> QPoint:
        if self.canvas.selection_shape:
            return self.canvas.selection_shape.boundingRect().center().toPoint()

        layer_manager = self._get_active_layer_manager()
        if layer_manager and layer_manager.active_layer:
            return layer_manager.active_layer.image.rect().center()

        return QPoint(0, 0)

    # ------------------------------------------------------------------
    def _get_scale_center_doc(self) -> QPoint:
        return self.pivot_doc

    # ------------------------------------------------------------------
    def _get_center(self) -> QPointF:
        return QPointF(self.canvas.get_canvas_coords(self.pivot_doc))

    # ------------------------------------------------------------------
    def _get_handle_pos(self) -> QPointF:
        center = self._get_center()
        distance = max(24.0, self.base_handle_distance * self.scale_factor)
        return QPointF(center.x() + distance, center.y())

    # ------------------------------------------------------------------
    def mousePressEvent(self, event, doc_pos):
        if self.is_hovering_handle:
            self.drag_mode = "scale"
            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            active_layer = layer_manager.active_layer
            if active_layer is None:
                return

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
            self.drag_mode = "pivot"

    # ------------------------------------------------------------------
    def mouseHoverEvent(self, event, doc_pos):
        canvas_pos = QPointF(event.pos())
        handle_pos = self._get_handle_pos()
        center_pos = self._get_center()

        distance_handle = math.hypot(
            canvas_pos.x() - handle_pos.x(),
            canvas_pos.y() - handle_pos.y(),
        )
        distance_center = math.hypot(
            canvas_pos.x() - center_pos.x(),
            canvas_pos.y() - center_pos.y(),
        )

        new_hover_handle = distance_handle <= 6
        new_hover_center = distance_center <= 10

        if (
            self.is_hovering_handle != new_hover_handle
            or self.is_hovering_center != new_hover_center
        ):
            self.is_hovering_handle = new_hover_handle
            self.is_hovering_center = new_hover_center
            self.canvas.repaint()

    # ------------------------------------------------------------------
    def mouseMoveEvent(self, event, doc_pos):
        if self.drag_mode == "scale":
            center = self._get_center()
            canvas_pos = QPointF(event.pos())

            distance = math.hypot(
                canvas_pos.x() - center.x(),
                canvas_pos.y() - center.y(),
            )
            distance = max(8.0, distance)
            scale = distance / self.base_handle_distance
            scale = max(0.125, scale)

            if event.modifiers() & Qt.ShiftModifier:
                snap_increment = 0.125
                scale = round(scale / snap_increment) * snap_increment

            if abs(scale - self.scale_factor) >= 1e-3:
                self.scale_factor = scale
                self.scale_changed.emit(self.scale_factor)
                self._update_preview_image()

            self.canvas.update()

        elif self.drag_mode == "pivot":
            self.pivot_doc = doc_pos
            self.canvas.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event, doc_pos):
        if self.drag_mode != "scale":
            self.drag_mode = None
            return

        self.canvas.temp_image = None
        self.canvas.temp_image_replaces_active_layer = False

        layer_manager = self._get_active_layer_manager()
        active_layer = None if layer_manager is None else layer_manager.active_layer

        if active_layer is not None and self.original_image is not None:
            if math.isclose(self.scale_factor, 1.0, abs_tol=1e-3):
                if self.original_selection_shape is not None:
                    self.canvas._update_selection_and_emit_size(
                        QPainterPath(self.original_selection_shape)
                    )
            else:
                center_doc = self._get_scale_center_doc()
                selection_shape = (
                    QPainterPath(self.original_selection_shape)
                    if self.original_selection_shape is not None
                    else None
                )
                scaled_shape = None
                if self.original_selection_shape is not None:
                    transform = (
                        QTransform()
                        .translate(center_doc.x(), center_doc.y())
                        .scale(self.scale_factor, self.scale_factor)
                        .translate(-center_doc.x(), -center_doc.y())
                    )
                    scaled_shape = transform.map(self.original_selection_shape)
                    self.canvas._update_selection_and_emit_size(scaled_shape)

                command = ScaleLayerCommand(
                    active_layer,
                    self.scale_factor,
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
        self.scale_changed.emit(self.scale_factor)
        self.drag_mode = None
        self.canvas.update()

    # ------------------------------------------------------------------
    def _update_preview_image(self):
        if self.original_image is None:
            return

        center_doc = self._get_scale_center_doc()
        transform = (
            QTransform()
            .translate(center_doc.x(), center_doc.y())
            .scale(self.scale_factor, self.scale_factor)
            .translate(-center_doc.x(), -center_doc.y())
        )

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
                return

        self.canvas.temp_image = image_to_modify

    # ------------------------------------------------------------------
    def draw_overlay(self, painter):
        painter.save()

        center = self._get_center()
        handle_pos = self._get_handle_pos()

        base_color = QColor("#0c7bdc")
        hover_color = base_color.lighter(120)

        color_handle = hover_color if self.is_hovering_handle else base_color
        color_center = hover_color if self.is_hovering_center else base_color

        painter.setPen(QPen(color_center, 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, 10, 10)

        painter.setPen(QPen(color_handle, 4))
        painter.drawLine(center, handle_pos)

        painter.setBrush(color_handle)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(handle_pos, 6, 6)

        text_rect = QRectF(center.x() - 40, center.y() - 46, 80, 20)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(text_rect, Qt.AlignCenter, f"{self.scale_factor:.2f}x")

        painter.restore()

