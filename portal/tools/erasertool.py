from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainter
from portal.tools.basetool import BaseTool


class EraserTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.last_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.last_point = doc_pos
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return

        self.canvas.temp_image_replaces_active_layer = True
        self.canvas.temp_image = active_layer.image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)

        self.canvas.drawing.draw_line_with_brush(painter, self.last_point, self.last_point, erase=True)

        painter.end()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.canvas.temp_image:
            return

        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        
        self.canvas.drawing.draw_line_with_brush(painter, self.last_point, doc_pos, erase=True)
        self.last_point = doc_pos
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if active_layer and self.canvas.temp_image:
            active_layer.image = self.canvas.temp_image
            active_layer.on_image_change.emit()
            self.canvas.app.add_undo_state()
            self.canvas.temp_image = None
            self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()