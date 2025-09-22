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
        self._tile_preview_listener_registered = False

        canvas_updated = getattr(self.canvas, "canvas_updated", None)
        connect = getattr(canvas_updated, "connect", None)
        if callable(connect):
            connect(self._on_canvas_updated)

        self._register_tile_preview_listener()

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
        if self._is_dragging:
            return
        self._clear_render_cache()

    def _register_tile_preview_listener(self):
        if self._tile_preview_listener_registered:
            return

        toggle_tile_preview = getattr(self.canvas, "toggle_tile_preview", None)
        if not callable(toggle_tile_preview):
            return

        callbacks = getattr(self.canvas, "_picker_tile_preview_callbacks", None)
        if callbacks is None:
            callbacks = []
            setattr(self.canvas, "_picker_tile_preview_callbacks", callbacks)

            original_toggle = toggle_tile_preview

            def wrapped_toggle(enabled, *, _orig=original_toggle, _canvas=self.canvas):
                result = _orig(enabled)
                for callback in list(getattr(_canvas, "_picker_tile_preview_callbacks", [])):
                    callback(enabled)
                return result

            setattr(self.canvas, "toggle_tile_preview", wrapped_toggle)

        callbacks.append(self._on_tile_preview_toggled)
        self._tile_preview_listener_registered = True

    def _on_tile_preview_toggled(self, enabled):
        if self._is_dragging:
            self._ensure_render_cache(force=True)
        else:
            self._clear_render_cache()
