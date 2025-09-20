import math

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
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

from portal.core.frame_manager import resolve_active_layer_manager
from portal.ui.background import BackgroundImageMode


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

        # Explicitly handle rotation preview to override normal document drawing
        if (
            self.canvas.temp_image
            and self.canvas.temp_image_replaces_active_layer
            and self.drawing_context.tool in {"Rotate", "Scale", "Transform"}
        ):
            final_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            final_image.fill(QColor("transparent"))
            image_painter = QPainter(final_image)
            layer_manager = resolve_active_layer_manager(document)
            if layer_manager is not None:
                active_layer = layer_manager.active_layer
                for layer in layer_manager.layers:
                    if layer.visible:
                        image_to_draw = layer.image
                        if layer is active_layer:
                            image_to_draw = self.canvas.temp_image
                        image_painter.setOpacity(layer.opacity)
                        image_painter.drawImage(0, 0, image_to_draw)
            image_painter.end()
            painter.drawImage(target_rect, final_image)
            image_to_draw_on = final_image
        else:
            image_to_draw_on = self._draw_document(painter, target_rect, document)
            if self.canvas.tile_preview_enabled:
                self._draw_tile_preview(painter, target_rect, image_to_draw_on)

        self._draw_border(painter, target_rect)
        self._draw_mirror_guides(painter, target_rect, document)
        self.draw_grid(painter, target_rect)
        self.draw_cursor(painter, target_rect, image_to_draw_on)
        self.canvas.current_tool.draw_overlay(painter)
        if self.canvas.selection_shape:
            self.draw_selection_overlay(painter, target_rect)
        self._draw_ai_output_overlay(painter, target_rect)

        self._draw_document_dimensions(painter, target_rect, document)

    def _draw_tile_preview(self, painter, target_rect, image):
        rows = self.canvas.tile_preview_rows
        cols = self.canvas.tile_preview_cols
        center_row = rows // 2
        center_col = cols // 2
        for row in range(rows):
            for col in range(cols):
                if row == center_row and col == center_col:
                    continue
                dx = (col - center_col) * target_rect.width()
                dy = (row - center_row) * target_rect.height()
                tile_rect = QRect(
                    target_rect.x() + dx,
                    target_rect.y() + dy,
                    target_rect.width(),
                    target_rect.height(),
                )
                self._draw_background(painter, tile_rect)
                painter.drawImage(tile_rect, image)
                overlay = self.canvas.tile_preview_image
                if overlay is not None:
                    if self.canvas.is_erasing_preview:
                        painter.save()
                        painter.setCompositionMode(
                            QPainter.CompositionMode_DestinationOut
                        )
                        painter.drawImage(tile_rect, overlay)
                        painter.restore()
                    else:
                        painter.drawImage(tile_rect, overlay)

    def _draw_mirror_guides(self, painter, target_rect, document):
        if not self.drawing_context.mirror_x and not self.drawing_context.mirror_y:
            return

        painter.save()
        pen = QPen(QColor(255, 0, 0, 150))  # A semi-transparent red
        pen.setCosmetic(True)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        zoom = self.canvas.zoom

        if self.drawing_context.mirror_x:
            axis_x = self.canvas._resolve_mirror_x_position()
            if axis_x is not None:
                line_x = target_rect.x() + (axis_x + 0.5) * zoom
                painter.drawLine(
                    int(round(line_x)), 0, int(round(line_x)), self.canvas.height()
                )

        if self.drawing_context.mirror_y:
            axis_y = self.canvas._resolve_mirror_y_position()
            if axis_y is not None:
                line_y = target_rect.y() + (axis_y + 0.5) * zoom
                painter.drawLine(
                    0, int(round(line_y)), self.canvas.width(), int(round(line_y))
                )

        painter.restore()

        handle_rects = self.canvas._mirror_handle_rects()
        if handle_rects:
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0, 180))
            for rect in handle_rects.values():
                painter.drawEllipse(rect)
            painter.restore()

    def _draw_background(self, painter, target_rect):
        background_image = self.canvas.background_image
        if background_image and not background_image.isNull():
            mode = getattr(self.canvas, "background_mode", BackgroundImageMode.FIT)
            alpha = getattr(self.canvas, "background_image_alpha", 1.0)
            try:
                alpha = float(alpha)
            except (TypeError, ValueError):
                alpha = 1.0
            alpha = max(0.0, min(1.0, alpha))
            if alpha <= 0:
                return

            painter.save()
            painter.setOpacity(alpha)
            try:
                if mode == BackgroundImageMode.STRETCH:
                    painter.drawPixmap(target_rect, background_image)
                elif mode == BackgroundImageMode.FIT:
                    scaled = background_image.scaled(
                        target_rect.size(), Qt.KeepAspectRatio, Qt.FastTransformation
                    )
                    if scaled.isNull():
                        return
                    dest_x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
                    dest_y = target_rect.y() + (target_rect.height() - scaled.height()) / 2
                    dest_rect = QRect(
                        int(round(dest_x)),
                        int(round(dest_y)),
                        scaled.width(),
                        scaled.height(),
                    )
                    painter.drawPixmap(dest_rect, scaled)
                elif mode == BackgroundImageMode.FILL:
                    scaled = background_image.scaled(
                        target_rect.size(),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.FastTransformation,
                    )
                    if scaled.isNull():
                        return
                    source_x = max(0, (scaled.width() - target_rect.width()) // 2)
                    source_y = max(0, (scaled.height() - target_rect.height()) // 2)
                    source_rect = QRect(
                        source_x,
                        source_y,
                        target_rect.width(),
                        target_rect.height(),
                    )
                    painter.drawPixmap(target_rect, scaled, source_rect)
                elif mode == BackgroundImageMode.CENTER:
                    scaled_width = max(
                        1, int(round(background_image.width() * self.canvas.zoom))
                    )
                    scaled_height = max(
                        1, int(round(background_image.height() * self.canvas.zoom))
                    )
                    if (
                        scaled_width != background_image.width()
                        or scaled_height != background_image.height()
                    ):
                        scaled = background_image.scaled(
                            scaled_width,
                            scaled_height,
                            Qt.IgnoreAspectRatio,
                            Qt.FastTransformation,
                        )
                    else:
                        scaled = background_image
                    if scaled.isNull():
                        return

                    dest_x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
                    dest_y = target_rect.y() + (target_rect.height() - scaled.height()) / 2

                    painter.save()
                    painter.setClipRect(target_rect)
                    painter.drawPixmap(int(round(dest_x)), int(round(dest_y)), scaled)
                    painter.restore()
                else:
                    # Fallback to stretch if an unknown mode is set.
                    painter.drawPixmap(target_rect, background_image)
            finally:
                painter.restore()
            return
        elif self.canvas.background.is_checkered:
            brush = QBrush(self.canvas.background_pixmap)
            transform = QTransform()
            transform.translate(target_rect.x(), target_rect.y())
            transform.scale(self.canvas.zoom, self.canvas.zoom)
            brush.setTransform(transform)
            painter.fillRect(target_rect, brush)
        else:
            painter.fillRect(target_rect, self.canvas.background.color)

    def _draw_document(self, painter, target_rect, document):
        layer_manager = resolve_active_layer_manager(document)
        if layer_manager is None:
            empty_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            empty_image.fill(Qt.transparent)
            painter.drawImage(target_rect, empty_image)
            return empty_image

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

            active_layer = layer_manager.active_layer
            for layer in layer_manager.layers:
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
            # This path handles the standard document rendering and optional tool previews.
            final_image = QImage(document.width, document.height, QImage.Format_ARGB32)
            final_image.fill(Qt.transparent)
            p = QPainter(final_image)

            active_layer = layer_manager.active_layer
            for layer in layer_manager.layers:
                if not layer.visible:
                    continue

                p.setOpacity(layer.opacity)

                if (
                    self.canvas.temp_image
                    and self.canvas.is_erasing_preview
                    and layer is active_layer
                ):
                    # Punch a hole in a copy of the active layer using the erase mask.
                    erased_active_layer = active_layer.image.copy()
                    p_temp = QPainter(erased_active_layer)
                    p_temp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                    p_temp.drawImage(0, 0, self.canvas.temp_image)
                    p_temp.end()
                    p.drawImage(0, 0, erased_active_layer)
                else:
                    p.drawImage(0, 0, layer.image)
                    if self.canvas.temp_image and layer is active_layer:
                        # Draw the temporary tool preview at the correct layer depth
                        p.drawImage(0, 0, self.canvas.temp_image)

            p.end()
            painter.drawImage(target_rect, final_image)
            return final_image

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

    def _draw_ai_output_overlay(self, painter, target_rect):
        if not getattr(self.canvas, "ai_output_edit_enabled", False):
            return

        overlay_rect = self.canvas._ai_output_overlay_rect()
        if overlay_rect is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        border_pen = QPen(QColor(220, 0, 0))
        border_pen.setCosmetic(True)
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(overlay_rect)

        handle_pen = QPen(QColor(0, 0, 0, 200))
        handle_pen.setCosmetic(True)
        handle_pen.setWidth(1)
        painter.setPen(handle_pen)

        handle_rects = self.canvas._ai_output_handle_rects()
        for name, rect in handle_rects.items():
            if name == self.canvas._ai_output_active_handle:
                brush = QColor(255, 200, 0)
            elif name == self.canvas._ai_output_hover_handle:
                brush = QColor(220, 220, 220)
            else:
                brush = QColor(255, 255, 255)
            painter.setBrush(brush)
            painter.drawRect(rect)

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

        major_visible = self.canvas.grid_major_visible and self.canvas.grid_major_spacing > 0
        minor_visible = self.canvas.grid_minor_visible and self.canvas.grid_minor_spacing > 0

        if not major_visible and not minor_visible:
            return

        doc_width = self.canvas._document_size.width()
        doc_height = self.canvas._document_size.height()

        # Define colors for grid lines
        palette = self.canvas.palette()
        minor_color = palette.color(QPalette.ColorRole.Mid)
        minor_color.setAlpha(100)
        major_color = palette.color(QPalette.ColorRole.Text)
        major_color.setAlpha(100)

        major_spacing = max(1, int(self.canvas.grid_major_spacing))
        minor_spacing = max(1, int(self.canvas.grid_minor_spacing))

        # Find the range of document coordinates currently visible on the canvas
        doc_top_left = self.canvas.get_doc_coords(QPoint(0, 0))
        doc_bottom_right = self.canvas.get_doc_coords(
            QPoint(self.canvas.width(), self.canvas.height())
        )

        start_x = max(0, math.floor(doc_top_left.x()))
        end_x = min(doc_width, math.ceil(doc_bottom_right.x()))
        start_y = max(0, math.floor(doc_top_left.y()))
        end_y = min(doc_height, math.ceil(doc_bottom_right.y()))

        # Draw vertical lines
        for dx in range(start_x, end_x + 1):
            canvas_x = target_rect.x() + dx * self.canvas.zoom
            pen = None
            if major_visible and dx % major_spacing == 0:
                pen = major_color
            elif minor_visible and dx % minor_spacing == 0:
                pen = minor_color

            if pen is None:
                continue

            painter.setPen(pen)
            painter.drawLine(
                round(canvas_x),
                target_rect.top(),
                round(canvas_x),
                target_rect.bottom(),
            )

        # Draw horizontal lines
        for dy in range(start_y, end_y + 1):
            canvas_y = target_rect.y() + dy * self.canvas.zoom
            pen = None
            if major_visible and dy % major_spacing == 0:
                pen = major_color
            elif minor_visible and dy % minor_spacing == 0:
                pen = minor_color

            if pen is None:
                continue

            painter.setPen(pen)
            painter.drawLine(
                target_rect.left(),
                round(canvas_y),
                target_rect.right(),
                round(canvas_y),
            )

    def draw_cursor(self, painter, target_rect, doc_image):
        layer_manager = resolve_active_layer_manager(self.canvas.document)
        active_layer = layer_manager.active_layer if layer_manager else None
        if (
            not self.canvas.mouse_over_canvas
            or (active_layer and not active_layer.visible)
            or self.canvas.drawing_context.tool
            in ["Bucket", "Picker", "Move", "Rotate", "Scale", "Transform"]
            or self.canvas.drawing_context.tool.startswith("Select")
            or self.canvas.ctrl_pressed
        ):
            return

        brush_type = self.canvas.drawing_context.brush_type
        is_eraser = self.canvas.drawing_context.tool == "Eraser"
        pattern_image = self.canvas.drawing_context.pattern_brush
        use_pattern_cursor = (
            brush_type == "Pattern"
            and pattern_image is not None
            and not pattern_image.isNull()
            and pattern_image.width() > 0
            and pattern_image.height() > 0
        )

        # Use the application's brush size
        brush_size = self.canvas.drawing_context.pen_width

        # Center the brush cursor around the mouse position
        doc_pos = self.canvas.cursor_doc_pos

        if use_pattern_cursor:
            pattern_width = pattern_image.width()
            pattern_height = pattern_image.height()
            doc_rect = QRect(
                doc_pos.x() - pattern_width // 2,
                doc_pos.y() - pattern_height // 2,
                pattern_width,
                pattern_height,
            )
        else:
            offset = brush_size / 2
            doc_rect = QRect(
                doc_pos.x() - int(math.floor(offset)),
                doc_pos.y() - int(math.floor(offset)),
                brush_size,
                brush_size,
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
            max(1, int(screen_height)),
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
            inverted_color = QColor(
                255 - bg_color.red(), 255 - bg_color.green(), 255 - bg_color.blue()
            )

        if use_pattern_cursor:
            painter.save()
            painter.setOpacity(0.7)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)
            source_rect = QRectF(0, 0, pattern_width, pattern_height)
            painter.drawImage(QRectF(cursor_screen_rect), pattern_image, source_rect)
            painter.restore()
        else:
            if not is_eraser:
                # Fill the cursor rectangle with the brush color when drawing.
                painter.setBrush(self.canvas.drawing_context.pen_color)
                painter.setPen(Qt.NoPen)  # No outline for the fill

                if brush_type == "Circular":
                    painter.drawEllipse(cursor_screen_rect)
                else:
                    painter.drawRect(cursor_screen_rect)

        if not use_pattern_cursor:
            # Draw the inverted outline on top for solid brushes
            painter.setPen(inverted_color)
            painter.setBrush(Qt.NoBrush)

            if brush_type == "Circular":
                painter.drawEllipse(cursor_screen_rect)
            else:
                painter.drawRect(cursor_screen_rect)
