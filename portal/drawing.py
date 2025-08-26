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

    def draw_rect(self, painter, rect):
        painter.setPen(self.pen_color)
        painter.drawRect(rect)

    def draw_ellipse(self, painter, rect):
        painter.setPen(self.pen_color)
        painter.drawEllipse(rect)

    def draw_selection_rect(self, painter, rect, zoom):
        pen = painter.pen()
        pen.setColor(QColor("black"))
        pen.setWidthF(1.0 / zoom)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect)

    def draw_selection_ellipse(self, painter, rect, zoom):
        pen = painter.pen()
        pen.setColor(QColor("black"))
        pen.setWidthF(1.0 / zoom)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(rect)

    def flood_fill(self, start_pos):
        active_layer = self.app.document.layer_manager.active_layer
        if not active_layer:
            return

        image = active_layer.image
        width = image.width()
        height = image.height()
        x, y = start_pos.x(), start_pos.y()

        if not (0 <= x < width and 0 <= y < height):
            return

        target_color = image.pixelColor(x, y)
        fill_color = self.pen_color

        if target_color == fill_color:
            return

        stack = [(x, y)]

        while stack:
            x, y = stack.pop()

            if not (0 <= x < width and 0 <= y < height):
                continue

            if image.pixelColor(x, y) == target_color:
                image.setPixelColor(x, y, fill_color)
                stack.append((x + 1, y))
                stack.append((x - 1, y))
                stack.append((x, y + 1))
                stack.append((x, y - 1))
