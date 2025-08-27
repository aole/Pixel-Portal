from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, QPainterPathStroker, Qt
from portal.tools.basetool import BaseTool


class BaseSelectTool(BaseTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.moving_selection = False
        self.selection_move_start_point = QPoint()

    def is_on_selection_border(self, doc_pos):
        if self.canvas.selection_shape is None:
            return False

        stroker = QPainterPathStroker()
        stroker.setWidth(10 / self.canvas.zoom)  # 10 pixel wide border for selection
        border = stroker.createStroke(self.canvas.selection_shape)
        return border.contains(doc_pos)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.is_on_selection_border(doc_pos):
            self.moving_selection = True
            self.selection_move_start_point = doc_pos
        else:
            super().mousePressEvent(event, doc_pos)

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if self.is_on_selection_border(doc_pos):
            self.canvas.setCursor(Qt.ArrowCursor)
        else:
            self.canvas.setCursor(Qt.CrossCursor)

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
        else:
            super().mouseReleaseEvent(event, doc_pos)
