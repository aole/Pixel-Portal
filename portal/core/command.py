from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING

from enum import Enum, auto

from PySide6.QtGui import QImage, QPainter, QPen, QColor, QPainterPath, QPainterPathStroker
from PySide6.QtCore import QRect, QPoint, Qt, QSize
from portal.core.layer import Layer
from portal.core.drawing import Drawing

if TYPE_CHECKING:
    from portal.core.document import Document


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


class CompositeCommand(Command):
    """A command that is composed of other commands."""
    def __init__(self, commands: list[Command], name: str = "Composite"):
        self.commands = commands
        self.name = name

    def execute(self):
        for command in self.commands:
            command.execute()

    def undo(self):
        for command in reversed(self.commands):
            command.undo()


class ModifyImageCommand(Command):
    """A command that modifies a layer's image with a drawing function."""
    def __init__(self, layer: Layer, drawing_func):
        self.layer = layer
        self.drawing_func = drawing_func
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        self.drawing_func(self.layer.image)
        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            self.layer.image = self.before_image.copy()
            self.layer.on_image_change.emit()


class DrawCommand(Command):
    def __init__(
        self,
        layer: Layer,
        points: list[QPoint],
        color: QColor,
        width: int,
        brush_type: str,
        document: 'Document',
        selection_shape: QPainterPath | None,
        erase: bool = False,
        mirror_x: bool = False,
        mirror_y: bool = False,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
        wrap: bool = False,
        pattern_image: QImage | None = None,
    ):
        from portal.core.document import Document
        self.layer = layer
        self.points = points
        self.color = color
        self.width = width
        self.brush_type = brush_type
        self.erase = erase
        self.document = document
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.mirror_x_position = mirror_x_position
        self.mirror_y_position = mirror_y_position
        self.selection_shape = selection_shape
        self.wrap = wrap
        self.pattern_image = pattern_image
        self.drawing = Drawing()

        self.bounding_rect = self._calculate_bounding_rect()
        self.before_image = None

    def _calculate_bounding_rect(self) -> QRect:
        if not self.points:
            return QRect()
        if self.wrap:
            return self.layer.image.rect()

        doc_width = self.document.width
        doc_height = self.document.height
        mirror_x = self.mirror_x
        mirror_y = self.mirror_y
        axis_x = self._resolve_axis(self.mirror_x_position, doc_width)
        axis_y = self._resolve_axis(self.mirror_y_position, doc_height)

        # Create the original path
        original_path = QPainterPath(self.points[0])
        for i in range(1, len(self.points)):
            original_path.lineTo(self.points[i])

        # Create a combined path including mirrored versions
        combined_path = QPainterPath()
        combined_path.addPath(original_path)

        if mirror_x and axis_x is not None:
            mirrored_path_x = QPainterPath()
            mirrored_path_x.moveTo(
                int(round(2 * axis_x - self.points[0].x())), self.points[0].y()
            )
            for i in range(1, len(self.points)):
                mirrored_path_x.lineTo(
                    int(round(2 * axis_x - self.points[i].x())),
                    self.points[i].y(),
                )
            combined_path.addPath(mirrored_path_x)

        if mirror_y and axis_y is not None:
            mirrored_path_y = QPainterPath()
            mirrored_path_y.moveTo(
                self.points[0].x(), int(round(2 * axis_y - self.points[0].y()))
            )
            for i in range(1, len(self.points)):
                mirrored_path_y.lineTo(
                    self.points[i].x(),
                    int(round(2 * axis_y - self.points[i].y())),
                )
            combined_path.addPath(mirrored_path_y)

        if mirror_x and mirror_y and axis_x is not None and axis_y is not None:
            mirrored_path_xy = QPainterPath()
            mirrored_path_xy.moveTo(
                int(round(2 * axis_x - self.points[0].x())),
                int(round(2 * axis_y - self.points[0].y())),
            )
            for i in range(1, len(self.points)):
                mirrored_path_xy.lineTo(
                    int(round(2 * axis_x - self.points[i].x())),
                    int(round(2 * axis_y - self.points[i].y())),
                )
            combined_path.addPath(mirrored_path_xy)


        stroker = QPainterPathStroker()
        stroker.setWidth(self.width)
        stroke = stroker.createStroke(combined_path)
        # Add a 1 pixel buffer for safety
        rect = stroke.boundingRect().toRect().adjusted(-1, -1, 1, 1)

        if (
            self.brush_type == "Pattern"
            and self.pattern_image is not None
            and not self.pattern_image.isNull()
        ):
            pad_x = max(0, (self.pattern_image.width() + 1) // 2)
            pad_y = max(0, (self.pattern_image.height() + 1) // 2)
            rect = rect.adjusted(-pad_x, -pad_y, pad_x, pad_y)

        # Intersect with layer bounds to stay within the image
        layer_rect = self.layer.image.rect()
        return rect.intersected(layer_rect)

    @staticmethod
    def _resolve_axis(position: float | None, size: int) -> float | None:
        if size <= 0:
            return None
        if position is None:
            return (size - 1) / 2.0
        return position

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
                    self.drawing.draw_brush(
                        mask_painter,
                        self.points[0],
                        doc_size,
                        self.brush_type,
                        self.width,
                        self.mirror_x,
                        self.mirror_y,
                        wrap=self.wrap,
                        pattern=self.pattern_image,
                        mirror_x_position=self.mirror_x_position,
                        mirror_y_position=self.mirror_y_position,
                    )
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
                            wrap=self.wrap,
                            erase=False,  # We are drawing the mask, not erasing
                            pattern=self.pattern_image,
                            mirror_x_position=self.mirror_x_position,
                            mirror_y_position=self.mirror_y_position,
                        )
                mask_painter.end()

                # Now, apply the mask to the layer's image
                painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                painter.drawImage(0, 0, mask_image)

            else: # Regular drawing
                painter.setPen(QPen(self.color))
                doc_size = QSize(self.document.width, self.document.height)
                if len(self.points) == 1:
                    self.drawing.draw_brush(
                        painter,
                        self.points[0],
                        doc_size,
                        self.brush_type,
                        self.width,
                        self.mirror_x,
                        self.mirror_y,
                        wrap=self.wrap,
                        pattern=self.pattern_image,
                        mirror_x_position=self.mirror_x_position,
                        mirror_y_position=self.mirror_y_position,
                    )
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
                            wrap=self.wrap,
                            erase=False,
                            pattern=self.pattern_image,
                            mirror_x_position=self.mirror_x_position,
                            mirror_y_position=self.mirror_y_position,
                        )
        finally:
            painter.end()
            self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image is not None:
            # Restore the image by swapping in the cached copy rather than
            # painting it back. Drawing through a QPainter can subtly mutate
            # pixel values, which broke exact undo comparisons in tests.
            self.layer.image = self.before_image.copy()
        self.layer.on_image_change.emit()


class FlipScope(Enum):
    LAYER = auto()
    FRAME = auto()
    DOCUMENT = auto()


class FlipCommand(Command):
    def __init__(
        self,
        document: 'Document',
        horizontal: bool,
        vertical: bool,
        scope: FlipScope,
    ):
        from portal.core.document import Document
        self.document = document
        self.horizontal = horizontal
        self.vertical = vertical
        self.scope = scope
        self._before_images: dict[int, QImage] = {}
        self._target_layers: list['Layer'] | None = None

    def execute(self):
        target_layers = self._resolve_target_layers()
        if not target_layers:
            return
        if not self._before_images:
            for layer in target_layers:
                self._before_images[id(layer)] = layer.image.copy()

        for layer in target_layers:
            if self.horizontal:
                layer.flip_horizontal()
            if self.vertical:
                layer.flip_vertical()

    def undo(self):
        for layer in self._resolve_target_layers():
            before_image = self._before_images.get(id(layer))
            if before_image is None:
                continue
            layer.image = before_image.copy()
            layer.on_image_change.emit()

    def _resolve_target_layers(self) -> list['Layer']:
        if self._target_layers is not None:
            return self._target_layers

        manager = getattr(self.document, "layer_manager", None)
        if manager is None:
            self._target_layers = []
            return self._target_layers

        if self.scope is FlipScope.LAYER:
            layer = manager.active_layer
            layers = [layer] if layer is not None else []
        elif self.scope is FlipScope.DOCUMENT:
            layers = list(getattr(manager, "layers", []))
        else:
            # ``FRAME`` falls back to operating on the visible stack now that
            # animation support has been removed.
            layers = list(getattr(manager, "layers", []))

        self._target_layers = layers
        return layers


class ResizeCommand(Command):
    def __init__(self, document: 'Document', new_width: int, new_height: int, interpolation: str):
        from portal.core.document import Document
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
    def __init__(self, document: 'Document', rect: QRect):
        from portal.core.document import Document
        self.document = document
        self.rect = rect
        self.old_document_clone = None

    def execute(self):
        # Store state for undo *before* executing
        if self.old_document_clone is None:
            self.old_document_clone = self.document.clone()
        self.document.crop(self.rect)

    def undo(self):
        if not self.old_document_clone:
            return

        original_doc = self.old_document_clone
        current_manager = self.document.layer_manager
        original_manager = original_doc.layer_manager

        # Restore document dimensions.
        self.document.width = original_doc.width
        self.document.height = original_doc.height
        current_manager.width = original_manager.width
        current_manager.height = original_manager.height

        # Restore layer images and properties in place so existing command
        # references remain valid for subsequent undo operations.
        current_layers = current_manager.layers
        original_layers = original_manager.layers

        if len(current_layers) != len(original_layers):
            # Fallback: replace the stack entirely if counts diverge (shouldn't
            # happen for crop but keeps undo resilient to future changes).
            current_manager.layers = [layer.clone(deep_copy=True) for layer in original_layers]
        else:
            for current_layer, original_layer in zip(current_layers, original_layers):
                current_layer.image = original_layer.image.copy()
                current_layer.visible = original_layer.visible
                current_layer.opacity = original_layer.opacity
                current_layer.name = original_layer.name
                current_layer.on_image_change.emit()

        current_manager.active_layer_index = original_manager.active_layer_index
        current_manager.layer_structure_changed.emit()


class AddLayerCommand(Command):
    def __init__(self, document: 'Document', image: QImage = None, name: str = None):
        from portal.core.document import Document
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
            manager = self.document.layer_manager
            if self.added_layer is None or self.insertion_index is None:
                return
            manager.layers.insert(self.insertion_index, self.added_layer)
            manager.select_layer(self.insertion_index)
            manager.layer_structure_changed.emit()

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
    def __init__(self, document: 'Document', q_image: QImage):
        from portal.core.document import Document
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
            manager = self.document.layer_manager
            if self.added_layer is None or self.insertion_index is None:
                return
            manager.layers.insert(self.insertion_index, self.added_layer)
            manager.select_layer(self.insertion_index)
            manager.layer_structure_changed.emit()

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


class PasteInSelectionCommand(Command):
    def __init__(self, document: 'Document', q_image: QImage, selection: QPainterPath):
        from portal.core.document import Document
        self.document = document
        self.q_image = q_image
        self.selection = selection
        self.added_layer = None
        self.insertion_index = None
        self.old_active_layer = document.layer_manager.active_layer

    def execute(self):
        if self.added_layer is None:
            # First execution
            pasted_content_image = QImage(self.document.width, self.document.height, QImage.Format_ARGB32)
            pasted_content_image.fill(Qt.transparent)

            painter = QPainter(pasted_content_image)
            painter.setClipPath(self.selection)

            # Paste the image at the top-left of the selection's bounding rect
            point = self.selection.boundingRect().topLeft()
            painter.drawImage(point, self.q_image)
            painter.end()

            self.document.layer_manager.add_layer_with_image(pasted_content_image, name="Pasted Layer")
            self.added_layer = self.document.layer_manager.active_layer
            self.insertion_index = self.document.layer_manager.active_layer_index
        else:
            # Redo
            manager = self.document.layer_manager
            if self.added_layer is None or self.insertion_index is None:
                return
            manager.layers.insert(self.insertion_index, self.added_layer)
            manager.select_layer(self.insertion_index)
            manager.layer_structure_changed.emit()

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
    def __init__(
        self,
        document: 'Document',
        layer: Layer,
        fill_pos: QPoint,
        fill_color: QColor,
        selection_shape: QPainterPath | None,
        mirror_x: bool,
        mirror_y: bool,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
        contiguous: bool = True,
    ):
        from portal.core.document import Document
        self.document = document
        self.layer = layer
        self.fill_pos = fill_pos
        self.fill_color = fill_color
        self.selection_shape = selection_shape
        self.drawing = Drawing()
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.mirror_x_position = mirror_x_position
        self.mirror_y_position = mirror_y_position
        self.contiguous = bool(contiguous)
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            self.before_image = self.layer.image.copy()

        doc_width = self.document.width
        doc_height = self.document.height
        axis_x = self._resolve_axis(self.mirror_x_position, doc_width)
        axis_y = self._resolve_axis(self.mirror_y_position, doc_height)
        processed_points = set()
        points_to_fill = [self.fill_pos]

        if self.mirror_x and axis_x is not None:
            mirrored_x = int(round(2 * axis_x - self.fill_pos.x()))
            if 0 <= mirrored_x < doc_width:
                points_to_fill.append(QPoint(mirrored_x, self.fill_pos.y()))
        if self.mirror_y and axis_y is not None:
            mirrored_y = int(round(2 * axis_y - self.fill_pos.y()))
            if 0 <= mirrored_y < doc_height:
                points_to_fill.append(QPoint(self.fill_pos.x(), mirrored_y))
        if self.mirror_x and self.mirror_y and axis_x is not None and axis_y is not None:
            mirrored_x = int(round(2 * axis_x - self.fill_pos.x()))
            mirrored_y = int(round(2 * axis_y - self.fill_pos.y()))
            if 0 <= mirrored_x < doc_width and 0 <= mirrored_y < doc_height:
                points_to_fill.append(QPoint(mirrored_x, mirrored_y))

        for point in points_to_fill:
            if tuple(point.toTuple()) not in processed_points:
                self.drawing.flood_fill(
                    self.layer,
                    point,
                    self.fill_color,
                    self.selection_shape,
                    contiguous=self.contiguous,
                )
                processed_points.add(tuple(point.toTuple()))

        self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(0, 0, self.before_image)
            painter.end()
            self.layer.on_image_change.emit()

    @staticmethod
    def _resolve_axis(position: float | None, size: int) -> float | None:
        if size <= 0:
            return None
        if position is None:
            return (size - 1) / 2.0
        return position


class ShapeCommand(Command):
    def __init__(
        self,
        layer: Layer,
        rect: QRect,
        shape_type: str,
        color: QColor,
        width: int,
        document: 'Document',
        selection_shape: QPainterPath | None,
        mirror_x: bool = False,
        mirror_y: bool = False,
        wrap: bool = False,
        brush_type: str = "Circular",
        pattern_image: QImage | None = None,
        mirror_x_position: float | None = None,
        mirror_y_position: float | None = None,
    ):
        from portal.core.document import Document
        self.layer = layer
        self.rect = rect
        self.shape_type = shape_type
        self.color = color
        self.width = width
        self.document = document
        self.selection_shape = selection_shape
        self.mirror_x = mirror_x
        self.mirror_y = mirror_y
        self.wrap = wrap
        self.brush_type = brush_type
        self.pattern_image = pattern_image
        self.mirror_x_position = mirror_x_position
        self.mirror_y_position = mirror_y_position
        self.drawing = Drawing()
        self.before_image = None

    def execute(self):
        if self.before_image is None:
            if self.wrap:
                self.before_image = self.layer.image.copy()
            else:
                pad_x, pad_y = self._calculate_padding()
                buffered_rect = self.rect.adjusted(-pad_x, -pad_y, pad_x, pad_y)
                self.before_image = self.layer.image.copy(buffered_rect)

        painter = QPainter(self.layer.image)
        try:
            if self.selection_shape:
                painter.setClipPath(self.selection_shape)

            pen = QPen(self.color)
            pen.setWidth(self.width)
            painter.setPen(pen)

            doc_size = QSize(self.document.width, self.document.height)
            if self.shape_type == 'ellipse':
                self.drawing.draw_ellipse(
                    painter,
                    self.rect,
                    doc_size,
                    self.brush_type,
                    self.width,
                    self.mirror_x,
                    self.mirror_y,
                    wrap=self.wrap,
                    pattern=self.pattern_image,
                    mirror_x_position=self.mirror_x_position,
                    mirror_y_position=self.mirror_y_position,
                )
            elif self.shape_type == 'rectangle':
                self.drawing.draw_rect(
                    painter,
                    self.rect,
                    doc_size,
                    self.brush_type,
                    self.width,
                    self.mirror_x,
                    self.mirror_y,
                    wrap=self.wrap,
                    pattern=self.pattern_image,
                    mirror_x_position=self.mirror_x_position,
                    mirror_y_position=self.mirror_y_position,
                )
        finally:
            painter.end()
            self.layer.on_image_change.emit()

    def undo(self):
        if self.before_image:
            painter = QPainter(self.layer.image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            if self.wrap:
                painter.drawImage(0, 0, self.before_image)
            else:
                pad_x, pad_y = self._calculate_padding()
                buffered_rect = self.rect.adjusted(-pad_x, -pad_y, pad_x, pad_y)
                painter.drawImage(buffered_rect.topLeft(), self.before_image)
            painter.end()
            self.layer.on_image_change.emit()

    def _calculate_padding(self) -> tuple[int, int]:
        pad_x = self.width
        pad_y = self.width
        if (
            self.brush_type == "Pattern"
            and self.pattern_image is not None
            and not self.pattern_image.isNull()
        ):
            pad_x = max(pad_x, (self.pattern_image.width() + 1) // 2)
            pad_y = max(pad_y, (self.pattern_image.height() + 1) // 2)
        return pad_x, pad_y

class MoveCommand(Command):
    def __init__(self, layer: Layer, before_move_image: QImage, after_cut_image: QImage, moved_image: QImage, delta: QPoint, original_selection_shape: QPainterPath | None):
        self.layer = layer
        self.before_move_image = before_move_image
        self.after_cut_image = after_cut_image
        self.moved_image = moved_image
        self.delta = delta
        self.original_selection_shape = original_selection_shape

    def execute(self):
        # Restore the 'after_cut' state first to handle redo correctly
        self.layer.image = self.after_cut_image.copy()
        painter = QPainter(self.layer.image)
        painter.drawImage(self.delta, self.moved_image)
        painter.end()
        self.layer.on_image_change.emit()

    def undo(self):
        # Restore the original state from before the move operation began
        self.layer.image = self.before_move_image.copy()
        self.layer.on_image_change.emit()

class DuplicateLayerCommand(Command):
    def __init__(self, document: 'Document', index: int):
        self.document = document
        self.layer_manager = document.layer_manager
        self.index = index
        self.duplicated_layer = None
        self.added_index = -1
        self.old_active_layer_index = self.layer_manager.active_layer_index

    def execute(self):
        if self.duplicated_layer is None:
            # First execution
            original_layer = self.layer_manager.layers[self.index]
            self.duplicated_layer = original_layer.clone(
                preserve_identity=False, deep_copy=True
            )
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


class ClearLayerAndKeysCommand(Command):
    """Clear a layer completely.

    Animation-era keyframe handling has been removed, so this command now acts
    as a convenience wrapper that wipes the layer's pixels and supports undo.
    """

    def __init__(self, document: 'Document', layer: Layer):
        self.document = document
        self.layer = layer
        self._before_image: QImage | None = None

    def execute(self):
        layer = self.layer
        if layer is None:
            return

        if self._before_image is None:
            self._before_image = layer.image.copy()

        layer.clear(None)
        layer.on_image_change.emit()

    def undo(self):
        layer = self.layer
        if layer is None or self._before_image is None:
            return

        layer.image = self._before_image.copy()
        layer.on_image_change.emit()
            
class RemoveLayerCommand(Command):
    def __init__(self, document: 'Document', index: int):
        self.document = document
        self.layer_manager = document.layer_manager
        self.index = index
        self.removed_layer = None
        self.old_active_layer_index = self.layer_manager.active_layer_index

    def execute(self):
        self.removed_layer = self.layer_manager.layers[self.index]
        self.layer_manager.remove_layer(self.index)

    def undo(self):
        if self.removed_layer:
            self.layer_manager.layers.insert(self.index, self.removed_layer)
            self.layer_manager.layer_structure_changed.emit()
            restore_index = self.old_active_layer_index
            if restore_index >= len(self.layer_manager.layers):
                restore_index = len(self.layer_manager.layers) - 1
            if restore_index >= 0:
                try:
                    self.layer_manager.select_layer(restore_index)
                except IndexError:
                    pass

class MoveLayerCommand(Command):
    def __init__(self, document: 'Document', from_index: int, to_index: int):
        self.document = document
        self.from_index = from_index
        self.to_index = to_index
        self._before_order: List[Layer] | None = None
        self._after_order: List[Layer] | None = None
        self._before_active: Optional[int] = None
        self._after_active: Optional[int] = None

    def execute(self):
        manager = getattr(self.document, "layer_manager", None)
        if manager is None:
            return

        layers = manager.layers
        count = len(layers)
        if count == 0:
            return

        from_index = max(0, min(self.from_index, count - 1))
        to_index = max(0, min(self.to_index, count - 1))
        if from_index == to_index:
            return

        if self._before_order is None:
            self._before_order = list(layers)
            self._before_active = manager.active_layer_index

            layer = layers.pop(from_index)
            layers.insert(to_index, layer)

            self._after_order = list(layers)
            self._after_active = self._resolve_active_index(
                self._before_active, from_index, to_index, len(layers)
            )

            if self._after_active is not None:
                manager.active_layer_index = self._after_active
        else:
            if self._after_order is None:
                return
            manager.layers = list(self._after_order)
            if self._after_active is not None and manager.layers:
                manager.active_layer_index = max(
                    0, min(self._after_active, len(manager.layers) - 1)
                )
            manager.layer_structure_changed.emit()
            return

        manager.layer_structure_changed.emit()

    def undo(self):
        manager = getattr(self.document, "layer_manager", None)
        if manager is None or self._before_order is None:
            return

        manager.layers = list(self._before_order)
        if self._before_active is not None and manager.layers:
            manager.active_layer_index = max(
                0, min(self._before_active, len(manager.layers) - 1)
            )
        manager.layer_structure_changed.emit()

    @staticmethod
    def _resolve_active_index(
        active_index: Optional[int],
        from_index: int,
        to_index: int,
        count: int,
    ) -> Optional[int]:
        if active_index is None:
            return None

        result = active_index
        if active_index == from_index:
            result = to_index
        elif from_index < to_index and from_index < active_index <= to_index:
            result = active_index - 1
        elif to_index < from_index and to_index <= active_index < from_index:
            result = active_index + 1

        return max(0, min(result, max(0, count - 1)))


class SetLayerOpacityCommand(Command):
    def __init__(self, layer: Layer, opacity: float, *, document: Optional['Document'] = None):
        self.layer = layer
        self.new_opacity = opacity
        self.old_opacity = layer.opacity
        self.document = document
        self._layer_uid = getattr(layer, "uid", None)
        self._instances: List[Layer] | None = None
        self._previous_values: List[float] | None = None

    def _collect_instances(self) -> List[Layer]:
        if self._instances is not None:
            return self._instances

        instances: List[Layer] = []
        if self.layer is not None:
            instances = [self.layer]

        self._instances = instances
        return self._instances

    def execute(self):
        instances = self._collect_instances()
        if self._previous_values is None:
            self._previous_values = [instance.opacity for instance in instances]
        for instance in instances:
            instance.opacity = self.new_opacity

    def undo(self):
        if self._previous_values is None:
            return
        instances = self._collect_instances()
        for instance, previous in zip(instances, self._previous_values):
            instance.opacity = previous
