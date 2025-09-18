from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt, QImage

from portal.tools.basetool import BaseTool
from portal.core.command import DrawCommand


class LineTool(BaseTool):
    name = "Line"
    icon = "icons/toolline.png"
    shortcut = "l"
    category = "shape"
    supports_auto_key = True

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self._allocate_preview_images(replace_active_layer=True, allocate_temp=False)
        self.command_generated.emit(("get_active_layer_image", "line_tool_start"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        self._refresh_preview_images(clear_temp=False)
        self._paint_preview_line(
            self.canvas.temp_image,
            wrap=self.canvas.tile_preview_enabled,
            start=self.start_point,
            end=doc_pos,
        )

        tile_preview = self.canvas.tile_preview_image
        if tile_preview is not None:
            self._paint_preview_line(
                tile_preview,
                wrap=True,
                start=self.start_point,
                end=doc_pos,
            )
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            self._clear_preview_images()
            self.canvas.update()
            return

        active_layer = layer_manager.active_layer
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
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
            wrap=self.canvas.tile_preview_enabled,
            pattern_image=self.canvas.drawing_context.pattern_brush,
        )
        self.command_generated.emit(command)

        self._clear_preview_images()
        self.canvas.update()

    def _paint_preview_line(
        self,
        image: QImage,
        *,
        wrap: bool,
        start: QPoint,
        end: QPoint,
    ):
        painter = QPainter(image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.drawing_context.pen_color))
        self.canvas.drawing.draw_line_with_brush(
            painter,
            start,
            end,
            self.canvas._document_size,
            self.canvas.drawing_context.brush_type,
            self.canvas.drawing_context.pen_width,
            self.canvas.drawing_context.mirror_x,
            self.canvas.drawing_context.mirror_y,
            wrap=wrap,
            pattern=self.canvas.drawing_context.pattern_brush,
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
        )
        painter.end()
