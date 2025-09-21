from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent

from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from portal.tools.basetool import BaseTool
from portal.tools.color_selection import build_color_selection_path


class SelectColorTool(BaseTool):
    name = "Select Color"
    icon = "icons/toolselectcolor.png"
    shortcut = "v"
    category = "select"

    def __init__(self, canvas):
        super().__init__(canvas)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return

        image = document.render()

        contiguous = not bool(event.modifiers() & Qt.ControlModifier)
        new_selection = build_color_selection_path(
            image, doc_pos, contiguous=contiguous
        )
        previous_selection = clone_selection_path(getattr(self.canvas, "selection_shape", None))
        next_selection = clone_selection_path(new_selection)

        if selection_paths_equal(previous_selection, new_selection):
            self.canvas._update_selection_and_emit_size(
                next_selection
            )
            return

        command = SelectionChangeCommand(
            self.canvas, previous_selection, new_selection
        )
        self.canvas._update_selection_and_emit_size(
            next_selection
        )
        self.command_generated.emit(command)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass
