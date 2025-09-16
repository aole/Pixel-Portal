from PySide6.QtWidgets import QMessageBox
from portal.core.layer import Layer
from portal.ui.script_dialog import ScriptDialog
from portal.core.command import AddLayerCommand, ModifyImageCommand

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

    def get_active_layer(self) -> Layer | None:
        """Returns the currently active layer, if any."""
        if self.app.document:
            return self.app.document.layer_manager.active_layer
        return None

    def create_layer(self, name):
        """Creates a new layer with the given name and returns it."""
        if self.app.document:
            command = AddLayerCommand(self.app.document, name=name)
            self.app.execute_command(command)
            # The command makes the new layer active
            return self.app.document.layer_manager.active_layer
        return None

    def modify_layer(self, layer, drawing_func):
        """Modifies a layer's image using a drawing function."""
        if layer:
            command = ModifyImageCommand(layer, drawing_func)
            self.app.execute_command(command)

    def show_message_box(self, title, text):
        """Shows a message box with the given title and text."""
        QMessageBox.information(self.app.main_window, title, text)
