import json
import math
import os

from PIL import Image
from PySide6.QtGui import QImage, QImageReader, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox

from portal.core.document import Document


class DocumentService:
    def __init__(self, app=None):
        self.app = app

    def open_document(self):
        app = self.app
        if not app.check_for_unsaved_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            app.last_directory,
            "All Supported Files (*.png *.jpg *.bmp *.tif *.tiff);;Image Files (*.png *.jpg *.bmp);;TIFF Files (*.tif *.tiff)"
        )
        if file_path:
            app.last_directory = os.path.dirname(file_path)
            app.config.set('General', 'last_directory', app.last_directory)

            if file_path.lower().endswith(('.tif', '.tiff')):
                document = Document.load_tiff(file_path)
            else:
                image = QImage(file_path)
                if image.isNull():
                    return
                document = Document(image.width(), image.height())
                document.layer_manager.layers[0].image = image

            app.attach_document(document)
            app.undo_manager.clear()
            app.is_dirty = False
            app.undo_stack_changed.emit()
            app.document_changed.emit()
            if app.main_window:
                app.main_window.canvas.set_initial_zoom()

    def open_as_key(self):
        app = self.app
        if app is None:
            return

        document = getattr(app, "document", None)
        if document is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image as Key",
            app.last_directory,
            "Image Files (*.png *.jpg *.bmp *.tif *.tiff);;All Files (*)",
        )
        if not file_path:
            return

        image = QImage(file_path)
        if image.isNull():
            return

        app.last_directory = os.path.dirname(file_path)
        app.config.set('General', 'last_directory', app.last_directory)

        paste_key = getattr(app, "paste_key_from_image", None)
        if callable(paste_key):
            paste_key(image)

    def save_document(self):
        app = self.app
        file_path, selected_filter = QFileDialog.getSaveFileName(
            None,
            "Save Image",
            app.last_directory,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;Bitmap (*.bmp);;TIFF (*.tif *.tiff)"
        )
        if file_path:
            app.last_directory = os.path.dirname(file_path)
            app.config.set('General', 'last_directory', app.last_directory)

            if "TIFF" in selected_filter:
                app.document.save_tiff(file_path)
            else:
                image = app.document.render()
                image.save(file_path)

            app.is_dirty = False

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

        export_directory = os.path.dirname(file_path)
        if export_directory:
            app.last_directory = export_directory
            app.config.set("General", "last_directory", app.last_directory)

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
        frame_count = len(frame_manager.frames)
        frame_chunks: list[dict[str, object]] = []
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
            if frame_chunks and frame_chunks[-1]["index"] == resolved_index:
                frame_chunks[-1]["repeats"] = int(frame_chunks[-1]["repeats"]) + 1
            else:
                frame_chunks.append({"index": resolved_index, "image": cached, "repeats": 1})

        if not frame_chunks:
            QMessageBox.information(
                parent,
                "Export Animation",
                "No frames are available to export for the current animation.",
            )
            return

        frame_duration = max(1, int(round(1000.0 / fps_value)))
        frame_repeats = [int(chunk["repeats"]) for chunk in frame_chunks]
        durations = [max(1, repeat * frame_duration) for repeat in frame_repeats]

        def _frame_has_transparency(image):
            alpha = image.getchannel("A")
            extrema = alpha.getextrema()
            return extrema is not None and extrema[0] < 255

        needs_transparency = any(
            _frame_has_transparency(chunk["image"]) for chunk in frame_chunks
        )

        converted_frames = []
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

            for chunk in frame_chunks:
                converted_frame, frame_transparency_index = _convert_frame_to_gif(
                    chunk["image"].copy()
                )
                converted_frames.append(converted_frame)
                if gif_transparency_index is None and frame_transparency_index is not None:
                    gif_transparency_index = frame_transparency_index

            base_frame = converted_frames[0]
            append_frames = converted_frames[1:]
            if gif_transparency_index is not None:
                try:
                    base_frame.info["background"] = gif_transparency_index
                except (AttributeError, TypeError):
                    pass
                for frame in append_frames:
                    try:
                        frame.info["background"] = gif_transparency_index
                    except (AttributeError, TypeError):
                        pass

        else:
            converted_frames = [chunk["image"].copy() for chunk in frame_chunks]
            base_frame = converted_frames[0]
            append_frames = converted_frames[1:]

        save_kwargs = {}
        if gif_transparency_index is not None:
            save_kwargs["transparency"] = gif_transparency_index
            save_kwargs.setdefault("background", gif_transparency_index)
        if append_frames:
            save_kwargs.update(
                {
                    "save_all": True,
                    "append_images": append_frames,
                    "loop": 0,
                    "duration": durations if len(durations) > 1 else durations[0],
                }
            )
            if format_name in {"GIF", "PNG"}:
                save_kwargs["disposal"] = 2
        else:
            if format_name in {"GIF", "PNG"}:
                save_kwargs["duration"] = durations[0]

        if format_name == "WEBP":
            save_kwargs["lossless"] = True
            if append_frames:
                save_kwargs.setdefault("save_all", True)

        if format_name == "GIF":
            metadata = {
                "version": 1,
                "total_frames": int(total_frames),
                "frame_repeats": frame_repeats,
                "frame_duration_ms": frame_duration,
                "fps": fps_value,
            }
            comment = json.dumps({"pixel_portal": metadata}, separators=(",", ":"))
            save_kwargs["comment"] = comment.encode("utf-8")

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

        valid_delays = [int(delay) for delay in delays if delay and delay > 0]
        # GIF timings are stored in milliseconds. When the delay is missing or zero,
        # browsers typically fall back to 100 ms (10 FPS). Mirror that behaviour so
        # that the imported animation has sensible timing.
        fallback_delay = valid_delays[0] if valid_delays else 100

        normalized_delays: list[int] = []
        last_valid_delay = fallback_delay
        for delay in delays:
            if delay and delay > 0:
                last_valid_delay = int(delay)
            normalized_delays.append(last_valid_delay)

        metadata = self._extract_animation_metadata(file_path)
        metadata_repeats = metadata.get("frame_repeats") if isinstance(metadata, dict) else None
        metadata_total_frames = metadata.get("total_frames") if isinstance(metadata, dict) else None
        metadata_frame_duration = metadata.get("frame_duration_ms") if isinstance(metadata, dict) else None
        metadata_fps = metadata.get("fps") if isinstance(metadata, dict) else None

        frame_entries: list[tuple[QImage, int]] = []
        total_playback_frames = 0

        if (
            isinstance(metadata_repeats, list)
            and len(metadata_repeats) == len(normalized_frames)
        ):
            parsed_repeats: list[int] = []
            for value in metadata_repeats:
                try:
                    repeat_value = int(value)
                except (TypeError, ValueError):
                    parsed_repeats = []
                    break
                if repeat_value <= 0:
                    parsed_repeats = []
                    break
                parsed_repeats.append(repeat_value)
            if parsed_repeats:
                for frame, repeats in zip(normalized_frames, parsed_repeats):
                    repeats = max(1, repeats)
                    frame_entries.append((frame, repeats))
                    total_playback_frames += repeats

        if not frame_entries:
            if not normalized_delays:
                fallback_entries = [(frame, 1) for frame in normalized_frames]
                return fallback_entries, len(fallback_entries), 12.0

            frame_unit = normalized_delays[0]
            for delay in normalized_delays[1:]:
                frame_unit = math.gcd(frame_unit, delay)
            frame_unit = max(1, frame_unit)

            last_frame_bytes = None
            for frame, delay in zip(normalized_frames, normalized_delays):
                repeats = max(1, delay // frame_unit)
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
        else:
            frame_unit = None

        if not frame_entries:
            # Fallback to treating every frame as unique with a single repeat.
            for frame in normalized_frames:
                frame_entries.append((frame, 1))
            total_playback_frames = len(frame_entries)
            frame_unit = None

        if frame_unit is None and metadata_frame_duration:
            try:
                frame_unit = int(metadata_frame_duration)
            except (TypeError, ValueError):
                frame_unit = None
            if frame_unit is not None and frame_unit <= 0:
                frame_unit = None

        if frame_unit is None and normalized_delays:
            frame_unit = normalized_delays[0]
            for delay in normalized_delays[1:]:
                frame_unit = math.gcd(frame_unit, delay)
            frame_unit = max(1, frame_unit)

        fps_value = None
        if metadata_fps is not None:
            try:
                fps_candidate = float(metadata_fps)
            except (TypeError, ValueError):
                fps_candidate = None
            if fps_candidate and math.isfinite(fps_candidate) and fps_candidate > 0:
                fps_value = fps_candidate
        if fps_value is None and frame_unit and frame_unit > 0:
            fps_value = 1000.0 / frame_unit
        if fps_value is None:
            fps_value = 12.0

        if metadata_total_frames:
            try:
                total_hint = int(metadata_total_frames)
            except (TypeError, ValueError):
                total_hint = None
            if total_hint and total_hint > 0:
                total_playback_frames = max(total_playback_frames, total_hint)

        return frame_entries, total_playback_frames or len(frame_entries), fps_value

    @staticmethod
    def _extract_animation_metadata(file_path):
        if not file_path.lower().endswith(".gif"):
            return None
        try:
            with Image.open(file_path) as image:
                comment = image.info.get("comment")
                if not comment:
                    return None
                if isinstance(comment, bytes):
                    try:
                        comment = comment.decode("utf-8")
                    except UnicodeDecodeError:
                        return None
                data = json.loads(comment)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        payload = data.get("pixel_portal")
        if not isinstance(payload, dict):
            return None
        return payload

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
