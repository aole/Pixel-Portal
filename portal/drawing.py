from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint, QSize
import math


class Drawing:
    def __init__(self):
        # These will be set by the Canvas
        self._pen_color = QColor("black")
        self._pen_width = 1
        self._brush_type = "Circular"
        self._mirror_x = False
        self._mirror_y = False

    def set_pen_color(self, color):
        self._pen_color = color

    def set_pen_width(self, width):
        self._pen_width = width

    def set_brush_type(self, brush_type):
        self._brush_type = brush_type

    def set_mirror_x(self, enabled):
        self._mirror_x = enabled

    def set_mirror_y(self, enabled):
        self._mirror_y = enabled

    def draw_brush(self, painter, point, document_size):
        doc_width = document_size.width
        doc_height = document_size.height

        points_to_draw = {point}
        if self._mirror_x:
            points_to_draw.add(QPoint(doc_width - 1 - point.x(), point.y()))
        if self._mirror_y:
            points_to_draw.add(QPoint(point.x(), doc_height - 1 - point.y()))
        if self._mirror_x and self._mirror_y:
            points_to_draw.add(QPoint(doc_width - 1 - point.x(), doc_height - 1 - point.y()))

        for p in points_to_draw:
            if self._brush_type == "Circular":
                self.draw_circular_brush(painter, p)
            elif self._brush_type == "Square":
                self.draw_square_brush(painter, p)

    def erase_brush(self, painter, point, document_size):
        doc_width = document_size.width()
        doc_height = document_size.height()

        points_to_erase = {point}
        if self._mirror_x:
            points_to_erase.add(QPoint(doc_width - 1 - point.x(), point.y()))
        if self._mirror_y:
            points_to_erase.add(QPoint(point.x(), doc_height - 1 - point.y()))
        if self._mirror_x and self._mirror_y:
            points_to_erase.add(QPoint(doc_width - 1 - point.x(), doc_height - 1 - point.y()))

        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        pen = QPen(QColor(0, 0, 0, 0), self._pen_width, Qt.SolidLine)
        painter.setPen(pen)

        for p in points_to_erase:
            painter.drawPoint(p)
        painter.restore()

    def draw_square_brush(self, painter, point):
        pen_width = self._pen_width
        offset = pen_width // 2
        top_left = QPoint(point.x() - offset, point.y() - offset)
        painter.fillRect(top_left.x(), top_left.y(), pen_width, pen_width, painter.pen().color())

    def draw_circular_brush(self, painter, point):
        pen_width = self._pen_width
        radius = pen_width / 2.0
        center_x, center_y = point.x(), point.y()

        for y in range(int(center_y - radius), int(center_y + radius) + 1):
            for x in range(int(center_x - radius), int(center_x + radius) + 1):
                dist_x = x - center_x
                dist_y = y - center_y
                if dist_x * dist_x + dist_y * dist_y <= radius * radius:
                    painter.drawPoint(x, y)

    def draw_line_with_brush(self, painter, p1, p2, document_size, erase=False):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        brush_func = self.erase_brush if erase else self.draw_brush

        if dx == 0 and dy == 0:
            brush_func(painter, p1, document_size)
            return

        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return

        x_inc = dx / steps
        y_inc = dy / steps

        x = float(p1.x())
        y = float(p1.y())

        for i in range(int(steps) + 1):
            brush_func(painter, QPoint(round(x), round(y)), document_size)
            x += x_inc
            y += y_inc

    def draw_rect(self, painter, rect, document_size):
        self.draw_line_with_brush(painter, rect.topLeft(), rect.topRight(), document_size)
        self.draw_line_with_brush(painter, rect.topRight(), rect.bottomRight(), document_size)
        self.draw_line_with_brush(painter, rect.bottomRight(), rect.bottomLeft(), document_size)
        self.draw_line_with_brush(painter, rect.bottomLeft(), rect.topLeft(), document_size)

    def draw_ellipse(self, painter, rect, document_size):
        center = rect.center()
        rx = rect.width() / 2
        ry = rect.height() / 2

        if rx == 0 or ry == 0:
            return

        for x in range(rect.left(), rect.right() + 1):
            y1 = center.y() - ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            y2 = center.y() + ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            self.draw_brush(painter, QPoint(x, round(y1)), document_size)
            self.draw_brush(painter, QPoint(x, round(y2)), document_size)

        for y in range(rect.top(), rect.bottom() + 1):
            x1 = center.x() - rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            x2 = center.x() + rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            self.draw_brush(painter, QPoint(round(x1), y), document_size)
            self.draw_brush(painter, QPoint(round(x2), y), document_size)

    def flood_fill(self, layer, start_pos, fill_color, selection_shape=None):
        if not layer:
            return

        image = layer.image
        width = image.width()
        height = image.height()
        x, y = start_pos.x(), start_pos.y()

        if not (0 <= x < width and 0 <= y < height):
            return

        if selection_shape and not selection_shape.contains(start_pos):
            return
            
        target_color = image.pixelColor(x, y)

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
                