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
        keys: list[Key] | None = None,
    ):
        super().__init__()
        if not isinstance(name, str) or not name:
            raise ValueError("Layer name must be a non-empty string.")

        self._name = name
        self._visible = True
        self.opacity = 1.0  # 0.0 (transparent) to 1.0 (opaque)
        self._onion_skin_enabled = False
        self._active_key_index = 0
        if keys is not None:
            provided_keys = list(keys)
        elif key is not None:
            provided_keys = [key]
        else:
            provided_keys = [Key(width, height, frame_number=0)]
        if not provided_keys:
            raise ValueError("Layer must be initialized with at least one key.")

        self.keys: list[Key] = []
        for key_instance in provided_keys:
            self._register_key(key_instance)
            self.keys.append(key_instance)

        self.uid = self._next_uid()

    def _register_key(self, key: Key) -> None:
        key.setParent(self)
        key.image_changed.connect(self.on_image_change.emit)
        key.image_changed.connect(key.mark_non_transparent_bounds_dirty)

    @property
    def active_key(self) -> Key:
        if not self.keys:
            raise ValueError("Layer does not contain any keys.")
        if not (0 <= self._active_key_index < len(self.keys)):
            self._active_key_index = 0
        return self.keys[self._active_key_index]

    @property
    def active_key_index(self) -> int:
        return self._active_key_index

    def set_active_key_index(self, index: int) -> None:
        if not self.keys:
            raise ValueError("Layer does not contain any keys.")
        if not (0 <= index < len(self.keys)):
            raise IndexError("Active key index out of range.")
        self._active_key_index = index

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
        return self.active_key.image

    @image.setter
    def image(self, value: QImage) -> None:
        self.active_key.image = value

    def clear(self, selection=None):
        """Fills the layer with transparent color."""
        self.active_key.clear(selection)

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

        cloned_keys = [key.clone(deep_copy=deep_copy) for key in self.keys]
        new_layer = Layer(
            self.image.width(),
            self.image.height(),
            self.name,
            keys=cloned_keys,
        )
        if preserve_identity:
            new_layer.uid = self.uid
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.onion_skin_enabled = self.onion_skin_enabled
        try:
            new_layer.set_active_key_index(self._active_key_index)
        except (IndexError, ValueError):
            new_layer.set_active_key_index(0)
        return new_layer

    def apply_key_state_from(
        self, other: "Layer | Key", *, deep_copy: bool = False
    ) -> None:
        """Copy image, visibility, and opacity from *other* without changing identity."""

        is_layer = isinstance(other, Layer)
        other_key = other.active_key if is_layer else other
        if not isinstance(other_key, Key):
            raise TypeError("other must be a Layer or Key instance")
        self.active_key.apply_state_from(other_key, deep_copy=deep_copy)
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
        key = Key.from_qimage(qimage, frame_number=0)
        layer = cls(width, height, name, keys=[key])
        return layer

    def flip_horizontal(self):
        self.active_key.flip_horizontal()

    def flip_vertical(self):
        self.active_key.flip_vertical()

    def mark_non_transparent_bounds_dirty(self) -> None:
        self.active_key.mark_non_transparent_bounds_dirty()

    @property
    def non_transparent_bounds(self) -> QRect | None:
        return self.active_key.non_transparent_bounds
