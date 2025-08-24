from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt


class DrawingLogic:
    def __init__(self, app):
        self.app = app
        self.pen_color = self.app.pen_color
        self.app.pen_color_changed.connect(self.on_pen_color_changed)

    def on_pen_color_changed(self, color):
        self.pen_color = color

    def draw_line(self, p1, p2):
        active_layer = self.app.document.layer_manager.active_layer
        if active_layer:
            painter = QPainter(active_layer.image)
            painter.setPen(self.pen_color)
            painter.drawLine(p1, p2)
