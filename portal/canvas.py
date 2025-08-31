import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QBrush,
    QPainter,
    QWheelEvent,
    QImage,
    QPixmap,
    QColor,
    QPen,
    QPainterPath,
    QTransform,
    QCursor,
    QPalette,
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, Slot, QSize
from .drawing import Drawing
from .renderer import CanvasRenderer
from .background import Background
from .tools import get_tools


class Canvas(QWidget):
    cursor_pos_changed = Signal(QPoint)
    zoom_changed = Signal(float)
    selection_changed = Signal(bool)
    selection_size_changed = Signal(int, int)
    canvas_updated = Signal()
    command_generated = Signal(object)

    def __init__(self, drawing_context, parent=None):
        super().__init__(parent)
        self.drawing_context = drawing_context
        self.renderer = CanvasRenderer(self, self.drawing_context)
        self.document = None
        self.drawing = Drawing()
        self.dragging = False
        self.x_offset = 0
        self.y_offset = 0
        self.zoom = 1.0
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.temp_image = None
        self.temp_image_replaces_active_layer = False
        self.original_image = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.background_pixmap = QPixmap("alphabg.png")
        self.cursor_doc_pos = QPoint()
        self.mouse_over_canvas = False
        self.grid_visible = False
        self.background = Background()
        self.background_color = self.palette().window().color()
        self.selection_shape = None
        self.ctrl_pressed = False
        self.picker_cursor = QCursor(QPixmap("icons/toolpicker.png"), 0, 31)
        self.is_erasing_preview = False

        # Properties that were previously in App
        self._document_size = QSize(64, 64)

        self.tools = {tool.name: tool(self) for tool in get_tools()}
        for tool in self.tools.values():
            if hasattr(tool, 'command_generated'):
                tool.command_generated.connect(self.command_generated)
        self.current_tool = self.tools["Pen"]

    @Slot(QSize)
    def set_document_size(self, size):
        self._document_size = size
        self.set_initial_zoom()
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.ctrl_pressed = True
            if hasattr(self.current_tool, 'deactivate'):
                self.current_tool.deactivate()
            self.current_tool = self.tools["Move"]
            if hasattr(self.current_tool, 'activate'):
                self.current_tool.activate()
            self.setCursor(Qt.ArrowCursor)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.ctrl_pressed = False
            if hasattr(self.current_tool, 'deactivate'):
                self.current_tool.deactivate()
            self.current_tool = self.tools[self.drawing_context.tool]
            if hasattr(self.current_tool, 'activate'):
                self.current_tool.activate()
            self.on_tool_changed(self.drawing_context.tool)

    def set_background(self, background: Background):
        self.background = background
        self.update()

    @Slot(str)
    def on_tool_changed(self, tool):
        if self.ctrl_pressed:
            return

        if hasattr(self.current_tool, 'deactivate'):
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool]
        if hasattr(self.current_tool, 'activate'):
            self.current_tool.activate()
        self.update()
        self.setCursor(self.current_tool.cursor)

    def _update_selection_and_emit_size(self, shape):
        self.selection_shape = shape
        if shape is None:
            self.selection_size_changed.emit(0, 0)
        else:
            bounds = shape.boundingRect()
            self.selection_size_changed.emit(int(bounds.width()), int(bounds.height()))
        self.update()
        self.selection_changed.emit(True)

    def select_all(self):
        qpp = QPainterPath()
        qpp.addRect(QRect(0, 0, self._document_size.width(), self._document_size.height()).normalized())
        self._update_selection_and_emit_size(qpp)

    def select_none(self):
        self._update_selection_and_emit_size(None)

    def invert_selection(self):
        if self.selection_shape is None:
            return
        qpp = QPainterPath()
        qpp.addRect(QRect(0, 0, self._document_size.width(), self._document_size.height()).normalized())
        if self.selection_shape:
            self.selection_shape = qpp.subtracted(self.selection_shape)
        else:
            self.selection_shape = qpp
        self.update()
        self._update_selection_and_emit_size(self.selection_shape)

    def enterEvent(self, event):
        self.setFocus()
        self.mouse_over_canvas = True
        self.on_tool_changed(self.drawing_context.tool)
        self.update()
        self.zoom_changed.emit(self.zoom)
        doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(doc_pos)

    def leaveEvent(self, event):
        self.mouse_over_canvas = False
        self.unsetCursor()
        self.update()

    def get_doc_coords(self, canvas_pos):
        doc_width_scaled = self._document_size.width() * self.zoom
        doc_height_scaled = self._document_size.height() * self.zoom
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        if self.zoom == 0:
            return QPoint(0, 0)

        return QPoint(
            (canvas_pos.x() - x_offset) / self.zoom,
            (canvas_pos.y() - y_offset) / self.zoom,
        )

    def get_canvas_coords(self, doc_pos):
        doc_width_scaled = self._document_size.width() * self.zoom
        doc_height_scaled = self._document_size.height() * self.zoom
        canvas_width = self.width()
        canvas_height = self.height()

        x_offset = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y_offset = (canvas_height - doc_height_scaled) / 2 + self.y_offset

        return QPoint(
            doc_pos.x() * self.zoom + x_offset,
            doc_pos.y() * self.zoom + y_offset,
        )

    def mousePressEvent(self, event):
        doc_pos = self.get_doc_coords(event.pos())
        if event.button() == Qt.LeftButton:
            self.current_tool.mousePressEvent(event, doc_pos)
        elif event.button() == Qt.RightButton:
            self.tools["Eraser"].mousePressEvent(event, doc_pos)
        elif event.button() == Qt.MiddleButton:
            self.dragging = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        self.cursor_doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(self.cursor_doc_pos)
        self.update()

        doc_pos = self.get_doc_coords(event.pos())

        if not (event.buttons() & Qt.LeftButton):
            if hasattr(self.current_tool, "mouseHoverEvent"):
                self.current_tool.mouseHoverEvent(event, doc_pos)

        if event.buttons() & Qt.LeftButton:
            self.current_tool.mouseMoveEvent(event, doc_pos)
            self.canvas_updated.emit()
        elif event.buttons() & Qt.RightButton:
            self.tools["Eraser"].mouseMoveEvent(event, doc_pos)
        elif (event.buttons() & Qt.MiddleButton) and self.dragging:
            delta = event.pos() - self.last_point
            self.x_offset += delta.x()
            self.y_offset += delta.y()
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        doc_pos = self.get_doc_coords(event.pos())
        if event.button() == Qt.LeftButton:
            self.current_tool.mouseReleaseEvent(event, doc_pos)
        elif event.button() == Qt.RightButton:
            self.tools["Eraser"].mouseReleaseEvent(event, doc_pos)
        elif event.button() == Qt.MiddleButton:
            self.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        mouse_pos = event.position().toPoint()
        doc_pos_before_zoom = self.get_doc_coords(mouse_pos)

        # Zoom
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom *= 1.25
        else:
            self.zoom /= 1.25

        # Clamp zoom level
        self.zoom = max(1, min(self.zoom, 20.0))

        # Adjust pan to keep doc_pos_before_zoom at the same mouse_pos
        doc_width_scaled = self._document_size.width() * self.zoom
        doc_height_scaled = self._document_size.height() * self.zoom

        # This is the top-left of the document in canvas coordinates *without* the old self.x_offset
        base_x_offset = (self.width() - doc_width_scaled) / 2
        base_y_offset = (self.height() - doc_height_scaled) / 2

        # This is where the doc_pos would be with the new zoom but without any panning
        canvas_x_after_zoom_no_pan = base_x_offset + doc_pos_before_zoom.x() * self.zoom
        canvas_y_after_zoom_no_pan = base_y_offset + doc_pos_before_zoom.y() * self.zoom

        # We want this point to be at mouse_pos. The difference is the required pan offset.
        self.x_offset = mouse_pos.x() - canvas_x_after_zoom_no_pan
        self.y_offset = mouse_pos.y() - canvas_y_after_zoom_no_pan

        self.update()
        self.zoom_changed.emit(self.zoom)

    def get_target_rect(self):
        doc_width = self._document_size.width()
        doc_height = self._document_size.height()
        canvas_width = self.width()
        canvas_height = self.height()

        doc_width_scaled = doc_width * self.zoom
        doc_height_scaled = doc_height * self.zoom

        x = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y = (canvas_height - doc_height_scaled) / 2 + self.y_offset
        return QRect(x, y, int(doc_width_scaled), int(doc_height_scaled))

    def set_document(self, document):
        self.document = document
        self.set_document_size(QSize(document.width, document.height))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.renderer.paint(painter, self.document)

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.update()

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass

    def set_initial_zoom(self):
        canvas_width = self.width()
        canvas_height = self.height()
        doc_width = self._document_size.width()
        doc_height = self._document_size.height()

        if doc_width == 0 or doc_height == 0:
            return

        zoom_x = (0.8 * canvas_width) / doc_width
        zoom_y = (0.8 * canvas_height) / doc_height
        self.zoom = min(zoom_x, zoom_y)
        self.zoom_changed.emit(self.zoom)
        self.update()

        