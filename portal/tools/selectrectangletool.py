from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.baseselecttool import BaseSelectTool


class SelectRectangleTool(BaseSelectTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.is_on_selection_border(doc_pos):
            self.start_point = doc_pos
            self.canvas._update_selection_and_emit_size(QPainterPath(self.start_point))
        super().mousePressEvent(event, doc_pos)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            qpp = QPainterPath()
            qpp.addRect(QRect(self.start_point, doc_pos).normalized())
            self.canvas._update_selection_and_emit_size(qpp)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape and self.canvas.selection_shape.isEmpty():
                self.canvas.selection_shape = None
            self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
        super().mouseReleaseEvent(event, doc_pos)
