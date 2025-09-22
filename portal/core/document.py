from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import io
import json

from PySide6.QtCore import QBuffer, QSize, Qt, QRect
from PySide6.QtGui import QImage, QPainter
from PIL import Image, ImageSequence, ImageQt

from portal.core.aole_archive import AOLEArchive
from portal.core.animation_player import DEFAULT_TOTAL_FRAMES
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
        self.file_path: str | None = None
        self.ai_output_rect = QRect(0, 0, max(1, int(width)), max(1, int(height)))
        self.playback_total_frames = self.normalize_playback_total_frames(
            DEFAULT_TOTAL_FRAMES
        )

    # ------------------------------------------------------------------
    def get_ai_output_rect(self) -> QRect:
        """Return the clamped rectangle the AI output should occupy."""

        return QRect(self._normalize_ai_output_rect(self.ai_output_rect))

    # ------------------------------------------------------------------
    def set_ai_output_rect(self, rect: QRect | None) -> QRect:
        """Clamp and store the preferred AI output rectangle."""

        normalized = self._normalize_ai_output_rect(rect)
        if normalized == self.ai_output_rect:
            return QRect(self.ai_output_rect)
        self.ai_output_rect = normalized
        return QRect(self.ai_output_rect)

    # ------------------------------------------------------------------
    def reset_ai_output_rect(self) -> QRect:
        """Reset the AI output rectangle to the full document bounds."""

        self.ai_output_rect = QRect(
            0,
            0,
            max(1, int(self.width)),
            max(1, int(self.height)),
        )
        return QRect(self.ai_output_rect)

    # ------------------------------------------------------------------
    def ensure_ai_output_rect(self) -> QRect:
        """Clamp the stored AI rectangle to the current document bounds."""

        self.ai_output_rect = self._normalize_ai_output_rect(self.ai_output_rect)
        return QRect(self.ai_output_rect)

    # ------------------------------------------------------------------
    def _normalize_ai_output_rect(self, rect: QRect | None) -> QRect:
        doc_width = max(1, int(self.width))
        doc_height = max(1, int(self.height))

        min_width = min(32, doc_width)
        min_height = min(32, doc_height)

        if rect is None:
            left = 0
            top = 0
            width = doc_width
            height = doc_height
        else:
            normalized = QRect(rect).normalized()
            width = max(1, int(normalized.width()))
            height = max(1, int(normalized.height()))
            left = int(normalized.x())
            top = int(normalized.y())

        width = max(min_width, min(width, doc_width))
        height = max(min_height, min(height, doc_height))

        max_left = doc_width - width
        max_top = doc_height - height
        left = max(0, min(left, max_left))
        top = max(0, min(top, max_top))

        return QRect(left, top, width, height)

    @property
    def layer_manager(self) -> LayerManager:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            raise ValueError("Document has no active frame.")
        setter = getattr(layer_manager, "set_document", None)
        if callable(setter):
            setter(self)
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
        new_doc.ai_output_rect = new_doc._normalize_ai_output_rect(self.ai_output_rect)
        new_doc.set_playback_total_frames(self.playback_total_frames)
        return new_doc

    @staticmethod
    def normalize_playback_total_frames(frame_count) -> int:
        try:
            normalized = int(frame_count)
        except (TypeError, ValueError):
            normalized = DEFAULT_TOTAL_FRAMES
        if normalized < 1:
            normalized = 1
        return normalized

    def set_playback_total_frames(self, frame_count) -> int:
        normalized = self.normalize_playback_total_frames(frame_count)
        self.playback_total_frames = normalized
        return normalized

    def render(self) -> QImage:
        """Composites all visible layers into a single image."""
        return self.render_current_frame()

    def add_frame(self):
        frame = self.frame_manager.add_frame()
        self._notify_layer_manager_changed()
        return frame

    def insert_frame(self, index: int):
        frame = self.frame_manager.insert_frame(index)
        self.select_frame(index)
        return frame

    def remove_frame(self, index: int):
        self.frame_manager.remove_frame(index)
        self._notify_layer_manager_changed()

    def select_frame(self, index: int):
        if index < 0:
            index = 0
        previous_manager = self.frame_manager.current_layer_manager
        previous_active_uid = None
        if previous_manager is not None and previous_manager.active_layer is not None:
            previous_active_uid = previous_manager.active_layer.uid
        self.frame_manager.ensure_frame(index)
        self.frame_manager.select_frame(index)
        if previous_active_uid is not None:
            new_manager = self.frame_manager.current_layer_manager
            if new_manager is not None:
                index = new_manager.index_for_layer_uid(previous_active_uid)
                if index is not None:
                    new_manager.select_layer(index)
        self._notify_layer_manager_changed()

    def render_current_frame(self) -> QImage:
        return self.frame_manager.render_current_frame()

    @property
    def key_frames(self) -> list[int]:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return [0]
        layer = layer_manager.active_layer
        if layer is None:
            return [0]
        return self.frame_manager.layer_key_frames(layer.uid)

    def set_key_frames(self, frames: Iterable[int]) -> bool:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        changed = self.frame_manager.set_layer_key_frames(layer.uid, frames)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def move_key_frames(self, moves: Mapping[int, int]) -> bool:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        changed = self.frame_manager.move_layer_keys(layer.uid, moves)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def add_key_frame(self, frame: int) -> bool:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        changed = self.frame_manager.add_layer_key(layer.uid, frame)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def remove_key_frame(self, frame: int) -> bool:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        changed = self.frame_manager.remove_layer_key(layer.uid, frame)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def duplicate_key_frame(
        self, source_frame: int | None = None, target_frame: int | None = None
    ) -> int | None:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return None
        layer = layer_manager.active_layer
        if layer is None:
            return None
        created = self.frame_manager.duplicate_layer_key(
            layer.uid, source_frame, target_frame
        )
        if created is not None:
            self._notify_layer_manager_changed()
        return created

    def copy_active_layer_key(self, frame: int) -> Layer | None:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return None
        layer = layer_manager.active_layer
        if layer is None:
            return None
        return self.frame_manager.clone_layer_key_state(layer.uid, frame)

    def paste_key_frame(self, frame: int, key_state: Layer) -> bool:
        layer_manager = self.frame_manager.current_layer_manager
        if layer_manager is None:
            return False
        layer = layer_manager.active_layer
        if layer is None:
            return False
        changed = self.frame_manager.paste_layer_key(layer.uid, frame, key_state)
        if changed:
            self._notify_layer_manager_changed()
        return changed

    def key_frames_for_layer(self, layer: Layer) -> list[int]:
        return self.frame_manager.layer_key_frames(layer.uid)

    def register_layer(
        self, layer: Layer, index: int | None = None, *, key_frames: Iterable[int] | None = None
    ) -> None:
        self.frame_manager.register_new_layer(layer, index, key_frames=key_frames)

    def unregister_layer(self, layer_uid: int) -> None:
        self.frame_manager.unregister_layer(layer_uid)

    def duplicate_layer_keys(self, source_layer: Layer, new_layer: Layer) -> None:
        self.frame_manager.duplicate_layer_keys(source_layer.uid, new_layer)

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
            pil_image.info["layer_onion_skin"] = str(layer.onion_skin_enabled)
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

        self.file_path = filename

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
                    layer.onion_skin_enabled = props.get("onion_skin_enabled", False)
                else:
                    layer = Layer.from_qimage(qimage, f"Layer {i+1}")
                doc.layer_manager.layers.append(layer)
                doc.register_layer(layer, len(doc.layer_manager.layers) - 1)

        doc.file_path = filename
        return doc

    def save_aole(self, filename: str) -> None:
        """Persist the entire document, including frames and layers, to an AOLE archive."""

        AOLEArchive.save(self, filename)
        self.file_path = filename

    @classmethod
    def load_aole(cls, filename: str) -> "Document":
        """Load a full document, including animation data, from an AOLE archive."""

        document = AOLEArchive.load(cls, filename)
        document.file_path = filename
        return document

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
        self.ensure_ai_output_rect()

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
        self.ensure_ai_output_rect()

    def _notify_layer_manager_changed(self) -> None:
        manager = self.frame_manager.current_layer_manager
        if manager is None:
            return
        setter = getattr(manager, "set_document", None)
        if callable(setter):
            setter(self)
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
