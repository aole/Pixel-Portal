from PySide6.QtGui import QPainter, QColor, QPen, QImage
from PySide6.QtCore import Qt, QPoint, QSize
import math


class Drawing:
    def draw_brush(
        self,
        painter,
        point,
        document_size,
        brush_type,
        pen_width,
        mirror_x,
        mirror_y,
        wrap=False,
        pattern: QImage | None = None,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        doc_width = document_size.width()
        doc_height = document_size.height()

        base_x = point.x()
        base_y = point.y()
        if wrap and doc_width:
            base_x %= doc_width
        if wrap and doc_height:
            base_y %= doc_height
        base_point = QPoint(base_x, base_y)

        points_to_draw = self._calculate_mirror_points(
            base_point,
            document_size,
            mirror_x,
            mirror_y,
            wrap,
            mirror_x_position,
            mirror_y_position,
        )

        for p in points_to_draw:
            if brush_type == "Pattern" and pattern is not None and not pattern.isNull():
                half_w = pattern.width() // 2
                half_h = pattern.height() // 2
                if pattern.width() > 0 and pattern.height() > 0:
                    top_left = QPoint(p.x() - half_w, p.y() - half_h)
                    painter.drawImage(top_left, pattern)
            elif brush_type == "Circular":
                self.draw_circular_brush(painter, p, pen_width)
            elif brush_type == "Square":
                self.draw_square_brush(painter, p, pen_width)

    def erase_brush(
        self,
        painter,
        point,
        document_size,
        pen_width,
        mirror_x,
        mirror_y,
        wrap=False,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        doc_width = document_size.width()
        doc_height = document_size.height()

        base_x = point.x()
        base_y = point.y()
        if wrap and doc_width:
            base_x %= doc_width
        if wrap and doc_height:
            base_y %= doc_height
        base_point = QPoint(base_x, base_y)

        points_to_erase = self._calculate_mirror_points(
            base_point,
            document_size,
            mirror_x,
            mirror_y,
            wrap,
            mirror_x_position,
            mirror_y_position,
        )

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

    def _calculate_mirror_points(
        self,
        base_point: QPoint,
        document_size: QSize,
        mirror_x: bool,
        mirror_y: bool,
        wrap: bool,
        mirror_x_position: float | None,
        mirror_y_position: float | None,
    ) -> set[QPoint]:
        width = document_size.width()
        height = document_size.height()

        points = {QPoint(base_point)}

        axis_x = mirror_x_position
        if axis_x is None and width:
            axis_x = (width - 1) / 2.0
        axis_y = mirror_y_position
        if axis_y is None and height:
            axis_y = (height - 1) / 2.0

        def add_point(x: int, y: int):
            if wrap:
                if width:
                    x %= width
                if height:
                    y %= height
                points.add(QPoint(int(x), int(y)))
            else:
                if 0 <= x < width and 0 <= y < height:
                    points.add(QPoint(int(x), int(y)))

        if mirror_x and axis_x is not None:
            mirrored_x = int(round(2 * axis_x - base_point.x()))
            add_point(mirrored_x, base_point.y())

        if mirror_y and axis_y is not None:
            mirrored_y = int(round(2 * axis_y - base_point.y()))
            add_point(base_point.x(), mirrored_y)

        if mirror_x and mirror_y and axis_x is not None and axis_y is not None:
            mirrored_x = int(round(2 * axis_x - base_point.x()))
            mirrored_y = int(round(2 * axis_y - base_point.y()))
            add_point(mirrored_x, mirrored_y)

        return points

    def draw_line_with_brush(
        self,
        painter,
        p1,
        p2,
        document_size,
        brush_type,
        pen_width,
        mirror_x,
        mirror_y,
        wrap=False,
        erase=False,
        pattern: QImage | None = None,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        width = document_size.width()
        height = document_size.height()

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if erase:
            brush_func = lambda p: self.erase_brush(
                painter,
                p,
                document_size,
                pen_width,
                mirror_x,
                mirror_y,
                wrap,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )
        else:
            brush_func = lambda p: self.draw_brush(
                painter,
                p,
                document_size,
                brush_type,
                pen_width,
                mirror_x,
                mirror_y,
                wrap,
                pattern=pattern,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )

        if dx == 0 and dy == 0:
            brush_func(p1)
            return

        if brush_type == "Pattern" and pattern is not None and not pattern.isNull():
            step_length = max(pattern.width(), pattern.height())
            if step_length <= 0:
                step_length = 1
            distance = math.hypot(dx, dy)
            steps = max(math.ceil(distance / step_length), 1)
        else:
            steps = max(abs(dx), abs(dy))
            if steps == 0:
                return

        x_inc = dx / steps
        y_inc = dy / steps

        x = float(p1.x())
        y = float(p1.y())

        for _ in range(int(steps) + 1):
            if wrap:
                wrapped_point = QPoint(round(x) % width, round(y) % height)
            else:
                wrapped_point = QPoint(round(x), round(y))
            brush_func(wrapped_point)
            x += x_inc
            y += y_inc

    def draw_rect(
        self,
        painter,
        rect,
        document_size,
        brush_type,
        pen_width,
        mirror_x,
        mirror_y,
        wrap=False,
        pattern: QImage | None = None,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        self.draw_line_with_brush(
            painter,
            rect.topLeft(),
            rect.topRight(),
            document_size,
            brush_type,
            pen_width,
            mirror_x,
            mirror_y,
            wrap=wrap,
            pattern=pattern,
            mirror_x_position=mirror_x_position,
            mirror_y_position=mirror_y_position,
        )
        self.draw_line_with_brush(
            painter,
            rect.topRight(),
            rect.bottomRight(),
            document_size,
            brush_type,
            pen_width,
            mirror_x,
            mirror_y,
            wrap=wrap,
            pattern=pattern,
            mirror_x_position=mirror_x_position,
            mirror_y_position=mirror_y_position,
        )
        self.draw_line_with_brush(
            painter,
            rect.bottomRight(),
            rect.bottomLeft(),
            document_size,
            brush_type,
            pen_width,
            mirror_x,
            mirror_y,
            wrap=wrap,
            pattern=pattern,
            mirror_x_position=mirror_x_position,
            mirror_y_position=mirror_y_position,
        )
        self.draw_line_with_brush(
            painter,
            rect.bottomLeft(),
            rect.topLeft(),
            document_size,
            brush_type,
            pen_width,
            mirror_x,
            mirror_y,
            wrap=wrap,
            pattern=pattern,
            mirror_x_position=mirror_x_position,
            mirror_y_position=mirror_y_position,
        )

    def draw_ellipse(
        self,
        painter,
        rect,
        document_size,
        brush_type,
        pen_width,
        mirror_x,
        mirror_y,
        wrap=False,
        pattern: QImage | None = None,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        center = rect.center()
        rx = rect.width() / 2
        ry = rect.height() / 2

        if rx == 0 or ry == 0:
            return

        for x in range(rect.left(), rect.right() + 1):
            y1 = center.y() - ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            y2 = center.y() + ry * math.sqrt(1 - ((x - center.x()) / rx) ** 2)
            self.draw_brush(
                painter,
                QPoint(x, round(y1)),
                document_size,
                brush_type,
                pen_width,
                mirror_x,
                mirror_y,
                wrap=wrap,
                pattern=pattern,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )
            self.draw_brush(
                painter,
                QPoint(x, round(y2)),
                document_size,
                brush_type,
                pen_width,
                mirror_x,
                mirror_y,
                wrap=wrap,
                pattern=pattern,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )

        for y in range(rect.top(), rect.bottom() + 1):
            x1 = center.x() - rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            x2 = center.x() + rx * math.sqrt(1 - ((y - center.y()) / ry) ** 2)
            self.draw_brush(
                painter,
                QPoint(round(x1), y),
                document_size,
                brush_type,
                pen_width,
                mirror_x,
                mirror_y,
                wrap=wrap,
                pattern=pattern,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )
            self.draw_brush(
                painter,
                QPoint(round(x2), y),
                document_size,
                brush_type,
                pen_width,
                mirror_x,
                mirror_y,
                wrap=wrap,
                pattern=pattern,
                mirror_x_position=mirror_x_position,
                mirror_y_position=mirror_y_position,
            )

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
                