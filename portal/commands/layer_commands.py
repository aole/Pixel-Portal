from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from portal.core.command import Command
from PySide6.QtGui import QTransform, QImage, QPainter, QPainterPath
from PySide6.QtCore import Qt, QPoint, QPointF, QBuffer
from PIL import Image
from PIL.ImageQt import ImageQt
import io

if TYPE_CHECKING:
    from portal.core.document import Document

# Importing `rembg` at module load time pulls in heavy dependencies and can
# significantly slow down or even hang test collection.  To keep the import
# lightweight, defer it until background removal is actually requested.
rembg_remove = None


def _merge_layer_down_with_union(document: 'Document', layer_index: int) -> bool:
    layer_manager = document.layer_manager
    try:
        layer_manager.merge_layer_down(layer_index)
    except IndexError:
        return False
    return True


def _merge_layer_down_current_frame(document: 'Document', layer_index: int) -> bool:
    return _merge_layer_down_with_union(document, layer_index)


@dataclass(slots=True)
class _LayerStateSnapshot:
    layer: "Layer"
    snapshot: "Layer"


@dataclass(slots=True)
class _MergeBeforeState:
    top: _LayerStateSnapshot
    bottom: _LayerStateSnapshot
    top_index: int
    bottom_index: int
    active_layer_index: int


@dataclass(slots=True)
class _MergeAfterState:
    bottom: _LayerStateSnapshot
    active_layer_index: int


@dataclass(slots=True)
class _LayerManagerState:
    snapshot: "LayerManager"
    layer_lookup: dict[int, "Layer"]


def _capture_layer_state(layer: "Layer") -> _LayerStateSnapshot:
    return _LayerStateSnapshot(layer=layer, snapshot=layer.clone(deep_copy=True))


def _restore_layer_state(state: _LayerStateSnapshot) -> None:
    from portal.core.layer import Layer

    layer = state.layer
    source = state.snapshot

    if not isinstance(layer, Layer):
        return

    existing_keys = {key.frame_number: key for key in layer.keys}
    new_keys = []

    for source_key in source.keys:
        key = existing_keys.pop(source_key.frame_number, None)
        if key is None:
            key = source_key.clone(deep_copy=True)
            layer._register_key(key)
        else:
            key.apply_state_from(source_key, deep_copy=True, emit_change=False)
        key.frame_number = source_key.frame_number
        new_keys.append(key)

    for stale_key in existing_keys.values():
        try:
            layer.keys.remove(stale_key)
        except ValueError:
            pass
        stale_key.setParent(None)

    layer.keys = new_keys
    layer.name = source.name
    layer.visible = source.visible
    layer.opacity = source.opacity
    layer.onion_skin_enabled = source.onion_skin_enabled

    try:
        layer.set_active_key_index(source.active_key_index)
    except (IndexError, ValueError):
        layer.set_active_key_index(0 if layer.keys else -1)

    layer.on_image_change.emit()


def _build_merge_before_state(layer_manager, layer_index: int) -> _MergeBeforeState | None:
    if not (0 < layer_index < len(layer_manager.layers)):
        return None

    top_index = layer_index
    bottom_index = layer_index - 1

    top_layer = layer_manager.layers[top_index]
    bottom_layer = layer_manager.layers[bottom_index]

    return _MergeBeforeState(
        top=_capture_layer_state(top_layer),
        bottom=_capture_layer_state(bottom_layer),
        top_index=top_index,
        bottom_index=bottom_index,
        active_layer_index=layer_manager.active_layer_index,
    )


def _build_merge_after_state(layer_manager, before_state: _MergeBeforeState) -> _MergeAfterState:
    return _MergeAfterState(
        bottom=_capture_layer_state(before_state.bottom.layer),
        active_layer_index=layer_manager.active_layer_index,
    )


def _undo_merge_state(layer_manager, before_state: _MergeBeforeState) -> None:
    layers = layer_manager.layers

    try:
        current_index = layers.index(before_state.top.layer)
    except ValueError:
        current_index = None

    if current_index is not None and current_index != before_state.top_index:
        layers.pop(current_index)
        current_index = None

    if current_index is None:
        insert_at = min(before_state.top_index, len(layers))
        layers.insert(insert_at, before_state.top.layer)
        before_state.top.layer.attach_to_manager(layer_manager)

    _restore_layer_state(before_state.bottom)
    _restore_layer_state(before_state.top)

    layer_manager.active_layer_index = before_state.active_layer_index
    layer_manager.layer_structure_changed.emit()


def _redo_merge_state(layer_manager, before_state: _MergeBeforeState, after_state: _MergeAfterState) -> None:
    layers = layer_manager.layers

    _restore_layer_state(after_state.bottom)

    try:
        top_index = layers.index(before_state.top.layer)
    except ValueError:
        top_index = None

    if top_index is None:
        return

    layer_manager.remove_layer(top_index)
    layer_manager.active_layer_index = after_state.active_layer_index


def _capture_layer_manager(layer_manager):
    from portal.core.layer import Layer  # Local import to avoid cycles in TYPE_CHECKING.

    snapshot = layer_manager.clone(deep_copy=True)
    layer_lookup: dict[int, Layer] = {}
    for layer in layer_manager.layers:
        layer_lookup[getattr(layer, "uid", id(layer))] = layer
    return _LayerManagerState(snapshot, layer_lookup)


def _restore_layer_manager(target_manager, state: _LayerManagerState):
    from portal.core.layer import Layer

    snapshot = state.snapshot
    lookup = state.layer_lookup

    def _apply_layer_state(destination: Layer, source: Layer) -> Layer:
        existing_keys = {key.frame_number: key for key in destination.keys}
        new_keys = []
        for source_key in source.keys:
            key = existing_keys.pop(source_key.frame_number, None)
            if key is None:
                key = source_key.clone(deep_copy=True)
                destination._register_key(key)
            else:
                key.apply_state_from(source_key, deep_copy=True, emit_change=False)
            key.frame_number = source_key.frame_number
            new_keys.append(key)

        # Remove any keys that are no longer present in the source snapshot.
        for stale_key in existing_keys.values():
            try:
                destination.keys.remove(stale_key)
            except ValueError:
                pass
            stale_key.setParent(None)

        destination.keys = new_keys

        # Mirror the layer level properties from the snapshot.
        destination.name = source.name
        destination.visible = source.visible
        destination.opacity = source.opacity
        destination.onion_skin_enabled = source.onion_skin_enabled

        try:
            destination.set_active_key_index(source.active_key_index)
        except (IndexError, ValueError):
            destination.set_active_key_index(0 if destination.keys else -1)

        destination.on_image_change.emit()
        return destination

    target_manager._current_frame = snapshot.current_frame

    restored_layers: list[Layer] = []
    for source_layer in snapshot.layers:
        uid = getattr(source_layer, "uid", None)
        destination = lookup.get(uid)
        if destination is None:
            destination = source_layer.clone(deep_copy=True)
        destination = _apply_layer_state(destination, source_layer)
        destination.attach_to_manager(target_manager)
        restored_layers.append(destination)

    target_manager.layers = restored_layers
    target_manager.active_layer_index = snapshot.active_layer_index
    target_manager.layer_structure_changed.emit()


def apply_qimage_transform_nearest(
    destination: QImage, source: QImage, transform: QTransform
) -> bool:
    """Map *source* into *destination* using nearest-neighbour sampling.

    Parameters
    ----------
    destination:
        The image that receives the transformed pixels. Pixels outside the
        transformed source are left untouched.
    source:
        Image providing the pixels to sample from.
    transform:
        Transform mapping source coordinates into destination coordinates.

    Returns
    -------
    bool
        ``True`` when the transform is invertible. ``False`` otherwise, in
        which case *destination* is left unmodified.
    """

    inverse_transform, invertible = transform.inverted()
    if not invertible:
        return False

    source_width = source.width()
    source_height = source.height()
    dest_width = destination.width()
    dest_height = destination.height()

    for y in range(dest_height):
        for x in range(dest_width):
            source_point = inverse_transform.map(QPointF(x, y))
            sx_float = source_point.x()
            sy_float = source_point.y()
            if 0 <= sx_float < source_width and 0 <= sy_float < source_height:
                sx = int(sx_float)
                sy = int(sy_float)
                color = source.pixelColor(sx, sy)
                if color.alpha() > 0:
                    destination.setPixelColor(x, y, color)

    return True


class MergeLayerDownCommand(Command):
    def __init__(self, document: 'Document', layer_index: int):
        self.document = document
        self.layer_index = layer_index
        self._before_state = None
        self._after_state = None

    def execute(self):
        layer_manager = self.document.layer_manager
        if self._before_state is None:
            before_state = _build_merge_before_state(layer_manager, self.layer_index)
            if before_state is None:
                return
            self._before_state = before_state
            self.layer_index = before_state.top_index
            if not _merge_layer_down_with_union(self.document, self.layer_index):
                self._before_state = None
                return
            self._after_state = _build_merge_after_state(layer_manager, self._before_state)
        else:
            if self._after_state is None or self._before_state is None:
                return
            _redo_merge_state(layer_manager, self._before_state, self._after_state)

    def undo(self):
        if self._before_state is None:
            return
        _undo_merge_state(self.document.layer_manager, self._before_state)


class MergeLayerDownCurrentFrameCommand(Command):
    def __init__(self, document: 'Document', layer_index: int):
        self.document = document
        self.layer_index = layer_index
        self._before_state = None
        self._after_state = None

    def execute(self):
        layer_manager = self.document.layer_manager
        if self._before_state is None:
            before_state = _build_merge_before_state(layer_manager, self.layer_index)
            if before_state is None:
                return
            self._before_state = before_state
            self.layer_index = before_state.top_index
            if not _merge_layer_down_current_frame(self.document, self.layer_index):
                self._before_state = None
                return
            self._after_state = _build_merge_after_state(layer_manager, self._before_state)
        else:
            if self._after_state is None or self._before_state is None:
                return
            _redo_merge_state(layer_manager, self._before_state, self._after_state)

    def undo(self):
        if self._before_state is None:
            return
        _undo_merge_state(self.document.layer_manager, self._before_state)


class CollapseLayersCommand(Command):
    def __init__(self, document: 'Document'):
        self.document = document
        self._before_state = None
        self._after_state = None

    def execute(self):
        layer_manager = self.document.layer_manager
        layer_count = len(layer_manager.layers)
        if layer_count <= 1:
            return

        if self._before_state is None:
            self._before_state = _capture_layer_manager(layer_manager)
            for index in range(layer_count - 1, 0, -1):
                if not _merge_layer_down_with_union(self.document, index):
                    self._before_state = None
                    return
            self._after_state = _capture_layer_manager(layer_manager)
        else:
            if self._after_state is None:
                return
            _restore_layer_manager(layer_manager, self._after_state)

    def undo(self):
        if self._before_state is None:
            return
        _restore_layer_manager(self.document.layer_manager, self._before_state)


class SetLayerVisibleCommand(Command):
    def __init__(self, layer_manager: 'LayerManager', layer_index: int, visible: bool):
        self.layer_manager = layer_manager
        self.layer_index = layer_index
        self.visible = bool(visible)

        try:
            layer = self.layer_manager.layers[self.layer_index]
        except IndexError:
            layer = None

        self.previous_visible = bool(getattr(layer, "visible", False))
        self._layer_uid = getattr(layer, "uid", None)
        self._instances = None
        self._previous_values = None

    def _collect_instances(self):
        if self._instances is not None:
            return self._instances

        instances = []
        layer = None
        try:
            layer = self.layer_manager.layers[self.layer_index]
        except IndexError:
            layer = None

        if layer is not None:
            instances = [layer]

        self._instances = instances
        return self._instances

    def _apply(self, value: bool) -> None:
        for instance in self._collect_instances():
            instance.visible = value

    def execute(self):
        instances = self._collect_instances()
        if self._previous_values is None:
            self._previous_values = [instance.visible for instance in instances]
        self._apply(self.visible)
        self.layer_manager.layer_visibility_changed.emit(self.layer_index)

    def undo(self):
        if self._previous_values is None:
            return
        instances = self._collect_instances()
        for instance, previous in zip(instances, self._previous_values):
            instance.visible = previous
        self.layer_manager.layer_visibility_changed.emit(self.layer_index)


class SetLayerOnionSkinCommand(Command):
    def __init__(self, layer_manager: 'LayerManager', layer_index: int, enabled: bool):
        self.layer_manager = layer_manager
        self.layer_index = layer_index
        self.enabled = bool(enabled)

        try:
            layer = self.layer_manager.layers[self.layer_index]
        except IndexError:
            layer = None

        self.previous_enabled = bool(getattr(layer, "onion_skin_enabled", False))
        self._layer_uid = getattr(layer, "uid", None)
        self._instances = None
        self._previous_values = None

    def _collect_instances(self):
        if self._instances is not None:
            return self._instances

        instances = []
        layer = None
        try:
            layer = self.layer_manager.layers[self.layer_index]
        except IndexError:
            layer = None

        if layer is not None:
            instances = [layer]

        self._instances = instances
        return self._instances

    def _apply(self, value: bool) -> None:
        for instance in self._collect_instances():
            instance.onion_skin_enabled = value

    def execute(self):
        instances = self._collect_instances()
        if self._previous_values is None:
            self._previous_values = [
                bool(getattr(instance, "onion_skin_enabled", False))
                for instance in instances
            ]
        self._apply(self.enabled)
        self.layer_manager.layer_onion_skin_changed.emit(self.layer_index)

    def undo(self):
        if self._previous_values is None:
            return
        instances = self._collect_instances()
        for instance, previous in zip(instances, self._previous_values):
            instance.onion_skin_enabled = previous
        self.layer_manager.layer_onion_skin_changed.emit(self.layer_index)


class RotateLayerCommand(Command):
    def __init__(
        self,
        layer: 'Layer',
        angle_degrees: float,
        center_point: QPoint,
        selection_shape: QPainterPath | None,
        *,
        canvas=None,
        rotated_selection_shape: QPainterPath | None = None,
    ):
        self.layer = layer
        self.angle_degrees = angle_degrees
        self.center_point = center_point
        self.selection_shape = QPainterPath(selection_shape) if selection_shape is not None else None
        self.before_selection_shape = QPainterPath(selection_shape) if selection_shape is not None else None
        self.after_selection_shape = (
            QPainterPath(rotated_selection_shape)
            if rotated_selection_shape is not None
            else None
        )
        self.canvas = canvas
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        image_to_modify = self.before_image.copy()
        painter = QPainter(image_to_modify)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        center = self.center_point
        transform = QTransform().translate(center.x(), center.y()).rotate(self.angle_degrees).translate(-center.x(), -center.y())

        if self.selection_shape:
            selected_pixels = QImage(self.before_image.size(), self.before_image.format())
            selected_pixels.fill(Qt.transparent)

            selection_painter = QPainter(selected_pixels)
            selection_painter.setRenderHint(QPainter.Antialiasing, False)
            selection_painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            selection_painter.setClipPath(self.selection_shape)
            selection_painter.drawImage(0, 0, self.before_image)
            selection_painter.end()

            painter.setClipPath(self.selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(self.selection_shape, Qt.transparent)
            painter.end()

            inverse_transform, invertible = transform.inverted()
            if not invertible:
                self.layer.image = image_to_modify
                self.layer.on_image_change.emit()
                return

            width = selected_pixels.width()
            height = selected_pixels.height()

            for y in range(image_to_modify.height()):
                for x in range(image_to_modify.width()):
                    source_point = inverse_transform.map(QPointF(x, y))
                    sx_float = source_point.x()
                    sy_float = source_point.y()
                    if 0 <= sx_float < width and 0 <= sy_float < height:
                        sx = int(sx_float)
                        sy = int(sy_float)
                        color = selected_pixels.pixelColor(sx, sy)
                        if color.alpha() > 0:
                            image_to_modify.setPixelColor(x, y, color)
            if self.after_selection_shape is None:
                self.after_selection_shape = transform.map(self.selection_shape)
        else:
            # If no selection, rotate the whole image
            # We need to clear the painter's own background before drawing
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(image_to_modify.rect(), Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setTransform(transform)
            painter.drawImage(0, 0, self.before_image)
            painter.end()
            self.layer.image = image_to_modify
            self.layer.on_image_change.emit()
            return

        self.layer.image = image_to_modify
        self.layer.on_image_change.emit()

        if self.canvas and (self.before_selection_shape is not None or self.after_selection_shape is not None):
            if self.after_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(QPainterPath(self.after_selection_shape))
            else:
                self.canvas._update_selection_and_emit_size(None)

    def undo(self):
        if self.before_image:
            self.layer.image = self.before_image.copy()
            self.layer.on_image_change.emit()

        if self.canvas and (self.before_selection_shape is not None or self.after_selection_shape is not None):
            if self.before_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(QPainterPath(self.before_selection_shape))
            else:
                self.canvas._update_selection_and_emit_size(None)


class ScaleLayerCommand(Command):
    def __init__(
        self,
        layer: 'Layer',
        scale_x: float,
        scale_y: float,
        center_point: QPoint,
        selection_shape: QPainterPath | None,
        *,
        canvas=None,
        scaled_selection_shape: QPainterPath | None = None,
    ):
        self.layer = layer
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.center_point = center_point
        self.selection_shape = (
            QPainterPath(selection_shape) if selection_shape is not None else None
        )
        self.before_selection_shape = (
            QPainterPath(selection_shape) if selection_shape is not None else None
        )
        self.after_selection_shape = (
            QPainterPath(scaled_selection_shape)
            if scaled_selection_shape is not None
            else None
        )
        self.canvas = canvas
        self.before_image = None

    def _build_transform(self) -> QTransform:
        center = self.center_point
        return (
            QTransform()
            .translate(center.x(), center.y())
            .scale(self.scale_x, self.scale_y)
            .translate(-center.x(), -center.y())
        )

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        transform = self._build_transform()

        if self.selection_shape:
            image_to_modify = self.before_image.copy()
            painter = QPainter(image_to_modify)
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            painter.setClipPath(self.selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(self.selection_shape, Qt.transparent)
            painter.end()

            selected_pixels = QImage(
                self.before_image.size(),
                self.before_image.format(),
            )
            selected_pixels.fill(Qt.transparent)

            selection_painter = QPainter(selected_pixels)
            selection_painter.setRenderHint(QPainter.Antialiasing, False)
            selection_painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            selection_painter.setClipPath(self.selection_shape)
            selection_painter.drawImage(0, 0, self.before_image)
            selection_painter.end()

            if not apply_qimage_transform_nearest(
                image_to_modify, selected_pixels, transform
            ):
                self.layer.image = self.before_image.copy()
                self.layer.on_image_change.emit()
                return

            if self.after_selection_shape is None:
                self.after_selection_shape = transform.map(self.selection_shape)
        else:
            image_to_modify = QImage(
                self.before_image.size(),
                self.before_image.format(),
            )
            image_to_modify.fill(Qt.transparent)

            if not apply_qimage_transform_nearest(image_to_modify, self.before_image, transform):
                return

        self.layer.image = image_to_modify
        self.layer.on_image_change.emit()

        if self.canvas and (
            self.before_selection_shape is not None
            or self.after_selection_shape is not None
        ):
            if self.after_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(
                    QPainterPath(self.after_selection_shape)
                )
            else:
                self.canvas._update_selection_and_emit_size(None)

    def undo(self):
        if self.before_image:
            self.layer.image = self.before_image.copy()
            self.layer.on_image_change.emit()

        if self.canvas and (
            self.before_selection_shape is not None
            or self.after_selection_shape is not None
        ):
            if self.before_selection_shape is not None:
                self.canvas._update_selection_and_emit_size(
                    QPainterPath(self.before_selection_shape)
                )
            else:
                self.canvas._update_selection_and_emit_size(None)

class RemoveBackgroundCommand(Command):
    def __init__(self, layer):
        self.layer = layer
        self.before_image = layer.image.copy()

    def execute(self):
        global rembg_remove
        if rembg_remove is None:
            try:
                from rembg import remove as rembg_remove  # type: ignore
            except Exception:
                print(
                    "Background removal unavailable: rembg or its dependencies are not installed."
                )
                return
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        self.before_image.save(buffer, "PNG")
        pil_image = Image.open(io.BytesIO(buffer.data()))
        try:
            result = rembg_remove(pil_image)
        except Exception as e:
            print(f"Background removal failed: {e}")
            return
        q_image = ImageQt(result.convert("RGBA"))
        self.layer.image = QImage(q_image)
        self.layer.on_image_change.emit()

    def undo(self):
        self.layer.image = self.before_image.copy()
        self.layer.on_image_change.emit()
