import base64
import binascii
import io
import json
import math
import os
from pathlib import Path
from typing import Callable, Iterable
import zlib
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from PIL import Image
from PySide6.QtGui import QImage, QImageReader, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox

from portal.core.document import Document


DEFAULT_PLAYBACK_FPS = 12.0


@dataclass
class AnimationFrameChunk:
    index: int
    image: Image.Image
    repeats: int = 1


@dataclass
class AnimationMetadata:
    version: Optional[int] = None
    frame_repeats: Optional[list[int]] = None
    total_frames: Optional[int] = None
    frame_duration_ms: Optional[int] = None
    fps: Optional[float] = None
    rgba_encoding: Optional[str] = None
    rgba_frames: Optional[list[str]] = None

    @property
    def has_rgba_payload(self) -> bool:
        return bool(self.rgba_frames and self.rgba_encoding == "png+zlib+base64")


class AnimationExportError(RuntimeError):
    """Raised when exporting an animation fails."""


class EmptyAnimationError(AnimationExportError):
    """Raised when no frames are available for export."""


class DocumentService:
    """High level operations for loading, saving, and exporting documents."""

    _OPEN_FILE_FILTERS: tuple[str, ...] = (
        "Pixel Portal Document (*.aole)",
        "All Supported Files (*.aole *.png *.jpg *.bmp *.tif *.tiff)",
        "Image Files (*.png *.jpg *.bmp)",
        "TIFF Files (*.tif *.tiff)",
    )

    _SAVE_FILE_FILTERS: tuple[str, ...] = (
        "Pixel Portal Document (*.aole)",
        "PNG (*.png)",
        "JPEG (*.jpg *.jpeg)",
        "Bitmap (*.bmp)",
        "TIFF (*.tif *.tiff)",
    )

    _FILTER_EXTENSION_HINTS: tuple[tuple[str, str], ...] = (
        ("pixel portal document", ".aole"),
        ("aole", ".aole"),
        ("tiff", ".tiff"),
        ("tif", ".tiff"),
        ("jpeg", ".jpg"),
        ("jpg", ".jpg"),
        ("png", ".png"),
        ("bmp", ".bmp"),
    )

    _RASTER_EXTENSIONS: frozenset[str] = frozenset({
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
    })

    _ARCHIVE_SAVE_HANDLERS: dict[str, Callable[[Document, str], None]] = {
        ".aole": Document.save_aole,
        ".tif": Document.save_tiff,
        ".tiff": Document.save_tiff,
    }

    def __init__(self, app=None):
        self.app = app

    def open_document(self):
        app = self.app
        if app is None:
            return
        if not app.check_for_unsaved_changes():
            return

        file_path, selected_filter = QFileDialog.getOpenFileName(
            self._dialog_parent(),
            "Open Document",
            app.last_directory,
            self._build_filter_string(self._OPEN_FILE_FILTERS),
        )
        if not file_path:
            return

        extension_hint = self._extract_extension_hint(selected_filter)
        document = self._load_document_from_path(file_path, extension_hint)
        if document is None:
            self._show_message(
                QMessageBox.Warning,
                "Unable to open the selected document.",
                "The file appears to be corrupted or in an unsupported format.",
            )
            return

        self._attach_opened_document(document, file_path)

    def open_as_key(self):
        app = self.app
        if app is None:
            return

        _app, document = self._require_document()
        if document is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self._dialog_parent(),
            "Open Image as Key",
            app.last_directory,
            "Image Files (*.png *.jpg *.bmp *.tif *.tiff);;All Files (*)",
        )
        if not file_path:
            return

        image = QImage(file_path)
        if image.isNull():
            return

        self._update_last_directory(file_path)

        paste_key = getattr(app, "paste_key_from_image", None)
        if callable(paste_key):
            paste_key(image)

    def save_document(self):
        app, document = self._require_document()
        if document is None:
            return

        file_path = getattr(document, "file_path", None)
        if not file_path:
            self.save_document_as()
            return

        if not self._save_document_to_path(document, file_path):
            self.save_document_as()
            return

        self._finalize_save(document, file_path)

    def save_document_as(self):
        app, document = self._require_document()
        if document is None:
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self._dialog_parent(),
            "Save Document",
            app.last_directory,
            self._build_filter_string(self._SAVE_FILE_FILTERS),
        )
        if not file_path:
            return

        normalized_path = self._normalize_save_path(file_path, selected_filter)
        if not self._save_document_to_path(document, normalized_path):
            return

        document.file_path = normalized_path
        self._finalize_save(document, normalized_path)

    def _normalize_save_path(self, file_path: str, selected_filter: str | None) -> str:
        base_path = Path(file_path)
        extension = base_path.suffix.lower()
        if extension in self._ARCHIVE_SAVE_HANDLERS or extension in self._RASTER_EXTENSIONS:
            return str(base_path.with_suffix(extension or base_path.suffix))

        filter_extension = self._extract_extension_hint(selected_filter)
        if filter_extension:
            extension = filter_extension

        if not extension:
            extension = ".png"

        if extension == ".jpeg":
            extension = ".jpg"

        return str(base_path.with_suffix(extension))

    def _save_document_to_path(self, document: Document, file_path: str) -> bool:
        extension = Path(file_path).suffix.lower()
        handler = self._ARCHIVE_SAVE_HANDLERS.get(extension)
        if handler is not None:
            try:
                handler(document, file_path)
            except (OSError, ValueError, RuntimeError) as exc:
                self._show_message(
                    QMessageBox.Critical,
                    "Failed to save document.",
                    str(exc),
                )
                return False
            return True

        if extension in self._RASTER_EXTENSIONS:
            image = document.render()
            if image.isNull():
                self._show_message(
                    QMessageBox.Critical,
                    "Failed to save document.",
                    "The document could not be rendered for saving.",
                )
                return False
            if image.save(file_path):
                return True
            self._show_message(
                QMessageBox.Critical,
                "Failed to save document.",
                "Qt was unable to write the image to disk.",
            )
            return False

        self._show_message(
            QMessageBox.Critical,
            "Unsupported file type.",
            f"Pixel Portal cannot save files with the '{extension or 'unknown'}' extension.",
        )
        return False

    def _finalize_save(self, document: Document, file_path: str) -> None:
        app = self.app
        if document is not None:
            document.file_path = file_path

        self._update_last_directory(file_path)

        if app is None:
            return

        setattr(app, "is_dirty", False)
        updater = getattr(app, "update_main_window_title", None)
        if callable(updater):
            updater()

    @staticmethod
    def _build_filter_string(filters: Iterable[str]) -> str:
        return ";;".join(filters)

    def _extract_extension_hint(self, selected_filter: str | None) -> str | None:
        if not selected_filter:
            return None
        lowered = selected_filter.lower()
        for token, extension in self._FILTER_EXTENSION_HINTS:
            if token in lowered:
                return extension
        return None

    def _load_document_from_path(
        self, file_path: str, extension_hint: str | None
    ) -> Document | None:
        extension = (extension_hint or Path(file_path).suffix).lower()
        try:
            if extension == ".aole":
                return Document.load_aole(file_path)
            if extension in {".tif", ".tiff"}:
                return Document.load_tiff(file_path)
        except (ValueError, OSError, json.JSONDecodeError):
            return None

        image = QImage(file_path)
        if image.isNull():
            return None

        document = Document(image.width(), image.height())
        document.layer_manager.layers[0].image = image
        return document

    def _attach_opened_document(self, document: Document, file_path: str) -> None:
        app = self.app
        document.file_path = file_path
        self._update_last_directory(file_path)

        if app is None:
            return

        attach = getattr(app, "attach_document", None)
        if callable(attach):
            attach(document)

        undo_manager = getattr(app, "undo_manager", None)
        if hasattr(undo_manager, "clear"):
            undo_manager.clear()

        if hasattr(app, "is_dirty"):
            app.is_dirty = False

        for signal_name in ("undo_stack_changed", "document_changed"):
            signal = getattr(app, signal_name, None)
            if hasattr(signal, "emit"):
                signal.emit()

        main_window = getattr(app, "main_window", None)
        canvas = getattr(main_window, "canvas", None) if main_window else None
        if hasattr(canvas, "set_initial_zoom"):
            canvas.set_initial_zoom()

        updater = getattr(app, "update_main_window_title", None)
        if callable(updater):
            updater()

    def _require_document(self) -> tuple[object | None, Document | None]:
        app = self.app
        document = getattr(app, "document", None) if app is not None else None
        return app, document

    def _dialog_parent(self):
        app = self.app
        return getattr(app, "main_window", None) if app is not None else None

    def _update_last_directory(self, reference_path: str) -> None:
        app = self.app
        if app is None:
            return

        directory = os.path.dirname(reference_path)
        if not directory:
            return

        try:
            app.last_directory = directory
        except AttributeError:
            return

        config = getattr(app, "config", None)
        if config is None:
            return

        try:
            has_section = getattr(config, "has_section", None)
            if callable(has_section) and not config.has_section('General'):
                config.add_section('General')
            config.set('General', 'last_directory', directory)
        except (AttributeError, TypeError, ValueError):
            pass

    def _show_message(
        self,
        icon: QMessageBox.Icon,
        text: str,
        informative_text: str = "",
    ) -> None:
        message_box = QMessageBox(self._dialog_parent())
        message_box.setIcon(icon)
        message_box.setText(text)
        if informative_text:
            message_box.setInformativeText(informative_text)
        message_box.exec()

    def export_animation(self):
        app = self.app
        if app is None:
            return

        document = getattr(app, "document", None)
        if document is None:
            return

        frame_manager = getattr(document, "frame_manager", None)
        if frame_manager is None or not getattr(frame_manager, "frames", None):
            parent = getattr(app, "main_window", None)
            QMessageBox.information(
                parent,
                "Export Animation",
                "The current document does not contain any animation frames to export.",
            )
            return

        parent = getattr(app, "main_window", None)
        file_path, selected_filter = QFileDialog.getSaveFileName(
            parent,
            "Export Animation",
            app.last_directory,
            "Animated GIF (*.gif);;Animated PNG (*.png *.apng);;Animated WebP (*.webp)",
        )
        if not file_path:
            return

        file_path, format_name = self._resolve_animation_export_path(file_path, selected_filter)

        export_directory = os.path.dirname(file_path)
        if export_directory:
            app.last_directory = export_directory
            app.config.set("General", "last_directory", app.last_directory)

        total_frames, fps_value = self._resolve_playback_state(app, frame_manager)

        try:
            self._export_animation_file(
                frame_manager=frame_manager,
                file_path=file_path,
                format_name=format_name,
                total_frames=total_frames,
                fps_value=fps_value,
            )
        except EmptyAnimationError:
            QMessageBox.information(
                parent,
                "Export Animation",
                "No frames are available to export for the current animation.",
            )
        except AnimationExportError as exc:
            QMessageBox.critical(
                parent,
                "Export Animation",
                f"Failed to export animation: {exc}",
            )

    @staticmethod
    def _resolve_animation_export_path(file_path: str, selected_filter: str) -> Tuple[str, str]:
        base_path, extension = os.path.splitext(file_path)
        extension = extension.lower()
        if not extension:
            if "GIF" in selected_filter:
                extension = ".gif"
            elif "PNG" in selected_filter:
                extension = ".apng"
            elif "WebP" in selected_filter:
                extension = ".webp"
            else:
                extension = ".gif"
            file_path = base_path + extension

        format_map = {
            ".gif": "GIF",
            ".png": "PNG",
            ".apng": "PNG",
            ".webp": "WEBP",
        }
        if extension not in format_map:
            extension = ".gif"
            file_path = base_path + extension
        format_name = format_map[extension]

        self._update_last_directory(file_path)
        return file_path, format_map[extension]

    def _resolve_playback_state(self, app, frame_manager) -> Tuple[int, float]:
        main_window = getattr(app, "main_window", None)
        total_frames = None
        fps_value: float = DEFAULT_PLAYBACK_FPS

        if main_window is not None:
            animation_player = getattr(main_window, "animation_player", None)
            if animation_player is not None:
                total_frames = self._safe_positive_int(
                    getattr(animation_player, "total_frames", None)
                )
                fps_value = self._sanitize_fps(
                    getattr(animation_player, "fps", DEFAULT_PLAYBACK_FPS)
                )

        if total_frames is None:
            total_frames = self._safe_positive_int(getattr(app, "playback_total_frames", None))

        if total_frames is None:
            total_frames = len(getattr(frame_manager, "frames", []) or [None])

        return max(1, total_frames), fps_value

    def _export_animation_file(
        self,
        *,
        frame_manager,
        file_path: str,
        format_name: str,
        total_frames: int,
        fps_value: float,
    ) -> None:
        total_frames = max(1, int(total_frames))
        fps_value = self._sanitize_fps(fps_value)

        frame_chunks = self._collect_frame_chunks(frame_manager, total_frames)
        if not frame_chunks:
            raise EmptyAnimationError(
                "No frames are available to export for the current animation."
            )

        frame_duration = max(1, int(round(1000.0 / fps_value)))
        frame_repeats = [int(chunk.repeats) for chunk in frame_chunks]
        durations = [max(1, repeats * frame_duration) for repeats in frame_repeats]

        needs_transparency = any(
            self._frame_has_transparency(chunk.image) for chunk in frame_chunks
        )

        converted_frames, transparency_index = self._convert_chunks_for_format(
            frame_chunks, format_name, needs_transparency
        )

        base_frame = converted_frames[0]
        append_frames = converted_frames[1:]

        save_kwargs = self._build_animation_save_kwargs(
            format_name=format_name,
            append_frames=append_frames,
            durations=durations,
            transparency_index=transparency_index,
        )

        comment = self._build_animation_metadata_comment(
            format_name=format_name,
            chunks=frame_chunks,
            total_frames=total_frames,
            frame_repeats=frame_repeats,
            frame_duration=frame_duration,
            fps_value=fps_value,
        )
        if comment is not None:
            save_kwargs["comment"] = comment

        try:
            base_frame.save(file_path, format=format_name, **save_kwargs)
        except (OSError, ValueError) as exc:
            raise AnimationExportError(str(exc)) from exc

    def _collect_frame_chunks(self, frame_manager, total_frames: int) -> List[AnimationFrameChunk]:
        rendered_cache: dict[int, Image.Image] = {}
        frame_chunks: List[AnimationFrameChunk] = []
        frame_count = len(getattr(frame_manager, "frames", []) or [])

        for playback_index in range(total_frames):
            resolved_index = frame_manager.resolve_key_frame_index(playback_index)
            if resolved_index is None or not (0 <= resolved_index < frame_count):
                continue

            cached = rendered_cache.get(resolved_index)
            if cached is None:
                qimage = frame_manager.frames[resolved_index].render()
                cached = Document.qimage_to_pil(qimage).convert("RGBA")
                rendered_cache[resolved_index] = cached

            if frame_chunks and frame_chunks[-1].index == resolved_index:
                frame_chunks[-1].repeats += 1
            else:
                frame_chunks.append(
                    AnimationFrameChunk(index=resolved_index, image=cached, repeats=1)
                )

        return frame_chunks

    @staticmethod
    def _frame_has_transparency(image: Image.Image) -> bool:
        alpha = image.getchannel("A")
        extrema = alpha.getextrema()
        return bool(extrema and extrema[0] < 255)

    def _convert_chunks_for_format(
        self,
        chunks: Sequence[AnimationFrameChunk],
        format_name: str,
        needs_transparency: bool,
    ) -> Tuple[List[Image.Image], Optional[int]]:
        if not chunks:
            raise EmptyAnimationError(
                "No frames are available to export for the current animation."
            )

        if format_name != "GIF":
            return [chunk.image.copy() for chunk in chunks], None

        converted: List[Image.Image] = []
        transparency_index: Optional[int] = None

        for chunk in chunks:
            pal_frame, frame_transparency_index = self._convert_rgba_to_gif_palette(
                chunk.image, needs_transparency
            )
            converted.append(pal_frame)
            if transparency_index is None and frame_transparency_index is not None:
                transparency_index = frame_transparency_index

        if transparency_index is not None:
            for frame in converted:
                try:
                    frame.info["background"] = transparency_index
                except (AttributeError, TypeError):
                    continue

        return converted, transparency_index

    @staticmethod
    def _convert_rgba_to_gif_palette(
        image: Image.Image, needs_transparency: bool
    ) -> Tuple[Image.Image, Optional[int]]:
        rgba_frame = image.convert("RGBA")
        rgb_frame = rgba_frame.convert("RGB")
        palette_colors = 255 if needs_transparency else 256
        pal_frame = rgb_frame.convert("P", palette=Image.ADAPTIVE, colors=palette_colors)

        transparency_index: Optional[int] = None
        if needs_transparency:
            palette = pal_frame.getpalette() or []
            if len(palette) < 768:
                palette = palette + [0] * (768 - len(palette))
            transparency_index = 255
            palette[transparency_index * 3 : transparency_index * 3 + 3] = [0, 0, 0]
            pal_frame.putpalette(palette)

            alpha = rgba_frame.getchannel("A")
            transparency_mask = alpha.point(lambda value: 255 if value == 0 else 0)
            if transparency_mask.getbbox():
                pal_frame.paste(transparency_index, mask=transparency_mask)
            pal_frame.info["transparency"] = transparency_index

        return pal_frame, transparency_index

    @staticmethod
    def _build_animation_save_kwargs(
        *,
        format_name: str,
        append_frames: Sequence[Image.Image],
        durations: Sequence[int],
        transparency_index: Optional[int],
    ) -> dict:
        save_kwargs: dict = {}
        durations = list(durations)

        if transparency_index is not None:
            save_kwargs["transparency"] = transparency_index
            save_kwargs.setdefault("background", transparency_index)

        if append_frames:
            save_kwargs.update(
                {
                    "save_all": True,
                    "append_images": list(append_frames),
                    "loop": 0,
                    "duration": durations if len(durations) > 1 else durations[0],
                }
            )
            if format_name in {"GIF", "PNG"}:
                save_kwargs["disposal"] = 2
        elif durations:
            if format_name in {"GIF", "PNG"}:
                save_kwargs["duration"] = durations[0]

        if format_name == "WEBP":
            save_kwargs["lossless"] = True
            if append_frames:
                save_kwargs.setdefault("save_all", True)

        return save_kwargs

    def _build_animation_metadata_comment(
        self,
        *,
        format_name: str,
        chunks: Sequence[AnimationFrameChunk],
        total_frames: int,
        frame_repeats: Sequence[int],
        frame_duration: int,
        fps_value: float,
    ) -> Optional[bytes]:
        if format_name != "GIF":
            return None

        metadata = {
            "version": 1,
            "total_frames": int(total_frames),
            "frame_repeats": [int(repeat) for repeat in frame_repeats],
            "frame_duration_ms": int(frame_duration),
            "fps": float(fps_value),
        }

        rgba_payload = self._encode_rgba_chunks(chunks)
        if rgba_payload:
            metadata["rgba_encoding"] = "png+zlib+base64"
            metadata["rgba_frames"] = rgba_payload

        comment = json.dumps({"pixel_portal": metadata}, separators=(",", ":"))
        return comment.encode("utf-8")

    def _encode_rgba_chunks(
        self, chunks: Sequence[AnimationFrameChunk]
    ) -> List[str]:
        encoded_frames: List[str] = []
        for chunk in chunks:
            buffer = io.BytesIO()
            try:
                chunk.image.save(buffer, format="PNG")
            except (OSError, ValueError):
                return []
            png_bytes = buffer.getvalue()
            try:
                compressed = zlib.compress(png_bytes)
            except zlib.error:
                return []
            encoded_frames.append(base64.b64encode(compressed).decode("ascii"))
        return encoded_frames

    @staticmethod
    def _sanitize_fps(value) -> float:
        try:
            fps_value = float(value)
        except (TypeError, ValueError):
            return DEFAULT_PLAYBACK_FPS
        if not math.isfinite(fps_value) or fps_value <= 0:
            return DEFAULT_PLAYBACK_FPS
        return fps_value

    @staticmethod
    def _safe_positive_int(value) -> Optional[int]:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        if number <= 0:
            return None
        return number

    def import_animation(self):
        app = self.app
        if app is None:
            return
        if not app.check_for_unsaved_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Import Animation",
            app.last_directory,
            "Animation Files (*.gif *.apng *.png *.webp *.tif *.tiff);;All Files (*)",
        )
        if not file_path:
            return

        app.last_directory = os.path.dirname(file_path)
        app.config.set('General', 'last_directory', app.last_directory)

        try:
            frame_entries, total_playback_frames, fps = self._read_animation_frames(file_path)
        except ValueError as exc:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(parent, "Import Animation", str(exc))
            return

        if not frame_entries:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(
                parent,
                "Import Animation",
                "No frames could be read from the selected file.",
            )
            return

        try:
            document = self._populate_document_with_frames(
                frame_entries,
                max(1, total_playback_frames),
                os.path.basename(file_path),
            )
        except ValueError as exc:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(parent, "Import Animation", str(exc))
            return

        app.attach_document(document)
        app.set_playback_total_frames(max(1, total_playback_frames))
        if app.main_window:
            app.main_window.apply_imported_animation_metadata(max(1, total_playback_frames), fps)
        app.undo_manager.clear()
        app.is_dirty = False
        app.undo_stack_changed.emit()
        app.document_changed.emit()
        if app.main_window:
            app.main_window.canvas.set_initial_zoom()

    def _read_animation_frames(self, file_path):
        frames, delays = self._read_raw_animation_frames(file_path)
        normalized_frames = self._normalize_frame_sizes(frames)
        normalized_delays = self._normalize_frame_delays(delays)

        metadata = self._extract_animation_metadata(file_path)
        decoded_frames = self._decode_metadata_rgba_frames(metadata)
        if (
            decoded_frames
            and len(decoded_frames) == len(normalized_frames)
            and self._frames_share_dimensions(decoded_frames)
        ):
            normalized_frames = decoded_frames

        frame_entries, total_playback_frames, frame_unit = self._build_import_frame_entries(
            normalized_frames, normalized_delays, metadata
        )

        fps_value = self._determine_import_fps(metadata, frame_unit)
        total_frames = self._apply_total_frame_hint(
            total_playback_frames, metadata.total_frames
        )

        return frame_entries, total_frames or len(frame_entries), fps_value

    def _read_raw_animation_frames(
        self, file_path: str
    ) -> tuple[list[QImage], list[int]]:
        reader = QImageReader(file_path)
        reader.setDecideFormatFromContent(True)
        if not reader.supportsAnimation():
            raise ValueError("The selected file does not contain animation frames.")

        frames: list[QImage] = []
        delays: list[int] = []
        while True:
            image = reader.read()
            if image.isNull():
                if frames:
                    break
                message = reader.errorString() or "Unable to read image data."
                raise ValueError(message)
            frames.append(image.convertToFormat(QImage.Format_ARGB32))
            delays.append(reader.nextImageDelay())

        return frames, delays

    @staticmethod
    def _normalize_frame_sizes(frames: Sequence[QImage]) -> list[QImage]:
        if not frames:
            return []

        base_width = frames[0].width()
        base_height = frames[0].height()
        normalized: list[QImage] = []
        for frame in frames:
            if frame.width() == base_width and frame.height() == base_height:
                normalized.append(frame)
                continue
            canvas = QImage(base_width, base_height, QImage.Format_ARGB32)
            canvas.fill(0)
            painter = QPainter(canvas)
            painter.drawImage(0, 0, frame)
            painter.end()
            normalized.append(canvas)
        return normalized

    @staticmethod
    def _normalize_frame_delays(delays: Sequence[int]) -> list[int]:
        valid_delays = [int(delay) for delay in delays if delay and delay > 0]
        fallback_delay = valid_delays[0] if valid_delays else 100

        normalized: list[int] = []
        last_valid_delay = fallback_delay
        for delay in delays:
            if delay and delay > 0:
                last_valid_delay = int(delay)
            normalized.append(last_valid_delay)
        return normalized

    def _decode_metadata_rgba_frames(
        self, metadata: AnimationMetadata
    ) -> list[QImage]:
        if not metadata.has_rgba_payload:
            return []

        decoded: list[QImage] = []
        for entry in metadata.rgba_frames or []:
            try:
                compressed = base64.b64decode(entry.encode('ascii'), validate=True)
                png_bytes = zlib.decompress(compressed)
            except (binascii.Error, ValueError, zlib.error):
                return []
            frame = QImage()
            if not frame.loadFromData(png_bytes, 'PNG'):
                return []
            decoded.append(frame.convertToFormat(QImage.Format_ARGB32))
        return decoded

    @staticmethod
    def _frames_share_dimensions(frames: Sequence[QImage]) -> bool:
        if not frames:
            return False
        width = frames[0].width()
        height = frames[0].height()
        return all(frame.width() == width and frame.height() == height for frame in frames)

    def _build_import_frame_entries(
        self,
        frames: Sequence[QImage],
        delays: Sequence[int],
        metadata: AnimationMetadata,
    ) -> tuple[list[tuple[QImage, int]], int, Optional[int]]:
        frame_entries: list[tuple[QImage, int]] = []
        total_playback_frames = 0
        frame_unit = self._compute_frame_unit(metadata.frame_duration_ms, delays)

        repeats = metadata.frame_repeats
        if repeats and len(repeats) == len(frames):
            for frame, repeat in zip(frames, repeats):
                repeat = max(1, int(repeat))
                frame_entries.append((frame, repeat))
                total_playback_frames += repeat
        else:
            if not delays:
                frame_entries = [(frame, 1) for frame in frames]
                total_playback_frames = len(frame_entries)
            else:
                effective_unit = frame_unit if frame_unit and frame_unit > 0 else delays[0]
                effective_unit = max(1, effective_unit)
                last_frame_bytes: Optional[bytes] = None

                for frame, delay in zip(frames, delays):
                    repeats = max(1, int(delay // effective_unit))
                    frame_bytes = frame.bits().tobytes()
                    if (
                        frame_entries
                        and last_frame_bytes is not None
                        and frame_bytes == last_frame_bytes
                    ):
                        previous_frame, previous_repeats = frame_entries[-1]
                        frame_entries[-1] = (previous_frame, previous_repeats + repeats)
                    else:
                        frame_entries.append((frame, repeats))
                    total_playback_frames += repeats
                    last_frame_bytes = frame_bytes

        if not frame_entries:
            frame_entries = [(frame, 1) for frame in frames]
            total_playback_frames = len(frame_entries)

        return frame_entries, total_playback_frames, frame_unit

    @staticmethod
    def _compute_frame_unit(
        frame_duration_ms: Optional[int], delays: Sequence[int]
    ) -> Optional[int]:
        if frame_duration_ms is not None and frame_duration_ms > 0:
            return frame_duration_ms
        if not delays:
            return None
        frame_unit = delays[0]
        for delay in delays[1:]:
            frame_unit = math.gcd(frame_unit, delay)
        return max(1, frame_unit)

    def _determine_import_fps(
        self, metadata: AnimationMetadata, frame_unit: Optional[int]
    ) -> float:
        if metadata.fps is not None:
            return metadata.fps
        if frame_unit and frame_unit > 0:
            return 1000.0 / frame_unit
        return DEFAULT_PLAYBACK_FPS

    @staticmethod
    def _apply_total_frame_hint(
        computed_total: int, metadata_total: Optional[int]
    ) -> int:
        if metadata_total is None or metadata_total <= 0:
            return computed_total
        return max(computed_total, metadata_total)

    @staticmethod
    def _extract_animation_metadata(file_path) -> AnimationMetadata:
        if not file_path.lower().endswith('.gif'):
            return AnimationMetadata()
        try:
            with Image.open(file_path) as image:
                comment = image.info.get('comment')
                if not comment:
                    return AnimationMetadata()
                if isinstance(comment, bytes):
                    try:
                        comment = comment.decode('utf-8')
                    except UnicodeDecodeError:
                        return AnimationMetadata()
                data = json.loads(comment)
        except (OSError, ValueError, json.JSONDecodeError):
            return AnimationMetadata()
        if not isinstance(data, dict):
            return AnimationMetadata()
        payload = data.get('pixel_portal')
        if not isinstance(payload, dict):
            return AnimationMetadata()
        return DocumentService._parse_animation_metadata(payload)

    @staticmethod
    def _parse_animation_metadata(payload: dict) -> AnimationMetadata:
        version = payload.get('version')
        if not isinstance(version, int):
            version = None

        frame_repeats = DocumentService._normalize_repeat_list(
            payload.get('frame_repeats')
        )
        total_frames = DocumentService._coerce_positive_int(payload.get('total_frames'))
        frame_duration = DocumentService._coerce_positive_int(
            payload.get('frame_duration_ms')
        )
        fps_value = DocumentService._coerce_positive_float(payload.get('fps'))

        rgba_frames = payload.get('rgba_frames')
        if not isinstance(rgba_frames, list) or not all(
            isinstance(entry, str) for entry in rgba_frames
        ):
            rgba_frames = None

        rgba_encoding = payload.get('rgba_encoding')
        if not isinstance(rgba_encoding, str):
            rgba_encoding = None

        return AnimationMetadata(
            version=version,
            frame_repeats=frame_repeats,
            total_frames=total_frames,
            frame_duration_ms=frame_duration,
            fps=fps_value,
            rgba_encoding=rgba_encoding,
            rgba_frames=rgba_frames,
        )

    @staticmethod
    def _normalize_repeat_list(value) -> Optional[list[int]]:
        if not isinstance(value, list) or not value:
            return None
        normalized: list[int] = []
        for entry in value:
            try:
                repeat = int(entry)
            except (TypeError, ValueError):
                return None
            if repeat <= 0:
                return None
            normalized.append(repeat)
        return normalized

    @staticmethod
    def _coerce_positive_int(value) -> Optional[int]:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def _coerce_positive_float(value) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number) or number <= 0:
            return None
        return number

    def _populate_document_with_frames(self, frame_entries, total_frames, filename):
        if not frame_entries:
            raise ValueError("No frames available to import.")

        width = frame_entries[0][0].width()
        height = frame_entries[0][0].height()
        document = Document(width, height)
        layer_manager = document.layer_manager
        active_layer = layer_manager.active_layer
        if active_layer is None:
            layer_manager.add_layer("Animation")
            active_layer = layer_manager.active_layer
        if active_layer is None:
            raise ValueError("Unable to create a layer for the imported animation.")

        base_name = os.path.splitext(filename)[0]
        if base_name:
            try:
                active_layer.name = base_name
            except ValueError:
                pass

        frame_manager = document.frame_manager
        layer_uid = active_layer.uid
        layer_keys = frame_manager.layer_keys.setdefault(layer_uid, {0})
        if 0 not in layer_keys:
            frame_manager.add_layer_key(layer_uid, 0)

        total_frames = max(1, int(total_frames))
        frame_manager.ensure_frame(total_frames - 1)

        playback_index = 0
        for frame, repeats in frame_entries:
            repeats = max(1, int(repeats))
            if playback_index < 0 or playback_index >= len(frame_manager.frames):
                break
            if playback_index != 0 and playback_index not in frame_manager.layer_keys.get(layer_uid, {0}):
                frame_manager.add_layer_key(layer_uid, playback_index)
            target_layer = self._layer_instance_for_frame(frame_manager, playback_index, layer_uid)
            if target_layer is None:
                playback_index += repeats
                continue
            target_layer.image = frame.copy()
            target_layer.on_image_change.emit()
            playback_index += repeats
            if playback_index >= total_frames:
                break

        document.select_frame(0)
        return document

    @staticmethod
    def _layer_instance_for_frame(frame_manager, frame_index, layer_uid):
        if not (0 <= frame_index < len(frame_manager.frames)):
            return None
        manager = frame_manager.frames[frame_index].layer_manager
        for layer in manager.layers:
            if getattr(layer, "uid", None) == layer_uid:
                return layer
        return None

    def _get_selected_image(self):
        app = self.app
        if not app.document or not app.main_window:
            return None

        active_layer = app.document.layer_manager.active_layer
        if not active_layer:
            return None

        selection = app.main_window.canvas.selection_shape
        if selection and not selection.isEmpty():
            return active_layer.image.copy(selection.boundingRect().toRect())
        else:
            return active_layer.image.copy()
