from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import zipfile

from PySide6.QtCore import QBuffer
from PySide6.QtGui import QImage

from portal.core.key import Key
from portal.core.layer import Layer


class ArchiveFormatError(ValueError):
    """Raised when an AOLE archive cannot be parsed."""


@dataclass
class _KeyRecord:
    frame: int
    image_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "image": self.image_path,
        }


@dataclass
class _LayerRecord:
    uid: int
    name: str
    visible: bool
    opacity: float
    onion_skin_enabled: bool
    image_path: str
    keys: list[_KeyRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = {
            "uid": self.uid,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "onion_skin_enabled": self.onion_skin_enabled,
            "image": self.image_path,
        }
        if self.keys:
            data["keys"] = [key.to_dict() for key in self.keys]
        return data


class AOLEArchive:
    """Serialize and deserialize Pixel Portal documents without animation."""

    METADATA_FILE = "document.json"
    IMAGE_ROOT = PurePosixPath("layers")
    VERSION = 3

    @classmethod
    def save(cls, document: "Document", filename: str) -> None:
        writer = _ArchiveWriter(document, cls.IMAGE_ROOT, cls.METADATA_FILE, cls.VERSION)
        writer.write(filename)

    @classmethod
    def load(cls, document_cls: type["Document"], filename: str) -> "Document":
        reader = _ArchiveReader(document_cls, cls.METADATA_FILE)
        return reader.read(filename)


class _ArchiveWriter:
    def __init__(
        self,
        document: "Document",
        image_root: PurePosixPath,
        metadata_file: str,
        version: int,
    ) -> None:
        self._document = document
        self._image_root = image_root
        self._metadata_file = metadata_file
        self._version = version
        self._binary_entries: dict[str, bytes] = {}

    def write(self, filename: str) -> None:
        metadata = self._build_metadata()

        target_dir = os.path.dirname(filename) or "."
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, payload in sorted(self._binary_entries.items()):
                archive.writestr(path, payload)
            archive.writestr(
                self._metadata_file,
                json.dumps(metadata, indent=2).encode("utf-8"),
            )

    def _build_metadata(self) -> dict[str, object]:
        document = self._document
        layer_manager = document.layer_manager

        loop_start, loop_end = document.get_playback_loop_range()

        metadata: dict[str, object] = {
            "version": self._version,
            "width": document.width,
            "height": document.height,
            "layers": [],
            "active_layer_index": layer_manager.active_layer_index,
            "playback_total_frames": getattr(document, "playback_total_frames", 1),
            "playback_fps": getattr(document, "playback_fps", 12.0),
            "playback_loop_start": loop_start,
            "playback_loop_end": loop_end,
        }

        for index, layer in enumerate(layer_manager.layers):
            record = self._serialize_layer(layer, index)
            metadata["layers"].append(record.to_dict())

        return metadata

    def _serialize_layer(self, layer: Layer, index: int) -> _LayerRecord:
        legacy_filename = f"{index}_{layer.uid}.png"
        legacy_path = self._image_root / legacy_filename
        legacy_path_str = str(legacy_path)

        active_key = layer.active_key

        sorted_keys = sorted(
            list(getattr(layer, "keys", []) or []),
            key=lambda key: getattr(key, "frame_number", 0),
        )

        key_records: list[_KeyRecord] = []

        if sorted_keys:
            for position, key in enumerate(sorted_keys):
                frame_number = getattr(key, "frame_number", 0)

                if key is active_key or (active_key is None and position == 0):
                    key_path_str = legacy_path_str
                else:
                    key_path = self._image_root / f"{index}_{layer.uid}_key{position}.png"
                    key_path_str = str(key_path)

                self._binary_entries[key_path_str] = self._encode_key_image(key)
                key_records.append(_KeyRecord(frame=frame_number, image_path=key_path_str))
        else:
            self._binary_entries[legacy_path_str] = self._encode_layer_image(layer)

        return _LayerRecord(
            uid=layer.uid,
            name=layer.name,
            visible=layer.visible,
            opacity=layer.opacity,
            onion_skin_enabled=getattr(layer, "onion_skin_enabled", False),
            image_path=legacy_path_str,
            keys=key_records,
        )

    @staticmethod
    def _encode_layer_image(layer: Layer) -> bytes:
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        layer.image.save(buffer, "PNG")
        return bytes(buffer.data())

    @staticmethod
    def _encode_key_image(key: Key) -> bytes:
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        key.image.save(buffer, "PNG")
        return bytes(buffer.data())


class _ArchiveReader:
    def __init__(self, document_cls: type["Document"], metadata_file: str) -> None:
        self._document_cls = document_cls
        self._metadata_file = metadata_file

    def read(self, filename: str) -> "Document":
        with zipfile.ZipFile(filename, "r") as archive:
            try:
                metadata_bytes = archive.read(self._metadata_file)
            except KeyError as exc:  # pragma: no cover - corrupted archive
                raise ArchiveFormatError("Missing metadata file") from exc

            try:
                metadata = json.loads(metadata_bytes.decode("utf-8"))
            except json.JSONDecodeError as exc:  # pragma: no cover - corrupted archive
                raise ArchiveFormatError("Metadata is not valid JSON") from exc

            width = int(metadata.get("width", 0))
            height = int(metadata.get("height", 0))
            if width <= 0 or height <= 0:
                raise ArchiveFormatError("Document dimensions are invalid")

            document = self._document_cls(width, height)
            document.layer_manager.layers = []

            for layer_info in metadata.get("layers", []):
                layer = self._restore_layer(layer_info, archive, document.layer_manager)
                document.layer_manager.layers.append(layer)

            active_index = int(metadata.get("active_layer_index", -1))
            if document.layer_manager.layers:
                active_index = max(0, min(active_index, len(document.layer_manager.layers) - 1))
            document.layer_manager.active_layer_index = active_index
            document.layer_manager.layer_structure_changed.emit()
            document.layer_manager.set_document(document)

            document.set_playback_total_frames(metadata.get("playback_total_frames"))
            document.set_playback_fps(metadata.get("playback_fps"))
            document.set_playback_loop_range(
                metadata.get("playback_loop_start"),
                metadata.get("playback_loop_end"),
            )

        return document

    def _restore_layer(
        self,
        info: dict[str, object],
        archive: zipfile.ZipFile,
        layer_manager: "LayerManager",
    ) -> Layer:
        image_path = info.get("image")
        if not isinstance(image_path, str):
            raise ArchiveFormatError("Layer image path missing")

        image = self._load_image(archive, image_path)

        name = info.get("name") or "Layer"
        keys: list[Key] = []
        keys_metadata = info.get("keys")

        for entry in keys_metadata:
            key_image_path = entry.get("image")
            key_image = self._load_image(archive, key_image_path)
            frame_number = entry.get("frame")
            key = Key.from_qimage(key_image, frame_number=frame_number)
            keys.append(key)

        keys.sort(key=lambda key: key.frame_number)

        if keys:
            layer = Layer(
                image.width(),
                image.height(),
                str(name),
                layer_manager=layer_manager,
                keys=keys,
            )
        else:
            layer = Layer(
                image.width(),
                image.height(),
                str(name),
                layer_manager=layer_manager,
            )
            layer.image = image

        layer.visible = bool(info.get("visible", True))
        layer.opacity = float(info.get("opacity", 1.0))
        layer.onion_skin_enabled = bool(info.get("onion_skin_enabled", False))

        uid = info.get("uid")
        if isinstance(uid, int):
            layer.uid = uid

        return layer

    def _load_image(self, archive: zipfile.ZipFile, image_path: str) -> QImage:
        try:
            image_bytes = archive.read(image_path)
        except KeyError as exc:  # pragma: no cover - corrupted archive
            raise ArchiveFormatError(f"Missing layer image: {image_path}") from exc

        image = QImage()
        image.loadFromData(image_bytes, "PNG")
        if image.isNull():
            raise ArchiveFormatError(f"Layer image is invalid: {image_path}")
        return image





from typing import TYPE_CHECKING  # noqa: E402  # circular import safe-guard

if TYPE_CHECKING:  # pragma: no cover
    from portal.core.document import Document
    from portal.core.layer_manager import LayerManager

