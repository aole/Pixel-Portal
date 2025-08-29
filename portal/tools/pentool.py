from .basetool import BaseTool
from PySide6.QtGui import QPainter, QPen, QImage, QPainterPath, QMouseEvent
from PySide6.QtCore import QPoint, Qt
from ..command import DrawCommand


class PenTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.points = []

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        active_layer = self.app.document.layer_manager.active_layer
        if not active_layer:
            return

        self.points = [doc_pos]

        # Use a transparent temp image for the preview overlay
        self.canvas.temp_image = QImage(self.app.document.width, self.app.document.height, QImage.Format_ARGB32)
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
        if not self.points or not self.app.document.layer_manager.active_layer:
            # Clean up preview and return
            self.points = []
            self.canvas.temp_image = None
            self.canvas.original_image = None
            self.canvas.temp_image_replaces_active_layer = False
            self.canvas.update()
            return

        # Create the command with all the points
        command = DrawCommand(
            layer=self.app.document.layer_manager.active_layer,
            points=self.points,
            color=self.app.pen_color,
            width=self.app.pen_width,
            brush_type=self.app.brush_type,
            drawing=self.canvas.drawing,
        )

        self.app.execute_command(command)

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
        
        # Set the pen for the live preview
        painter.setPen(QPen(self.app.pen_color))
        
        # Use the drawing class to handle mirroring and brush styles
        if len(self.points) == 1:
            self.canvas.drawing.draw_brush(painter, self.points[0])
        else:
            for i in range(len(self.points) - 1):
                self.canvas.drawing.draw_line_with_brush(painter, self.points[i], self.points[i+1], erase=False)

        painter.end()
        