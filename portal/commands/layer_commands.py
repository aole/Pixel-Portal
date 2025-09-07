from portal.core.command import Command
from PySide6.QtGui import QTransform, QImage, QPainter, QPainterPath
from PySide6.QtCore import Qt, QPoint


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
    def __init__(self, layer: 'Layer', angle_degrees: float, center_point: QPoint, selection_shape: QPainterPath | None):
        self.layer = layer
        self.angle_degrees = angle_degrees
        self.center_point = center_point
        self.selection_shape = selection_shape
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
            # Clear the area within the selection
            painter.setClipPath(self.selection_shape)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.layer.image.rect(), Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw the rotated original image, clipped to the selection
            painter.setTransform(transform)
            painter.drawImage(0, 0, self.before_image)
        else:
            # If no selection, rotate the whole image
            painter.setTransform(transform)
            # We need to clear the painter's own background before drawing
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.layer.image.rect(), Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawImage(0, 0, self.before_image)

        painter.end()
        self.layer.image = image_to_modify
        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            self.layer.image = self.before_image.copy()
            self.layer.on_image_change.emit()
