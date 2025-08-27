from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QMouseEvent

class BaseTool:
    """Abstract base class for all drawing tools."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.app = canvas.app

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def activate(self):
        """Called when the tool becomes active."""
        pass

    def deactivate(self):
        """Called when the tool is switched."""
        pass