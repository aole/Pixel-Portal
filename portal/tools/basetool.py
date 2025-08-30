from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QCursor


class BaseTool:
    """Abstract base class for all drawing tools."""

    name = None
    icon = None
    shortcut = None

    def __init__(self, canvas):
        self.canvas = canvas
        self.app = canvas.app
        self.cursor = QCursor(Qt.CrossCursor)

    def mousePressEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseMoveEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseReleaseEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def mouseHoverEvent(self, event: QMouseEvent, doc_pos: QPoint):
        pass

    def activate(self):
        """Called when the tool becomes active."""
        pass

    def deactivate(self):
        """Called when the tool is switched."""
        pass
