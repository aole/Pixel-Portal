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
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from .drawing import DrawingLogic
from .renderer import CanvasRenderer
from .tools.pentool import PenTool
from .tools.buckettool import BucketTool
from .tools.rectangletool import RectangleTool
from .tools.ellipsetool import EllipseTool
from .tools.linetool import LineTool
from .tools.selectrectangletool import SelectRectangleTool
from .tools.selectcircletool import SelectCircleTool
from .tools.selectlassotool import SelectLassoTool
from .tools.movetool import MoveTool
from .tools.erasertool import EraserTool
from .tools.pickertool import PickerTool


class Canvas(QWidget):
    cursor_pos_changed = Signal(QPoint)
    zoom_changed = Signal(float)
    selection_changed = Signal(bool)
    selection_size_changed = Signal(int, int)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.renderer = CanvasRenderer(self)
        self.drawing_logic = DrawingLogic(self.app)
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
        self.background_color = self.palette().window().color()
        self.selection_shape = None
        self.ctrl_pressed = False
        self.picker_cursor = QCursor(QPixmap("icons/toolpicker.png"), 0, 31)

        self.tools = {
            "Pen": PenTool(self),
            "Bucket": BucketTool(self),
            "Rectangle": RectangleTool(self),
            "Ellipse": EllipseTool(self),
            "Line": LineTool(self),
            "Select Rectangle": SelectRectangleTool(self),
            "Select Circle": SelectCircleTool(self),
            "Select Lasso": SelectLassoTool(self),
            "Move": MoveTool(self),
            "Eraser": EraserTool(self),
            "Picker": PickerTool(self),
        }
        self.current_tool = self.tools["Pen"]

        self.app.tool_changed.connect(self.on_tool_changed)
        self.app.document_changed.connect(self.update)

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
            self.current_tool = self.tools[self.app.tool]
            if hasattr(self.current_tool, 'activate'):
                self.current_tool.activate()
            self.on_tool_changed(self.app.tool)

    def on_tool_changed(self, tool):
        if self.ctrl_pressed:
            return

        if hasattr(self.current_tool, 'deactivate'):
            self.current_tool.deactivate()
        self.current_tool = self.tools[tool]
        if hasattr(self.current_tool, 'activate'):
            self.current_tool.activate()
        self.update()
        if tool == "Picker":
            self.setCursor(self.picker_cursor)
        elif tool in ["Bucket", "Rectangle", "Ellipse", "Line", "Select Rectangle", "Select Circle", "Select Lasso"]:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.BlankCursor)

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
        qpp.addRect(QRect(0, 0, self.app.document.width, self.app.document.height).normalized())
        self._update_selection_and_emit_size(qpp)

    def select_none(self):
        self._update_selection_and_emit_size(None)

    def invert_selection(self):
        if self.selection_shape is None:
            return
        qpp = QPainterPath()
        qpp.addRect(QRect(0, 0, self.app.document.width, self.app.document.height).normalized())
        if self.selection_shape:
            self.selection_shape = qpp.subtracted(self.selection_shape)
        else:
            self.selection_shape = qpp
        self.update()
        self._update_selection_and_emit_size(qpp.subtracted(self.selection_shape))

    def enterEvent(self, event):
        self.setFocus()
        self.mouse_over_canvas = True
        self.on_tool_changed(self.app.tool)
        self.update()
        self.zoom_changed.emit(self.zoom)
        doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(doc_pos)

    def leaveEvent(self, event):
        self.mouse_over_canvas = False
        self.unsetCursor()
        self.update()

    def get_doc_coords(self, canvas_pos):
        doc_width_scaled = self.app.document.width * self.zoom
        doc_height_scaled = self.app.document.height * self.zoom
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
        doc_width_scaled = self.app.document.width * self.zoom
        doc_height_scaled = self.app.document.height * self.zoom

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
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        doc_width_scaled = doc_width * self.zoom
        doc_height_scaled = doc_height * self.zoom

        x = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y = (canvas_height - doc_height_scaled) / 2 + self.y_offset
        return QRect(x, y, int(doc_width_scaled), int(doc_height_scaled))

    def paintEvent(self, event):
        painter = QPainter(self)
        self.renderer.paint(painter)

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.update()

    def draw_grid(self, painter, target_rect):
        if self.zoom < 2 or not self.grid_visible:
            return

        doc_width = self.app.document.width
        doc_height = self.app.document.height

        # Define colors for grid lines
        palette = self.palette()
        minor_color = palette.color(QPalette.ColorRole.Mid)
        minor_color.setAlpha(100)
        major_color = palette.color(QPalette.ColorRole.Text)
        major_color.setAlpha(100)

        # Find the range of document coordinates currently visible on the canvas
        doc_top_left = self.get_doc_coords(QPoint(0, 0))
        doc_bottom_right = self.get_doc_coords(QPoint(self.width(), self.height()))

        start_x = max(0, math.floor(doc_top_left.x()))
        end_x = min(doc_width, math.ceil(doc_bottom_right.x()))
        start_y = max(0, math.floor(doc_top_left.y()))
        end_y = min(doc_height, math.ceil(doc_bottom_right.y()))

        # Draw vertical lines
        for dx in range(start_x, end_x + 1):
            canvas_x = target_rect.x() + dx * self.zoom
            if dx % 8 == 0:
                painter.setPen(major_color)
            else:
                painter.setPen(minor_color)
            painter.drawLine(round(canvas_x), target_rect.top(), round(canvas_x), target_rect.bottom())

        # Draw horizontal lines
        for dy in range(start_y, end_y + 1):
            canvas_y = target_rect.y() + dy * self.zoom
            if dy % 8 == 0:
                painter.setPen(major_color)
            else:
                painter.setPen(minor_color)
            painter.drawLine(target_rect.left(), round(canvas_y), target_rect.right(), round(canvas_y))

    def draw_cursor(self, painter, target_rect, doc_image):
        if (
            not self.mouse_over_canvas
            or self.app.tool in ["Bucket", "Picker"]
            or self.app.tool.startswith("Select")
            or self.ctrl_pressed
        ):
            return

        # Use the application's brush size
        brush_size = self.app.pen_width

        # Center the brush cursor around the mouse position
        doc_pos = self.cursor_doc_pos
        offset = brush_size / 2
        doc_rect = QRect(
            doc_pos.x() - int(math.floor(offset)),
            doc_pos.y() - int(math.floor(offset)),
            brush_size,
            brush_size
        )

        # Convert document rectangle to screen coordinates for drawing
        screen_x = target_rect.x() + doc_rect.x() * self.zoom
        screen_y = target_rect.y() + doc_rect.y() * self.zoom
        screen_width = doc_rect.width() * self.zoom
        screen_height = doc_rect.height() * self.zoom

        cursor_screen_rect = QRect(
            int(screen_x),
            int(screen_y),
            max(1, int(screen_width)),
            max(1, int(screen_height))
        )

        # Sample the color from the document image instead of grabbing the screen
        total_r, total_g, total_b = 0, 0, 0
        pixel_count = 0

        # Clamp the doc_rect to the image boundaries
        clamped_doc_rect = doc_rect.intersected(doc_image.rect())

        if not clamped_doc_rect.isEmpty():
            for x in range(clamped_doc_rect.left(), clamped_doc_rect.right() + 1):
                for y in range(clamped_doc_rect.top(), clamped_doc_rect.bottom() + 1):
                    # Clamp coordinates to be within the image bounds
                    if 0 <= x < doc_image.width() and 0 <= y < doc_image.height():
                        color = doc_image.pixelColor(x, y)
                        # Only consider visible pixels for the average
                        if color.alpha() > 0:
                            total_r += color.red()
                            total_g += color.green()
                            total_b += color.blue()
                            pixel_count += 1

        if pixel_count > 0:
            avg_r = total_r / pixel_count
            avg_g = total_g / pixel_count
            avg_b = total_b / pixel_count
            # Invert the average color
            inverted_color = QColor(255 - avg_r, 255 - avg_g, 255 - avg_b)
        else:
            # Fallback for transparent areas or if off-canvas: use the cached background color
            bg_color = self.background_color
            inverted_color = QColor(255 - bg_color.red(), 255 - bg_color.green(), 255 - bg_color.blue())

        # Fill the cursor rectangle with the brush color
        painter.setBrush(self.app.pen_color)
        painter.setPen(Qt.NoPen) # No outline for the fill
        painter.drawRect(cursor_screen_rect)

        # Draw the inverted outline on top
        painter.setPen(inverted_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(cursor_screen_rect)

    def resizeEvent(self, event):
        # The canvas widget has been resized.
        # The document size does not change.
        pass

    def draw_line_for_test(self, p1, p2):
        self.drawing_logic.draw_line(p1, p2)

    def erase_line_for_test(self, p1, p2):
        active_layer = self.app.document.layer_manager.active_layer
        if active_layer:
            painter = QPainter(active_layer.image)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QColor(0, 0, 0, 0))
            painter.drawLine(p1, p2)

    def set_initial_zoom(self):
        canvas_width = self.width()
        canvas_height = self.height()
        doc_width = self.app.document.width
        doc_height = self.app.document.height

        if doc_width == 0 or doc_height == 0:
            return

        zoom_x = (0.8 * canvas_width) / doc_width
        zoom_y = (0.8 * canvas_height) / doc_height
        self.zoom = min(zoom_x, zoom_y)
        self.zoom_changed.emit(self.zoom)
        self.update()
