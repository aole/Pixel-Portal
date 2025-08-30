from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt

from portal.tools.basetool import BaseTool
from ..command import ShapeCommand


class EllipseTool(BaseTool):
    name = "Ellipse"
    icon = "icons/toolellipse.png"
    shortcut = "c"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self.canvas.temp_image_replaces_active_layer = True
        # The command will need the original image state
        self.command_generated.emit(("get_active_layer_image", "ellipse_tool_start"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas._pen_color))

        end_point = doc_pos
        if event.modifiers() & Qt.ShiftModifier:
            dx = end_point.x() - self.start_point.x()
            dy = end_point.y() - self.start_point.y()
            size = min(abs(dx), abs(dy))
            end_point = QPoint(
                self.start_point.x() + size * (1 if dx > 0 else -1),
                self.start_point.y() + size * (1 if dy > 0 else -1),
            )

        rect = QRect(self.start_point, end_point).normalized()
        self.canvas.drawing.draw_ellipse(painter, rect, self.canvas._document_size)
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        end_point = doc_pos
        if event.modifiers() & Qt.ShiftModifier:
            dx = end_point.x() - self.start_point.x()
            dy = end_point.y() - self.start_point.y()
            size = min(abs(dx), abs(dy))
            end_point = QPoint(
                self.start_point.x() + size * (1 if dx > 0 else -1),
                self.start_point.y() + size * (1 if dy > 0 else -1),
            )

        rect = QRect(self.start_point, end_point).normalized()

        shape_data = {
            "rect": rect,
            "shape_type": 'ellipse',
            "color": self.canvas._pen_color,
            "width": self.canvas._pen_width,
            "selection_shape": self.canvas.selection_shape,
        }
        self.command_generated.emit(("shape", shape_data))

        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
