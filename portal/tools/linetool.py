from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt

from portal.tools.basetool import BaseTool
from portal.core.command import DrawCommand


class LineTool(BaseTool):
    name = "Line"
    icon = "icons/toolline.png"
    shortcut = "l"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self.canvas.temp_image_replaces_active_layer = True
        self.command_generated.emit(("get_active_layer_image", "line_tool_start"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        painter = QPainter(self.canvas.temp_image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.drawing_context.pen_color))
        self.canvas.drawing.draw_line_with_brush(
            painter,
            self.start_point,
            doc_pos,
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

        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        command = DrawCommand(
            layer=active_layer,
            points=[self.start_point, doc_pos],
            color=self.canvas.drawing_context.pen_color,
            width=self.canvas.drawing_context.pen_width,
            brush_type=self.canvas.drawing_context.brush_type,
            document=self.canvas.document,
            selection_shape=self.canvas.selection_shape,
            erase=False,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
        )
        self.command_generated.emit(command)

        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
