from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QImage, QPainterPath

from portal.tools.basetool import BaseTool
from ..command import DrawCommand


class EraserTool(BaseTool):
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
            color=self.app.pen_color, # Color is needed for the pen, but will be ignored by the composition mode
            width=self.app.pen_width,
            brush_type=self.app.brush_type,
            erase=True
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

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        pen = QPen()
        pen.setColor(Qt.black) # Color doesn't matter for clearing
        pen.setWidth(self.app.pen_width)

        if self.app.brush_type == "Circular":
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        else:
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Draw the path from the collected points
        if len(self.points) == 1:
            painter.drawPoint(self.points[0])
        else:
            path = QPainterPath(self.points[0])
            for i in range(1, len(self.points)):
                path.lineTo(self.points[i])
            painter.drawPath(path)

        painter.end()