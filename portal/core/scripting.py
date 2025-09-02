from PySide6.QtWidgets import QMessageBox, QInputDialog, QColorDialog
from PySide6.QtGui import QColor
from portal.core.layer import Layer

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

    def get_text(self, title, label):
        """Shows an input dialog to get text from the user."""
        text, ok = QInputDialog.getText(self.app.main_window, title, label)
        if ok:
            return text
        return None

    def get_color(self, title):
        """Shows a color dialog to get a color from the user."""
        color = QColorDialog.getColor(parent=self.app.main_window, title=title)
        if color.isValid():
            return color
        return None

    def get_item(self, title, label, items):
        """Shows a dialog to get an item from a list from the user."""
        item, ok = QInputDialog.getItem(self.app.main_window, title, label, items, 0, False)
        if ok and item:
            return item
        return None
