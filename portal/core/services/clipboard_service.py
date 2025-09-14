from PySide6.QtWidgets import QApplication
from portal.core.command import ClearLayerCommand, PasteCommand, PasteInSelectionCommand


class ClipboardService:
    def __init__(self, document_service, app=None):
        self.document_service = document_service
        self.app = app

    def cut(self):
        app = self.app
        if not app.document or not app.main_window:
            return

        self.copy()

        active_layer = app.document.layer_manager.active_layer
        if not active_layer:
            return

        selection = app.main_window.canvas.selection_shape
        command = ClearLayerCommand(active_layer, selection)
        app.execute_command(command)

    def copy(self):
        app = self.app
        if not app.document:
            return

        image = self.document_service._get_selected_image()
        if image:
            QApplication.clipboard().setImage(image)

    def paste(self):
        app = self.app
        if not app.document or not app.main_window:
            return

        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            return

        selection = app.main_window.canvas.selection_shape
        if selection and not selection.isEmpty():
            command = PasteInSelectionCommand(app.document, image, selection)
            app.execute_command(command)
        else:
            command = PasteCommand(app.document, image)
            app.execute_command(command)

    def paste_as_new_image(self):
        app = self.app
        clipboard = QApplication.clipboard()
        image = clipboard.image()

        if not image.isNull():
            app.new_document(image.width(), image.height())
            command = PasteCommand(app.document, image)
            app.execute_command(command)

    def paste_as_new_layer(self):
        app = self.app
        clipboard = QApplication.clipboard()
        image = clipboard.image()

        if app.document and not image.isNull():
            command = PasteCommand(app.document, image)
            app.execute_command(command)
