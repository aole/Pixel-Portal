from __future__ import annotations

from collections.abc import Callable
import io
import json

from PySide6.QtCore import QBuffer, QRect, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PIL import Image, ImageSequence, ImageQt

from portal.core.aole_archive import AOLEArchive
from portal.core.layer import Layer
from portal.core.layer_manager import LayerManager


DEFAULT_TOTAL_FRAMES = 1
DEFAULT_PLAYBACK_FPS = 12.0
DEFAULT_PLAYBACK_LOOP_START = 0
DEFAULT_PLAYBACK_LOOP_END = 12


class Document:
    """Lightweight document model backed by a single layer stack."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.layer_manager = LayerManager(width, height)
        self.layer_manager.set_document(self)
        self._layer_manager_listeners: list[Callable[[LayerManager], None]] = []
        self.file_path: str | None = None
        self.ai_output_rect = QRect(
            0,
            0,
            max(1, int(width)),
            max(1, int(height)),
        )
        self.playback_total_frames = self.normalize_playback_total_frames(
            DEFAULT_TOTAL_FRAMES
        )
        self.playback_fps = self.normalize_playback_fps(DEFAULT_PLAYBACK_FPS)
        self.set_playback_loop_range(
            DEFAULT_PLAYBACK_LOOP_START, DEFAULT_PLAYBACK_LOOP_END
        )
        self._notify_layer_manager_changed()

    # ------------------------------------------------------------------
    # Layer manager notifications
    # ------------------------------------------------------------------
    def add_layer_manager_listener(
        self,
        callback: Callable[[LayerManager], None],
        *,
        invoke_immediately: bool = True,
    ) -> Callable[[], None]:
        """Register *callback* to be notified when the layer manager changes."""

        self._layer_manager_listeners.append(callback)
        if invoke_immediately:
            callback(self.layer_manager)

        def remove() -> None:
            try:
                self._layer_manager_listeners.remove(callback)
            except ValueError:
                pass

        return remove

    def remove_layer_manager_listener(
        self, callback: Callable[[LayerManager], None]
    ) -> None:
        try:
            self._layer_manager_listeners.remove(callback)
        except ValueError:
            pass

    def _notify_layer_manager_changed(self) -> None:
        for callback in list(self._layer_manager_listeners):
            callback(self.layer_manager)

    # ------------------------------------------------------------------
    # Cloning
    # ------------------------------------------------------------------
    def clone(self) -> "Document":
        duplicate = Document(self.width, self.height)
        duplicate.layer_manager = self.layer_manager.clone(deep_copy=True)
        duplicate.layer_manager.set_document(duplicate)
        duplicate.ai_output_rect = duplicate._normalize_ai_output_rect(
            self.ai_output_rect
        )
        duplicate.set_playback_total_frames(self.playback_total_frames)
        duplicate.set_playback_fps(self.playback_fps)
        duplicate.set_playback_loop_range(
            getattr(self, "playback_loop_start", DEFAULT_PLAYBACK_LOOP_START),
            getattr(self, "playback_loop_end", DEFAULT_PLAYBACK_LOOP_END),
        )
        duplicate._notify_layer_manager_changed()
        return duplicate

    # ------------------------------------------------------------------
    # Playback metadata stubs (retained for UI compatibility)
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_playback_total_frames(frame_count: object) -> int:
        try:
            value = int(frame_count)
        except (TypeError, ValueError):
            value = DEFAULT_TOTAL_FRAMES
        if value < 1:
            value = DEFAULT_TOTAL_FRAMES
        return value

    def set_playback_total_frames(self, frame_count: object) -> int:
        normalized = self.normalize_playback_total_frames(frame_count)
        self.playback_total_frames = normalized
        return normalized

    @staticmethod
    def normalize_playback_fps(value: object) -> float:
        try:
            fps_value = float(value)
        except (TypeError, ValueError):
            fps_value = DEFAULT_PLAYBACK_FPS
        if fps_value <= 0:
            fps_value = DEFAULT_PLAYBACK_FPS
        return fps_value

    def set_playback_fps(self, fps: object) -> float:
        normalized = self.normalize_playback_fps(fps)
        self.playback_fps = normalized
        return normalized

    def set_playback_loop_range(self, start: object, end: object) -> tuple[int, int]:
        if start is None:
            return
        
        if end <= start:
            end = start + 1
        self.playback_loop_start = start
        self.playback_loop_end = end
        return start, end

    def get_playback_loop_range(self) -> tuple[int, int]:
        return self.playback_loop_start, self.playback_loop_end

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def render(self, frame: int | None = None) -> QImage:
        """Composite visible layers for the requested frame (or current frame)."""

        final_image = QImage(
            QSize(max(1, int(self.width)), max(1, int(self.height))),
            QImage.Format_ARGB32,
        )
        final_image.fill(Qt.transparent)

        layer_manager = getattr(self, "layer_manager", None)
        if frame is None:
            frame = getattr(layer_manager, "current_frame", 0)

        painter = QPainter(final_image)
        for layer in list(getattr(layer_manager, "layers", [])):
            if not getattr(layer, "visible", False):
                continue

            frame_image = self._image_for_layer_frame(layer, frame)

            painter.setOpacity(getattr(layer, "opacity", 1.0))
            painter.drawImage(0, 0, frame_image)
        painter.end()
        return final_image

    def render_except(self, layer_to_exclude: Layer) -> QImage:
        """Render the document while skipping ``layer_to_exclude``."""

        final_image = QImage(
            QSize(max(1, int(self.width)), max(1, int(self.height))),
            QImage.Format_ARGB32,
        )
        final_image.fill(Qt.transparent)

        painter = QPainter(final_image)
        for layer in self.layer_manager.layers:
            if layer is layer_to_exclude or not layer.visible:
                continue
            painter.setOpacity(layer.opacity)
            painter.drawImage(0, 0, layer.image)
        painter.end()
        return final_image

    def _image_for_layer_frame(self, layer: Layer, frame: int) -> QImage | None:
        if layer is None:
            return None

        keys = getattr(layer, "keys", None)
        if not keys:
            image = getattr(layer, "image", None)
            return image if isinstance(image, QImage) else None

        try:
            index = layer._index_for_frame(frame)
        except Exception:
            try:
                index = layer.active_key_index
            except Exception:
                index = 0

        try:
            key = keys[index]
        except Exception:
            return None

        image = getattr(key, "image", None)
        if isinstance(image, QImage):
            return image
        return None

    # ------------------------------------------------------------------
    # AI output rectangle helpers
    # ------------------------------------------------------------------
    def get_ai_output_rect(self) -> QRect:
        return QRect(self._normalize_ai_output_rect(self.ai_output_rect))

    def set_ai_output_rect(self, rect: QRect | None) -> QRect:
        normalized = self._normalize_ai_output_rect(rect)
        if normalized == self.ai_output_rect:
            return QRect(self.ai_output_rect)
        self.ai_output_rect = normalized
        return QRect(self.ai_output_rect)

    def reset_ai_output_rect(self) -> QRect:
        self.ai_output_rect = QRect(
            0,
            0,
            max(1, int(self.width)),
            max(1, int(self.height)),
        )
        return QRect(self.ai_output_rect)

    def ensure_ai_output_rect(self) -> QRect:
        self.ai_output_rect = self._normalize_ai_output_rect(self.ai_output_rect)
        return QRect(self.ai_output_rect)

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

    # ------------------------------------------------------------------
    # Document IO
    # ------------------------------------------------------------------
    def save_tiff(self, filename: str) -> None:
        images = []
        for layer in self.layer_manager.layers:
            pil_image = ImageQt.fromqimage(layer.image)
            pil_image.info["layer_name"] = layer.name
            pil_image.info["layer_visible"] = str(layer.visible)
            pil_image.info["layer_opacity"] = str(layer.opacity)
            pil_image.info["layer_onion_skin"] = str(layer.onion_skin_enabled)
            images.append(pil_image)

        if images:
            layer_properties = [
                layer.get_properties() for layer in self.layer_manager.layers
            ]
            images[0].save(
                filename,
                save_all=True,
                append_images=images[1:],
                format="TIFF",
                compression="tiff_lzw",
                description=json.dumps(layer_properties),
            )

        self.file_path = filename

    @staticmethod
    def load_tiff(filename: str) -> "Document":
        with Image.open(filename) as img:
            width, height = img.size
            doc = Document(width, height)
            doc.layer_manager.layers = []

            try:
                layer_properties = json.loads(img.tag_v2[270])
            except (KeyError, json.JSONDecodeError):
                layer_properties = None

            for i, page in enumerate(ImageSequence.Iterator(img)):
                qimage = ImageQt.toqimage(page.convert("RGBA"))

                if layer_properties and i < len(layer_properties):
                    props = layer_properties[i]
                    layer = Layer.from_qimage(
                        qimage, props.get("name", f"Layer {i + 1}")
                    )
                    layer.visible = props.get("visible", True)
                    layer.opacity = props.get("opacity", 1.0)
                    layer.onion_skin_enabled = props.get(
                        "onion_skin_enabled", False
                    )
                else:
                    layer = Layer.from_qimage(qimage, f"Layer {i + 1}")

                doc.layer_manager.layers.append(layer)

            if doc.layer_manager.layers:
                doc.layer_manager.active_layer_index = len(
                    doc.layer_manager.layers
                ) - 1
            doc.layer_manager.layer_structure_changed.emit()
            doc.layer_manager.set_document(doc)

        doc.file_path = filename
        return doc

    def save_aole(self, filename: str) -> None:
        AOLEArchive.save(self, filename)
        self.file_path = filename

    @classmethod
    def load_aole(cls, filename: str) -> "Document":
        document = AOLEArchive.load(cls, filename)
        document.file_path = filename
        return document

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def resize(self, width: int, height: int, interpolation: str) -> None:
        self.width = width
        self.height = height
        self.layer_manager.width = width
        self.layer_manager.height = height

        if interpolation == "Smooth":
            mode = Qt.SmoothTransformation
        else:
            mode = Qt.FastTransformation

        for layer in self.layer_manager.layers:
            layer.image = layer.image.scaled(
                QSize(width, height), Qt.IgnoreAspectRatio, mode
            )
            layer.on_image_change.emit()

        self.ensure_ai_output_rect()

    def crop(self, rect: QRect) -> None:
        rect = rect.normalized()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        new_width = rect.width()
        new_height = rect.height()

        self.width = new_width
        self.height = new_height
        self.layer_manager.width = new_width
        self.layer_manager.height = new_height

        for layer in self.layer_manager.layers:
            layer.image = layer.image.copy(rect)
            layer.on_image_change.emit()

        self.ensure_ai_output_rect()

    # ------------------------------------------------------------------
    # Clipboard helpers
    # ------------------------------------------------------------------
    @staticmethod
    def qimage_to_pil(qimage: QImage) -> Image.Image:
        return ImageQt.fromqimage(qimage)

    def get_current_image_for_ai(self) -> Image.Image | None:
        q_image = self.render()
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        try:
            return Image.open(io.BytesIO(buffer.data()))
        except Exception:
            return None

    def add_new_layer_with_image(self, image) -> None:
        self.layer_manager.add_layer_with_image(image, name="AI Generated Layer")

    def add_layer_from_clipboard(self, q_image: QImage) -> None:
        if q_image.width() > self.width or q_image.height() > self.height:
            q_image = q_image.scaled(
                self.width,
                self.height,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )

        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        q_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))

        self.layer_manager.add_layer_with_image(pil_image, name="Pasted Layer")

