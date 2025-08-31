from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint, QSize
import math


class Drawing:
    def draw_brush(self, painter, point, document_size, brush_type, pen_width, mirror_x, mirror_y):
        doc_width = document_size.width()
        doc_height = document_size.height()

        points_to_draw = {point}
        if mirror_x:
            points_to_draw.add(QPoint(doc_width - 1 - point.x(), point.y()))
        if mirror_y:
            points_to_draw.add(QPoint(point.x(), doc_height - 1 - point.y()))
        if mirror_x and mirror_y:
            points_to_draw.add(QPoint(doc_width - 1 - point.x(), doc_height - 1 - point.y()))

        for p in points_to_draw:
            if brush_type == "Circular":
                self.draw_circular_brush(painter, p, pen_width)
            elif brush_type == "Square":
                self.draw_square_brush(painter, p, pen_width)

    def erase_brush(self, painter, point, document_size, pen_width, mirror_x, mirror_y):
        doc_width = document_size.width()
        doc_height = document_size.height()

        points_to_erase = {point}
        if mirror_x:
            points_to_erase.add(QPoint(doc_width - 1 - point.x(), point.y()))
        if mirror_y:
            points_to_erase.add(QPoint(point.x(), doc_height - 1 - point.y()))
        if mirror_x and mirror_y:
            points_to_erase.add(QPoint(doc_width - 1 - point.x(), doc_height - 1 - point.y()))

        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        pen = QPen(QColor(0, 0, 0, 0), pen_width, Qt.SolidLine)
        painter.setPen(pen)

        for p in points_to_erase:
            painter.drawPoint(p)
        painter.restore()

    def draw_square_brush(self, painter, point, pen_width):
        offset = pen_width // 2
        top_left = QPoint(point.x() - offset, point.y() - offset)
        painter.fillRect(top_left.x(), top_left.y(), pen_width, pen_width, painter.pen().color())

    def draw_circular_brush(self, painter, point, pen_width):
        radius = pen_width / 2.0
        center_x, center_y = point.x(), point.y()

        for y in range(int(center_y - radius), int(center_y + radius) + 1):
            for x in range(int(center_x - radius), int(center_x + radius) + 1):
                dist_x = x - center_x
                dist_y = y - center_y
                if dist_x * dist_x + dist_y * dist_y <= radius * radius:
                    painter.drawPoint(x, y)

    def draw_line_with_brush(self, painter, p1, p2, document_size, brush_type, pen_width, mirror_x, mirror_y, erase=False):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if erase:
            brush_func = lambda p: self.erase_brush(p, document_size, pen_width, mirror_x, mirror_y)
        else:
            brush_func = lambda p: self.draw_brush(p, document_size, brush_type, pen_width, mirror_x, mirror_y)

        if dx == 0 and dy == 0:
            brush_func(p1)
            return

        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return

        x_inc = dx / steps
        y_inc = dy / steps

        x = float(p1.x())
        y = float(p1.y())

        for i in range(int(steps) + 1):
            brush_func(QPoint(round(x), round(y)))
            x += x_inc
            y += y_inc

    def draw_rect(self, painter, rect, document_size, brush_type, pen_width, mirror_x, mirror_y):
        self.draw_line_with_brush(painter, rect.topLeft(), rect.topRight(), document_size, brush_type, pen_width, mirror_x, mirror_y)
        self.draw_line_with_brush(painter, rect.topRight(), rect.bottomRight(), document_size, brush_type, pen_width, mirror_x, mirror_y)
        self.draw_line_with_brush(painter, rect.bottomRight(), rect.bottomLeft(), document_size, brush_type, pen_width, mirror_x, mirror_y)
        self.draw_line_with_brush(painter, rect.bottomLeft(), rect.topLeft(), document_size, brush_type, pen_width, mirror_x, mirror_y)

    def draw_ellipse(self, painter, rect, document_size, brush_type, pen_width, mirror_x, mirror_y):
        center = rect.center()
        rx = rect.width() / 2
        ry = rect.height() / 2

        if rx == 0 or ry == 0:
            return

        for x in range(rect.left(), rect.right() + 1):
            y1 = center.y() - ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            y2 = center.y() + ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            self.draw_brush(painter, QPoint(x, round(y1)), document_size, brush_type, pen_width, mirror_x, mirror_y)
            self.draw_brush(painter, QPoint(x, round(y2)), document_size, brush_type, pen_width, mirror_x, mirror_y)

        for y in range(rect.top(), rect.bottom() + 1):
            x1 = center.x() - rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            x2 = center.x() + rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            self.draw_brush(painter, QPoint(round(x1), y), document_size, brush_type, pen_width, mirror_x, mirror_y)
            self.draw_brush(painter, QPoint(round(x2), y), document_size, brush_type, pen_width, mirror_x, mirror_y)

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
                