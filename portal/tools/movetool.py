from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QImage, QPainter, Qt, QPainterPath, QCursor

from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from portal.tools.basetool import BaseTool
from portal.core.command import CompositeCommand, MoveCommand


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

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            return
        self.before_image = active_layer.image.copy()

        if self.canvas.selection_shape:
            self.moving_selection = True
            self.original_selection_shape = QPainterPath(self.canvas.selection_shape)
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

        layer_manager = self._get_active_layer_manager()
        if layer_manager is None:
            return

        active_layer = layer_manager.active_layer
        if not active_layer:
            return

        move_command = MoveCommand(
            layer=active_layer,
            before_move_image=self.before_image,
            after_cut_image=active_layer.image.copy(),
            moved_image=self.canvas.original_image,
            delta=delta,
            original_selection_shape=self.original_selection_shape,
        )
        command_to_emit: MoveCommand | CompositeCommand = move_command
        if self.moving_selection and self.original_selection_shape is not None:
            final_selection = getattr(self.canvas, "selection_shape", None)
            previous_selection = clone_selection_path(self.original_selection_shape)
            current_selection = clone_selection_path(final_selection)
            if not selection_paths_equal(previous_selection, current_selection):
                selection_command = SelectionChangeCommand(
                    self.canvas,
                    previous_selection,
                    current_selection,
                )
                command_to_emit = CompositeCommand(
                    [move_command, selection_command], name="Move Selection"
                )

        self.command_generated.emit(command_to_emit)

        if self.moving_selection:
            self.moving_selection = False
            self.original_selection_shape = None

        self.before_image = None
        self.canvas.temp_image = None
        self.canvas.original_image = None
        self.canvas.temp_image_replaces_active_layer = False
        self.canvas.update()
        