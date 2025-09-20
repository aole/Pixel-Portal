from collections import deque

from PySide6.QtCore import QPoint, QRect, Qt
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

        contiguous = not bool(event.modifiers() & Qt.ControlModifier)
        new_selection = self._build_selection_path(
            rendered_image, doc_pos, contiguous=contiguous
        )
        previous_selection = clone_selection_path(getattr(self.canvas, "selection_shape", None))

        if selection_paths_equal(previous_selection, new_selection):
            self.canvas._update_selection_and_emit_size(
                clone_selection_path(new_selection)
            )
            return

        command = SelectionChangeCommand(
            self.canvas, previous_selection, new_selection
        )
        self.canvas._update_selection_and_emit_size(
            clone_selection_path(new_selection)
        )
        self.command_generated.emit(command)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def _build_selection_path(
        self, image, point: QPoint, *, contiguous: bool
    ) -> QPainterPath | None:
        if image is None or image.isNull():
            return None
        if not image.rect().contains(point):
            return None

        target_x = int(point.x())
        target_y = int(point.y())
        target_rgba = int(image.pixel(target_x, target_y))

        path = QPainterPath()

        if contiguous:
            width = image.width()
            height = image.height()
            queue: deque[tuple[int, int]] = deque()
            queue.append((target_x, target_y))
            visited: set[tuple[int, int]] = set()
            while queue:
                x, y = queue.popleft()
                if (x, y) in visited:
                    continue
                visited.add((x, y))
                if int(image.pixel(x, y)) != target_rgba:
                    continue
                path.addRect(QRect(x, y, 1, 1))
                if x > 0:
                    queue.append((x - 1, y))
                if x + 1 < width:
                    queue.append((x + 1, y))
                if y > 0:
                    queue.append((x, y - 1))
                if y + 1 < height:
                    queue.append((x, y + 1))
        else:
            for x in range(image.width()):
                for y in range(image.height()):
                    if int(image.pixel(x, y)) == target_rgba:
                        path.addRect(QRect(x, y, 1, 1))

        simplified = path.simplified()
        if simplified.isEmpty():
            return None
        return simplified
