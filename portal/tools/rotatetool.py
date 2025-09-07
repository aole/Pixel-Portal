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
    angle_changed = Signal(float)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)
        self.angle = 0.0
        self.is_hovering_handle = False
        self.is_dragging = False
        self.original_image = None

    def get_rotation_center_doc(self) -> QPoint:
        if self.canvas.selection_shape:
            return self.canvas.selection_shape.boundingRect().center().toPoint()
        else:
            active_layer = self.canvas.document.layer_manager.active_layer
            if active_layer:
                return active_layer.image.rect().center()
            return QPoint(0, 0) # Fallback

    def get_center(self) -> QPointF:
        target_rect = self.canvas.get_target_rect()
        if self.canvas.selection_shape:
            center_doc = self.canvas.selection_shape.boundingRect().center()
            doc_width_scaled = self.canvas._document_size.width() * self.canvas.zoom
            doc_height_scaled = self.canvas._document_size.height() * self.canvas.zoom
            canvas_width = self.canvas.width()
            canvas_height = self.canvas.height()
            x_offset = (canvas_width - doc_width_scaled) / 2 + self.canvas.x_offset
            y_offset = (canvas_height - doc_height_scaled) / 2 + self.canvas.y_offset
            return QPointF(
                center_doc.x() * self.canvas.zoom + x_offset,
                center_doc.y() * self.canvas.zoom + y_offset,
            )
        else:
            return QPointF(target_rect.center())

    def get_handle_pos(self) -> QPointF:
        center = self.get_center()
        return QPointF(
            center.x() + 100 * math.cos(self.angle),
            center.y() + 100 * math.sin(self.angle),
        )

    def mousePressEvent(self, event, doc_pos):
        if self.is_hovering_handle:
            self.is_dragging = True
            active_layer = self.canvas.document.layer_manager.active_layer
            if active_layer:
                self.original_image = active_layer.image.copy()
                self.canvas.temp_image_replaces_active_layer = True

    def mouseHoverEvent(self, event, doc_pos):
        canvas_pos = QPointF(event.pos())
        handle_pos = self.get_handle_pos()

        dx = canvas_pos.x() - handle_pos.x()
        dy = canvas_pos.y() - handle_pos.y()
        distance = math.sqrt(dx * dx + dy * dy)

        new_hover_state = (distance <= 6)

        if self.is_hovering_handle != new_hover_state:
            self.is_hovering_handle = new_hover_state
            self.canvas.repaint()

    def mouseMoveEvent(self, event, doc_pos):
        if not self.is_dragging:
            return

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
                painter.setTransform(transform)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(self.original_image.rect(), Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.drawImage(0, 0, self.original_image)

            painter.end()
            self.canvas.temp_image = image_to_modify

        self.canvas.update()

    def mouseReleaseEvent(self, event, doc_pos):
        if self.is_dragging:
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False

            active_layer = self.canvas.document.layer_manager.active_layer
            if active_layer:
                center_doc = self.get_rotation_center_doc()
                selection_shape = self.canvas.selection_shape
                command = RotateLayerCommand(active_layer, math.degrees(self.angle), center_doc, selection_shape)
                self.command_generated.emit(command)

            self.is_dragging = False
            self.original_image = None
            self.angle = 0.0
            self.angle_changed.emit(math.degrees(self.angle))
        else:
            self.is_dragging = False

    def deactivate(self):
        if self.is_dragging:
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False
            if self.original_image and self.canvas.document.layer_manager.active_layer:
                self.canvas.document.layer_manager.active_layer.image = self.original_image
                self.canvas.document.layer_manager.active_layer.on_image_change.emit()
            self.is_dragging = False
            self.original_image = None
            self.angle = 0.0
            self.angle_changed.emit(math.degrees(self.angle))

    def draw_overlay(self, painter):
        painter.save()

        center = self.get_center()
        handle_pos = self.get_handle_pos()

        color = QColor("lightgreen") if self.is_hovering_handle else QColor("green")

        # Circle
        pen = QPen(color, 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, 10, 10)

        # Line
        painter.drawLine(center, handle_pos)

        # Handle
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(handle_pos, 6, 6)

        painter.restore()
