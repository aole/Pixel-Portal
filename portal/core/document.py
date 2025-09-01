from portal.commands.layer_manager import LayerManager
from portal.core.layer import Layer
from PySide6.QtGui import QImage, QPainter, QTransform
from PySide6.QtCore import QSize, QBuffer, Qt
from PIL import Image, ImageSequence, ImageQt
import io
import json


class Document:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layer_manager = LayerManager(width, height)

    def clone(self):
        new_doc = Document(self.width, self.height)
        new_doc.layer_manager = self.layer_manager.clone()
        return new_doc

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

    @staticmethod
    def qimage_to_pil(qimage):
        return ImageQt.fromqimage(qimage)

    def save_tiff(self, filename):
        images = []
        for layer in self.layer_manager.layers:
            pil_image = self.qimage_to_pil(layer.image)
            # Store metadata in the 'info' dictionary
            pil_image.info["layer_name"] = layer.name
            pil_image.info["layer_visible"] = str(layer.visible)
            pil_image.info["layer_opacity"] = str(layer.opacity)
            images.append(pil_image)

        if images:
            # The 'info' dictionary is only saved for the first image
            # when using save_all. We need to save each image individually
            # if we want to preserve metadata for each layer.
            # A better approach is to use a different format that supports layers
            # like PSD, but for TIFF, we can store it in the description tag.
            # For now, let's just fix the loading of names.
            layer_properties = [layer.get_properties() for layer in self.layer_manager.layers]
            images[0].save(
                filename,
                save_all=True,
                append_images=images[1:],
                format='TIFF',
                compression='tiff_lzw',
                description=json.dumps(layer_properties)
            )

    @staticmethod
    def load_tiff(filename):
        with Image.open(filename) as img:
            width, height = img.size
            doc = Document(width, height)
            doc.layer_manager.layers = []  # Clear default layer

            try:
                layer_properties = json.loads(img.tag_v2[270])
            except (KeyError, json.JSONDecodeError):
                layer_properties = None

            for i, page in enumerate(ImageSequence.Iterator(img)):
                # Convert PIL image to QImage
                qimage = ImageQt.toqimage(page.convert("RGBA"))

                if layer_properties and i < len(layer_properties):
                    props = layer_properties[i]
                    layer = Layer.from_qimage(qimage, props.get("name", f"Layer {i+1}"))
                    layer.visible = props.get("visible", True)
                    layer.opacity = props.get("opacity", 1.0)
                else:
                    layer = Layer.from_qimage(qimage, f"Layer {i+1}")
                doc.layer_manager.layers.append(layer)
        
        return doc

    def resize(self, width, height, interpolation):
        self.width = width
        self.height = height

        if interpolation == "Smooth":
            mode = Qt.SmoothTransformation
        else:
            mode = Qt.FastTransformation

        for layer in self.layer_manager.layers:
            layer.image = layer.image.scaled(QSize(width, height), Qt.IgnoreAspectRatio, mode)
            layer.on_image_change.emit()

    def crop(self, rect):
        self.width = rect.width()
        self.height = rect.height()

        for layer in self.layer_manager.layers:
            layer.image = layer.image.copy(rect)
            layer.on_image_change.emit()

    def get_current_image_for_ai(self):
        q_image = self.render()
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))
        return pil_image

    def add_new_layer_with_image(self, image):
        self.layer_manager.add_layer_with_image(image, name="AI Generated Layer")

    def add_layer_from_clipboard(self, q_image):
        if q_image.width() > self.width or q_image.height() > self.height:
            q_image = q_image.scaled(self.width, self.height, Qt.KeepAspectRatio, Qt.FastTransformation)

        # Convert QImage to PIL Image
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))

        self.layer_manager.add_layer_with_image(pil_image, name="Pasted Layer")

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
