from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainterPath, Qt

from portal.tools.baseselecttool import BaseSelectTool


class SelectCircleTool(BaseSelectTool):
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
            end_point = doc_pos
            if event.modifiers() & Qt.ShiftModifier:
                dx = end_point.x() - self.start_point.x()
                dy = end_point.y() - self.start_point.y()
                size = max(abs(dx), abs(dy))
                end_point = QPoint(
                    self.start_point.x() + size * (1 if dx > 0 else -1),
                    self.start_point.y() + size * (1 if dy > 0 else -1),
                )

            qpp = QPainterPath()
            qpp.addEllipse(QRect(self.start_point, end_point).normalized())
            self.canvas._update_selection_and_emit_size(qpp)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape and self.canvas.selection_shape.isEmpty():
                self.canvas.selection_shape = None
            self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
        super().mouseReleaseEvent(event, doc_pos)
