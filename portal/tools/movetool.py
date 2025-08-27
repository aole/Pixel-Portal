from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QImage, QPainter, Qt

from portal.tools.basetool import BaseTool


class MoveTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.moving_selection = False

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer:
            return

        if self.canvas.selection_shape:
            self.moving_selection = True
            self.canvas.original_image = QImage(active_layer.image.size(), QImage.Format_ARGB32)
            self.canvas.original_image.fill(Qt.transparent)
            painter = QPainter(self.canvas.original_image)
            painter.setClipPath(self.canvas.selection_shape)
            painter.drawImage(0, 0, active_layer.image)
            painter.end()

            painter = QPainter(active_layer.image)
            painter.setClipPath(self.canvas.selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(active_layer.image.rect(), Qt.transparent)
            painter.end()
        else:
            self.canvas.original_image = active_layer.image.copy()

        self.canvas.temp_image = QImage(active_layer.image.size(), QImage.Format_ARGB32)
        self.canvas.temp_image.fill(Qt.transparent)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.canvas.original_image:
            return

        delta = doc_pos - self.start_point
        self.canvas.temp_image.fill(Qt.transparent)
        painter = QPainter(self.canvas.temp_image)
        painter.drawImage(delta, self.canvas.original_image)
        painter.end()
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.canvas.app.document.layer_manager.active_layer
        if not active_layer or not self.canvas.original_image:
            return

        delta = doc_pos - self.start_point
        if self.moving_selection:
            painter = QPainter(active_layer.image)
            painter.drawImage(delta, self.canvas.original_image)
            painter.end()
            self.moving_selection = False
        else:
            active_layer.image.fill(Qt.transparent)
            painter = QPainter(active_layer.image)
            painter.drawImage(delta, self.canvas.original_image)
            painter.end()

        self.canvas.app.add_undo_state()
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.update()
