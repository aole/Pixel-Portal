from collections import deque

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.commands.selection_commands import clone_selection_path

from portal.tools.baseselecttool import BaseSelectTool


class SelectLassoTool(BaseSelectTool):
    name = "Select Lasso"
    icon = "icons/toolselectlasso.png"
    shortcut = "f"
    category = "select"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._lasso_path: QPainterPath | None = None
        self._lasso_last_point: QPoint | None = None
        self._lasso_dragged = False
        self._color_pick_point: QPoint | None = None
        self._color_pick_contiguous = True

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        super().mousePressEvent(event, doc_pos)
        if self.moving_selection:
            return
        self._lasso_dragged = False
        self._color_pick_point = doc_pos if self._point_within_document(doc_pos) else None
        self._color_pick_contiguous = not bool(event.modifiers() & Qt.ControlModifier)
        clamped_pos = self._clamp_to_document(doc_pos)
        self._lasso_last_point = clamped_pos
        self._lasso_path = QPainterPath(clamped_pos)
        self._preview_selection_path(self._lasso_path)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection and self._lasso_path is not None:
            clamped_pos = self._clamp_to_document(doc_pos, extend_max=True)
            if self._lasso_last_point is None or clamped_pos != self._lasso_last_point:
                self._lasso_dragged = True
                self._lasso_path.lineTo(clamped_pos)
                self._lasso_last_point = clamped_pos
                self._preview_selection_path(self._lasso_path)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection and self._lasso_path is not None:
            if self._lasso_dragged:
                self._lasso_path.closeSubpath()
                self._preview_selection_path(self._lasso_path)
                combined = self._build_preview_path()
                has_selection = combined is not None and not combined.isEmpty()
                self.canvas.selection_changed.emit(has_selection)
            else:
                if self._color_pick_point is not None:
                    color_path = self._build_color_selection_path(
                        self._color_pick_point, contiguous=self._color_pick_contiguous
                    )
                else:
                    color_path = None
                if color_path is None:
                    color_path = clone_selection_path(self._selection_before_edit)
                self._preview_selection_path(color_path)
                combined = self._build_preview_path()
                has_selection = combined is not None and not combined.isEmpty()
                self.canvas.selection_changed.emit(has_selection)
            self._lasso_path = None
            self._lasso_last_point = None
            self._color_pick_point = None
            self._lasso_dragged = False
        super().mouseReleaseEvent(event, doc_pos)

    def _point_within_document(self, point: QPoint) -> bool:
        size = getattr(self.canvas, "_document_size", None)
        if size is None or size.isEmpty():
            return False
        return 0 <= point.x() < size.width() and 0 <= point.y() < size.height()

    def _build_color_selection_path(
        self, point: QPoint, *, contiguous: bool
    ) -> QPainterPath | None:
        document = getattr(self.canvas, "document", None)
        if document is None:
            return None

        image = document.render()
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
