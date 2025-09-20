from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.commands.selection_commands import clone_selection_path
from portal.tools.baseselecttool import BaseSelectTool
from portal.tools.color_selection import build_color_selection_path


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
        self._color_pick_point = (
            QPoint(doc_pos) if self._point_within_document(doc_pos) else None
        )
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
                preview = self._preview_selection_path(self._lasso_path)
            else:
                color_path = self._resolve_color_pick_path()
                if color_path is None:
                    color_path = clone_selection_path(self._selection_before_edit)
                preview = self._preview_selection_path(color_path)
            self._emit_preview_selection_changed(preview)
            self._reset_lasso_state()
        super().mouseReleaseEvent(event, doc_pos)

    def _point_within_document(self, point: QPoint) -> bool:
        size = getattr(self.canvas, "_document_size", None)
        if size is None or size.isEmpty():
            return False
        return 0 <= point.x() < size.width() and 0 <= point.y() < size.height()

    def _resolve_color_pick_path(self) -> QPainterPath | None:
        if self._color_pick_point is None:
            return None

        document = getattr(self.canvas, "document", None)
        if document is None:
            return None

        image = document.render()
        return build_color_selection_path(
            image,
            self._color_pick_point,
            contiguous=self._color_pick_contiguous,
        )

    def _reset_lasso_state(self) -> None:
        self._lasso_path = None
        self._lasso_last_point = None
        self._color_pick_point = None
        self._lasso_dragged = False
        self._color_pick_contiguous = True
