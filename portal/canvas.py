from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from .drawing import DrawingLogic


class Canvas(QWidget):
    cursor_pos_changed = Signal(QPoint)
    zoom_changed = Signal(float)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.drawing_logic = DrawingLogic(self.app)
        self.drawing = False
        self.dragging = False
        self.x_offset = 0
        self.y_offset = 0
        self.zoom = 1.0
        self.last_point = QPoint()
        self.temp_image = None
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.zoom_changed.emit(self.zoom)
        doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(doc_pos)

    def get_doc_coords(self, canvas_pos):
        doc_width_scaled = self.app.document.width * self.zoom
        doc_height_scaled = self.app.document.height * self.zoom
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        if self.zoom == 0:
            return QPoint(0, 0)

        return QPoint(
            (canvas_pos.x() - x_offset) / self.zoom,
            (canvas_pos.y() - y_offset) / self.zoom,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = self.get_doc_coords(event.pos())
            self.temp_image = self.app.document.image.copy()
        if event.button() == Qt.MiddleButton:
            self.dragging = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(doc_pos)

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            current_point = self.get_doc_coords(event.pos())
            painter = QPainter(self.temp_image)
            painter.setPen(self.app.pen_color)
            painter.drawLine(self.last_point, current_point)
            self.last_point = current_point
            self.update()
        if (event.buttons() & Qt.MiddleButton) and self.dragging:
            delta = event.pos() - self.last_point
            self.x_offset += delta.x()
            self.y_offset += delta.y()
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.app.document.image = self.temp_image
            self.temp_image = None
            self.app.add_undo_state()
            self.update()
        if event.button() == Qt.MiddleButton:
            self.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        mouse_pos = event.position().toPoint()
        doc_pos_before_zoom = self.get_doc_coords(mouse_pos)

        # Zoom
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom *= 1.25
        else:
            self.zoom /= 1.25

        # Clamp zoom level
        self.zoom = max(0.1, min(self.zoom, 20.0))

        # Adjust pan to keep doc_pos_before_zoom at the same mouse_pos
        doc_width_scaled = self.app.document.width * self.zoom
        doc_height_scaled = self.app.document.height * self.zoom

        # This is the top-left of the document in canvas coordinates *without* the old self.x_offset
        base_x_offset = (self.width() - doc_width_scaled) / 2
        base_y_offset = (self.height() - doc_height_scaled) / 2

        # This is where the doc_pos would be with the new zoom but without any panning
        canvas_x_after_zoom_no_pan = base_x_offset + doc_pos_before_zoom.x() * self.zoom
        canvas_y_after_zoom_no_pan = base_y_offset + doc_pos_before_zoom.y() * self.zoom

        # We want this point to be at mouse_pos. The difference is the required pan offset.
        self.x_offset = mouse_pos.x() - canvas_x_after_zoom_no_pan
        self.y_offset = mouse_pos.y() - canvas_y_after_zoom_no_pan

        self.update()
        self.zoom_changed.emit(self.zoom)

    def paintEvent(self, event):
        canvas_painter = QPainter(self)
        canvas_painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        # Fill background
        canvas_painter.fillRect(self.rect(), self.palette().window())

        # Center and draw document
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        doc_width_scaled = doc_width * self.zoom
        doc_height_scaled = doc_height * self.zoom

        x = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        if self.drawing and self.temp_image:
            image = self.temp_image
        else:
            image = self.app.document.image

        target_rect = QRect(x, y, int(doc_width_scaled), int(doc_height_scaled))
        canvas_painter.drawImage(target_rect, image)

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass

    def draw_line_for_test(self, p1, p2):
        self.drawing_logic.draw_line(p1, p2)
