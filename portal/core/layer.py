from __future__ import annotations

from PySide6.QtGui import QImage, QColor, QPainter
from PySide6.QtCore import QSize, QObject, Signal, Qt, QRect

class Layer(QObject):
    """
    Represents a single layer in the document.
    """
    on_image_change = Signal()
    visibility_changed = Signal()
    onion_skin_changed = Signal(bool)
    name_changed = Signal(str)

    _uid_counter = 0

    @classmethod
    def _next_uid(cls) -> int:
        cls._uid_counter += 1
        return cls._uid_counter

    def __init__(self, width: int, height: int, name: str):
        super().__init__()
        if not isinstance(name, str) or not name:
            raise ValueError("Layer name must be a non-empty string.")

        self._name = name
        self._visible = True
        self.opacity = 1.0  # 0.0 (transparent) to 1.0 (opaque)
        self._onion_skin_enabled = False

        self.image = QImage(QSize(width, height), QImage.Format_ARGB32)
        self.image.fill(QColor(0, 0, 0, 0))  # Fill with transparent
        self.uid = self._next_uid()

        self._non_transparent_bounds: QRect | None = None
        self._non_transparent_bounds_dirty = False
        self.on_image_change.connect(self._mark_non_transparent_bounds_dirty)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self._name != value:
            if not isinstance(value, str) or not value:
                raise ValueError("Layer name must be a non-empty string.")
            self._name = value
            self.name_changed.emit(self._name)

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        if self._visible != value:
            self._visible = value
            self.visibility_changed.emit()

    @property
    def onion_skin_enabled(self) -> bool:
        return self._onion_skin_enabled

    @onion_skin_enabled.setter
    def onion_skin_enabled(self, value: bool) -> None:
        normalized = bool(value)
        if self._onion_skin_enabled != normalized:
            self._onion_skin_enabled = normalized
            self.onion_skin_changed.emit(self._onion_skin_enabled)

    def clear(self, selection=None):
        """Fills the layer with transparent color."""
        if selection and not selection.isEmpty():
            painter = QPainter(self.image)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(selection, QColor(0, 0, 0, 0))
            painter.end()
        else:
            self.image.fill(QColor(0, 0, 0, 0))

        self.on_image_change.emit()
        self._set_non_transparent_bounds(None)

    def clone(
        self,
        *,
        preserve_identity: bool = True,
        deep_copy: bool = False,
    ) -> "Layer":
        """Create a copy of this layer.

        When ``deep_copy`` is ``False`` (the default) the returned layer shares the
        source image's pixel buffer thanks to Qt's implicit sharing. Callers that
        require an isolated buffer must request ``deep_copy=True``.
        """

        new_layer = Layer(self.image.width(), self.image.height(), self.name)
        if preserve_identity:
            new_layer.uid = self.uid
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.onion_skin_enabled = self.onion_skin_enabled
        if deep_copy:
            new_layer.image = self.image.copy()
        else:
            new_layer.image = QImage(self.image)
        new_layer._copy_non_transparent_bounds_from(self)
        return new_layer

    def apply_key_state_from(
        self, other: "Layer", *, deep_copy: bool = False
    ) -> None:
        """Copy image, visibility, and opacity from *other* without changing identity."""

        if deep_copy:
            self.image = other.image.copy()
        else:
            self.image = QImage(other.image)
        self.visible = other.visible
        self.opacity = other.opacity
        self.onion_skin_enabled = other.onion_skin_enabled
        self.on_image_change.emit()
        if isinstance(other, Layer):
            self._copy_non_transparent_bounds_from(other)
        else:
            self._non_transparent_bounds = None
            self._non_transparent_bounds_dirty = True

    def get_properties(self):
        """Returns a dictionary of layer properties."""
        return {
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "onion_skin_enabled": self.onion_skin_enabled,
        }

    @classmethod
    def from_qimage(cls, qimage, name):
        """Creates a new layer from a QImage."""
        width = qimage.width()
        height = qimage.height()
        layer = cls(width, height, name)
        layer.image = qimage
        layer._non_transparent_bounds = None
        layer._non_transparent_bounds_dirty = True
        return layer

    def flip_horizontal(self):
        self.image = self.image.flipped(Qt.Horizontal)
        self.on_image_change.emit()

    def flip_vertical(self):
        self.image = self.image.flipped(Qt.Vertical)
        self.on_image_change.emit()

    def _mark_non_transparent_bounds_dirty(self) -> None:
        self._non_transparent_bounds_dirty = True

    def _set_non_transparent_bounds(self, bounds: QRect | None) -> None:
        if bounds is None:
            self._non_transparent_bounds = None
        else:
            self._non_transparent_bounds = QRect(bounds)
        self._non_transparent_bounds_dirty = False

    def _copy_non_transparent_bounds_from(self, other: "Layer") -> None:
        if other._non_transparent_bounds_dirty:
            self._non_transparent_bounds = None
            self._non_transparent_bounds_dirty = True
        else:
            self._set_non_transparent_bounds(other._non_transparent_bounds)

    def mark_non_transparent_bounds_dirty(self) -> None:
        self._non_transparent_bounds_dirty = True

    @property
    def non_transparent_bounds(self) -> QRect | None:
        if self._non_transparent_bounds_dirty:
            self._recalculate_non_transparent_bounds()
        if self._non_transparent_bounds is None:
            return None
        return QRect(self._non_transparent_bounds)

    def _recalculate_non_transparent_bounds(self) -> None:
        bounds = self._calculate_non_transparent_bounds()
        if bounds is None or not bounds.isValid() or bounds.isEmpty():
            self._non_transparent_bounds = None
        else:
            self._non_transparent_bounds = bounds
        self._non_transparent_bounds_dirty = False

    def _calculate_non_transparent_bounds(self) -> QRect | None:
        image = getattr(self, "image", None)
        if image is None or image.isNull():
            return None

        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return None

        left = width
        right = -1
        top = height
        bottom = -1

        for y in range(height):
            row_left = None
            row_right = None

            for x in range(width):
                if image.pixelColor(x, y).alpha() > 0:
                    row_left = x
                    break

            if row_left is None:
                continue

            for x in range(width - 1, -1, -1):
                if image.pixelColor(x, y).alpha() > 0:
                    row_right = x
                    break

            if row_right is None:
                continue

            if row_left < left:
                left = row_left
            if row_right > right:
                right = row_right
            if top == height:
                top = y
            bottom = y

        if right < left or bottom < top:
            return None

        return QRect(left, top, right - left + 1, bottom - top + 1)
