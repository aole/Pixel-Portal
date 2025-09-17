from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from portal.tools.basetool import BaseTool


class SelectColorTool(BaseTool):
    name = "Select Color"
    icon = "icons/toolselectcolor.png"
    shortcut = "w"
    category = "select"

    def __init__(self, canvas):
        super().__init__(canvas)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        rendered_image = self.canvas.document.render()
        if not rendered_image.rect().contains(doc_pos):
            return

        target_color = rendered_image.pixelColor(doc_pos)
        path = QPainterPath()

        for x in range(rendered_image.width()):
            for y in range(rendered_image.height()):
                if rendered_image.pixelColor(x, y) == target_color:
                    path.addRect(QRect(x, y, 1, 1))
        new_selection = path.simplified()
        if new_selection.isEmpty():
            new_selection = None
        previous_selection = clone_selection_path(getattr(self.canvas, "selection_shape", None))

        if selection_paths_equal(previous_selection, new_selection):
            self.canvas._update_selection_and_emit_size(
                clone_selection_path(new_selection)
            )
            return

        command = SelectionChangeCommand(
            self.canvas, previous_selection, new_selection
        )
        self.command_generated.emit(command)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass
