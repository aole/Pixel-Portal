from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import io
import json
import os
import zipfile

from PySide6.QtCore import QBuffer, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PIL import Image, ImageSequence, ImageQt

from portal.core.frame import Frame
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
                for position, layer in enumerate(new_manager.layers):
                    if layer.uid == previous_active_uid:
                        new_manager.select_layer(position)
                        break
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
                else:
                    layer = Layer.from_qimage(qimage, f"Layer {i+1}")
                doc.layer_manager.layers.append(layer)
                doc.register_layer(layer, len(doc.layer_manager.layers) - 1)

        doc.file_path = filename
        return doc

    def save_aole(self, filename: str) -> None:
        """Persist the entire document, including frames and layers, to an AOLE archive."""

        frame_manager = self.frame_manager
        metadata: dict[str, object] = {
            "version": 1,
            "width": self.width,
            "height": self.height,
            "frames": [],
            "frame_manager": {
                "active_frame_index": frame_manager.active_frame_index,
                "frame_markers": sorted(frame_manager.frame_markers),
                "layer_keys": {
                    str(layer_uid): sorted(frames)
                    for layer_uid, frames in frame_manager.layer_keys.items()
                },
            },
        }

        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

        with zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for frame_index, frame in enumerate(frame_manager.frames):
                layer_manager = frame.layer_manager
                frame_entry: dict[str, object] = {
                    "active_layer_index": layer_manager.active_layer_index,
                    "layers": [],
                }
                for layer_position, layer in enumerate(layer_manager.layers):
                    image_buffer = QBuffer()
                    image_buffer.open(QBuffer.ReadWrite)
                    layer.image.save(image_buffer, "PNG")
                    image_path = f"frames/{frame_index}/layers/{layer.uid}_{layer_position}.png"
                    archive.writestr(image_path, bytes(image_buffer.data()))
                    layer_entry = {
                        "uid": layer.uid,
                        "name": layer.name,
                        "visible": layer.visible,
                        "opacity": layer.opacity,
                        "image": image_path,
                    }
                    frame_entry["layers"].append(layer_entry)
                metadata["frames"].append(frame_entry)

            archive.writestr(
                "document.json",
                json.dumps(metadata, indent=2).encode("utf-8"),
            )

        self.file_path = filename

    @classmethod
    def load_aole(cls, filename: str) -> "Document":
        """Load a full document, including animation data, from an AOLE archive."""

        try:
            with zipfile.ZipFile(filename, "r") as archive:
                try:
                    metadata_bytes = archive.read("document.json")
                except KeyError as exc:
                    raise ValueError("Document metadata is missing from archive") from exc
                metadata = json.loads(metadata_bytes.decode("utf-8"))

                width = int(metadata.get("width", 0))
                height = int(metadata.get("height", 0))
                if width <= 0 or height <= 0:
                    raise ValueError("Invalid document dimensions in archive")

                frame_manager = FrameManager(width, height, frame_count=0)
                frames_data = metadata.get("frames", [])
                for frame_data in frames_data:
                    frame = Frame(width, height, create_background=False)
                    layer_manager = frame.layer_manager
                    layer_manager.layers = []
                    try:
                        active_layer_index = int(frame_data.get("active_layer_index", -1))
                    except (TypeError, ValueError):
                        active_layer_index = -1
                    layers_data = frame_data.get("layers", [])
                    for layer_data in layers_data:
                        image_path = layer_data.get("image")
                        if not image_path:
                            continue
                        try:
                            image_bytes = archive.read(image_path)
                        except KeyError as exc:
                            raise ValueError(f"Missing layer image '{image_path}'") from exc
                        qimage = QImage()
                        if not qimage.loadFromData(image_bytes, "PNG"):
                            raise ValueError(f"Layer image '{image_path}' could not be read")
                        name = layer_data.get("name") or f"Layer {len(layer_manager.layers) + 1}"
                        layer = Layer.from_qimage(qimage, name)
                        try:
                            layer.uid = int(layer_data.get("uid", layer.uid))
                        except (TypeError, ValueError):
                            layer.uid = layer.uid
                        visible_value = layer_data.get("visible", True)
                        if isinstance(visible_value, str):
                            layer.visible = visible_value.lower() == "true"
                        else:
                            layer.visible = bool(visible_value)
                        try:
                            layer.opacity = float(layer_data.get("opacity", 1.0))
                        except (TypeError, ValueError):
                            layer.opacity = 1.0
                        layer_manager.layers.append(layer)
                    if layer_manager.layers:
                        if active_layer_index < 0 or active_layer_index >= len(layer_manager.layers):
                            active_layer_index = 0
                    layer_manager.active_layer_index = active_layer_index
                    frame_manager.frames.append(frame)

                if not frame_manager.frames:
                    raise ValueError("Document archive does not contain any frames")

                frame_meta = metadata.get("frame_manager", {})
                raw_layer_keys = frame_meta.get("layer_keys", {})
                layer_keys: dict[int, set[int]] = {}
                for uid_str, frames in raw_layer_keys.items():
                    try:
                        layer_uid = int(uid_str)
                    except (TypeError, ValueError):
                        continue
                    normalized: set[int] = set()
                    for value in frames:
                        try:
                            index = int(value)
                        except (TypeError, ValueError):
                            continue
                        if index >= 0:
                            normalized.add(index)
                    if not normalized and frame_manager.frames:
                        normalized = {0}
                    layer_keys[layer_uid] = normalized

                for frame in frame_manager.frames:
                    for layer in frame.layer_manager.layers:
                        if layer.uid not in layer_keys:
                            layer_keys[layer.uid] = {0} if frame_manager.frames else set()

                frame_manager.layer_keys = layer_keys

                markers = frame_meta.get("frame_markers") or []
                normalized_markers: set[int] = set()
                for marker in markers:
                    try:
                        normalized_markers.add(int(marker))
                    except (TypeError, ValueError):
                        continue
                frame_manager.frame_markers = normalized_markers
                if not frame_manager.frame_markers and frame_manager.frames:
                    frame_manager.frame_markers = {0}

                try:
                    active_index = int(frame_meta.get("active_frame_index", 0))
                except (TypeError, ValueError):
                    active_index = 0
                if frame_manager.frames:
                    active_index = max(0, min(active_index, len(frame_manager.frames) - 1))
                else:
                    active_index = -1
                frame_manager.active_frame_index = active_index

                if frame_manager.frames:
                    rebind = getattr(frame_manager, "_rebind_all_layers", None)
                    if callable(rebind):
                        rebind()

        except zipfile.BadZipFile as exc:
            raise ValueError("The provided file is not a valid AOLE archive") from exc

        document = cls(width, height)
        document.apply_frame_manager_snapshot(frame_manager)

        document.file_path = filename

        max_uid = 0
        for frame in document.frame_manager.frames:
            for layer in frame.layer_manager.layers:
                if layer.uid > max_uid:
                    max_uid = layer.uid
        if max_uid > Layer._uid_counter:
            Layer._uid_counter = max_uid

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
