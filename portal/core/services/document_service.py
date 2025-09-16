from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog
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
