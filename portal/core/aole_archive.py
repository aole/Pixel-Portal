from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Iterable, Iterator, Mapping
import zipfile

from PySide6.QtCore import QBuffer
from PySide6.QtGui import QImage

from portal.core.animation_player import DEFAULT_TOTAL_FRAMES
from portal.core.frame import Frame
from portal.core.frame_manager import FrameManager
from portal.core.layer import Layer

if TYPE_CHECKING:  # pragma: no cover - circular import safe-guard
    from portal.core.document import Document


class ArchiveFormatError(ValueError):
    """Raised when an AOLE archive cannot be parsed."""


@dataclass
class _LayerRecord:
    uid: int
    name: str
    visible: bool
    opacity: float
    image_path: str
    onion_skin_enabled: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "uid": self.uid,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "image": self.image_path,
            "onion_skin_enabled": self.onion_skin_enabled,
        }


@dataclass
class _FrameRecord:
    layers: list[_LayerRecord]
    active_layer_index: int

    def to_dict(self) -> dict[str, object]:
        return {
            "active_layer_index": self.active_layer_index,
            "layers": [layer.to_dict() for layer in self.layers],
        }


class AOLEArchive:
    """Serialize and deserialize Pixel Portal documents."""

    METADATA_FILE = "document.json"
    IMAGE_ROOT = PurePosixPath("frames")
    VERSION = 1

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
        frame_manager = document.frame_manager
        metadata: dict[str, object] = {
            "version": self._version,
            "width": document.width,
            "height": document.height,
            "frames": [],
            "playback_total_frames": self._normalize_playback_total_frames(
                getattr(document, "playback_total_frames", None)
            ),
            "frame_manager": {
                "active_frame_index": frame_manager.active_frame_index,
                "frame_markers": sorted(frame_manager.frame_markers),
                "layer_keys": {
                    str(layer_uid): sorted(self._normalize_frame_indices(indices))
                    for layer_uid, indices in frame_manager.layer_keys.items()
                },
            },
        }

        for frame_index, frame in enumerate(frame_manager.frames):
            frame_record = self._serialize_frame(frame, frame_index)
            metadata["frames"].append(frame_record.to_dict())

        return metadata

    def _serialize_frame(self, frame: Frame, frame_index: int) -> _FrameRecord:
        layer_manager = frame.layer_manager
        layer_records: list[_LayerRecord] = []
        for layer_index, layer in enumerate(layer_manager.layers):
            image_bytes = self._encode_layer_image(layer)
            image_filename = f"{layer.uid}_{layer_index}.png"
            image_path = self._image_root / str(frame_index) / "layers" / image_filename
            self._binary_entries[str(image_path)] = image_bytes
            record = _LayerRecord(
                uid=layer.uid,
                name=layer.name,
                visible=layer.visible,
                opacity=layer.opacity,
                image_path=str(image_path),
                onion_skin_enabled=getattr(layer, "onion_skin_enabled", False),
            )
            layer_records.append(record)

        active_index = layer_manager.active_layer_index
        if layer_records:
            active_index = max(0, min(active_index, len(layer_records) - 1))
        else:
            active_index = -1

        return _FrameRecord(layer_records, active_index)

    @staticmethod
    def _encode_layer_image(layer: Layer) -> bytes:
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        layer.image.save(buffer, "PNG")
        return bytes(buffer.data())

    @staticmethod
    def _normalize_frame_indices(indices: Iterable[int]) -> Iterator[int]:
        for value in indices:
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if index >= 0:
                yield index

    @staticmethod
    def _normalize_playback_total_frames(value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = DEFAULT_TOTAL_FRAMES
        if normalized < 1:
            normalized = DEFAULT_TOTAL_FRAMES
        return normalized


class _ArchiveReader:
    def __init__(self, document_cls: type["Document"], metadata_file: str) -> None:
        self._document_cls = document_cls
        self._metadata_file = metadata_file

    def read(self, filename: str) -> "Document":
        try:
            with zipfile.ZipFile(filename, "r") as archive:
                metadata = self._load_metadata(archive)
                frame_manager = self._restore_frame_manager(metadata, archive)
        except zipfile.BadZipFile as exc:  # pragma: no cover - zipfile error handling
            raise ArchiveFormatError("The provided file is not a valid AOLE archive") from exc

        width = int(metadata.get("width", 0))
        height = int(metadata.get("height", 0))
        if width <= 0 or height <= 0:
            raise ArchiveFormatError("Invalid document dimensions in archive")

        document = self._document_cls(width, height)
        document.apply_frame_manager_snapshot(frame_manager)
        playback_total = self._extract_playback_total_frames(
            metadata, len(frame_manager.frames)
        )
        setter = getattr(document, "set_playback_total_frames", None)
        if callable(setter):
            setter(playback_total)
        else:
            document.playback_total_frames = playback_total

        self._sync_layer_uid_counter(document)

        return document

    def _load_metadata(self, archive: zipfile.ZipFile) -> dict[str, object]:
        try:
            metadata_bytes = archive.read(self._metadata_file)
        except KeyError as exc:
            raise ArchiveFormatError("Document metadata is missing from archive") from exc

        try:
            return json.loads(metadata_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArchiveFormatError("Document metadata is malformed") from exc

    def _restore_frame_manager(
        self, metadata: Mapping[str, object], archive: zipfile.ZipFile
    ) -> FrameManager:
        width = int(metadata.get("width", 0))
        height = int(metadata.get("height", 0))

        frame_manager = FrameManager(width, height, frame_count=0)

        frames_data = metadata.get("frames", [])
        if not isinstance(frames_data, list):
            raise ArchiveFormatError("Frame list is missing or invalid")

        for frame_index, frame_data in enumerate(frames_data):
            frame = Frame(width, height, create_background=False)
            layer_manager = frame.layer_manager
            layer_manager.layers = []

            layers_data = self._extract_layers(frame_data)
            for layer_position, layer_data in enumerate(layers_data):
                layer = self._restore_layer(archive, layer_data, frame_index, layer_position)
                layer_manager.layers.append(layer)

            active_layer_index = self._normalize_index(
                frame_data.get("active_layer_index"), len(layer_manager.layers)
            )
            layer_manager.active_layer_index = active_layer_index
            frame_manager.frames.append(frame)

        if not frame_manager.frames:
            raise ArchiveFormatError("Document archive does not contain any frames")

        self._apply_frame_manager_metadata(frame_manager, metadata)

        rebind = getattr(frame_manager, "_rebind_all_layers", None)
        if callable(rebind):
            rebind()

        return frame_manager

    def _extract_layers(self, frame_data: Mapping[str, object]) -> list[Mapping[str, object]]:
        layers = frame_data.get("layers", [])
        if not isinstance(layers, list):
            return []
        return [layer for layer in layers if isinstance(layer, Mapping)]

    def _restore_layer(
        self,
        archive: zipfile.ZipFile,
        layer_data: Mapping[str, object],
        frame_index: int,
        layer_position: int,
    ) -> Layer:
        image_path = layer_data.get("image")
        if not image_path:
            raise ArchiveFormatError(
                f"Layer {layer_position} in frame {frame_index} is missing image data"
            )

        try:
            image_bytes = archive.read(str(image_path))
        except KeyError as exc:
            raise ArchiveFormatError(f"Missing layer image '{image_path}'") from exc

        image = QImage()
        if not image.loadFromData(image_bytes, "PNG"):
            raise ArchiveFormatError(f"Layer image '{image_path}' could not be read")

        name = layer_data.get("name") or f"Layer {layer_position + 1}"
        layer = Layer.from_qimage(image, str(name))

        layer.uid = self._coerce_int(layer_data.get("uid"), layer.uid)
        layer.visible = self._coerce_bool(layer_data.get("visible"), True)
        layer.opacity = self._coerce_float(layer_data.get("opacity"), 1.0, minimum=0.0, maximum=1.0)
        layer.onion_skin_enabled = self._coerce_bool(layer_data.get("onion_skin_enabled"), False)

        return layer

    def _apply_frame_manager_metadata(self, frame_manager: FrameManager, metadata: Mapping[str, object]) -> None:
        manager_meta = metadata.get("frame_manager", {})
        if not isinstance(manager_meta, Mapping):
            manager_meta = {}

        frame_count = len(frame_manager.frames)

        raw_active_index = manager_meta.get("active_frame_index")
        frame_manager.active_frame_index = self._normalize_index(raw_active_index, frame_count)

        raw_markers = manager_meta.get("frame_markers", [])
        frame_manager.frame_markers = self._normalize_marker_set(raw_markers, frame_count)

        raw_layer_keys = manager_meta.get("layer_keys", {})
        layer_keys = self._normalize_layer_keys(raw_layer_keys, frame_count, frame_manager)
        frame_manager.layer_keys = layer_keys

    def _normalize_layer_keys(
        self,
        raw_layer_keys: object,
        frame_count: int,
        frame_manager: FrameManager,
    ) -> dict[int, set[int]]:
        if not isinstance(raw_layer_keys, Mapping):
            raw_layer_keys = {}

        valid_layers = {
            layer.uid
            for frame in frame_manager.frames
            for layer in frame.layer_manager.layers
        }

        normalized: dict[int, set[int]] = {}
        for uid_str, frames in raw_layer_keys.items():
            try:
                layer_uid = int(uid_str)
            except (TypeError, ValueError):
                continue
            if layer_uid not in valid_layers:
                continue
            indices = {
                index
                for index in self._iter_frame_indices(frames)
                if 0 <= index < frame_count
            }
            if not indices and frame_count:
                indices = {0}
            normalized[layer_uid] = indices

        if frame_count:
            for uid in valid_layers:
                normalized.setdefault(uid, {0})

        return normalized

    def _normalize_marker_set(self, values: object, frame_count: int) -> set[int]:
        markers = {
            index
            for index in self._iter_frame_indices(values)
            if 0 <= index < frame_count
        }
        if not markers and frame_count:
            markers = {0}
        return markers

    def _iter_frame_indices(self, values: object) -> Iterator[int]:
        if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
            for value in values:
                try:
                    yield int(value)
                except (TypeError, ValueError):
                    continue

    def _normalize_index(self, value: object, count: int) -> int:
        if count <= 0:
            return -1
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = 0
        return max(0, min(index, count - 1))

    def _coerce_int(self, value: object, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _coerce_bool(self, value: object, fallback: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        return fallback

    def _coerce_float(
        self,
        value: object,
        fallback: float,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            result = fallback
        if minimum is not None:
            result = max(minimum, result)
        if maximum is not None:
            result = min(maximum, result)
        return result

    def _extract_playback_total_frames(
        self, metadata: Mapping[str, object], frame_count: int
    ) -> int:
        fallback = max(1, int(frame_count) if frame_count else DEFAULT_TOTAL_FRAMES)
        raw_total = metadata.get("playback_total_frames")
        try:
            total = int(raw_total)
        except (TypeError, ValueError):
            total = fallback
        if total < 1:
            total = fallback
        return total

    def _sync_layer_uid_counter(self, document: "Document") -> None:
        max_uid = 0
        for frame in document.frame_manager.frames:
            for layer in frame.layer_manager.layers:
                max_uid = max(max_uid, layer.uid)
        if max_uid > Layer._uid_counter:
            Layer._uid_counter = max_uid

