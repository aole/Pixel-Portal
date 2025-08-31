from abc import ABC, abstractmethod
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QPainterPath, QPainterPathStroker
from PySide6.QtCore import QRect, QPoint, Qt, QSize
from .layer import Layer
from .document import Document
from .drawing import Drawing


class Command(ABC):
    """
    Abstract base class for all commands.
    """

    @abstractmethod
    def execute(self):
        """
        Executes the command.
        """
        raise NotImplementedError

    @abstractmethod
    def undo(self):
        """
        Undoes the command.
        """
        raise NotImplementedError


class DrawCommand(Command):
    def __init__(self, layer: Layer, points: list[QPoint], color: QColor, width: int, brush_type: str, document, selection_shape: QPainterPath | None, erase: bool = False, mirror_x: bool = False, mirror_y: bool = False):
        self.layer = layer
        self.points = points
        self.color = color
        self.width = width
        self.brush_type = brush_type
        self.erase = erase
        self.document = document
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.selection_shape = selection_shape
        self.drawing = Drawing()

        self.bounding_rect = self._calculate_bounding_rect()
        self.before_image = None

    def _calculate_bounding_rect(self) -> QRect:
        if not self.points:
            return QRect()

        doc_width = self.document.width
        doc_height = self.document.height
        mirror_x = self.mirror_x
        mirror_y = self.mirror_y

        # Create the original path
        original_path = QPainterPath(self.points[0])
        for i in range(1, len(self.points)):
            original_path.lineTo(self.points[i])

        # Create a combined path including mirrored versions
        combined_path = QPainterPath()
        combined_path.addPath(original_path)

        if mirror_x:
            mirrored_path_x = QPainterPath()
            mirrored_path_x.moveTo(doc_width - 1 - self.points[0].x(), self.points[0].y())
            for i in range(1, len(self.points)):
                mirrored_path_x.lineTo(doc_width - 1 - self.points[i].x(), self.points[i].y())
            combined_path.addPath(mirrored_path_x)

        if mirror_y:
            mirrored_path_y = QPainterPath()
            mirrored_path_y.moveTo(self.points[0].x(), doc_height - 1 - self.points[0].y())
            for i in range(1, len(self.points)):
                mirrored_path_y.lineTo(self.points[i].x(), doc_height - 1 - self.points[i].y())
            combined_path.addPath(mirrored_path_y)

        if mirror_x and mirror_y:
            mirrored_path_xy = QPainterPath()
            mirrored_path_xy.moveTo(doc_width - 1 - self.points[0].x(), doc_height - 1 - self.points[0].y())
            for i in range(1, len(self.points)):
                mirrored_path_xy.lineTo(doc_width - 1 - self.points[i].x(), doc_height - 1 - self.points[i].y())
            combined_path.addPath(mirrored_path_xy)


        stroker = QPainterPathStroker()
        stroker.setWidth(self.width)
        stroke = stroker.createStroke(combined_path)
        # Add a 1 pixel buffer for safety
        rect = stroke.boundingRect().toRect().adjusted(-1, -1, 1, 1)

        # Intersect with layer bounds to stay within the image
        layer_rect = self.layer.image.rect()
        return rect.intersected(layer_rect)

    def execute(self):
        if not self.bounding_rect.isValid():
            return

        # Store the 'before' state only on the first execution
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        # Perform the drawing
        painter = QPainter(self.layer.image)
        try:
            if self.selection_shape:
                painter.setClipPath(self.selection_shape)

            painter.setPen(QPen(self.color))

            doc_size = QSize(self.document.width, self.document.height)

            if self.erase:
                # Create a mask image, same size as the layer, and fill it with transparency
                mask_image = QImage(self.layer.image.size(), QImage.Format_ARGB32)
                mask_image.fill(Qt.transparent)

                # Create a painter for the mask
                mask_painter = QPainter(mask_image)
                mask_painter.setPen(QPen(Qt.black)) # The color of the mask doesn't matter, just the alpha

                # Draw the path onto the mask
                doc_size = QSize(self.document.width, self.document.height)
                if len(self.points) == 1:
                    self.drawing.draw_brush(mask_painter, self.points[0], doc_size, self.brush_type, self.width, self.mirror_x, self.mirror_y)
                else:
                    for i in range(len(self.points) - 1):
                        self.drawing.draw_line_with_brush(
                            mask_painter,
                            self.points[i],
                            self.points[i + 1],
                            doc_size,
                            self.brush_type,
                            self.width,
                            self.mirror_x,
                            self.mirror_y,
                            erase=False  # We are drawing the mask, not erasing
                        )
                mask_painter.end()

                # Now, apply the mask to the layer's image
                painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                painter.drawImage(0, 0, mask_image)

            else: # Regular drawing
                painter.setPen(QPen(self.color))
                doc_size = QSize(self.document.width, self.document.height)
                if len(self.points) == 1:
                    self.drawing.draw_brush(painter, self.points[0], doc_size, self.brush_type, self.width, self.mirror_x, self.mirror_y)
                else:
                    for i in range(len(self.points) - 1):
                        self.drawing.draw_line_with_brush(
                            painter,
                            self.points[i],
                            self.points[i + 1],
                            doc_size,
                            self.brush_type,
                            self.width,
                            self.mirror_x,
                            self.mirror_y,
                            erase=False
                        )
        finally:
            painter.end()
            self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            # Use CompositionMode_Source to replace pixels, ignoring alpha
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(0, 0, self.before_image)
            painter.end()
            self.layer.on_image_change.emit()


class FlipCommand(Command):
    def __init__(self, document: Document, axis: str):
        self.document = document
        self.axis = axis  # 'horizontal' or 'vertical'

    def execute(self):
        if self.axis == 'horizontal':
            self.document.flip_horizontal()
        else:
            self.document.flip_vertical()

    def undo(self):
        # Flipping the same axis twice restores the original state
        self.execute()


class ResizeCommand(Command):
    def __init__(self, document: Document, new_width: int, new_height: int, interpolation: str):
        self.document = document
        self.new_width = new_width
        self.new_height = new_height
        self.interpolation = interpolation
        self.old_width = document.width
        self.old_height = document.height

    def execute(self):
        self.document.resize(self.new_width, self.new_height, self.interpolation)

    def undo(self):
        self.document.resize(self.old_width, self.old_height, self.interpolation)


class CropCommand(Command):
    def __init__(self, document: Document, rect: QRect):
        self.document = document
        self.rect = rect
        self.old_document_clone = None

    def execute(self):
        # Store state for undo *before* executing
        if self.old_document_clone is None:
            self.old_document_clone = self.document.clone()
        self.document.crop(self.rect)

    def undo(self):
        if self.old_document_clone:
            # This is a heavy undo, but crop is a complex operation to reverse manually
            self.document.width = self.old_document_clone.width
            self.document.height = self.old_document_clone.height
            self.document.layer_manager = self.old_document_clone.layer_manager
            # We need to re-emit signals so the UI updates
            self.document.layer_manager.layer_structure_changed.emit()


class AddLayerCommand(Command):
    def __init__(self, document: Document, image: QImage = None, name: str = None):
        self.document = document
        self.image = image
        self.name = name
        self.added_layer = None
        self.insertion_index = None
        self.old_active_layer = document.layer_manager.active_layer

    def execute(self):
        if self.added_layer is None:
            # First execution: create the layer
            if self.image:
                self.document.layer_manager.add_layer_with_image(self.image, self.name)
            else:
                self.document.layer_manager.add_layer(self.name)
            self.added_layer = self.document.layer_manager.active_layer
            self.insertion_index = self.document.layer_manager.active_layer_index
        else:
            # Redo: re-insert the existing layer object
            self.document.layer_manager.layers.insert(self.insertion_index, self.added_layer)
            self.document.layer_manager.select_layer(self.insertion_index)
            self.document.layer_manager.layer_structure_changed.emit()

    def undo(self):
        if self.added_layer:
            try:
                # `remove_layer` needs an index, and it's safer to find it dynamically
                index = self.document.layer_manager.layers.index(self.added_layer)
                self.document.layer_manager.remove_layer(index)

                # Restore the previously active layer
                if self.old_active_layer in self.document.layer_manager.layers:
                    old_active_index = self.document.layer_manager.layers.index(self.old_active_layer)
                    self.document.layer_manager.select_layer(old_active_index)

            except ValueError:
                pass

class PasteCommand(Command):
    def __init__(self, document: Document, q_image: QImage):
        self.document = document
        self.q_image = q_image
        self.added_layer = None
        self.insertion_index = None
        self.old_active_layer = document.layer_manager.active_layer

    def execute(self):
        if self.added_layer is None:
            # First execution
            if self.q_image.width() > self.document.width or self.q_image.height() > self.document.height:
                scaled_image = self.q_image.scaled(self.document.width, self.document.height, Qt.KeepAspectRatio, Qt.FastTransformation)
            else:
                scaled_image = self.q_image

            self.document.layer_manager.add_layer_with_image(scaled_image, name="Pasted Layer")
            self.added_layer = self.document.layer_manager.active_layer
            self.insertion_index = self.document.layer_manager.active_layer_index
        else:
            # Redo
            self.document.layer_manager.layers.insert(self.insertion_index, self.added_layer)
            self.document.layer_manager.select_layer(self.insertion_index)
            self.document.layer_manager.layer_structure_changed.emit()

    def undo(self):
        if self.added_layer:
            try:
                index = self.document.layer_manager.layers.index(self.added_layer)
                self.document.layer_manager.remove_layer(index)
                if self.old_active_layer in self.document.layer_manager.layers:
                    old_active_index = self.document.layer_manager.layers.index(self.old_active_layer)
                    self.document.layer_manager.select_layer(old_active_index)
            except ValueError:
                pass


class FillCommand(Command):
    def __init__(self, document: Document, layer: Layer, fill_pos: QPoint, fill_color: QColor, selection_shape: QPainterPath | None, mirror_x: bool, mirror_y: bool):
        self.document = document
        self.layer = layer
        self.fill_pos = fill_pos
        self.fill_color = fill_color
        self.selection_shape = selection_shape
        self.drawing = Drawing()
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        doc_width = self.document.width
        doc_height = self.document.height
        processed_points = set()
        points_to_fill = [self.fill_pos]

        if self.mirror_x:
            points_to_fill.append(QPoint(doc_width - 1 - self.fill_pos.x(), self.fill_pos.y()))
        if self.mirror_y:
            points_to_fill.append(QPoint(self.fill_pos.x(), doc_height - 1 - self.fill_pos.y()))
        if self.mirror_x and self.mirror_y:
            points_to_fill.append(QPoint(doc_width - 1 - self.fill_pos.x(), doc_height - 1 - self.fill_pos.y()))

        for point in points_to_fill:
            if tuple(point.toTuple()) not in processed_points:
                self.drawing.flood_fill(self.layer, point, self.fill_color, self.selection_shape)
                processed_points.add(tuple(point.toTuple()))

        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(0, 0, self.before_image)
            painter.end()
            self.layer.on_image_change.emit()


class ShapeCommand(Command):
    def __init__(self, layer: Layer, rect: QRect, shape_type: str, color: QColor, width: int, document, selection_shape: QPainterPath | None, mirror_x: bool = False, mirror_y: bool = False):
        self.layer = layer
        self.rect = rect
        self.shape_type = shape_type
        self.color = color
        self.width = width
        self.document = document
        self.selection_shape = selection_shape
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.drawing = Drawing()
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            # Add a 1 pixel buffer for safety, especially for shape outlines
            buffered_rect = self.rect.adjusted(-self.width, -self.width, self.width, self.width)
            self.before_image = self.layer.image.copy(buffered_rect)

        painter = QPainter(self.layer.image)
        try:
            if self.selection_shape:
                painter.setClipPath(self.selection_shape)

            pen = QPen(self.color)
            pen.setWidth(self.width)
            painter.setPen(pen)

            doc_size = QSize(self.document.width, self.document.height)
            # The brush type for shapes is always 'Circular' for now
            # This could be a parameter in the future
            brush_type = "Circular"
            if self.shape_type == 'ellipse':
                self.drawing.draw_ellipse(painter, self.rect, doc_size, brush_type, self.width, self.mirror_x, self.mirror_y)
            elif self.shape_type == 'rectangle':
                self.drawing.draw_rect(painter, self.rect, doc_size, brush_type, self.width, self.mirror_x, self.mirror_y)
        finally:
            painter.end()
            self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            # Add a 1 pixel buffer for safety
            buffered_rect = self.rect.adjusted(-self.width, -self.width, self.width, self.width)
            painter.drawImage(buffered_rect.topLeft(), self.before_image)
            painter.end()
            self.layer.on_image_change.emit()

class MoveCommand(Command):
    def __init__(self, layer: Layer, original_image: QImage, moved_image: QImage, delta: QPoint, original_selection_shape: QPainterPath | None):
        self.layer = layer
        self.original_image = original_image
        self.moved_image = moved_image
        self.delta = delta
        self.original_selection_shape = original_selection_shape

    def execute(self):
        painter = QPainter(self.layer.image)
        painter.drawImage(self.delta, self.moved_image)
        painter.end()
        self.layer.on_image_change.emit()

    def undo(self):
        painter = QPainter(self.layer.image)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawImage(0, 0, self.original_image)
        painter.end()
        self.layer.on_image_change.emit()

class DuplicateLayerCommand(Command):
    def __init__(self, layer_manager, index: int):
        self.layer_manager = layer_manager
        self.index = index
        self.duplicated_layer = None
        self.added_index = -1
        self.old_active_layer_index = layer_manager.active_layer_index

    def execute(self):
        if self.duplicated_layer is None:
            # First execution
            original_layer = self.layer_manager.layers[self.index]
            self.duplicated_layer = original_layer.clone()
            self.duplicated_layer.name = f"{original_layer.name} copy"
            self.added_index = self.index + 1

        self.layer_manager.layers.insert(self.added_index, self.duplicated_layer)
        self.layer_manager.select_layer(self.added_index)
        self.layer_manager.layer_structure_changed.emit()

    def undo(self):
        if self.duplicated_layer:
            try:
                # We need to find the layer's current index before removing
                current_index = self.layer_manager.layers.index(self.duplicated_layer)
                self.layer_manager.remove_layer(current_index) # remove_layer handles signals and active layer adjustment
                self.layer_manager.select_layer(self.old_active_layer_index) # Explicitly set active layer back
            except ValueError:
                # Layer not found, maybe already removed.
                pass
        
class ClearLayerCommand(Command):
    def __init__(self, layer: Layer, selection: QPainterPath | None):
        self.layer = layer
        self.selection = selection
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()
        self.layer.clear(self.selection)

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(0, 0, self.before_image)
            painter.end()
            self.layer.on_image_change.emit()
            
class RemoveLayerCommand(Command):
    def __init__(self, layer_manager, index: int):
        self.layer_manager = layer_manager
        self.index = index
        self.removed_layer = None
        self.old_active_layer_index = layer_manager.active_layer_index

    def execute(self):
        self.removed_layer = self.layer_manager.layers[self.index]
        self.layer_manager.remove_layer(self.index)

    def undo(self):
        if self.removed_layer:
            self.layer_manager.layers.insert(self.index, self.removed_layer)
            self.layer_manager.select_layer(self.old_active_layer_index)
            self.layer_manager.layer_structure_changed.emit()

class MoveLayerCommand(Command):
    def __init__(self, layer_manager, from_index: int, to_index: int):
        self.layer_manager = layer_manager
        self.from_index = from_index
        self.to_index = to_index

    def execute(self):
        layer = self.layer_manager.layers.pop(self.from_index)
        self.layer_manager.layers.insert(self.to_index, layer)
        # Adjust active layer index
        if self.layer_manager.active_layer_index == self.from_index:
            self.layer_manager.active_layer_index = self.to_index
        self.layer_manager.layer_structure_changed.emit()

    def undo(self):
        layer = self.layer_manager.layers.pop(self.to_index)
        self.layer_manager.layers.insert(self.from_index, layer)
        # Adjust active layer index
        if self.layer_manager.active_layer_index == self.to_index:
            self.layer_manager.active_layer_index = self.from_index
        self.layer_manager.layer_structure_changed.emit()
