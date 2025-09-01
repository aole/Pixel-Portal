from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt

from portal.tools.basetool import BaseTool
from portal.core.command import ShapeCommand


class RectangleTool(BaseTool):
    name = "Rectangle"
    icon = "icons/toolrect.png"
    shortcut = "r"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self.canvas.temp_image_replaces_active_layer = True
        self.command_generated.emit(("get_active_layer_image", "rectangle_tool_start"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.drawing_context.pen_color))

        end_point = doc_pos
        if event.modifiers() & Qt.ShiftModifier:
            dx = end_point.x() - self.start_point.x()
            dy = end_point.y() - self.start_point.y()
            size = min(abs(dx), abs(dy))
            end_point = QPoint(
                self.start_point.x() + size * (1 if dx > 0 else -1),
                self.start_point.y() + size * (1 if dy > 0 else -1),
            )

        rect = QRect(self.start_point, end_point).normalized()
        self.canvas.drawing.draw_rect(
            painter,
            rect,
            self.canvas._document_size,
            self.canvas.drawing_context.brush_type,
            self.canvas.drawing_context.pen_width,
            self.canvas.drawing_context.mirror_x,
            self.canvas.drawing_context.mirror_y,
        )
        painter.end()
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        end_point = doc_pos
        if event.modifiers() & Qt.ShiftModifier:
            dx = end_point.x() - self.start_point.x()
            dy = end_point.y() - self.start_point.y()
            size = min(abs(dx), abs(dy))
            end_point = QPoint(
                self.start_point.x() + size * (1 if dx > 0 else -1),
                self.start_point.y() + size * (1 if dy > 0 else -1),
            )

        rect = QRect(self.start_point, end_point).normalized()

        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        command = ShapeCommand(
            layer=active_layer,
            rect=rect,
            shape_type='rectangle',
            color=self.canvas.drawing_context.pen_color,
            width=self.canvas.drawing_context.pen_width,
            document=self.canvas.document,
            selection_shape=self.canvas.selection_shape,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
        )
        self.command_generated.emit(command)

        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
