from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.baseselecttool import BaseSelectTool


class SelectLassoTool(BaseSelectTool):
    name = "Select Lasso"
    icon = "icons/toolselectlasso.png"
    shortcut = "f"

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.is_on_selection_border(doc_pos):
            self.canvas._update_selection_and_emit_size(QPainterPath(doc_pos))
        super().mousePressEvent(event, doc_pos)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape:
                self.canvas.selection_shape.lineTo(doc_pos)
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
