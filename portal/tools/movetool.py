from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QImage, QPainter, Qt, QPainterPath, QCursor

from portal.tools.basetool import BaseTool
from portal.core.command import MoveCommand


class MoveTool(BaseTool):
    name = "Move"
    icon = "icons/toolmove.png"
    shortcut = "m"
    category = "draw"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()
        self.moving_selection = False
        self.original_selection_shape: QPainterPath | None = None
        self.before_image = None
        self.cursor = QCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self.canvas.temp_image_replaces_active_layer = False

        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return
        self.before_image = active_layer.image.copy()

        if self.canvas.selection_shape:
            self.moving_selection = True
            self.original_selection_shape = self.canvas.selection_shape
            self.command_generated.emit(("cut_selection", "move_tool_start"))
        else:
            self.command_generated.emit(("cut_selection", "move_tool_start_no_selection"))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None:
            return

        delta = doc_pos - self.start_point
        self.canvas.temp_image.fill(Qt.transparent)
        painter = QPainter(self.canvas.temp_image)
        painter.drawImage(delta, self.canvas.original_image)
        painter.end()

        if self.moving_selection:
            self.canvas.selection_shape = self.original_selection_shape.translated(delta.x(), delta.y())

        self.canvas.update()

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.original_image is None or self.before_image is None:
            return

        delta = doc_pos - self.start_point

        active_layer = self.canvas.document.layer_manager.active_layer
        if not active_layer:
            return

        command = MoveCommand(
            layer=active_layer,
            before_move_image=self.before_image,
            after_cut_image=active_layer.image.copy(),
            moved_image=self.canvas.original_image,
            delta=delta,
            original_selection_shape=self.original_selection_shape,
        )
        self.command_generated.emit(command)

        if self.moving_selection:
            self.moving_selection = False
            self.original_selection_shape = None

        self.before_image = None
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
        