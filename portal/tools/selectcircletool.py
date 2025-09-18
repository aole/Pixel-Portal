from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QMouseEvent, QPainterPath, Qt

from portal.tools.baseselecttool import BaseSelectTool


class SelectCircleTool(BaseSelectTool):
    name = "Select Circle"
    icon = "icons/toolselectcircle.png"
    shortcut = "a"
    category = "select"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = QPoint()

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        super().mousePressEvent(event, doc_pos)
        if self.moving_selection:
            return
        clamped_start = self._clamp_to_document(doc_pos)
        self.start_point = clamped_start
        self._preview_selection_path(QPainterPath(clamped_start))

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            end_point = self._clamp_to_document(
                doc_pos, extend_min=True, extend_max=True
            )
            if event.modifiers() & Qt.ShiftModifier:
                dx = end_point.x() - self.start_point.x()
                dy = end_point.y() - self.start_point.y()
                size = min(abs(dx), abs(dy))
                end_point = QPoint(
                    self.start_point.x() + size * (1 if dx > 0 else -1),
                    self.start_point.y() + size * (1 if dy > 0 else -1),
                )

            end_point = self._clamp_to_document(
                end_point, extend_min=True, extend_max=True
            )

            qpp = QPainterPath()
            rect = self._rect_from_points(self.start_point, end_point)
            size = getattr(self.canvas, "_document_size", None)
            if size is not None and not size.isEmpty():
                doc_rect = QRect(0, 0, size.width(), size.height())
                rect = rect.intersected(doc_rect)
            qpp.addEllipse(rect)
            self._preview_selection_path(qpp)
        super().mouseMoveEvent(event, doc_pos)

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        if not self.moving_selection:
            if self.canvas.selection_shape and self.canvas.selection_shape.isEmpty():
                self.canvas.selection_shape = None
            self.canvas.selection_changed.emit(self.canvas.selection_shape is not None)
        super().mouseReleaseEvent(event, doc_pos)
