from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt

from portal.tools.basetool import BaseTool
from ..drawing import Drawing


class LineTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.drawing = Drawing(self.canvas.app)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return
        self.canvas.temp_image_replaces_active_layer = True
        self.canvas.original_image = active_layer.image.copy()
        self.canvas.temp_image = self.canvas.original_image.copy()

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.canvas.temp_image:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.app.pen_color))
        self.drawing.draw_line_with_brush(painter, self.start_point, doc_pos)
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer or not self.canvas.temp_image:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.app.pen_color))
        self.drawing.draw_line_with_brush(painter, self.start_point, doc_pos)

        active_layer.image = self.canvas.temp_image
        active_layer.on_image_change.emit()
        self.canvas.app.add_undo_state()
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
