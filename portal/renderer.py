import math

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap, QTransform


class CanvasRenderer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.app = canvas.app

    def paint(self, painter):
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.fillRect(self.canvas.rect(), self.canvas.palette().window())

        target_rect = self.canvas.get_target_rect()

        self._draw_background(painter, target_rect)
        image_to_draw_on = self._draw_document(painter, target_rect)
        self._draw_border(painter, target_rect)
        self.canvas.draw_grid(painter, target_rect)
        self.canvas.draw_cursor(painter, target_rect, image_to_draw_on)
        if self.canvas.selection_shape:
            self.draw_selection_overlay(painter, target_rect)

        self._draw_document_dimensions(painter, target_rect)

    def _draw_background(self, painter, target_rect):
        brush = QBrush(self.canvas.background_pixmap)
        transform = QTransform()
        transform.translate(target_rect.x(), target_rect.y())
        transform.scale(self.canvas.zoom, self.canvas.zoom)
        brush.setTransform(transform)
        painter.fillRect(target_rect, brush)

    def _draw_document(self, painter, target_rect):
        composite_image = self.app.document.render()
        image_to_draw_on = composite_image

        active_layer = self.app.document.layer_manager.active_layer
        if self.canvas.temp_image and active_layer:
            final_image = QImage(
                self.app.document.width,
                self.app.document.height,
                QImage.Format_ARGB32,
            )
            final_image.fill(QColor("transparent"))
            image_painter = QPainter(final_image)

            for layer in self.app.document.layer_manager.layers:
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
            painter.drawImage(target_rect, composite_image)

        return image_to_draw_on

    def _draw_border(self, painter, target_rect):
        border_color = QColor("black")
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

        black_pen = QPen(QColor("black"), 2)
        black_pen.setCosmetic(True)
        black_pen.setDashPattern([4, 4])
        painter.setPen(black_pen)
        painter.drawPath(self.canvas.selection_shape)

        white_pen = QPen(QColor("white"), 2)
        white_pen.setCosmetic(True)
        white_pen.setDashPattern([4, 4])
        white_pen.setDashOffset(4)
        painter.setPen(white_pen)
        painter.drawPath(self.canvas.selection_shape)

        painter.restore()

    def _draw_document_dimensions(self, painter, target_rect):
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("black"))

        width_text = f"{self.app.document.width}px"
        height_text = f"{self.app.document.height}px"

        width_rect = painter.fontMetrics().boundingRect(width_text)
        width_x = target_rect.right() + 5
        width_y = target_rect.top() + width_rect.height()
        painter.drawText(width_x, width_y, width_text)

        height_rect = painter.fontMetrics().boundingRect(height_text)
        height_x = target_rect.left() - height_rect.width() - 5
        height_y = target_rect.bottom()
        painter.drawText(height_x, height_y, height_text)
