from portal.tools.basetool import BaseTool
from PySide6.QtGui import QPainter, QPen, QImage, QPainterPath, QMouseEvent, QKeySequence, QCursor
from PySide6.QtCore import QPoint, Qt
from portal.core.command import DrawCommand


class PenTool(BaseTool):
    name = "Pen"
    icon = "icons/toolpen.png"
    shortcut = "b"
    category = "draw"
    supports_right_click_erase = True

    def __init__(self, canvas):
        super().__init__(canvas)
        self.points = []
        self.cursor = QCursor(Qt.BlankCursor)
        self._is_erasing = False

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if event.button() not in (Qt.LeftButton, Qt.RightButton):
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer or not active_layer.visible:
            return

        self._is_erasing = event.button() == Qt.RightButton
        self.points = [doc_pos]

        # Prepare transparent overlays for the live preview.
        self._allocate_preview_images(
            replace_active_layer=False,
            allocate_temp=True,
            erase_preview=self._is_erasing,
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
        if not self.points:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            self._is_erasing = False
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            self._is_erasing = False
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            # Clean up preview and return
            self.points = []
            self._clear_preview_images()
            self.canvas.update()
            self._is_erasing = False
            return

        command = DrawCommand(
            layer=active_layer,
            points=self.points,
            color=self.canvas.drawing_context.pen_color,
            width=self.canvas.drawing_context.pen_width,
            brush_type=self.canvas.drawing_context.brush_type,
            document=self.canvas.document,
            selection_shape=self.canvas.selection_shape,
            erase=self._is_erasing,
            mirror_x=self.canvas.drawing_context.mirror_x,
            mirror_y=self.canvas.drawing_context.mirror_y,
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
            wrap=self.canvas.tile_preview_enabled,
            pattern_image=self.canvas.drawing_context.pattern_brush,
        )
        self.command_generated.emit(command)

        # Clean up preview
        self.points = []
        self._clear_preview_images()
        self.canvas.update()
        self._is_erasing = False

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
        pen_color = Qt.black if self._is_erasing else self.canvas.drawing_context.pen_color
        painter.setPen(QPen(pen_color))

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
                pattern=self.canvas.drawing_context.pattern_brush,
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
                    pattern=self.canvas.drawing_context.pattern_brush,
                    mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                    mirror_y_position=self.canvas.drawing_context.mirror_y_position,
                )
        painter.end()

