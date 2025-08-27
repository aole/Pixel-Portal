from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainterPath

from portal.tools.basetool import BaseTool


class SelectCircleTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        self.start_point = doc_pos
        self.canvas._update_selection_and_emit_size(QPainterPath(self.start_point))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        qpp = QPainterPath()
        qpp.addEllipse(QRect(self.start_point, doc_pos).normalized())
        self.canvas._update_selection_and_emit_size(qpp)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.canvas.selection_shape and self.canvas.selection_shape.isEmpty():
            self.canvas.selection_shape = None
        self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
