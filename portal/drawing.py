from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPoint
import math


class Drawing:
    def __init__(self, app):
        self.app = app

    def draw_brush(self, painter, point):
        if self.app.brush_type == "Circular":
            self.draw_circular_brush(painter, point)
        elif self.app.brush_type == "Square":
            self.draw_square_brush(painter, point)

    def draw_square_brush(self, painter, point):
        pen_width = self.app.pen_width
        offset = pen_width // 2
        top_left = QPoint(point.x() - offset, point.y() - offset)
        painter.drawRect(top_left.x(), top_left.y(), pen_width, pen_width)

    def draw_circular_brush(self, painter, point):
        pen_width = self.app.pen_width
        radius = pen_width / 2.0
        center_x, center_y = point.x(), point.y()

        for y in range(int(center_y - radius), int(center_y + radius) + 1):
            for x in range(int(center_x - radius), int(center_x + radius) + 1):
                dist_x = x - center_x
                dist_y = y - center_y
                if dist_x * dist_x + dist_y * dist_y <= radius * radius:
                    painter.drawPoint(x, y)

    def draw_line_with_brush(self, painter, p1, p2):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if dx == 0 and dy == 0:
            self.draw_brush(painter, p1)
            return

        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return

        x_inc = dx / steps
        y_inc = dy / steps

        x = float(p1.x())
        y = float(p1.y())

        for i in range(int(steps) + 1):
            self.draw_brush(painter, QPoint(round(x), round(y)))
            x += x_inc
            y += y_inc

    def draw_rect(self, painter, rect):
        self.draw_line_with_brush(painter, rect.topLeft(), rect.topRight())
        self.draw_line_with_brush(painter, rect.topRight(), rect.bottomRight())
        self.draw_line_with_brush(painter, rect.bottomRight(), rect.bottomLeft())
        self.draw_line_with_brush(painter, rect.bottomLeft(), rect.topLeft())

    def draw_ellipse(self, painter, rect):
        # Using a simple midpoint algorithm to draw the ellipse with the brush
        center = rect.center()
        rx = rect.width() / 2
        ry = rect.height() / 2

        if rx == 0 or ry == 0:
            return

        # Top and bottom
        for x in range(rect.left(), rect.right() + 1):
            y1 = center.y() - ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            y2 = center.y() + ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            self.draw_brush(painter, QPoint(x, round(y1)))
            self.draw_brush(painter, QPoint(x, round(y2)))

        # Left and right
        for y in range(rect.top(), rect.bottom() + 1):
            x1 = center.x() - rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            x2 = center.x() + rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            self.draw_brush(painter, QPoint(round(x1), y))
            self.draw_brush(painter, QPoint(round(x2), y))

    def flood_fill(self, start_pos, selection_shape=None):
        active_layer = self.app.document.layer_manager.active_layer
        if not active_layer:
            return

        image = active_layer.image
        width = image.width()
        height = image.height()
        x, y = start_pos.x(), start_pos.y()

        if not (0 <= x < width and 0 <= y < height):
            return

        if selection_shape and not selection_shape.contains(start_pos):
            return
            
        target_color = image.pixelColor(x, y)
        fill_color = self.app.pen_color

        if target_color == fill_color:
            return

        stack = [(x, y)]

        while stack:
            x, y = stack.pop()

            if not (0 <= x < width and 0 <= y < height):
                continue

            if selection_shape and not selection_shape.contains(QPoint(x, y)):
                continue
                
            if image.pixelColor(x, y) == target_color:
                image.setPixelColor(x, y, fill_color)
                stack.append((x + 1, y))
                stack.append((x - 1, y))
                stack.append((x, y + 1))
                stack.append((x, y - 1))
