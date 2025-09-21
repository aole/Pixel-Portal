from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QPen, Qt, QCursor, QImage

from portal.tools.basetool import BaseTool
from portal.core.command import ShapeCommand


class RectangleTool(BaseTool):
    name = "Rectangle"
    icon = "icons/toolrect.png"
    shortcut = "s"
    category = "shape"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.cursor = QCursor(Qt.BlankCursor)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer or not active_layer.visible:
            return

        self.start_point = doc_pos
        self._allocate_preview_images(replace_active_layer=True, allocate_temp=False)
        self.command_generated.emit(("get_active_layer_image", "rectangle_tool_start"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer or not active_layer.visible:
            return

        self.canvas.temp_image = self.canvas.original_image.copy()
        self._refresh_preview_images(clear_temp=False)

        end_point = doc_pos
        if event.modifiers() & Qt.ShiftModifier:
            dx = end_point.x() - self.start_point.x()
            dy = end_point.y() - self.start_point.y()
            size = min(abs(dx), abs(dy))
            end_point = QPoint(
                self.start_point.x() + size * (1 if dx > 0 else -1),
                self.start_point.y() + size * (1 if dy > 0 else -1),
            )

        rect = self._rect_from_points(self.start_point, end_point)
        self._paint_preview_rect(
            self.canvas.temp_image,
            rect=rect,
            wrap=self.canvas.tile_preview_enabled,
        )

        tile_preview = self.canvas.tile_preview_image
        if tile_preview is not None:
            self._paint_preview_rect(tile_preview, rect=rect, wrap=True)
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

        rect = self._rect_from_points(self.start_point, end_point)

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            self._clear_preview_images()
            self.canvas.update()
            return

        active_layer = layer_manager.active_layer
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
            wrap=self.canvas.tile_preview_enabled,
            brush_type=self.canvas.drawing_context.brush_type,
            pattern_image=self.canvas.drawing_context.pattern_brush,
            mirror_x_position=self.canvas.drawing_context.mirror_x_position,
            mirror_y_position=self.canvas.drawing_context.mirror_y_position,
        )
        self.command_generated.emit(command)

        self._clear_preview_images()
        self.canvas.update()

    def _paint_preview_rect(self, image: QImage, *, rect: QRect, wrap: bool):
        painter = QPainter(image)
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        painter.setPen(QPen(self.canvas.drawing_context.pen_color))
        self.canvas.drawing.draw_rect(
            painter,
            rect,
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
