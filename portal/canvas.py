import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QWheelEvent, QImage, QPixmap, QColor, QPen, QPainterPath, QTransform
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from .drawing import DrawingLogic


class Canvas(QWidget):
    cursor_pos_changed = Signal(QPoint)
    zoom_changed = Signal(float)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.drawing_logic = DrawingLogic(self.app)
        self.drawing = False
        self.erasing = False
        self.dragging = False
        self.x_offset = 0
        self.y_offset = 0
        self.zoom = 1.0
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.temp_image = None
        self.original_image = None
        self.setMouseTracking(True)
        self.background_pixmap = QPixmap("alphabg.png")
        self.cursor_doc_pos = QPoint()
        self.mouse_over_canvas = False
        self.grid_visible = False
        self.background_color = self.palette().window().color()
        self.selection_shape = None
        self.app.tool_changed.connect(self.on_tool_changed)

    def on_tool_changed(self, tool):
        self.update()
        if tool in ["Bucket", "Rectangle", "Ellipse", "Line", "Select Rectangle", "Select Circle", "Select Lasso"]:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.BlankCursor)

    def select_all(self):
        qpp = QPainterPath()
        qpp.addRect(QRect(0, 0, self.app.document.width, self.app.document.height).normalized())
        self.selection_shape = qpp
        self.update()

    def select_none(self):
        self.selection_shape = None
        self.update()

    def invert_selection(self):
        qpp = QPainterPath()
        qpp.addRect(QRect(0, 0, self.app.document.width, self.app.document.height).normalized())
        self.selection_shape = qpp.subtracted(self.selection_shape)
        self.update()

    def enterEvent(self, event):
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
        if event.button() == Qt.LeftButton:
            if self.app.tool == "Bucket":
                self.drawing_logic.flood_fill(self.get_doc_coords(event.pos()), self.selection_shape)
                self.app.add_undo_state()
                self.update()
                return

            active_layer = self.app.document.layer_manager.active_layer
            if active_layer:
                self.drawing = True
                self.start_point = self.get_doc_coords(event.pos())
                self.last_point = self.start_point

                if self.app.tool not in ["Select Rectangle", "Select Circle", "Select Lasso"]:
                    self.original_image = active_layer.image.copy()
                    self.temp_image = self.original_image.copy()

                if self.app.tool == "Select Rectangle":
                    self.selection_shape = QPainterPath(self.start_point)
                elif self.app.tool == "Select Circle":
                    self.selection_shape = QPainterPath(self.start_point)
                elif self.app.tool == "Select Lasso":
                    self.selection_shape = QPainterPath(self.start_point)

                if self.app.tool == "Pen":
                    # Draw a single point for a click
                    painter = QPainter(self.temp_image)
                    if self.selection_shape:
                        painter.setClipPath(self.selection_shape)
                    pen = QPen(self.app.pen_color, self.app.pen_width, Qt.SolidLine)
                    painter.setPen(pen)
                    painter.drawPoint(self.last_point)
                    painter.end()
                    self.update()

        if event.button() == Qt.MiddleButton:
            self.dragging = True
            self.last_point = event.pos()

        if event.button() == Qt.RightButton:
            active_layer = self.app.document.layer_manager.active_layer
            if active_layer:
                self.erasing = True
                self.last_point = self.get_doc_coords(event.pos())
                self.temp_image = active_layer.image.copy()

                # Erase a single point for a click
                painter = QPainter(self.temp_image)
                if self.selection_shape:
                    painter.setClipPath(self.selection_shape)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen(QColor(0, 0, 0, 0), self.app.pen_width, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawPoint(self.last_point)
                painter.end()
                self.update()

    def mouseMoveEvent(self, event):
        self.cursor_doc_pos = self.get_doc_coords(event.pos())
        self.cursor_pos_changed.emit(self.cursor_doc_pos)
        self.update()  # Redraw to show cursor updates

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            current_point = self.get_doc_coords(event.pos())

            if self.app.tool in ["Line", "Rectangle", "Ellipse"]:
                # For shapes, we draw on a fresh copy of the original image each time
                self.temp_image = self.original_image.copy()

            if self.app.tool in ["Select Rectangle", "Select Circle", "Select Lasso"]:
                if self.app.tool == "Select Rectangle":
                    qpp = QPainterPath()
                    qpp.addRect(QRect(self.start_point, current_point).normalized())
                    self.selection_shape = qpp
                elif self.app.tool == "Select Circle":
                    qpp = QPainterPath()
                    qpp.addEllipse(QRect(self.start_point, current_point).normalized())
                    self.selection_shape = qpp
                elif self.app.tool == "Select Lasso":
                    self.selection_shape.lineTo(current_point)
                self.update()
                return

            painter = QPainter(self.temp_image)
            if self.selection_shape:
                painter.setClipPath(self.selection_shape)
            pen = QPen(self.app.pen_color, self.app.pen_width, Qt.SolidLine)
            painter.setPen(pen)

            if self.app.tool == "Pen":
                painter.drawLine(self.last_point, current_point)
                self.last_point = current_point
            elif self.app.tool == "Line":
                painter.drawLine(self.start_point, current_point)
            elif self.app.tool == "Rectangle":
                rect = QRect(self.start_point, current_point).normalized()
                self.drawing_logic.draw_rect(painter, rect)
            elif self.app.tool == "Ellipse":
                rect = QRect(self.start_point, current_point).normalized()
                self.drawing_logic.draw_ellipse(painter, rect)
                
            self.update()
        if (event.buttons() & Qt.RightButton) and self.erasing:
            current_point = self.get_doc_coords(event.pos())
            painter = QPainter(self.temp_image)
            if self.selection_shape:
                painter.setClipPath(self.selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(QColor(0, 0, 0, 0), self.app.pen_width, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.last_point, current_point)
            self.last_point = current_point
            self.update()
        if (event.buttons() & Qt.MiddleButton) and self.dragging:
            delta = event.pos() - self.last_point
            self.x_offset += delta.x()
            self.y_offset += delta.y()
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            active_layer = self.app.document.layer_manager.active_layer
            if active_layer:
                current_point = self.get_doc_coords(event.pos())

                # For shape tools, we need to do a final draw on mouse release
                if self.app.tool in ["Line", "Rectangle", "Ellipse"]:
                    self.temp_image = self.original_image.copy()
                    painter = QPainter(self.temp_image)
                    if self.selection_shape:
                        painter.setClipPath(self.selection_shape)
                    pen = QPen(self.app.pen_color, self.app.pen_width, Qt.SolidLine)
                    painter.setPen(pen)

                    if self.app.tool == "Line":
                        painter.drawLine(self.start_point, current_point)
                    elif self.app.tool == "Rectangle":
                        rect = QRect(self.start_point, current_point).normalized()
                        self.drawing_logic.draw_rect(painter, rect)
                    elif self.app.tool == "Ellipse":
                        rect = QRect(self.start_point, current_point).normalized()
                        self.drawing_logic.draw_ellipse(painter, rect)

                    painter.end()

                # For drawing tools, commit the temp image to the active layer.
                if self.app.tool not in ["Select Rectangle", "Select Circle", "Select Lasso"]:
                    active_layer.image = self.temp_image
                    self.app.add_undo_state()
                    self.temp_image = None
                    self.original_image = None

                self.update()
                
        if event.button() == Qt.RightButton and self.erasing:
            self.erasing = False
            active_layer = self.app.document.layer_manager.active_layer
            if active_layer:
                active_layer.image = self.temp_image
                self.temp_image = None
                self.app.add_undo_state()
                self.update()
        if event.button() == Qt.MiddleButton:
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

    def paintEvent(self, event):
        canvas_painter = QPainter(self)
        canvas_painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        # Fill background of entire canvas
        canvas_painter.fillRect(self.rect(), self.palette().window())

        # Calculate document dimensions and position
        doc_width = self.app.document.width
        doc_height = self.app.document.height
        canvas_width = self.width()
        canvas_height = self.height()

        doc_width_scaled = doc_width * self.zoom
        doc_height_scaled = doc_height * self.zoom

        x = (canvas_width - doc_width_scaled) / 2 + self.x_offset
        y = (canvas_height - doc_height_scaled) / 2 + self.y_offset
        target_rect = QRect(x, y, int(doc_width_scaled), int(doc_height_scaled))

        # Draw the tiled background for the document area
        canvas_painter.drawTiledPixmap(target_rect, self.background_pixmap)

        # Render all layers
        composite_image = self.app.document.render()
        image_to_draw_on = composite_image

        # Draw the active layer (or the temp drawing image) in the correct order
        active_layer = self.app.document.layer_manager.active_layer
        if (self.drawing or self.erasing) and self.temp_image and active_layer:
            # We are actively drawing, so we need to composite the image with the temporary drawing
            final_image = QImage(self.app.document.width, self.app.document.height, QImage.Format_ARGB32)
            final_image.fill(Qt.transparent)
            painter = QPainter(final_image)

            # Draw all layers in order
            for layer in self.app.document.layer_manager.layers:
                if layer.visible:
                    image_to_draw = layer.image
                    if layer is active_layer:
                        # If it's the active layer, draw the temp image instead
                        image_to_draw = self.temp_image

                    painter.setOpacity(layer.opacity)
                    painter.drawImage(0, 0, image_to_draw)

            painter.end()
            canvas_painter.drawImage(target_rect, final_image)
            image_to_draw_on = final_image
        else:
            # We are not drawing, just show the rendered document
            canvas_painter.drawImage(target_rect, composite_image)

        self.draw_grid(canvas_painter, target_rect)
        self.draw_cursor(canvas_painter, target_rect, image_to_draw_on)
        if self.selection_shape:
            self.draw_selection_overlay(canvas_painter, target_rect)

    def draw_selection_overlay(self, painter, target_rect):
        painter.save()

        transform = QTransform()
        transform.translate(target_rect.x(), target_rect.y())
        transform.scale(self.zoom, self.zoom)
        painter.setTransform(transform)

        black_pen = QPen(QColor("black"), 2)
        black_pen.setCosmetic(True)
        black_pen.setDashPattern([4, 4])
        painter.setPen(black_pen)
        painter.drawPath(self.selection_shape)

        white_pen = QPen(QColor("white"), 2)
        white_pen.setCosmetic(True)
        white_pen.setDashPattern([4, 4])
        white_pen.setDashOffset(4)
        painter.setPen(white_pen)
        painter.drawPath(self.selection_shape)

        painter.restore()

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        self.update()

    def draw_grid(self, painter, target_rect):
        if self.zoom < 2 or not self.grid_visible:
            return

        doc_width = self.app.document.width
        doc_height = self.app.document.height

        # Define colors for grid lines
        minor_color = QColor(0, 0, 0, 40)
        major_color = QColor(0, 0, 0, 100)

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
        if not self.mouse_over_canvas or self.app.tool == "Bucket":
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
