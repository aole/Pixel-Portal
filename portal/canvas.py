from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import Qt, QPoint
from .drawing import DrawingLogic


class Canvas(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.drawing_logic = DrawingLogic(self.app)
        self.drawing = False
        self.dragging = False
        self.x_offset = 0
        self.y_offset = 0
        self.last_point = QPoint()

        self.app.document.selection_changed.connect(self.update)

    def get_doc_coords(self, canvas_pos):
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height) / 2 + self.y_offset

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
            self.x_offset += delta.x()
            self.y_offset += delta.y()
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

        x = (canvas_width - doc_width) / 2 + self.x_offset
        y = (canvas_height - doc_height) / 2 + self.y_offset

        image = self.app.document.image
        canvas_painter.drawImage(x, y, image)

        # Draw selection
        canvas_painter.setBrush(QBrush(Qt.NoBrush))
        pen = QPen(QColor(0, 0, 0, 255))
        pen.setStyle(Qt.DashLine)
        canvas_painter.setPen(pen)

        selection_path = self.app.document.selection.translated(x,y)
        canvas_painter.drawPath(selection_path)

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass
