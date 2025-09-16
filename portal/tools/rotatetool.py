import math
from PySide6.QtGui import QCursor, QPen, QColor, QTransform, QImage, QPainter
from PySide6.QtCore import Qt, QPoint, QPointF, Signal
from portal.tools.basetool import BaseTool
from portal.commands.layer_commands import RotateLayerCommand


class RotateTool(BaseTool):
    """
    A tool for rotating the layer.
    """
    name = "Rotate"
    icon = "icons/toolrotate.png"
    category = "draw"
    angle_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)
        self.angle = 0.0
        self.is_hovering_handle = False
        self.is_hovering_center = False
        self.drag_mode = None  # None, 'rotate', or 'pivot'
        self.original_image = None
        self.pivot_doc = QPoint(0, 0)

    def activate(self):
        self.pivot_doc = self.calculate_default_pivot_doc()

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
        center = self.get_center()
        return QPointF(
            center.x() + 100 * math.cos(self.angle),
            center.y() + 100 * math.sin(self.angle),
        )

    def mousePressEvent(self, event, doc_pos):
        if self.is_hovering_handle:
            self.drag_mode = 'rotate'
            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            active_layer = layer_manager.active_layer
            if active_layer:
                self.original_image = active_layer.image.copy()
                self.canvas.temp_image_replaces_active_layer = True
        elif self.is_hovering_center:
            self.drag_mode = 'pivot'

    def mouseHoverEvent(self, event, doc_pos):
        canvas_pos = QPointF(event.pos())
        handle_pos = self.get_handle_pos()
        center_pos = self.get_center()

        dx = canvas_pos.x() - handle_pos.x()
        dy = canvas_pos.y() - handle_pos.y()
        distance_handle = math.sqrt(dx * dx + dy * dy)

        dx_center = canvas_pos.x() - center_pos.x()
        dy_center = canvas_pos.y() - center_pos.y()
        distance_center = math.sqrt(dx_center * dx_center + dy_center * dy_center)

        new_hover_handle = (distance_handle <= 6)
        new_hover_center = (distance_center <= 10)

        if self.is_hovering_handle != new_hover_handle or self.is_hovering_center != new_hover_center:
            self.is_hovering_handle = new_hover_handle
            self.is_hovering_center = new_hover_center
            self.canvas.repaint()

    def mouseMoveEvent(self, event, doc_pos):
        if not self.drag_mode:
            return

        if self.drag_mode == 'rotate':
            canvas_pos = QPointF(event.pos())
            center = self.get_center()

            dx = canvas_pos.x() - center.x()
            dy = canvas_pos.y() - center.y()
            self.angle = math.atan2(dy, dx)
            self.angle_changed.emit(math.degrees(self.angle))

            if self.original_image:
                image_to_modify = self.original_image.copy()
                painter = QPainter(image_to_modify)
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

                center = self.get_rotation_center_doc()
                transform = QTransform().translate(center.x(), center.y()).rotate(math.degrees(self.angle)).translate(-center.x(), -center.y())

                selection_shape = self.canvas.selection_shape
                if selection_shape:
                    painter.setClipPath(selection_shape)
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.fillRect(self.original_image.rect(), Qt.transparent)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                    painter.setTransform(transform)
                    painter.drawImage(0, 0, self.original_image)
                else:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.fillRect(self.original_image.rect(), Qt.transparent)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.setTransform(transform)
                    painter.drawImage(0, 0, self.original_image)

                painter.end()
                self.canvas.temp_image = image_to_modify

            self.canvas.update()
        elif self.drag_mode == 'pivot':
            self.pivot_doc = doc_pos
            self.canvas.update()

    def mouseReleaseEvent(self, event, doc_pos):
        if self.drag_mode == 'rotate':
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False

            layer_manager = self._get_active_layer_manager()
            if layer_manager is None:
                return

            active_layer = layer_manager.active_layer
            if active_layer:
                center_doc = self.get_rotation_center_doc()
                selection_shape = self.canvas.selection_shape
                command = RotateLayerCommand(active_layer, math.degrees(self.angle), center_doc, selection_shape)
                self.command_generated.emit(command)

            self.original_image = None
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
            self.original_image = None
            self.angle = 0.0
            self.angle_changed.emit(math.degrees(self.angle))
        self.drag_mode = None

    def draw_overlay(self, painter):
        painter.save()

        center = self.get_center()
        handle_pos = self.get_handle_pos()

        color_handle = QColor("lightgreen") if self.is_hovering_handle else QColor("green")
        color_center = QColor("lightgreen") if self.is_hovering_center else QColor("green")

        # Circle (pivot)
        pen = QPen(color_center, 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, 10, 10)

        # Line
        painter.setPen(QPen(color_handle, 4))
        painter.drawLine(center, handle_pos)

        # Handle
        painter.setBrush(color_handle)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(handle_pos, 6, 6)

        painter.restore()
