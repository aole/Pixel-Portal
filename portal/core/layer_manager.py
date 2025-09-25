from __future__ import annotations

from portal.core.layer import Layer
from portal.core.key import Key
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPainter, QColor, QImage
from PIL.ImageQt import ImageQt
from portal.commands.layer_commands import SetLayerVisibleCommand, SetLayerOnionSkinCommand


class LayerManager(QObject):
    """
    Manages the stack of layers in a document.
    """
    layer_visibility_changed = Signal(int)
    layer_structure_changed = Signal()
    layer_onion_skin_changed = Signal(int)
    command_generated = Signal(object)

    def __init__(self, width: int, height: int, create_background: bool = True):
        super().__init__()
        self.width = width
        self.height = height
        self.layers: list[Layer] = []
        self.active_layer_index = -1
        self._document = None
        self._current_frame = 0

        if create_background:
            self.add_layer("Background")

    @property
    def active_layer(self) -> Layer | None:
        """Returns the currently active layer."""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    @property
    def document(self):
        """Return the document this manager belongs to, if any."""

        return self._document

    def set_document(self, document) -> None:
        """Assign the owning document so commands can reach frame data."""

        self._document = document
        for layer in self.layers:
            layer.attach_to_manager(self)

    # ------------------------------------------------------------------
    # Layer lookup helpers
    # ------------------------------------------------------------------
    def index_for_layer_uid(self, layer_uid: int | None) -> int | None:
        """Return the index of the layer with ``layer_uid`` if it exists."""

        if layer_uid is None:
            return None

        for index, layer in enumerate(self.layers):
            if getattr(layer, "uid", None) == layer_uid:
                return index

        return None

    def find_layer_by_uid(self, layer_uid: int | None) -> Layer | None:
        """Return the layer identified by ``layer_uid`` if present."""

        index = self.index_for_layer_uid(layer_uid)
        if index is None:
            return None
        return self.layers[index]

    def add_layer(self, name: str):
        """Adds a new layer to the top of the stack."""
        new_layer = Layer(self.width, self.height, name)
        new_layer.attach_to_manager(self)
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
        new_layer.attach_to_manager(self)

        painter = QPainter(new_layer.image)
        painter.drawImage(0, 0, q_image)
        painter.end()

        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.layer_structure_changed.emit()

    def remove_layer(self, index: int):
        """Removes the layer at the given index."""
        if len(self.layers) == 1:
            raise ValueError("Cannot remove the last layer.")

        layer = self.layers.pop(index)

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

    def merge_layer_down(self, index: int) -> None:
        """Merge the layer at ``index`` into the one directly below it."""

        if not (0 < index < len(self.layers)):
            raise IndexError("Cannot merge: invalid index or no layer below.")

        top_layer = self.layers[index]
        bottom_layer = self.layers[index - 1]

        top_frames = {key.frame_number: key for key in top_layer.keys}
        bottom_frames = {key.frame_number: key for key in bottom_layer.keys}
        union_frames = sorted(set(top_frames) | set(bottom_frames))

        def _insert_key_sorted(layer: Layer, key: Key) -> None:
            insert_at = len(layer.keys)
            for idx, existing in enumerate(layer.keys):
                if existing.frame_number > key.frame_number:
                    insert_at = idx
                    break
            layer.keys.insert(insert_at, key)

        for frame in union_frames:
            top_key = top_frames.get(frame)
            bottom_key = bottom_frames.get(frame)

            if bottom_key is None:
                if top_key is None:
                    continue
                new_key = top_key.clone(deep_copy=True)
                new_key.frame_number = frame
                bottom_layer._register_key(new_key)
                _insert_key_sorted(bottom_layer, new_key)
                bottom_frames[frame] = new_key
                bottom_key = new_key
                continue

            if top_key is None:
                continue

            painter = QPainter(bottom_key.image)
            painter.setOpacity(top_layer.opacity)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawImage(0, 0, top_key.image)
            painter.end()
            bottom_key.image_changed.emit()

        if bottom_layer._layer_manager is self:
            current_frame = self.current_frame
            resolved_index = bottom_layer._index_for_frame(current_frame)
            bottom_layer.set_active_key_index(resolved_index)

        self.remove_layer(index)

    def toggle_visibility(self, index: int):
        """Toggles the visibility of the layer at the given index."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")

        layer = self.layers[index]
        command = SetLayerVisibleCommand(self, index, not layer.visible)
        self.command_generated.emit(command)

    def toggle_onion_skin(self, index: int) -> None:
        """Toggle the onion-skin participation flag for the layer at ``index``."""
        if not (0 <= index < len(self.layers)):
            raise IndexError("Layer index out of range.")

        layer = self.layers[index]
        command = SetLayerOnionSkinCommand(self, index, not layer.onion_skin_enabled)
        self.command_generated.emit(command)

    def clone(self, *, deep_copy: bool = False):
        """Create a copy of the layer manager."""
        new_manager = LayerManager(self.width, self.height, create_background=False)
        new_manager.layers = [layer.clone(deep_copy=deep_copy) for layer in self.layers]
        for layer in new_manager.layers:
            layer.attach_to_manager(new_manager)
        new_manager.active_layer_index = self.active_layer_index
        new_manager._document = self._document
        new_manager._current_frame = self._current_frame
        return new_manager

    @property
    def current_frame(self) -> int:
        return self._current_frame

    def set_current_frame(self, frame: int) -> None:
        if frame == self._current_frame:
            return
        self._current_frame = frame
        for layer in self.layers:
            layer.on_current_frame_changed(self._current_frame)
