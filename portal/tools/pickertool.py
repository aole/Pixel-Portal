from portal.tools.basetool import BaseTool
from PySide6.QtGui import QColor, QCursor, QPixmap
from PySide6.QtCore import QPoint


class PickerTool(BaseTool):
    name = "Picker"
    icon = "icons/toolpicker.png"
    shortcut = "i"
    category = "draw"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.cursor = QCursor(QPixmap("icons/toolpicker.png"), 0, 31)
        self._cached_render = None
        self._cached_tile_preview_enabled = None
        self._is_dragging = False

        canvas_updated = getattr(self.canvas, "canvas_updated", None)
        connect = getattr(canvas_updated, "connect", None)
        if callable(connect):
            connect(self._on_canvas_updated)

    def mousePressEvent(self, event, doc_pos):
        self._begin_drag()
        self.pick_color(doc_pos)

    def mouseMoveEvent(self, event, doc_pos):
        if event.buttons():  # Only pick if a mouse button is pressed
            self.pick_color(doc_pos)

    def mouseReleaseEvent(self, event, doc_pos):
        self._end_drag()
        if self.canvas.drawing_context.previous_tool:
            self.canvas.drawing_context.set_tool(self.canvas.drawing_context.previous_tool)

    def pick_color(self, doc_pos):
        rendered_image = self._ensure_render_cache()
        if rendered_image is None:
            return
        sample_pos = doc_pos
        if self.canvas.tile_preview_enabled:
            doc_width = rendered_image.width()
            doc_height = rendered_image.height()
            sample_pos = QPoint(doc_pos.x() % doc_width, doc_pos.y() % doc_height)

        if rendered_image.rect().contains(sample_pos):
            color = rendered_image.pixelColor(sample_pos)
            if color.alpha() > 0:  # Only pick visible colors
                self.canvas.drawing_context.set_pen_color(color.name())

    def _begin_drag(self):
        self._is_dragging = True
        self._ensure_render_cache(force=True)

    def _end_drag(self):
        if not self._is_dragging:
            return
        self._is_dragging = False
        self._clear_render_cache()

    def _ensure_render_cache(self, *, force=False):
        tile_preview_enabled = bool(getattr(self.canvas, "tile_preview_enabled", False))
        needs_refresh = force or self._cached_render is None
        if not needs_refresh and tile_preview_enabled != self._cached_tile_preview_enabled:
            needs_refresh = True

        if not needs_refresh:
            return self._cached_render

        document = getattr(self.canvas, "document", None)
        if document is None or not hasattr(document, "render"):
            self._cached_render = None
            self._cached_tile_preview_enabled = tile_preview_enabled
            return None

        self._cached_render = document.render()
        self._cached_tile_preview_enabled = tile_preview_enabled
        return self._cached_render

    def _clear_render_cache(self):
        self._cached_render = None
        self._cached_tile_preview_enabled = None

    def _on_canvas_updated(self):
        self._clear_render_cache()
