from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QSize, QObject, Signal

class Layer(QObject):
    """
    Represents a single layer in the document.
    """
    on_image_change = Signal()
    visibility_changed = Signal()

    def __init__(self, width: int, height: int, name: str):
        super().__init__()
        if not isinstance(name, str) or not name:
            raise ValueError("Layer name must be a non-empty string.")

        self.name = name
        self._visible = True
        self.opacity = 1.0  # 0.0 (transparent) to 1.0 (opaque)

        self.image = QImage(QSize(width, height), QImage.Format_ARGB32)
        self.image.fill(QColor(0, 0, 0, 0))  # Fill with transparent

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self._visible != value:
            self._visible = value
            self.visibility_changed.emit()

    def clear(self):
        """Fills the layer with transparent color."""
        self.image.fill(QColor(0, 0, 0, 0))
        self.on_image_change.emit()

    def clone(self):
        """Creates a deep copy of this layer."""
        new_layer = Layer(self.image.width(), self.image.height(), self.name)
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.image = self.image.copy()  # Use QImage's copy method
        return new_layer

    @classmethod
    def from_qimage(cls, qimage, name):
        """Creates a new layer from a QImage."""
        width = qimage.width()
        height = qimage.height()
        layer = cls(width, height, name)
        layer.image = qimage
        return layer
