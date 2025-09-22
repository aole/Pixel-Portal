from PySide6.QtCore import QPoint, Qt, QObject, Signal, QRect
from PySide6.QtGui import QMouseEvent, QCursor, QImage

from portal.core.frame_manager import resolve_active_layer_manager


class BaseTool(QObject):
    """Abstract base class for all drawing tools."""

    name = None
    icon = None
    shortcut = None
    category = None
    requires_visible_layer = True
    supports_right_click_erase = False
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

    # Geometry helpers ----------------------------------------------------
    @staticmethod
    def _rect_from_points(p1: QPoint, p2: QPoint) -> QRect:
        """Return an inclusive :class:`QRect` spanning *p1* and *p2*.

        ``QRect`` treats the second point of the ``(QPoint, QPoint)``
        constructor as inclusive, which means ``normalized()`` can shrink the
        rectangle by a pixel when ``p2`` lies up/left of ``p1``. The tools rely
        on consistent coverage regardless of drag direction, so we build the
        rectangle explicitly from the extremities instead of using
        ``normalized()``.
        """

        left = min(p1.x(), p2.x())
        right = max(p1.x(), p2.x())
        top = min(p1.y(), p2.y())
        bottom = max(p1.y(), p2.y())
        return QRect(QPoint(left, top), QPoint(right, bottom))

    # Preview helpers -----------------------------------------------------
    def _allocate_preview_images(
        self,
        *,
        replace_active_layer: bool = False,
        allocate_temp: bool = True,
        erase_preview: bool = False,
    ):
        """Prepare temporary and tile preview images for live rendering."""

        canvas = self.canvas
        canvas.temp_image_replaces_active_layer = replace_active_layer

        if allocate_temp:
            canvas.temp_image = QImage(canvas._document_size, QImage.Format_ARGB32)
            canvas.temp_image.fill(Qt.transparent)
        else:
            canvas.temp_image = None

        if erase_preview:
            canvas.is_erasing_preview = True
        else:
            # Ensure the attribute is reset even if the caller never touches it.
            canvas.is_erasing_preview = False

        if canvas.tile_preview_enabled:
            canvas.tile_preview_image = QImage(canvas._document_size, QImage.Format_ARGB32)
            canvas.tile_preview_image.fill(Qt.transparent)
        else:
            canvas.tile_preview_image = None

    def _refresh_preview_images(
        self,
        *,
        clear_temp: bool = True,
        clear_tile_preview: bool = True,
    ):
        """Clear preview buffers so they can be redrawn."""

        canvas = self.canvas
        if clear_temp and canvas.temp_image is not None:
            canvas.temp_image.fill(Qt.transparent)

        if not clear_tile_preview:
            return

        if canvas.tile_preview_enabled:
            if canvas.tile_preview_image is None:
                canvas.tile_preview_image = QImage(canvas._document_size, QImage.Format_ARGB32)
            canvas.tile_preview_image.fill(Qt.transparent)
        else:
            canvas.tile_preview_image = None

    def _clear_preview_images(self, *, clear_original: bool = True):
        """Reset preview buffers to an idle state."""

        canvas = self.canvas
        canvas.temp_image = None
        if clear_original:
            canvas.original_image = None
        canvas.tile_preview_image = None
        canvas.temp_image_replaces_active_layer = False
        canvas.is_erasing_preview = False

    def _get_active_layer_manager(self):
        document = getattr(self.canvas, "document", None)
        if document is None:
            return None
        return resolve_active_layer_manager(document)
