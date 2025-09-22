from __future__ import annotations

import json
import os
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
import zipfile

from PySide6.QtCore import QBuffer
from PySide6.QtGui import QImage

from portal.core.layer import Layer


class ArchiveFormatError(ValueError):
    """Raised when an AOLE archive cannot be parsed."""


@dataclass
class _LayerRecord:
    uid: int
    name: str
    visible: bool
    opacity: float
    onion_skin_enabled: bool
    image_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "uid": self.uid,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "onion_skin_enabled": self.onion_skin_enabled,
            "image": self.image_path,
        }


class AOLEArchive:
    """Serialize and deserialize Pixel Portal documents without animation."""

    METADATA_FILE = "document.json"
    IMAGE_ROOT = PurePosixPath("layers")
    VERSION = 2

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

        metadata: dict[str, object] = {
            "version": self._version,
            "width": document.width,
            "height": document.height,
            "layers": [],
            "active_layer_index": layer_manager.active_layer_index,
            "playback_total_frames": getattr(document, "playback_total_frames", 1),
            "playback_fps": getattr(document, "playback_fps", 12.0),
        }

        for index, layer in enumerate(layer_manager.layers):
            record = self._serialize_layer(layer, index)
            metadata["layers"].append(record.to_dict())

        return metadata

    def _serialize_layer(self, layer: Layer, index: int) -> _LayerRecord:
        image_bytes = self._encode_layer_image(layer)
        image_filename = f"{index}_{layer.uid}.png"
        image_path = self._image_root / image_filename
        self._binary_entries[str(image_path)] = image_bytes
        return _LayerRecord(
            uid=layer.uid,
            name=layer.name,
            visible=layer.visible,
            opacity=layer.opacity,
            onion_skin_enabled=getattr(layer, "onion_skin_enabled", False),
            image_path=str(image_path),
        )

    @staticmethod
    def _encode_layer_image(layer: Layer) -> bytes:
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        layer.image.save(buffer, "PNG")
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
                layer = self._restore_layer(layer_info, archive)
                document.layer_manager.layers.append(layer)

            active_index = int(metadata.get("active_layer_index", -1))
            if document.layer_manager.layers:
                active_index = max(0, min(active_index, len(document.layer_manager.layers) - 1))
            document.layer_manager.active_layer_index = active_index
            document.layer_manager.layer_structure_changed.emit()
            document.layer_manager.set_document(document)

            document.set_playback_total_frames(metadata.get("playback_total_frames"))
            document.set_playback_fps(metadata.get("playback_fps"))

        return document

    def _restore_layer(self, info: dict[str, object], archive: zipfile.ZipFile) -> Layer:
        image_path = info.get("image")
        if not isinstance(image_path, str):
            raise ArchiveFormatError("Layer image path missing")

        try:
            image_bytes = archive.read(image_path)
        except KeyError as exc:  # pragma: no cover - corrupted archive
            raise ArchiveFormatError(f"Missing layer image: {image_path}") from exc

        image = QImage()
        image.loadFromData(image_bytes, "PNG")
        if image.isNull():
            raise ArchiveFormatError(f"Layer image is invalid: {image_path}")

        name = info.get("name") or "Layer"
        layer = Layer(image.width(), image.height(), str(name))
        layer.image = image
        layer.visible = bool(info.get("visible", True))
        layer.opacity = float(info.get("opacity", 1.0))
        layer.onion_skin_enabled = bool(info.get("onion_skin_enabled", False))

        uid = info.get("uid")
        if isinstance(uid, int):
            layer.uid = uid

        return layer


from typing import TYPE_CHECKING  # noqa: E402  # circular import safe-guard

if TYPE_CHECKING:  # pragma: no cover
    from portal.core.document import Document

