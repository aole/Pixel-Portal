from PySide6.QtWidgets import QMessageBox
from portal.core.layer import Layer
from portal.ui.script_dialog import ScriptDialog

class ScriptingAPI:
    def __init__(self, app):
        self.app = app

    def get_all_layers(self):
        """Returns a list of all layers in the current document."""
        if self.app.document:
            return self.app.document.layer_manager.layers
        return []

    def get_layer(self, index):
        """Returns the layer at the specified index."""
        layers = self.get_all_layers()
        if 0 <= index < len(layers):
            return layers[index]
        return None

    def create_layer(self, name):
        """Creates a new layer with the given name."""
        if self.app.document:
            self.app.document.layer_manager.add_layer(name)
            return self.app.document.layer_manager.active_layer
        return None

    def show_message_box(self, title, text):
        """Shows a message box with the given title and text."""
        QMessageBox.information(self.app.main_window, title, text)

    def get_parameters(self, params):
        """Shows a dialog to get parameters from the user."""
        dialog = ScriptDialog(params, self.app.main_window)
        if dialog.exec():
            return dialog.get_values()
        return None
