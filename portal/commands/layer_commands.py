from portal.core.command import Command
from PySide6.QtGui import QTransform, QImage, QPainter, QPainterPath
from PySide6.QtCore import Qt, QPoint, QPointF, QBuffer
from PIL import Image
from PIL.ImageQt import ImageQt
import io

# Importing `rembg` at module load time pulls in heavy dependencies and can
# significantly slow down or even hang test collection.  To keep the import
# lightweight, defer it until background removal is actually requested.
rembg_remove = None


class MergeLayerDownCommand(Command):
    def __init__(self, layer_manager, layer_index):
        self.layer_manager = layer_manager
        self.layer_index = layer_index
        self.removed_layer = None
        self.original_bottom_image = None

    def execute(self):
        if not (0 < self.layer_index < len(self.layer_manager.layers)):
            return

        self.removed_layer = self.layer_manager.layers[self.layer_index]
        self.original_bottom_image = self.layer_manager.layers[self.layer_index - 1].image.copy()
        self.layer_manager.merge_layer_down(self.layer_index)

    def undo(self):
        if self.removed_layer is None or self.original_bottom_image is None:
            return

        # Restore the bottom layer's image
        self.layer_manager.layers[self.layer_index - 1].image = self.original_bottom_image

        # Re-insert the removed layer
        self.layer_manager.layers.insert(self.layer_index, self.removed_layer)

        # Adjust active layer and emit signals
        if self.layer_manager.active_layer_index >= self.layer_index - 1:
            self.layer_manager.active_layer_index += 1
        self.layer_manager.layer_structure_changed.emit()


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
                    sx = int(source_point.x())
                    sy = int(source_point.y())
                    if 0 <= sx < width and 0 <= sy < height:
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
