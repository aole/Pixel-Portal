from .layer import Layer
from PySide6.QtGui import QPainter

class LayerManager:
    """
    Manages the stack of layers in a document.
    """
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers = []
        self.active_layer_index = -1

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

    def remove_layer(self, index: int):
        """Removes the layer at the given index."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")
        if len(self.layers) == 1:
            raise ValueError("Cannot remove the last layer.")

        del self.layers[index]

        if self.active_layer_index >= index:
            self.active_layer_index = max(0, self.active_layer_index - 1)

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
        self.layers[index].visible = not self.layers[index].visible
