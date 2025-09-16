from PySide6.QtCore import QPoint, Qt, QObject, Signal
from PySide6.QtGui import QMouseEvent, QCursor

from portal.core.frame_manager import resolve_active_layer_manager


class BaseTool(QObject):
    """Abstract base class for all drawing tools."""

    name = None
    icon = None
    shortcut = None
    category = None
    command_generated = Signal(object)

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.cursor = QCursor(Qt.ArrowCursor)

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

    def draw_overlay(self, painter):
        """Called when the canvas is being painted."""
        pass

    def _get_active_layer_manager(self):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return None
        return resolve_active_layer_manager(document)
