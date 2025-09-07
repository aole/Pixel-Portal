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

        image_to_rotate = self.before_image
        center = self.center_point

        transform = QTransform().translate(center.x(), center.y()).rotate(self.angle_degrees).translate(-center.x(), -center.y())

        if self.selection_shape:
            # When there is a selection, we rotate the whole layer, but only apply
            # the rotated pixels inside the selection area.
            rotated_full_image = image_to_rotate.transformed(transform, Qt.SmoothTransformation)

            final_image = self.before_image.copy()
            painter = QPainter(final_image)
            painter.setClipPath(self.selection_shape)

            # Paste the rotated image back, centered on the rotation point
            x = center.x() - rotated_full_image.width() / 2
            y = center.y() - rotated_full_image.height() / 2
            painter.drawImage(QPoint(int(x), int(y)), rotated_full_image)
            painter.end()
            self.layer.image = final_image
        else:
            # Original logic for rotating the whole layer
            new_image = QImage(image_to_rotate.size(), QImage.Format_ARGB32)
            new_image.fill(Qt.transparent)
            painter = QPainter(new_image)
            painter.setTransform(transform)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawImage(0, 0, image_to_rotate)
            painter.end()
            self.layer.image = new_image

        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            self.layer.image = self.before_image.copy()
            self.layer.on_image_change.emit()
