from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QImage, QPainterPath, QCursor

from portal.tools.basetool import BaseTool
from portal.core.command import DrawCommand


class EraserTool(BaseTool):
    name = "Eraser"
    icon = "icons/tooleraser.png"
    shortcut = "e"
    category = "draw"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.points = []
        self.cursor = QCursor(Qt.BlankCursor)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer or not active_layer.visible:
            return

        self.points = [doc_pos]

        self._allocate_preview_images(
            replace_active_layer=False,
            allocate_temp=True,
            erase_preview=True,
        )

        self.draw_path_on_temp_image()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.points:
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer or not active_layer.visible:
            return

        self.points.append(doc_pos)
        self.draw_path_on_temp_image()
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.canvas.is_erasing_preview = False
        if not self.points:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            return

        command = DrawCommand(
            layer=active_layer,
            points=self.points,
            color=self.canvas.drawing_context.pen_color,
            width=self.canvas.drawing_context.pen_width,
            brush_type=self.canvas.drawing_context.brush_type,
            document=self.canvas.document,
            selection_shape=self.canvas.selection_shape,
            erase=True,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
            wrap=self.canvas.tile_preview_enabled,
        )
        self.command_generated.emit(command)

        # Clean up preview
        self.points = []
        self._clear_preview_images()
        self.canvas.update()

    def draw_path_on_temp_image(self):
        if not self.points or self.canvas.temp_image is None:
            return

        self._refresh_preview_images()

        self._paint_preview_path(self.canvas.temp_image, wrap=self.canvas.tile_preview_enabled)

        tile_preview = self.canvas.tile_preview_image
        if tile_preview is not None:
            self._paint_preview_path(tile_preview, wrap=True)

    def _paint_preview_path(self, image: QImage, *, wrap: bool):
        painter = QPainter(image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)

        painter.setPen(QPen(Qt.black))

        if len(self.points) == 1:
            self.canvas.drawing.draw_brush(
                painter,
                self.points[0],
                self.canvas._document_size,
                self.canvas.drawing_context.brush_type,
                self.canvas.drawing_context.pen_width,
                self.canvas.drawing_context.mirror_x,
                self.canvas.drawing_context.mirror_y,
                wrap=wrap,
                mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                mirror_y_position=self.canvas.drawing_context.mirror_y_position,
            )
        else:
            for start, end in zip(self.points, self.points[1:]):
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
                    erase=False,
                    mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                    mirror_y_position=self.canvas.drawing_context.mirror_y_position,
                )

        painter.end()
