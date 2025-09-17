from PySide6.QtGui import QImage, QImageReader, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox
import os

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
