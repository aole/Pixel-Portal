from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.baseselecttool import BaseSelectTool


class SelectLassoTool(BaseSelectTool):
    name = "Select Lasso"
    icon = "icons/toolselectlasso.png"
    shortcut = "f"
    category = "select"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._lasso_path: QPainterPath | None = None

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        super().mousePressEvent(event, doc_pos)
        if self.moving_selection:
            return
        clamped_pos = self._clamp_to_document(doc_pos)
        self._lasso_path = QPainterPath(clamped_pos)
        self._preview_selection_path(self._lasso_path)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection and self._lasso_path is not None:
            clamped_pos = self._clamp_to_document(doc_pos, extend_max=True)
            self._lasso_path.lineTo(clamped_pos)
            self._preview_selection_path(self._lasso_path)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection and self._lasso_path is not None:
            self._lasso_path.closeSubpath()
            self._preview_selection_path(self._lasso_path)
            if self.canvas.selection_shape and self.canvas.selection_shape.isEmpty():
                self.canvas.selection_shape = None
            self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
            self._lasso_path = None
        super().mouseReleaseEvent(event, doc_pos)
