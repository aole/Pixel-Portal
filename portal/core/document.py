from __future__ import annotations

from collections.abc import Callable, Iterable
import io
import json

from PySide6.QtCore import QBuffer, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PIL import Image, ImageSequence, ImageQt

from portal.core.frame_manager import FrameManager
from portal.core.layer import Layer
from portal.core.layer_manager import LayerManager


class Document:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.frame_manager = FrameManager(width, height)
        self._layer_manager_listeners: list[Callable[[LayerManager], None]] = []
        self._notify_layer_manager_changed()

    @property
    def layer_manager(self) -> LayerManager:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            raise ValueError("Document has no active frame.")
        return layer_manager

    def add_layer_manager_listener(
        self,
        callback: Callable[[LayerManager], None],
        *,
        invoke_immediately: bool = True,
    ) -> Callable[[], None]:
        """Register a callback that fires whenever the active layer manager changes."""

        self._layer_manager_listeners.append(callback)
        if invoke_immediately:
            callback(self.layer_manager)

        def remove() -> None:
            try:
                self._layer_manager_listeners.remove(callback)
            except ValueError:
                pass

        return remove

    def remove_layer_manager_listener(self, callback: Callable[[LayerManager], None]) -> None:
        """Unregister a previously registered layer manager listener."""

        try:
            self._layer_manager_listeners.remove(callback)
        except ValueError:
            pass

    def clone(self):
        new_doc = Document(self.width, self.height)
        new_doc.frame_manager = self.frame_manager.clone()
        new_doc._notify_layer_manager_changed()
        return new_doc

    def render(self) -> QImage:
        """Composites all visible layers into a single image."""
        return self.render_current_frame()

    def add_frame(self):
        frame = self.frame_manager.add_frame()
        self._notify_layer_manager_changed()
        return frame

    def remove_frame(self, index: int):
        self.frame_manager.remove_frame(index)
        self._notify_layer_manager_changed()

    def select_frame(self, index: int):
        self.frame_manager.select_frame(index)
        self._notify_layer_manager_changed()

    def render_current_frame(self) -> QImage:
        return self.frame_manager.render_current_frame()

    @property
    def key_frames(self) -> list[int]:
        return sorted(self.frame_manager.key_frames)

    def set_key_frames(self, frames: Iterable[int]) -> bool:
        changed = self.frame_manager.set_key_frames(frames)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def add_key_frame(self, frame: int) -> bool:
        changed = self.frame_manager.add_key_frame(frame)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def remove_key_frame(self, frame: int) -> bool:
        changed = self.frame_manager.remove_key_frame(frame)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def duplicate_key_frame(
        self, source_frame: int | None = None, target_frame: int | None = None
    ) -> int | None:
        created = self.frame_manager.duplicate_key_frame(source_frame, target_frame)
        if created is not None:
            self._notify_layer_manager_changed()
        return created

    def apply_frame_manager_snapshot(self, snapshot: FrameManager) -> None:
        self.frame_manager = snapshot.clone()
        self.width = self.frame_manager.width
        self.height = self.frame_manager.height
        self._notify_layer_manager_changed()

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
        self.frame_manager.width = width
        self.frame_manager.height = height

        if interpolation == "Smooth":
            mode = Qt.SmoothTransformation
        else:
            mode = Qt.FastTransformation

        for frame in self.frame_manager.frames:
            layer_manager = frame.layer_manager
            layer_manager.width = width
            layer_manager.height = height
            for layer in layer_manager.layers:
                layer.image = layer.image.scaled(QSize(width, height), Qt.IgnoreAspectRatio, mode)
                layer.on_image_change.emit()

    def crop(self, rect):
        rect = rect.normalized()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        new_width = rect.width()
        new_height = rect.height()

        self.width = new_width
        self.height = new_height
        self.frame_manager.width = new_width
        self.frame_manager.height = new_height

        for frame in self.frame_manager.frames:
            layer_manager = frame.layer_manager
            layer_manager.width = new_width
            layer_manager.height = new_height
            for layer in layer_manager.layers:
                layer.image = layer.image.copy(rect)
                layer.on_image_change.emit()

    def _notify_layer_manager_changed(self) -> None:
        manager = self.frame_manager.current_layer_manager
        if manager is None:
            return
        for callback in list(self._layer_manager_listeners):
            callback(manager)

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
