from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, QRect, Signal

from .key import Key

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

    def __init__(
        self,
        width: int,
        height: int,
        name: str,
        *,
        key: Key | None = None,
    ):
        super().__init__()
        if not isinstance(name, str) or not name:
            raise ValueError("Layer name must be a non-empty string.")

        self._name = name
        self._visible = True
        self.opacity = 1.0  # 0.0 (transparent) to 1.0 (opaque)
        self._onion_skin_enabled = False

        if key is None:
            key = Key(width, height)
        key.setParent(self)
        self.key = key
        self.key.image_changed.connect(self.on_image_change.emit)
        self.on_image_change.connect(self.key.mark_non_transparent_bounds_dirty)

        self.uid = self._next_uid()

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

    @property
    def image(self) -> QImage:
        return self.key.image

    @image.setter
    def image(self, value: QImage) -> None:
        self.key.image = value

    def clear(self, selection=None):
        """Fills the layer with transparent color."""
        self.key.clear(selection)

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

        new_layer = Layer(
            self.image.width(), self.image.height(), self.name, key=self.key.clone(deep_copy=deep_copy)
        )
        if preserve_identity:
            new_layer.uid = self.uid
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.onion_skin_enabled = self.onion_skin_enabled
        return new_layer

    def apply_key_state_from(
        self, other: "Layer | Key", *, deep_copy: bool = False
    ) -> None:
        """Copy image, visibility, and opacity from *other* without changing identity."""

        is_layer = isinstance(other, Layer)
        other_key = other.key if is_layer else other
        self.key.apply_state_from(other_key, deep_copy=deep_copy)
        if is_layer:
            self.visible = other.visible
            self.opacity = other.opacity
            self.onion_skin_enabled = other.onion_skin_enabled

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
        key = Key.from_qimage(qimage)
        layer = cls(width, height, name, key=key)
        return layer

    def flip_horizontal(self):
        self.key.flip_horizontal()

    def flip_vertical(self):
        self.key.flip_vertical()

    def mark_non_transparent_bounds_dirty(self) -> None:
        self.key.mark_non_transparent_bounds_dirty()

    @property
    def non_transparent_bounds(self) -> QRect | None:
        return self.key.non_transparent_bounds
