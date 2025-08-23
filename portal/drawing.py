from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt, QPoint, QSize


class Drawing:
    def __init__(self, size):
        self.image = QImage(size, QImage.Format_ARGB32)
        self.image.fill(Qt.white)

    def draw_line(self, p1, p2):
        painter = QPainter(self.image)
        painter.setPen(QColor(Qt.black))
        painter.drawLine(p1, p2)

    def get_image(self):
        return self.image

    def resize(self, size):
        if size.width() > self.image.width() or size.height() > self.image.height():
            new_image = QImage(size, QImage.Format_ARGB32)
            new_image.fill(Qt.white)
            painter = QPainter(new_image)
            painter.drawImage(QPoint(0, 0), self.image)
            self.image = new_image
