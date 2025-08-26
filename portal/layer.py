from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QSize

class Layer:
    """
    Represents a single layer in the document.
    """
    def __init__(self, width: int, height: int, name: str):
        if not isinstance(name, str) or not name:
            raise ValueError("Layer name must be a non-empty string.")

        self.name = name
        self.visible = True
        self.opacity = 1.0  # 0.0 (transparent) to 1.0 (opaque)

        self.image = QImage(QSize(width, height), QImage.Format_ARGB32)
        self.image.fill(QColor(0, 0, 0, 0))  # Fill with transparent

    def clear(self):
        """Fills the layer with transparent color."""
        self.image.fill(QColor(0, 0, 0, 0))

    def clone(self):
        """Creates a deep copy of this layer."""
        new_layer = Layer(self.image.width(), self.image.height(), self.name)
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.image = self.image.copy()  # Use QImage's copy method
        return new_layer
