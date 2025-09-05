from PySide6.QtGui import QCursor, QPen, QColor
from PySide6.QtCore import Qt, QPoint
from portal.tools.basetool import BaseTool


class RotateTool(BaseTool):
    """
    A tool for rotating the layer.
    """
    name = "Rotate"
    icon = "icons/toolrotate.png"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(Qt.ArrowCursor)

    def draw_overlay(self, painter):
        painter.save()

        target_rect = self.canvas.get_target_rect()

        if self.canvas.selection_shape:
            center_doc = self.canvas.selection_shape.boundingRect().center()
            center = self.canvas.get_canvas_coords(center_doc)
        else:
            center = target_rect.center()

        # Circle
        pen = QPen(QColor("green"), 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, 10, 10)

        # Line
        painter.drawLine(center, QPoint(center.x() + 100, center.y()))

        # Handle
        painter.setBrush(QColor("green"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(center.x() + 100, center.y()), 6, 6)

        painter.restore()
