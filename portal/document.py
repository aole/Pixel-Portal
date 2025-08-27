from .layer_manager import LayerManager
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QSize, QBuffer
from PIL import Image
import io


class Document:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layer_manager = LayerManager(width, height)

    def render(self) -> QImage:
        """Composites all visible layers into a single image."""
        final_image = QImage(QSize(self.width, self.height), QImage.Format_ARGB32)
        final_image.fill("transparent")

        painter = QPainter(final_image)
        for layer in self.layer_manager.layers:
            if layer.visible:
                painter.setOpacity(layer.opacity)
                painter.drawImage(0, 0, layer.image)
        painter.end()

        return final_image

    def get_current_image_for_ai(self):
        q_image = self.render()
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))
        return pil_image

    def add_new_layer_with_image(self, image):
        self.layer_manager.add_layer_with_image(image)

    def add_layer_from_clipboard(self, q_image):
        # Convert QImage to PIL Image
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))

        self.layer_manager.add_layer_with_image(pil_image)

    def render_except(self, layer_to_exclude) -> QImage:
        """Composites all visible layers into a single image, except for the given layer."""
        final_image = QImage(QSize(self.width, self.height), QImage.Format_ARGB32)
        final_image.fill("transparent")

        painter = QPainter(final_image)
        for layer in self.layer_manager.layers:
            if layer.visible and layer is not layer_to_exclude:
                painter.setOpacity(layer.opacity)
                painter.drawImage(0, 0, layer.image)
        painter.end()

        return final_image
