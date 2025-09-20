import json
import math
import os
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image
from PySide6.QtGui import QImage, QImageReader, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox

from portal.core.document import Document


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

        main_window = getattr(app, "main_window", None)
        total_frames = None
        if main_window is not None:
            try:
                total_frames = int(main_window.animation_player.total_frames)
            except (TypeError, ValueError):
                total_frames = None
            fps_value = getattr(main_window.animation_player, "fps", 12.0)
        else:
            fps_value = 12.0

        if total_frames is None:
            playback_total = getattr(app, "playback_total_frames", None)
            if playback_total is not None:
                try:
                    total_frames = int(playback_total)
                except (TypeError, ValueError):
                    total_frames = None

        if total_frames is None:
            total_frames = len(frame_manager.frames)

        if total_frames <= 0:
            total_frames = 1

        try:
            fps_value = float(fps_value)
        except (TypeError, ValueError):
            fps_value = 12.0
        if not math.isfinite(fps_value) or fps_value <= 0:
            fps_value = 12.0

        rendered_cache = {}
        pil_frames = []
        frame_count = len(frame_manager.frames)
        for playback_index in range(total_frames):
            resolved_index = frame_manager.resolve_key_frame_index(playback_index)
            if resolved_index is None:
                continue
            if not (0 <= resolved_index < frame_count):
                continue
            cached = rendered_cache.get(resolved_index)
            if cached is None:
                qimage = frame_manager.frames[resolved_index].render()
                cached = Document.qimage_to_pil(qimage).convert("RGBA")
                rendered_cache[resolved_index] = cached
            pil_frames.append(cached.copy())

        if not pil_frames:
            QMessageBox.information(
                parent,
                "Export Animation",
                "No frames are available to export for the current animation.",
            )
            return

        frame_duration = max(1, int(round(1000.0 / fps_value)))

        def _frame_has_transparency(image):
            alpha = image.getchannel("A")
            extrema = alpha.getextrema()
            return extrema is not None and extrema[0] < 255

        needs_transparency = any(_frame_has_transparency(frame) for frame in pil_frames)

        base_frame = pil_frames[0]
        append_frames = [frame.copy() for frame in pil_frames[1:]]
        gif_transparency_index = None

        if format_name == "GIF":
            def _convert_frame_to_gif(frame):
                rgba_frame = frame.convert("RGBA")
                rgb_frame = rgba_frame.convert("RGB")
                palette_colors = 255 if needs_transparency else 256
                pal_frame = rgb_frame.convert("P", palette=Image.ADAPTIVE, colors=palette_colors)

                transparency_index = None
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

            base_frame, gif_transparency_index = _convert_frame_to_gif(base_frame)
            converted_append_frames = []
            for frame in append_frames:
                converted_frame, frame_transparency_index = _convert_frame_to_gif(frame)
                converted_append_frames.append(converted_frame)
                if gif_transparency_index is None and frame_transparency_index is not None:
                    gif_transparency_index = frame_transparency_index
            append_frames = converted_append_frames

        save_kwargs = {}
        if gif_transparency_index is not None:
            save_kwargs["transparency"] = gif_transparency_index
        if append_frames:
            save_kwargs.update(
                {
                    "save_all": True,
                    "append_images": append_frames,
                    "loop": 0,
                    "duration": frame_duration,
                }
            )
            if format_name in {"GIF", "PNG"}:
                save_kwargs["disposal"] = 2
        else:
            if format_name in {"GIF", "PNG"}:
                save_kwargs["duration"] = frame_duration

        if format_name == "WEBP":
            save_kwargs["lossless"] = True
            if append_frames:
                save_kwargs.setdefault("save_all", True)

        try:
            base_frame.save(file_path, format=format_name, **save_kwargs)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                parent,
                "Export Animation",
                f"Failed to export animation: {exc}",
            )

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
            frames, fps = self._read_animation_frames(file_path)
        except ValueError as exc:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(parent, "Import Animation", str(exc))
            return

        if not frames:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(
                parent,
                "Import Animation",
                "No frames could be read from the selected file.",
            )
            return

        try:
            document = self._populate_document_with_frames(frames, os.path.basename(file_path))
        except ValueError as exc:
            parent = getattr(app, "main_window", None)
            QMessageBox.warning(parent, "Import Animation", str(exc))
            return

        app.attach_document(document)
        app.set_playback_total_frames(len(frames))
        if app.main_window:
            app.main_window.apply_imported_animation_metadata(len(frames), fps)
        app.undo_manager.clear()
        app.is_dirty = False
        app.undo_stack_changed.emit()
        app.document_changed.emit()
        if app.main_window:
            app.main_window.canvas.set_initial_zoom()

    def _read_animation_frames(self, file_path):
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
            converted = image.convertToFormat(QImage.Format_ARGB32)
            frames.append(converted)
            delays.append(reader.nextImageDelay())

        base_width = frames[0].width()
        base_height = frames[0].height()
        normalized_frames: list[QImage] = []
        for frame in frames:
            if frame.width() == base_width and frame.height() == base_height:
                normalized_frames.append(frame)
                continue
            canvas = QImage(base_width, base_height, QImage.Format_ARGB32)
            canvas.fill(0)
            painter = QPainter(canvas)
            painter.drawImage(0, 0, frame)
            painter.end()
            normalized_frames.append(canvas)

        valid_delays = [delay for delay in delays if delay and delay > 0]
        if valid_delays:
            average = sum(valid_delays) / len(valid_delays)
            fps = 1000.0 / average if average > 0 else 12.0
        else:
            fps = 12.0

        return normalized_frames, fps

    def _populate_document_with_frames(self, frames, filename):
        if not frames:
            raise ValueError("No frames available to import.")

        width = frames[0].width()
        height = frames[0].height()
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
        for index, frame in enumerate(frames):
            frame_manager.ensure_frame(index)
            if index not in frame_manager.layer_keys.get(layer_uid, {0}):
                frame_manager.add_layer_key(layer_uid, index)
            target_layer = self._layer_instance_for_frame(frame_manager, index, layer_uid)
            if target_layer is None:
                continue
            target_layer.image = frame.copy()
            target_layer.on_image_change.emit()

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
