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

        file_filters = (
            "Pixel Portal Document (*.aole);;"
            "All Supported Files (*.aole *.png *.jpg *.bmp *.tif *.tiff);;"
            "Image Files (*.png *.jpg *.bmp);;"
            "TIFF Files (*.tif *.tiff)"
        )
        file_path, selected_filter = QFileDialog.getOpenFileName(
            None,
            "Open Document",
            app.last_directory,
            file_filters,
        )
        if file_path:
            app.last_directory = os.path.dirname(file_path)
            app.config.set('General', 'last_directory', app.last_directory)

            extension = os.path.splitext(file_path)[1].lower()
            selected_filter_lower = (selected_filter or "").lower()
            if not extension:
                if "pixel portal document" in selected_filter_lower:
                    extension = ".aole"
                elif "tiff" in selected_filter_lower:
                    extension = ".tiff"

            try:
                if extension == ".aole":
                    document = Document.load_aole(file_path)
                elif extension in ('.tif', '.tiff'):
                    document = Document.load_tiff(file_path)
                else:
                    image = QImage(file_path)
                    if image.isNull():
                        return
                    document = Document(image.width(), image.height())
                    document.layer_manager.layers[0].image = image
                document.file_path = file_path
            except (ValueError, OSError, json.JSONDecodeError):
                message_box = QMessageBox()
                message_box.setText("Unable to open the selected document.")
                message_box.setInformativeText("The file appears to be corrupted or in an unsupported format.")
                message_box.setIcon(QMessageBox.Warning)
                message_box.exec()
                return

            app.attach_document(document)
            app.undo_manager.clear()
            app.is_dirty = False
            app.undo_stack_changed.emit()
            app.document_changed.emit()
            if app.main_window:
                app.main_window.canvas.set_initial_zoom()
            if hasattr(app, "update_main_window_title"):
                app.update_main_window_title()

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
        file_filters = (
            "Pixel Portal Document (*.aole);;"
            "PNG (*.png);;"
            "JPEG (*.jpg *.jpeg);;"
            "Bitmap (*.bmp);;"
            "TIFF (*.tif *.tiff)"
        )
        file_path, selected_filter = QFileDialog.getSaveFileName(
            None,
            "Save Document",
            app.last_directory,
            file_filters,
        )
        if file_path:
            app.last_directory = os.path.dirname(file_path)
            app.config.set('General', 'last_directory', app.last_directory)

            base_path, extension = os.path.splitext(file_path)
            extension = extension.lower()

            selected_filter_lower = (selected_filter or "").lower()

            if "pixel portal document" in selected_filter_lower or extension == ".aole":
                if extension != ".aole":
                    file_path = base_path + ".aole"
                app.document.save_aole(file_path)
            elif "tiff" in selected_filter_lower or extension in (".tif", ".tiff"):
                if extension not in (".tif", ".tiff"):
                    file_path = base_path + ".tiff"
                app.document.save_tiff(file_path)
            else:
                if not extension:
                    if "jpeg" in selected_filter_lower or "jpg" in selected_filter_lower:
                        extension = ".jpg"
                    elif "bmp" in selected_filter_lower:
                        extension = ".bmp"
                    else:
                        extension = ".png"
                    file_path = base_path + extension
                image = app.document.render()
                image.save(file_path)
            if hasattr(app.document, "file_path"):
                app.document.file_path = file_path
            app.is_dirty = False
            if hasattr(app, "update_main_window_title"):
                app.update_main_window_title()

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
        if main_window is not None:
            try:
                total_frames = int(main_window.animation_player.total_frames)
            except (TypeError, ValueError):
                total_frames = len(frame_manager.frames)
            fps_value = getattr(main_window.animation_player, "fps", 12.0)
        else:
            total_frames = len(frame_manager.frames)
            fps_value = 12.0

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
