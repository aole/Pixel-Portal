from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QMouseEvent, QPen, Qt

from portal.tools.basetool import BaseTool


class PenTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.last_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.last_point = doc_pos
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return

        self.canvas.original_image = active_layer.image.copy()
        self.canvas.temp_image = self.canvas.original_image.copy()

        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        pen = QPen(self.canvas.app.pen_color, self.canvas.app.pen_width, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawPoint(self.last_point)
        painter.end()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.canvas.temp_image:
            return

        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        pen = QPen(self.canvas.app.pen_color, self.canvas.app.pen_width, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawLine(self.last_point, doc_pos)
        self.last_point = doc_pos
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if active_layer and self.canvas.temp_image:
            active_layer.image = self.canvas.temp_image
            self.canvas.app.add_undo_state()
            self.canvas.temp_image = None
            self.canvas.original_image = None
        self.canvas.update()