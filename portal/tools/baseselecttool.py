from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPathStroker, Qt

from portal.commands.selection_commands import (
    SelectionChangeCommand,
    clone_selection_path,
    selection_paths_equal,
)
from portal.tools.basetool import BaseTool


class BaseSelectTool(BaseTool):
    category = "select"
    def __init__(self, canvas):
        super().__init__(canvas)
        self.moving_selection = False
        self.selection_move_start_point = QPoint()
        self._selection_before_edit = None
        if not hasattr(self.canvas, "selection_shape"):
            self.canvas.selection_shape = None

    def is_on_selection_border(self, doc_pos):
        if self.canvas.selection_shape is None:
            return False

        stroker = QPainterPathStroker()
        stroker.setWidth(10 / self.canvas.zoom)  # 10 pixel wide border for selection
        border = stroker.createStroke(self.canvas.selection_shape)
        return border.contains(doc_pos)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self._selection_before_edit = clone_selection_path(
            getattr(self.canvas, "selection_shape", None)
        )
        if self.is_on_selection_border(doc_pos):
            self.moving_selection = True
            self.selection_move_start_point = doc_pos
        else:
            self.moving_selection = False

    def mouseHoverEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.is_on_selection_border(doc_pos):
            self.canvas.setCursor(Qt.ArrowCursor)
        else:
            self.canvas.setCursor(Qt.CrossCursor)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.moving_selection:
            delta = doc_pos - self.selection_move_start_point
            self.canvas.selection_shape.translate(delta)
            self.selection_move_start_point = doc_pos
            self.canvas.update()
        else:
            super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.moving_selection:
            self.moving_selection = False
            if not self.is_on_selection_border(doc_pos):
                self.canvas.setCursor(Qt.CrossCursor)
        else:
            super().mouseReleaseEvent(event, doc_pos)
        self._finalize_selection_change()

    def _clamp_to_document(
        self,
        point: QPoint,
        *,
        extend_min: bool = False,
        extend_max: bool = False,
    ) -> QPoint:
        """Clamp *point* to the document bounds.

        When ``extend_min`` or ``extend_max`` are ``True`` the method allows
        callers to stretch a point by one pixel beyond the document edges.
        This mirrors the behaviour the selection tools relied on prior to the
        clamping change: rectangle and ellipse selections need to reach ``-1``
        to include the first row/column after normalization, while free-form
        selections need access to ``width``/``height`` to cover the last
        column/row.
        """

        size = getattr(self.canvas, "_document_size", None)
        if size is None or size.isEmpty():
            return QPoint(point)

        min_x = -1 if extend_min and size.width() > 0 else 0
        min_y = -1 if extend_min and size.height() > 0 else 0
        max_x = size.width() if extend_max and size.width() > 0 else max(
            size.width() - 1, 0
        )
        max_y = size.height() if extend_max and size.height() > 0 else max(
            size.height() - 1, 0
        )

        clamped_x = min(max(point.x(), min_x), max_x)
        clamped_y = min(max(point.y(), min_y), max_y)
        return QPoint(clamped_x, clamped_y)

    def _finalize_selection_change(self):
        new_selection = clone_selection_path(getattr(self.canvas, "selection_shape", None))
        previous_selection = clone_selection_path(self._selection_before_edit)
        self._selection_before_edit = None
        if selection_paths_equal(previous_selection, new_selection):
            return
        command = SelectionChangeCommand(self.canvas, previous_selection, new_selection)
        self.command_generated.emit(command)
