from abc import ABC, abstractmethod
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QPainterPath, QPainterPathStroker
from PySide6.QtCore import QRect, QPoint, Qt
from .layer import Layer
from .document import Document


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
    def __init__(self, layer: Layer, points: list[QPoint], color: QColor, width: int, brush_type: str, erase: bool = False):
        self.layer = layer
        self.points = points
        self.color = color
        self.width = width
        self.brush_type = brush_type
        self.erase = erase

        self.bounding_rect = self._calculate_bounding_rect()
        self.before_image = None

    def _calculate_bounding_rect(self) -> QRect:
        if not self.points:
            return QRect()

        path = QPainterPath(self.points[0])
        for i in range(1, len(self.points)):
            path.lineTo(self.points[i])

        stroker = QPainterPathStroker()
        stroker.setWidth(self.width)
        stroke = stroker.createStroke(path)
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
            self.before_image = self.layer.image.copy(self.bounding_rect)

        # Perform the drawing
        painter = QPainter(self.layer.image)

        if self.erase:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        pen = QPen()
        pen.setColor(self.color)
        pen.setWidth(self.width)

        if self.brush_type == "Circular":
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        else:
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if len(self.points) == 1:
            painter.drawPoint(self.points[0])
        else:
            path = QPainterPath(self.points[0])
            for i in range(1, len(self.points)):
                path.lineTo(self.points[i])
            painter.drawPath(path)

        painter.end()
        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            # Use CompositionMode_Source to replace pixels, ignoring alpha
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(self.bounding_rect.topLeft(), self.before_image)
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
    def __init__(self, document: Document, layer: Layer, fill_pos: QPoint, fill_color: QColor, selection_shape: QPainterPath | None, drawing, mirror_x: bool, mirror_y: bool):
        self.document = document
        self.layer = layer
        self.fill_pos = fill_pos
        self.fill_color = fill_color
        self.selection_shape = selection_shape
        self.drawing = drawing
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        self.drawing.app.pen_color = self.fill_color

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
                self.drawing.flood_fill(point, self.selection_shape)
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
    def __init__(self, layer: Layer, rect: QRect, shape_type: str, color: QColor, width: int, drawing):
        self.layer = layer
        self.rect = rect
        self.shape_type = shape_type
        self.color = color
        self.width = width
        self.drawing = drawing
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            # Add a 1 pixel buffer for safety, especially for shape outlines
            buffered_rect = self.rect.adjusted(-self.width, -self.width, self.width, self.width)
            self.before_image = self.layer.image.copy(buffered_rect)

        painter = QPainter(self.layer.image)
        pen = QPen(self.color)
        pen.setWidth(self.width)
        painter.setPen(pen)

        if self.shape_type == 'ellipse':
            self.drawing.draw_ellipse(painter, self.rect)
        elif self.shape_type == 'rectangle':
            self.drawing.draw_rect(painter, self.rect)

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
