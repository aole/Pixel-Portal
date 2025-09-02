from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QImage, QPainterPath, QCursor

from portal.tools.basetool import BaseTool
from portal.core.command import DrawCommand


class EraserTool(BaseTool):
    name = "Eraser"
    icon = "icons/brush.png"
    shortcut = "e"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.points = []
        self.cursor = QCursor(Qt.BlankCursor)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.canvas.is_erasing_preview = True
        self.points = [doc_pos]

        # Use a transparent temp image for the preview overlay
        self.canvas.temp_image = QImage(self.canvas._document_size, QImage.Format_ARGB32)
        self.canvas.temp_image.fill(Qt.transparent)

        # This flag tells the renderer to draw our temp_image ON TOP of the document, not instead of it.
        self.canvas.temp_image_replaces_active_layer = False

        self.draw_path_on_temp_image()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.points:
            return

        self.points.append(doc_pos)
        self.draw_path_on_temp_image()
        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.canvas.is_erasing_preview = False
        if not self.points:
            # Clean up preview and return
            self.points = []
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
            self.canvas.update()
            return

        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            # Clean up preview and return
            self.points = []
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
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
        )
        self.command_generated.emit(command)

        # Clean up preview
        self.points = []
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()

    def draw_path_on_temp_image(self):
        if not self.points or self.canvas.temp_image is None:
            return

        # Clear the temp image before redrawing the path
        self.canvas.temp_image.fill(Qt.transparent)

        painter = QPainter(self.canvas.temp_image)

        # Handle selection mask
        if self.canvas.selection_shape:
            painter.setClipPath(self.canvas.selection_shape)

        # The mask can be any opaque color.
        painter.setPen(QPen(Qt.black))

        # Use the normal drawing function to create an opaque mask on the temp image.
        # The renderer will then use this mask to "erase" from the main preview.
        if len(self.points) == 1:
            self.canvas.drawing.draw_brush(
                painter,
                self.points[0],
                self.canvas._document_size,
                self.canvas.drawing_context.brush_type,
                self.canvas.drawing_context.pen_width,
                self.canvas.drawing_context.mirror_x,
                self.canvas.drawing_context.mirror_y,
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
                    erase=False
                )

        painter.end()
        