from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.baseselecttool import BaseSelectTool


class SelectLassoTool(BaseSelectTool):
    name = "Select Lasso"
    icon = "icons/toolselectlasso.png"
    shortcut = "f"
    category = "select"

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        super().mousePressEvent(event, doc_pos)
        if self.moving_selection:
            return
        clamped_pos = self._clamp_to_document(doc_pos)
        self.canvas._update_selection_and_emit_size(QPainterPath(clamped_pos))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape:
                clamped_pos = self._clamp_to_document(
                    doc_pos, extend_max=True
                )
                self.canvas.selection_shape.lineTo(clamped_pos)
                self.canvas._update_selection_and_emit_size(self.canvas.selection_shape)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape:
                self.canvas.selection_shape.closeSubpath()
                if self.canvas.selection_shape.isEmpty():
                    self.canvas.selection_shape = None
            self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
        super().mouseReleaseEvent(event, doc_pos)
