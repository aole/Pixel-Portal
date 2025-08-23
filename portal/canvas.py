from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QPoint
from .drawing import Drawing


class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing_logic = Drawing(self.size())
        self.drawing = False
        self.last_point = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            self.drawing_logic.draw_line(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def paintEvent(self, event):
        canvas_painter = QPainter(self)
        image = self.drawing_logic.get_image()
        canvas_painter.drawImage(self.rect(), image, image.rect())

    def resizeEvent(self, event):
        self.drawing_logic.resize(self.size())
