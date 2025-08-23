from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt


class DrawingLogic:
    def __init__(self, app):
        self.app = app

    def draw_line(self, p1, p2):
        painter = QPainter(self.app.document.image)
        painter.setPen(QColor(Qt.black))
        painter.drawLine(p1, p2)
