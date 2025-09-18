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


def _find_layer_with_uid(layer_manager, layer_uid):
    for layer in layer_manager.layers:
        if getattr(layer, "uid", None) == layer_uid:
            return layer
    return None


def _merge_layer_down_with_union(document: 'Document', layer_index: int) -> bool:
    layer_manager = document.layer_manager
    if not (0 < layer_index < len(layer_manager.layers)):
        return False

    top_layer = layer_manager.layers[layer_index]
    bottom_layer = layer_manager.layers[layer_index - 1]

    top_uid = getattr(top_layer, "uid", None)
    bottom_uid = getattr(bottom_layer, "uid", None)
    if top_uid is None or bottom_uid is None:
        return False

    frame_manager = document.frame_manager

    top_keys = set(frame_manager.layer_keys.get(top_uid, {0}))
    bottom_keys = set(frame_manager.layer_keys.get(bottom_uid, {0}))
    union_keys = sorted(top_keys | bottom_keys)

    bottom_keys_set = frame_manager.layer_keys.get(bottom_uid)
    if bottom_keys_set is None:
        bottom_keys_set = frame_manager.layer_keys[bottom_uid] = {0}

    for frame_index in union_keys:
        frame_manager.ensure_frame(frame_index)
        if frame_index not in bottom_keys_set:
            frame_manager.add_layer_key(bottom_uid, frame_index)
            bottom_keys_set = frame_manager.layer_keys.get(bottom_uid, bottom_keys_set)

        top_source_index = frame_manager.resolve_layer_key_frame_index(top_uid, frame_index)
        if top_source_index is None:
            continue
        if not (0 <= top_source_index < len(frame_manager.frames)):
            continue

        top_manager = frame_manager.frames[top_source_index].layer_manager
        target_manager = frame_manager.frames[frame_index].layer_manager

        top_source_layer = _find_layer_with_uid(top_manager, top_uid)
        bottom_target_layer = _find_layer_with_uid(target_manager, bottom_uid)

        if top_source_layer is None or bottom_target_layer is None:
            continue

        painter = QPainter(bottom_target_layer.image)
        painter.setOpacity(top_source_layer.opacity)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.drawImage(0, 0, top_source_layer.image)
        painter.end()

        bottom_target_layer.on_image_change.emit()

    layer_manager.remove_layer(layer_index)
    document.unregister_layer(top_uid)
    return True


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
        if self._before_state is None:
            if not (0 < self.layer_index < len(self.document.layer_manager.layers)):
                return
            self._before_state = self.document.frame_manager.clone()
            if not _merge_layer_down_with_union(self.document, self.layer_index):
                self._before_state = None
                return
            self._after_state = self.document.frame_manager.clone()
        else:
            if self._after_state is None:
                return
            self.document.apply_frame_manager_snapshot(self._after_state)

    def undo(self):
        if self._before_state is None:
            return
        self.document.apply_frame_manager_snapshot(self._before_state)


class CollapseLayersCommand(Command):
    def __init__(self, document: 'Document'):
        self.document = document
        self._before_state = None
        self._after_state = None

    def execute(self):
        layer_count = len(self.document.layer_manager.layers)
        if layer_count <= 1:
            return

        if self._before_state is None:
            self._before_state = self.document.frame_manager.clone()
            for index in range(layer_count - 1, 0, -1):
                _merge_layer_down_with_union(self.document, index)
            self._after_state = self.document.frame_manager.clone()
        else:
            if self._after_state is None:
                return
            self.document.apply_frame_manager_snapshot(self._after_state)

    def undo(self):
        if self._before_state is None:
            return
        self.document.apply_frame_manager_snapshot(self._before_state)


class SetLayerVisibleCommand(Command):
    def __init__(self, layer_manager: 'LayerManager', layer_index: int, visible: bool):
        self.layer_manager = layer_manager
        self.layer_index = layer_index
        self.visible = visible
        self.previous_visible = self.layer_manager.layers[self.layer_index].visible

    def execute(self):
        self.layer_manager.layers[self.layer_index].visible = self.visible
        self.layer_manager.layer_visibility_changed.emit(self.layer_index)

    def undo(self):
        self.layer_manager.layers[self.layer_index].visible = self.previous_visible
        self.layer_manager.layer_visibility_changed.emit(self.layer_index)


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
