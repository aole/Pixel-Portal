from portal.core.layer import Layer
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPainter, QColor, QImage
from PIL.ImageQt import ImageQt
from portal.commands.layer_commands import SetLayerVisibleCommand


class LayerManager(QObject):
    """
    Manages the stack of layers in a document.
    """
    layer_visibility_changed = Signal(int)
    layer_structure_changed = Signal()
    command_generated = Signal(object)

    def __init__(self, width: int, height: int, create_background: bool = True):
        super().__init__()
        self.width = width
        self.height = height
        self.layers = []
        self.active_layer_index = -1

        if create_background:
            self.add_layer("Background")

    @property
    def active_layer(self) -> Layer | None:
        """Returns the currently active layer."""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    def add_layer(self, name: str):
        """Adds a new layer to the top of the stack."""
        new_layer = Layer(self.width, self.height, name)
        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.layer_structure_changed.emit()

    def add_layer_with_image(self, image, name="Image Layer"):
        if not isinstance(image, QImage):
            q_image = ImageQt(image.convert("RGBA"))
            q_image = QImage(q_image)
        else:
            q_image = image

        new_layer = Layer(self.width, self.height, name)

        painter = QPainter(new_layer.image)
        painter.drawImage(0, 0, q_image)
        painter.end()

        new_layer.image.save("debug_03_final_layer_image.png")

        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.layer_structure_changed.emit()

    def remove_layer(self, index: int):
        """Removes the layer at the given index."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")
        if len(self.layers) == 1:
            raise ValueError("Cannot remove the last layer.")

        del self.layers[index]

        if self.active_layer_index >= index:
            self.active_layer_index = max(0, self.active_layer_index - 1)
        self.layer_structure_changed.emit()

    def select_layer(self, index: int):
        """Selects the layer at the given index as the active one."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")
        self.active_layer_index = index

    def move_layer_up(self, index: int):
        """Moves the layer at the given index up one step in the stack."""
        if not (0 <= index < len(self.layers) - 1):
            return # Can't move up if it's the top layer or invalid

        self.layers[index], self.layers[index + 1] = self.layers[index + 1], self.layers[index]

        # Adjust active layer index if it was affected
        if self.active_layer_index == index:
            self.active_layer_index += 1
        elif self.active_layer_index == index + 1:
            self.active_layer_index -= 1
        self.layer_structure_changed.emit()

    def move_layer_down(self, index: int):
        """Moves the layer at the given index down one step in the stack."""
        if not (0 < index < len(self.layers)):
            return # Can't move down if it's the bottom layer or invalid

        self.layers[index], self.layers[index - 1] = self.layers[index - 1], self.layers[index]

        # Adjust active layer index if it was affected
        if self.active_layer_index == index:
            self.active_layer_index -= 1
        elif self.active_layer_index == index - 1:
            self.active_layer_index += 1
        self.layer_structure_changed.emit()

    def merge_layer_down(self, index: int):
        """Merges the layer at the given index with the layer below it."""
        if not (0 < index < len(self.layers)):
            raise IndexError("Cannot merge: invalid index or no layer below.")

        top_layer = self.layers[index]
        bottom_layer = self.layers[index - 1]

        painter = QPainter(bottom_layer.image)
        painter.setOpacity(top_layer.opacity)
        painter.drawImage(0, 0, top_layer.image)
        painter.end()

        self.remove_layer(index)

    def toggle_visibility(self, index: int):
        """Toggles the visibility of the layer at the given index."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")

        layer = self.layers[index]
        command = SetLayerVisibleCommand(self, index, not layer.visible)
        self.command_generated.emit(command)

    def clone(self):
        """Creates a deep copy of the layer manager."""
        new_manager = LayerManager(self.width, self.height, create_background=False)
        new_manager.layers = [layer.clone() for layer in self.layers]
        new_manager.active_layer_index = self.active_layer_index
        return new_manager
