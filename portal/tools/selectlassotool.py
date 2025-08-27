from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.basetool import BaseTool


class SelectLassoTool(BaseTool):
    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.canvas._update_selection_and_emit_size(QPainterPath(doc_pos))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.selection_shape:
            self.canvas.selection_shape.lineTo(doc_pos)
            self.canvas._update_selection_and_emit_size(self.canvas.selection_shape)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.selection_shape:
            self.canvas.selection_shape.closeSubpath()
            if self.canvas.selection_shape.isEmpty():
                self.canvas.selection_shape = None
        self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
