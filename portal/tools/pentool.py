from portal.tools.basetool import BaseTool
from PySide6.QtGui import QPainter, QPen, QImage, QPainterPath, QMouseEvent, QKeySequence, QCursor
from PySide6.QtCore import QPoint, Qt
from portal.core.command import DrawCommand


class PenTool(BaseTool):
    name = "Pen"
    icon = "icons/toolpen.png"
    shortcut = "b"
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

        # Use a transparent temp image for the preview overlay
        self.canvas.temp_image = QImage(self.canvas._document_size, QImage.Format_ARGB32)
        self.canvas.temp_image.fill(Qt.transparent)

        if self.canvas.tile_preview_enabled:
            self.canvas.tile_preview_image = QImage(self.canvas._document_size, QImage.Format_ARGB32)
            self.canvas.tile_preview_image.fill(Qt.transparent)
        else:
            self.canvas.tile_preview_image = None

        # This flag tells the renderer to draw our temp_image ON TOP of the document, not instead of it.
        self.canvas.temp_image_replaces_active_layer = False

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
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
            self.canvas.tile_preview_image = None
            self.canvas.update()
            return

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            # Clean up preview and return
            self.points = []
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
            self.canvas.tile_preview_image = None
            self.canvas.update()
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            # Clean up preview and return
            self.points = []
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
            self.canvas.tile_preview_image = None
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
            erase=False,
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
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.tile_preview_image = None
        self.canvas.update()

    def draw_path_on_temp_image(self):
        if not self.points or self.canvas.temp_image is None:
            return

        # Clear the temp image before redrawing the path
        self.canvas.temp_image.fill(Qt.transparent)
        if self.canvas.tile_preview_enabled and self.canvas.tile_preview_image is not None:
            self.canvas.tile_preview_image.fill(Qt.transparent)

        painter = QPainter(self.canvas.temp_image)

        # Handle selection mask
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)
        
        # Set the pen for the live preview
        painter.setPen(QPen(self.canvas.drawing_context.pen_color))
        
        # Use the drawing class to handle mirroring and brush styles
        if len(self.points) == 1:
            self.canvas.drawing.draw_brush(
                painter,
                self.points[0],
                self.canvas._document_size,
                self.canvas.drawing_context.brush_type,
                self.canvas.drawing_context.pen_width,
                self.canvas.drawing_context.mirror_x,
                self.canvas.drawing_context.mirror_y,
                wrap=self.canvas.tile_preview_enabled,
                pattern=self.canvas.drawing_context.pattern_brush,
                mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                mirror_y_position=self.canvas.drawing_context.mirror_y_position,
            )
        else:
            for i in range(len(self.points) - 1):
                self.canvas.drawing.draw_line_with_brush(
                    painter,
                    self.points[i],
                    self.points[i+1],
                    self.canvas._document_size,
                    self.canvas.drawing_context.brush_type,
                    self.canvas.drawing_context.pen_width,
                    self.canvas.drawing_context.mirror_x,
                    self.canvas.drawing_context.mirror_y,
                    wrap=self.canvas.tile_preview_enabled,
                    erase=False,
                    pattern=self.canvas.drawing_context.pattern_brush,
                    mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                    mirror_y_position=self.canvas.drawing_context.mirror_y_position,
                )

        painter.end()

        if self.canvas.tile_preview_enabled and self.canvas.tile_preview_image is not None:
            preview_painter = QPainter(self.canvas.tile_preview_image)
            if self.canvas.selection_shape:
                preview_painter.setClipPath(self.canvas.selection_shape)
            preview_painter.setPen(QPen(self.canvas.drawing_context.pen_color))
            if len(self.points) == 1:
                self.canvas.drawing.draw_brush(
                    preview_painter,
                    self.points[0],
                    self.canvas._document_size,
                    self.canvas.drawing_context.brush_type,
                    self.canvas.drawing_context.pen_width,
                    self.canvas.drawing_context.mirror_x,
                    self.canvas.drawing_context.mirror_y,
                    wrap=True,
                    pattern=self.canvas.drawing_context.pattern_brush,
                    mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                    mirror_y_position=self.canvas.drawing_context.mirror_y_position,
                )
            else:
                for i in range(len(self.points) - 1):
                    self.canvas.drawing.draw_line_with_brush(
                        preview_painter,
                        self.points[i],
                        self.points[i + 1],
                        self.canvas._document_size,
                        self.canvas.drawing_context.brush_type,
                        self.canvas.drawing_context.pen_width,
                        self.canvas.drawing_context.mirror_x,
                        self.canvas.drawing_context.mirror_y,
                        wrap=True,
                        erase=False,
                        pattern=self.canvas.drawing_context.pattern_brush,
                        mirror_x_position=self.canvas.drawing_context.mirror_x_position,
                        mirror_y_position=self.canvas.drawing_context.mirror_y_position,
                    )
            preview_painter.end()
        
