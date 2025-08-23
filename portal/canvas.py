from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QPoint
from .drawing import DrawingLogic


class Canvas(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.drawing_logic = DrawingLogic(self.app)
        self.drawing = False
        self.dragging = False
        self.last_point = QPoint()

    def get_doc_coords(self, canvas_pos):
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width) / 2 + self.app.document.x_offset
        y_offset = (canvas_height - doc_height) / 2 + self.app.document.y_offset

        return QPoint(canvas_pos.x() - x_offset, canvas_pos.y() - y_offset)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = self.get_doc_coords(event.pos())
        if event.button() == Qt.MiddleButton:
            self.dragging = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            current_point = self.get_doc_coords(event.pos())
            self.drawing_logic.draw_line(self.last_point, current_point)
            self.last_point = current_point
            self.update()
        if (event.buttons() & Qt.MiddleButton) and self.dragging:
            delta = event.pos() - self.last_point
            self.app.document.x_offset += delta.x()
            self.app.document.y_offset += delta.y()
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
        if event.button() == Qt.MiddleButton:
            self.dragging = False

    def paintEvent(self, event):
        canvas_painter = QPainter(self)

        # Fill background
        canvas_painter.fillRect(self.rect(), self.palette().window())

        # Center and draw document
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        x = (canvas_width - doc_width) / 2 + self.app.document.x_offset
        y = (canvas_height - doc_height) / 2 + self.app.document.y_offset

        image = self.app.document.image
        canvas_painter.drawImage(x, y, image)

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass
