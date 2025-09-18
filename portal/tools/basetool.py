from PySide6.QtCore import QPoint, Qt, QObject, Signal
from PySide6.QtGui import QMouseEvent, QCursor, QImage

from portal.core.frame_manager import resolve_active_layer_manager


class BaseTool(QObject):
    """Abstract base class for all drawing tools."""

    name = None
    icon = None
    shortcut = None
    category = None
    requires_visible_layer = True
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
