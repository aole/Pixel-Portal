from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QWheelEvent


class CanvasInputHandler:
    def __init__(self, canvas):
        self.canvas = canvas
        self.drawing_context = canvas.drawing_context
        self._ctrl_forced_move = False
        self._alt_forced_picker = False

    def _is_selection_tool_active(self) -> bool:
        current_tool = getattr(self.canvas, "current_tool", None)
        category = getattr(current_tool, "category", None)
        return isinstance(category, str) and category == "select"

    def keyPressEvent(self, event):
        key_text = event.text()
        for tool in self.canvas.tools.values():
            if tool.shortcut and key_text == tool.shortcut:
                self.drawing_context.set_tool(tool.name)
                return

        if event.key() == Qt.Key_Alt:
            if not self._is_selection_tool_active():
                self.drawing_context.set_tool("Picker")
                self._alt_forced_picker = True
            else:
                self._alt_forced_picker = False
        elif event.key() == Qt.Key_Control:
            if self._is_selection_tool_active():
                self._ctrl_forced_move = False
            else:
                self.drawing_context.set_tool("Move")
                self._ctrl_forced_move = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Alt:
            if self._alt_forced_picker:
                self.drawing_context.set_tool(self.drawing_context.previous_tool)
            self._alt_forced_picker = False
        elif event.key() == Qt.Key_Control:
            if self._ctrl_forced_move:
                self.drawing_context.set_tool(self.drawing_context.previous_tool)
            self._ctrl_forced_move = False

    def mousePressEvent(self, event):
        current_tool = getattr(self.canvas, "current_tool", None)
        requires_visible = True
        if current_tool is not None:
            requires_visible = getattr(current_tool, "requires_visible_layer", True)

        document = getattr(self.canvas, "document", None)
        active_layer = None
        if document is not None and document.layer_manager is not None:
            active_layer = document.layer_manager.active_layer

        if active_layer and not active_layer.visible and requires_visible:
            self.canvas.setCursor(Qt.ForbiddenCursor)
            return

        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._ensure_auto_keyframe()

        doc_pos = self.canvas.get_doc_coords(
            event.position().toPoint(),
            wrap=False,
        )
        if event.button() == Qt.LeftButton:
            self.canvas.current_tool.mousePressEvent(event, doc_pos)
        elif event.button() == Qt.RightButton:
            self.canvas.tools["Eraser"].mousePressEvent(event, doc_pos)
        elif event.button() == Qt.MiddleButton:
            self.canvas.dragging = True
            self.canvas.last_point = event.position().toPoint()

    def mouseMoveEvent(self, event):
        self.canvas.cursor_doc_pos = self.canvas.get_doc_coords(
            event.position().toPoint(), wrap=False
        )
        self.canvas.cursor_pos_changed.emit(self.canvas.cursor_doc_pos)
        self.canvas.update()

        doc_pos = self.canvas.get_doc_coords(
            event.position().toPoint(),
            wrap=False,
        )

        current_tool = getattr(self.canvas, "current_tool", None)
        requires_visible = True
        if current_tool is not None:
            requires_visible = getattr(current_tool, "requires_visible_layer", True)

        document = getattr(self.canvas, "document", None)
        active_layer = None
        if document is not None and document.layer_manager is not None:
            active_layer = document.layer_manager.active_layer

        if active_layer and not active_layer.visible and requires_visible:
            self.canvas.setCursor(Qt.ForbiddenCursor)
        elif current_tool is not None:
            self.canvas.setCursor(current_tool.cursor)

        if not (event.buttons() & Qt.LeftButton):
            if current_tool is not None and hasattr(current_tool, "mouseHoverEvent"):
                current_tool.mouseHoverEvent(event, doc_pos)

        if active_layer and not active_layer.visible and requires_visible:
            return

        if event.buttons() & Qt.LeftButton:
            if current_tool is not None:
                current_tool.mouseMoveEvent(event, doc_pos)
            self.canvas.canvas_updated.emit()
        elif event.buttons() & Qt.RightButton:
            self.canvas.tools["Eraser"].mouseMoveEvent(event, doc_pos)
        elif (event.buttons() & Qt.MiddleButton) and self.canvas.dragging:
            delta = event.position().toPoint() - self.canvas.last_point
            self.canvas.x_offset += delta.x()
            self.canvas.y_offset += delta.y()
            self.canvas.last_point = event.position().toPoint()
            self.canvas.update()

    def mouseReleaseEvent(self, event):
        current_tool = getattr(self.canvas, "current_tool", None)
        requires_visible = True
        if current_tool is not None:
            requires_visible = getattr(current_tool, "requires_visible_layer", True)

        document = getattr(self.canvas, "document", None)
        active_layer = None
        if document is not None and document.layer_manager is not None:
            active_layer = document.layer_manager.active_layer

        if active_layer and not active_layer.visible and requires_visible:
            if current_tool is not None:
                self.canvas.setCursor(current_tool.cursor)
            return

        doc_pos = self.canvas.get_doc_coords(
            event.position().toPoint(),
            wrap=False,
        )
        if event.button() == Qt.LeftButton:
            if current_tool is not None:
                current_tool.mouseReleaseEvent(event, doc_pos)
        elif event.button() == Qt.RightButton:
            self.canvas.tools["Eraser"].mouseReleaseEvent(event, doc_pos)
        elif event.button() == Qt.MiddleButton:
            self.canvas.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        mouse_pos = event.position().toPoint()
        doc_pos_before_zoom = self.canvas.get_doc_coords(mouse_pos)

        # Zoom
        delta = event.angleDelta().y()
        if delta > 0:
            self.canvas.zoom *= 1.25
        else:
            self.canvas.zoom /= 1.25

        # Clamp zoom level
        min_zoom = getattr(self.canvas, "min_zoom", 0.05)
        max_zoom = getattr(self.canvas, "max_zoom", 20.0)
        self.canvas.zoom = max(min_zoom, min(self.canvas.zoom, max_zoom))

        # Adjust pan to keep doc_pos_before_zoom at the same mouse_pos
        doc_width_scaled = self.canvas._document_size.width() * self.canvas.zoom
        doc_height_scaled = self.canvas._document_size.height() * self.canvas.zoom

        # This is the top-left of the document in canvas coordinates *without* the old self.canvas.x_offset
        base_x_offset = (self.canvas.width() - doc_width_scaled) / 2
        base_y_offset = (self.canvas.height() - doc_height_scaled) / 2

        # This is where the doc_pos would be with the new zoom but without any panning
        canvas_x_after_zoom_no_pan = base_x_offset + doc_pos_before_zoom.x() * self.canvas.zoom
        canvas_y_after_zoom_no_pan = base_y_offset + doc_pos_before_zoom.y() * self.canvas.zoom

        # We want this point to be at mouse_pos. The difference is the required pan offset.
        self.canvas.x_offset = mouse_pos.x() - canvas_x_after_zoom_no_pan
        self.canvas.y_offset = mouse_pos.y() - canvas_y_after_zoom_no_pan

        self.canvas.update()
        self.canvas.zoom_changed.emit(self.canvas.zoom)

    def _ensure_auto_keyframe(self) -> bool:
        canvas = self.canvas
        if not getattr(canvas, "is_auto_key_enabled", None):
            return False
        if not canvas.is_auto_key_enabled():
            return False
        app = getattr(canvas, "app", None)
        if app is None:
            return False
        ensure_method = getattr(app, "ensure_auto_key_for_active_layer", None)
        if ensure_method is None:
            return False
        return bool(ensure_method())
