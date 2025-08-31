import math

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QTransform,
)


class CanvasRenderer:
    def __init__(self, canvas, drawing_context):
        self.canvas = canvas
        self.drawing_context = drawing_context

    def paint(self, painter, document):
        if not document:
            return

        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.canvas.rect(), self.canvas.palette().window())

        target_rect = self.canvas.get_target_rect()

        self._draw_background(painter, target_rect)
        image_to_draw_on = self._draw_document(painter, target_rect, document)
        self._draw_border(painter, target_rect)
        self._draw_mirror_guides(painter, target_rect, document)
        self.draw_grid(painter, target_rect)
        self.draw_cursor(painter, target_rect, image_to_draw_on)
        if self.canvas.selection_shape:
            self.draw_selection_overlay(painter, target_rect)

        self._draw_document_dimensions(painter, target_rect, document)

    def _draw_mirror_guides(self, painter, target_rect, document):
        if not self.drawing_context.mirror_x and not self.drawing_context.mirror_y:
            return

        painter.save()
        pen = QPen(QColor(255, 0, 0, 150)) # A semi-transparent red
        pen.setCosmetic(True)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)

        doc_width = document.width
        doc_height = document.height

        if self.drawing_context.mirror_x:
            center_x = target_rect.x() + (doc_width / 2) * self.canvas.zoom
            painter.drawLine(int(center_x), 0, int(center_x), self.canvas.height())

        if self.drawing_context.mirror_y:
            center_y = target_rect.y() + (doc_height / 2) * self.canvas.zoom
            painter.drawLine(0, int(center_y), self.canvas.width(), int(center_y))

        painter.restore()


    def _draw_background(self, painter, target_rect):
        if self.canvas.background.is_checkered:
            brush = QBrush(self.canvas.background_pixmap)
            transform = QTransform()
            transform.translate(target_rect.x(), target_rect.y())
            transform.scale(self.canvas.zoom, self.canvas.zoom)
            brush.setTransform(transform)
            painter.fillRect(target_rect, brush)
        else:
            painter.fillRect(target_rect, self.canvas.background.color)

    def _draw_document(self, painter, target_rect, document):
        if self.canvas.temp_image and self.canvas.temp_image_replaces_active_layer:
            # This path is for tools like the Eraser, which operate on a copy of the active layer.
            # The `temp_image` is a full replacement for the active layer's image.
            # We need to reconstruct the entire document image, substituting the original active
            # layer with the temporary one.
            final_image = QImage(
                document.width,
                document.height,
                QImage.Format_ARGB32,
            )
            final_image.fill(QColor("transparent"))
            image_painter = QPainter(final_image)

            active_layer = document.layer_manager.active_layer
            for layer in document.layer_manager.layers:
                if layer.visible:
                    image_to_draw = layer.image
                    if layer is active_layer:
                        image_to_draw = self.canvas.temp_image

                    image_painter.setOpacity(layer.opacity)
                    image_painter.drawImage(0, 0, image_to_draw)

            image_painter.end()
            painter.drawImage(target_rect, final_image)
            return final_image
        else:
            # This path is for tools that create a temporary overlay or preview.
            composite_image = document.render()
            image_to_draw_on = composite_image

            if self.canvas.temp_image:
                # Create a new final image to compose our preview onto.
                final_image = QImage(composite_image.size(), QImage.Format_ARGB32)
                final_image.fill(Qt.transparent)
                p = QPainter(final_image)

                # Special case for the eraser preview
                if self.canvas.is_erasing_preview:
                    active_layer = document.layer_manager.active_layer
                    if active_layer:
                        # 1. Render all layers *except* the active one as the base
                        background = document.render_except(active_layer)
                        p.drawImage(0, 0, background)

                        # 2. Punch a hole in a copy of the active layer
                        erased_active_layer = active_layer.image.copy()
                        p_temp = QPainter(erased_active_layer)
                        p_temp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                        p_temp.drawImage(0, 0, self.canvas.temp_image) # temp_image is the erase mask
                        p_temp.end()

                        # 3. Draw the modified active layer on top of the background
                        p.setOpacity(active_layer.opacity)
                        p.drawImage(0, 0, erased_active_layer)

                # Case for other tools (Pen, Shapes, etc.)
                else:
                    # Draw the current document state first
                    p.drawImage(0, 0, composite_image)
                    # Then draw the temporary tool preview (e.g., a brush stroke) on top
                    p.drawImage(0, 0, self.canvas.temp_image)

                p.end()
                image_to_draw_on = final_image

            painter.drawImage(target_rect, image_to_draw_on)
            return image_to_draw_on

    def _draw_border(self, painter, target_rect):
        border_color = self.canvas.palette().color(QPalette.ColorRole.Text)
        border_pen = QPen(border_color, 1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.drawRect(target_rect.adjusted(0, 0, -1, -1))

    def draw_selection_overlay(self, painter, target_rect):
        painter.save()

        transform = QTransform()
        transform.translate(target_rect.x(), target_rect.y())
        transform.scale(self.canvas.zoom, self.canvas.zoom)
        painter.setTransform(transform)

        pen1 = QPen(self.canvas.palette().color(QPalette.ColorRole.Highlight), 2)
        pen1.setCosmetic(True)
        pen1.setDashPattern([4, 4])
        painter.setPen(pen1)
        painter.drawPath(self.canvas.selection_shape)

        pen2 = QPen(self.canvas.palette().color(QPalette.ColorRole.HighlightedText), 2)
        pen2.setCosmetic(True)
        pen2.setDashPattern([4, 4])
        pen2.setDashOffset(4)
        painter.setPen(pen2)
        painter.drawPath(self.canvas.selection_shape)

        painter.restore()

    def _draw_document_dimensions(self, painter, target_rect, document):
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(self.canvas.palette().color(QPalette.ColorRole.Text))

        width_text = f"{document.width}px"
        height_text = f"{document.height}px"

        width_rect = painter.fontMetrics().boundingRect(width_text)
        width_x = target_rect.right() + 5
        width_y = target_rect.top() + width_rect.height()
        painter.drawText(width_x, width_y, width_text)

        height_rect = painter.fontMetrics().boundingRect(height_text)
        height_x = target_rect.left() - height_rect.width() - 5
        height_y = target_rect.bottom()
        painter.drawText(height_x, height_y, height_text)

    def draw_grid(self, painter, target_rect):
        if self.canvas.zoom < 2 or not self.canvas.grid_visible:
            return

        doc_width = self.canvas._document_size.width()
        doc_height = self.canvas._document_size.height()

        # Define colors for grid lines
        palette = self.canvas.palette()
        minor_color = palette.color(QPalette.ColorRole.Mid)
        minor_color.setAlpha(100)
        major_color = palette.color(QPalette.ColorRole.Text)
        major_color.setAlpha(100)

        # Find the range of document coordinates currently visible on the canvas
        doc_top_left = self.canvas.get_doc_coords(QPoint(0, 0))
        doc_bottom_right = self.canvas.get_doc_coords(QPoint(self.canvas.width(), self.canvas.height()))

        start_x = max(0, math.floor(doc_top_left.x()))
        end_x = min(doc_width, math.ceil(doc_bottom_right.x()))
        start_y = max(0, math.floor(doc_top_left.y()))
        end_y = min(doc_height, math.ceil(doc_bottom_right.y()))

        # Draw vertical lines
        for dx in range(start_x, end_x + 1):
            canvas_x = target_rect.x() + dx * self.canvas.zoom
            if dx % 8 == 0:
                painter.setPen(major_color)
            else:
                painter.setPen(minor_color)
            painter.drawLine(round(canvas_x), target_rect.top(), round(canvas_x), target_rect.bottom())

        # Draw horizontal lines
        for dy in range(start_y, end_y + 1):
            canvas_y = target_rect.y() + dy * self.canvas.zoom
            if dy % 8 == 0:
                painter.setPen(major_color)
            else:
                painter.setPen(minor_color)
            painter.drawLine(target_rect.left(), round(canvas_y), target_rect.right(), round(canvas_y))

    def draw_cursor(self, painter, target_rect, doc_image):
        if (
            not self.canvas.mouse_over_canvas
            or self.canvas.drawing_context.tool in ["Bucket", "Picker"]
            or self.canvas.drawing_context.tool.startswith("Select")
            or self.canvas.ctrl_pressed
        ):
            return

        # Use the application's brush size
        brush_size = self.canvas.drawing_context.pen_width

        # Center the brush cursor around the mouse position
        doc_pos = self.canvas.cursor_doc_pos
        offset = brush_size / 2
        doc_rect = QRect(
            doc_pos.x() - int(math.floor(offset)),
            doc_pos.y() - int(math.floor(offset)),
            brush_size,
            brush_size
        )

        # Convert document rectangle to screen coordinates for drawing
        screen_x = target_rect.x() + doc_rect.x() * self.canvas.zoom
        screen_y = target_rect.y() + doc_rect.y() * self.canvas.zoom
        screen_width = doc_rect.width() * self.canvas.zoom
        screen_height = doc_rect.height() * self.canvas.zoom

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
            bg_color = self.canvas.background_color
            inverted_color = QColor(255 - bg_color.red(), 255 - bg_color.green(), 255 - bg_color.blue())

        # Fill the cursor rectangle with the brush color
        painter.setBrush(self.canvas.drawing_context.pen_color)
        painter.setPen(Qt.NoPen)  # No outline for the fill

        if self.canvas.drawing_context.brush_type == "Circular":
            painter.drawEllipse(cursor_screen_rect)
        else:
            painter.drawRect(cursor_screen_rect)


        # Draw the inverted outline on top
        painter.setPen(inverted_color)
        painter.setBrush(Qt.NoBrush)

        if self.canvas.drawing_context.brush_type == "Circular":
            painter.drawEllipse(cursor_screen_rect)
        else:
            painter.drawRect(cursor_screen_rect)